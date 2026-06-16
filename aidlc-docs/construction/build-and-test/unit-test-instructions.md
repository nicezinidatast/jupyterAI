# Unit Test Execution — 내부망 데이터 분석 플랫폼

## 1. 전체 실행

```bash
# 모든 백엔드 유닛 (병렬)
for unit in shared-lib gateway-unit auth-unit audit-unit credential-unit data-unit notebook-unit admin-unit/backend; do
  (cd units/$unit && pytest --cov=src --cov-report=xml --junitxml=test-results.xml) &
done
wait
```

```bash
# Frontend
(cd units/admin-unit/admin-console && pnpm test --coverage --run)
(cd units/admin-unit/auditor-console && pnpm test --coverage --run)
(cd units/admin-unit/jupyter-extensions && pnpm test --run)
```

## 2. PBT (Hypothesis) 별도 실행

```bash
# Property-based tests에 더 많은 예제 + seed 로깅
pytest -m property --hypothesis-seed=0 \
       --hypothesis-show-statistics \
       --hypothesis-profile=ci
```

`units/shared-lib/conftest.py`:
```python
from hypothesis import settings
settings.register_profile("ci", max_examples=500, deadline=2000)
settings.register_profile("dev", max_examples=100)
```

## 3. 기대값

| 유닛 | Coverage | PBT 통과 |
|---|---|---|
| shared-lib | ≥ 90% | Result chain (Round-trip), idempotency key (Determinism), audit event (Round-trip) |
| gateway-unit | ≥ 80% | rate limit (Invariant), authorize (Invariant) |
| auth-unit | ≥ 85% | active admin ≥ 1 (Invariant), session lifecycle (State-Machine), verifyAccess (Invariant) |
| audit-unit | ≥ 85% | outbox 유실 0 (Invariant), event roundtrip |
| credential-unit | ≥ 85% | idempotent register, lifecycle state machine, resolve invariant |
| data-unit | ≥ 80% | RBAC list invariant, PII mask oracle + idempotent, file roundtrip |
| notebook-unit | ≥ 80% | auto-commit idempotent, share-link invariant, job state machine |
| admin-unit | ≥ 80% (backend), ≥ 60% (SPA) | backup invariant |

## 4. CI 통합

`.gitlab-ci.yml` (root):
```yaml
stages: [lint, unit, integration, performance, security, package, deploy]

unit:python:
  stage: unit
  image: python:3.11-slim
  parallel:
    matrix:
      - UNIT: [shared-lib, gateway-unit, auth-unit, audit-unit, credential-unit, data-unit, notebook-unit, admin-unit-backend]
  script:
    - cd units/${UNIT}
    - uv sync
    - pytest --cov=src --cov-report=xml --junitxml=junit.xml
  artifacts:
    reports:
      junit: units/${UNIT}/junit.xml
      coverage_report:
        coverage_format: cobertura
        path: units/${UNIT}/coverage.xml

unit:frontend:
  stage: unit
  image: node:20
  parallel:
    matrix:
      - APP: [admin-console, auditor-console, jupyter-extensions]
  script:
    - cd units/admin-unit/${APP}
    - pnpm install --frozen-lockfile
    - pnpm test --run
```

## 5. 로컬 테스트 — fixtures

```bash
# Postgres + Redis 일회용 컨테이너 (pytest-docker 또는 testcontainers-python)
docker compose -f infra/docker-compose/test.yml up -d postgres redis
pytest units/auth-unit
docker compose -f infra/docker-compose/test.yml down -v
```

## 6. 실패 시

1. junit.xml에서 실패 케이스 확인
2. `pytest -x --lf` (last-failed만 재실행)
3. PBT 실패: seed 출력에서 minimal counter-example 확인 → 재현
4. 수정 후 `pytest -m property` 다시

## 7. 마스킹 보안 회귀 테스트

```bash
# PII 패턴이 어떻게 누락 없이 마스킹되는지 검증
pytest units/data-unit/tests/test_pii_masking.py -v --hypothesis-show-statistics
```

> "임의의 한국 이름·주민번호·전화·이메일을 무작위 생성 → 마스킹 결과에서 원본 패턴이 정규식으로 찾아지지 않아야 함" 라는 PBT가 핵심.
