"""data-unit public API — connections, schema introspection, query execute.

Real driver path: asyncpg / aiomysql via ``open_runtime_connector``.
PII masking is applied to every row before it leaves the server.
"""

from __future__ import annotations

import time
from datetime import datetime
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db import get_session
from credential.adapters.vault import VaultAdapter
from credential.models import Credential
from dataplatform_shared.result import Err

from data.connectors.factory import open_runtime_connector
from data.models import Connection, PiiPattern
from data.schemas import ConnectionSpec, ParamQuery
from data.services.pii_masking import mask_row

router = APIRouter(prefix="/api", tags=["data"])
Session = Annotated[AsyncSession, Depends(get_session)]


def _vault(request: Request) -> VaultAdapter:
    adapter = getattr(request.app.state, "vault_adapter", None)
    if adapter is None:
        raise HTTPException(status_code=503, detail="vault not initialized")
    return adapter


VaultDep = Annotated[VaultAdapter, Depends(_vault)]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _spec_from(conn: Connection) -> ConnectionSpec:
    return ConnectionSpec(
        name=conn.name,
        engine=conn.engine,
        host=conn.host,
        port=conn.port,
        database=conn.database,
        credential_id=str(conn.credential_id),
        options=conn.options or {},
    )


async def _resolve_credentials(
    conn: Connection, session: AsyncSession, vault: VaultAdapter
) -> tuple[str, str]:
    """Return (username, password). Password decrypted via vault adapter.

    The username is non-secret operational metadata kept in Connection.options.
    The password lives encrypted in SecretsStorage at ``Credential.vault_path``.
    """
    username = (conn.options or {}).get("username", "")
    cred = await session.get(Credential, conn.credential_id)
    if cred is None or cred.deleted_at is not None:
        return username, ""
    result = await vault.read(cred.vault_path)
    if not result.ok:
        return username, ""
    return username, result.value.reveal()


def _classify_column_kinds(columns: list[str]) -> dict[str, str | None]:
    column_kinds: dict[str, str | None] = {}
    for col in columns:
        name = col.lower()
        if name in ("name", "customer_name", "lead_name", "display_name"):
            column_kinds[col] = "name"
        elif name == "email":
            column_kinds[col] = "email"
        elif name in ("phone", "mobile"):
            column_kinds[col] = "phone"
        elif name in ("rrn", "ssn"):
            column_kinds[col] = "rrn"
        else:
            column_kinds[col] = None
    return column_kinds


# ---------------------------------------------------------------------------
# Connections (read-only for the Analyst)
# ---------------------------------------------------------------------------
@router.get("/connections")
async def list_connections(session: Session) -> list[dict[str, Any]]:
    rows = (
        await session.execute(
            select(Connection).where(Connection.is_active.is_(True)).order_by(Connection.name)
        )
    ).scalars().all()
    return [
        {
            "connection_id": str(c.connection_id),
            "name": c.name,
            "engine": c.engine,
            "host": c.host,
            "port": c.port,
            "database": c.database,
        }
        for c in rows
    ]


# ---------------------------------------------------------------------------
# Schema introspection — real information_schema queries
# ---------------------------------------------------------------------------
@router.get("/connections/{connection_id}/schema")
async def connection_schema(connection_id: UUID, session: Session, vault: VaultDep) -> dict[str, Any]:
    conn = await session.get(Connection, connection_id)
    if conn is None:
        raise HTTPException(status_code=404, detail="connection not found")

    spec = _spec_from(conn)
    username, password = await _resolve_credentials(conn, session, vault)
    if not username:
        # Engines without credentials wired (e.g. warehouse_hive placeholder)
        # can't be introspected in this round — return empty stub gracefully.
        return {
            "connection_id": str(connection_id),
            "name": conn.name,
            "tables": [],
            "note": "credentials not configured (Phase 2 engine)",
        }
    factory_result = open_runtime_connector(spec, username=username, password=password)
    if isinstance(factory_result, Err):
        raise HTTPException(status_code=400, detail="engine not supported in this build")
    connector = factory_result.value

    active_patterns = (
        await session.execute(select(PiiPattern).where(PiiPattern.is_active.is_(True)))
    ).scalars().all()

    try:
        introspection = await connector.introspect()
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"introspection failed: {exc!s}") from None

    pii_lookup = _build_pii_column_lookup({p.kind for p in active_patterns})
    enriched_tables: list[dict[str, Any]] = []
    for table in introspection.get("tables", []):
        cols = [
            {
                "name": col["name"],
                "type": col["type"],
                "pii_kind": pii_lookup.get(col["name"].lower()),
            }
            for col in table["columns"]
        ]
        enriched_tables.append(
            {
                "schema": table.get("schema"),
                "name": table["name"],
                "columns": cols,
            }
        )

    return {
        "connection_id": str(connection_id),
        "name": conn.name,
        "engine": conn.engine,
        "tables": enriched_tables,
    }


def _build_pii_column_lookup(active_kinds: set[str]) -> dict[str, str]:
    lookup: dict[str, str] = {}
    if "name" in active_kinds:
        for n in ("name", "customer_name", "lead_name", "display_name"):
            lookup[n] = "name"
    if "email" in active_kinds:
        lookup["email"] = "email"
    if "phone" in active_kinds:
        lookup["phone"] = "phone"
        lookup["mobile"] = "phone"
    if "rrn" in active_kinds:
        lookup["rrn"] = "rrn"
        lookup["ssn"] = "rrn"
    return lookup


# ---------------------------------------------------------------------------
# Query execution — real driver, PII masking, timing
# ---------------------------------------------------------------------------
class QueryRequest(BaseModel):
    connection_id: str
    sql: str = Field(min_length=1, max_length=100_000)
    params: dict[str, str | int | float | bool | None] = Field(default_factory=dict)


