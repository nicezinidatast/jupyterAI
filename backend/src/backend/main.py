"""복합(composite) FastAPI 앱. 각 유닛이 라우터를 제공한다.

이 모듈은 게이트웨이 뒷단에서 동작하는 단일 ASGI 프로세스로,
auth·audit·credential·data·notebook·admin·copilot 유닛의 라우터를 하나로 조립한다.

테이블 생성 전략
----------------
데모 빌드에서는 시작 시 SQLAlchemy ``create_all``로 테이블을 직접 생성한다.
프로덕션에서는 init 컨테이너에서 ``alembic upgrade head``를 실행하는 방식으로 교체한다.
와이어링 경로는 ``infra/ansible/site.yml`` 참조.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncIterator
from urllib.parse import urlsplit

from fastapi import FastAPI, Response
from sqlalchemy import inspect as sa_inspect
from sqlalchemy import text as sa_text
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine

from admin_backend.api.router import router as admin_router
from admin_backend.models import Base as AdminBase
from backend.seed import bootstrap_admin, seed_demo_data
from audit.api.router import router as audit_router
from audit.models import Base as AuditBase
from auth.api.oidc_dependency import OidcVerifier
from auth.api.router import router as auth_router
from auth.models import Base as AuthBase
from backend.config import BackendSettings
from credential.adapters.local_kms import LocalKmsAdapter
from credential.api.router import router as credential_router
from credential.models import Base as CredentialBase
from cryptography.fernet import Fernet
from data.api.router import router as data_router
from data.models import Base as DataBase
from dataplatform_shared.telemetry import (
    configure_logging,
    configure_tracing,
    get_logger,
    metrics_endpoint,
)
from copilot.api.router import router as copilot_router
from notebook.api.router import router as notebook_router
from notebook.models import Base as NotebookBase

logger = get_logger("backend.main")

_ALL_BASES = (AuthBase, AuditBase, CredentialBase, DataBase, NotebookBase, AdminBase)


async def _ensure_user_columns(engine: AsyncEngine) -> None:
    """나중에 추가된 ``users`` 컬럼을 기존 DB에도 멱등하게 보강한다.

    ``create_all``은 이미 존재하는 테이블에 컬럼을 추가하지 않는다. 그래서 영속
    볼륨에 남아 있는 기존 SQLite DB(또는 운영 DB)는 신규 컬럼이 없어, 모델이 그
    컬럼을 SELECT하는 순간 "no such column"으로 로그인·조회가 모두 깨진다. 여기서
    누락 컬럼만 골라 ``ALTER TABLE ... ADD COLUMN``으로 채운다 — 이미 있으면 건너뛰어
    멱등하다. ``DEFAULT false``는 SQLite(3.23+)와 Postgres 양쪽에서 동작한다.

    대상: ``must_change_password``(첫 로그인 비밀번호 변경 안내 플래그).
    """

    def _add(sync_conn) -> None:
        existing = {c["name"] for c in sa_inspect(sync_conn).get_columns("users")}
        if "must_change_password" not in existing:
            sync_conn.execute(
                sa_text(
                    "ALTER TABLE users ADD COLUMN must_change_password "
                    "BOOLEAN NOT NULL DEFAULT false"
                )
            )

    async with engine.begin() as conn:
        await conn.run_sync(_add)


async def _create_all_tables(engine: AsyncEngine) -> None:
    """모든 유닛의 ORM Base를 순회하며 누락된 테이블을 생성한다.

    ``create_all``은 이미 존재하는 테이블을 건드리지 않으므로 멱등(idempotent)하다.
    유닛별 Base를 분리한 이유는 각 유닛이 자체 메타데이터를 소유해
    의존성 역전을 유지하기 위해서다.
    """
    async with engine.begin() as conn:
        for base in _ALL_BASES:
            await conn.run_sync(base.metadata.create_all)


def sqlite_file_path(database_url: str) -> Path | None:
    """SQLite URL에서 디스크 경로를 추출한다. 다른 엔진이면 ``None``을 반환한다.

    처리하는 URL 형태:
    - ``sqlite+aiosqlite:///relative/path.db`` (상대 경로)
    - ``sqlite+aiosqlite:////absolute/path.db`` (절대 경로)
    - 인메모리 형태 (파일 없음 → ``None`` 반환)

    urlsplit 파싱 규칙:
    - ``sqlite:///x.db`` → path = ``/x.db`` (슬래시 하나 = 상대 파일 ``x.db``)
    - ``sqlite:////abs`` → path = ``//abs`` (슬래시 둘 = 절대 파일 ``/abs``)
    """
    if not database_url.startswith("sqlite"):
        return None
    # 스킴의 "://" 이후 부분. SQLite는 netloc이 비어 있고 path가 뒤따른다.
    parts = urlsplit(database_url)
    path = parts.path
    if not path or path == "/:memory:" or ":memory:" in database_url:
        return None
    # urlsplit은 path 앞에 항상 "/" 를 붙인다.
    # "//abs" 형태면 절대 경로이므로 앞 슬래시 하나를 제거한다.
    if path.startswith("//"):
        return Path(path[1:])  # 절대 경로
    return Path(path.lstrip("/"))


def _ensure_sqlite_dir(database_url: str) -> None:
    """파일 기반 SQLite DB의 부모 디렉터리가 없으면 생성한다.

    aiosqlite는 누락된 디렉터리를 자동으로 만들지 않기 때문에
    엔진 초기화 전에 이 함수를 호출해야 한다.
    인메모리 SQLite나 Postgres URL이면 아무것도 하지 않는다.
    """
    file_path = sqlite_file_path(database_url)
    if file_path is None:
        return
    parent = file_path.parent
    if parent and not parent.exists():
        parent.mkdir(parents=True, exist_ok=True)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """ASGI 라이프스팬 핸들러 — 앱 시작/종료 시 공유 자원을 초기화·정리한다.

    초기화 순서 (순서 변경 시 의존성 오류 발생 가능):
    1. 로깅·트레이싱 설정
    2. Copilot LLM 프로바이더 확인 (비치명적 — 실패해도 나머지 서비스는 정상 동작)
    3. SQLite 디렉터리 생성 (엔진보다 먼저)
    4. SQLAlchemy 비동기 엔진·세션 팩토리 생성
    5. Fernet 자격증명 암호화 키 및 vault 어댑터 초기화
    6. OIDC 검증기 초기화 (issuer 설정 여부에 따라 분기)
    7. 테이블 생성 + 관리자 계정 부트스트랩 + 데모 시드

    DB 초기화가 실패해도 ``/healthz``는 계속 서비스한다.
    docker-compose 헬스체크가 통과해야 의존 컨테이너가 시작되기 때문이다.
    """
    settings: BackendSettings = app.state.settings
    configure_logging(level=settings.log_level)
    configure_tracing(service_name="backend", otlp_endpoint=settings.otlp_endpoint or None)

    # Copilot LLM 프로바이더를 부트 직후 로그에 출력한다
    # (예: provider=internal/gemma4 model=gemma4-31b-vllm).
    # 잘못된 설정도 치명적이지 않다 — 경고 로그만 남기고 /api/copilot/* 는 503으로 처리.
    try:
        from copilot.factory import describe_active

        logger.info("copilot_provider_ready", **describe_active())
    except Exception as e:  # noqa: BLE001
        logger.warning("copilot_provider_unavailable", error=str(e))

    # 파일 기반 SQLite DB: 엔진이 파일을 열기 전에 부모 디렉터리를 생성해야 한다.
    # aiosqlite는 누락된 디렉터리를 자동으로 만들지 않는다.
    _ensure_sqlite_dir(settings.database_url)

    # pool_pre_ping: 풀에 보관된 asyncpg 연결이 Postgres 재시작·idle timeout으로
    # 끊길 수 있다. ping 없이 체크아웃하면 InterfaceError('connection is closed')가
    # 사용자에게 500으로 노출된다.
    # SQLite는 단일 연결 풀을 쓰고 이런 네트워크 장애 모드가 없으므로 ping은 불필요하다.
    is_sqlite = settings.database_url.startswith("sqlite")
    engine = create_async_engine(
        settings.database_url, echo=False, pool_pre_ping=not is_sqlite
    )
    app.state.engine = engine
    app.state.session_factory = async_sessionmaker(engine, expire_on_commit=False)

    # 로컬 KMS vault 어댑터용 Fernet 키.
    # 설정이 비어 있으면 프로세스 수명 동안만 유효한 임시 키를 생성한다(데모 허용).
    # 프로덕션에서는 시크릿 매니저로 안정적인 키를 주입해야 재시작 후에도 기존 암호문을 복호화할 수 있다.
    key_b = settings.credential_key.encode("utf-8") if settings.credential_key else Fernet.generate_key()
    app.state.vault_adapter = LocalKmsAdapter(
        key=key_b, session_factory=app.state.session_factory
    )

    # OIDC 검증기 초기화 — issuer가 설정된 경우에만 생성한다.
    if settings.oidc_issuer:
        app.state.oidc_verifier = OidcVerifier(
            issuer=settings.oidc_issuer,
            audience=settings.oidc_audience or None,
        )
        logger.info("oidc_verifier_ready", issuer=settings.oidc_issuer, strict=settings.oidc_strict)
    else:
        app.state.oidc_verifier = None
        logger.info("oidc_disabled_demo_mode")
    app.state.oidc_strict = settings.oidc_strict

    try:
        await _create_all_tables(engine)
        # 기존 DB에 누락된 신규 컬럼(must_change_password)을 보강한다(create_all 직후).
        await _ensure_user_columns(engine)
        # DB URL에서 패스워드 부분(@ 앞)을 제외하고 로그에 기록한다.
        logger.info("backend_startup", database=settings.database_url.split("@")[-1])
        async with app.state.session_factory() as session:
            # 실제 admin 계정은 BACKEND_SEED_DEMO 여부와 무관하게 항상 부트스트랩한다.
            # 멱등하므로 재시작해도 기존 계정을 건드리지 않는다.
            await bootstrap_admin(session)
            if settings.seed_demo:
                await seed_demo_data(session, vault_adapter=app.state.vault_adapter)
    except Exception as e:  # noqa: BLE001
        logger.error("startup_failed", error=str(e))
        # /healthz는 계속 서비스해 docker-compose 헬스체크가 통과하게 한다.
        # DB가 필요한 API 엔드포인트는 호출 시점에 503을 반환한다.
    yield
    await engine.dispose()


def create_app(settings: BackendSettings | None = None) -> FastAPI:
    """앱 팩토리 — 테스트가 싱글턴 상태에서 자유롭도록 매번 새 인스턴스를 반환한다.

    각 유닛의 라우터를 포함시키고 헬스체크·메트릭 엔드포인트를 인라인으로 등록한다.
    ``settings``를 생략하면 환경 변수에서 자동으로 읽어온다.
    """
    settings = settings or BackendSettings()
    app = FastAPI(title="dataplatform backend", version="0.1.0", lifespan=lifespan)
    app.state.settings = settings

    # 각 유닛 라우터를 포함한다. 유닛별 prefix는 각 router 정의에서 설정한다.
    app.include_router(auth_router)
    app.include_router(audit_router)
    app.include_router(credential_router)
    app.include_router(data_router)
    app.include_router(notebook_router)
    app.include_router(admin_router)
    app.include_router(copilot_router)

    @app.get("/healthz")
    async def healthz() -> dict[str, str]:
        """Liveness 프로브 — 프로세스가 살아 있는지만 확인한다."""
        return {"status": "ok"}

    @app.get("/readyz")
    async def readyz() -> dict[str, str]:
        """Readiness 프로브 — 트래픽을 받을 준비가 됐는지 알린다."""
        return {"status": "ready"}

    @app.get("/metrics")
    async def metrics() -> Response:
        """Prometheus 스크레이프 엔드포인트 — 수집기가 주기적으로 호출한다."""
        body, content_type = metrics_endpoint()
        return Response(content=body, media_type=content_type)

    @app.get("/")
    async def root() -> dict[str, object]:
        """서비스 기본 정보와 주요 엔드포인트 목록을 반환한다."""
        return {
            "service": "dataplatform-backend",
            "version": "0.1.0",
            "endpoints": [
                "/healthz",
                "/readyz",
                "/metrics",
                "/api/auth/me",
                "/api/audit/ping",
                "/api/credentials/ping",
                "/api/connections/ping",
                "/api/queries/ping",
                "/api/files/ping",
                "/api/notebooks/ping",
                "/api/share/ping",
                "/api/admin/ping",
            ],
        }

    return app


# 모듈 임포트 시 기본 인스턴스 생성. uvicorn은 이 심볼을 진입점으로 사용한다.
app = create_app()
