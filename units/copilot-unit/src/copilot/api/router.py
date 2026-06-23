"""코파일럿 HTTP 표면 — POST /api/copilot/chat (스트리밍).

요청 한 건의 흐름:

1. 호출자가 ``{question, history?, connection_id?}``를 보낸다.
2. ``connection_id``가 주어지면 data-unit을 통해 스키마를 인트로스펙트
   (introspect)해, 메타데이터만 담은 시스템 프롬프트를 만든다(FR-LLM-05).
3. 설정된 프로바이더(Anthropic / Ollama / 내부망 vLLM)가 텍스트를 줄 단위
   JSON 청크로 스트리밍한다. 각 청크는 서버를 떠나기 전에 PII 패턴 검사를
   거쳐 마스킹된다.
4. ``audit_log`` 행에 질문, 프로바이더명, 응답 길이, 그리고 "행 데이터는
   전송하지 않았음"을 명시하는 플래그를 기록한다.
"""

from __future__ import annotations

import json
import os
import re
import time
from datetime import datetime
from typing import Annotated, Any
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from audit.models import AuditLog
from auth.api.oidc_dependency import actor_from_request
from backend.db import get_session
from credential.models import Credential
from copilot.factory import get_provider
from copilot.prompts import build_system_prompt
from copilot.providers.base import ChatMessage
from data.models import Connection, PiiPattern

router = APIRouter(prefix="/api/copilot", tags=["copilot"])
Session = Annotated[AsyncSession, Depends(get_session)]


class ChatTurn(BaseModel):
    role: str = Field(pattern="^(user|assistant)$")
    content: str


class ChatRequest(BaseModel):
    question: str = Field(min_length=1, max_length=8000)
    history: list[ChatTurn] = Field(default_factory=list, max_length=20)
    connection_id: str | None = None


@router.get("/ping")
async def ping() -> dict[str, str]:
    return {"status": "ok"}


class CellInsertEvent(BaseModel):
    notebook_path: str = Field(min_length=1, max_length=512)
    language: str = Field(pattern="^(sql|python)$")
    source_length: int = Field(ge=0)
    connection_id: str | None = None


@router.post("/cell-inserted")
async def cell_inserted(
    body: CellInsertEvent, session: Session, request: Request
) -> dict[str, str]:
    """SPA가 코드 셀을 JupyterLab에 넣은 직후 호출하는 감사 훅(audit hook).

    추가 전용(append-only) ``copilot_cell_inserted`` 이벤트를 남겨, 감사자가
    어떤 생성 셀이 어느 노트북에 들어갔는지 정확히 재구성할 수 있게 한다.
    """
    actor = await actor_from_request(request)
    session.add(
        AuditLog(
            event_type="copilot_cell_inserted",
            actor_id=actor,
            resource=f"notebook:{body.notebook_path}",
            result="success",
            occurred_at=datetime.utcnow(),
            corr_id=f"copilot-cell-{uuid4()}",
            payload={
                "notebook_path": body.notebook_path,
                "language": body.language,
                "source_length": body.source_length,
                "connection_id": body.connection_id,
            },
        )
    )
    await session.commit()
    return {"status": "recorded"}


@router.get("/provider")
async def current_provider() -> dict[str, str]:
    """SPA가 올바른 라벨(어느 모델인지)을 표시할 수 있게 조회용으로 노출한다."""
    try:
        p = get_provider()
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=503, detail=str(exc)) from None
    return {"provider": p.name}


# 스키마 인트로스펙션을 위한 인메모리 TTL 캐시. 키는 connection_id(str).
# 단일 프로세스 앱이라 평범한 모듈 dict면 충분하다(락 불필요).
# 값 형태: (monotonic 타임스탬프, engine, schema). 성공한 인트로스펙션만
# 캐시하고, 오류는 캐시하지 않아 다음 번에 DB를 다시 친다.
_SCHEMA_CACHE_TTL = 300.0  # 초
_schema_cache: dict[str, tuple[float, str, dict[str, Any] | None]] = {}


