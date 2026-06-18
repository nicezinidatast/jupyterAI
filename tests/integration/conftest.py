"""통합 테스트 conftest.

세션당 하나의 임시 postgres 컨테이너(testcontainers)를 기동하고,
SQLAlchemy async 세션 팩토리(audit/credential 어댑터용)와
raw asyncpg URL(data-unit 커넥터용)을 픽스처로 제공한다.

모든 unit 의 ``src/`` 디렉터리를 ``sys.path`` 앞에 추가하여,
editable install 없이도 unit 패키지를 임포트할 수 있게 한다.

컨테이너는 속도를 위해 세션 스코프로 재사용된다.
격리가 필요한 경우 ``fresh_session_factory`` 픽스처가 테스트마다 스키마를 재생성한다.
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
    """Docker 데몬에 ping 이 성공하면 True 를 반환한다.

    Docker 없이 실행 중인 환경(예: CI runner)에서 통합 테스트 전체를 skip하기 위한 조건이다.
    """
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
    """임시 postgres:16-alpine 컨테이너를 기동하고 접속 정보를 반환한다.

    Docker 가 없으면 통합 모듈 전체를 skip하여, Docker 없는 환경에서도
    다른 테스트 스위트는 계속 실행되도록 한다.

    반환 딕셔너리 키: host, port, user, password, database, async_url, asyncpg_dsn.
    """
    if not _docker_available():
        pytest.skip("docker not available")
    from testcontainers.postgres import PostgresContainer  # type: ignore[import-not-found]

    container = PostgresContainer(
        image="postgres:16-alpine",
        username="itest",
        password="itest",  # noqa: S106 — 임시 테스트 컨테이너
        dbname="itest",
    )
    container.start()
    try:
        host = container.get_container_host_ip()
        port = int(container.get_exposed_port(5432))
        # Testcontainers 기본 호스트는 'localhost' 이지만 Windows 환경의 컨테이너 네트워크에서
        # 0.0.0.0 으로 해석되는 경우가 있다. 안정적인 연결을 위해 127.0.0.1 로 정규화한다.
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
    """테스트마다 신선한 스키마를 가진 세션 팩토리를 반환한다.

    각 unit 의 Base 에 등록된 모든 메타데이터 테이블을 drop 후 재생성한다.
    이렇게 하면 새 컨테이너를 기동하는 비용 없이 테스트 간 상태 독립을 보장한다.
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
    """임시 postgres 컨테이너의 asyncpg DSN 을 반환한다.

    data-unit 커넥터가 asyncpg 드라이버를 직접 사용하는 경우에 제공한다.
    """
    return postgres_container["asyncpg_dsn"]


@pytest.fixture
def spec_for_postgres(postgres_container: dict[str, str]):
    """임시 postgres 컨테이너를 가리키는 ConnectionSpec 을 반환한다.

    data-unit 의 PostgresConnector 테스트에서 커넥션 설정 객체로 사용한다.
    """
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
    """tests/integration/ 경로의 모든 테스트에 `integration` 마커를 자동으로 붙인다.

    이 훅을 통해 ``pytest -m integration`` 으로 통합 테스트만 선택 실행할 수 있다.
    """
    for item in items:
        if "tests/integration" in str(getattr(item, "fspath", "")):
            item.add_marker(pytest.mark.integration)
