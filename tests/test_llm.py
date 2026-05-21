from harness_agent.config import RuntimeSettings
from harness_agent.llm import LiteLLMChatClient
from harness_agent.messages import ChatMessage


def test_litellm_client_builds_provider_override_payload() -> None:
    settings = RuntimeSettings(
        _env_file=None,
        LITELLM_API_KEY="test-key",
        LITELLM_API_BASE="https://llm.example.test/v1",
        LITELLM_API_VERSION="2024-01-01",
    )
    client = LiteLLMChatClient(settings=settings)

    payload = client._build_payload(
        model="openai/gpt-5",
        messages=[ChatMessage(role="user", content="hi")],
        tools=[],
        temperature=0.1,
    )

    assert payload["model"] == "openai/gpt-5"
    assert payload["api_key"] == "test-key"
    assert payload["api_base"] == "https://llm.example.test/v1"
    assert payload["api_version"] == "2024-01-01"
