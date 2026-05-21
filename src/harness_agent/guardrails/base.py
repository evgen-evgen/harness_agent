from __future__ import annotations

from typing import Any, Protocol

from pydantic import BaseModel


class GuardrailDecision(BaseModel):
    allowed: bool
    reason: str | None = None
    replacement: str | None = None


class Guardrail(Protocol):
    id: str

    def check_user_input(self, text: str) -> GuardrailDecision:
        ...

    def check_tool_call(self, tool_name: str, arguments: dict[str, Any]) -> GuardrailDecision:
        ...

    def check_output(self, text: str) -> GuardrailDecision:
        ...

