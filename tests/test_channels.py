from harness_agent.channels import default_channel_registry
from harness_agent.config import AgentConfig, RuntimeSettings


def test_default_channel_registry_exposes_telegram_and_console() -> None:
    registry = default_channel_registry()

    assert registry.names() == ["console", "telegram"]


def test_agent_config_defaults_to_telegram_channel() -> None:
    config = AgentConfig(name="test", model="test/model", system_prompt="system")

    assert config.channels == ["telegram"]


def test_telegram_channel_uses_configured_thinking_message() -> None:
    channel = default_channel_registry().create(
        "telegram",
        RuntimeSettings(
            _env_file=None,
            TELEGRAM_BOT_TOKEN="token",
            TELEGRAM_THINKING_MESSAGE="Working...",
        ),
    )

    assert channel._thinking_message == "Working..."
