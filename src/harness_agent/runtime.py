from __future__ import annotations

import asyncio
from contextlib import suppress
from datetime import UTC, datetime

from harness_agent.agent import AgentRunner
from harness_agent.channels import Channel, ChannelContext, IncomingMessage, OutgoingMessage
from harness_agent.config import AgentConfig, RuntimeSettings
from harness_agent.scheduler import TaskStatus, default_scheduler_registry


class AgentRuntime:
    def __init__(self, config: AgentConfig, *, settings: RuntimeSettings | None = None) -> None:
        self.config = config
        self.settings = settings or RuntimeSettings()
        self.runner = AgentRunner(config, settings=self.settings)
        self.scheduler_store = default_scheduler_registry().create(config.scheduler, self.settings)

    async def handle_message(self, message: IncomingMessage) -> OutgoingMessage:
        session_id = self.session_id_for(message)
        result = await self.runner.run(
            message.text,
            session_id=session_id,
            channel_id=message.metadata.get("channel"),
            conversation_id=message.conversation_id,
            user_id=message.user_id,
        )
        return OutgoingMessage(text=result.final, conversation_id=message.conversation_id)

    def channel_context(self) -> ChannelContext:
        return ChannelContext(agent_name=self.config.name)

    @staticmethod
    def session_id_for(message: IncomingMessage) -> str:
        channel = message.metadata.get("channel", "unknown")
        user = message.user_id or "anonymous"
        return f"{channel}:{message.conversation_id}:{user}"

    async def run_scheduler_loop(self, channel: Channel) -> None:
        while True:
            await self.run_due_once(channel)
            await asyncio.sleep(self.settings.scheduler_poll_seconds)

    async def run_due_once(self, channel: Channel) -> int:
        due = await self.scheduler_store.due(datetime.now(UTC))
        completed = 0
        for task in due:
            running = task.model_copy(update={"status": TaskStatus.RUNNING})
            await self.scheduler_store.update(running)
            try:
                result = await self.runner.run(
                    task.prompt,
                    session_id=task.session_id,
                    channel_id=task.channel_id,
                    conversation_id=task.conversation_id,
                    user_id=task.user_id,
                )
                completed_task = running.model_copy(
                    update={"status": TaskStatus.COMPLETED, "result": result.final}
                )
                await self.scheduler_store.update(completed_task)
                if task.conversation_id:
                    await channel.send(
                        OutgoingMessage(
                            text=result.final,
                            conversation_id=task.conversation_id,
                            metadata={"scheduled_task_id": task.id},
                        )
                    )
                completed += 1
            except Exception as exc:
                await self.scheduler_store.update(
                    running.model_copy(update={"status": TaskStatus.FAILED, "error": str(exc)})
                )
        return completed

    async def serve_with_scheduler(self, channel: Channel) -> None:
        scheduler_task = asyncio.create_task(self.run_scheduler_loop(channel))
        try:
            await channel.serve(self.handle_message, self.channel_context())
        finally:
            scheduler_task.cancel()
            with suppress(asyncio.CancelledError):
                await scheduler_task
