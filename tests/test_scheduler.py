from datetime import UTC, datetime, timedelta

import pytest

from harness_agent.scheduler import LocalJsonSchedulerStore, ScheduledTask, TaskStatus
from harness_agent.tools.schedule_task import ScheduleTaskTool


@pytest.mark.anyio
async def test_local_scheduler_store_lists_due_tasks(tmp_path) -> None:
    store = LocalJsonSchedulerStore(tmp_path / "scheduled.json")
    now = datetime.now(UTC)
    due_task = ScheduledTask(id="due", agent="a", prompt="run", run_at=now - timedelta(seconds=1))
    future_task = ScheduledTask(id="future", agent="a", prompt="later", run_at=now + timedelta(days=1))

    await store.add(due_task)
    await store.add(future_task)

    due = await store.due(now)

    assert [task.id for task in due] == ["due"]


@pytest.mark.anyio
async def test_schedule_task_tool_creates_task(tmp_path) -> None:
    store = LocalJsonSchedulerStore(tmp_path / "scheduled.json")
    tool = ScheduleTaskTool(store=store, agent_name="agent")

    result = await tool.run("do it", "2030-01-01T00:00:00Z", session_id="chat-1")

    tasks = await store.list(status=TaskStatus.PENDING)
    assert result.ok
    assert len(tasks) == 1
    assert tasks[0].prompt == "do it"
    assert tasks[0].session_id == "chat-1"


@pytest.mark.anyio
async def test_schedule_task_tool_rejects_past_time(tmp_path) -> None:
    store = LocalJsonSchedulerStore(tmp_path / "scheduled.json")
    tool = ScheduleTaskTool(store=store, agent_name="agent")

    result = await tool.run("do it", "2020-01-01T00:00:00Z", session_id="chat-1")

    assert not result.ok
    assert "Cannot schedule task in the past" in result.content
    assert await store.list() == []


@pytest.mark.anyio
async def test_local_scheduler_store_sees_tasks_added_by_another_instance(tmp_path) -> None:
    path = tmp_path / "scheduled.json"
    loop_store = LocalJsonSchedulerStore(path)
    tool_store = LocalJsonSchedulerStore(path)
    now = datetime.now(UTC)

    await tool_store.add(
        ScheduledTask(
            id="due",
            agent="a",
            prompt="run",
            run_at=now - timedelta(seconds=1),
        )
    )

    due = await loop_store.due(now)

    assert [task.id for task in due] == ["due"]
