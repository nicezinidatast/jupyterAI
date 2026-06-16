# audit-unit — Code Generation Plan

**실제 코드 위치**: `units/audit-unit/`

## Plan
- [ ] `pyproject.toml`
- [ ] `migrations/0001_audit_tables.py` (audit_outbox, audit_log, WORM trigger)
- [ ] `migrations/0002_audit_indexes.py`
- [ ] `src/audit/models.py`
- [ ] `src/audit/emitter.py` (OutboxAuditEmitter — shared-lib SL-2 구현)
- [ ] `src/audit/consumer.py` (background loop)
- [ ] `src/audit/services/query_api.py`
- [ ] `src/audit/api/router.py` (`/api/audit/...`)
- [ ] `src/audit/retention.py` (cron entry)
- [ ] `src/audit/main.py`
- [ ] `tests/test_outbox_invariant.py` (PBT — 유실 0)
- [ ] `tests/test_event_roundtrip.py` (PBT)
- [ ] `tests/test_worm_trigger.py` (UPDATE/DELETE 시도 → 차단)
- [ ] `tests/test_search.py`
- [ ] `tests/integration/test_consumer_under_load.py`
- [ ] `.gitlab-ci.yml`

## Definition of Done
- coverage ≥ 85%
- PBT: outbox invariant (도메인 emit 수 == audit_log row 수)
- WORM 트리거 검증 (UPDATE/DELETE 시도 시 raise)
- 1000 events/s 처리량 검증 (Locust 부하 테스트)
