# auth-unit — Infrastructure Design

## 배포 단위
**컨테이너 B (backend)에 통합** — MVP에서는 auth + audit + credential + data + notebook(서버) + admin이 단일 컨테이너 안에 모듈로 공존 (Modular Monolith). Phase 2 K8s에서 분리.

## Docker (backend 컨테이너 발췌)
```dockerfile
FROM python:3.11-slim
WORKDIR /app
RUN useradd -r -u 10001 app
COPY --chown=app units/auth-unit/dist/ units/audit-unit/dist/ units/credential-unit/dist/ units/data-unit/dist/ units/notebook-unit/dist/ units/admin-unit/dist/ ./
RUN pip install --index-url ${INTERNAL_PYPI} --no-deps ./*.whl
USER app
EXPOSE 8000
ENV UNIT_MODE=backend  # 모든 백엔드 유닛 모듈 로드
HEALTHCHECK CMD curl -f http://localhost:8000/healthz || exit 1
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
```

## 환경 변수
- `DATABASE_URL` (postgresql+asyncpg://...)
- `REDIS_URL`
- `KEYCLOAK_ISSUER`, `KEYCLOAK_CLIENT_ID`, `KEYCLOAK_CLIENT_SECRET`
- `SESSION_TTL_SECONDS=28800`
- `MFA_REQUIRED_FOR_ADMIN=true`

## DB 마이그레이션
- Alembic — `units/auth-unit/migrations/`
- 초기 마이그레이션: 위 schema (users, user_roles, sessions)
- backend 컨테이너 startup hook이 `alembic upgrade head` 실행 (Idempotent)

## 외부 의존
- Keycloak (TLS 1.2+, 사내 내부 도메인)
- Postgres (TLS 옵션, 사내 인증서)
- Redis (AUTH password, ACL 사용)

## 보안 강화
- DB 사용자: auth-unit 모듈은 `auth_app` 사용자로 (RLS 또는 schema 권한 분리 검토)
- Vault 통합 X (auth-unit은 자격증명을 저장하지 않음, Keycloak 토큰만 다룸)
- secrets: `${KEYCLOAK_CLIENT_SECRET}`는 Docker Compose secrets로 마운트 (`/run/secrets/`)

## 백업
- `users`, `user_roles`, `sessions` 테이블은 BackupService의 데일리 백업 대상 (admin-unit의 BackupScheduler)
