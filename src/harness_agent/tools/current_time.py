from __future__ import annotations

from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from harness_agent.risk import ToolRiskLevel
from harness_agent.tools.base import ToolResult


class CurrentTimeTool:
    name = "current_time"
    description = "Fetch the current local time in a specified IANA timezone."
    risk_level = ToolRiskLevel.SAFE
    cacheable = False
    input_schema: dict[str, Any] = {
        "type": "object",
        "properties": {
            "timezone": {
                "type": "string",
                "description": "IANA timezone name, for example America/New_York or Europe/Minsk.",
            }
        },
        "required": ["timezone"],
        "additionalProperties": False,
    }

    async def run(self, timezone: str) -> ToolResult:
        try:
            tz = ZoneInfo(timezone)
        except ZoneInfoNotFoundError:
            return ToolResult(
                ok=False,
                content=f"Error fetching time for timezone '{timezone}': unknown timezone",
            )
        local_time = datetime.now(tz)
        return ToolResult(
            ok=True,
            content=(
                f"The current local time in {timezone} is: "
                f"{local_time.strftime('%Y-%m-%d %H:%M:%S %Z%z')}"
            ),
            metadata={"timezone": timezone, "iso": local_time.isoformat()},
        )
