from __future__ import annotations

from dataclasses import dataclass, field
from typing import Awaitable, Callable, Protocol


@dataclass(frozen=True)
class IncomingMessage:
    text: str
    conversation_id: str
    user_id: str | None = None
    metadata: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class OutgoingMessage:
    text: str
    conversation_id: str
    metadata: dict[str, str] = field(default_factory=dict)


MessageHandler = Callable[[IncomingMessage], Awaitable[OutgoingMessage]]


@dataclass(frozen=True)
class ChannelContext:
    agent_name: str


class Channel(Protocol):
    id: str

    async def serve(self, handler: MessageHandler, context: ChannelContext) -> None:
        ...

    async def send(self, message: OutgoingMessage) -> None:
        ...
