from __future__ import annotations

from rich.console import Console

from harness_agent.channels.base import ChannelContext, IncomingMessage, MessageHandler, OutgoingMessage


class ConsoleChannel:
    id = "console"

    def __init__(self) -> None:
        self._console = Console()

    async def serve(self, handler: MessageHandler, context: ChannelContext) -> None:
        self._console.print(f"Serving {context.agent_name} on console. Type /exit to stop.")
        while True:
            text = self._console.input("> ").strip()
            if text in {"/exit", "/quit"}:
                return
            if not text:
                continue
            response = await handler(
                IncomingMessage(
                    text=text,
                    conversation_id="console",
                    user_id="local",
                    metadata={"channel": self.id},
                )
            )
            self._console.print(response.text)

    async def send(self, message: OutgoingMessage) -> None:
        self._console.print(f"[scheduled:{message.conversation_id}] {message.text}")
