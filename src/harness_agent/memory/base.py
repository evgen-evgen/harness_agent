from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol


@dataclass(frozen=True)
class MemoryRecord:
    content: str
    score: float = 0.0
    metadata: dict[str, str] = field(default_factory=dict)


class MemoryStore(Protocol):
    async def add(self, content: str, metadata: dict[str, str] | None = None) -> None:
        ...

    async def search(self, query: str, limit: int) -> list[MemoryRecord]:
        ...

