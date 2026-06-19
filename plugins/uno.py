"""
plugins/uno.py - UNO card game for Telegram groups 🎴
Uses stickers from the configured sticker pack URL as card visuals.
Flow: /uno -> join button -> deal animation -> inline card picker -> game loop -> winner 🏆
"""

import re
import asyncio
import random
import logging
from pyrogram import Client, filters
from pyrogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    InlineQuery,
    InlineQueryResultArticle,
    InputTextMessageContent,
)

from config import UNO_STICKER_PACK_URL
from utils.database import save_uno_game, get_uno_game, delete_uno_game

logger = logging.getLogger(__name__)

# ─── Extract sticker pack short-name from the full URL ────────────────────────
# e.g. "https://t.me/addstickers/classic_colorblind" -> "classic_colorblind"

def _extract_pack_name(url: str) -> str:
    match = re.search(r"addstickers/([A-Za-z0-9_]+)", url)
    return match.group(1) if match else url


UNO_STICKER_PACK = _extract_pack_name(UNO_STICKER_PACK_URL)

# ─── UNO Card Definitions 🎴 ───────────────────────────────────────────────────

COLORS  = ["Red", "Green", "Blue", "Yellow"]
NUMBERS = ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9"]
SPECIALS = ["Skip", "Reverse", "+2"]
WILDS    = ["Wild", "Wild+4"]


def build_deck() -> list[str]:
    """Build a standard 108-card UNO deck. 🃏"""
    deck = []
    for color in COLORS:
        deck.append(f"{color}_0")          # one 0 per color
        for num in NUMBERS[1:]:            # two of 1-9
            deck += [f"{color}_{num}"] * 2
        for sp in SPECIALS:
            deck += [f"{color}_{sp}"] * 2
    for wild in WILDS:
        deck += [wild] * 4
    random.shuffle(deck)
    return deck


def card_display(card: str) -> str:
    """Human-readable card name with emoji color indicator."""
    color_emojis = {"Red": "🔴", "Green": "🟢", "Blue": "🔵", "Yellow": "🟡"}
    parts = card.split("_", 1)
    if len(parts) == 1:
        return f"🌈 {card}"
    color, value = parts
    emoji = color_emojis.get(color, "")
    return f"{emoji} {color} {value}"


def deal_hand(deck: list, count: int = 7) -> tuple[list, list]:
    """Deal `count` cards from the top of the deck."""
    hand = deck[:count]
    remaining = deck[count:]
    return hand, remaining


def is_valid_play(card: str, top_card: str, current_color: str) -> bool:
    """Check if a card can legally be played on top_card."""
    if card.startswith("Wild"):
        return True
    c_color, c_value = card.split("_", 1)
    t_color, t_value = top_card.split("_", 1) if "_" in top_card else (top_card, "")
    active_color = current_color or t_color
    return c_color == active_color or c_value == t_value


# ─── Game State Helpers 🗂️ ─────────────────────────────────────────────────────

def fresh_game(chat_id: int, host_id: int, host_name: str) -> dict:
    deck = build_deck()
    return {
        "chat_id":       chat_id,
        "host_id":       host_id,
        "players":       {str(host_id): {"name": host_name, "hand": []}},
        "player_order":  [str(host_id)],
        "deck":          deck,
        "discard":       [],
        "top_card":      "",
        "current_color": "",
        "current_turn":  0,
        "started":       False,
        "direction":     1,           # 1 = normal, -1 = reversed
        "join_msg_id":   None,
    }


def current_player(state: dict) -> str:
    """Return the user_id string of the current player."""
    idx = state["current_turn"] % len(state["player_order"])
    return state["player_order"][idx]


def next_turn(state: dict, skip: bool = False):
    offset = 2 if skip else 1
    state["current_turn"] = (state["current_turn"] + offset * state["direction"]) % len(state["player_order"])


# ─── /uno — start a new game 🎮 ────────────────────────────────────────────────

@Client.on_message(filters.command("uno") & filters.group)
async def uno_start(client: Client, message: Message):
    chat_id = message.chat.id
    user    = message.from_user

    existing = await get_uno_game(chat_id)
    if existing:
        return await message.reply_text(
            "⚠️ A UNO game is already in progress in this group!\n"
            "Wait for it to finish or ask the host to cancel it. ⏳"
        )

    state = fresh_game(chat_id, user.id, user.first_name)
    await save_uno_game(chat_id, state)

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Join Game", callback_data=f"uno_join_{chat_id}")],
        [InlineKeyboardButton("🚀 Start Game", callback_data=f"uno_begin_{chat_id}")],
        [InlineKeyboardButton("❌ Cancel", callback_data=f"uno_cancel_{chat_id}")],
    ])

    sent = await message.reply_text(
        f"🎴 **UNO Game**\n\n"
        f"👑 Host: **{user.first_name}**\n"
        f"👥 Players: **{user.first_name}** (1/10)\n\n"
        f"Tap **➕ Join Game** to join!\n"
        f"Host taps **🚀 Start Game** when ready (minimum 2 players).",
        reply_markup=keyboard,
    )

    state["join_msg_id"] = sent.id
    await save_uno_game(chat_id, state)


