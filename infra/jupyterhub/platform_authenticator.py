"""JupyterHub Authenticator that delegates to the platform backend.

The backend issues a short-lived ``platform_token`` after SSO at the gateway;
JupyterHub posts it here for verification.
"""

from __future__ import annotations

import os

import httpx
from jupyterhub.auth import Authenticator


class PlatformAuthenticator(Authenticator):
    async def authenticate(self, handler, data):  # noqa: ARG002
        token = data.get("platform_token")
        if not token:
            return None
        backend_url = os.environ.get("BACKEND_URL", "http://backend:8000")
        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.get(
                f"{backend_url}/api/auth/me",
                headers={"Authorization": f"Bearer {token}"},
            )
        if r.status_code != 200:
            return None
        return {"name": r.json().get("user_id"), "auth_state": {"token": token}}