def invalidate_schema_cache(connection_id: str | None = None) -> None:
    """특정 연결 하나, 또는 전체의 캐시된 인트로스펙션을 버린다.

    엔드포인트에 연결돼 있지는 않지만, 연결의 스키마·자격증명을 바꾼 뒤
    즉시 최신 메타데이터가 필요한 호출자를 위해 제공한다.
    """
    if connection_id is None:
        _schema_cache.clear()
    else:
        _schema_cache.pop(connection_id, None)


async def _introspect_cached(
    request: Request,
    session: AsyncSession,
    connection_id: UUID,
) -> tuple[str, dict[str, Any] | None]:
    """:func:`_introspect`를 감싼 TTL 캐시 래퍼(TTFT 단축 효과가 가장 크다).

    만료되지 않은 캐시가 있으면 DB를 건드리지 않고 ``(engine, schema)``를
    그대로 돌려준다. 미스/만료 시에만 실제 인트로스펙션을 돌리고 결과를 저장한다.
    (TTFT = Time To First Token, 첫 토큰까지 걸리는 시간.)
    """
    key = str(connection_id)
    now = time.monotonic()
    cached = _schema_cache.get(key)
    if cached is not None and (now - cached[0]) < _SCHEMA_CACHE_TTL:
        return cached[1], cached[2]
    engine, schema = await _introspect(request, session, connection_id)
    _schema_cache[key] = (now, engine, schema)
    return engine, schema


async def _introspect(
    request: Request,
    session: AsyncSession,
    connection_id: UUID,
) -> tuple[str, dict[str, Any] | None]:
    """data-unit까지 들어가 시스템 프롬프트용 스키마 메타데이터를 만든다.

    (engine, schema-dict)를 돌려준다. 스키마에는 테이블·컬럼 이름과 타입만
    담기고 행 값은 절대 담기지 않는다(FR-LLM-05).

    자격증명을 못 얻거나 커넥터 생성·인트로스펙션이 실패하면, 던지지 않고
    스키마를 ``None``으로 돌려준다 — 코파일럿은 스키마 없이도 답할 수 있어야
    하므로, 메타데이터 확보 실패가 채팅 자체를 막아선 안 된다.
    """
    from data.connectors.factory import open_runtime_connector
    from data.schemas import ConnectionSpec
    from dataplatform_shared.result import Err

    conn = await session.get(Connection, connection_id)
    if conn is None:
        return "", None
    spec = ConnectionSpec(
        name=conn.name,
        engine=conn.engine,
        host=conn.host,
        port=conn.port,
        database=conn.database,
        credential_id=str(conn.credential_id),
        options=conn.options or {},
    )
    # 비밀번호는 DB에 저장하지 않고 Vault에서만 읽는다. Vault 어댑터가 없거나
    # username이 비어 있으면 자격증명을 못 얻으므로 그대로 비워 둔다.
    username = (conn.options or {}).get("username", "")
    vault = getattr(request.app.state, "vault_adapter", None)
    password = ""
    if vault is not None and username:
        cred = await session.get(Credential, conn.credential_id)
        # 소프트 삭제(deleted_at)된 자격증명은 무효로 본다.
        if cred is not None and cred.deleted_at is None:
            v = await vault.read(cred.vault_path)
            if v.ok:
                password = v.value.reveal()
    # 접속 자격이 불완전하면 인트로스펙션을 시도하지 않고 스키마 없이 진행한다.
    if not username or not password:
        return conn.engine, None
    factory_result = open_runtime_connector(spec, username=username, password=password)
    if isinstance(factory_result, Err):
        return conn.engine, None
    connector = factory_result.value
    try:
        return conn.engine, await connector.introspect()
    except Exception:  # noqa: BLE001
        return conn.engine, None


