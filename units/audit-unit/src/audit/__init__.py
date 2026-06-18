"""audit-unit — outbox 패턴 기반 감사 로그 수집 패키지.

이미터(``audit.emitter.OutboxAuditEmitter``)가 도메인 트랜잭션과 동일한 세션에
이벤트를 삽입하고, 컨슈머(``audit.consumer.OutboxConsumer``)가 백그라운드에서
audit_log 테이블로 이관한다. 조회는 ``audit.api.router`` 및
``audit.services.query_api.AuditQueryApi`` 를 통해 제공된다.
"""

__version__ = "0.1.0"
