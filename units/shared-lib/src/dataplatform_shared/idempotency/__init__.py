"""클라이언트 재시도 안전성을 위한 결정적(deterministic) 멱등성 키 패키지.

멱등(idempotent): 같은 요청을 여러 번 보내도 결과가 한 번 보낸 것과 같음.
네트워크 재시도로 중복 요청이 와도 한 번만 처리되도록 키로 식별한다.
"""

from dataplatform_shared.idempotency.keys import idempotency_key

__all__ = ["idempotency_key"]
