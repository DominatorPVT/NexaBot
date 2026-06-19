"""
plugins/chatbot.py - AI chatbot with typing animation, /chatbot toggle, /stats 🤖
"""

import asyncio
import logging
from pyrogram import Client, filters
from pyrogram.types import Message

from config import OWNER_ID, ADMIN_IDS, BOT_NAME
from utils.database import (
    is_chatbot_enabled,
    set_chatbot_enabled,
    increment_message_count,
    get_user_count,
    get_chat_count,
    get_total_messages,
    upsert_user,
    upsert_chat,
)
from utils.ai import get_ai_response

logger = logging.getLogger(__name__)


def is_admin(user_id: int) -> bool:
    return user_id == OWNER_ID or user_id in ADMIN_IDS


# ─── /chatbot — toggle ⚙️ ───────────────────────────────────────────────────────

@Client.on_message(filters.command("chatbot") & filters.group)
async def chatbot_toggle(client: Client, message: Message):
    user = message.from_user

    # Only admins/owner can toggle 🛡️
    if not is_admin(user.id):
        member = await client.get_chat_member(message.chat.id, user.id)
        from pyrogram.enums import ChatMemberStatus
        if member.status not in (ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER):
            return await message.reply_text("🚫 Only group admins can toggle the chatbot.")

    chat_id  = message.chat.id
    enabled  = await is_chatbot_enabled(chat_id)
    new_val  = not enabled
    await set_chatbot_enabled(chat_id, new_val)

    status = "enabled ✅" if new_val else "disabled ❌"
    await message.reply_text(f"⚙️ Chatbot is now **{status}** for this group.")


# ─── /stats 📊 ──────────────────────────────────────────────────────────────────

@Client.on_message(filters.command("stats"))
async def stats_command(client: Client, message: Message):
    if not is_admin(message.from_user.id):
        return await message.reply_text("🚫 Only the owner or admins can view stats.")

    users    = await get_user_count()
    chats    = await get_chat_count()
    messages = await get_total_messages()

    me = await client.get_me()

    text = (
        f"📊 **{BOT_NAME} Statistics**\n\n"
        f"🤖 Bot: @{me.username}\n"
        f"👥 Total Users: `{users}`\n"
        f"💬 Total Chats: `{chats}`\n"
        f"📨 Messages Handled: `{messages}`\n"
    )
    await message.reply_text(text)


# ─── Typing animation helper ⌨️ ────────────────────────────────────────────────

TYPING_FRAMES = ["⌨️ Thinking.", "⌨️ Thinking..", "⌨️ Thinking..."]


async def send_typing_animation(message: Message) -> Message:
    """Send a placeholder message and animate typing dots. ⌨️"""
    sent = await message.reply_text(TYPING_FRAMES[0])
    for frame in TYPING_FRAMES[1:]:
        await asyncio.sleep(0.5)
        await sent.edit_text(frame)
    return sent


# ─── Main chatbot handler 💬 ────────────────────────────────────────────────────

@Client.on_message(
    filters.text
    & ~filters.command(["start", "help", "ping", "id", "broadcast", "chatbot", "stats", "uno"])
    & (filters.group | filters.private)
)
async def chatbot_handler(client: Client, message: Message):
    user = message.from_user
    if not user or user.is_bot:
        return

    chat_id = message.chat.id
    from pyrogram.enums import ChatType

    # In groups: only reply if chatbot is enabled AND the message mentions the bot or is a reply to the bot 🤖
    if message.chat.type in (ChatType.GROUP, ChatType.SUPERGROUP):
        if not await is_chatbot_enabled(chat_id):
            return

        me = await client.get_me()
        is_reply_to_bot = (
            message.reply_to_message
            and message.reply_to_message.from_user
            and message.reply_to_message.from_user.id == me.id
        )
        mentioned = me.username and f"@{me.username.lower()}" in message.text.lower()

        if not is_reply_to_bot and not mentioned:
            return

    # Register user & chat 📝
    await upsert_user(user.id, {
        "first_name": user.first_name,
        "username":   user.username or "",
    })
    await upsert_chat(chat_id, {
        "chat_type": str(message.chat.type),
        "title":     message.chat.title or message.chat.first_name or "",
    })
    await increment_message_count(chat_id)

    # Typing animation ⌨️
    typing_msg = await send_typing_animation(message)

    # Get AI response 🧠
    response = await get_ai_response(message.text, user.first_name)

    await typing_msg.edit_text(response)
