# data-unit — Code Generation Plan

**실제 코드 위치**: `units/data-unit/`

## Plan
- [ ] `pyproject.toml` (대량 deps: fastapi, sqlalchemy[asyncio], asyncpg, psycopg, pymysql, oracledb, pymssql, pyhive[all], impyla, gssapi, pandas, pyarrow, openpyxl, s3fs, redis, regex, dataplatform-shared)
- [ ] `requirements.lock`
- [ ] `migrations/0001_data_tables.py`
- [ ] `src/data/models.py`
- [ ] `src/data/schemas.py` (ParamQuery validator 포함)
- [ ] `src/data/repositories/connections.py`
- [ ] `src/data/repositories/grants.py`
- [ ] `src/data/repositories/pii.py`
- [ ] `src/data/repositories/executions.py`
- [ ] `src/data/connectors/base.py` (Connector protocol)
- [ ] `src/data/connectors/factory.py`
- [ ] `src/data/connectors/rdbms.py` (Postgres/MySQL/Oracle/MSSQL)
- [ ] `src/data/connectors/bigdata.py` (Hive/Impala/Presto/Trino + Kerberos)
- [ ] `src/data/services/query_executor.py`
- [ ] `src/data/services/schema_introspector.py`
- [ ] `src/data/services/pii_masking.py`
- [ ] `src/data/services/data_access_service.py` (얇은 서비스 — 시나리오 A 흐름)
- [ ] `src/data/services/file_upload.py`
- [ ] `src/data/jobs/background_worker.py`
- [ ] `src/data/cache.py` (ResultCache)
- [ ] `src/data/storage/nas.py`
- [ ] `src/data/storage/minio.py`
- [ ] `src/data/api/router.py` (`/api/connections`, `/api/queries`, `/api/files`, `/api/schemas`)
- [ ] `src/data/main.py`
- [ ] `tests/test_connection_registry.py` (PBT — Idempotent + RBAC Invariant)
- [ ] `tests/test_pii_masking.py` (PBT — Oracle + Idempotent + Domain-Generator)
- [ ] `tests/test_query_executor.py` (5s 임계 시뮬레이션, PBT)
- [ ] `tests/test_file_upload_roundtrip.py` (PBT — Round-trip)
- [ ] `tests/test_param_query_safety.py` (인젝션 시도 차단)
- [ ] `tests/test_schema_introspect_rbac.py`
- [ ] `tests/integration/test_end_to_end_query.py` (실제 Postgres 컨테이너 fixture)
- [ ] `tests/integration/test_hive_kerberos.py` (옵셔널)
- [ ] `.gitlab-ci.yml`

## Definition of Done
- coverage ≥ 80% (대용량 유닛 — Connectors 별로 별도 카운트)
- PBT 5종 통과
- 50명 동시 시뮬레이션 (Locust) → p95 < 2s (단순 쿼리 가정)
- 인젝션 시도가 모두 422로 차단
- 마스킹된 결과에서 원본 PII 패턴이 정규식으로 찾아지지 않음

## 비고
- data-unit은 가장 큰 유닛 — 내부적으로 src 트리 안에서 도메인 모듈 분리(connectors/, services/, repositories/)
- Phase 2 외부 DW(ClickHouse, Snowflake, BigQuery)는 `phase2-incubation/dw-connector` 로 격리
