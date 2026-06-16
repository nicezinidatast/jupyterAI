# audit-unit — Infrastructure Design

## 배포
- backend 컨테이너 B에 모듈로 동거
- consumer는 별도 thread/task로 FastAPI lifespan에서 spawn
- Phase 2: separate `audit-worker` 컨테이너로 분리 가능

## DB 분리 (선택)
- MVP: 메인 Postgres의 `audit` schema 사용 (권한 분리 적용)
- Phase 2: 별도 audit DB로 물리 분리 검토 (보안 강화)

## 환경 변수
- `DATABASE_URL`
- `REDIS_URL`
- `AUDIT_FAIL_CLOSED=false` (MVP 기본)
- `AUDIT_RETENTION_DAYS=395`
- `AUDIT_CONSUMER_BATCH=100`

## 백업
- audit_log는 데일리 백업 + 월별 archive (NFR-AUDIT)
- Backup 자체도 감사 이벤트 발행 (메타-감사)

## 외부 의존
- Postgres (audit schema)
- Redis Streams (선택, best-effort 알림)

## Cron Job (infra/)
- 일 1회: retention job (Postgres pg_cron 또는 Ansible 스케줄러)
- 월 1회: archive job (Phase 2)
- 분기 1회: 권한 리뷰 보고서 자동 생성 (NFR-AUDIT-03)
