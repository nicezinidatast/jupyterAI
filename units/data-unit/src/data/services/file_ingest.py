"""안전한 파일 적재(ingestion) — 매직 바이트(magic bytes) 검사 + 안전한 저장 경로 생성.

업로드 파일은 ``UPLOAD_DIR``(기본 ``/uploads``)에 마운트된 공유 볼륨에 떨어진다.
JupyterLab도 같은 볼륨을 ``/home/jovyan/work/uploads``에 마운트하므로, 분석가가
방금 올린 파일을 곧바로 읽을 수 있다.

핵심 안전장치는 세 가지다: (1) 파일명 정규화로 경로 조작·이상 문자 차단,
(2) 매직 바이트로 확장자와 실제 내용 일치 검증(가짜 확장자 방지),
(3) 크기 상한(1 GiB)으로 디스크 고갈 방지.
"""

from __future__ import annotations

import os
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path

UPLOAD_DIR = Path(os.environ.get("UPLOAD_DIR", "/uploads"))
MAX_BYTES = 1024 * 1024 * 1024  # 1 GiB hard cap (디스크 고갈 방지용 강제 상한)


# 확장자 → (허용 종류, 매직 바이트 접두사 또는 None)
# 매직 바이트가 있는 형식은 첫 바이트가 일치해야 통과한다. None인 텍스트
# 형식(csv/json 등)은 매직 바이트가 없어 확장자만으로 종류를 정한다.
_KIND_RULES: dict[str, tuple[str, bytes | None]] = {
    ".csv":     ("csv", None),
    ".tsv":     ("tsv", None),
    ".json":    ("json", None),
    ".jsonl":   ("jsonl", None),
    ".ndjson":  ("ndjson", None),
    ".parquet": ("parquet", b"PAR1"),
    ".xlsx":    ("xlsx", b"PK\x03\x04"),
    ".feather": ("feather", b"ARROW1"),
    ".arrow":   ("feather", b"ARROW1"),
}


@dataclass
class IngestResult:
    safe_name: str
    storage_path: Path
    jupyter_path: str  # JupyterLab 안에서 분석가에게 보이는 경로
    kind: str
    size_bytes: int
    mime: str


class IngestError(ValueError):
    # 적재 거절 사유(미지원 확장자·크기 초과·매직 바이트 불일치)를 나타내는 예외.
    # router에서 415 응답으로 변환된다.
    pass


def _safe_filename(name: str) -> str:
    # 사용자 파일명을 그대로 디스크에 쓰면 경로 조작(../)·제어문자·널바이트 등으로
    # 위험하다. 그래서 ASCII로 정규화한 뒤 안전한 문자만 남긴다.
    norm = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode("ascii")
    # 경로 구분자·제어문자 제거. 영숫자와 . _ - 외 문자는 _ 로 치환하고
    # 앞뒤의 . _ - 를 다듬는다(숨김파일·확장자 혼란 방지).
    norm = re.sub(r"[^A-Za-z0-9._-]+", "_", norm).strip("._-")
    if not norm:
        norm = "upload"  # 정규화 후 빈 문자열이 되면 기본 이름으로 대체
    if len(norm) > 200:
        norm = norm[:200]  # 파일시스템 이름 길이 제한 대비
    return norm


def _kind_for(filename: str) -> tuple[str, bytes | None]:
    ext = Path(filename).suffix.lower()
    rule = _KIND_RULES.get(ext)
    if rule is None:
        raise IngestError(f"unsupported file extension: {ext or '(none)'}")
    return rule


def _mime_for(kind: str) -> str:
    return {
        "csv": "text/csv",
        "tsv": "text/tab-separated-values",
        "json": "application/json",
        "jsonl": "application/json-lines",
        "ndjson": "application/json-lines",
        "parquet": "application/vnd.apache.parquet",
        "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "feather": "application/vnd.apache.arrow.file",
    }.get(kind, "application/octet-stream")


async def ingest_upload(filename: str, stream) -> IngestResult:
    """업로드를 공유 볼륨으로 스트리밍 저장하며 크기·매직 바이트를 검증한다.

    ``stream``은 FastAPI ``UploadFile`` 또는 ``read(n)``을 가진 임의 객체면 된다.
    전체를 메모리에 올리지 않고 청크 단위로 흘려보내, 큰 파일도 메모리 압박 없이
    처리한다. 검증에 실패하면 부분 저장된 파일을 즉시 지워 잔여물을 남기지 않는다.
    """
    safe = _safe_filename(filename)
    kind, magic = _kind_for(safe)

    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    # 기존 파일을 덮어쓰지 않도록 숫자 접미사를 붙여 고유 경로를 얻는다.
    target = _unique_path(UPLOAD_DIR / safe)

    total = 0
    first_chunk: bytes | None = None
    chunk_size = 1024 * 1024
    with target.open("wb") as out:
        while True:
            chunk = await stream.read(chunk_size)
            if not chunk:
                break
            # 첫 청크 앞부분만 매직 바이트 검사용으로 보관한다(매직 길이와 8 중
            # 큰 쪽까지). 끝까지 다 받은 뒤 검사하므로 매직 길이 확보가 보장된다.
            if first_chunk is None:
                first_chunk = chunk[: max(len(magic) if magic else 0, 8)]
            total += len(chunk)
            # 상한 초과 시 더 받지 않고 부분 파일을 삭제한 뒤 거절(디스크 보호).
            if total > MAX_BYTES:
                out.close()
                target.unlink(missing_ok=True)
                raise IngestError("file exceeds 1 GiB limit")
            out.write(chunk)

    # 확장자가 요구하는 매직 바이트로 시작하지 않으면 위장 파일로 보고 거절.
    # 저장이 끝난 뒤 검사하므로, 불일치 시 이미 쓴 파일을 지워 잔여물을 없앤다.
    if magic is not None and first_chunk is not None and not first_chunk.startswith(magic):
        target.unlink(missing_ok=True)
        raise IngestError(f"file content does not match expected {kind} format")

    return IngestResult(
        safe_name=target.name,
        storage_path=target,
        jupyter_path=f"uploads/{target.name}",
        kind=kind,
        size_bytes=total,
        mime=_mime_for(kind),
    )


def _unique_path(p: Path) -> Path:
    # 동일 이름이 이미 있으면 ``name_1``, ``name_2`` 식으로 빈 번호를 찾아
    # 충돌을 피한다. 같은 파일명을 여러 번 올려도 기존 것을 덮어쓰지 않는다.
    if not p.exists():
        return p
    stem = p.stem
    suffix = p.suffix
    i = 1
    while True:
        candidate = p.with_name(f"{stem}_{i}{suffix}")
        if not candidate.exists():
            return candidate
        i += 1
