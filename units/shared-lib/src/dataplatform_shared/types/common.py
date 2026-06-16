"""Common identifier types and the UserContext propagated through requests."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, NewType

# Use NewType so type checkers catch mix-ups between IDs at compile time, while
# keeping the runtime representation as a plain str/UUID-string.
UserId = NewType("UserId", str)
SessionId = NewType("SessionId", str)
CorrelationId = NewType("CorrelationId", str)

# 4 role types matching personas.md (Q-USR-1=B,D)
Role = Literal["Admin", "Analyst", "Viewer", "Auditor"]


@dataclass(frozen=True, slots=True)
class UserContext:
    """Authenticated principal passed to every domain call."""

    user_id: UserId
    roles: tuple[Role, ...]
    session_id: SessionId
    corr_id: CorrelationId

    def has_role(self, role: Role) -> bool:
        return role in self.roles
