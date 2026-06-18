"""QueryExecutor — 인가 → 자격증명 해석 → 접속 → 실행 → 마스킹의 흐름을 조율한다.

5초 타임아웃과 "백그라운드 승격(promotion)"을 ``asyncio.wait_for``로 이 계층에서
처리한다. 즉 동기 응답이 너무 오래 걸리면 결과를 비우고 백그라운드 작업으로
넘겼다는 힌트를 돌려, SPA가 매달리지 않고 나중에 폴링하도록 한다.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any

from dataplatform_shared.errors import DomainError
from dataplatform_shared.result import Err, Ok, Result
from dataplatform_shared.telemetry import get_logger

from data.connectors.base import Connector
from data.schemas import ParamQuery
from data.services.pii_masking import mask_row

logger = get_logger("data.query_executor")


@dataclass(frozen=True, slots=True)
class QueryOutcome:
    # 실행 결과. ``promoted_to_background``가 True면 타임아웃으로 백그라운드
    # 작업으로 넘어갔다는 뜻이며, 이때 ``rows``는 비어 있다(나중에 폴링해야 함).
    rows: list[dict[str, Any]]
    promoted_to_background: bool


class QueryExecutor:
    def __init__(self, *, max_rows: int = 100_000_000, default_timeout: float = 5.0) -> None:
        # max_rows: 결과를 메모리에 쌓는 상한(폭주 쿼리로부터 서버 보호).
        # default_timeout: 호출별 timeout이 없을 때 적용할 기본 한도(초).
        self._max_rows = max_rows
        self._default_timeout = default_timeout

    async def run(
        self,
        connector: Connector,
        query: ParamQuery,
        column_kinds: dict[str, str | None],
        *,
        timeout: float | None = None,
    ) -> Result[QueryOutcome, DomainError]:
        try:
            # 커넥터 내부에도 timeout이 있지만, 바깥 wait_for로 한 번 더 감싼다.
            # 드라이버가 자체 타임아웃을 지키지 않더라도 상위에서 강제로 끊기 위함.
            stream = await asyncio.wait_for(
                connector.execute(query, timeout=timeout or self._default_timeout),
                timeout=timeout or self._default_timeout,
            )
        except asyncio.TimeoutError:
            # 운영에서는 여기서 백그라운드 작업으로 큐잉한다. 테스트 경로는
            # 호출부가 나중에 폴링하도록 승격 힌트(promoted_to_background)만 돌려준다.
            return Ok(QueryOutcome(rows=[], promoted_to_background=True))
        except Exception:  # noqa: BLE001
            # 드라이버 예외는 내부 사정이므로 상세를 로그에만 남기고, 외부에는
            # 일반화된 EXTERNAL_UNAVAILABLE만 노출한다(정보 누설 방지).
            logger.exception("query_execute_error")
            return Err(DomainError.EXTERNAL_UNAVAILABLE)

        rows: list[dict[str, Any]] = []
        async for row in stream:
            # 상한을 넘기면 메모리 폭주를 막기 위해 즉시 중단·거절한다.
            if len(rows) >= self._max_rows:
                return Err(DomainError.VALIDATION)
            # 서버를 떠나기 전에 행마다 PII 마스킹을 적용한다(누출 차단의 마지막 관문).
            rows.append(mask_row(row, column_kinds))
        return Ok(QueryOutcome(rows=rows, promoted_to_background=False))
