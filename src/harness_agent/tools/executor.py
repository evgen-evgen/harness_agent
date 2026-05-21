from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Any

from harness_agent.cache import CacheStore
from harness_agent.config import AgentConfig
from harness_agent.errors import ToolExecutionError
from harness_agent.guardrails import Guardrail
from harness_agent.metrics import RunMetrics
from harness_agent.observability import Tracer
from harness_agent.risk import ToolRiskLevel
from harness_agent.tools.registry import ToolRegistry


@dataclass(frozen=True)
class ToolExecutionResult:
    content: str
    tool_name: str
    blocked: bool = False
    cache_hit: bool = False


class ToolPermissionPolicy:
    def __init__(self, allowed_risk_levels: list[ToolRiskLevel]) -> None:
        self.allowed_risk_levels = set(allowed_risk_levels)

    def check(self, tool_name: str, risk_level: ToolRiskLevel) -> str | None:
        if risk_level not in self.allowed_risk_levels:
            return f"tool '{tool_name}' risk level '{risk_level.value}' is not allowed"
        return None


class ToolExecutor:
    def __init__(
        self,
        *,
        config: AgentConfig,
        tool_registry: ToolRegistry,
        cache_store: CacheStore,
        guardrails: list[Guardrail],
    ) -> None:
        self.config = config
        self.tool_registry = tool_registry
        self.cache_store = cache_store
        self.guardrails = guardrails
        self.permission_policy = ToolPermissionPolicy(config.allowed_tool_risk_levels)

    async def execute(
        self,
        *,
        tool_name: str,
        arguments: dict[str, Any],
        metrics: RunMetrics,
        tracer: Tracer,
    ) -> ToolExecutionResult:
        guardrail_block = self._check_guardrails(tool_name, arguments)
        if guardrail_block:
            metrics.event("tool_blocked", tool=tool_name, reason=guardrail_block)
            return ToolExecutionResult(
                tool_name=tool_name,
                content=f"Tool call blocked: {guardrail_block}",
                blocked=True,
            )

        tool = self.tool_registry.get(tool_name)
        permission_block = self.permission_policy.check(tool_name, tool.risk_level)
        if permission_block:
            metrics.event(
                "tool_permission_blocked",
                tool=tool_name,
                risk_level=tool.risk_level.value,
                reason=permission_block,
            )
            return ToolExecutionResult(
                tool_name=tool_name,
                content=f"Tool call blocked: {permission_block}",
                blocked=True,
            )

        metrics.tool_calls += 1
        cache_key = self._cache_key(arguments)
        cache_namespace = self._cache_namespace(tool_name, tool)
        if tool.cacheable:
            cached = await self.cache_store.get(cache_namespace, cache_key)
            if cached is not None:
                metrics.event("tool_cache_hit", tool=tool_name, risk_level=tool.risk_level.value)
                return ToolExecutionResult(
                    tool_name=tool_name,
                    content=cached,
                    cache_hit=True,
                )

        metrics.event("tool_started", tool=tool_name, risk_level=tool.risk_level.value)
        try:
            with tracer.span("tool.run", tool=tool_name, risk_level=tool.risk_level.value):
                result = await tool.run(**arguments)
            if tool.cacheable and result.ok:
                ttl_seconds = getattr(tool, "cache_ttl_seconds", self.config.cache_ttl_seconds)
                await self.cache_store.set(
                    cache_namespace,
                    self._cache_key(arguments),
                    result.content,
                    ttl_seconds=ttl_seconds,
                )
            metrics.event(
                "tool_finished",
                tool=tool_name,
                ok=result.ok,
                risk_level=tool.risk_level.value,
                metadata=result.metadata,
            )
            return ToolExecutionResult(tool_name=tool_name, content=result.content)
        except Exception as exc:
            error = ToolExecutionError(
                f"{type(exc).__name__}: {exc}",
                details={"tool": tool_name, "risk_level": tool.risk_level.value},
            )
            metrics.event("tool_failed", tool=tool_name, error=error.to_dict())
            return ToolExecutionResult(
                tool_name=tool_name,
                content=f"Tool failed: {error.message}",
            )

    def _check_guardrails(self, tool_name: str, arguments: dict[str, Any]) -> str | None:
        for guardrail in self.guardrails:
            decision = guardrail.check_tool_call(tool_name, arguments)
            if not decision.allowed:
                return decision.reason
        return None

    @staticmethod
    def _cache_key(arguments: dict[str, Any]) -> str:
        return json.dumps(arguments, ensure_ascii=False, sort_keys=True, separators=(",", ":"))

    @staticmethod
    def _cache_namespace(tool_name: str, tool: Any) -> str:
        version = getattr(tool, "cache_version", None)
        if version:
            return f"tool:{tool_name}:{version}"
        return f"tool:{tool_name}"
