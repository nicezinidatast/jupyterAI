"""사내 데이터 분석 플랫폼의 공유 라이브러리.

다른 모든 단위(unit)가 이 패키지에 의존한다 — 즉 모든 단위가 공유하는 토대
추상화(Result 모나드, DomainError, 감사·보안·텔레메트리 인터페이스 등)의
집합소다. 의존성 방향이 단방향(다른 단위 → shared-lib)이라 여기에는 특정
단위에 종속된 코드를 두지 않는다. 설계는 aidlc-docs/construction/shared-lib/ 참조.

아래 re-export는 가장 자주 쓰는 심볼을 패키지 최상단에서 바로 import할 수 있게
한 편의 표면(API surface)이다.
"""

__version__ = "0.1.0"

from dataplatform_shared.errors import DomainError, safe_boundary
from dataplatform_shared.result import Err, Ok, Result, and_then, map_ok

__all__ = [
    "Ok",
    "Err",
    "Result",
    "map_ok",
    "and_then",
    "DomainError",
    "safe_boundary",
    "__version__",
]
