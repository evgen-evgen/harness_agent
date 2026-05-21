from __future__ import annotations

from collections.abc import Callable

from harness_agent.guardrails.base import Guardrail
from harness_agent.guardrails.defaults import DefaultGuardrail


class GuardrailRegistry:
    def __init__(self) -> None:
        self._factories: dict[str, Callable[[], Guardrail]] = {}

    def register(self, guardrail_id: str, factory: Callable[[], Guardrail]) -> None:
        self._factories[guardrail_id] = factory

    def create(self, guardrail_id: str) -> Guardrail:
        try:
            return self._factories[guardrail_id]()
        except KeyError as exc:
            raise KeyError(f"unknown guardrail: {guardrail_id}") from exc

    def select(self, ids: list[str]) -> list[Guardrail]:
        return [self.create(guardrail_id) for guardrail_id in ids]

    def names(self) -> list[str]:
        return sorted(self._factories)


def default_guardrail_registry() -> GuardrailRegistry:
    registry = GuardrailRegistry()
    registry.register("default", DefaultGuardrail)
    return registry
