from __future__ import annotations

from datetime import UTC, datetime

from harness_agent.agent import AgentRunner
from harness_agent.config import AgentConfig
from harness_agent.scheduler.base import SchedulerStore, TaskStatus


class ScheduledTaskRunner:
    def __init__(self, store: SchedulerStore, agent_config: AgentConfig) -> None:
        self.store = store
        self.agent_config = agent_config

    async def run_due(self, *, now: datetime | None = None) -> int:
        due = await self.store.due(now or datetime.now(UTC))
        completed = 0
        for task in due:
            running = task.model_copy(update={"status": TaskStatus.RUNNING})
            await self.store.update(running)
            try:
                result = await AgentRunner(self.agent_config).run(
                    task.prompt,
                    session_id=task.session_id,
                )
            except Exception as exc:
                await self.store.update(
                    running.model_copy(update={"status": TaskStatus.FAILED, "error": str(exc)})
                )
                continue
            await self.store.update(
                running.model_copy(
                    update={"status": TaskStatus.COMPLETED, "result": result.final}
                )
            )
            completed += 1
        return completed
