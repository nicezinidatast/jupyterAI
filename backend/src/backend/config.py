from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class BackendSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="BACKEND_", env_file=".env", extra="ignore")

    database_url: str = "postgresql+asyncpg://postgres:postgres@postgres:5432/dataplatform"
    redis_url: str = "redis://redis:6379/0"
    log_level: str = "INFO"
    otlp_endpoint: str = ""
    # 32-byte url-safe base64 Fernet key. If empty at startup the backend
    # generates a key for this run only (acceptable for the in-network demo).
    # Production deployments inject a stable key via secrets manager.
    credential_key: str = ""

    # OIDC / Keycloak. Hybrid behaviour:
    #   * ``oidc_issuer`` empty → no verifier; identity comes from
    #     ``X-User-Email`` header or the seeded admin (demo mode).
    #   * ``oidc_issuer`` set → verifier built lazily; when a request brings a
    #     Bearer token it is verified against Keycloak's JWKS and the token
    #     wins. Requests *without* a token still fall through to demo mode
    #     unless ``oidc_strict`` is true.
    #   * ``oidc_strict`` true → Bearer token becomes mandatory. Production
    #     enables this once the gateway is in front of every request.
    oidc_issuer: str = "http://keycloak:8080/realms/dataplatform"
    oidc_strict: bool = False
    oidc_audience: str = ""  # empty = skip audience check (Keycloak default `account` aud is awkward)
