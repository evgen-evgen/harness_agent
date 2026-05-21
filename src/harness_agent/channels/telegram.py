from __future__ import annotations

import asyncio
from contextlib import suppress

from harness_agent.channels.base import ChannelContext, IncomingMessage, MessageHandler, OutgoingMessage


class TelegramChannel:
    id = "telegram"

    def __init__(self, token: str | None, *, thinking_message: str | None = "Думаю...") -> None:
        if not token:
            raise ValueError("TELEGRAM_BOT_TOKEN is required for telegram channel")
        self._token = token
        self._thinking_message = thinking_message.strip() if thinking_message else None
        self._application = None

    async def serve(self, handler: MessageHandler, context: ChannelContext) -> None:
        try:
            from telegram import Update
            from telegram.constants import ChatAction
            from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler as TgMessageHandler, filters
        except ImportError as exc:
            raise RuntimeError(
                "Telegram channel requires optional dependency: uv sync --extra telegram"
            ) from exc

        async def start(update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
            if update.message:
                await update.message.reply_text(f"{context.agent_name} is ready.")

        async def on_text(update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
            if not update.message or not update.message.text:
                return
            user = update.effective_user
            chat = update.effective_chat
            incoming = IncomingMessage(
                text=update.message.text,
                conversation_id=str(chat.id) if chat else "telegram",
                user_id=str(user.id) if user else None,
                metadata={"channel": self.id},
            )
            thinking = None
            if self._thinking_message:
                thinking = await update.message.reply_text(self._thinking_message)
            typing_task = asyncio.create_task(self._typing_loop(chat.id, ChatAction.TYPING)) if chat else None
            try:
                outgoing = await handler(incoming)
            finally:
                if typing_task:
                    typing_task.cancel()
                    with suppress(asyncio.CancelledError):
                        await typing_task
            if thinking:
                await thinking.edit_text(outgoing.text)
            else:
                await update.message.reply_text(outgoing.text)

        application = Application.builder().token(self._token).build()
        self._application = application
        application.add_handler(CommandHandler("start", start))
        application.add_handler(TgMessageHandler(filters.TEXT & ~filters.COMMAND, on_text))
        await application.initialize()
        await application.start()
        await application.updater.start_polling()
        try:
            await asyncio.Event().wait()
        finally:
            await application.updater.stop()
            await application.stop()
            await application.shutdown()
            self._application = None

    async def send(self, message: OutgoingMessage) -> None:
        if self._application is None:
            raise RuntimeError("telegram channel is not running")
        await self._application.bot.send_message(
            chat_id=message.conversation_id,
            text=message.text,
        )

    async def _typing_loop(self, chat_id: int, action: str) -> None:
        if self._application is None:
            return
        while True:
            await self._application.bot.send_chat_action(chat_id=chat_id, action=action)
            await asyncio.sleep(4)
