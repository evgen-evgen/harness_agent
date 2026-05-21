from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, Protocol


SessionRole = Literal["user", "assistant"]


@dataclass(frozen=True)
class SessionMessage:
    role: SessionRole
    content: str
    metadata: dict[str, str] = field(default_factory=dict)


class SessionStore(Protocol):
    async def recent(self, session_id: str, limit: int) -> list[SessionMessage]:
        ...

    async def append(self, session_id: str, message: SessionMessage) -> None:
        ...

