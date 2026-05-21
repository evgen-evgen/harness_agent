from __future__ import annotations

from collections.abc import Callable

from harness_agent.config import RuntimeSettings
from harness_agent.scheduler.base import SchedulerStore
from harness_agent.scheduler.local import LocalJsonSchedulerStore


class SchedulerRegistry:
    def __init__(self) -> None:
        self._factories: dict[str, Callable[[RuntimeSettings], SchedulerStore]] = {}

    def register(self, scheduler_id: str, factory: Callable[[RuntimeSettings], SchedulerStore]) -> None:
        self._factories[scheduler_id] = factory

    def create(self, scheduler_id: str, settings: RuntimeSettings) -> SchedulerStore:
        try:
            return self._factories[scheduler_id](settings)
        except KeyError as exc:
            raise KeyError(f"unknown scheduler store: {scheduler_id}") from exc

    def names(self) -> list[str]:
        return sorted(self._factories)


def default_scheduler_registry() -> SchedulerRegistry:
    registry = SchedulerRegistry()
    registry.register("local_json", lambda settings: LocalJsonSchedulerStore(settings.scheduler_path))
    return registry

