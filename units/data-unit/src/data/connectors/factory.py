"""Dispatch a ConnectionSpec to the right Connector implementation.

The factory has two surfaces:

* ``create_connector(spec, secret)`` — historic Secret-based path. Returns the
  skeleton ``RdbmsConnector`` for backward compatibility with existing tests.
* ``open_runtime_connector(spec, username, password)`` — production path used by
  the data-unit query executor and admin "test connection" probe. Returns a
  *real* engine-specific connector (asyncpg for Postgres, aiomysql for MySQL).
  Engines outside the MVP set raise ``DomainError.VALIDATION``.
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
    if spec.engine in ("postgres", "mysql", "oracle", "mssql"):
        return Ok(RdbmsConnector(spec, secret))
    # Big-data engines live in connectors/bigdata.py — skeleton not wired into MVP.
    return Err(DomainError.VALIDATION)


def open_runtime_connector(
    spec: ConnectionSpec, *, username: str, password: str
) -> Result[Connector, DomainError]:
    if spec.engine == "postgres":
        return Ok(PostgresConnector(spec, username=username, password=password))
    if spec.engine == "mysql":
        return Ok(MysqlConnector(spec, username=username, password=password))
    # Oracle / MSSQL / Hive / Impala / Presto / Trino : out of scope for this round.
    return Err(DomainError.VALIDATION)
