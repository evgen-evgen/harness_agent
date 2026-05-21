from __future__ import annotations

import re


class MemoryPolicy:
    def __init__(self, max_chars: int, min_meaningful_chars: int = 40) -> None:
        self.max_chars = max_chars
        self.min_meaningful_chars = min_meaningful_chars
        self._secret_patterns = [
            re.compile(r"\b(sk-[A-Za-z0-9_-]{20,})\b"),
            re.compile(
                r"\b([A-Za-z0-9_]*API[_-]?KEY[A-Za-z0-9_]*\s*=\s*[^\s]+)\b",
                re.IGNORECASE,
            ),
        ]

    def prepare_dialogue_memory(self, user_input: str, assistant_output: str) -> str | None:
        user = user_input.strip()
        assistant = assistant_output.strip()
        if len(user) + len(assistant) < self.min_meaningful_chars:
            return None
        text = self._summarize_dialogue(user, assistant)
        text = self._redact(text)
        if len(text) <= self.max_chars:
            return text
        return text[: self.max_chars].rstrip() + "\n[TRUNCATED]"

    @staticmethod
    def _summarize_dialogue(user_input: str, assistant_output: str) -> str:
        return (
            "Dialogue memory candidate:\n"
            f"- User asked: {user_input}\n"
            f"- Assistant answered: {assistant_output}"
        )

    def _redact(self, text: str) -> str:
        redacted = text
        for pattern in self._secret_patterns:
            redacted = pattern.sub("[REDACTED_SECRET]", redacted)
        return redacted
