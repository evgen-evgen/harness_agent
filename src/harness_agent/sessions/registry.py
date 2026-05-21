from __future__ import annotations

from collections.abc import Callable

from harness_agent.config import RuntimeSettings
from harness_agent.sessions.base import SessionStore
from harness_agent.sessions.local import LocalJsonSessionStore


class SessionRegistry:
    def __init__(self) -> None:
        self._factories: dict[str, Callable[[RuntimeSettings], SessionStore]] = {}

    def register(self, session_id: str, factory: Callable[[RuntimeSettings], SessionStore]) -> None:
        self._factories[session_id] = factory

    def create(self, session_id: str, settings: RuntimeSettings) -> SessionStore:
        try:
            return self._factories[session_id](settings)
        except KeyError as exc:
            raise KeyError(f"unknown session store: {session_id}") from exc

    def names(self) -> list[str]:
        return sorted(self._factories)


def default_session_registry() -> SessionRegistry:
    registry = SessionRegistry()
    registry.register("local_json", lambda settings: LocalJsonSessionStore(settings.session_path))
    return registry

