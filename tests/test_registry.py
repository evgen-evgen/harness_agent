from harness_agent.cache import default_cache_registry
from harness_agent.guardrails import default_guardrail_registry
from harness_agent.memory import default_memory_registry
from harness_agent.sessions import default_session_registry
from harness_agent.skills import default_skill_registry
from harness_agent.tools import default_tool_registry
from harness_agent.config import AgentConfig, RuntimeSettings


def test_default_registries_expose_web_research() -> None:
    tools = default_tool_registry()
    skills = default_skill_registry()

    assert "final_answer" in tools.names()
    assert "web_search" in tools.names()
    assert skills.get("web_research").tools == ["web_search"]
    assert default_guardrail_registry().names() == ["default"]
    assert default_cache_registry().names() == ["local_json"]
    assert default_memory_registry().names() == ["local_jsonl"]
    assert default_session_registry().names() == ["local_json"]


def test_default_tool_registry_with_agent_exposes_schedule_task(tmp_path) -> None:
    config = AgentConfig(
        name="test",
        model="test/model",
        system_prompt="system",
        tools=["schedule_task"],
    )
    settings = RuntimeSettings(_env_file=None, SCHEDULER_PATH=tmp_path / "tasks.json")

    names = default_tool_registry(config, settings).names()
    assert "schedule_task" in names
    assert "filesystem" in names
