"""어드민 콘솔 백엔드 — 사용자·커넥션·PII 패턴·백업 CRUD 라우터.

설계 경계 교차(cross-unit access):
이 라우터는 의도적으로 여러 유닛(auth, data, credential, notebook, audit)의
테이블을 직접 읽고 변경한다. admin-unit이 통합 계층(integration layer) 역할을
담당하도록 설계됐기 때문이다(설계 근거: components.md §11.1).

보안 전제:
- 이 라우터의 모든 엔드포인트는 상위 게이트웨이(gateway-unit)에서
  어드민 역할 검사를 마친 요청만 도달한다고 가정한다.
- 라우터 내부에서 추가 역할 검증을 하지 않는 이유는 단일 책임 원칙에 따라
  인증·인가를 게이트웨이에 집중하기 위해서다.
"""

from __future__ import annotations

from datetime import datetime, timedelta
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
from auth.services.password import hash_password
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
# Session 타입 별칭 — FastAPI Depends를 통해 요청마다 새 세션을 주입받는다.
Session = Annotated[AsyncSession, Depends(get_session)]


# ---------------------------------------------------------------------------
# Pings used by the SPA smoke-test screen
# ---------------------------------------------------------------------------
@router.get("/ping")
async def ping() -> dict[str, str]:
    """SPA 스모크 테스트 화면에서 백엔드 생존 여부를 확인하는 헬스체크 엔드포인트."""
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------
class UserOut(BaseModel):
    """사용자 정보 응답 스키마.

    password_hash 등 민감 필드는 의도적으로 제외한다.
    roles는 UserRole 행들을 집계해 정렬된 리스트로 제공한다.
    """

    user_id: UUID
    email: str
    display_name: str | None
    is_active: bool
    roles: list[str]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UserCreate(BaseModel):
    """사용자 생성 요청 스키마.

    email은 최소 3자·최대 320자(RFC 5321 최대 길이) 제약을 둔다. 이 값은 사실상
    로그인 아이디로 쓰인다(``login_router``가 동일 컬럼 ``User.email``을 조회한다).
    roles는 빈 리스트를 기본값으로 허용 — 역할 없이 생성 후 별도 PATCH로 부여 가능.

    password는 로컬 비밀번호 로그인용 초기 비밀번호다. 선택값이지만, 주지 않으면
    생성된 사용자는 ``password_hash``가 없어 ``/api/auth/login``으로 로그인할 수 없다
    (그 경우 OIDC 전용 사용자만 의미가 있다). 제약(min 4 / max 72)은 signup의
    ``SignupBody``와 동일하게 맞춰, 어느 경로로 만들든 같은 규칙으로 검증되게 한다.
    """

    email: str = Field(min_length=3, max_length=320)
    display_name: str | None = Field(default=None, max_length=200)
    roles: list[str] = Field(default_factory=list)
    password: str | None = Field(default=None, min_length=4, max_length=72)


class UserRolesPatch(BaseModel):
    """역할 교체 요청 스키마 — 현재 역할 집합을 이 목록으로 완전히 대체한다."""

    roles: list[str]


class UserPasswordReset(BaseModel):
    """관리자 비밀번호 초기화 요청 스키마.

    제약(min 4 / max 72)은 signup·본인 변경과 동일하게 맞춘다.
    현재 비밀번호는 요구하지 않는다 — 관리자 권한으로 분실 계정을 복구하는
    경로이기 때문이다(본인 변경과 달리 '현재 비밀번호 확인'이 없다).
    """

    password: str = Field(min_length=4, max_length=72)


