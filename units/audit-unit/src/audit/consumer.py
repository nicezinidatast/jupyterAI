"""Background consumer: outbox → audit_log.

Uses ``SELECT ... FOR UPDATE SKIP LOCKED`` to allow many workers to run in
parallel without stepping on the same rows. SQLite falls back to a regular
select; the test fixture uses a single consumer so locking is unnecessary
there.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime

from sqlalchemy import func, insert, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from dataplatform_shared.telemetry import get_logger

from audit.models import AuditLog, AuditOutbox

logger = get_logger("audit.consumer")


class OutboxConsumer:
    def __init__(self, session_factory, *, batch: int = 100, idle_sleep_s: float = 5.0) -> None:
        self._session_factory = session_factory
        self._batch = batch
        self._idle_sleep_s = idle_sleep_s
        self._stopped = asyncio.Event()

    def stop(self) -> None:
        self._stopped.set()

    async def run(self) -> None:
        while not self._stopped.is_set():
            processed = await self._drain_once()
            if processed == 0:
                try:
                    await asyncio.wait_for(self._stopped.wait(), timeout=self._idle_sleep_s)
                except TimeoutError:
                    pass

    async def _drain_once(self) -> int:
        async with self._session_factory() as session:  # type: AsyncSession
            async with session.begin():
                stmt = (
                    select(AuditOutbox)
                    .where(AuditOutbox.delivered_at.is_(None))
                    .order_by(AuditOutbox.id)
                    .limit(self._batch)
                )
                # FOR UPDATE SKIP LOCKED is Postgres-only; suppress for sqlite tests.
                try:
                    stmt = stmt.with_for_update(skip_locked=True)
                except Exception:  # noqa: BLE001
                    pass
                rows = (await session.execute(stmt)).scalars().all()
                if not rows:
                    return 0
                for row in rows:
                    event = row.event
                    await session.execute(
                        insert(AuditLog).values(
                            event_type=event["type"],
                            actor_id=event["actor"],
                            resource=event.get("resource"),
                            result=event["result"],
                            occurred_at=_parse_at(event["at"]),
                            corr_id=event.get("corr_id"),
                            payload=event.get("payload", {}),
                        )
                    )
                    await session.execute(
                        update(AuditOutbox)
                        .where(AuditOutbox.id == row.id)
                        .values(delivered_at=func.now())
                    )
                logger.info("audit_drained", count=len(rows))
                return len(rows)


def _parse_at(value: str) -> datetime:
    # Accept Z-suffixed UTC as well as +HH:MM offsets.
    if value.endswith("Z"):
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    return datetime.fromisoformat(value).astimezone(UTC)
