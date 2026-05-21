from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Skill:
    id: str
    instructions: str
    tools: list[str] = field(default_factory=list)

