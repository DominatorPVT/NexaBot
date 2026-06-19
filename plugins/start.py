"""
plugins/start.py - /start, /help, /ping, /id commands 🚀
"""

import time
import logging
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

from config import BOT_NAME, BOT_VERSION, OWNER_ID
from utils.database import upsert_user, upsert_chat

logger = logging.getLogger(__name__)


# ─── /start 🌟 ──────────────────────────────────────────────────────────────────

@Client.on_message(filters.command("start"))
async def start_command(client: Client, message: Message):
    user = message.from_user

    # Register user in DB 👤
    await upsert_user(user.id, {
        "first_name": user.first_name,
        "username":   user.username or "",
        "is_bot":     user.is_bot,
    })

    # Register chat in DB 💬
    if message.chat:
        await upsert_chat(message.chat.id, {
            "chat_type": str(message.chat.type),
            "title":     message.chat.title or message.chat.first_name or "",
        })

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🛠 Commands", callback_data="cb_tools"),
            InlineKeyboardButton("👑 Owner", callback_data="cb_owner"),
        ],
        [
            InlineKeyboardButton("🤖 Chatbot & Stats", callback_data="cb_chatbot"),
        ],
    ])

    await message.reply_text(
        f"👋 Hello, **{user.first_name}**!\n\n"
        f"I am **{BOT_NAME}** — your intelligent Telegram companion. ✨\n\n"
        f"Use the buttons below to explore my features, or just send me a message to chat! 💬",
        reply_markup=keyboard,
    )


# ─── Callback handlers for start menu buttons 🔘 ───────────────────────────────

@Client.on_callback_query(filters.regex("^cb_tools$"))
async def cb_tools(client: Client, query: CallbackQuery):
    text = (
        "🛠 **Tools & Commands**\n\n"
        "⟦ `/start` ⟧\n↳ Wake up the bot & get a welcome ✨\n\n"
        "⟦ `/help` ⟧\n↳ See all commands & features 📋\n\n"
        "⟦ `/ping` ⟧\n↳ Check bot response time ⚡\n\n"
        "⟦ `/id` ⟧\n↳ Get user ID, chat ID & message ID 🔍\n\n"
        "⟦ `/broadcast` ⟧\n↳ Forward message to all chats 📡\n"
        "  ↳ eg: `/broadcast -pin Hello!`\n\n"
        "⟦ `/uno` ⟧\n↳ Start a UNO card game 🎴"
    )
    back_btn = InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data="cb_back_start")]])
    await query.message.edit_text(text, reply_markup=back_btn)


@Client.on_callback_query(filters.regex("^cb_chatbot$"))
async def cb_chatbot(client: Client, query: CallbackQuery):
    text = (
        "🤖 **Chatbot & Stats**\n\n"
        "⟦ `/chatbot` ⟧\n↳ Enable/disable the chatbot ⚙️\n\n"
        "⟦ `/stats` ⟧\n↳ Get complete bot stats 📊\n\n"
        "The chatbot uses AI to reply to messages in groups when enabled. 🧠"
    )
    back_btn = InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data="cb_back_start")]])
    await query.message.edit_text(text, reply_markup=back_btn)


@Client.on_callback_query(filters.regex("^cb_owner$"))
async def cb_owner(client: Client, query: CallbackQuery):
    text = (
        f"👑 **Owner Info**\n\n"
        f"Owner ID: `{OWNER_ID}`\n\n"
        f"The owner has full control over the bot, including admin management and broadcasts. 🛡️\n\n"
        f"Bot Version: `{BOT_VERSION}` 🏷️"
    )
    back_btn = InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data="cb_back_start")]])
    await query.message.edit_text(text, reply_markup=back_btn)


@Client.on_callback_query(filters.regex("^cb_back_start$"))
async def cb_back_start(client: Client, query: CallbackQuery):
    user = query.from_user
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🛠 Commands", callback_data="cb_tools"),
            InlineKeyboardButton("👑 Owner", callback_data="cb_owner"),
        ],
        [
            InlineKeyboardButton("🤖 Chatbot & Stats", callback_data="cb_chatbot"),
        ],
    ])
    await query.message.edit_text(
        f"👋 Hello, **{user.first_name}**!\n\n"
        f"I am **{BOT_NAME}** — your intelligent Telegram companion. ✨\n\n"
        f"Use the buttons below to explore my features, or just send me a message to chat! 💬",
        reply_markup=keyboard,
    )


# ─── /help 📋 ───────────────────────────────────────────────────────────────────

@Client.on_message(filters.command("help"))
async def help_command(client: Client, message: Message):
    text = (
        f"📋 **{BOT_NAME} — Command Reference**\n\n"
        "**🛠 General**\n"
        "⟦ `/start` ⟧ ↳ Wake up the bot & get a welcome ✨\n"
        "⟦ `/help` ⟧ ↳ Show this help message 📋\n"
        "⟦ `/ping` ⟧ ↳ Check bot response time ⚡\n"
        "⟦ `/id` ⟧ ↳ Get user ID, chat ID & message ID 🔍\n\n"
        "**🤖 Chatbot**\n"
        "⟦ `/chatbot` ⟧ ↳ Enable/disable the AI chatbot ⚙️\n"
        "⟦ `/stats` ⟧ ↳ Get complete bot statistics 📊\n\n"
        "**🎮 Games**\n"
        "⟦ `/uno` ⟧ ↳ Start a UNO card game 🎴\n\n"
        "**👑 Admin / Owner**\n"
        "⟦ `/broadcast` ⟧ ↳ Broadcast a message to all chats 📡\n"
        "  ↳ Usage: `/broadcast Hello!`\n"
        "  ↳ Pin option: `/broadcast -pin Hello!`\n\n"
        "💬 Just send a message in a group where I am enabled to chat with the AI!"
    )
    await message.reply_text(text)


# ─── /ping ⚡ ───────────────────────────────────────────────────────────────────

@Client.on_message(filters.command("ping"))
async def ping_command(client: Client, message: Message):
    start = time.monotonic()
    sent  = await message.reply_text("🏓 Pinging...")
    delta = (time.monotonic() - start) * 1000
    await sent.edit_text(f"🏓 Pong! Response time: **{delta:.2f} ms** ⚡")


# ─── /id 🔍 ─────────────────────────────────────────────────────────────────────

@Client.on_message(filters.command("id"))
async def id_command(client: Client, message: Message):
    user    = message.from_user
    chat    = message.chat
    msg_id  = message.id

    text = (
        f"🔍 **ID Information**\n\n"
        f"👤 User ID: `{user.id}`\n"
        f"💬 Chat ID: `{chat.id}`\n"
        f"📩 Message ID: `{msg_id}`\n"
    )

    if message.reply_to_message:
        r = message.reply_to_message
        text += (
            f"\n**↪️ Replied Message**\n"
            f"👤 User ID: `{r.from_user.id if r.from_user else 'N/A'}`\n"
            f"📩 Message ID: `{r.id}`\n"
        )

    await message.reply_text(text)
