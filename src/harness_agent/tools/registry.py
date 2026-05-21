from __future__ import annotations

from harness_agent.config import AgentConfig, RuntimeSettings
from harness_agent.scheduler import default_scheduler_registry
from harness_agent.tools.base import Tool
from harness_agent.tools.current_time import CurrentTimeTool
from harness_agent.tools.final_answer import FinalAnswerTool
from harness_agent.tools.filesystem import FilesystemTool
from harness_agent.tools.schedule_task import ScheduleTaskTool
from harness_agent.tools.web_search import WebSearchTool


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        self._tools[tool.name] = tool

    def get(self, name: str) -> Tool:
        try:
            return self._tools[name]
        except KeyError as exc:
            raise KeyError(f"unknown tool: {name}") from exc

    def select(self, names: list[str]) -> list[Tool]:
        return [self.get(name) for name in names]

    def names(self) -> list[str]:
        return sorted(self._tools)


def default_tool_registry(
    config: AgentConfig | None = None,
    settings: RuntimeSettings | None = None,
) -> ToolRegistry:
    registry = ToolRegistry()
    registry.register(CurrentTimeTool())
    registry.register(FinalAnswerTool())
    runtime = settings or RuntimeSettings()
    registry.register(
        WebSearchTool(
            brave_api_key=runtime.brave_search_api_key,
            tavily_api_key=runtime.tavily_api_key,
            cache_ttl_seconds=runtime.web_search_cache_ttl_seconds,
        )
    )
    if config is not None:
        scheduler_store = default_scheduler_registry().create(config.scheduler, runtime)
        registry.register(ScheduleTaskTool(store=scheduler_store, agent_name=config.name))
        registry.register(FilesystemTool(workspace_root=runtime.file_workspace_root))
    return registry
