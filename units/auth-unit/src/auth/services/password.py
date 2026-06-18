"""비밀번호 해싱/검증 헬퍼.

``bcrypt`` 라이브러리를 직접 쓴다 — 이식성 있고 솔트(salt, 무작위 값)를 섞는
적응형(adaptive, 비용을 올려 무차별 대입에 대응) 해시이며, 결과가 평범한 문자열
컬럼이라 SQLite와 Postgres에서 동일하게 동작한다. ``passlib``를 거치지 않고
``bcrypt``를 직접 부르는 이유: 최근 ``bcrypt``(>=4.1)가 ``passlib`` 1.7의 내부
버전 탐지를 깨뜨렸기 때문이며, 네이티브 API(``hashpw``/``checkpw``)는 안정적이다.

임포트는 지연(lazy)으로 한다. 그래야 네이티브 ``bcrypt`` 휠이 설치되지 않은
맨 로컬 체크아웃에서도 ``python -m py_compile``이나 임포트 시점 도구가 성공한다.
런타임(도커 이미지는 의존성을 선언)에서는 첫 호출이 이를 해결하고, 정말로
의존성이 없으면 보안을 조용히 약화시키는 대신 명확한 :class:`RuntimeError`를
던진다 — 평문 저장 같은 위험한 폴백을 절대 만들지 않기 위함이다.
"""

from __future__ import annotations

from typing import Any

# bcrypt는 바이트열로 동작하며 72바이트를 넘는 부분을 조용히 무시한다. 우리는
# 명시적으로 잘라서, 과도하게 긴 입력이 bcrypt>=4.1에서 예외로 터지지 않고
# 결정적으로(같은 입력→같은 처리) 해싱되게 한다.
_BCRYPT_MAX_BYTES = 72


def _bcrypt() -> Any:
    # 지연 임포트 + 명확한 실패. 의존성이 없으면 보안을 약화시키지 않고 즉시 알린다.
    try:
        import bcrypt
    except ImportError as exc:  # pragma: no cover - 의존성이 없을 때만 발생
        raise RuntimeError(
            "bcrypt is required for password hashing; install the auth-unit "
            "dependencies (see pyproject.toml)."
        ) from exc
    return bcrypt


def _encode(plain: str) -> bytes:
    # UTF-8로 인코딩한 뒤 72바이트로 자른다. 해싱·검증이 동일한 인코딩 규칙을
    # 공유해야 같은 입력이 같은 결과를 내므로, 이 헬퍼를 둘 다에서 재사용한다.
    return plain.encode("utf-8")[:_BCRYPT_MAX_BYTES]


def hash_password(plain: str) -> str:
    """``plain``의 솔트 적용 bcrypt 해시를 DB 저장에 적합한 문자열로 반환한다."""
    bcrypt = _bcrypt()
    # gensalt()가 매번 새 솔트를 만들므로 같은 비밀번호라도 해시가 매번 다르다.
    return bcrypt.hashpw(_encode(plain), bcrypt.gensalt()).decode("ascii")


def verify_password(plain: str, hashed: str | None) -> bool:
    """``plain``을 저장된 해시와 대조한다.

    저장된 해시가 없거나(OIDC 전용 사용자) 형식이 깨졌을 때 예외를 던지지 않고
    ``False``를 반환한다. 호출자는 이를 일반적인 인증 실패와 똑같이 다루면 되고,
    "해시 없음"과 "비밀번호 틀림"을 구분해 흘리지 않아 정보 노출을 막는다.
    """
    if not hashed:
        return False
    bcrypt = _bcrypt()
    try:
        return bcrypt.checkpw(_encode(plain), hashed.encode("ascii"))
    except (ValueError, TypeError):  # 형식이 깨졌거나 알 수 없는 해시
        return False
