"""Safe file ingestion — sniffs magic bytes, generates safe storage path.

Files land in the shared volume mounted at ``UPLOAD_DIR`` (default
``/uploads``); JupyterLab mounts the same volume at
``/home/jovyan/work/uploads`` so the analyst can immediately read what they
just uploaded.
"""

from __future__ import annotations

import os
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path

UPLOAD_DIR = Path(os.environ.get("UPLOAD_DIR", "/uploads"))
MAX_BYTES = 1024 * 1024 * 1024  # 1 GiB hard cap


# Extension → (allowed kinds, optional magic-byte prefix)
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
    jupyter_path: str  # path the analyst sees inside JupyterLab
    kind: str
    size_bytes: int
    mime: str


class IngestError(ValueError):
    pass


def _safe_filename(name: str) -> str:
    norm = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode("ascii")
    # Strip path separators, control chars; collapse whitespace and weird chars
    norm = re.sub(r"[^A-Za-z0-9._-]+", "_", norm).strip("._-")
    if not norm:
        norm = "upload"
    if len(norm) > 200:
        norm = norm[:200]
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
    """Stream the upload into the shared volume, validating size + magic.

    ``stream`` may be a FastAPI ``UploadFile`` or any object with ``read(n)``.
    """
    safe = _safe_filename(filename)
    kind, magic = _kind_for(safe)

    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    # Avoid clobbering existing files. Append a numeric suffix.
    target = _unique_path(UPLOAD_DIR / safe)

    total = 0
    first_chunk: bytes | None = None
    chunk_size = 1024 * 1024
    with target.open("wb") as out:
        while True:
            chunk = await stream.read(chunk_size)
            if not chunk:
                break
            if first_chunk is None:
                first_chunk = chunk[: max(len(magic) if magic else 0, 8)]
            total += len(chunk)
            if total > MAX_BYTES:
                out.close()
                target.unlink(missing_ok=True)
                raise IngestError("file exceeds 1 GiB limit")
            out.write(chunk)

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
