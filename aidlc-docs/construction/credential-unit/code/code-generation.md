# credential-unit — Code Generation Plan

**실제 코드 위치**: `units/credential-unit/`

## Plan
- [ ] `pyproject.toml` (deps: fastapi, sqlalchemy[asyncio], asyncpg, hvac, dataplatform-shared)
- [ ] `requirements.lock`
- [ ] `migrations/0001_credentials.py`
- [ ] `src/credential/models.py`
- [ ] `src/credential/schemas.py`
- [ ] `src/credential/adapters/vault.py` (VaultAdapter)
- [ ] `src/credential/services/vault_service.py` (CredentialVault)
- [ ] `src/credential/cache.py` (ResolveCache)
- [ ] `src/credential/api/router.py`
- [ ] `src/credential/main.py`
- [ ] `tests/test_idempotent_register.py` (PBT)
- [ ] `tests/test_lifecycle_state_machine.py` (PBT)
- [ ] `tests/test_resolve_invariant.py` (PBT — owner != requester → FORBIDDEN)
- [ ] `tests/test_vault_adapter.py` (mock with responses)
- [ ] `tests/integration/test_register_rotate_delete.py`
- [ ] `.gitlab-ci.yml`

## Definition of Done
- coverage ≥ 85%
- PBT 3종 통과
- Vault adapter circuit-breaker 동작 (Vault 다운 시 graceful fallback)
- 평문 secret이 어떤 로그·메트릭에도 노출되지 않음 (bandit + grep CI 룰)
