from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class ErrorKind(StrEnum):
    CONFIG = "config_error"
    PROVIDER = "provider_error"
    GUARDRAIL = "guardrail_block"
    TOOL = "tool_error"
    CHANNEL = "channel_error"
    EVAL = "eval_error"


@dataclass(frozen=True)
class AgentError(Exception):
    kind: ErrorKind
    message: str
    retryable: bool = False
    details: dict[str, str] | None = None

    def __str__(self) -> str:
        return self.message

    def to_dict(self) -> dict[str, object]:
        return {
            "kind": self.kind.value,
            "message": self.message,
            "retryable": self.retryable,
            "details": self.details or {},
        }


class ConfigError(AgentError):
    def __init__(self, message: str, details: dict[str, str] | None = None) -> None:
        super().__init__(ErrorKind.CONFIG, message, retryable=False, details=details)


class ToolExecutionError(AgentError):
    def __init__(self, message: str, *, retryable: bool = False, details: dict[str, str] | None = None) -> None:
        super().__init__(ErrorKind.TOOL, message, retryable=retryable, details=details)


class EvalError(AgentError):
    def __init__(self, message: str, details: dict[str, str] | None = None) -> None:
        super().__init__(ErrorKind.EVAL, message, retryable=False, details=details)

