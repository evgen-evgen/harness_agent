from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest

from harness_agent.channels import IncomingMessage, OutgoingMessage
from harness_agent.config import AgentConfig, RuntimeSettings
from harness_agent.runtime import AgentRuntime
from harness_agent.scheduler import ScheduledTask, TaskStatus
from harness_agent.tools.schedule_task import ScheduleTaskTool
from harness_agent.run_context import RunContext, reset_run_context, set_run_context


@dataclass
class _Choice:
    message: Any


@dataclass
class _Response:
    choices: list[_Choice]


class _FinalClient:
    async def complete(self, **_: Any) -> _Response:
        return _Response(choices=[_Choice(message={"content": "scheduled done", "tool_calls": None})])


class _FakeChannel:
    id = "fake"

    def __init__(self) -> None:
        self.sent: list[OutgoingMessage] = []

    async def serve(self, handler, context) -> None:
        return None

    async def send(self, message: OutgoingMessage) -> None:
        self.sent.append(message)


def _settings(tmp_path) -> RuntimeSettings:
    return RuntimeSettings(
        _env_file=None,
        METRICS_PATH=tmp_path / "metrics.jsonl",
        CACHE_PATH=tmp_path / "cache.json",
        MEMORY_PATH=tmp_path / "memory.jsonl",
        SESSION_PATH=tmp_path / "sessions.json",
        SCHEDULER_PATH=tmp_path / "scheduled.json",
        SCHEDULER_POLL_SECONDS=0.01,
    )


def test_runtime_session_id_includes_channel_conversation_and_user() -> None:
    message = IncomingMessage(
        text="hi",
        conversation_id="chat-1",
        user_id="user-1",
        metadata={"channel": "telegram"},
    )

    assert AgentRuntime.session_id_for(message) == "telegram:chat-1:user-1"


@pytest.mark.anyio
async def test_schedule_task_tool_uses_current_run_context(tmp_path) -> None:
    settings = _settings(tmp_path)
    runtime = AgentRuntime(
        AgentConfig(
            name="test",
            model="test/model",
            system_prompt="system",
            scheduler="local_json",
        ),
        settings=settings,
    )
    tool = ScheduleTaskTool(store=runtime.scheduler_store, agent_name="test")
    token = set_run_context(
        RunContext(
            session_id="telegram:chat:user",
            channel_id="telegram",
            conversation_id="chat",
            user_id="user",
        )
    )
    try:
        await tool.run("later", (datetime.now(UTC) + timedelta(days=1)).isoformat())
    finally:
        reset_run_context(token)

    tasks = await runtime.scheduler_store.list(status=TaskStatus.PENDING)
    assert tasks[0].session_id == "telegram:chat:user"
    assert tasks[0].channel_id == "telegram"
    assert tasks[0].conversation_id == "chat"
    assert tasks[0].user_id == "user"


@pytest.mark.anyio
async def test_runtime_run_due_once_delivers_to_channel(tmp_path) -> None:
    settings = _settings(tmp_path)
    config = AgentConfig(
        name="test",
        model="test/model",
        system_prompt="system",
        scheduler="local_json",
    )
    runtime = AgentRuntime(config, settings=settings)
    runtime.runner.chat_client = _FinalClient()
    await runtime.scheduler_store.add(
        ScheduledTask(
            id="task-1",
            agent="test",
            prompt="do it",
            run_at=datetime.now(UTC) - timedelta(seconds=1),
            session_id="fake:chat:user",
            channel_id="fake",
            conversation_id="chat",
            user_id="user",
        )
    )
    channel = _FakeChannel()

    completed = await runtime.run_due_once(channel)
    tasks = await runtime.scheduler_store.list()

    assert completed == 1
    assert tasks[0].status == TaskStatus.COMPLETED
    assert channel.sent[0].conversation_id == "chat"
    assert channel.sent[0].text == "scheduled done"
