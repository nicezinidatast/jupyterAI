# data-unit — NFR Requirements

| ID | 요구사항 |
|---|---|
| NFR-DU-PERF-01 | 5초 임계 → 백그라운드 잡 승격 자동 | 동기 쿼리는 5s deadline 강제 |
| NFR-DU-PERF-02 | 단일 결과 한도 | ≤ 10GB 또는 1억 행, 초과 시 거절 |
| NFR-DU-PERF-03 | 페이지네이션 100/page | 첫 페이지 < 1s |
| NFR-DU-PERF-04 | 동시 활성 쿼리 | 사용자당 5개, 부서 총 50개 |
| NFR-DU-PERF-05 | 파일 업로드 | 단일 ≤ 1GB, 1GB 업로드 < 60s (사내 LAN) |
| NFR-DU-SEC-01 (SECURITY-05) | 파라미터화 쿼리 강제 | runtime 검증 + lint |
| NFR-DU-SEC-02 (SECURITY-13) | 안전한 파일 파싱 | pandas + pyarrow (안전), pickle 거절 |
| NFR-DU-SEC-03 | 마운트 sandbox 외 경로 거절 | path 정규화 + prefix 검사 |
| NFR-DU-SEC-04 | PII 마스킹 우회 불가 | 모든 결과 응답은 mask() 통과 |
| NFR-DU-AUDIT-01 | 쿼리 실행/파일 업로드/스키마 조회 감사 | shared-lib emitter |
| NFR-DU-OBS-01 | 메트릭: query_total, query_latency, rows_returned histogram, background_jobs gauge | Prometheus |

## 기술 스택

| 항목 | 결정 |
|---|---|
| Web Framework | FastAPI |
| ORM | SQLAlchemy 2 + asyncpg (메타 DB) |
| RDBMS Drivers | `psycopg[binary] >= 3` (Postgres), `pymysql` (MySQL), `oracledb` (Oracle, thin mode), `pymssql` 또는 `pyodbc + freetds` (MSSQL) |
| Big-Data SQL | `pyhive` (Hive/Presto/Trino) — Kerberos 옵션, `impyla` (Impala) |
| Kerberos | `gssapi` + `requests-kerberos` |
| File parsing | `pandas >= 2.2`, `pyarrow >= 15`, `openpyxl` (Excel) |
| Object Storage | `s3fs` (MinIO 호환) |
| Redis (jobs) | redis-py async |
| Regex | `regex` (PyPI, RE2-like timeouts) — 마스킹 정규식 안전성 |
| Result cache | Redis (1MB 미만) + 디스크 (큰 결과는 임시 parquet) |

## 호환성
- Postgres 12+, MySQL 5.7+, Oracle 19c+, MSSQL 2019+
- Hive 3+, Impala 3.4+, Presto 0.275+, Trino 400+
