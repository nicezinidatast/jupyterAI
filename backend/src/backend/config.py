"""백엔드 환경 변수 기반 설정 (12-factor 앱 원칙).

모든 설정값은 ``BACKEND_`` 접두어가 붙은 환경 변수로 주입된다.
기본값은 SQLite 파일 DB를 사용해 외부 Postgres 없이도 바로 실행 가능하다.
"""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class BackendSettings(BaseSettings):
    """백엔드 전역 설정 컨테이너.

    pydantic-settings가 환경 변수 → 필드 바인딩·타입 변환을 담당한다.
    ``extra="ignore"``로 알 수 없는 환경 변수는 자동으로 무시한다.
    """

    model_config = SettingsConfigDict(env_prefix="BACKEND_", env_file=".env", extra="ignore")

    # 앱 데이터 저장소. 기본값은 로컬 SQLite 파일 — 외부 Postgres 없이 데모 실행 가능.
    # 부모 디렉터리는 시작 시 없으면 자동으로 생성된다.
    # Postgres로 전환하려면 BACKEND_DATABASE_URL=postgresql+asyncpg://... 형태로 지정.
    database_url: str = "sqlite+aiosqlite:///./data/platform.db"
    # 세션 캐시·레이트 리밋 공유에 사용하는 Redis.
    redis_url: str = "redis://redis:6379/0"
    log_level: str = "INFO"
    # OTLP(OpenTelemetry Protocol) 수집기 엔드포인트. 빈 문자열이면 트레이싱 비활성.
    otlp_endpoint: str = ""

    # 브라우저 세션 쿠키 보안 강화.
    # SameSite=Lax + HttpOnly는 항상 활성화되어 있다.
    # Secure 플래그는 이 설정으로 제어한다 — 내부망 HTTP 데모에서는 TLS 없이도
    # 동작해야 하므로 기본 False. 프로덕션(HTTPS 환경)에서는 BACKEND_COOKIE_SECURE=true 필수.
    cookie_secure: bool = False

    # 데모 시드 마스터 스위치.
    # False(기본)이면 시작 시 실제 admin 계정만 부트스트랩하고 나머지 데모 행은 건너뛴다.
    # BACKEND_SEED_DEMO=true로 설정하면 쇼케이스 픽스처 전체를 다시 삽입한다.
    seed_demo: bool = False

    # 32바이트 url-safe base64 Fernet 키. 자격증명 암호화에 사용한다.
    # 빈 문자열이면 시작 시 프로세스 수명 동안만 유효한 임시 키를 생성한다(데모 허용).
    # 프로덕션 배포에서는 시크릿 매니저로 안정적인 키를 주입해야 한다.
    credential_key: str = ""

    # OIDC / Keycloak 하이브리드 동작 모드.
    #
    # oidc_issuer 비어 있음(empty):
    #   검증기를 만들지 않는다. X-User-Email 헤더 또는 시드된 admin으로 신원 확인(데모 모드).
    #
    # oidc_issuer 설정됨:
    #   검증기를 지연 생성(lazy). Bearer 토큰이 있으면 Keycloak JWKS로 검증하고
    #   토큰의 클레임이 우선한다. 토큰이 없는 요청은 oidc_strict가 false이면
    #   데모 모드로 fallthrough.
    #
    # oidc_strict true:
    #   Bearer 토큰이 필수. 게이트웨이가 모든 요청 앞에 위치하는 프로덕션에서 활성화.
    oidc_issuer: str = "http://keycloak:8080/realms/dataplatform"
    oidc_strict: bool = False
    # 빈 문자열이면 audience 검사를 건너뛴다.
    # Keycloak 기본 audience인 'account'는 다루기 불편하므로 기본으로 비워 둔다.
    oidc_audience: str = ""