# 기본 PII 정규식. (이메일·전화번호·주민등록번호(rrn). 한국 형식 포함.)
_DEFAULT_PII_REGEXES: tuple[tuple[str, str], ...] = (
    ("email", r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b"),
    ("phone", r"\b01[016789]-?\d{3,4}-?\d{4}\b"),
    ("rrn",   r"\b\d{6}-?\d{7}\b"),
)


# 컴파일된 PII 정규식 목록을 위한 인메모리 TTL 캐시. 패턴 집합은 작고 거의
# 바뀌지 않아, 매 요청마다 다시 컴파일하면 순수 오버헤드다.
# 값 형태: (monotonic 타임스탬프, patterns).
_PII_CACHE_TTL = 60.0  # 초
_pii_cache: dict[str, tuple[float, list[tuple[str, re.Pattern[str]]]]] = {}


def invalidate_pii_cache() -> None:
    """캐시된 PII 정규식 목록을 버려, 다음 요청이 다시 컴파일하게 한다."""
    _pii_cache.clear()


async def _load_pii_regexes_cached(
    session: AsyncSession,
) -> list[tuple[str, re.Pattern[str]]]:
    """:func:`_load_pii_regexes`를 감싼 TTL 캐시 래퍼."""
    now = time.monotonic()
    cached = _pii_cache.get("patterns")
    if cached is not None and (now - cached[0]) < _PII_CACHE_TTL:
        return cached[1]
    patterns = await _load_pii_regexes(session)
    _pii_cache["patterns"] = (now, patterns)
    return patterns


async def _load_pii_regexes(session: AsyncSession) -> list[tuple[str, re.Pattern[str]]]:
    rows = (
        await session.execute(select(PiiPattern).where(PiiPattern.is_active.is_(True)))
    ).scalars().all()
    patterns: list[tuple[str, re.Pattern[str]]] = []
    for r in rows:
        # 운영자가 DB에 넣은 잘못된 정규식 하나가 전체 마스킹을 깨뜨리지
        # 않도록, 컴파일 실패한 패턴은 건너뛴다.
        try:
            patterns.append((r.kind, re.compile(r.regex)))
        except re.error:
            continue
    # DB 시드 상태에 의존하지 않도록 방어용 기본 패턴을 항상 추가한다 —
    # DB가 비어 있어도 최소한의 PII는 마스킹된다.
    for kind, raw in _DEFAULT_PII_REGEXES:
        try:
            patterns.append((kind, re.compile(raw)))
        except re.error:
            continue
    return patterns


def _mask_text(text: str, patterns: list[tuple[str, re.Pattern[str]]]) -> str:
    # 모든 패턴을 순서대로 적용해 매칭 구간을 [REDACTED]로 치환한다. 청크가
    # 서버를 떠나기 직전 마지막 방어선이다.
    out = text
    for _, pattern in patterns:
        out = pattern.sub("[REDACTED]", out)
    return out


async def _copilot_rate_limited(request: Request, actor_key: str) -> bool:
    """사용자당 분당 10요청 제한(FR-LLM-04 취지 / NFR-SEC-11).

    백엔드가 Redis를 연결해 뒀으면(``app.state.copilot_limiter``) 그걸 쓰고,
    없으면 프로세스 로컬 슬라이딩 윈도(sliding-window) dict로 폴백한다 — Redis
    없는 단일 파드(single-pod) 데모 배포라도 속도 제한은 걸린다.

    True를 돌려주면 "제한 초과"라는 뜻이다.
    """
    import time as _t

    limiter = getattr(request.app.state, "copilot_limiter", None)
    if limiter is not None:
        # 공유 리미터의 check()는 통과 시 True를 주므로, 의미를 맞추려 뒤집는다.
        return not await limiter.check(actor_key)

    # 로컬 폴백: actor마다 최근 요청 타임스탬프 리스트를 둔다.
    bucket = getattr(request.app.state, "_copilot_local_bucket", None)
    if bucket is None:
        bucket = {}
        request.app.state._copilot_local_bucket = bucket
    now = _t.time()
    arr = bucket.setdefault(actor_key, [])
    # 60초보다 오래된 항목을 떨궈 윈도를 1분으로 유지한다.
    cutoff = now - 60.0
    while arr and arr[0] < cutoff:
        arr.pop(0)
    if len(arr) >= 10:
        return True
    arr.append(now)
    return False


@router.post("/chat")
async def chat(
    body: ChatRequest,
    session: Session,
    request: Request,
) -> StreamingResponse:
    # 게이트웨이가 심은 x-forwarded-user를 1순위로, 없으면 클라이언트 IP를
    # 속도 제한 키로 쓴다(둘 다 없으면 "anonymous").
    actor_key = request.headers.get("x-forwarded-user") or request.client.host if request.client else "anonymous"
    if await _copilot_rate_limited(request, f"copilot:{actor_key}"):
        raise HTTPException(status_code=429, detail="copilot rate limit exceeded (10 req/min)")
    try:
        provider = get_provider()
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=503, detail=f"copilot provider unavailable: {exc!s}") from None

    engine = ""
    schema: dict[str, Any] | None = None
    if body.connection_id:
        try:
            engine, schema = await _introspect_cached(request, session, UUID(body.connection_id))
        except ValueError:
            raise HTTPException(status_code=422, detail="invalid connection id") from None

    system_prompt = build_system_prompt(connection_engine=engine, schema=schema)

    # 이전 대화 이력 뒤에 이번 질문을 user 메시지로 덧붙인다.
    messages: list[ChatMessage] = [
        {"role": t.role, "content": t.content} for t in body.history
    ]
    messages.append({"role": "user", "content": body.question})

    # PII 정규식은 스트리밍 시작 전에 한 번만 로드해, 청크마다 재조회를 피한다.
    pii_patterns = await _load_pii_regexes_cached(session)

    # 감사 actor: 로그인 세션(dp_session)으로 실제 사용자(이메일=아이디)를 해석한다.
    # 스트림이 시작되기 전에 계산해 generator 클로저에 담는다(요청 컨텍스트 보존).
    actor = await actor_from_request(request)
    # 거버넌스: 셀 실행 출력(행 값 포함 가능)은 내부망 LLM일 때만 프론트가 컨텍스트에
    # "[이 셀 출력]" 마커로 싣는다. 그 마커가 질문에 있으면 행 데이터가 전송된 것으로
    # 정직하게 기록한다(외부 API 사용 시엔 프론트가 출력을 싣지 않으므로 False 유지).
    row_data_sent = "[이 셀 출력]" in body.question
    audit_id = uuid4()

    async def generator():
        full = []
        try:
            async for chunk in provider.stream(system=system_prompt, messages=messages):
                # 청크는 클라이언트로 나가기 직전에 마스킹한다(서버 경계가 마지막
                # 방어선). 마스킹된 텍스트만 모아 감사용 길이 집계에 쓴다.
                masked = _mask_text(chunk, pii_patterns)
                full.append(masked)
                yield json.dumps({"chunk": masked}) + "\n"
        except Exception as exc:  # noqa: BLE001
            # 스트리밍 도중 오류는 끊지 않고 error 청크로 흘려 클라이언트가 인지하게 한다.
            yield json.dumps({"error": str(exc)}) + "\n"
        finally:
            full_text = "".join(full)
            # 감사 로그는 best-effort다. 실패해도 스트림을 깨지 않는다 —
            # 클라이언트는 이미 콘텐츠를 받았기 때문이다.
            try:
                session.add(
                    AuditLog(
                        event_type="copilot_chat",
                        actor_id=actor,
                        resource=f"copilot:{provider.name}",
                        result="success" if full_text else "failure",
                        occurred_at=datetime.utcnow(),
                        corr_id=f"copilot-{audit_id}",
                        payload={
                            "provider": provider.name,
                            "connection_id": body.connection_id,
                            "schema_attached": schema is not None,
                            "response_chars": len(full_text),
                            "row_data_transmitted": row_data_sent,
                        },
                    )
                )
                await session.commit()
            except Exception:  # noqa: BLE001
                await session.rollback()

    return StreamingResponse(generator(), media_type="application/x-ndjson")


