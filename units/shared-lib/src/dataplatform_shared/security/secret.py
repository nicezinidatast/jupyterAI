"""Secret brand — opaque wrapper that refuses to render itself in logs.

Use ``secret.reveal()`` at the exact call site that needs the plaintext (e.g.
just before passing to a DB driver). Any incidental ``str(secret)``,
``f"{secret}"``, ``pickle.dumps(secret)``, or ``json.dumps(payload)`` (when
using ``SafeJSONEncoder``) refuses to surface the value.
"""

from __future__ import annotations

import json
from typing import Any


class Secret(str):
    """Subclass of ``str`` whose default representation is redacted.

    Inheriting from ``str`` keeps ergonomic interop with type-checkers and
    libraries that expect strings while ensuring incidental serialisation
    cannot leak the value.
    """

    __slots__ = ()

    def __repr__(self) -> str:
        return "<Secret REDACTED>"

    def __str__(self) -> str:  # noqa: DUN — explicit override is intentional
        return "<Secret REDACTED>"

    def __format__(self, format_spec: str) -> str:  # noqa: ARG002
        return "<Secret REDACTED>"

    def __reduce__(self) -> Any:  # noqa: D401
        # Pickling a Secret almost certainly means it leaked into a queue
        # payload by mistake. Fail loud at the boundary.
        raise TypeError(
            "Secret values cannot be serialised; call .reveal() at the call site"
        )

    def __reduce_ex__(self, protocol: int) -> Any:  # noqa: ARG002
        raise TypeError(
            "Secret values cannot be serialised; call .reveal() at the call site"
        )

    def reveal(self) -> str:
        """Explicit accessor for the underlying string.

        Reviewers can grep for ``.reveal()`` to audit all plaintext usages.
        """
        return super().__str__()


class SafeJSONEncoder(json.JSONEncoder):
    """JSON encoder that refuses to emit ``Secret`` values anywhere in the tree.

    Use everywhere we serialise to durable storage or wire payloads::

        json.dumps(payload, cls=SafeJSONEncoder)

    Because ``Secret`` inherits from ``str``, the default encoder would emit
    the plaintext silently. This encoder walks the tree before encoding and
    raises ``TypeError`` on the first leak it finds.
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
        # Depth cap of 64 mirrors json's default recursion limit. A payload
        # nested past 64 levels is almost certainly a bug; we let json itself
        # reject it with RecursionError after our walk completes.
        if depth > 64:
            return
        if isinstance(node, Secret):
            raise TypeError("Refusing to serialise Secret to JSON")
        if isinstance(node, dict):
            for k, v in node.items():
                if isinstance(k, Secret):
                    raise TypeError("Refusing to serialise Secret to JSON")
                SafeJSONEncoder._check_no_secret(v, depth + 1)
        elif isinstance(node, list | tuple | set | frozenset):
            for v in node:
                SafeJSONEncoder._check_no_secret(v, depth + 1)
