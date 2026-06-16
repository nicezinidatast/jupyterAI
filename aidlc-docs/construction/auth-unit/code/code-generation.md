# auth-unit — Code Generation Plan & Summary

**실제 코드 위치**: `units/auth-unit/`

## Plan (체크리스트)
- [ ] `pyproject.toml` (deps: fastapi, sqlalchemy[asyncio], asyncpg, alembic, redis, httpx, dataplatform-shared)
- [ ] `requirements.lock`
- [ ] `migrations/versions/0001_initial.py` (Alembic)
- [ ] `src/auth/models.py` (User, UserRole, Session SQLAlchemy)
- [ ] `src/auth/schemas.py` (Pydantic DTOs)
- [ ] `src/auth/repositories/users.py`
- [ ] `src/auth/repositories/sessions.py`
- [ ] `src/auth/services/auth_service.py`
- [ ] `src/auth/services/orchestrator.py`
- [ ] `src/auth/services/role_resolver.py`
- [ ] `src/auth/adapters/keycloak.py`
- [ ] `src/auth/api/router.py` (FastAPI router)
- [ ] `src/auth/api/dependencies.py` (db session, current user)
- [ ] `src/auth/cache.py` (Redis verify cache)
- [ ] `src/auth/main.py` (모듈 entry — backend.main에서 register)
- [ ] `tests/test_role_invariant.py` (PBT — 활성 Admin ≥ 1)
- [ ] `tests/test_session_lifecycle.py` (PBT — State-Machine)
- [ ] `tests/test_verify_access.py` (PBT — Invariant)
- [ ] `tests/test_keycloak_adapter.py` (mock with respx)
- [ ] `tests/integration/test_login_flow.py`
- [ ] `.gitlab-ci.yml`

## Definition of Done
- coverage ≥ 85%
- PBT 3종 통과
- Alembic 마이그레이션 idempotent
- mypy strict + ruff + bandit + safety 통과
