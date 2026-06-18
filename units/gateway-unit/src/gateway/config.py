"""게이트웨이 환경 변수 기반 설정 (12-factor 앱 원칙).

모든 설정값은 ``GATEWAY_`` 접두어가 붙은 환경 변수로 주입된다.
기본값은 docker-compose 내부망 서비스명을 가리키므로
별도 설정 없이 compose up만으로 로컬 개발이 가능하다.
"""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class GatewaySettings(BaseSettings):
    """게이트웨이 전역 설정 컨테이너.

    pydantic-settings가 환경 변수 → 필드 바인딩·타입 변환을 담당하므로
    코드에서 ``os.environ``을 직접 참조하지 않는다.
    ``extra="ignore"``로 정의되지 않은 환경 변수는 자동으로 무시한다.
    """

    model_config = SettingsConfigDict(env_prefix="GATEWAY_", env_file=".env", extra="ignore")

    # 내부망 백엔드 서비스 주소. compose 환경에서는 서비스명 DNS가 해석된다.
    backend_url: str = "http://backend:8000"
    # 레이트 리밋 슬라이딩 윈도우 카운터와 세션 TTL 저장소로 사용하는 Redis.
    redis_url: str = "redis://redis:6379/0"
    # OIDC(OpenID Connect) 발급자 URL — Keycloak 렐름의 Well-Known 엔드포인트 기준.
    keycloak_issuer: str = "https://sso.internal/realms/dataplatform"
    keycloak_client_id: str = "dataplatform"
    keycloak_client_secret: str = ""  # Docker secrets에서 런타임 주입; 소스에 하드코딩 금지
    log_level: str = "INFO"
    # OTLP(OpenTelemetry Protocol) 수집기 엔드포인트. 빈 문자열이면 트레이싱 비활성.
    otlp_endpoint: str = ""

    # --- 레이트 리밋 (분당 최대 요청 수) ---
    # IP 기반 제한: DDoS·스캐닝 차단. 인증 여부와 무관하게 적용.
    rate_limit_per_ip_minute: int = 200
    # 인증된 사용자별 제한: 대량 자동화 요청 억제. X-Auth-User 헤더 기준.
    rate_limit_per_user_minute: int = 300
    # 미인증(익명) 요청 제한: 인증 없는 공개 경로(healthz 등)에 보수적 상한 적용.
    rate_limit_per_anon_minute: int = 60

    # --- 세션 ---
    # 세션 유효 기간(초). 기본 8시간 — 업무 시간대 재로그인 불필요.
    session_ttl_seconds: int = 28800
