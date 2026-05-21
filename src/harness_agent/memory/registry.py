from __future__ import annotations

from collections.abc import Callable

from harness_agent.config import RuntimeSettings
from harness_agent.memory.base import MemoryStore
from harness_agent.memory.local import LocalJsonlMemoryStore


class MemoryRegistry:
    def __init__(self) -> None:
        self._factories: dict[str, Callable[[RuntimeSettings], MemoryStore]] = {}

    def register(self, memory_id: str, factory: Callable[[RuntimeSettings], MemoryStore]) -> None:
        self._factories[memory_id] = factory

    def create(self, memory_id: str, settings: RuntimeSettings) -> MemoryStore:
        try:
            return self._factories[memory_id](settings)
        except KeyError as exc:
            raise KeyError(f"unknown memory store: {memory_id}") from exc

    def names(self) -> list[str]:
        return sorted(self._factories)


def default_memory_registry() -> MemoryRegistry:
    registry = MemoryRegistry()
    registry.register("local_jsonl", lambda settings: LocalJsonlMemoryStore(settings.memory_path))
    return registry
