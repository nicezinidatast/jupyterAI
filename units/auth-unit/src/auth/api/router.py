"""auth-unit public API.

The session/login endpoints live in :mod:`auth.api.login_router`; this module
re-exports a single ``router`` (mounted by ``backend.main``) that includes
them, plus the profile endpoint.

Identity is resolved through :func:`auth.api.oidc_dependency.get_current_identity`
which resolves, in order:

* the **``dp_session`` httpOnly cookie** → a server-side session row (primary
  path once a user has logged in / verified);
* an OIDC Bearer token (when Keycloak is wired in); and
* the demo fallback (``X-User-Email`` header or seeded admin) for bring-up.
"""

from __future__ import annotations

from fastapi import APIRouter

from auth.api.login_router import router as login_router

router = APIRouter(prefix="/api/auth", tags=["auth"])

# Mount signup/login/logout/me/check.
router.include_router(login_router)
