import asyncio
import os
from importlib import import_module

import httpx

BACKEND_CHAT_URL = os.getenv("BACKEND_CHAT_URL", "http://localhost:8000/chat")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
BACKEND_BEARER_TOKEN = os.getenv("BACKEND_BEARER_TOKEN", "")


async def start(update, _) -> None:
    if update.message:
        await update.message.reply_text("Send a message and I will ask the AI backend.")


async def chat_proxy(update, _) -> None:
    if not update.message or not update.message.text:
        return

    payload = {"message": update.message.text}
    headers = {
        "Content-Type": "application/json",
        "Accept": "text/event-stream",
    }
    if BACKEND_BEARER_TOKEN:
        headers["Authorization"] = f"Bearer {BACKEND_BEARER_TOKEN}"

    assistant_text = []
    async with httpx.AsyncClient(timeout=120.0) as client:
        async with client.stream("POST", BACKEND_CHAT_URL, json=payload, headers=headers) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if not line.startswith("data:"):
                    continue
                assistant_text.append(line[5:].strip())

    # Keep Telegram response concise and human-readable.
    merged = "\n".join(assistant_text)
    await update.message.reply_text(merged[:3800] if merged else "No response")


async def run_bot() -> None:
    if not TELEGRAM_BOT_TOKEN:
        raise RuntimeError("Missing TELEGRAM_BOT_TOKEN")

    telegram_ext = import_module("telegram.ext")
    Application = getattr(telegram_ext, "Application")
    CommandHandler = getattr(telegram_ext, "CommandHandler")
    ContextTypes = getattr(telegram_ext, "ContextTypes")
    MessageHandler = getattr(telegram_ext, "MessageHandler")
    filters = getattr(telegram_ext, "filters")

    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, chat_proxy))

    await application.initialize()
    await application.start()
    await application.updater.start_polling()


if __name__ == "__main__":
    asyncio.run(run_bot())
