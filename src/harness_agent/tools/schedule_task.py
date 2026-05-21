from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from harness_agent.scheduler import ScheduledTask, SchedulerStore
from harness_agent.run_context import get_run_context
from harness_agent.risk import ToolRiskLevel
from harness_agent.tools.base import ToolResult


class ScheduleTaskTool:
    name = "schedule_task"
    description = "Schedule a prompt to be run by this agent later."
    risk_level = ToolRiskLevel.WRITE
    cacheable = False
    input_schema: dict[str, Any] = {
        "type": "object",
        "properties": {
            "prompt": {
                "type": "string",
                "description": "Prompt to run later.",
            },
            "run_at": {
                "type": "string",
                "description": "ISO 8601 datetime. Use timezone-aware values when possible.",
            },
            "session_id": {
                "type": "string",
                "description": "Optional session id for the scheduled run. Defaults to current session.",
            },
            "channel_id": {
                "type": "string",
                "description": "Optional delivery channel id. Defaults to current channel.",
            },
            "conversation_id": {
                "type": "string",
                "description": "Optional conversation/chat id for delivery. Defaults to current conversation.",
            },
        },
        "required": ["prompt", "run_at"],
        "additionalProperties": False,
    }

    def __init__(self, *, store: SchedulerStore, agent_name: str) -> None:
        self.store = store
        self.agent_name = agent_name

    async def run(
        self,
        prompt: str,
        run_at: str,
        session_id: str | None = None,
        channel_id: str | None = None,
        conversation_id: str | None = None,
    ) -> ToolResult:
        context = get_run_context()
        scheduled_at = self._parse_run_at(run_at)
        if scheduled_at <= datetime.now(UTC):
            return ToolResult(
                ok=False,
                content=(
                    "Cannot schedule task in the past. "
                    f"run_at={scheduled_at.isoformat()} is before current time."
                ),
            )
        task = ScheduledTask(
            id=str(uuid4()),
            agent=self.agent_name,
            prompt=prompt,
            run_at=scheduled_at,
            session_id=session_id or (context.session_id if context else "scheduled"),
            channel_id=channel_id or (context.channel_id if context else None),
            conversation_id=conversation_id or (context.conversation_id if context else None),
            user_id=context.user_id if context else None,
        )
        await self.store.add(task)
        return ToolResult(
            ok=True,
            content=f"Scheduled task {task.id} for {task.run_at.isoformat()}",
            metadata={"task_id": task.id, "run_at": task.run_at.isoformat()},
        )

    @staticmethod
    def _parse_run_at(value: str) -> datetime:
        normalized = value.replace("Z", "+00:00")
        parsed = datetime.fromisoformat(normalized)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=UTC)
        return parsed
