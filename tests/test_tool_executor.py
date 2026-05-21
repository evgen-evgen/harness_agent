from dataclasses import dataclass

import pytest

from harness_agent.cache.local import LocalJsonCacheStore
from harness_agent.config import AgentConfig
from harness_agent.metrics import JsonlMetricsSink, RunMetrics
from harness_agent.observability import Tracer
from harness_agent.risk import ToolRiskLevel
from harness_agent.tools.base import ToolResult
from harness_agent.tools.executor import ToolExecutor
from harness_agent.tools.registry import ToolRegistry


class _WriteTool:
    name = "write_tool"
    description = "Write something."
    risk_level = ToolRiskLevel.WRITE
    cacheable = False
    input_schema = {"type": "object", "properties": {}, "additionalProperties": False}

    async def run(self) -> ToolResult:
        return ToolResult(ok=True, content="written")


class _FailingCacheableTool:
    name = "failing_cacheable"
    description = "Fail but cacheable."
    risk_level = ToolRiskLevel.SAFE
    cacheable = True
    input_schema = {"type": "object", "properties": {}, "additionalProperties": False}

    async def run(self) -> ToolResult:
        return ToolResult(ok=False, content="failed")


@pytest.mark.anyio
async def test_tool_executor_blocks_disallowed_risk_level(tmp_path) -> None:
    registry = ToolRegistry()
    registry.register(_WriteTool())
    config = AgentConfig(
        name="test",
        model="test/model",
        system_prompt="system",
        allowed_tool_risk_levels=[ToolRiskLevel.SAFE],
    )
    metrics = RunMetrics(JsonlMetricsSink(tmp_path / "metrics.jsonl"), agent_name="test", model="m")

    result = await ToolExecutor(
        config=config,
        tool_registry=registry,
        cache_store=LocalJsonCacheStore(tmp_path / "cache.json"),
        guardrails=[],
    ).execute(tool_name="write_tool", arguments={}, metrics=metrics, tracer=Tracer(metrics))

    assert result.blocked
    assert "risk level 'write' is not allowed" in result.content


@pytest.mark.anyio
async def test_tool_executor_does_not_cache_failed_results(tmp_path) -> None:
    registry = ToolRegistry()
    registry.register(_FailingCacheableTool())
    config = AgentConfig(name="test", model="test/model", system_prompt="system")
    cache = LocalJsonCacheStore(tmp_path / "cache.json")
    metrics = RunMetrics(JsonlMetricsSink(tmp_path / "metrics.jsonl"), agent_name="test", model="m")

    result = await ToolExecutor(
        config=config,
        tool_registry=registry,
        cache_store=cache,
        guardrails=[],
    ).execute(tool_name="failing_cacheable", arguments={}, metrics=metrics, tracer=Tracer(metrics))

    assert result.content == "failed"
    assert await cache.get("tool:failing_cacheable", "{}") is None
