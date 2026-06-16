"""Startup seeding.

Two distinct concerns live here:

* :func:`bootstrap_admin` — **always** runs at startup. It guarantees exactly
  one real admin account (identifier ``admin`` / password ``admin_st``) exists
  and is active with the ``Admin`` role. Idempotent.
* :func:`seed_demo_data` — the original showcase fixtures (demo users, demo
  connections, PII patterns, fake backups/audit/notebooks/share-links). This is
  now **opt-in** and only runs when ``BACKEND_SEED_DEMO=true``. It is idempotent
  per-table.
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

# The real, unconditional admin account (shared contract).
ADMIN_EMAIL = "admin"
ADMIN_PASSWORD = "admin_st"
ADMIN_DISPLAY_NAME = "Administrator"


async def bootstrap_admin(session: AsyncSession) -> None:
    """Ensure the real admin account exists, is active, and has the Admin role.

    Idempotent: on re-runs it leaves an existing admin untouched (but repairs a
    missing password hash / inactive flag / Admin role if a partial row exists).
    Runs unconditionally on every startup — independent of BACKEND_SEED_DEMO.
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
        await session.flush()  # make user_id visible for the role insert
        logger.info("admin_bootstrap_created")
    else:
        # Repair a partial/legacy row without overwriting a working one.
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


_DEMO_USERS: list[tuple[str, str, list[str]]] = [
    ("admin@example.test", "Park Min-jun (Admin)", ["Admin"]),
    ("alice.kim@example.test", "Alice Kim (Analyst)", ["Analyst"]),
    ("bob.lee@example.test", "Bob Lee (Analyst)", ["Analyst"]),
    ("viewer@example.test", "Choi Ji-hye (Viewer)", ["Viewer"]),
    ("auditor@example.test", "Lee Sung-ho (Auditor)", ["Auditor"]),
]

# Host names point at the demo-* compose services. The platform connects to
# real Postgres/MySQL containers seeded via infra/demo-data/*. Hive remains
# a placeholder unreachable host — out of scope for this round (Phase 2).
_DEMO_CONNECTIONS: list[tuple[str, str, str, int, str, str, str]] = [
    # name, engine, host, port, database, username, password
    ("sales_db", "postgres", "demo-postgres", 5432, "sales", "demo", "demo"),
    ("crm_mysql", "mysql", "demo-mysql", 3306, "crm", "demo", "demo"),
    ("warehouse_hive", "hive", "hive.internal", 10000, "default", "hive", "hive"),
]

_DEMO_PII: list[tuple[str, str, str]] = [
    # Hangul range encoded as \u escapes so the source survives non-UTF-8
    # source encodings (Windows cp949 can mangle literal 한글).
    ("Korean Name", "name", "^[가-힣]{2,4}$"),
    ("RRN", "rrn", r"\b\d{6}-?\d{7}\b"),
    ("Mobile Phone", "phone", r"\b01[016789]-?\d{3,4}-?\d{4}\b"),
    ("Email Address", "email", r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b"),
]


async def seed_demo_data(
    session: AsyncSession, *, vault_adapter: VaultAdapter | None = None
) -> None:
    """Insert demo/showcase rows where tables are empty. Commits per-domain.

    Opt-in only: ``backend.main`` invokes this exclusively when
    ``BACKEND_SEED_DEMO=true``. The real admin account is handled separately by
    :func:`bootstrap_admin` and is never gated by this flag.
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
        # The username is operational metadata (not secret) so it lives in
        # Connection.options. The password is encrypted at rest via the vault
        # adapter; the DB row stores ciphertext only.
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
            # Write the password ciphertext to the SecretsStorage table.
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
    # Flush so the FK target row is visible to the notebook insert that follows.
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
        await session.flush()  # FK target visible before audience rows insert.
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