# ─── Join Game ➕ ───────────────────────────────────────────────────────────────

@Client.on_callback_query(filters.regex(r"^uno_join_(-?\d+)$"))
async def uno_join(client: Client, query: CallbackQuery):
    chat_id = int(query.matches[0].group(1))
    user    = query.from_user
    state   = await get_uno_game(chat_id)

    if not state or state.get("started"):
        return await query.answer("⚠️ No open game to join!", show_alert=True)

    uid = str(user.id)
    if uid in state["players"]:
        return await query.answer("✋ You already joined!", show_alert=True)

    if len(state["players"]) >= 10:
        return await query.answer("🚫 Game is full (max 10 players).", show_alert=True)

    state["players"][uid] = {"name": user.first_name, "hand": []}
    state["player_order"].append(uid)
    await save_uno_game(chat_id, state)
    await query.answer(f"✅ You joined the game, {user.first_name}!")

    names = ", ".join(p["name"] for p in state["players"].values())
    count = len(state["players"])

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Join Game", callback_data=f"uno_join_{chat_id}")],
        [InlineKeyboardButton("🚀 Start Game", callback_data=f"uno_begin_{chat_id}")],
        [InlineKeyboardButton("❌ Cancel", callback_data=f"uno_cancel_{chat_id}")],
    ])

    await query.message.edit_text(
        f"🎴 **UNO Game**\n\n"
        f"👑 Host: **{state['players'][str(state['host_id'])]['name']}**\n"
        f"👥 Players ({count}/10): **{names}**\n\n"
        f"Tap **➕ Join Game** to join!\n"
        f"Host taps **🚀 Start Game** when ready (minimum 2 players).",
        reply_markup=keyboard,
    )


# ─── Start Game 🚀 ──────────────────────────────────────────────────────────────

@Client.on_callback_query(filters.regex(r"^uno_begin_(-?\d+)$"))
async def uno_begin(client: Client, query: CallbackQuery):
    chat_id = int(query.matches[0].group(1))
    user    = query.from_user
    state   = await get_uno_game(chat_id)

    if not state:
        return await query.answer("⚠️ No game found.", show_alert=True)
    if user.id != state["host_id"]:
        return await query.answer("🚫 Only the host can start the game!", show_alert=True)
    if len(state["players"]) < 2:
        return await query.answer("⚠️ Need at least 2 players to start!", show_alert=True)
    if state.get("started"):
        return await query.answer("⚠️ Game already started!", show_alert=True)

    await query.message.edit_text("🃏 Dealing cards, please wait...")

    # Animate card dealing 🎬
    await asyncio.sleep(0.5)
    await query.message.edit_text("🔀 Shuffling the deck...")
    await asyncio.sleep(0.8)
    await query.message.edit_text("🎴 Dealing cards to all players...")
    await asyncio.sleep(0.8)

    # Deal 7 cards to each player
    deck = state["deck"]
    for uid in state["player_order"]:
        hand, deck = deal_hand(deck, 7)
        state["players"][uid]["hand"] = hand
    state["deck"] = deck

    # Flip first card (must not be Wild)
    top = None
    while not top or top.startswith("Wild"):
        if not deck:
            deck = build_deck()
        top  = deck.pop(0)
    state["deck"]    = deck
    state["discard"] = [top]
    state["top_card"] = top
    state["current_color"] = top.split("_")[0] if "_" in top else ""
    state["started"]       = True
    state["current_turn"]  = 0

    await save_uno_game(chat_id, state)

    first_player_id   = current_player(state)
    first_player_name = state["players"][first_player_id]["name"]

    await asyncio.sleep(0.5)

    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton(
            "🃏 Play your cards",
            switch_inline_query_current_chat=f"uno_{chat_id}",
        )
    ]])

    await query.message.edit_text(
        f"🎮 **UNO Game Started!**\n\n"
        f"✅ Cards have been dealt to all players.\n"
        f"🔝 Top card: **{card_display(top)}**\n"
        f"🎨 Active color: **{state['current_color']}**\n\n"
        f"▶️ It is **{first_player_name}**'s turn!\n\n"
        f"👉 **{first_player_name}**: tap the button below to see and play your cards.",
        reply_markup=keyboard,
    )