# ---------------------------------------------------------------------------
# 셀 단위 인라인 편집 — LLM으로 하는 Cursor 스타일 "이 셀 다시 쓰기".
# 비스트리밍: 수정된 셀 소스 전체를 한 번에 돌려줘, SPA가 활성 셀 내용을
# 통째로 교체할 수 있게 한다.
# (아래 _EDIT_SYSTEM은 LLM 동작에 직결되는 프롬프트라 원문 영어 그대로 둔다.)
# ---------------------------------------------------------------------------
_EDIT_SYSTEM = """\
You are editing a SINGLE code cell inside a JupyterLab notebook.
Apply the user's instruction to the given cell and return the COMPLETE modified
cell — not a diff, not a snippet.

Hard rules:
1. Return ONLY the code, wrapped in exactly one fenced block tagged with the
   cell's language (```python or ```sql). No prose before or after.
2. Preserve everything that still works; change only what the instruction asks.
3. If the cell is SQL (starts with %%sql or is plainly SQL), keep it SQL and
   keep the %%sql magic if it was present.
4. Use ONLY tables/columns from the SCHEMA block (if present). Never echo PII
   values.
"""

_CODE_FENCE_RE = re.compile(r"```(?:sql|python|py)?\s*\n?(.*?)```", re.IGNORECASE | re.DOTALL)


