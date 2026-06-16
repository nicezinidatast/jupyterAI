# gateway-unit — Code Generation Plan & Summary

**유닛**: `gateway-unit`
**실제 코드 위치**: `units/gateway-unit/`

## Part 1 — Plan

- [ ] `units/gateway-unit/pyproject.toml` (deps: fastapi, uvicorn[standard], redis, pyjwt, dataplatform-shared)
- [ ] `units/gateway-unit/requirements.lock`
- [ ] `src/gateway/main.py` (FastAPI app, middleware stack)
- [ ] `src/gateway/middlewares/security_headers.py`
- [ ] `src/gateway/middlewares/rate_limit.py`
- [ ] `src/gateway/middlewares/request_id.py`
- [ ] `src/gateway/middlewares/access_log.py`
- [ ] `src/gateway/middlewares/jwt_auth.py`
- [ ] `src/gateway/middlewares/tracing.py`
- [ ] `src/gateway/oidc/callback.py`
- [ ] `src/gateway/oidc/state_store.py`
- [ ] `src/gateway/oidc/jwks_cache.py`
- [ ] `src/gateway/security/kernel.py` (SecurityKernel 구현)
- [ ] `src/gateway/routes/proxy.py` (백엔드 패스스루)
- [ ] `src/gateway/routes/health.py`
- [ ] `src/gateway/config.py` (Pydantic Settings)
- [ ] `tests/test_security_headers.py`
- [ ] `tests/test_rate_limit.py` (PBT — Invariant)
- [ ] `tests/test_oidc_callback.py`
- [ ] `tests/test_authorize.py` (PBT — Invariant)
- [ ] `tests/integration/test_routing.py`
- [ ] `Dockerfile`
- [ ] `.gitlab-ci.yml`

## Part 2 — Generation (코드 직접 산출)
Code Generation Part 2는 마지막 유닛 완료 후 일괄 진행.

## Definition of Done

- [ ] 위 모든 [x]
- [ ] coverage ≥ 80%
- [ ] PBT 통과 (rate limit invariant, authorize invariant)
- [ ] Trivy 컨테이너 스캔 0 critical/high
- [ ] integration test: 모든 라우트가 화이트리스트 기반으로만 통과
