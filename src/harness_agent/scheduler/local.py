from __future__ import annotations

from datetime import datetime
import json
from pathlib import Path

from harness_agent.scheduler.base import ScheduledTask, TaskStatus


class LocalJsonSchedulerStore:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    async def add(self, task: ScheduledTask) -> ScheduledTask:
        tasks = self._load()
        tasks[task.id] = task
        self._save(tasks)
        return task

    async def list(self, *, status: TaskStatus | None = None) -> list[ScheduledTask]:
        tasks = sorted(self._load().values(), key=lambda item: item.run_at)
        if status is None:
            return tasks
        return [task for task in tasks if task.status == status]

    async def due(self, now: datetime) -> list[ScheduledTask]:
        return [
            task
            for task in await self.list(status=TaskStatus.PENDING)
            if task.run_at <= now
        ]

    async def update(self, task: ScheduledTask) -> None:
        tasks = self._load()
        tasks[task.id] = task
        self._save(tasks)

    def _load(self) -> dict[str, ScheduledTask]:
        if not self.path.exists():
            return {}
        raw = json.loads(self.path.read_text(encoding="utf-8") or "[]")
        return {
            item["id"]: ScheduledTask.model_validate(item)
            for item in raw
        }

    def _save(self, tasks_by_id: dict[str, ScheduledTask]) -> None:
        tasks = list(tasks_by_id.values())
        payload = [
            task.model_dump(mode="json")
            for task in sorted(tasks, key=lambda item: item.run_at)
        ]
        self.path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