@router.get("/users", response_model=list[UserOut])
async def list_users(session: Session) -> list[UserOut]:
    """전체 사용자 목록과 각 사용자의 역할을 반환한다.

    N+1 쿼리를 피하기 위해 User와 UserRole을 각각 한 번씩 조회한 뒤
    Python 딕셔너리로 조인한다.
    """
    users = (await session.execute(select(User).order_by(User.created_at))).scalars().all()
    role_rows = (await session.execute(select(UserRole))).scalars().all()
    # user_id → 역할 이름 리스트 매핑: N+1을 피하는 인메모리 조인.
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
    """사용자를 생성하고, 요청한 역할을 UserRole 테이블에 삽입한다.

    역할 유효성은 허용 목록(Admin, Analyst, Viewer, Auditor)으로 사전 검증하며,
    알 수 없는 역할이 하나라도 있으면 422를 반환한다.
    email 중복 시 DB IntegrityError를 잡아 409로 변환한다.

    로그인이 가능하도록 두 가지를 맞춘다:
    - 식별자 정규화: ``login_router``는 입력 아이디를 ``strip().lower()``로 정규화한
      뒤 ``User.email``을 조회한다. 여기서도 동일하게 정규화해 저장하지 않으면, 대소문자나
      앞뒤 공백만 달라도 비밀번호가 맞아도 로그인 조회에 실패한다.
    - 비밀번호 해시: ``body.password``가 있으면 signup과 똑같은 bcrypt 해시로 저장한다.
      없으면 ``password_hash``는 None으로 남고, 그 사용자는 로컬 비밀번호 로그인을 할 수
      없다(OIDC로만 인증 가능). 평문은 절대 저장하지 않는다.
    """
    user_id = uuid4()
    # 로그인 조회 키와 어긋나지 않도록 login_router와 동일한 규칙으로 정규화한다.
    identifier = body.email.strip().lower()
    password_hash = hash_password(body.password) if body.password else None
    session.add(
        User(
            user_id=user_id,
            email=identifier,
            display_name=body.display_name,
            password_hash=password_hash,
            is_active=True,
        )
    )
    for role in body.roles:
        if role not in ("Admin", "Analyst", "Viewer", "Auditor"):
            raise HTTPException(status_code=422, detail=f"invalid role: {role}")
        session.add(UserRole(user_id=user_id, role=role))
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        # email UNIQUE 제약 위반 — 클라이언트에게 충돌 사실만 알린다.
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
    """사용자의 역할 집합을 요청 목록으로 완전히 교체한다.

    차분(diff) 방식으로 동작한다:
    - (현재 역할) - (요청 역할) → revoke_role 호출.
    - (요청 역할) - (현재 역할) → assign_role 호출.

    RoleResolver.revoke_role은 마지막 Admin을 제거하려 하면 Err를 반환하므로,
    시스템에 Admin이 항상 한 명 이상 남도록 보장된다.
    """
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
    # 제거할 역할: revoke_role이 마지막 Admin 제거를 거부하면 409 반환.
    for role in current - requested:
        result = await resolver.revoke_role(user_id, role)
        if not result.ok:
            raise HTTPException(status_code=409, detail=f"cannot revoke {role}: would leave system without an admin")
    # 추가할 역할: assign_role은 중복 삽입 없이 안전하게 처리된다.
    for role in requested - current:
        await resolver.assign_role(user_id, role)
    await session.commit()
    return await get_user(user_id, session)


@router.put("/users/{user_id}/password", status_code=200)
async def reset_user_password(
    user_id: UUID, body: UserPasswordReset, session: Session
) -> dict[str, bool]:
    """관리자가 특정 사용자의 비밀번호를 새 값으로 초기화한다.

    비밀번호를 분실했거나 admin이 만든 직후의 계정을 복구하는 경로다. signup·본인
    변경과 같은 bcrypt 해시로 저장하므로, 초기화 직후 그 비밀번호로 바로 로그인된다.
    평문은 저장하지 않으며, 기존 비밀번호 확인은 요구하지 않는다(관리자 권한 전제).

    보안 전제는 이 라우터의 다른 엔드포인트와 같다 — 상위 게이트웨이에서 어드민
    역할 검사를 통과한 요청만 도달한다고 가정한다. 사용자가 없으면 404.
    """
    user = await session.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="user not found")
    user.password_hash = hash_password(body.password)
    await session.commit()
    return {"ok": True}


@router.delete("/users/{user_id}", status_code=204, response_model=None)
async def delete_user(user_id: UUID, session: Session) -> None:
    """사용자를 삭제한다.

    불변식: 마지막 활성 Admin 사용자는 삭제할 수 없다.
    삭제 전 해당 사용자의 Admin 역할을 revoke 시도하고, Err이면 409를 반환한다.
    이렇게 하면 Admin 사용자 수가 0이 되는 상황을 DB 삭제 전에 미리 방지한다.
    """
    user = await session.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="user not found")
    # 마지막 활성 Admin을 삭제하지 못하도록 먼저 Admin 역할 박탈을 시도한다.
    resolver = RoleResolver(session)
    if (await resolver.get_roles(user_id)).value and "Admin" in (await resolver.get_roles(user_id)).value:
        revoke = await resolver.revoke_role(user_id, "Admin")
        if not revoke.ok:
            raise HTTPException(status_code=409, detail="cannot delete the last active admin")
    await session.delete(user)
    await session.commit()


