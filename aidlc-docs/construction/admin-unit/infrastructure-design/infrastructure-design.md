# admin-unit — Infrastructure Design

## 배포

| 컴포넌트 | 컨테이너 |
|---|---|
| AdminConsole SPA (정적) | **컨테이너 D** (nginx static serving) 또는 gateway-unit이 직접 서빙 |
| AuditorConsole SPA (정적) | 동일 (별도 path) |
| AdminService backend 모듈 | 컨테이너 B (backend) |
| BackupService backend 모듈 | 컨테이너 B (cron task로 lifespan에 등록) |
| JupyterExtensionsBundle | 사용자 컨테이너 이미지에 빌드 시 포함 |

## 컨테이너 D (정적 SPA 서빙)
```dockerfile
FROM nginx:alpine
COPY units/admin-unit/admin-console/dist /usr/share/nginx/html/admin
COPY units/admin-unit/auditor-console/dist /usr/share/nginx/html/auditor
COPY infra/nginx/spa.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
```

> MVP에서는 gateway-unit이 SPA를 직접 서빙하는 옵션도 가능 (별도 컨테이너 D 생략, 단순화).
> 권장: 컨테이너 D 분리 — 정적 자산 캐싱 + 보안 헤더 단순화

## 환경 변수 (backend 모듈)
- `BACKUP_DIR=/var/backups`
- `BACKUP_SCHEDULE_CRON=0 2 * * *` (매일 02:00)
- `RESTORE_REHEARSAL_CRON=0 3 1 * *` (매월 1일 03:00)
- `QUARTERLY_REVIEW_CRON=0 4 1 1,4,7,10 *` (분기 시작)
- `BACKUP_FAILURE_ALERT_RECIPIENTS=secops@internal.example.com`
- `SMTP_HOST=mail.internal`
- `GRAFANA_BASE_URL=https://grafana.internal`

## DB 마이그레이션
- backups, restore_rehearsals, quarterly_access_reviews

## 외부 의존
- Postgres (메타 + audit_log 읽기)
- 사내 백업 스토리지 (NAS or S3)
- 사내 메일 시스템 (SMTP)
- Grafana (대시보드 임베드, iframe + Bearer token forward)
- Prometheus (메트릭 query)

## SPA CSP (강화)
- `Content-Security-Policy: default-src 'self'; script-src 'self' 'nonce-{random}'; style-src 'self' 'unsafe-inline'`
- nginx config에서 nonce 주입 또는 build 시점에 nonce placeholder

## 백업 격리 환경 (restore rehearsal)
```yaml
# infra/restore-test/compose.yml
services:
  postgres-test:
    image: postgres:16
    environment: ...
    volumes:
      - /tmp/restore-test:/var/lib/postgresql/data
  ...
```
- 매월 1일 03:00 spawn → 5분 내 sanity → tear down

## 백업 retention
- 일 단위: 14일 보관
- 주 단위: 8주
- 월 단위: 12개월
- (cron으로 expiration)

## 보안 강화
- SPA 빌드 산출물 Subresource Integrity (SRI) — 자동 생성
- 백업 파일 OS-level encryption (LUKS 또는 fs encryption)
- BackupScheduler는 별도 DB user (`backup_user`)로 pg_dump 권한만
