"""structlog 기반 구조화 JSON 로깅 (NFR-SL-OBS-02 / NFR-SEC-03).

상관관계 id(corr_id)를 ``ContextVar``에 보관하는 것이 핵심 설계다. ContextVar는
async 태스크 경계를 넘어 자동 상속되므로, 한 요청에서 파생된 모든 코루틴이
같은 corr_id를 본다(스레드별·태스크별 격리도 보장). ``_inject_corr_id``
프로세서가 매 로그 라인에 이 값을 자동으로 붙여, 호출부가 매번 corr_id를
직접 넘기지 않아도 로그 상관 추적이 된다.
"""

from __future__ import annotations

from contextvars import ContextVar
from typing import Any

import structlog

_corr_id_var: ContextVar[str | None] = ContextVar("corr_id", default=None)


# structlog 프로세서 시그니처(logger, method_name, event_dict)를 따른다.
# setdefault를 쓰는 이유: 호출부가 명시적으로 넘긴 corr_id가 있으면 덮어쓰지
# 않고 존중한다.
def _inject_corr_id(
    _logger: Any, _name: str, event_dict: dict[str, Any]
) -> dict[str, Any]:
    cid = _corr_id_var.get()
    if cid is not None:
        event_dict.setdefault("corr_id", cid)
    return event_dict


def configure_logging(level: str = "INFO") -> None:
    """멱등(idempotent) — 테스트에서 여러 번 호출해도 안전하다.

    프로세서 체인 순서가 의미를 가진다: contextvars 병합 → corr_id 주입 →
    레벨/타임스탬프 추가 → 예외 포맷 → 마지막에 JSON 직렬화. JSONRenderer를
    맨 끝에 두어 그 전까지 쌓인 필드를 한 줄 JSON으로 출력한다.
    """
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            _inject_corr_id,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(_level_to_int(level)),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def _level_to_int(level: str) -> int:
    # 표준 logging 레벨 이름("DEBUG" 등)을 정수로 변환. 알 수 없는 이름은
    # INFO로 폴백한다. logging은 함수 안에서 지연 import — 이 모듈은 표준
    # 로깅이 아닌 structlog를 쓰므로 상단 import를 피해 의존을 국소화한다.
    import logging

    return logging.getLevelNamesMapping().get(level.upper(), logging.INFO)


def bind_corr_id(corr_id: str) -> None:
    """현재 async / 스레드 컨텍스트에 상관관계 id를 바인딩한다.

    보통 요청 진입 미들웨어에서 한 번 호출하면, 이후 같은 컨텍스트에서 찍는
    모든 로그에 corr_id가 자동으로 따라붙는다.
    """
    _corr_id_var.set(corr_id)


def get_corr_id() -> str | None:
    return _corr_id_var.get()


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    return structlog.get_logger(name)
