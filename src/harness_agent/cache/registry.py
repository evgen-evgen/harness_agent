from __future__ import annotations

from collections.abc import Callable

from harness_agent.cache.base import CacheStore
from harness_agent.cache.local import LocalJsonCacheStore
from harness_agent.config import RuntimeSettings


class CacheRegistry:
    def __init__(self) -> None:
        self._factories: dict[str, Callable[[RuntimeSettings], CacheStore]] = {}

    def register(self, cache_id: str, factory: Callable[[RuntimeSettings], CacheStore]) -> None:
        self._factories[cache_id] = factory

    def create(self, cache_id: str, settings: RuntimeSettings) -> CacheStore:
        try:
            return self._factories[cache_id](settings)
        except KeyError as exc:
            raise KeyError(f"unknown cache store: {cache_id}") from exc

    def names(self) -> list[str]:
        return sorted(self._factories)


def default_cache_registry() -> CacheRegistry:
    registry = CacheRegistry()
    registry.register("local_json", lambda settings: LocalJsonCacheStore(settings.cache_path))
    return registry

