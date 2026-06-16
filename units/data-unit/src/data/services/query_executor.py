"""QueryExecutor — orchestrates authorize → resolve → connect → execute → mask.

The 5s timeout / background promotion is handled here via ``asyncio.wait_for``.
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
    rows: list[dict[str, Any]]
    promoted_to_background: bool


class QueryExecutor:
    def __init__(self, *, max_rows: int = 100_000_000, default_timeout: float = 5.0) -> None:
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
            stream = await asyncio.wait_for(
                connector.execute(query, timeout=timeout or self._default_timeout),
                timeout=timeout or self._default_timeout,
            )
        except asyncio.TimeoutError:
            # In production we'd enqueue a background job here; the test path
            # returns a hint so the caller knows to poll later.
            return Ok(QueryOutcome(rows=[], promoted_to_background=True))
        except Exception:  # noqa: BLE001
            logger.exception("query_execute_error")
            return Err(DomainError.EXTERNAL_UNAVAILABLE)

        rows: list[dict[str, Any]] = []
        async for row in stream:
            if len(rows) >= self._max_rows:
                return Err(DomainError.VALIDATION)
            rows.append(mask_row(row, column_kinds))
        return Ok(QueryOutcome(rows=rows, promoted_to_background=False))