async def get_user(user_id: UUID, session: AsyncSession) -> UserOut:
    """단일 사용자를 조회해 UserOut으로 반환하는 내부 헬퍼.

    라우터 내부에서만 사용하며, 여러 엔드포인트가 공유한다.
    사용자가 없으면 404를 발생시킨다.
    """
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
    """커넥션 접근 권한(grant) 한 건의 응답 스키마.

    subject_user_id와 subject_role 중 하나만 채워진다.
    사용자 지정 권한이면 user_id, 역할 지정 권한이면 role.
    """

    subject_user_id: UUID | None
    subject_role: str | None
    action: str


class ConnectionOut(BaseModel):
    """DB 커넥션 응답 스키마. 자격증명(password)은 포함하지 않는다."""

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
    """커넥션 생성 요청 스키마."""

    name: str
    engine: str
    host: str
    port: int
    database: str | None = None


@router.get("/connections", response_model=list[ConnectionOut])
async def list_connections(session: Session) -> list[ConnectionOut]:
    """전체 커넥션 목록과 각 커넥션의 접근 권한(grants)을 반환한다.

    list_users와 마찬가지로 Connection·ConnectionGrant를 각각 한 번 조회 후
    인메모리 조인으로 N+1 쿼리를 방지한다.
    """
    conns = (await session.execute(select(Connection).order_by(Connection.created_at))).scalars().all()
    grant_rows = (await session.execute(select(ConnectionGrant))).scalars().all()
    # connection_id → GrantOut 리스트 매핑.
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
    """커넥션을 생성하고 기본 접근 권한(Analyst read+execute)을 자동 부여한다.

    생성 시 Credential 행도 함께 생성한다. 실제 자격증명(username/password)은
    Vault에 별도 저장하며, Credential은 Vault 경로만 참조한다.

    기본 권한으로 Analyst 역할에 read·execute를 부여하는 이유:
    데이터 분석가가 바로 커넥션을 사용할 수 있어야 하기 때문이다.
    더 세밀한 권한 조정은 별도 grant API로 수행한다.
    """
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
    # Analyst 역할에 read+execute 기본 권한을 부여해 커넥션 생성 직후 바로 사용 가능하게 한다.
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
    # 방금 생성된 커넥션을 목록 마지막에서 반환한다(생성순 정렬이므로 마지막이 최신).
    return (await list_connections(session))[-1]


@router.delete("/connections/{connection_id}", status_code=204, response_model=None)
async def delete_connection(connection_id: UUID, session: Session) -> None:
    """커넥션을 삭제한다. 연결된 ConnectionGrant는 cascade로 함께 삭제된다."""
    conn = await session.get(Connection, connection_id)
    if conn is None:
        raise HTTPException(status_code=404, detail="connection not found")
    await session.delete(conn)
    await session.commit()


# ---------------------------------------------------------------------------
# Test Connection — real connectivity probe via the configured driver.
# ---------------------------------------------------------------------------
class TestConnectionResult(BaseModel):
    """커넥션 연결 테스트 결과 스키마."""

    ok: bool
    latency_ms: int | None = None
    reason: str | None = None


@router.post("/connections/{connection_id}/test", response_model=TestConnectionResult)
async def test_connection(
    connection_id: UUID,
    session: Session,
    request: 'Request',
) -> TestConnectionResult:
    """저장된 커넥션을 실제로 연결해 응답 지연 시간(latency_ms)을 측정한다.

    동작 흐름:
    1. DB에서 Connection 행을 가져온다.
    2. app.state.vault_adapter를 통해 연결된 Credential의 실제 비밀번호를 읽는다.
    3. 자격증명이 없으면 즉시 실패로 반환한다(fake success 방지).
    4. open_runtime_connector로 드라이버 커넥터를 생성하고 ping을 호출한다.
    5. 오류 세부 내용은 서버 로그에만 남기고, 클라이언트에는 일반 실패 메시지만 반환한다.

    Vault가 app.state에 없으면 자격증명을 읽지 못해 실패로 처리된다.
    이 동작은 의도적이다 — 자격증명 없이 테스트 성공을 가장하면 안 되기 때문이다.
    """
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
    # app.state.vault_adapter가 없으면 자격증명을 읽을 수 없어 테스트가 실패한다.
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
        # 전체 오류 내용은 서버 로그에 남기고, 클라이언트에는 일반적인 실패 이유만 반환한다.
        return TestConnectionResult(ok=False, reason="connection refused or timed out")
    elapsed = int((_time.perf_counter() - started) * 1000)
    if result.get("ok"):
        return TestConnectionResult(ok=True, latency_ms=elapsed)
    return TestConnectionResult(ok=False, reason="probe returned non-ok")


