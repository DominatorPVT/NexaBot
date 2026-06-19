"""
utils/database.py - MongoDB connection and helper functions 🍃
"""

from motor.motor_asyncio import AsyncIOMotorClient
from config import MONGO_URI, DB_NAME
import logging

logger = logging.getLogger(__name__)

client = None
db     = None


async def connect_db():
    """Initialize MongoDB connection. 🔌"""
    global client, db
    try:
        client = AsyncIOMotorClient(MONGO_URI)
        db = client[DB_NAME]
        await client.admin.command("ping")
        logger.info("✅ MongoDB connected successfully.")
    except Exception as e:
        logger.error(f"❌ MongoDB connection failed: {e}")
        raise


async def close_db():
    """Close MongoDB connection. 🔒"""
    global client
    if client:
        client.close()
        logger.info("👋 MongoDB connection closed.")


# ─── User helpers 👤 ───────────────────────────────────────────────────────────

async def upsert_user(user_id: int, data: dict):
    """Insert or update a user document."""
    await db.users.update_one(
        {"user_id": user_id},
        {"$set": data, "$setOnInsert": {"user_id": user_id}},
        upsert=True,
    )


async def get_user(user_id: int) -> dict | None:
    return await db.users.find_one({"user_id": user_id}, {"_id": 0})


async def get_all_users() -> list[dict]:
    return await db.users.find({}, {"_id": 0}).to_list(length=None)


async def get_user_count() -> int:
    return await db.users.count_documents({})


# ─── Chat helpers 💬 ────────────────────────────────────────────────────────────

async def upsert_chat(chat_id: int, data: dict):
    """Insert or update a chat document."""
    await db.chats.update_one(
        {"chat_id": chat_id},
        {"$set": data, "$setOnInsert": {"chat_id": chat_id}},
        upsert=True,
    )


async def get_chat(chat_id: int) -> dict | None:
    return await db.chats.find_one({"chat_id": chat_id}, {"_id": 0})


async def get_all_chats() -> list[dict]:
    return await db.chats.find({}, {"_id": 0}).to_list(length=None)


async def get_chat_count() -> int:
    return await db.chats.count_documents({})


async def is_chatbot_enabled(chat_id: int) -> bool:
    """Return True if chatbot is enabled for the given chat. ⚙️"""
    chat = await get_chat(chat_id)
    if not chat:
        return True          # enabled by default ✅
    return chat.get("chatbot_enabled", True)


async def set_chatbot_enabled(chat_id: int, value: bool):
    await upsert_chat(chat_id, {"chatbot_enabled": value})


# ─── Message counter 📊 ─────────────────────────────────────────────────────────

async def increment_message_count(chat_id: int):
    await db.chats.update_one(
        {"chat_id": chat_id},
        {"$inc": {"message_count": 1}, "$setOnInsert": {"chat_id": chat_id}},
        upsert=True,
    )


async def get_total_messages() -> int:
    pipeline = [{"$group": {"_id": None, "total": {"$sum": "$message_count"}}}]
    result = await db.chats.aggregate(pipeline).to_list(length=1)
    return result[0]["total"] if result else 0


# ─── UNO game state 🎴 ──────────────────────────────────────────────────────────

async def save_uno_game(chat_id: int, state: dict):
    await db.uno_games.update_one(
        {"chat_id": chat_id},
        {"$set": state, "$setOnInsert": {"chat_id": chat_id}},
        upsert=True,
    )


async def get_uno_game(chat_id: int) -> dict | None:
    return await db.uno_games.find_one({"chat_id": chat_id}, {"_id": 0})


async def delete_uno_game(chat_id: int):
    await db.uno_games.delete_one({"chat_id": chat_id})