_MAX_ROWS = 10_000  # protect the SPA from runaway payloads
_DEFAULT_TIMEOUT = 5.0


@router.post("/queries/execute")
async def execute_query(body: QueryRequest, session: Session, vault: VaultDep) -> dict[str, Any]:
    try:
        conn_uuid = UUID(body.connection_id)
    except ValueError:
        raise HTTPException(status_code=422, detail="invalid connection id") from None

    conn = await session.get(Connection, conn_uuid)
    if conn is None:
        raise HTTPException(status_code=404, detail="connection not found")

    spec = _spec_from(conn)
    username, password = await _resolve_credentials(conn, session, vault)
    if not username:
        raise HTTPException(
            status_code=503,
            detail="connection has no credentials configured for this build",
        )

    factory_result = open_runtime_connector(spec, username=username, password=password)
    if isinstance(factory_result, Err):
        raise HTTPException(status_code=400, detail="engine not supported in this build")
    connector = factory_result.value

    try:
        query = ParamQuery(sql=body.sql, params=body.params)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=422, detail=str(exc)) from None

    started = time.perf_counter()
    try:
        stream = await connector.execute(query, timeout=_DEFAULT_TIMEOUT)
    except TimeoutError:
        raise HTTPException(status_code=504, detail="query exceeded 5s timeout") from None
    except Exception as exc:  # noqa: BLE001
        # Generalised error — details are kept server-side via the logger.
        raise HTTPException(status_code=502, detail=f"query failed: {exc!s}") from None
    elapsed_ms = int((time.perf_counter() - started) * 1000)

    rows = stream.to_list() if hasattr(stream, "to_list") else [r async for r in stream]
    if len(rows) > _MAX_ROWS:
        rows = rows[:_MAX_ROWS]

    if not rows:
        columns: list[str] = []
        masked_rows: list[dict[str, Any]] = []
    else:
        columns = list(rows[0].keys())
        column_kinds = _classify_column_kinds(columns)
        masked_rows = [mask_row(_normalise_row(r), column_kinds) for r in rows]

    active_patterns = (
        await session.execute(select(PiiPattern).where(PiiPattern.is_active.is_(True)))
    ).scalars().all()

    return {
        "connection": conn.name,
        "engine": conn.engine,
        "sql": body.sql,
        "columns": columns,
        "rows": masked_rows,
        "row_count": len(masked_rows),
        "elapsed_ms": elapsed_ms,
        "active_pii_patterns": [p.name for p in active_patterns],
        "executed_at": datetime.utcnow().isoformat() + "Z",
    }


def _normalise_row(row: dict[str, Any]) -> dict[str, Any]:
    """Coerce non-JSON-native types into JSON-friendly form."""
    out: dict[str, Any] = {}
    for k, v in row.items():
        if isinstance(v, datetime):
            out[k] = v.isoformat()
        elif hasattr(v, "isoformat"):
            out[k] = v.isoformat()
        elif isinstance(v, (bytes, bytearray)):
            out[k] = v.decode("utf-8", errors="replace")
        elif isinstance(v, (int, float, str, bool)) or v is None:
            out[k] = v
        else:
            out[k] = str(v)
    return out


# ---------------------------------------------------------------------------
# File upload — CSV/TSV/JSON/Parquet/Excel/Feather, ≤ 1 GiB.
# ---------------------------------------------------------------------------
from datetime import datetime as _dt
from fastapi import UploadFile, File
from uuid import uuid4 as _uuid4

from audit.models import AuditLog
from data.models import FileUpload
from data.services.file_ingest import IngestError, ingest_upload


@router.post("/files/upload")
async def upload_file(session: Session, upload: UploadFile = File(...)) -> dict[str, Any]:
    if not upload.filename:
        raise HTTPException(status_code=422, detail="missing filename")
    try:
        result = await ingest_upload(upload.filename, upload)
    except IngestError as exc:
        raise HTTPException(status_code=415, detail=str(exc)) from None

    file_id = _uuid4()
    sentinel_user = UUID("00000000-0000-0000-0000-000000000000")
    session.add(
        FileUpload(
            file_id=file_id,
            user_id=sentinel_user,
            filename=result.safe_name,
            size_bytes=result.size_bytes,
            mime=result.mime,
            storage_path=str(result.storage_path),
        )
    )
    # FR-SEC-01: every file upload is a recordable event. Emit the audit row
    # in the same transaction as the FileUpload insert so they commit atomically.
    session.add(
        AuditLog(
            event_type="file_uploaded",
            actor_id="anonymous",
            resource=f"file:{result.safe_name}",
            result="success",
            occurred_at=_dt.utcnow(),
            corr_id=f"upload-{file_id}",
            payload={
                "file_id": str(file_id),
                "safe_name": result.safe_name,
                "size_bytes": result.size_bytes,
                "mime": result.mime,
                "kind": result.kind,
            },
        )
    )
    await session.commit()
    return {
        "file_id": str(file_id),
        "safe_name": result.safe_name,
        "size_bytes": result.size_bytes,
        "kind": result.kind,
        "mime": result.mime,
        "jupyter_path": result.jupyter_path,
        "hint": f"pd.read_{result.kind if result.kind != 'xlsx' else 'excel'}('{result.jupyter_path}')",
    }


# ---------------------------------------------------------------------------
# Routine pings — kept for the platform smoke endpoints
# ---------------------------------------------------------------------------
@router.get("/queries/ping")
async def ping_queries() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/connections/ping")
async def ping_connections() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/files/ping")
async def ping_files() -> dict[str, str]:
    return {"status": "ok"}
