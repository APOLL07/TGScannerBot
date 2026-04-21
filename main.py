import asyncio
import os
import sys

from dotenv import load_dotenv

load_dotenv()


async def main() -> None:
    import uvicorn
    from aiogram import Bot

    from bot.handlers import create_dispatcher
    from db.database import init_db
    from web.app import create_app

    token = os.environ.get("BOT_TOKEN")
    if not token:
        print("ERROR: BOT_TOKEN environment variable is not set.")
        sys.exit(1)

    await init_db()

    bot = Bot(token=token)
    dp = create_dispatcher()
    app = create_app()

    port = int(os.environ.get("PORT", 8000))
    config = uvicorn.Config(app, host="0.0.0.0", port=port, log_level="info")
    server = uvicorn.Server(config)

    await asyncio.gather(
        dp.start_polling(bot, allowed_updates=["message", "callback_query"]),
        server.serve(),
    )


if __name__ == "__main__":
    asyncio.run(main())
