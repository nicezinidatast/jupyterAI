"""Liveness·Readiness·Prometheus 메트릭 엔드포인트.

Kubernetes 또는 docker-compose 헬스체크가 이 경로를 주기적으로 호출한다.
세 엔드포인트를 하나의 라우터에 묶어 main.py에서 ``include_router`` 한 번으로 등록한다.
"""

from __future__ import annotations

from fastapi import APIRouter, Response

from dataplatform_shared.telemetry.metrics import metrics_endpoint

router = APIRouter()


@router.get("/healthz")
async def healthz() -> dict[str, str]:
    """Liveness 프로브 — 프로세스가 살아 있는지만 확인한다.

    DB·Redis 같은 외부 의존성은 검사하지 않는다.
    컨테이너 재시작 여부를 결정하는 가장 단순한 신호다.
    """
    return {"status": "ok"}


@router.get("/readyz")
async def readyz() -> dict[str, str]:
    """Readiness 프로브 — 트래픽을 받을 준비가 됐는지 알린다.

    실제 의존성 점검(Redis·backend ping)은 통합 테스트 스위트에서 수행한다.
    이 엔드포인트는 kubelet 프로브가 연달아 호출해도 부하가 없도록 최대한 가볍게 유지한다.
    """
    return {"status": "ready"}


@router.get("/metrics")
async def metrics() -> Response:
    """Prometheus 스크레이프 엔드포인트.

    ``metrics_endpoint()``가 Prometheus 텍스트 포맷으로 직렬화된 메트릭 본문과
    Content-Type을 반환하며, 그대로 응답에 실어 보낸다.
    """
    body, content_type = metrics_endpoint()
    return Response(content=body, media_type=content_type)
