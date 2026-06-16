"""Anti-corruption layer around Keycloak's OIDC endpoints."""

from __future__ import annotations

from dataclasses import dataclass

import httpx

from dataplatform_shared.errors import DomainError
from dataplatform_shared.result import Err, Ok, Result
from dataplatform_shared.security.secret import Secret


@dataclass(frozen=True, slots=True)
class KeycloakTokens:
    access_token: Secret
    refresh_token: Secret
    id_token: Secret
    expires_in: int


class KeycloakAdapter:
    """Talks HTTP/JSON to Keycloak; ``httpx.AsyncClient`` is injected for tests.

    All errors are flattened to DomainError so callers never see Keycloak-shaped
    exceptions leak past the adapter boundary (Q-AD-10=A).
    """

    def __init__(
        self,
        *,
        issuer: str,
        client_id: str,
        client_secret: Secret,
        http: httpx.AsyncClient,
    ) -> None:
        self._issuer = issuer.rstrip("/")
        self._client_id = client_id
        self._client_secret = client_secret
        self._http = http

    async def exchange_auth_code(
        self, code: str, redirect_uri: str
    ) -> Result[KeycloakTokens, DomainError]:
        try:
            r = await self._http.post(
                f"{self._issuer}/protocol/openid-connect/token",
                data={
                    "grant_type": "authorization_code",
                    "code": code,
                    "redirect_uri": redirect_uri,
                    "client_id": self._client_id,
                    "client_secret": self._client_secret.reveal(),
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                timeout=10.0,
            )
        except httpx.HTTPError:
            return Err(DomainError.EXTERNAL_UNAVAILABLE)
        if r.status_code == 400:
            return Err(DomainError.VALIDATION)
        if r.status_code >= 500:
            return Err(DomainError.EXTERNAL_UNAVAILABLE)
        if r.status_code != 200:
            return Err(DomainError.UNAUTHORIZED)
        data = r.json()
        return Ok(
            KeycloakTokens(
                access_token=Secret(data["access_token"]),
                refresh_token=Secret(data.get("refresh_token", "")),
                id_token=Secret(data["id_token"]),
                expires_in=int(data.get("expires_in", 3600)),
            )
        )

    async def introspect(self, token: str) -> Result[dict, DomainError]:
        try:
            r = await self._http.post(
                f"{self._issuer}/protocol/openid-connect/token/introspect",
                data={
                    "token": token,
                    "client_id": self._client_id,
                    "client_secret": self._client_secret.reveal(),
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                timeout=5.0,
            )
        except httpx.HTTPError:
            return Err(DomainError.EXTERNAL_UNAVAILABLE)
        if r.status_code != 200:
            return Err(DomainError.UNAUTHORIZED)
        body = r.json()
        if not body.get("active"):
            return Err(DomainError.EXPIRED)
        return Ok(body)
