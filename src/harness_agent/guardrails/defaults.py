from __future__ import annotations

import re
from typing import Any

from harness_agent.guardrails.base import GuardrailDecision


class DefaultGuardrail:
    id = "default"

    _blocked_input_patterns = [
        re.compile(pattern, re.IGNORECASE)
        for pattern in (
            r"ignore (all )?(previous|prior) instructions",
            r"reveal (the )?(system|developer) prompt",
            r"print (the )?(system|developer) prompt",
        )
    ]
    _secret_patterns = [
        re.compile(r"\b(sk-[A-Za-z0-9_-]{20,})\b"),
        re.compile(r"\b([A-Za-z0-9_]*API[_-]?KEY[A-Za-z0-9_]*\s*=\s*[^\s]+)\b", re.IGNORECASE),
    ]

    def check_user_input(self, text: str) -> GuardrailDecision:
        if len(text) > 30_000:
            return GuardrailDecision(allowed=False, reason="input is too long")
        for pattern in self._blocked_input_patterns:
            if pattern.search(text):
                return GuardrailDecision(allowed=False, reason="prompt extraction attempt")
        return GuardrailDecision(allowed=True)

    def check_tool_call(self, tool_name: str, arguments: dict[str, Any]) -> GuardrailDecision:
        if tool_name.startswith("_"):
            return GuardrailDecision(allowed=False, reason="private tool name")
        if len(str(arguments)) > 20_000:
            return GuardrailDecision(allowed=False, reason="tool arguments are too large")
        return GuardrailDecision(allowed=True)

    def check_output(self, text: str) -> GuardrailDecision:
        redacted = text
        for pattern in self._secret_patterns:
            redacted = pattern.sub("[REDACTED_SECRET]", redacted)
        return GuardrailDecision(allowed=True, replacement=redacted if redacted != text else None)

