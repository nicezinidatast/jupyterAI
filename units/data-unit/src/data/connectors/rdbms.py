"""RDBMS 커넥터 골격(skeleton).

실제 드라이버 연결(asyncpg, pymysql, oracledb, pymssql)은 통합 단계에서 붙인다.
이 골격은 표면을 최소로 유지해, 아래의 인메모리 가짜(fake) 스트림만으로도
``DataAccessService``를 끝에서 끝까지(end-to-end) 굴려볼 수 있게 한다. 운영
경로는 이 골격 대신 postgres.py / mysql.py의 실 커넥터를 쓴다.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

from dataplatform_shared.security.secret import Secret

from data.connectors.base import Connector, ResultStream
from data.schemas import ConnectionSpec, ParamQuery


class _ListResultStream:
    # 미리 준비한 행 목록을 ``ResultStream`` 프로토콜 모양으로 감싸는 어댑터.
    # 실제 DB 커서 없이도 상위 계층이 ``async for``로 소비할 수 있게 한다.
    def __init__(self, rows: list[dict[str, Any]]) -> None:
        self._rows = rows

    async def __aiter__(self) -> AsyncIterator[dict[str, Any]]:
        for row in self._rows:
            yield row


class RdbmsConnector(Connector):
    """골격 커넥터. 테스트는 ``_canned_rows``를 주입해 결정적(deterministic) 실행을 얻는다."""

    def __init__(self, spec: ConnectionSpec, secret: Secret) -> None:
        self._spec = spec
        self._secret = secret  # 실제 드라이버 연결 시 자격증명 복호화에 사용된다
        self._canned_rows: list[dict[str, Any]] = []

    def set_canned_rows(self, rows: list[dict[str, Any]]) -> None:
        """테스트용 후크 — 운영 코드는 대신 실제 드라이버를 호출한다."""
        self._canned_rows = rows

    async def execute(self, query: ParamQuery, *, timeout: float = 5.0) -> ResultStream:
        # 실제 구현: 엔진에 맞는 드라이버를 고르고 ``self._secret.reveal()``로
        # 커넥션을 연 뒤, paramstyle에 맞춰 cursor.execute를 호출한다.
        # ``timeout``은 운영에서 드라이버별 kwargs로 전달된다.
        del query, timeout  # 골격에서는 입력을 쓰지 않음을 명시(linter 경고 억제)
        return _ListResultStream(list(self._canned_rows))

    async def introspect(self, schema: str | None = None) -> dict[str, Any]:
        del schema
        return {"tables": []}

    async def close(self) -> None:
        # 실제 구현은 여기서 하위 커넥션을 닫는다.
        return None
