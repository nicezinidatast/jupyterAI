"""OIDC callback handler skeleton — full token exchange happens in auth-unit."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from dataplatform_shared.telemetry import get_logger

router = APIRouter(prefix="/oidc")
logger = get_logger("gateway.oidc")


@router.get("/callback")
async def callback(request: Request, code: str | None = None, state: str | None = None) -> dict[str, str]:
    """Receive the OIDC authorization code and hand it off to auth-unit.

    In MVP this proxies to ``${BACKEND_URL}/api/auth/callback``; the integration
    test asserts the redirect lifecycle end-to-end. We deliberately keep the
    gateway side thin so the security-critical token exchange stays in one
    place (auth-unit).
    """
    if not code or not state:
        # Don't leak which one was missing — generalised message (SECURITY-09).
        raise HTTPException(status_code=400, detail="invalid_request")
    logger.info("oidc_callback_received", state=state)
    # Defer to auth-unit — implementation will issue session + redirect in §US-CODE-07.
    return {"received": "ok", "next": "auth-unit/exchange"}
