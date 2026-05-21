from harness_agent.config import AgentConfig
from harness_agent.context import ContextBuilder
from harness_agent.memory import MemoryRecord
from harness_agent.sessions import SessionMessage
from harness_agent.skills import Skill


def test_context_builder_includes_memory_skills_session_and_user() -> None:
    config = AgentConfig(
        name="test",
        model="test/model",
        system_prompt="system",
        context_max_chars=10_000,
    )

    result = ContextBuilder(config).build(
        user_input="current",
        skills=[Skill(id="s", instructions="skill instruction")],
        memory_records=[MemoryRecord(content="remember this")],
        session_messages=[SessionMessage(role="user", content="previous")],
    )

    assert result.memory_used == 1
    assert result.session_used == 1
    assert result.messages[0].role == "system"
    assert "Current runtime time:" in str(result.messages[0].content)
    assert "remember this" in str(result.messages[0].content)
    assert "skill instruction" in str(result.messages[0].content)
    assert result.messages[-1].content == "current"


def test_context_builder_drops_old_session_when_budget_is_small() -> None:
    config = AgentConfig(
        name="test",
        model="test/model",
        system_prompt="system",
        context_max_chars=200,
        context_session_max_chars=20,
    )

    result = ContextBuilder(config).build(
        user_input="current",
        skills=[],
        memory_records=[],
        session_messages=[
            SessionMessage(role="user", content="old message that will not fit"),
            SessionMessage(role="assistant", content="new"),
        ],
    )

    assert result.session_used == 1
    assert result.session_dropped == 1
    assert result.messages[1].content == "new"
