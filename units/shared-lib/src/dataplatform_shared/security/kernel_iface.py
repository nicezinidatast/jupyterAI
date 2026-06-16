"""SecurityKernel Protocol — concrete impl lives in gateway-unit."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Protocol

from dataplatform_shared.errors import DomainError
from dataplatform_shared.result import Result
from dataplatform_shared.types.common import UserContext

Action = Literal["read", "execute", "write", "admin"]


@dataclass(frozen=True, slots=True)
class Resource:
    kind: Literal["connection", "notebook", "audit", "system", "credential", "share_link"]
    id: str | None = None


Decision = Literal["allow", "deny"]


class SecurityKernel(Protocol):
    """Defense in Depth (Q-AD-13=A) — call at every domain entry point."""

    async def authenticate(self, headers: dict[str, str]) -> Result[UserContext, DomainError]:
        """Resolve a UserContext from request headers."""
        ...

    async def authorize(
        self, ctx: UserContext, action: Action, resource: Resource
    ) -> Result[None, DomainError]:
        """Return Ok if allowed, Err(FORBIDDEN) otherwise."""
        ...
