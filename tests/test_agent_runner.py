from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pytest

from harness_agent.agent import AgentRunner
from harness_agent.cache.local import LocalJsonCacheStore
from harness_agent.config import AgentConfig, RuntimeSettings
from harness_agent.memory.local import LocalJsonlMemoryStore
from harness_agent.sessions.base import SessionMessage
from harness_agent.sessions.local import LocalJsonSessionStore
from harness_agent.risk import ToolRiskLevel
from harness_agent.tools.base import ToolResult
from harness_agent.tools.registry import ToolRegistry


@dataclass
class _Choice:
    message: Any


@dataclass
class _Response:
    choices: list[_Choice]


class _FakeChatClient:
    def __init__(self) -> None:
        self.calls = 0
        self.seen_messages: list[Any] = []

    async def complete(self, **kwargs: Any) -> _Response:
        self.calls += 1
        self.seen_messages.append(list(kwargs["messages"]))
        if self.calls == 1:
            return _Response(
                choices=[
                    _Choice(
                        message={
                            "content": "",
                            "tool_calls": [
                                {
                                    "id": "call_1",
                                    "type": "function",
                                    "function": {
                                        "name": "echo",
                                        "arguments": '{"text": "hello"}',
                                    },
                                }
                            ],
                        }
                    )
                ]
            )
        return _Response(choices=[_Choice(message={"content": "done", "tool_calls": None})])


class _FinalAnswerChatClient:
    def __init__(self) -> None:
        self.calls = 0

    async def complete(self, **_: Any) -> _Response:
        self.calls += 1
        return _Response(
            choices=[
                _Choice(
                    message={
                        "content": "",
                        "tool_calls": [
                            {
                                "id": "call_final",
                                "type": "function",
                                "function": {
                                    "name": "final_answer",
                                    "arguments": '{"answer": "final via tool"}',
                                },
                            }
                        ],
                    }
                )
            ]
        )


class _EchoTool:
    name = "echo"
    description = "Echo text."
    risk_level = ToolRiskLevel.SAFE
    cacheable = True
    input_schema = {
        "type": "object",
        "properties": {"text": {"type": "string"}},
        "required": ["text"],
    }

    async def run(self, text: str) -> ToolResult:
        return ToolResult(ok=True, content=text)


@pytest.mark.anyio
async def test_agent_runner_executes_tool_call(tmp_path) -> None:
    registry = ToolRegistry()
    registry.register(_EchoTool())
    client = _FakeChatClient()
    config = AgentConfig(
        name="test",
        model="test/model",
        system_prompt="system",
        tools=["echo"],
        max_iterations=3,
    )

    result = await AgentRunner(
        config,
        chat_client=client,
        tool_registry=registry,
        cache_store=LocalJsonCacheStore(tmp_path / "cache.json"),
        memory_store=LocalJsonlMemoryStore(tmp_path / "memory.jsonl"),
        session_store=LocalJsonSessionStore(tmp_path / "sessions.json"),
        settings=RuntimeSettings(_env_file=None, METRICS_PATH=tmp_path / "metrics.jsonl"),
    ).run("hi")

    assert result.final == "done"
    assert client.calls == 2
    assert client.seen_messages[1][-2].tool_calls is not None
    assert client.seen_messages[1][-1].role == "tool"


@pytest.mark.anyio
async def test_agent_runner_uses_cached_tool_result(tmp_path) -> None:
    registry = ToolRegistry()
    registry.register(_EchoTool())
    client = _FakeChatClient()
    cache = LocalJsonCacheStore(tmp_path / "cache.json")
    await cache.set("tool:echo", '{"text":"hello"}', "cached hello")
    config = AgentConfig(
        name="test",
        model="test/model",
        system_prompt="system",
        tools=["echo"],
        max_iterations=3,
    )

    result = await AgentRunner(
        config,
        chat_client=client,
        tool_registry=registry,
        cache_store=cache,
        memory_store=LocalJsonlMemoryStore(tmp_path / "memory.jsonl"),
        session_store=LocalJsonSessionStore(tmp_path / "sessions.json"),
        settings=RuntimeSettings(_env_file=None, METRICS_PATH=tmp_path / "metrics.jsonl"),
    ).run("hi")

    assert result.final == "done"
    assert client.seen_messages[1][-1].content == "cached hello"


@pytest.mark.anyio
async def test_agent_runner_includes_session_history(tmp_path) -> None:
    registry = ToolRegistry()
    registry.register(_EchoTool())
    client = _FakeChatClient()
    sessions = LocalJsonSessionStore(tmp_path / "sessions.json")
    await sessions.append("chat-1", SessionMessage(role="user", content="previous user"))
    await sessions.append("chat-1", SessionMessage(role="assistant", content="previous assistant"))
    config = AgentConfig(
        name="test",
        model="test/model",
        system_prompt="system",
        tools=["echo"],
        max_iterations=3,
    )

    await AgentRunner(
        config,
        chat_client=client,
        tool_registry=registry,
        cache_store=LocalJsonCacheStore(tmp_path / "cache.json"),
        memory_store=LocalJsonlMemoryStore(tmp_path / "memory.jsonl"),
        session_store=sessions,
        settings=RuntimeSettings(_env_file=None, METRICS_PATH=tmp_path / "metrics.jsonl"),
    ).run("current", session_id="chat-1")

    first_call_messages = client.seen_messages[0]
    assert [message.content for message in first_call_messages[1:4]] == [
        "previous user",
        "previous assistant",
        "current",
    ]


@pytest.mark.anyio
async def test_agent_runner_stops_on_final_answer_tool(tmp_path) -> None:
    client = _FinalAnswerChatClient()
    config = AgentConfig(
        name="test",
        model="test/model",
        system_prompt="system",
        tools=["final_answer"],
        max_iterations=3,
    )

    result = await AgentRunner(
        config,
        chat_client=client,
        cache_store=LocalJsonCacheStore(tmp_path / "cache.json"),
        memory_store=LocalJsonlMemoryStore(tmp_path / "memory.jsonl"),
        session_store=LocalJsonSessionStore(tmp_path / "sessions.json"),
        settings=RuntimeSettings(_env_file=None, METRICS_PATH=tmp_path / "metrics.jsonl"),
    ).run("hi")

    assert result.final == "final via tool"
    assert result.iterations == 1
    assert client.calls == 1