# ─── Cancel Game ❌ ─────────────────────────────────────────────────────────────

@Client.on_callback_query(filters.regex(r"^uno_cancel_(-?\d+)$"))
async def uno_cancel(client: Client, query: CallbackQuery):
    chat_id = int(query.matches[0].group(1))
    user    = query.from_user
    state   = await get_uno_game(chat_id)

    if not state:
        return await query.answer("⚠️ No active game.", show_alert=True)
    if user.id != state["host_id"]:
        return await query.answer("🚫 Only the host can cancel.", show_alert=True)

    await delete_uno_game(chat_id)
    await query.message.edit_text("❌ UNO game cancelled.")


# ─── Inline Query — show player's hand 🔍 ──────────────────────────────────────

@Client.on_inline_query(filters.regex(r"^uno_(-?\d+)$"))
async def uno_inline_hand(client: Client, query: InlineQuery):
    """Show the current player's hand as inline results."""
    chat_id = int(query.matches[0].group(1))
    user    = query.from_user
    state   = await get_uno_game(chat_id)

    if not state or not state.get("started"):
        return await query.answer(
            [InlineQueryResultArticle(
                id="no_game",
                title="⚠️ No active game",
                input_message_content=InputTextMessageContent("No UNO game is running."),
            )],
            cache_time=0,
        )

    uid = str(user.id)
    if uid not in state["players"]:
        return await query.answer(
            [InlineQueryResultArticle(
                id="not_in_game",
                title="🚫 You are not in this game",
                input_message_content=InputTextMessageContent("You are not a player in this game."),
            )],
            cache_time=0,
        )

    hand       = state["players"][uid]["hand"]
    top_card   = state["top_card"]
    cur_color  = state["current_color"]
    is_my_turn = current_player(state) == uid

    results = []
    for i, card in enumerate(hand):
        playable = is_valid_play(card, top_card, cur_color)
        title    = card_display(card)
        if not is_my_turn:
            desc = "⏳ Not your turn"
        elif playable:
            desc = "✅ Tap to play this card"
        else:
            desc = "🚫 Cannot play this card now"

        results.append(
            InlineQueryResultArticle(
                id=f"card_{i}",
                title=title,
                description=desc,
                input_message_content=InputTextMessageContent(
                    f"uno_play:{chat_id}:{uid}:{i}:{card}"
                ),
            )
        )

    # Draw card option 🎴
    results.append(
        InlineQueryResultArticle(
            id="draw",
            title="🎴 Draw a card",
            description="Draw 1 card from the deck",
            input_message_content=InputTextMessageContent(
                f"uno_draw:{chat_id}:{uid}"
            ),
        )
    )

    await query.answer(results, cache_time=0)


# ─── Card Play Handler 🃏 ───────────────────────────────────────────────────────

