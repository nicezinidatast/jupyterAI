# shared-lib — Functional Design

**유닛**: `shared-lib` (가상 유닛, 라이브러리 패키지)
**책임**: 모든 유닛이 import 하는 공통 코드 — Telemetry, ResultTypes, SecurityKernel/AuditEventEmitter 인터페이스

---

## 1. 모듈 인벤토리

| 모듈 | 책임 |
|---|---|
| `result.py` | `Result[T, E]` / `DomainError` enum |
| `errors.py` | 도메인 에러 계층 + 코드 매핑 |
| `telemetry/metrics.py` | Prometheus exporter 헬퍼 |
| `telemetry/logging.py` | structlog 기반 JSON 구조화 로깅 |
| `telemetry/tracing.py` | OpenTelemetry SDK wrapper |
| `security/kernel_iface.py` | `SecurityKernel` Protocol (인터페이스) |
| `audit/emitter_iface.py` | `AuditEventEmitter` Protocol |
| `audit/events.py` | 표준 `DomainEvent` 데이터클래스 |
| `idempotency/keys.py` | 멱등성 키 생성 헬퍼 |
| `types/common.py` | `UserId`, `Role`, `CorrelationId` 등 공통 타입 |

---

## 2. 핵심 데이터 모델

```python
# result.py — Q-AD-5=A: Result/Either 통일
from dataclasses import dataclass
from typing import Generic, TypeVar, Union

T = TypeVar('T'); E = TypeVar('E')

@dataclass(frozen=True, slots=True)
class Ok(Generic[T]):
    value: T
    @property
    def ok(self) -> bool: return True

@dataclass(frozen=True, slots=True)
class Err(Generic[E]):
    error: E
    @property
    def ok(self) -> bool: return False

Result = Union[Ok[T], Err[E]]

# errors.py
from enum import Enum

class DomainError(str, Enum):
    UNAUTHORIZED = "UNAUTHORIZED"
    FORBIDDEN = "FORBIDDEN"
    NOT_FOUND = "NOT_FOUND"
    CONFLICT = "CONFLICT"
    VALIDATION = "VALIDATION"
    EXTERNAL_UNAVAILABLE = "EXTERNAL_UNAVAILABLE"
    RATE_LIMITED = "RATE_LIMITED"
    EXPIRED = "EXPIRED"
    BAD_INPUT = "BAD_INPUT"
    INTERNAL_ERROR = "INTERNAL_ERROR"

# audit/events.py
from datetime import datetime
from typing import Literal, TypedDict

class DomainEvent(TypedDict):
    type: str                  # 'login', 'query_executed', 'role_changed', ...
    actor: str                 # UserId
    resource: str | None
    result: Literal['success', 'failure']
    at: datetime               # UTC, ISO 8601
    corr_id: str
    payload: dict              # JSON-serializable, no secrets
```

---

## 3. 핵심 비즈니스 룰

### 3.1 ResultTypes
- 모든 도메인 함수는 예외 던지지 않고 `Result` 반환
- `Result` 사용 시 mypy 강제: `if isinstance(r, Err): ...` 패턴
- 시스템 오류(메모리 부족, 디스크 풀)는 예외 throw 허용 — 전역 핸들러가 fail-closed (SECURITY-15)

### 3.2 DomainEvent 규칙
- `payload`에 **Secret 타입** 포함 금지 (정적 검사로 강제 — bandit + 사용자 정의 ruff 룰)
- `corr_id`는 OpenTelemetry trace_id와 동일 또는 propagate
- `at`은 항상 UTC, naive datetime 금지

### 3.3 Idempotency Keys
- 클라이언트 → 서버 멱등 요청에 사용 (예: 자격증명 등록)
- 키 형식: `{user_id}:{operation}:{resource_hash}` (SHA-256 단축)
- TTL: 24시간 (Redis)

---

## 4. 외부 의존성

- 없음 (다른 유닛 의존 0개)
- 외부 라이브러리: `structlog`, `prometheus_client`, `opentelemetry-api`, `opentelemetry-sdk`, `pydantic` (TypedDict 검증), `hypothesis` (테스트만)

---

## 5. PBT 적용 (NFR-TEST-01~10)

| 함수 | PBT 기법 | 무엇을 검증 |
|---|---|---|
| `Result.map / and_then` | Round-trip | `Ok(x).map(f).map(g) == Ok(g(f(x)))` |
| `idempotency_key()` | Domain-Generator + Invariant | 같은 입력 → 같은 키 (deterministic) |
| `audit/events serialization` | Round-trip | event → JSON → event 동일성 |

---

## 6. 완료 정의 (Definition of Done)

- [x] 모듈 인벤토리 + 데이터 모델 정의 완료
- [x] 비즈니스 룰 (3개) 명시
- [x] PBT 적용 위치 식별
- 후속(Code Generation): 단위 테스트 80%+, 타입 검증 통과, 사내 PyPI 미러에 0.1.0 발행
