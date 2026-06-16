# audit-unit — NFR Design

## 1. SL-2 emitter 호스팅

```python
# shared-lib 인터페이스는 abstract, 구체 구현은 audit-unit에서 register
class OutboxAuditEmitter:
    def __init__(self, session_factory): self._session_factory = session_factory

    async def emit(self, session, event: DomainEvent) -> None:
        # 같은 세션(=같은 tx)에서 insert
        await session.execute(
            insert(AuditOutbox).values(event=event)
        )
        # commit은 호출자 트랜잭션
```

각 도메인 유닛은 자기 트랜잭션에서 `await emitter.emit(session, event)` 호출.

## 2. Consumer Loop

```python
async def consumer_loop():
    redis = await aioredis.from_url(REDIS_URL)
    pubsub = await redis.subscribe("audit:notify")
    async with AsyncSessionLocal() as session:
        while True:
            # 즉시 모드: 알림 받으면 즉시 처리
            try:
                async with asyncio.timeout(5):  # 5초 polling 안전망
                    await pubsub.get_message()
            except TimeoutError:
                pass

            async with session.begin():
                rows = await session.execute(
                    select(AuditOutbox)
                    .where(AuditOutbox.delivered_at.is_(None))
                    .order_by(AuditOutbox.id)
                    .limit(100)
                    .with_for_update(skip_locked=True)
                )
                for row in rows.scalars():
                    await session.execute(
                        insert(AuditLog).values(**row.event)
                    )
                    row.delivered_at = func.now()
            METRIC_PROCESSED.inc(len(rows.scalars().all()))
```

- `with_for_update(skip_locked=True)` — 다중 워커 동시 실행 가능

## 3. Retention Job

```python
# 일 1회 cron — 1년 + 30일 grace 지난 row 삭제 (audit table 권한이 별도라 별 schema user)
async def retention():
    # WORM trigger 우회를 위한 별도 superuser/role 필요
    await session.execute(text(
        "DELETE FROM audit_log WHERE occurred_at < NOW() - INTERVAL '395 days'"
    ))
```

> 운영 정책: 1년 보관(NFR-AUDIT-01) + 30일 grace.
> Phase 2: 월별 partition + 오래된 partition은 archive(parquet) 후 detach.

## 4. 검색 API

```python
@router.get("/api/audit", dependencies=[require_role(["Auditor", "Admin"])])
async def search(filter: AuditFilter, page: int = 0):
    rows = ...  # SQL
    await emitter.emit(session, audit_searched_event(actor, filter))
    return {"items": rows, "page": page, "has_next": ...}

@router.get("/api/audit/export", dependencies=[require_role(["Auditor"])])
async def export(filter: AuditFilter, format: str = "csv"):
    # streaming response
    ...
```

## 5. 메트릭

```
audit_emit_total{event_type}
audit_outbox_depth        (gauge)
audit_consumer_lag_seconds (gauge)
audit_search_total{result}
audit_export_total{format}
```

## 6. 권한 분리

- DB user `app_user`: outbox/audit_log INSERT + audit_log SELECT
- DB user `retention_user`: audit_log DELETE (cron job 전용)
- DB user `dba_user`: 백업 (admin-unit BackupService 호출 시 사용)
