from __future__ import annotations

from typing import Any, Protocol

from litellm import acompletion

from harness_agent.config import RuntimeSettings
from harness_agent.messages import ChatMessage


class ChatClient(Protocol):
    async def complete(
        self,
        *,
        model: str,
        messages: list[ChatMessage],
        tools: list[dict[str, Any]],
        temperature: float,
    ) -> Any:
        ...


class LiteLLMChatClient:
    def __init__(self, settings: RuntimeSettings | None = None) -> None:
        self.settings = settings or RuntimeSettings()

    async def complete(
        self,
        *,
        model: str,
        messages: list[ChatMessage],
        tools: list[dict[str, Any]],
        temperature: float,
    ) -> Any:
        return await acompletion(
            **self._build_payload(
                model=model,
                messages=messages,
                tools=tools,
                temperature=temperature,
            )
        )

    def _build_payload(
        self,
        *,
        model: str,
        messages: list[ChatMessage],
        tools: list[dict[str, Any]],
        temperature: float,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "model": model,
            "messages": [message.model_dump(exclude_none=True) for message in messages],
            "temperature": temperature,
        }
        if self.settings.litellm_api_key:
            payload["api_key"] = self.settings.litellm_api_key
        if self.settings.litellm_api_base:
            payload["api_base"] = self.settings.litellm_api_base
        if self.settings.litellm_api_version:
            payload["api_version"] = self.settings.litellm_api_version
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"
        return payload
