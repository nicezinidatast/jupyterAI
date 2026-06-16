"""Deterministic idempotency key generator.

The function MUST be pure: identical inputs always produce identical keys so
clients can retry safely. Used by data-unit (credential register), notebook-unit
(notebook save), etc.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any


def idempotency_key(user_id: str, operation: str, resource: Any) -> str:
    """Return a stable ``user:op:hash16`` identifier.

    ``resource`` is serialised with ``sort_keys=True`` so dicts in different
    insertion orders still produce the same key.
    """
    encoded = json.dumps(resource, sort_keys=True, default=str, separators=(",", ":")).encode()
    digest = hashlib.sha256(encoded).hexdigest()[:16]
    return f"{user_id}:{operation}:{digest}"
