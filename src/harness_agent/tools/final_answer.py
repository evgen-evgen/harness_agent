from __future__ import annotations

from typing import Any

from harness_agent.risk import ToolRiskLevel
from harness_agent.tools.base import ToolResult


class FinalAnswerTool:
    name = "final_answer"
    description = "Return the final answer to the user and stop the agent loop."
    risk_level = ToolRiskLevel.SAFE
    cacheable = False
    input_schema: dict[str, Any] = {
        "type": "object",
        "properties": {
            "answer": {
                "type": "string",
                "description": "Final user-facing answer.",
            }
        },
        "required": ["answer"],
        "additionalProperties": False,
    }

    async def run(self, answer: str) -> ToolResult:
        return ToolResult(ok=True, content=answer)