@Client.on_message(filters.regex(r"^uno_play:(-?\d+):(\d+):(\d+):(.+)$") & filters.group)
async def uno_play_card(client: Client, message: Message):
    match = re.match(r"^uno_play:(-?\d+):(\d+):(\d+):(.+)$", message.text)
    if not match:
        return

    chat_id   = int(match.group(1))
    uid       = match.group(2)
    card_idx  = int(match.group(3))
    card      = match.group(4)
    state     = await get_uno_game(chat_id)

    if not state or not state.get("started"):
        return await message.delete()

    if current_player(state) != uid or str(message.from_user.id) != uid:
        await message.delete()
        return

    hand = state["players"][uid]["hand"]
    if card_idx >= len(hand) or hand[card_idx] != card:
        await message.delete()
        return

    top_card  = state["top_card"]
    cur_color = state["current_color"]

    if not is_valid_play(card, top_card, cur_color):
        await message.reply_text(f"🚫 You cannot play {card_display(card)} now!", quote=True)
        await message.delete()
        return

    # Remove card from hand
    hand.pop(card_idx)
    state["players"][uid]["hand"] = hand
    state["discard"].append(card)
    state["top_card"] = card

    player_name = state["players"][uid]["name"]
    await message.delete()

    # Handle specials 🌀
    skip_next   = False
    draw_amount = 0
    color_change = False

    if "_" in card:
        _, value = card.split("_", 1)
        color    = card.split("_")[0]
        state["current_color"] = color

        if value == "Skip":
            skip_next = True
        elif value == "Reverse":
            state["direction"] *= -1
            if len(state["player_order"]) == 2:
                skip_next = True   # in 2-player, Reverse acts as Skip
        elif value == "+2":
            draw_amount = 2
            skip_next   = True
    elif card.startswith("Wild+4"):
        draw_amount  = 4
        skip_next    = True
        color_change = True
    elif card.startswith("Wild"):
        color_change = True

    # Wild: pick a color (auto-pick most common color in hand) 🎨
    if color_change:
        remaining_hand = hand
        color_counts   = {c: 0 for c in COLORS}
        for h_card in remaining_hand:
            if "_" in h_card:
                h_color = h_card.split("_")[0]
                if h_color in color_counts:
                    color_counts[h_color] += 1
        chosen_color = max(color_counts, key=lambda c: color_counts[c])
        state["current_color"] = chosen_color

    # Apply draw penalty to next player
    next_idx    = (state["current_turn"] + state["direction"]) % len(state["player_order"])
    next_uid    = state["player_order"][next_idx]
    next_name   = state["players"][next_uid]["name"]

    if draw_amount > 0:
        drawn = state["deck"][:draw_amount]
        state["deck"] = state["deck"][draw_amount:]
        state["players"][next_uid]["hand"].extend(drawn)

    # Check win condition 🏆
    if len(hand) == 0:
        await save_uno_game(chat_id, state)
        await _announce_winner(client, message.chat.id, player_name, next_name)
        await delete_uno_game(chat_id)
        return

    next_turn(state, skip=skip_next)
    await save_uno_game(chat_id, state)

    new_current     = current_player(state)
    new_player_name = state["players"][new_current]["name"]
    cards_left      = len(hand)

    uno_warning = "\n🔥 **UNO!** Last card!" if cards_left == 1 else ""

    play_btn = InlineKeyboardMarkup([[
        InlineKeyboardButton(
            "🃏 Play your cards",
            switch_inline_query_current_chat=f"uno_{chat_id}",
        )
    ]])

    status_lines = "\n".join(
        f"👤 {p['name']}: {len(p['hand'])} cards"
        for uid2, p in state["players"].items()
    )

    await client.send_message(
        message.chat.id,
        f"🎴 **{player_name}** played **{card_display(card)}**{uno_warning}\n\n"
        f"🔝 Top card: **{card_display(state['top_card'])}**\n"
        f"🎨 Active color: **{state['current_color']}**\n\n"
        f"📊 **Card counts:**\n{status_lines}\n\n"
        f"▶️ It is **{new_player_name}**'s turn!",
        reply_markup=play_btn,
    )


# ─── Draw Card Handler 🎴 ───────────────────────────────────────────────────────

@Client.on_message(filters.regex(r"^uno_draw:(-?\d+):(\d+)$") & filters.group)
async def uno_draw_card(client: Client, message: Message):
    match = re.match(r"^uno_draw:(-?\d+):(\d+)$", message.text)
    if not match:
        return

    chat_id = int(match.group(1))
    uid     = match.group(2)
    state   = await get_uno_game(chat_id)

    if not state or not state.get("started"):
        return await message.delete()

    if current_player(state) != uid or str(message.from_user.id) != uid:
        await message.delete()
        return

    if not state["deck"]:
        state["deck"] = build_deck()

    drawn = state["deck"].pop(0)
    state["players"][uid]["hand"].append(drawn)
    player_name = state["players"][uid]["name"]

    await message.delete()

    # Skip to next turn
    next_turn(state)
    await save_uno_game(chat_id, state)

    new_current     = current_player(state)
    new_player_name = state["players"][new_current]["name"]

    play_btn = InlineKeyboardMarkup([[
        InlineKeyboardButton(
            "🃏 Play your cards",
            switch_inline_query_current_chat=f"uno_{chat_id}",
        )
    ]])

    await client.send_message(
        message.chat.id,
        f"🎴 **{player_name}** drew a card.\n\n"
        f"🔝 Top card: **{card_display(state['top_card'])}**\n"
        f"🎨 Active color: **{state['current_color']}**\n\n"
        f"▶️ It is **{new_player_name}**'s turn!",
        reply_markup=play_btn,
    )


# ─── Winner announcement 🏆 ─────────────────────────────────────────────────────

async def _announce_winner(client: Client, chat_id: int, winner: str, loser: str):
    """Send a celebratory sticker from the configured pack, then announce results."""
    try:
        # Get the first sticker from the configured pack to use as the win sticker 🎉
        sticker_set = await client.get_stickers(UNO_STICKER_PACK)
        if sticker_set:
            await client.send_sticker(chat_id, sticker_set[0].file_id)
    except Exception as e:
        logger.warning(f"⚠️ Could not send winner sticker: {e}")

    await client.send_message(
        chat_id,
        f"🏆 **Game Over!**\n\n"
        f"🥇 Winner: **{winner}**\n"
        f"😢 Loser: **{loser}**\n\n"
        f"🎉 Congratulations to {winner}! Well played!"
    )