def _extract_code(text: str) -> str:
    """첫 번째 펜스 코드 블록(```...```)을 꺼낸다. 없으면 공백 정리한 본문으로 폴백.

    모델이 규칙을 어기고 산문을 덧붙여도 코드만 추려 셀에 넣기 위함이다.
    """
    m = _CODE_FENCE_RE.search(text)
    if m:
        return m.group(1).strip("\n")
    return text.strip()


class EditCellRequest(BaseModel):
    source: str = Field(default="", max_length=20000)
    instruction: str = Field(min_length=1, max_length=4000)
    language: str = Field(default="python", pattern="^(python|sql)$")
    connection_id: str | None = None


@router.post("/edit-cell")
async def edit_cell(
    body: EditCellRequest,
    session: Session,
    request: Request,
) -> dict[str, str]:
    """지시(instruction)대로 노트북 셀 하나를 다시 쓰고, 새 소스를 돌려준다.

    채팅과 달리 스트리밍하지 않는다 — 결과 셀 전체가 필요하므로 청크를 모은
    뒤 펜스 블록만 추출하고 PII 마스킹해서 한 번에 반환한다.
    """
    actor_key = request.headers.get("x-forwarded-user") or (
        request.client.host if request.client else "anonymous"
    )
    if await _copilot_rate_limited(request, f"copilot-edit:{actor_key}"):
        raise HTTPException(status_code=429, detail="copilot rate limit exceeded (10 req/min)")
    try:
        provider = get_provider()
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=503, detail=f"copilot provider unavailable: {exc!s}") from None

    engine = ""
    schema: dict[str, Any] | None = None
    if body.connection_id:
        try:
            engine, schema = await _introspect_cached(request, session, UUID(body.connection_id))
        except ValueError:
            raise HTTPException(status_code=422, detail="invalid connection id") from None

    system_prompt = (
        _EDIT_SYSTEM.strip()
        + "\n\n"
        + build_system_prompt(connection_engine=engine, schema=schema)
    )
    user = (
        f"Current cell ({body.language}):\n"
        f"```{body.language}\n{body.source}\n```\n\n"
        f"Instruction: {body.instruction}\n\n"
        "Return the full modified cell as one fenced code block."
    )

    chunks: list[str] = []
    try:
        async for chunk in provider.stream(
            system=system_prompt,
            messages=[{"role": "user", "content": user}],
            # 단발성(멀티턴 아님)이므로 설정돼 있으면 더 가볍고 빠른 모델을 쓴다.
            # (내부망 vLLM 프로바이더는 이 override를 무시한다 — internal.py 참고.)
            model=os.environ.get("COPILOT_EDIT_MODEL") or None,
        ):
            chunks.append(chunk)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"copilot edit failed: {exc!s}") from None

    # 모은 출력에서 코드 블록만 추출한 뒤 PII 마스킹해 셀 소스로 돌려준다.
    pii_patterns = await _load_pii_regexes_cached(session)
    edited = _mask_text(_extract_code("".join(chunks)), pii_patterns)

    actor = await actor_from_request(request)
    try:
        session.add(
            AuditLog(
                event_type="copilot_cell_edit",
                actor_id=actor,
                resource=f"copilot:{provider.name}",
                result="success" if edited else "failure",
                occurred_at=datetime.utcnow(),
                corr_id=f"copilot-edit-{uuid4()}",
                payload={
                    "provider": provider.name,
                    "connection_id": body.connection_id,
                    "schema_attached": schema is not None,
                    "instruction_chars": len(body.instruction),
                    "result_chars": len(edited),
                    "row_data_transmitted": False,
                },
            )
        )
        await session.commit()
    except Exception:  # noqa: BLE001
        await session.rollback()

    return {"source": edited, "language": body.language}
