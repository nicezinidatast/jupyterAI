"""시작 시드 처리.

이 모듈에는 성격이 다른 두 가지 관심사가 공존한다:

* :func:`bootstrap_admin` — **항상** 시작 시 실행된다. ``admin`` / ``admin`` 계정이
  정확히 하나 존재하고 활성 상태이며 Admin 역할을 가지고 있음을 보장한다.
  멱등(idempotent)하므로 재시작해도 안전하다.
* :func:`seed_demo_data` — 쇼케이스 픽스처(데모 사용자·연결·PII 패턴·백업·감사로그·
  노트북·공유링크)를 삽입한다. ``BACKEND_SEED_DEMO=true`` 일 때만 실행되는 옵트인 방식이며,
  테이블별로 멱등하다(이미 행이 있으면 건너뛴다).
"""

from __future__ import annotations

from datetime import datetime, timedelta
from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from admin_backend.models import Backup
from auth.models import User, UserRole
from auth.services.password import hash_password
from credential.adapters.vault import VaultAdapter
from credential.models import Credential
from data.models import Connection, ConnectionGrant, PiiPattern
from dataplatform_shared.security.secret import Secret
from dataplatform_shared.telemetry import get_logger

logger = get_logger("backend.seed")

# 실제 운영용 admin 계정 — 이 값은 공유 계약이므로 변경 시 전체 영향도 확인 필요.
ADMIN_EMAIL = "admin"
ADMIN_PASSWORD = "admin"
ADMIN_DISPLAY_NAME = "Administrator"


async def bootstrap_admin(session: AsyncSession) -> None:
    """실제 admin 계정이 존재하고 활성 상태이며 Admin 역할을 가졌음을 보장한다.

    멱등(idempotent): 재실행해도 기존 행을 건드리지 않는다.
    단, 부분적으로 손상된 행(비밀번호 해시 누락·비활성·역할 누락)은 복구한다.
    BACKEND_SEED_DEMO 설정과 무관하게 매 시작 시 무조건 실행된다.

    flush를 사용하는 이유: ``session.add(user)`` 직후 user_id가 DB에 쓰여야
    뒤따르는 UserRole INSERT의 FK 제약이 통과하기 때문이다.
    """
    user = (
        await session.execute(select(User).where(User.email == ADMIN_EMAIL))
    ).scalar_one_or_none()

    if user is None:
        user = User(
            user_id=uuid4(),
            email=ADMIN_EMAIL,
            display_name=ADMIN_DISPLAY_NAME,
            password_hash=hash_password(ADMIN_PASSWORD),
            is_active=True,
        )
        session.add(user)
        await session.flush()  # 역할 INSERT의 FK 대상인 user_id를 DB에 먼저 반영
        logger.info("admin_bootstrap_created")
    else:
        # 정상 동작 중인 행은 덮어쓰지 않고 누락된 부분만 복구한다.
        if not user.password_hash:
            user.password_hash = hash_password(ADMIN_PASSWORD)
        if not user.is_active:
            user.is_active = True

    has_admin_role = (
        await session.execute(
            select(UserRole).where(
                UserRole.user_id == user.user_id, UserRole.role == "Admin"
            )
        )
    ).scalar_one_or_none()
    if has_admin_role is None:
        session.add(UserRole(user_id=user.user_id, role="Admin"))

    await session.commit()


# 데모 사용자 목록: (이메일, 표시 이름, 역할 목록)
_DEMO_USERS: list[tuple[str, str, list[str]]] = [
    ("admin@example.test", "Park Min-jun (Admin)", ["Admin"]),
    ("alice.kim@example.test", "Alice Kim (Analyst)", ["Analyst"]),
    ("bob.lee@example.test", "Bob Lee (Analyst)", ["Analyst"]),
    ("viewer@example.test", "Choi Ji-hye (Viewer)", ["Viewer"]),
    ("auditor@example.test", "Lee Sung-ho (Auditor)", ["Auditor"]),
]

