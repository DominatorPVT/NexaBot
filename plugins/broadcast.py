"""
plugins/broadcast.py - /broadcast command for owner/admins 📡
"""

import asyncio
import logging
from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.errors import FloodWait, UserIsBlocked, InputUserDeactivated

from config import OWNER_ID, ADMIN_IDS
from utils.database import get_all_chats

logger = logging.getLogger(__name__)


def is_admin(user_id: int) -> bool:
    return user_id == OWNER_ID or user_id in ADMIN_IDS


@Client.on_message(filters.command("broadcast"))
async def broadcast_command(client: Client, message: Message):
    if not is_admin(message.from_user.id):
        return await message.reply_text("🚫 Only the owner or admins can broadcast messages.")

    args  = message.text.split(None, 2)
    pin   = False
    text  = ""

    # Parse -pin flag 📌
    if len(args) >= 2 and args[1].lower() == "-pin":
        pin  = True
        text = args[2] if len(args) > 2 else ""
    else:
        text = " ".join(args[1:]) if len(args) > 1 else ""

    if not text and not message.reply_to_message:
        return await message.reply_text(
            "📡 **Usage:**\n"
            "`/broadcast Hello everyone!`\n"
            "`/broadcast -pin Important update!` 📌\n\n"
            "Or reply to a message with `/broadcast`."
        )

    status_msg = await message.reply_text("📡 Broadcasting...")

    chats = await get_all_chats()
    done = failed = pinned = 0

    for chat in chats:
        chat_id = chat.get("chat_id")
        if not chat_id:
            continue
        try:
            if message.reply_to_message and not text:
                sent = await message.reply_to_message.forward(chat_id)
            else:
                sent = await client.send_message(chat_id, text)

            if pin:
                try:
                    await client.pin_chat_message(chat_id, sent.id)
                    pinned += 1
                except Exception:
                    pass

            done += 1
            await asyncio.sleep(0.05)   # avoid flood ⏳

        except FloodWait as e:
            await asyncio.sleep(e.value)
        except (UserIsBlocked, InputUserDeactivated):
            failed += 1
        except Exception as exc:
            logger.warning(f"⚠️ Broadcast failed for {chat_id}: {exc}")
            failed += 1

    summary = (
        f"✅ **Broadcast complete.**\n\n"
        f"📨 Delivered: `{done}`\n"
        f"❌ Failed: `{failed}`\n"
    )
    if pin:
        summary += f"📌 Pinned: `{pinned}`\n"

    await status_msg.edit_text(summary)
