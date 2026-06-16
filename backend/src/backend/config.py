from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class BackendSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="BACKEND_", env_file=".env", extra="ignore")

    # Application data store. Defaults to a local SQLite file (no external
    # Postgres needed for app data). The parent directory is created at
    # startup if missing. Override with BACKEND_DATABASE_URL to point at
    # Postgres (e.g. postgresql+asyncpg://...) in environments that prefer it.
    database_url: str = "sqlite+aiosqlite:///./data/platform.db"
    redis_url: str = "redis://redis:6379/0"
    log_level: str = "INFO"
    otlp_endpoint: str = ""

    # Browser session cookie hardening. SameSite=Lax + HttpOnly are always on;
    # Secure is gated behind this flag so the internal-http demo works without
    # TLS. Production behind HTTPS should set BACKEND_COOKIE_SECURE=true.
    cookie_secure: bool = False

    # Demo seed master switch. When false (default) the startup path bootstraps
    # ONLY the real admin account; all other demo rows are skipped. Set
    # BACKEND_SEED_DEMO=true to repopulate the showcase fixtures.
    seed_demo: bool = False
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
