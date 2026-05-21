from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


Role = Literal["system", "user", "assistant", "tool"]


class ChatMessage(BaseModel):
    role: Role
    content: str | list[dict[str, Any]] | None = None
    name: str | None = None
    tool_call_id: str | None = None
    tool_calls: list[dict[str, Any]] | None = None


class AgentResult(BaseModel):
    final: str
    messages: list[ChatMessage]
    iterations: int
    metrics: dict[str, Any] = Field(default_factory=dict)
