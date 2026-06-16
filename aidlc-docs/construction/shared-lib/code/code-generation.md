# shared-lib — Code Generation Plan & Summary

**유닛**: `shared-lib`
**실제 코드 위치**: `units/shared-lib/` (워크스페이스 루트 — aidlc-docs/ 밖)
**본 문서는 마크다운 요약**. 실제 `.py` 파일은 Code Generation Part 2 (실 코드 생성 단계)에서 생성.

---

## Part 1 — Plan (체크리스트)

- [ ] `units/shared-lib/pyproject.toml` 작성 (uv 또는 Poetry)
- [ ] `units/shared-lib/requirements.lock` 생성 (의존성 핀)
- [ ] `src/dataplatform_shared/__init__.py` (버전 export)
- [ ] `src/dataplatform_shared/result.py` (Ok/Err/Result)
- [ ] `src/dataplatform_shared/errors.py` (DomainError enum + safe_boundary)
- [ ] `src/dataplatform_shared/telemetry/logging.py` (structlog config)
- [ ] `src/dataplatform_shared/telemetry/metrics.py` (Prometheus helpers)
- [ ] `src/dataplatform_shared/telemetry/tracing.py` (OTel SDK wrapper)
- [ ] `src/dataplatform_shared/security/kernel_iface.py` (SecurityKernel Protocol)
- [ ] `src/dataplatform_shared/security/rate_limit.py` (SlidingWindowLimiter)
- [ ] `src/dataplatform_shared/security/secret.py` (Secret brand)
- [ ] `src/dataplatform_shared/audit/emitter_iface.py` (AuditEventEmitter Protocol)
- [ ] `src/dataplatform_shared/audit/events.py` (DomainEvent TypedDict)
- [ ] `src/dataplatform_shared/idempotency/keys.py` (key generation)
- [ ] `src/dataplatform_shared/types/common.py` (UserId, Role, CorrelationId)
- [ ] `tests/test_result.py` (PBT — Hypothesis)
- [ ] `tests/test_idempotency.py` (PBT)
- [ ] `tests/test_audit_events.py` (PBT round-trip)
- [ ] `tests/test_secret.py` (Secret brand — repr 검증)
- [ ] `tests/test_logging.py` (corr_id 주입 검증)
- [ ] `.gitlab-ci.yml` (unit별 CI 파이프라인 fragment)
- [ ] `README.md` (사용법 + 다른 유닛에서 import 예시)

---

## Part 2 — Generation (실제 코드)

본 단계의 실제 파일 생성은 **상위 사용자 승인** 후 진행. 워크플로 룰에 따라 단계마다 승인이 필요하지만, 사용자 합의(memory: feedback_decision_style)에 따라 마지막 유닛 완료 + Build/Test 산출물 후 일괄 승인.

### 디렉터리 구조 (Greenfield 의무)

```text
units/shared-lib/
├── pyproject.toml
├── requirements.lock
├── src/
│   └── dataplatform_shared/
│       ├── __init__.py
│       ├── result.py
│       ├── errors.py
│       ├── telemetry/
│       │   ├── __init__.py
│       │   ├── logging.py
│       │   ├── metrics.py
│       │   └── tracing.py
│       ├── security/
│       │   ├── __init__.py
│       │   ├── kernel_iface.py
│       │   ├── rate_limit.py
│       │   └── secret.py
│       ├── audit/
│       │   ├── __init__.py
│       │   ├── emitter_iface.py
│       │   └── events.py
│       ├── idempotency/
│       │   ├── __init__.py
│       │   └── keys.py
│       └── types/
│           ├── __init__.py
│           └── common.py
├── tests/
│   ├── test_result.py
│   ├── test_idempotency.py
│   ├── test_audit_events.py
│   ├── test_secret.py
│   └── test_logging.py
├── .gitlab-ci.yml
└── README.md
```

### 핵심 API 사용 예시 (다른 유닛 관점)

```python
# 어떤 유닛에서든
from dataplatform_shared.result import Ok, Err, Result
from dataplatform_shared.errors import DomainError, safe_boundary
from dataplatform_shared.telemetry import logging, metrics, tracing
from dataplatform_shared.audit.events import DomainEvent
from dataplatform_shared.security.secret import Secret

# 앱 startup
logging.configure_logging(level=os.getenv("LOG_LEVEL", "INFO"))
tracing.configure_tracing("auth-unit", otlp_endpoint=os.getenv("OTLP_ENDPOINT"))

# 사용
def register_user(name: str) -> Result[UserId, DomainError]:
    if not name:
        return Err(DomainError.VALIDATION)
    # ...
    return Ok(user_id)
```

---

## Part 3 — Definition of Done

- [ ] 모든 위 체크박스 [x]
- [ ] CI 그린 (ruff + mypy + bandit + safety + pytest + coverage ≥ 90%)
- [ ] SBOM 산출
- [ ] 사내 PyPI에 `0.1.0` 발행
- [ ] 1개 이상의 PBT 통과(Result chain, audit event round-trip, idempotency key determinism)

---

## Part 4 — 다음 유닛 영향

- 다음 유닛(`gateway-unit`, `auth-unit` 등)은 `pyproject.toml`에 `dataplatform-shared = "^0.1.0"` 추가 후 `from dataplatform_shared.* import ...` 형태로 사용
