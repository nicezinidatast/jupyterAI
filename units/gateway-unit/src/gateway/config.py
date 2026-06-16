"""Gateway configuration via env vars (12-factor)."""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class GatewaySettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="GATEWAY_", env_file=".env", extra="ignore")

    backend_url: str = "http://backend:8000"
    redis_url: str = "redis://redis:6379/0"
    keycloak_issuer: str = "https://sso.internal/realms/dataplatform"
    keycloak_client_id: str = "dataplatform"
    keycloak_client_secret: str = ""  # injected from Docker secrets
    log_level: str = "INFO"
    otlp_endpoint: str = ""
    # Rate limits
    rate_limit_per_ip_minute: int = 200
    rate_limit_per_user_minute: int = 300
    rate_limit_per_anon_minute: int = 60
    # Session
    session_ttl_seconds: int = 28800
