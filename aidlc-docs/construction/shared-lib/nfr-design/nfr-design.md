# shared-lib — NFR Design

**유닛**: `shared-lib`
**상위**: nfr-requirements.md

---

## 1. Structured Logging (NFR-SL-OBS-02)

```python
# telemetry/logging.py
import structlog
from contextvars import ContextVar

_corr_id: ContextVar[str | None] = ContextVar("corr_id", default=None)

def configure_logging(level: str = "INFO") -> None:
    structlog.configure(
        processors=[
            _inject_corr_id,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            structlog.processors.add_log_level,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(level),
    )

def _inject_corr_id(_logger, _name, event_dict):
    if cid := _corr_id.get():
        event_dict["corr_id"] = cid
    return event_dict
```

**규약**:
- 모든 로그는 JSON one-line. 멀티라인 메시지 금지.
- `corr_id` 자동 주입. HTTP 미들웨어가 `_corr_id.set(req_id)`.

---

## 2. Prometheus Metrics (NFR-SL-OBS-01)

```python
# telemetry/metrics.py
from prometheus_client import Counter, Histogram, generate_latest

REQUEST_COUNT = Counter("requests_total", "Total requests", ["unit", "endpoint", "code"])
REQUEST_LATENCY = Histogram("request_latency_seconds", "Request latency", ["unit", "endpoint"],
                            buckets=(0.01, 0.05, 0.1, 0.5, 1, 2.5, 5, 10, 30, 60))

def metrics_endpoint() -> bytes:
    return generate_latest()
```

**규약**: 메트릭 이름은 `<unit>_<concept>_<unit_of_measure>` (예: `auth_login_attempts_total`).

---

## 3. OpenTelemetry Tracing (NFR-SL-OBS-03)

```python
# telemetry/tracing.py
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter

def configure_tracing(service_name: str, otlp_endpoint: str | None) -> None:
    provider = TracerProvider()
    if otlp_endpoint:
        provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=otlp_endpoint)))
    trace.set_tracer_provider(provider)
```

> Phase 2에서 OTLP collector 가동 (NFR-OBS-03).

---

## 4. Result Type (NFR-SL-PERF-01)

- `Result`는 frozen dataclass + `__slots__`로 메모리/속도 최적화
- `map`/`and_then` 헬퍼는 평범한 함수 호출만 — JIT 친화

```python
def and_then(r: Result[T, E], f: Callable[[T], Result[U, E]]) -> Result[U, E]:
    return f(r.value) if isinstance(r, Ok) else r
```

---

## 5. Secret Brand (NFR-SL-SEC-06)

```python
class Secret(str):
    """평문 자격증명 brand. 로깅·직렬화 금지."""
    __slots__ = ()
    def __repr__(self) -> str: return "<Secret REDACTED>"
    def __str__(self) -> str: return "<Secret REDACTED>"
    def reveal(self) -> str:
        """명시적 호출만으로 평문 노출 가능 (사용 직전 vault.resolve 직후)."""
        return super().__str__()
```

- ruff 사용자 룰: `f"{secret}"` 또는 `str(secret)` 사용 시 lint 에러

---

## 6. Safe Boundary (fail-closed)

```python
# errors.py
import contextlib, sys

@contextlib.contextmanager
def safe_boundary(unit: str, op: str):
    try:
        yield
    except DomainException:
        raise
    except Exception as e:
        logger.error("unexpected_error", unit=unit, op=op, exc_info=True)
        # 사용자 메시지는 일반화, 상세는 로그/감사로
        raise InternalErrorResponse("internal_error") from None
```

---

## 7. Rate Limiting 헬퍼 (NFR-SL-SEC-03)

```python
# security/rate_limit.py
class SlidingWindowLimiter:
    def __init__(self, redis_client, key_prefix: str, limit: int, window_s: int): ...
    async def check(self, key: str) -> bool: ...  # True if allowed
```

> gateway-unit에서 IP·사용자별 호출.

---

## 8. 의존성 핀 (NFR-SL-SEC-02)

- `uv.lock` 또는 `requirements.lock` 커밋
- 사내 PyPI 미러 URL 강제: `pip install --index-url https://pypi.internal.example.com/simple/`
- CI에서 `cyclonedx-py` 로 SBOM 생성 → `dist/sbom.json` 산출물

---

## 9. CI 게이트

각 PR/Push에서:
1. `ruff check` (custom rules 포함)
2. `mypy --strict`
3. `bandit -r src/`
4. `safety check`
5. `pytest` (coverage ≥ 90%)
6. `cyclonedx-py` (SBOM)
7. (Phase 2) `trivy fs` (라이브러리 자체는 컨테이너 없음)
