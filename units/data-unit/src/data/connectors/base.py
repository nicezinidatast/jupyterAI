"""커넥터 프로토콜 — 모든 드라이버가 따라야 할 계약(contract).

DB 엔진(Postgres·MySQL·…)마다 드라이버 API가 제각각이지만, 상위 계층
(QueryExecutor·router)은 엔진을 몰라도 동작해야 한다. 그래서 구조적 타이핑인
``Protocol``로 최소 표면(execute/introspect/close)만 고정하고, 각 구현체가
이 모양에 자신을 맞춘다(상속이 아니라 덕 타이핑). 새 엔진을 붙일 때 이
세 메서드만 지키면 팩토리가 그대로 끼워 넣을 수 있다는 것이 핵심 불변식이다.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any, Protocol

from data.schemas import ParamQuery


class ResultStream(Protocol):
    """결과 행을 비동기로 흘려보내는 스트림 계약.

    전체 결과를 한 번에 메모리로 올리지 않고 ``async for``로 한 행씩 소비할 수
    있게 하기 위한 추상화. 구현체는 ``__aiter__``만 제공하면 된다.
    """

    async def __aiter__(self) -> AsyncIterator[dict[str, Any]]: ...


class Connector(Protocol):
    """DB 접속·질의·내부 구조 조회를 추상화한 커넥터 계약.

    구현체가 반드시 지켜야 할 약속:
    - ``execute``: 파라미터 바인딩된 ``ParamQuery``만 받는다(문자열 보간 금지).
      ``timeout`` 안에 결과를 못 내면 시간 초과로 끝나야 한다.
    - ``introspect``: information_schema 등을 읽어 테이블/컬럼 메타를 반환한다.
    - ``close``: 점유한 커넥션·리소스를 반드시 정리한다.
    """

    async def execute(self, query: ParamQuery, *, timeout: float = 5.0) -> ResultStream: ...
    async def introspect(self, schema: str | None = None) -> dict[str, Any]: ...
    async def close(self) -> None: ...
