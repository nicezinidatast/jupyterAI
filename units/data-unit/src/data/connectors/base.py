"""Connector Protocol — drivers must adapt to this contract."""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any, Protocol

from data.schemas import ParamQuery


class ResultStream(Protocol):
    async def __aiter__(self) -> AsyncIterator[dict[str, Any]]: ...


class Connector(Protocol):
    async def execute(self, query: ParamQuery, *, timeout: float = 5.0) -> ResultStream: ...
    async def introspect(self, schema: str | None = None) -> dict[str, Any]: ...
    async def close(self) -> None: ...
