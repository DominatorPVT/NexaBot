"""
bot.py - NexaBot main entry point 🚀
Loads config, connects to MongoDB, and starts the Pyrogram client with all plugins.
"""

import sys
import subprocess
import importlib
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# ─── Auto dependency check ──────────────────────────────────────────────────
# Reads requirements.txt, checks if each package is installed, and if any are
# missing, logs it clearly and tries to auto-install them. If installation
# fails, the bot logs the error and exits instead of crashing randomly later.

# Maps the pip package name (as written in requirements.txt) to the actual
# importable module name, since they don't always match.
PIP_TO_IMPORT_NAME = {
    "pyrogram": "pyrogram",
    "tgcrypto": "tgcrypto",
    "motor": "motor",
    "aiohttp": "aiohttp",
}


def check_and_install_requirements(requirements_file: str = "requirements.txt"):
    try:
        with open(requirements_file, "r") as f:
            lines = [line.strip() for line in f if line.strip() and not line.startswith("#")]
    except FileNotFoundError:
        logger.error(f"❌ {requirements_file} not found. Cannot verify dependencies.")
        sys.exit(1)

    missing = []

    for line in lines:
        # Strip version specifiers like ==, >=, etc. to get the bare package name
        pkg_name = line.split("==")[0].split(">=")[0].split("<=")[0].strip()
        import_name = PIP_TO_IMPORT_NAME.get(pkg_name.lower(), pkg_name.lower())

        try:
            importlib.import_module(import_name)
        except ImportError:
            missing.append(line)

    if not missing:
        logger.info("✅ All required packages are already installed.")
        return

    logger.warning(f"⚠️ Missing required package(s): {', '.join(missing)}")
    logger.info("📦 Attempting to auto-install missing packages...")

    for pkg in missing:
        logger.info(f"📥 Installing {pkg} ...")
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", pkg],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            logger.error(f"❌ Failed to install {pkg}.")
            logger.error(result.stderr.strip())
            logger.error("🛑 Bot cannot start without this package. Shutting down.")
            sys.exit(1)
        else:
            logger.info(f"✅ Successfully installed {pkg}.")

    logger.info("✅ All missing packages installed. Continuing startup...")


check_and_install_requirements()

# ─── Now safe to import third-party packages ────────────────────────────────

import asyncio
from pyrogram import Client

from config import BOT_TOKEN, BOT_NAME
from utils.database import connect_db, close_db

# ─── API credentials (Telegram API ID/Hash) ───────────────────────────────────
# Get these from https://my.telegram.org -> API Development Tools
API_ID   = 2040            # default public Telegram desktop API id (replace if you have your own)
API_HASH = "b18441a1ff607e10a989891a5462e627"   # replace with your own if available


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
