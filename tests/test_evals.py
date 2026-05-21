from dataclasses import dataclass
from typing import Any

import pytest

from harness_agent.agent import AgentRunner
from harness_agent.cache.local import LocalJsonCacheStore
from harness_agent.config import AgentConfig, RuntimeSettings
from harness_agent.evals import EvalCase, EvalRunner
from harness_agent.memory.local import LocalJsonlMemoryStore
from harness_agent.sessions.local import LocalJsonSessionStore


@dataclass
class _Choice:
    message: Any


@dataclass
class _Response:
    choices: list[_Choice]


class _FinalClient:
    async def complete(self, **_: Any) -> _Response:
        return _Response(choices=[_Choice(message={"content": "hello world", "tool_calls": None})])


@pytest.mark.anyio
async def test_eval_runner_checks_expected_text(tmp_path) -> None:
    config = AgentConfig(name="test", model="test/model", system_prompt="system")
    runner = AgentRunner(
        config,
        chat_client=_FinalClient(),
        cache_store=LocalJsonCacheStore(tmp_path / "cache.json"),
        memory_store=LocalJsonlMemoryStore(tmp_path / "memory.jsonl"),
        session_store=LocalJsonSessionStore(tmp_path / "sessions.json"),
        settings=RuntimeSettings(_env_file=None, METRICS_PATH=tmp_path / "metrics.jsonl"),
    )

    summary = await EvalRunner(runner).run_cases(
        [EvalCase(id="contains", input="hi", expect_contains=["hello"])]
    )

    assert summary.ok
    assert summary.passed == 1

