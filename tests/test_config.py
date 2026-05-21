from pathlib import Path

from harness_agent.config import AgentConfig, RuntimeSettings


def test_agent_config_loads_prompt(tmp_path: Path) -> None:
    prompt = tmp_path / "system.md"
    prompt.write_text("System prompt", encoding="utf-8")
    config = tmp_path / "agent.yaml"
    config.write_text(
        """
name: test
model: openai/test
system_prompt: system.md
tools: []
skills: []
""",
        encoding="utf-8",
    )

    loaded = AgentConfig.from_yaml(config, settings=RuntimeSettings(_env_file=None))

    assert loaded.name == "test"
    assert loaded.system_prompt == "System prompt"

