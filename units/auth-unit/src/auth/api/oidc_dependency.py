"""FastAPI dependency that resolves the authenticated user.

Two modes are supported by a single dependency:

* **Demo mode** (``settings.oidc_enabled=False``) — falls back to the
  ``X-User-Email`` header (set in dev/test) or the seeded admin user. This
  preserves the historic behaviour so the SPA bring-up does not require
  Keycloak.
* **OIDC mode** (``settings.oidc_enabled=True``) — requires a Bearer token
  in the ``Authorization`` header. The token is verified against the Keycloak
  JWKS using RS256, the issuer claim is checked against
  ``settings.oidc_issuer`` and the resolved identity carries the email +
  realm-roles from the token claims.

Only the four canonical platform roles (Admin / Analyst / Auditor / Viewer)
are propagated; any other realm-roles in the token are discarded so that
Keycloak-side typos cannot widen access.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated

import jwt
from fastapi import Depends, Header, HTTPException, Request, status
from jwt import PyJWKClient

_PLATFORM_ROLES = frozenset({"Admin", "Analyst", "Auditor", "Viewer"})


@dataclass(frozen=True, slots=True)
class AuthIdentity:
    """Resolved request identity. ``source`` is informational only."""

    email: str
    roles: tuple[str, ...]
    source: str  # "oidc" | "demo-header" | "demo-default"


class OidcVerifier:
    """Thin wrapper around ``PyJWKClient`` that caches the signing keys.

    ``verify`` raises :class:`jwt.PyJWTError` on any validation failure; the
    dependency turns that into a 401 with a generic body to avoid leaking
    the specific failure reason to clients (SECURITY-09).
    """

    def __init__(self, *, issuer: str, audience: str | None = None) -> None:
        self.issuer = issuer.rstrip("/")
        self.audience = audience or None
        # ``cache_keys=True`` (default) caches by kid so subsequent verifies are
        # in-memory after the first JWKS GET.
        self._jwks = PyJWKClient(
            f"{self.issuer}/protocol/openid-connect/certs",
            cache_keys=True,
        )

    def verify(self, token: str) -> dict[str, object]:
        signing_key = self._jwks.get_signing_key_from_jwt(token).key
        return jwt.decode(
            token,
            signing_key,
            algorithms=["RS256"],
            issuer=self.issuer,
            audience=self.audience,
            options={
                "verify_aud": self.audience is not None,
                "require": ["iss", "exp"],
            },
        )


def _roles_from_claims(claims: dict[str, object]) -> tuple[str, ...]:
    realm_access = claims.get("realm_access") or {}
    if not isinstance(realm_access, dict):
        return ()
    roles = realm_access.get("roles") or []
    if not isinstance(roles, list):
        return ()
    return tuple(sorted(r for r in roles if isinstance(r, str) and r in _PLATFORM_ROLES))


def _demo_identity(x_user_email: str | None) -> AuthIdentity:
    if x_user_email:
        return AuthIdentity(email=x_user_email, roles=(), source="demo-header")
    return AuthIdentity(email="admin@example.test", roles=(), source="demo-default")


async def get_current_identity(
    request: Request,
    authorization: Annotated[str | None, Header(alias="Authorization")] = None,
    x_user_email: Annotated[str | None, Header(alias="X-User-Email")] = None,
) -> AuthIdentity:
    """Resolve the active identity for this request.

    Hybrid policy (driven by ``request.app.state.oidc_verifier`` and
    ``oidc_strict``):

    * Bearer token present → must verify, even when not strict. A bad token
      is never silently downgraded to demo mode (SECURITY-09).
    * No token + strict → 401.
    * No token + not strict → demo fallback (header or seeded admin).
    """
    verifier: OidcVerifier | None = getattr(request.app.state, "oidc_verifier", None)
    strict: bool = bool(getattr(request.app.state, "oidc_strict", False))
    has_bearer = bool(authorization and authorization.lower().startswith("bearer "))

    if has_bearer and verifier is not None:
        token = authorization.split(" ", 1)[1].strip()
        try:
            claims = verifier.verify(token)
        except jwt.PyJWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="invalid token",
                headers={"WWW-Authenticate": 'Bearer realm="dataplatform"'},
            ) from None
        email = claims.get("email") or claims.get("preferred_username")
        if not isinstance(email, str) or "@" not in email:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="token missing email claim",
            )
        return AuthIdentity(email=email, roles=_roles_from_claims(claims), source="oidc")

    if strict:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="missing bearer token",
            headers={"WWW-Authenticate": 'Bearer realm="dataplatform"'},
        )
    return _demo_identity(x_user_email)


CurrentIdentity = Annotated[AuthIdentity, Depends(get_current_identity)]