# 호스트명은 demo-* compose 서비스를 가리킨다.
# Postgres·MySQL은 infra/demo-data/*로 시드된 실제 컨테이너에 연결된다.
# Hive는 Phase 2 범위 — 현재는 도달 불가능한 플레이스홀더 호스트다.
# 컬럼 순서: (이름, 엔진, 호스트, 포트, 데이터베이스, 사용자명, 비밀번호)
_DEMO_CONNECTIONS: list[tuple[str, str, str, int, str, str, str]] = [
    ("sales_db", "postgres", "demo-postgres", 5432, "sales", "demo", "demo"),
    ("crm_mysql", "mysql", "demo-mysql", 3306, "crm", "demo", "demo"),
    ("warehouse_hive", "hive", "hive.internal", 10000, "default", "hive", "hive"),
]

# PII 패턴 목록: (이름, 종류, 정규식)
# 한글 범위는 \u 이스케이프로 인코딩한다.
# Windows cp949 환경에서 소스 파일을 열면 리터럴 한글이 깨질 수 있기 때문이다.
_DEMO_PII: list[tuple[str, str, str]] = [
    ("Korean Name", "name", "^[가-힣]{2,4}$"),
    ("RRN", "rrn", r"\b\d{6}-?\d{7}\b"),
    ("Mobile Phone", "phone", r"\b01[016789]-?\d{3,4}-?\d{4}\b"),
    ("Email Address", "email", r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b"),
]


async def seed_demo_data(
    session: AsyncSession, *, vault_adapter: VaultAdapter | None = None
) -> None:
    """테이블이 비어 있을 때 데모·쇼케이스 행을 삽입한다. 도메인별로 커밋한다.

    옵트인 전용: ``BACKEND_SEED_DEMO=true`` 일 때만 ``backend.main``이 호출한다.
    실제 admin 계정은 :func:`bootstrap_admin`이 별도로 처리하며 이 플래그와 무관하다.

    각 내부 함수는 테이블이 비어 있는지 먼저 확인하고, 이미 데이터가 있으면
    아무것도 삽입하지 않는다(멱등). 순서가 중요하다 — 사용자가 먼저 삽입되어야
    노트북·공유링크가 FK를 참조할 수 있다.
    """
    await _seed_users(session)
    await _seed_connections(session, vault_adapter=vault_adapter)
    await _seed_pii(session)
    await _seed_backups(session)
    await _seed_workspaces_notebooks(session)
    await _seed_share_links(session)
    await _seed_audit_events(session)


async def _seed_users(session: AsyncSession) -> None:
    existing = await session.scalar(select(func.count()).select_from(User))
    if existing:
        return
    for email, name, roles in _DEMO_USERS:
        uid = uuid4()
        session.add(User(user_id=uid, email=email, display_name=name, is_active=True))
        for role in roles:
            session.add(UserRole(user_id=uid, role=role))
    await session.commit()
    logger.info("demo_users_seeded", count=len(_DEMO_USERS))


async def _seed_connections(
    session: AsyncSession, *, vault_adapter: VaultAdapter | None = None
) -> None:
    """데모 데이터베이스 연결과 자격증명을 삽입한다.

    사용자명은 민감 정보가 아니므로 Connection.options(평문)에 저장한다.
    비밀번호는 vault 어댑터를 통해 암호화하고 DB에는 암호문(ciphertext)만 남긴다.
    """
    existing = await session.scalar(select(func.count()).select_from(Connection))
    if existing:
        return
    for name, engine, host, port, db, username, password in _DEMO_CONNECTIONS:
        cred_id = uuid4()
        conn_id = uuid4()
        vault_path = f"dataplatform/shared/{cred_id}"
        session.add(
            Credential(
                credential_id=cred_id,
                scope="shared",
                owner_user_id=None,
                name=f"{name}-cred",
                vault_path=vault_path,
                is_active=True,
            )
        )
        # 사용자명은 운영 메타데이터(비밀 아님)이므로 Connection.options에 평문 저장.
        # 비밀번호는 vault 어댑터가 암호화해 SecretsStorage 테이블에 기록한다.
        session.add(
            Connection(
                connection_id=conn_id,
                name=name,
                engine=engine,
                host=host,
                port=port,
                database=db,
                credential_id=cred_id,
                options={"username": username},
                is_active=True,
            )
        )
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
        if vault_adapter is not None and password:
            # 비밀번호 암호문을 SecretsStorage 테이블에 기록한다.
            result = await vault_adapter.write(vault_path, Secret(password))
            if not result.ok:
                logger.error("seed_credential_write_failed", name=name)
    await session.commit()
    logger.info("demo_connections_seeded", count=len(_DEMO_CONNECTIONS))


async def _seed_pii(session: AsyncSession) -> None:
    existing = await session.scalar(select(func.count()).select_from(PiiPattern))
    if existing:
        return
    for name, kind, regex in _DEMO_PII:
        session.add(
            PiiPattern(
                pattern_id=uuid4(),
                name=name,
                kind=kind,
                regex=regex,
                is_active=True,
            )
        )
    await session.commit()
    logger.info("demo_pii_seeded", count=len(_DEMO_PII))


async def _seed_backups(session: AsyncSession) -> None:
    existing = await session.scalar(select(func.count()).select_from(Backup))
    if existing:
        return
    now = datetime.utcnow()
    rows = [
        ("meta_db", now - timedelta(days=3), "success", 6_500_000),
        ("workspaces", now - timedelta(days=2), "success", 134_000_000),
        ("meta_db", now - timedelta(days=1), "failed", None),
        ("meta_db", now - timedelta(hours=2), "success", 6_700_000),
    ]
    for target, ts, state, size in rows:
        session.add(
            Backup(
                backup_id=uuid4(),
                target=target,
                started_at=ts,
                ended_at=ts + timedelta(minutes=2),
                state=state,
                size_bytes=size,
                location=f"/var/backups/{uuid4()}.dump" if size else None,
                error=None if state == "success" else "pg_dump: connection refused",
            )
        )
    await session.commit()
    logger.info("demo_backups_seeded", count=len(rows))


async def _seed_workspaces_notebooks(session: AsyncSession) -> None:
    from notebook.models import Notebook, NotebookVersion, Workspace

    if await session.scalar(select(func.count()).select_from(Workspace)):
        return
    analyst = (
        await session.execute(
            select(User).where(User.email == "alice.kim@example.test")
        )
    ).scalar_one_or_none()
    if analyst is None:
        return
    ws_id = uuid4()
    session.add(
        Workspace(
            workspace_id=ws_id,
            owner_user_id=analyst.user_id,
            kind="personal",
            name="Alice Personal",
            git_repo_url="https://gitea.internal/alice/notebooks.git",
            git_branch="main",
        )
    )
    # 뒤따르는 Notebook INSERT가 FK 대상인 workspace_id를 참조할 수 있도록 먼저 flush한다.
    await session.flush()

    sample_content = {
        "cells": [
            {
                "kind": "sql",
                "connection": "sales_db",
                "sql": "SELECT customer_name, email, amount FROM orders LIMIT 25",
            },
            {
                "kind": "chart",
                "type": "bar",
                "mapping": {"x": "city", "y": "amount"},
            },
        ],
        "title": "Daily Sales Snapshot",
    }

    notebooks = [
        ("analyses/daily-sales.ipynb", sample_content),
        ("analyses/lead-funnel.ipynb", {
            "title": "Lead Funnel",
            "cells": [
                {"kind": "sql", "connection": "crm_mysql", "sql": "SELECT stage, COUNT(*) AS leads FROM leads GROUP BY stage"},
                {"kind": "chart", "type": "pie", "mapping": {"x": "stage", "y": "leads"}},
            ],
        }),
        ("analyses/warehouse-overview.ipynb", {
            "title": "Warehouse Overview",
            "cells": [
                {"kind": "sql", "connection": "warehouse_hive", "sql": "SELECT event_date, revenue FROM events_daily LIMIT 30"},
                {"kind": "chart", "type": "line", "mapping": {"x": "event_date", "y": "revenue"}},
            ],
        }),
    ]
    for path, content in notebooks:
        nb_id = uuid4()
        session.add(
            Notebook(
                notebook_id=nb_id,
                workspace_id=ws_id,
                path=path,
                created_by=analyst.user_id,
            )
        )
        await session.flush()
        import hashlib
        import json as _json

        encoded = _json.dumps(content, sort_keys=True, separators=(",", ":")).encode()
        digest = hashlib.sha256(encoded).hexdigest()
        session.add(
            NotebookVersion(
                version_id=uuid4(),
                notebook_id=nb_id,
                content_sha256=digest,
                content=content,
                saved_by=analyst.user_id,
                is_autosave=False,
                git_commit_sha=None,
            )
        )
    await session.commit()
    logger.info("demo_workspaces_seeded", count=len(notebooks))


async def _seed_share_links(session: AsyncSession) -> None:
    from notebook.models import Notebook, ShareAudience, ShareLink

    if await session.scalar(select(func.count()).select_from(ShareLink)):
        return
    notebooks = (
        await session.execute(select(Notebook).order_by(Notebook.created_at).limit(2))
    ).scalars().all()
    if not notebooks:
        return
    for nb, perm, roles in zip(
        notebooks,
        ("read", "execute"),
        (["Viewer", "Analyst"], ["Analyst"]),
        strict=False,
    ):
        link_id = uuid4()
        session.add(
            ShareLink(
                link_id=link_id,
                notebook_id=nb.notebook_id,
                permission=perm,
                created_by=nb.created_by,
            )
        )
        await session.flush()  # ShareAudience INSERT의 FK 대상인 link_id를 먼저 반영
        for role in roles:
            session.add(
                ShareAudience(
                    audience_id=uuid4(),
                    link_id=link_id,
                    subject_user_id=None,
                    subject_role=role,
                )
            )
    await session.commit()
    logger.info("demo_share_links_seeded")


async def _seed_audit_events(session: AsyncSession) -> None:
    from audit.models import AuditLog

    if await session.scalar(select(func.count()).select_from(AuditLog)):
        return
    users = (await session.execute(select(User))).scalars().all()
    if not users:
        return
    user_emails = [u.email for u in users]
    event_types = [
        ("login", "session", "success"),
        ("login", "session", "failure"),
        ("query_executed", "connection:sales_db", "success"),
        ("query_executed", "connection:crm_mysql", "success"),
        ("query_executed", "connection:warehouse_hive", "failure"),
        ("role_assigned", "user", "success"),
        ("connection_registered", "connection:sales_db", "success"),
        ("pii_pattern_added", "pii", "success"),
        ("notebook_saved", "notebook", "success"),
        ("share_link_created", "share", "success"),
        ("backup_started", "backup", "success"),
        ("backup_failed", "backup", "failure"),
        ("file_uploaded", "file:sales.csv", "success"),
        ("audit_searched", "audit", "success"),
        ("audit_exported", "audit", "success"),
    ]
    now = datetime.utcnow()
    for i in range(50):
        et, res, result = event_types[i % len(event_types)]
        actor = user_emails[i % len(user_emails)]
        session.add(
            AuditLog(
                event_type=et,
                actor_id=actor,
                resource=res,
                result=result,
                occurred_at=now - timedelta(minutes=i * 17),
                corr_id=f"seed-{i:04d}",
                payload={"seq": i, "demo": True},
            )
        )
    await session.commit()
    logger.info("demo_audit_seeded", count=50)
