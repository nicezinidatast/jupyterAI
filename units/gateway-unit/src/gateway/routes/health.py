"""Liveness + readiness + Prometheus metrics endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Response

from dataplatform_shared.telemetry.metrics import metrics_endpoint

router = APIRouter()


@router.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/readyz")
async def readyz() -> dict[str, str]:
    # Real readiness checks (Redis/backend ping) live in the integration suite;
    # this endpoint stays cheap so kubelet probes don't fan-out.
    return {"status": "ready"}


@router.get("/metrics")
async def metrics() -> Response:
    body, content_type = metrics_endpoint()
    return Response(content=body, media_type=content_type)
