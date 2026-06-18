"""``ConnectionSpec``를 보고 알맞은 ``Connector`` 구현체로 분기하는 팩토리.

엔진 선택 분기를 한 곳에 모아, 호출부가 ``if engine == ...`` 같은 조건을
중복하지 않도록 한다. 팩토리는 두 개의 진입점을 둔다:

* ``create_connector(spec, secret)`` — 과거 Secret 기반 경로. 기존 테스트와의
  하위 호환을 위해 골격(skeleton)인 ``RdbmsConnector``를 돌려준다.
* ``open_runtime_connector(spec, username, password)`` — 운영 경로. data-unit
  쿼리 실행기와 관리자의 "연결 테스트" 프로브가 쓴다. 엔진별 *실제* 커넥터
  (Postgres=asyncpg, MySQL=aiomysql)를 반환한다.

MVP 지원 범위를 벗어난 엔진은 ``DomainError.VALIDATION``으로 거절한다. 잘못된
엔진을 조용히 통과시키지 않고 명시적 실패로 막는 것이 의도다.
"""

from __future__ import annotations

from dataplatform_shared.errors import DomainError
from dataplatform_shared.result import Err, Ok, Result
from dataplatform_shared.security.secret import Secret

from data.connectors.base import Connector
from data.connectors.mysql import MysqlConnector
from data.connectors.postgres import PostgresConnector
from data.connectors.rdbms import RdbmsConnector
from data.schemas import ConnectionSpec


def create_connector(spec: ConnectionSpec, secret: Secret) -> Result[Connector, DomainError]:
    # RDBMS 계열은 공통 골격 커넥터로 처리. 빅데이터 엔진(Hive 등)은
    # connectors/bigdata.py에 별도로 두며 MVP에는 아직 연결돼 있지 않다.
    if spec.engine in ("postgres", "mysql", "oracle", "mssql"):
        return Ok(RdbmsConnector(spec, secret))
    return Err(DomainError.VALIDATION)


def open_runtime_connector(
    spec: ConnectionSpec, *, username: str, password: str
) -> Result[Connector, DomainError]:
    # 이번 라운드에서 실제 드라이버가 연결된 엔진만 운영 커넥터를 만든다.
    # 그 외(Oracle / MSSQL / Hive / Impala / Presto / Trino)는 범위 밖이라
    # VALIDATION으로 거절해, 자격증명을 들고 미지원 엔진에 붙는 일을 막는다.
    if spec.engine == "postgres":
        return Ok(PostgresConnector(spec, username=username, password=password))
    if spec.engine == "mysql":
        return Ok(MysqlConnector(spec, username=username, password=password))
    return Err(DomainError.VALIDATION)
