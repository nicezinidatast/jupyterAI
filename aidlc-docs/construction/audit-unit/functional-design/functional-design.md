# audit-unit — Functional Design

**모듈**: AuditWriter, AuditQueryApi, AuditEventEmitter(SL-2 호스팅), AuditService

---

## 1. 데이터 모델

```sql
-- 각 도메인 유닛이 같은 트랜잭션에 outbox row insert
CREATE TABLE audit_outbox (
    id BIGSERIAL PRIMARY KEY,
    event JSONB NOT NULL,            -- DomainEvent 직렬화
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    delivered_at TIMESTAMPTZ
);
CREATE INDEX idx_audit_outbox_undelivered ON audit_outbox(id) WHERE delivered_at IS NULL;

-- 영구 감사 저장소 (append-only)
CREATE TABLE audit_log (
    id BIGSERIAL PRIMARY KEY,
    event_type TEXT NOT NULL,
    actor_id UUID,
    resource TEXT,
    result TEXT NOT NULL CHECK (result IN ('success', 'failure')),
    occurred_at TIMESTAMPTZ NOT NULL,
    corr_id TEXT,
    payload JSONB NOT NULL,
    written_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_audit_log_actor_time ON audit_log(actor_id, occurred_at DESC);
CREATE INDEX idx_audit_log_type_time ON audit_log(event_type, occurred_at DESC);
CREATE INDEX idx_audit_log_resource ON audit_log(resource);

-- WORM 강제 (Postgres에서는 trigger로 UPDATE/DELETE 차단)
CREATE OR REPLACE FUNCTION block_audit_modification() RETURNS TRIGGER AS $$
BEGIN
    RAISE EXCEPTION 'audit_log is append-only';
END;
$$ LANGUAGE plpgsql;
CREATE TRIGGER trig_audit_log_no_modify
    BEFORE UPDATE OR DELETE OR TRUNCATE ON audit_log
    EXECUTE FUNCTION block_audit_modification();

-- 1년 보존 — Phase 2에서 파티셔닝(월별) 적용
```

## 2. Outbox Pattern

```text
도메인 유닛에서:
  BEGIN TX
    INSERT INTO <domain_table>(...);
    INSERT INTO audit_outbox(event) VALUES (jsonb_event);
  COMMIT
  XADD audit:notify * id <new_id>      -- Redis Streams 알림 (best-effort)

audit-unit consumer:
  while True:
    # 두 트리거: Redis 알림 OR 5초 폴링 (안전망)
    rows = SELECT id, event FROM audit_outbox
           WHERE delivered_at IS NULL
           ORDER BY id LIMIT 100 FOR UPDATE SKIP LOCKED;
    for row in rows:
      try:
        INSERT INTO audit_log(...) FROM row.event;
        UPDATE audit_outbox SET delivered_at = NOW() WHERE id = row.id;
      except IntegrityError:
        log warn (이미 처리됨 가능성), mark delivered
```

## 3. 핵심 비즈니스 룰

### 3.1 유실률 0 보장 (US-SEC-01)
- outbox는 same-tx 보장 → 도메인 변경 + 이벤트 atomic
- consumer 다운 시 polling 안전망
- audit_log 저장 실패 시 outbox row 그대로 남아 재시도

### 3.2 fail-closed 옵션 (NFR-SEC-15)
- `AUDIT_FAIL_CLOSED=true` 모드: outbox 큐 깊이 > 임계 (예: 10,000)이면 새 도메인 요청 거절
- 기본은 best-effort (outbox 보존만)

### 3.3 검색 (US-SEC-03)
```text
search(filter, page):
  SELECT id, event_type, actor_id, resource, result, occurred_at, payload
  FROM audit_log
  WHERE (filter.user is null OR actor_id = filter.user)
    AND (filter.from is null OR occurred_at >= filter.from)
    AND (filter.to is null OR occurred_at <= filter.to)
    AND (filter.actions is null OR event_type = ANY(filter.actions))
    AND (filter.resources is null OR resource = ANY(filter.resources))
  ORDER BY occurred_at DESC
  LIMIT 100 OFFSET <page>;
```

### 3.4 검색·내보내기 자체도 감사
- `audit_searched`, `audit_exported` 이벤트 발행 → 자기 자신의 outbox에 insert

## 4. PBT
| 함수 | 기법 | 검증 |
|---|---|---|
| `outbox consume` | Invariant | outbox row 수 + audit_log 수 = 발행 수 (유실 0) |
| `audit_log insert` | Idempotent | 같은 id 두 번 처리 시 동일 결과 (또는 충돌 무시) |
| `DomainEvent JSON` | Round-trip | event → JSONB → event 동일 |

## 5. 외부 의존
Postgres (트리거 + JSONB), Redis Streams (best-effort 알림)

## 6. Story 매핑
US-SEC-01 (전수 기록), US-SEC-03 (검색)
