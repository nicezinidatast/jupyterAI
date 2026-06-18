"""Secret 브랜드 — 로그에 자신을 절대 드러내지 않는 불투명(opaque) 래퍼.

위협 모델: 비밀값(비밀번호·토큰 등)이 로그·예외 메시지·직렬화 페이로드에
"실수로" 섞여 들어가는 사고를 코드 차원에서 막는다. 평문이 필요한 정확히 그
호출 지점에서만 명시적으로 ``secret.reveal()``을 호출하게 강제한다(예: DB
드라이버에 넘기기 직전). 그 외 우발적 ``str(secret)``·``f"{secret}"``·
``pickle.dumps(secret)``·(``SafeJSONEncoder`` 사용 시) ``json.dumps(payload)``는
모두 값을 노출하지 않는다 — 노출이 안전한 기본값(safe by default)이 되게 했다.
"""

from __future__ import annotations

import json
from typing import Any


class Secret(str):
    """기본 표현이 가려지는(redacted) ``str`` 서브클래스.

    ``str``을 상속한 이유: 문자열을 기대하는 타입 검사기·라이브러리와 매끄럽게
    호환되면서도, 우발적 직렬화로 값이 새지 않도록 표현 계열 메서드만 가린다.
    즉 "문자열처럼 다루되 출력될 때만 가린다"는 절충이다. 단, 이 상속 때문에
    평범한 ``json.dumps``는 여전히 평문을 흘린다 — 그래서 영속 저장·전송에는
    아래 SafeJSONEncoder를 반드시 써야 한다.
    """

    __slots__ = ()

    def __repr__(self) -> str:
        return "<Secret REDACTED>"

    def __str__(self) -> str:  # noqa: DUN — explicit override is intentional
        return "<Secret REDACTED>"

    def __format__(self, format_spec: str) -> str:  # noqa: ARG002
        # f-string/format()도 막는다. str의 기본 __format__은 값을 그대로
        # 내보내므로 반드시 오버라이드해야 누출이 닫힌다.
        return "<Secret REDACTED>"

    def __reduce__(self) -> Any:  # noqa: D401
        # Secret을 pickle한다는 건 큐 페이로드 등에 실수로 섞여 들어갔다는
        # 신호일 가능성이 크다. 조용히 통과시키지 말고 경계에서 크게 실패시킨다.
        raise TypeError(
            "Secret values cannot be serialised; call .reveal() at the call site"
        )

    def __reduce_ex__(self, protocol: int) -> Any:  # noqa: ARG002
        # __reduce_ex__도 막아야 한다. pickle은 보통 __reduce_ex__를 먼저
        # 호출하므로 이쪽을 닫지 않으면 __reduce__ 차단이 우회된다.
        raise TypeError(
            "Secret values cannot be serialised; call .reveal() at the call site"
        )

    def reveal(self) -> str:
        """내부 평문에 접근하는 유일한 명시적 통로.

        평문 사용을 ``.reveal()`` 한 지점으로 좁혔기에, 리뷰어가 ``.reveal()``을
        grep하는 것만으로 모든 평문 사용처를 감사(audit)할 수 있다.
        """
        return super().__str__()


class SafeJSONEncoder(json.JSONEncoder):
    """트리 어디에 있든 ``Secret`` 값의 JSON 출력을 거부하는 인코더.

    영속 저장소나 와이어 페이로드로 직렬화하는 모든 곳에서 쓴다::

        json.dumps(payload, cls=SafeJSONEncoder)

    ``Secret``이 ``str``을 상속하므로 기본 인코더는 평문을 조용히 내보낸다.
    그래서 default() 훅에만 의존할 수 없다 — Secret은 str로 인식돼 default()에
    도달조차 하지 않기 때문. 따라서 인코딩 전에 트리를 직접 순회(walk)해
    Secret을 먼저 찾고, 첫 누출 지점에서 ``TypeError``를 던진다.
    encode/iterencode 두 진입점을 모두 가드해 어느 경로로 호출돼도 검사되게 한다.
    """

    def encode(self, o: Any) -> str:  # noqa: D401
        self._check_no_secret(o)
        return super().encode(o)

    def iterencode(self, o: Any, _one_shot: bool = False) -> Any:  # noqa: ANN401
        self._check_no_secret(o)
        return super().iterencode(o, _one_shot)

    def default(self, o: Any) -> Any:
        if isinstance(o, Secret):
            raise TypeError("Refusing to serialise Secret to JSON")
        return super().default(o)

    @staticmethod
    def _check_no_secret(node: Any, depth: int = 0) -> None:
        # 깊이 상한 64는 json의 기본 재귀 한도를 본뜬 것. 64단계 이상 중첩된
        # 페이로드는 거의 버그이므로 여기서 멈추고, 순회가 끝난 뒤 json 자신이
        # RecursionError로 거부하게 둔다(우리는 그 전까지의 Secret 누출만 책임).
        if depth > 64:
            return
        if isinstance(node, Secret):
            raise TypeError("Refusing to serialise Secret to JSON")
        if isinstance(node, dict):
            for k, v in node.items():
                # 값뿐 아니라 "키"가 Secret인 병적 케이스도 막는다.
                if isinstance(k, Secret):
                    raise TypeError("Refusing to serialise Secret to JSON")
                SafeJSONEncoder._check_no_secret(v, depth + 1)
        elif isinstance(node, list | tuple | set | frozenset):
            # 모든 시퀀스/집합 컨테이너를 동일하게 재귀 검사한다.
            for v in node:
                SafeJSONEncoder._check_no_secret(v, depth + 1)
