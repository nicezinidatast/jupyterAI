"""표준 ``DomainEvent`` 봉투(envelope) 정의.

생산자(producer)는 payload를 JSON 직렬화 가능한 매핑으로 채운다. 이 payload에는
``Secret`` 값이 절대 들어가면 안 된다 — 감사 로그는 영속·외부 공유될 수 있어
비밀값이 새면 치명적이기 때문. :func:`make_event`의 런타임 가드가 이 불변식을
강제하므로, 실수로 비밀값을 넣으면 이벤트 생성 시점에 바로 실패한다.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Literal, TypedDict

from dataplatform_shared.security.secret import Secret
from dataplatform_shared.types.common import CorrelationId, UserId

EventResult = Literal["success", "failure"]


class DomainEvent(TypedDict):
    """감사 가능한 이벤트의 표준 봉투.

    TypedDict로 정의한 이유: 직렬화·DB 저장·큐 전송에 그대로 쓰이는 평범한
    dict이면서도, 키 구성을 타입으로 고정해 생산자 간 형식 불일치를 막는다.
    ``at``은 datetime 객체가 아니라 ISO-8601 UTC 문자열로 둔다 — DB 계층·큐
    페이로드 어디로 넘겨도 깨지지 않는 이식성(portability)을 위함.
    """

    type: str
    actor: str
    resource: str | None
    result: EventResult
    at: str
    corr_id: str
    payload: dict[str, Any]


def _scrub_payload(payload: dict[str, Any], path: str = "") -> None:
    """payload 트리 어디에 있든 Secret 값을 거부한다.

    중첩 dict까지 재귀로 훑으며, 누출 위치를 ``path``로 추적해 에러 메시지에
    담는다 — 디버깅 때 "어느 키에 비밀값이 들어갔는지" 바로 알 수 있게.
    """
    for key, value in payload.items():
        if isinstance(value, Secret):
            raise ValueError(f"DomainEvent payload contains Secret at {path}/{key}")
        if isinstance(value, dict):
            _scrub_payload(value, f"{path}/{key}")


def make_event(
    *,
    type: str,
    actor: UserId | str,
    result: EventResult,
    corr_id: CorrelationId | str,
    resource: str | None = None,
    payload: dict[str, Any] | None = None,
    at: datetime | None = None,
) -> DomainEvent:
    """검증을 거친 DomainEvent를 만드는 유일한 진입점(팩토리).

    모든 인자를 키워드 전용(keyword-only, ``*``)으로 받아 호출부 가독성과
    인자 순서 실수 방지를 높였다. ``dict(payload or {})``로 방어적 복사를 해,
    원본 payload가 나중에 바뀌어도 이벤트 내용이 흔들리지 않게 한다(불변성).
    복사본에 대해 Secret 스크럽을 돌린 뒤에야 봉투를 조립한다 — 즉 검증을
    통과하지 못하면 이벤트 자체가 만들어지지 않는다.
    """
    safe_payload = dict(payload or {})
    _scrub_payload(safe_payload)
    return DomainEvent(
        type=type,
        actor=str(actor),
        resource=resource,
        result=result,
        at=(at or datetime.now(UTC)).isoformat(),
        corr_id=str(corr_id),
        payload=safe_payload,
    )
