from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Protocol

from pydantic import BaseModel, Field


class TaskStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class ScheduledTask(BaseModel):
    id: str
    agent: str
    prompt: str
    run_at: datetime
    session_id: str = "scheduled"
    channel_id: str | None = None
    conversation_id: str | None = None
    user_id: str | None = None
    status: TaskStatus = TaskStatus.PENDING
    result: str | None = None
    error: str | None = None
    metadata: dict[str, str] = Field(default_factory=dict)


class SchedulerStore(Protocol):
    async def add(self, task: ScheduledTask) -> ScheduledTask:
        ...

    async def list(self, *, status: TaskStatus | None = None) -> list[ScheduledTask]:
        ...

    async def due(self, now: datetime) -> list[ScheduledTask]:
        ...

    async def update(self, task: ScheduledTask) -> None:
        ...
