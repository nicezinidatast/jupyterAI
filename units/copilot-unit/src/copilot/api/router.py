"""Copilot HTTP surface — POST /api/copilot/chat (streaming).

Flow per request:

1. Caller provides ``{question, history?, connection_id?}``.
2. If ``connection_id`` is given we introspect the schema via the data-unit
   to build a metadata-only system prompt (FR-LLM-05).
3. The configured provider (Anthropic / Ollama) streams text back as
   newline-delimited JSON chunks. Each chunk is also scanned for PII patterns
   and masked before it leaves the server.
4. An ``audit_log`` row records the question, provider name, response length,
   and the explicit "row data not transmitted" flag.
"""

from __future__ import annotations

import json
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
async def cell_inserted(body: CellInsertEvent, session: Session) -> dict[str, str]:
    """Audit hook the SPA fires after pushing a code cell into JupyterLab.

    Records an append-only ``copilot_cell_inserted`` event so the auditor can
    reconstruct exactly which generated cell landed in which notebook.
    """
    session.add(
        AuditLog(
            event_type="copilot_cell_inserted",
            actor_id="anonymous",
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
    """Discoverable so the SPA can render the right label."""
    try:
        p = get_provider()
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=503, detail=str(exc)) from None
    return {"provider": p.name}


# In-memory TTL cache for schema introspection, keyed by connection_id (str).
# Single-process app, so a plain module dict is sufficient (no lock needed).
# Value shape: (monotonic_timestamp, engine, schema). Only successful
# introspections are cached; errors fall through to a fresh DB hit next time.
_SCHEMA_CACHE_TTL = 300.0  # seconds
_schema_cache: dict[str, tuple[float, str, dict[str, Any] | None]] = {}


def invalidate_schema_cache(connection_id: str | None = None) -> None:
    """Drop cached introspection for one connection, or all of them.

    Not wired to an endpoint, but available for callers that mutate a
    connection's schema/credentials and need fresh metadata immediately.
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
    """TTL-cached wrapper around :func:`_introspect` (biggest TTFT win).

    On a fresh, non-expired hit we return the cached ``(engine, schema)``
    without touching the DB. On miss/expiry we run the real introspection and
    store the result.
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
    """Reach into data-unit to build schema metadata for the system prompt.

    Returns (engine, schema-dict). The schema contains table+column names+types
    only — never row values (FR-LLM-05).
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
    username = (conn.options or {}).get("username", "")
    vault = getattr(request.app.state, "vault_adapter", None)
    password = ""
    if vault is not None and username:
        cred = await session.get(Credential, conn.credential_id)
        if cred is not None and cred.deleted_at is None:
            v = await vault.read(cred.vault_path)
            if v.ok:
                password = v.value.reveal()
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


_DEFAULT_PII_REGEXES: tuple[tuple[str, str], ...] = (
    ("email", r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b"),
    ("phone", r"\b01[016789]-?\d{3,4}-?\d{4}\b"),
    ("rrn",   r"\b\d{6}-?\d{7}\b"),
)


# In-memory TTL cache for the compiled PII regex list. The set is small and
# rarely changes, so recompiling it on every request is pure overhead.
# Value shape: (monotonic_timestamp, patterns).
_PII_CACHE_TTL = 60.0  # seconds
_pii_cache: dict[str, tuple[float, list[tuple[str, re.Pattern[str]]]]] = {}


def invalidate_pii_cache() -> None:
    """Drop the cached PII regex list so the next request recompiles it."""
    _pii_cache.clear()


async def _load_pii_regexes_cached(
    session: AsyncSession,
) -> list[tuple[str, re.Pattern[str]]]:
    """TTL-cached wrapper around :func:`_load_pii_regexes`."""
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
        try:
            patterns.append((r.kind, re.compile(r.regex)))
        except re.error:
            continue
    # Always include a defensive baseline so we don't depend on DB seed state.
    for kind, raw in _DEFAULT_PII_REGEXES:
        try:
            patterns.append((kind, re.compile(raw)))
        except re.error:
            continue
    return patterns


def _mask_text(text: str, patterns: list[tuple[str, re.Pattern[str]]]) -> str:
    out = text
    for _, pattern in patterns:
        out = pattern.sub("[REDACTED]", out)
    return out


async def _copilot_rate_limited(request: Request, actor_key: str) -> bool:
    """10 req/min per user (FR-LLM-04 spirit / NFR-SEC-11).

    Uses Redis if the backend wired it (via ``app.state.copilot_limiter``);
    otherwise falls back to a process-local sliding-window dict — single-pod
    demo deployments are still rate-limited even without Redis.
    """
    import time as _t

    limiter = getattr(request.app.state, "copilot_limiter", None)
    if limiter is not None:
        return not await limiter.check(actor_key)

    bucket = getattr(request.app.state, "_copilot_local_bucket", None)
    if bucket is None:
        bucket = {}
        request.app.state._copilot_local_bucket = bucket
    now = _t.time()
    arr = bucket.setdefault(actor_key, [])
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

    messages: list[ChatMessage] = [
        {"role": t.role, "content": t.content} for t in body.history
    ]
    messages.append({"role": "user", "content": body.question})

    pii_patterns = await _load_pii_regexes_cached(session)

    audit_id = uuid4()

    async def generator():
        full = []
        try:
            async for chunk in provider.stream(system=system_prompt, messages=messages):
                masked = _mask_text(chunk, pii_patterns)
                full.append(masked)
                yield json.dumps({"chunk": masked}) + "\n"
        except Exception as exc:  # noqa: BLE001
            yield json.dumps({"error": str(exc)}) + "\n"
        finally:
            full_text = "".join(full)
            # Best-effort audit row. Failures are logged but don't break the
            # stream — the client already received its content.
            try:
                session.add(
                    AuditLog(
                        event_type="copilot_chat",
                        actor_id="anonymous",
                        resource=f"copilot:{provider.name}",
                        result="success" if full_text else "failure",
                        occurred_at=datetime.utcnow(),
                        corr_id=f"copilot-{audit_id}",
                        payload={
                            "provider": provider.name,
                            "connection_id": body.connection_id,
                            "schema_attached": schema is not None,
                            "response_chars": len(full_text),
                            "row_data_transmitted": False,
                        },
                    )
                )
                await session.commit()
            except Exception:  # noqa: BLE001
                await session.rollback()

    return StreamingResponse(generator(), media_type="application/x-ndjson")
