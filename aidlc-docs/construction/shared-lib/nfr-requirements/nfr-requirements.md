# shared-lib — NFR Requirements

**유닛**: `shared-lib`
**상위 매핑**: requirements.md NFR-SEC-03, NFR-SEC-10·11·12, NFR-OBS-01~04, NFR-TEST-01~10

---

## 1. 성능 NFR

| ID | 목표 | 측정 |
|---|---|---|
| NFR-SL-PERF-01 | `Result.map/and_then` 오버헤드 | < 1μs (in-process) |
| NFR-SL-PERF-02 | Telemetry metric increment | < 5μs |
| NFR-SL-PERF-03 | structlog `info()` 호출 | < 50μs (JSON 직렬화 포함) |
| NFR-SL-PERF-04 | OpenTelemetry span start/end 오버헤드 | < 20μs |

> 본 라이브러리는 *모든 호출 경로의 hot path* 에 들어가므로 마이크로 단위 측정 필요.

---

## 2. 보안 NFR

| ID | 요구사항 | 적용 |
|---|---|---|
| NFR-SL-SEC-01 (SECURITY-03) | 구조화 JSON 로깅 — `timestamp/level/corr_id/message` 필수 | structlog config 강제 |
| NFR-SL-SEC-02 (SECURITY-10) | 의존성 핀 + SBOM | poetry.lock + cyclonedx-bom |
| NFR-SL-SEC-03 (SECURITY-11) | Rate Limiting 헬퍼 제공 (사용은 gateway-unit) | sliding window 알고리즘 |
| NFR-SL-SEC-04 (SECURITY-13) | Safe deserialization | `pickle` 금지, JSON만. ruff 사용자 룰로 강제 |
| NFR-SL-SEC-05 (SECURITY-15) | fail-closed 전역 예외 핸들러 헬퍼 | `with safe_boundary():` 컨텍스트 매니저 |
| NFR-SL-SEC-06 | Secret 타입 brand — 로깅·직렬화 차단 | `Secret(str)` subclass + `__repr__` 오버라이드 |

---

## 3. 관측성 NFR

| ID | 요구사항 |
|---|---|
| NFR-SL-OBS-01 | Prometheus metric exporter (HTTP `/metrics` 헬퍼) |
| NFR-SL-OBS-02 | 구조화 로깅 (Loki 친화 JSON, `level/ts/corr_id/event/...`) |
| NFR-SL-OBS-03 | OpenTelemetry tracer + correlation-id propagation |
| NFR-SL-OBS-04 | `/healthz` / `/readyz` 핸들러 헬퍼 |

---

## 4. 테스트 NFR (PBT)

| ID | 요구사항 |
|---|---|
| NFR-SL-TEST-01 | Hypothesis 사용, Shrinking + Seed 로깅 (NFR-TEST-08) |
| NFR-SL-TEST-02 | Round-trip PBT — Result chain, audit event JSON |
| NFR-SL-TEST-03 | Domain-Generator — idempotency key |
| NFR-SL-TEST-04 | Coverage ≥ 90% (라이브러리는 모든 유닛이 의존하므로 강한 기준) |
| NFR-SL-TEST-05 | mypy strict + ruff + bandit 통과 |

---

## 5. 기술 스택 (확정)

| 항목 | 결정 |
|---|---|
| 언어 | **Python 3.11+** |
| 패키징 | **uv** (또는 Poetry, 사내 표준에 따름) |
| Lint | **ruff** + custom rules (pickle 금지 등) |
| Type Check | **mypy --strict** |
| 보안 스캔 | **bandit** + **safety** |
| 의존성 핀 | `requirements.lock` 또는 `uv.lock` |
| 배포 형태 | Python wheel → 사내 PyPI 미러 |
| 필수 외부 패키지 | `structlog>=24`, `prometheus-client>=0.20`, `opentelemetry-api>=1.25`, `opentelemetry-sdk>=1.25`, `pydantic>=2.7`, `hypothesis>=6.100`(dev) |

---

## 6. 호환성

- Python 3.11, 3.12 모두 지원
- Linux x86_64 / arm64
- 의존성 모두 사내 PyPI 미러에 미러링 가능한 것만 채택 (NFR-DEPLOY-03)
