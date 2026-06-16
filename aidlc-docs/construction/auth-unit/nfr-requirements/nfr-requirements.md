# auth-unit — NFR Requirements

| ID | 요구사항 | 매핑 |
|---|---|---|
| NFR-AU-PERF-01 | `verifyAccess` 호출 | < 5ms (p95) — 모든 요청의 hot path |
| NFR-AU-PERF-02 | `issue session` | < 50ms |
| NFR-AU-PERF-03 | role assignment 트랜잭션 | < 200ms |
| NFR-AU-SEC-01 (SECURITY-12) | argon2id/PBKDF2 해시 (Keycloak에 위임) | Realm 정책 |
| NFR-AU-SEC-02 | 세션 쿠키 `Secure;HttpOnly;SameSite=Lax` | gateway-unit이 세팅 |
| NFR-AU-SEC-03 | 무차별 대입 차단 (5회 실패 → IdP 잠금) | Keycloak에 위임 |
| NFR-AU-SEC-04 | 활성 Admin ≥ 1 invariant | PBT로 검증 |
| NFR-AU-AUDIT-01 | 모든 로그인/로그아웃/역할 변경 감사 발행 | shared-lib emitter |
| NFR-AU-OBS-01 | 메트릭: login attempts/successes/failures, active sessions gauge | Prometheus |

## 기술 스택

| 항목 | 결정 |
|---|---|
| Web Framework | FastAPI |
| ORM | **SQLAlchemy 2.x + asyncpg** |
| Migration | **Alembic** |
| Cache/Session | redis-py (async) |
| Keycloak Client | `python-keycloak` 또는 직접 httpx 호출 (가벼움) |
| 비밀번호 정책 | Keycloak Realm에 위임 |

## 호환성
- Keycloak 22.x 이상
- Postgres 16 (jsonb, ON DELETE CASCADE)
