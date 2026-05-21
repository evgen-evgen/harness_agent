from __future__ import annotations

from typing import Any, Protocol

from pydantic import BaseModel, Field

from harness_agent.risk import ToolRiskLevel


class ToolResult(BaseModel):
    ok: bool
    content: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class Tool(Protocol):
    name: str
    description: str
    input_schema: dict[str, Any]
    risk_level: ToolRiskLevel
    cacheable: bool

    async def run(self, **kwargs: Any) -> ToolResult:
        ...


def tool_to_litellm_tool(tool: Tool) -> dict[str, Any]:
    return {
        "type": "function",
        "function": {
            "name": tool.name,
            "description": tool.description,
            "parameters": tool.input_schema,
        },
    }
