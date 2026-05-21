from __future__ import annotations

from contextvars import ContextVar
from dataclasses import dataclass


@dataclass(frozen=True)
class RunContext:
    session_id: str
    channel_id: str | None = None
    conversation_id: str | None = None
    user_id: str | None = None


_current_run_context: ContextVar[RunContext | None] = ContextVar(
    "current_run_context",
    default=None,
)


def get_run_context() -> RunContext | None:
    return _current_run_context.get()


def set_run_context(context: RunContext):
    return _current_run_context.set(context)


def reset_run_context(token) -> None:
    _current_run_context.reset(token)
