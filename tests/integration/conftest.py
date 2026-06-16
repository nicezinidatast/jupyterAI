"""Integration-test conftest.

Spins up a single ephemeral postgres container per session and exposes both
SQLAlchemy async session factories (for audit / credential adapters) and a raw
``asyncpg`` URL (for the data-unit connector). All unit ``src/`` directories
are prepended to ``sys.path`` so the unit packages import without an editable
install.

The container is reused across the whole integration suite (session scope) for
speed; tables are recreated per-test via the ``fresh_session_factory`` fixture
when isolation matters.
"""

from __future__ import annotations

import sys
from collections.abc import Iterator
from pathlib import Path

import pytest
import pytest_asyncio

ROOT = Path(__file__).resolve().parents[2]
_UNIT_SRC_DIRS = [
    ROOT / "units" / "shared-lib" / "src",
    ROOT / "units" / "audit-unit" / "src",
    ROOT / "units" / "credential-unit" / "src",
    ROOT / "units" / "data-unit" / "src",
]
for src in _UNIT_SRC_DIRS:
    p = str(src)
    if p not in sys.path:
        sys.path.insert(0, p)


def _docker_available() -> bool:
    try:
        import docker  # type: ignore[import-not-found]

        docker.from_env().ping()
        return True
    except Exception:  # noqa: BLE001
        return False


pytestmark_docker = pytest.mark.skipif(
    not _docker_available(), reason="docker daemon not reachable"
)


@pytest.fixture(scope="session")
def postgres_container() -> Iterator[dict[str, str]]:
    """Ephemeral postgres:16 container. Returns connection coordinates.

    We skip the entire integration module if docker isn't available — this lets
    the suite stay green on machines without a docker daemon.
    """
    if not _docker_available():
        pytest.skip("docker not available")
    from testcontainers.postgres import PostgresContainer  # type: ignore[import-not-found]

    container = PostgresContainer(
        image="postgres:16-alpine",
        username="itest",
        password="itest",  # noqa: S106 — ephemeral test container
        dbname="itest",
    )
    container.start()
    try:
        host = container.get_container_host_ip()
        port = int(container.get_exposed_port(5432))
        # Testcontainers' default host can be 'localhost' but on Windows resolves to
        # 0.0.0.0 inside the container's network. Normalise to 127.0.0.1.
        if host in ("localhost", "0.0.0.0"):
            host = "127.0.0.1"
        yield {
            "host": host,
            "port": str(port),
            "user": "itest",
            "password": "itest",
            "database": "itest",
            "async_url": f"postgresql+asyncpg://itest:itest@{host}:{port}/itest",
            "asyncpg_dsn": f"postgresql://itest:itest@{host}:{port}/itest",
        }
    finally:
        container.stop()


@pytest_asyncio.fixture
async def fresh_session_factory(postgres_container: dict[str, str]):
    """Per-test session factory backed by a freshly-created schema.

    Drops + recreates every metadata table for each unit's Base so tests stay
    independent without paying for a new container.
    """
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    from audit.models import Base as AuditBase
    from credential.models import Base as CredBase

    engine = create_async_engine(postgres_container["async_url"], echo=False, future=True)
    try:
        async with engine.begin() as conn:
            for base in (AuditBase, CredBase):
                await conn.run_sync(base.metadata.drop_all)
                await conn.run_sync(base.metadata.create_all)
        session_factory = async_sessionmaker(engine, expire_on_commit=False)
        yield session_factory
    finally:
        await engine.dispose()


@pytest.fixture
def asyncpg_dsn(postgres_container: dict[str, str]) -> str:
    return postgres_container["asyncpg_dsn"]


@pytest.fixture
def spec_for_postgres(postgres_container: dict[str, str]):
    """ConnectionSpec pointing at the ephemeral postgres."""
    from data.schemas import ConnectionSpec

    return ConnectionSpec(
        name="itest_pg",
        engine="postgres",
        host=postgres_container["host"],
        port=int(postgres_container["port"]),
        database=postgres_container["database"],
        credential_id="00000000-0000-0000-0000-000000000001",
    )


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    """All integration tests must run with the `integration` marker."""
    for item in items:
        if "tests/integration" in str(getattr(item, "fspath", "")):
            item.add_marker(pytest.mark.integration)