# ---------------------------------------------------------------------------
# PII Patterns
# ---------------------------------------------------------------------------
class PiiPatternOut(BaseModel):
    """PII(개인식별정보) 탐지 패턴 응답 스키마."""

    pattern_id: UUID
    name: str
    kind: str
    regex: str
    is_active: bool


class PiiPatternCreate(BaseModel):
    """PII 패턴 생성 요청 스키마."""

    name: str
    kind: str
    regex: str


@router.get("/pii-patterns", response_model=list[PiiPatternOut])
async def list_pii_patterns(session: Session) -> list[PiiPatternOut]:
    """등록된 PII 탐지 패턴 목록을 이름 순으로 반환한다."""
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
    """PII 탐지 패턴을 생성한다.

    정규식 검증을 data-unit의 validate_regex에 위임한다.
    이 함수는 길이 제한 및 ReDoS(정규식 기반 서비스 거부 공격) 위험이 있는
    패턴을 걸러 낸다. 검증을 직접 구현하지 않고 data-unit을 재사용하는 이유는
    단일 진실 공급원(single source of truth)을 유지하기 위해서다.

    kind는 허용 목록("name", "rrn", "phone", "email", "custom")으로 제한한다.
    """
    if body.kind not in ("name", "rrn", "phone", "email", "custom"):
        raise HTTPException(status_code=422, detail="invalid kind")
    # data-unit의 정규식 검증기를 재사용한다 — 단일 진실 공급원 유지.
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
    """PII 패턴의 활성화 상태를 토글한다(활성→비활성, 비활성→활성).

    삭제 대신 토글을 제공하는 이유: 패턴을 완전히 제거하면 과거 마스킹 이력과의
    연결이 끊기므로, 비활성화로 논리 삭제하는 방식을 우선 제공한다.
    """
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


@router.delete("/pii-patterns/{pattern_id}", status_code=204, response_model=None)
async def delete_pii_pattern(pattern_id: UUID, session: Session) -> None:
    """PII 패턴을 물리 삭제한다. 복구 불가하므로 UI에서 확인 절차가 필요하다."""
    row = await session.get(PiiPattern, pattern_id)
    if row is None:
        raise HTTPException(status_code=404, detail="pattern not found")
    await session.delete(row)
    await session.commit()


