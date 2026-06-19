"""
bot.py - NexaBot main entry point 🚀
Loads config, connects to MongoDB, and starts the Pyrogram client with all plugins.
"""

import logging
import asyncio
from pyrogram import Client

from config import BOT_TOKEN, BOT_NAME
from utils.database import connect_db, close_db

# ─── API credentials (Telegram API ID/Hash) ───────────────────────────────────
# Get these from https://my.telegram.org -> API Development Tools
API_ID   = 2040            # default public Telegram desktop API id (replace if you have your own)
API_HASH = "b18441a1ff607e10a989891a5462e627"   # replace with your own if available

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


app = Client(
    name="nexabot_session",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
    plugins=dict(root="plugins"),
)


async def main():
    logger.info(f"🚀 Starting {BOT_NAME}...")
    await connect_db()          # 🍃 connect MongoDB before bot starts
    await app.start()
    me = await app.get_me()
    logger.info(f"✅ {BOT_NAME} is online as @{me.username}")
    logger.info("🤖 Bot is now listening for messages...")

    try:
        await asyncio.Event().wait()    # keep running forever ♾️
    finally:
        await app.stop()
        await close_db()
        logger.info(f"🛑 {BOT_NAME} has stopped.")


if __name__ == "__main__":
    asyncio.run(main())
