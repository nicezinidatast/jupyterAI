# audit-unit — NFR Requirements

| ID | 요구사항 |
|---|---|
| NFR-AD-PERF-01 | outbox emit (same tx) 오버헤드 | < 2ms |
| NFR-AD-PERF-02 | consumer 처리량 | ≥ 1000 events/s (peak) |
| NFR-AD-PERF-03 | search 응답 (≤ 100 rows) | < 500ms |
| NFR-AD-SEC-01 (SECURITY-14) | append-only 강제 | DB trigger |
| NFR-AD-SEC-02 (NFR-AUDIT-01) | 1년 보존 | partitioning + retention job |
| NFR-AD-SEC-03 (NFR-AUDIT-02) | WORM 또는 권한 분리 | `audit_log` 테이블에 `app_user` 권한 INSERT/SELECT만 |
| NFR-AD-SEC-04 | 검색·내보내기 자기-감사 | 모든 search/export call → 새 audit row |
| NFR-AD-AVL-01 | consumer 다운 시에도 outbox 무손실 | polling 안전망 |
| NFR-AD-OBS-01 | 메트릭: outbox depth, consumer lag, write rate | Prometheus |

## 기술 스택
- FastAPI (검색 API)
- SQLAlchemy 2 + asyncpg
- Alembic
- Redis Streams (`redis-py async`)
- 백그라운드 워커: FastAPI lifespan에 task + 별도 worker process 옵션
