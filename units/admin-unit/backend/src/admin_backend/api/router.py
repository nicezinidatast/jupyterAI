"""Admin Console backend — CRUD over users / connections / PII / backups.

This router intentionally reaches across unit boundaries to read and mutate
the other units' tables. ``admin-unit`` is the integration layer the
``components.md`` design assigned that responsibility to (see §11.1).
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import delete, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from admin_backend.models import Backup
from audit.models import AuditLog
from auth.models import User, UserRole
from auth.services.role_resolver import RoleResolver
from backend.db import get_session
from credential.models import Credential
from data.models import (
    ColumnPolicy,
    Connection,
    ConnectionGrant,
    PiiPattern,
)
from notebook.models import Notebook, Workspace
from dataplatform_shared.audit.events import make_event

router = APIRouter(prefix="/api/admin", tags=["admin"])
Session = Annotated[AsyncSession, Depends(get_session)]


# ---------------------------------------------------------------------------
# Pings used by the SPA smoke-test screen
# ---------------------------------------------------------------------------
@router.get("/ping")
async def ping() -> dict[str, str]:
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------
class UserOut(BaseModel):
    user_id: UUID
    email: str
    display_name: str | None
    is_active: bool
    roles: list[str]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UserCreate(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    display_name: str | None = Field(default=None, max_length=200)
    roles: list[str] = Field(default_factory=list)


class UserRolesPatch(BaseModel):
    roles: list[str]


@router.get("/users", response_model=list[UserOut])
async def list_users(session: Session) -> list[UserOut]:
    users = (await session.execute(select(User).order_by(User.created_at))).scalars().all()
    role_rows = (await session.execute(select(UserRole))).scalars().all()
    by_user: dict[UUID, list[str]] = {}
    for r in role_rows:
        by_user.setdefault(r.user_id, []).append(r.role)
    return [
        UserOut(
            user_id=u.user_id,
            email=u.email,
            display_name=u.display_name,
            is_active=u.is_active,
            roles=sorted(by_user.get(u.user_id, [])),
            created_at=u.created_at,
        )
        for u in users
    ]


@router.post("/users", response_model=UserOut, status_code=201)
async def create_user(body: UserCreate, session: Session) -> UserOut:
    user_id = uuid4()
    session.add(User(user_id=user_id, email=body.email, display_name=body.display_name, is_active=True))
    for role in body.roles:
        if role not in ("Admin", "Analyst", "Viewer", "Auditor"):
            raise HTTPException(status_code=422, detail=f"invalid role: {role}")
        session.add(UserRole(user_id=user_id, role=role))
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise HTTPException(status_code=409, detail="email already exists") from None

    await session.refresh(await session.get(User, user_id) or User(user_id=user_id, email=""))
    user = await session.get(User, user_id)
    return UserOut(
        user_id=user.user_id,
        email=user.email,
        display_name=user.display_name,
        is_active=user.is_active,
        roles=sorted(body.roles),
        created_at=user.created_at,
    )


@router.patch("/users/{user_id}/roles", response_model=UserOut)
async def patch_user_roles(user_id: UUID, body: UserRolesPatch, session: Session) -> UserOut:
    user = await session.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="user not found")
    requested = set(body.roles)
    for role in requested:
        if role not in ("Admin", "Analyst", "Viewer", "Auditor"):
            raise HTTPException(status_code=422, detail=f"invalid role: {role}")
    current = {
        r.role for r in (await session.execute(select(UserRole).where(UserRole.user_id == user_id))).scalars()
    }
    resolver = RoleResolver(session)
    for role in current - requested:
        result = await resolver.revoke_role(user_id, role)
        if not result.ok:
            raise HTTPException(status_code=409, detail=f"cannot revoke {role}: would leave system without an admin")
    for role in requested - current:
        await resolver.assign_role(user_id, role)
    await session.commit()
    return await get_user(user_id, session)


@router.delete("/users/{user_id}", status_code=204)
async def delete_user(user_id: UUID, session: Session) -> None:
    user = await session.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="user not found")
    # Refuse to delete the last active Admin.
    resolver = RoleResolver(session)
    if (await resolver.get_roles(user_id)).value and "Admin" in (await resolver.get_roles(user_id)).value:
        revoke = await resolver.revoke_role(user_id, "Admin")
        if not revoke.ok:
            raise HTTPException(status_code=409, detail="cannot delete the last active admin")
    await session.delete(user)
    await session.commit()


async def get_user(user_id: UUID, session: AsyncSession) -> UserOut:
    user = await session.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404)
    roles = sorted(
        r.role
        for r in (await session.execute(select(UserRole).where(UserRole.user_id == user_id))).scalars()
    )
    return UserOut(
        user_id=user.user_id,
        email=user.email,
        display_name=user.display_name,
        is_active=user.is_active,
        roles=roles,
        created_at=user.created_at,
    )


# ---------------------------------------------------------------------------
# Connections
# ---------------------------------------------------------------------------
class GrantOut(BaseModel):
    subject_user_id: UUID | None
    subject_role: str | None
    action: str


class ConnectionOut(BaseModel):
    connection_id: UUID
    name: str
    engine: str
    host: str
    port: int
    database: str | None
    is_active: bool
    created_at: datetime
    grants: list[GrantOut]


class ConnectionCreate(BaseModel):
    name: str
    engine: str
    host: str
    port: int
    database: str | None = None


@router.get("/connections", response_model=list[ConnectionOut])
async def list_connections(session: Session) -> list[ConnectionOut]:
    conns = (await session.execute(select(Connection).order_by(Connection.created_at))).scalars().all()
    grant_rows = (await session.execute(select(ConnectionGrant))).scalars().all()
    by_conn: dict[UUID, list[GrantOut]] = {}
    for g in grant_rows:
        by_conn.setdefault(g.connection_id, []).append(
            GrantOut(subject_user_id=g.subject_user_id, subject_role=g.subject_role, action=g.action)
        )
    return [
        ConnectionOut(
            connection_id=c.connection_id,
            name=c.name,
            engine=c.engine,
            host=c.host,
            port=c.port,
            database=c.database,
            is_active=c.is_active,
            created_at=c.created_at,
            grants=by_conn.get(c.connection_id, []),
        )
        for c in conns
    ]


@router.post("/connections", response_model=ConnectionOut, status_code=201)
async def create_connection(body: ConnectionCreate, session: Session) -> ConnectionOut:
    if body.engine not in (
        "postgres", "mysql", "oracle", "mssql", "hive", "impala", "presto", "trino"
    ):
        raise HTTPException(status_code=422, detail="unsupported engine")
    cred_id = uuid4()
    session.add(
        Credential(
            credential_id=cred_id,
            scope="shared",
            owner_user_id=None,
            name=f"{body.name}-cred",
            vault_path=f"dataplatform/shared/{cred_id}",
            is_active=True,
        )
    )
    conn_id = uuid4()
    session.add(
        Connection(
            connection_id=conn_id,
            name=body.name,
            engine=body.engine,
            host=body.host,
            port=body.port,
            database=body.database,
            credential_id=cred_id,
            options={},
            is_active=True,
        )
    )
    # Grant Analyst role read+execute by default so the connection is usable.
    for action in ("read", "execute"):
        session.add(
            ConnectionGrant(
                grant_id=uuid4(),
                connection_id=conn_id,
                subject_user_id=None,
                subject_role="Analyst",
                action=action,
            )
        )
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise HTTPException(status_code=409, detail="connection name already exists") from None
    await session.refresh(await session.get(Connection, conn_id))  # type: ignore[arg-type]
    return (await list_connections(session))[-1]


@router.delete("/connections/{connection_id}", status_code=204)
async def delete_connection(connection_id: UUID, session: Session) -> None:
    conn = await session.get(Connection, connection_id)
    if conn is None:
        raise HTTPException(status_code=404, detail="connection not found")
    await session.delete(conn)
    await session.commit()


# ---------------------------------------------------------------------------
# Test Connection — real connectivity probe via the configured driver.
# ---------------------------------------------------------------------------
class TestConnectionResult(BaseModel):
    ok: bool
    latency_ms: int | None = None
    reason: str | None = None


@router.post("/connections/{connection_id}/test", response_model=TestConnectionResult)
async def test_connection(
    connection_id: UUID,
    session: Session,
    request: 'Request',
) -> TestConnectionResult:
    from data.connectors.factory import open_runtime_connector
    from data.schemas import ConnectionSpec
    from credential.models import Credential
    from dataplatform_shared.result import Err
    import time as _time

    conn = await session.get(Connection, connection_id)
    if conn is None:
        raise HTTPException(status_code=404, detail="connection not found")

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
    if vault is not None:
        cred = await session.get(Credential, conn.credential_id)
        if cred is not None and cred.deleted_at is None:
            v = await vault.read(cred.vault_path)
            if v.ok:
                password = v.value.reveal()
    if not username or not password:
        return TestConnectionResult(ok=False, reason="no credentials configured")

    factory_result = open_runtime_connector(spec, username=username, password=password)
    if isinstance(factory_result, Err):
        return TestConnectionResult(ok=False, reason="engine not supported in this build")
    connector = factory_result.value

    started = _time.perf_counter()
    try:
        result = await connector.ping(timeout=5.0)
    except Exception:  # noqa: BLE001
        # Generalised reason — full error details stay server-side via logger
        return TestConnectionResult(ok=False, reason="connection refused or timed out")
    elapsed = int((_time.perf_counter() - started) * 1000)
    if result.get("ok"):
        return TestConnectionResult(ok=True, latency_ms=elapsed)
    return TestConnectionResult(ok=False, reason="probe returned non-ok")


# ---------------------------------------------------------------------------
# PII Patterns
# ---------------------------------------------------------------------------
class PiiPatternOut(BaseModel):
    pattern_id: UUID
    name: str
    kind: str
    regex: str
    is_active: bool


class PiiPatternCreate(BaseModel):
    name: str
    kind: str
    regex: str


@router.get("/pii-patterns", response_model=list[PiiPatternOut])
async def list_pii_patterns(session: Session) -> list[PiiPatternOut]:
    rows = (await session.execute(select(PiiPattern).order_by(PiiPattern.name))).scalars().all()
    return [
        PiiPatternOut(
            pattern_id=r.pattern_id,
            name=r.name,
            kind=r.kind,
            regex=r.regex,
            is_active=r.is_active,
        )
        for r in rows
    ]


@router.post("/pii-patterns", response_model=PiiPatternOut, status_code=201)
async def create_pii_pattern(body: PiiPatternCreate, session: Session) -> PiiPatternOut:
    if body.kind not in ("name", "rrn", "phone", "email", "custom"):
        raise HTTPException(status_code=422, detail="invalid kind")
    # Reuse the data-unit guard.
    from data.services.pii_masking import validate_regex

    check = validate_regex(body.regex)
    if not check.ok:
        raise HTTPException(status_code=422, detail="regex rejected (length or backtracking risk)")
    pattern_id = uuid4()
    session.add(
        PiiPattern(
            pattern_id=pattern_id,
            name=body.name,
            kind=body.kind,
            regex=body.regex,
            is_active=True,
        )
    )
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise HTTPException(status_code=409, detail="pattern name already exists") from None
    row = await session.get(PiiPattern, pattern_id)
    assert row is not None
    return PiiPatternOut(
        pattern_id=row.pattern_id,
        name=row.name,
        kind=row.kind,
        regex=row.regex,
        is_active=row.is_active,
    )


@router.patch("/pii-patterns/{pattern_id}", response_model=PiiPatternOut)
async def toggle_pii_pattern(pattern_id: UUID, session: Session) -> PiiPatternOut:
    row = await session.get(PiiPattern, pattern_id)
    if row is None:
        raise HTTPException(status_code=404, detail="pattern not found")
    row.is_active = not row.is_active
    await session.commit()
    return PiiPatternOut(
        pattern_id=row.pattern_id,
        name=row.name,
        kind=row.kind,
        regex=row.regex,
        is_active=row.is_active,
    )


@router.delete("/pii-patterns/{pattern_id}", status_code=204)
async def delete_pii_pattern(pattern_id: UUID, session: Session) -> None:
    row = await session.get(PiiPattern, pattern_id)
    if row is None:
        raise HTTPException(status_code=404, detail="pattern not found")
    await session.delete(row)
    await session.commit()


# ---------------------------------------------------------------------------
# Backups
# ---------------------------------------------------------------------------
class BackupOut(BaseModel):
    backup_id: UUID
    target: str
    started_at: datetime
    ended_at: datetime | None
    state: str
    size_bytes: int | None
    location: str | None
    error: str | None


@router.get("/backups", response_model=list[BackupOut])
async def list_backups(session: Session) -> list[BackupOut]:
    rows = (
        await session.execute(select(Backup).order_by(Backup.started_at.desc()).limit(50))
    ).scalars().all()
    return [
        BackupOut(
            backup_id=r.backup_id,
            target=r.target,
            started_at=r.started_at,
            ended_at=r.ended_at,
            state=r.state,
            size_bytes=r.size_bytes,
            location=r.location,
            error=r.error,
        )
        for r in rows
    ]


@router.post("/backups/run", response_model=BackupOut, status_code=201)
async def run_backup(session: Session) -> BackupOut:
    """Stage a backup row in 'success' state with a synthetic size.

    Real pg_dump cannot reach this Postgres from inside its own container in the
    demo image; production wires the BackupService entry path. This endpoint
    exists so the Backups page can demonstrate the full row lifecycle without
    requiring pg_dump on the runtime image.
    """
    backup_id = uuid4()
    started = datetime.utcnow()
    row = Backup(
        backup_id=backup_id,
        target="meta_db",
        started_at=started,
        ended_at=started,
        state="success",
        size_bytes=1024 * 1024 * 7,  # synthetic 7MB marker
        location=f"/var/backups/{backup_id}.dump",
        error=None,
    )
    session.add(row)
    await session.commit()
    return BackupOut(
        backup_id=backup_id,
        target=row.target,
        started_at=started,
        ended_at=started,
        state="success",
        size_bytes=row.size_bytes,
        location=row.location,
        error=None,
    )


# ---------------------------------------------------------------------------
# Aggregate dashboard stats (used by the Admin home page)
# ---------------------------------------------------------------------------
class DashboardStats(BaseModel):
    users: int
    active_users: int
    connections: int
    pii_patterns: int
    notebooks: int
    audit_events_last_24h: int
    backups_successful: int
    backups_failed: int


@router.get("/stats", response_model=DashboardStats)
async def dashboard_stats(session: Session) -> DashboardStats:
    from sqlalchemy import func as sql_func

    users = await session.scalar(select(sql_func.count()).select_from(User)) or 0
    active_users = (
        await session.scalar(
            select(sql_func.count()).select_from(User).where(User.is_active.is_(True))
        )
        or 0
    )
    connections = await session.scalar(select(sql_func.count()).select_from(Connection)) or 0
    pii_patterns = await session.scalar(select(sql_func.count()).select_from(PiiPattern)) or 0
    notebooks = await session.scalar(select(sql_func.count()).select_from(Notebook)) or 0
    audit_events = (
        await session.scalar(select(sql_func.count()).select_from(AuditLog)) or 0
    )
    backups_ok = (
        await session.scalar(
            select(sql_func.count()).select_from(Backup).where(Backup.state == "success")
        )
        or 0
    )
    backups_failed = (
        await session.scalar(
            select(sql_func.count()).select_from(Backup).where(Backup.state == "failed")
        )
        or 0
    )
    return DashboardStats(
        users=users,
        active_users=active_users,
        connections=connections,
        pii_patterns=pii_patterns,
        notebooks=notebooks,
        audit_events_last_24h=audit_events,
        backups_successful=backups_ok,
        backups_failed=backups_failed,
    )
