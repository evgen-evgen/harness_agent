from __future__ import annotations

from collections.abc import Callable

from harness_agent.channels.base import Channel
from harness_agent.channels.console import ConsoleChannel
from harness_agent.channels.telegram import TelegramChannel
from harness_agent.config import RuntimeSettings


class ChannelRegistry:
    def __init__(self) -> None:
        self._factories: dict[str, Callable[[RuntimeSettings], Channel]] = {}

    def register(self, channel_id: str, factory: Callable[[RuntimeSettings], Channel]) -> None:
        self._factories[channel_id] = factory

    def create(self, channel_id: str, settings: RuntimeSettings) -> Channel:
        try:
            return self._factories[channel_id](settings)
        except KeyError as exc:
            raise KeyError(f"unknown channel: {channel_id}") from exc

    def names(self) -> list[str]:
        return sorted(self._factories)


def default_channel_registry() -> ChannelRegistry:
    registry = ChannelRegistry()
    registry.register("console", lambda _: ConsoleChannel())
    registry.register(
        "telegram",
        lambda settings: TelegramChannel(
            settings.telegram_bot_token,
            thinking_message=settings.telegram_thinking_message,
        ),
    )
    return registry
