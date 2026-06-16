"""Password hashing/verification helpers.

Uses the ``bcrypt`` library directly — a portable, salted, adaptive hash whose
output is a plain string column, so it works identically on SQLite and
Postgres. We call ``bcrypt`` rather than going through ``passlib`` because
recent ``bcrypt`` (>=4.1) broke ``passlib`` 1.7's internal version probing; the
native API (``hashpw`` / ``checkpw``) is stable.

The import is performed lazily so ``python -m py_compile`` and import-time
tooling succeed even when the optional native ``bcrypt`` wheel is not installed
in a bare local checkout. At runtime (the docker image declares the dependency)
the first call resolves it; a genuinely missing dependency raises a clear
:class:`RuntimeError` rather than silently degrading security.
"""

from __future__ import annotations

from typing import Any

# bcrypt operates on bytes and silently ignores anything past 72 bytes; we
# truncate explicitly so over-long inputs hash deterministically instead of
# raising on bcrypt>=4.1.
_BCRYPT_MAX_BYTES = 72


def _bcrypt() -> Any:
    try:
        import bcrypt
    except ImportError as exc:  # pragma: no cover - only without the dep
        raise RuntimeError(
            "bcrypt is required for password hashing; install the auth-unit "
            "dependencies (see pyproject.toml)."
        ) from exc
    return bcrypt


def _encode(plain: str) -> bytes:
    return plain.encode("utf-8")[:_BCRYPT_MAX_BYTES]


def hash_password(plain: str) -> str:
    """Return a salted bcrypt hash of ``plain`` suitable for DB storage."""
    bcrypt = _bcrypt()
    return bcrypt.hashpw(_encode(plain), bcrypt.gensalt()).decode("ascii")


def verify_password(plain: str, hashed: str | None) -> bool:
    """Check ``plain`` against a stored hash.

    Returns ``False`` (never raises) when there is no stored hash (OIDC-only
    user) or the hash is malformed, so callers can treat it as a plain auth
    failure without leaking which case occurred.
    """
    if not hashed:
        return False
    bcrypt = _bcrypt()
    try:
        return bcrypt.checkpw(_encode(plain), hashed.encode("ascii"))
    except (ValueError, TypeError):  # malformed/unknown hash
        return False