# ---------------------------------------------------------------------------
# Backups
# ---------------------------------------------------------------------------
class BackupOut(BaseModel):
    """백업 실행 이력 한 건의 응답 스키마."""

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
    """최근 백업 이력 최대 50건을 최신 순으로 반환한다.

    50건으로 제한하는 이유: 백업 이력은 운영 모니터링 목적이므로 최근 것만
    충분하며, 페이지네이션 없이 단순하게 유지한다.
    """
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
async def run_backup(session: Session, request: Request) -> BackupOut:
    """애플리케이션 DB의 실제 백업을 수행하고 결과를 기록한다.

    앱 DB가 파일 기반 SQLite인 경우:
    - SQLite의 온라인 백업 API(``sqlite3.connect.backup()``)를 먼저 시도한다.
      온라인 백업 API를 쓰는 이유: 쓰기 진행 중인 DB를 복사해도 스냅샷이 일관성을
      유지하기 때문이다(단순 파일 복사는 쓰기 중간 상태를 포착할 수 있다).
    - 온라인 API가 실패하면 shutil.copy2로 파일을 복사한다(폴백).

    앱 DB가 SQLite가 아니거나(예: PostgreSQL) 파일이 존재하지 않으면,
    "failed" 상태 행을 기록하고 솔직한 오류 메시지를 반환한다.
    절대로 가짜 성공(fake success)을 반환하지 않는다.

    기록하는 size_bytes는 실제 아티팩트 크기이며 조작하지 않는다.
    """
    import shutil
    import sqlite3
    from pathlib import Path
    from urllib.parse import urlsplit

    def sqlite_file_path(url: str) -> Path | None:
        """파일 기반 SQLite URL에서 디스크 경로를 추출한다.

        메모리 DB(:memory:)나 SQLite가 아닌 URL에는 None을 반환한다.
        이 함수를 로컬에 두는 이유: admin-unit이 복합 backend 패키지에
        의존하지 않도록 결합도를 낮추기 위해서다.
        """
        if not url.startswith("sqlite"):
            return None
        path = urlsplit(url).path
        if not path or ":memory:" in url:
            return None
        if path.startswith("//"):
            return Path(path[1:])  # 절대 경로 형식 처리.
        return Path(path.lstrip("/"))

    settings = getattr(request.app.state, "settings", None)
    database_url = getattr(settings, "database_url", "") or ""

    backup_id = uuid4()
    started = datetime.utcnow()

    def _fail(reason: str) -> Backup:
        """실패 Backup 행을 생성하는 내부 헬퍼. 중복 코드를 줄이기 위해 사용."""
        return Backup(
            backup_id=backup_id,
            target="meta_db",
            started_at=started,
            ended_at=datetime.utcnow(),
            state="failed",
            size_bytes=None,
            location=None,
            error=reason,
        )

    src_path = sqlite_file_path(database_url)
    if src_path is None:
        row = _fail("backup unavailable: app DB is not a file-backed SQLite database")
    elif not src_path.exists():
        row = _fail(f"backup unavailable: database file not found at {src_path}")
    else:
        try:
            backups_dir = src_path.parent / "backups"
            backups_dir.mkdir(parents=True, exist_ok=True)
            stamp = started.strftime("%Y%m%dT%H%M%SZ")
            dest = backups_dir / f"platform-{stamp}-{backup_id}.db"

            # SQLite 온라인 백업 API로 쓰기 일관성을 보장한다.
            # 실패 시 shutil.copy2로 폴백한다(파일 일관성 보장 없음, 마지막 수단).
            try:
                src_conn = sqlite3.connect(str(src_path))
                dst_conn = sqlite3.connect(str(dest))
                try:
                    src_conn.backup(dst_conn)
                finally:
                    dst_conn.close()
                    src_conn.close()
            except sqlite3.Error:
                shutil.copy2(str(src_path), str(dest))

            size = Path(dest).stat().st_size
            row = Backup(
                backup_id=backup_id,
                target="meta_db",
                started_at=started,
                ended_at=datetime.utcnow(),
                state="success",
                size_bytes=size,
                location=str(dest),
                error=None,
            )
        except OSError as exc:
            row = _fail(f"backup failed: {exc}")

    session.add(row)
    await session.commit()
    return BackupOut(
        backup_id=row.backup_id,
        target=row.target,
        started_at=row.started_at,
        ended_at=row.ended_at,
        state=row.state,
        size_bytes=row.size_bytes,
        location=row.location,
        error=row.error,
    )


# ---------------------------------------------------------------------------
# Aggregate dashboard stats (used by the Admin home page)
# ---------------------------------------------------------------------------
class DashboardStats(BaseModel):
    """어드민 홈 화면 대시보드 집계 수치 스키마."""

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
    """어드민 홈 화면에 표시할 플랫폼 전체 집계 수치를 반환한다.

    각 테이블에서 COUNT(*)를 개별 쿼리로 실행한다.
    단일 복잡한 조인 대신 개별 쿼리를 사용하는 이유:
    - 각 쿼리가 독립적이라 이해·디버깅이 쉽다.
    - 대시보드 수치는 엄격한 정합성이 필요 없으므로 일관된 스냅샷 트랜잭션이
      불필요하다.

    audit_events_last_24h는 occurred_at(이벤트 실제 발생 시각)이 최근 24시간 안인
    감사 로그만 센다. cutoff는 naive UTC로 계산한다 — 이벤트 생산자들이 occurred_at을
    datetime.utcnow()(naive UTC)로 기록하므로 같은 형식으로 비교해야 한다.
    """
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
    audit_cutoff = datetime.utcnow() - timedelta(hours=24)
    audit_events = (
        await session.scalar(
            select(sql_func.count())
            .select_from(AuditLog)
            .where(AuditLog.occurred_at >= audit_cutoff)
        )
        or 0
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
