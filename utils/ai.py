"""
utils/ai.py - AI API wrapper for NexaBot 🧠
The actual API endpoint lives in utils/_core.py, kept separate from config.py
so it never gets shared when config.py is shared/copied.
"""

import aiohttp
import logging
from config import BOT_NAME, CUSTOM_PROMPT
from utils._core import AI_API_URL, AI_MODEL, AI_MAX_TOKENS

logger = logging.getLogger(__name__)


async def get_ai_response(user_message: str, user_name: str = "User") -> str:
    """
    Send a message to the AI API and return the text response. 💬

    Args:
        user_message: The user's message text.
        user_name:    The user's first name for personalization.

    Returns:
        AI response string, or a friendly error message.
    """
    # Build the system prompt using the bot name from config.py
    base_prompt = CUSTOM_PROMPT.format(bot_name=BOT_NAME)
    personalized_prompt = (
        base_prompt.strip()
        + f"\n\nThe user's name is {user_name}. Address them by name when appropriate. 👋"
    )

    payload = {
        "model":      AI_MODEL,
        "max_tokens": AI_MAX_TOKENS,
        "messages": [
            {"role": "system", "content": personalized_prompt},
            {"role": "user",   "content": user_message},
        ],
    }

    url = f"{AI_API_URL}/v1/chat/completions"

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                if resp.status != 200:
                    logger.error(f"⚠️ AI API returned status {resp.status}")
                    return "Sorry, I could not process your request right now. Try again later. 🙏"

                data = await resp.json()

                # Parse standard OpenAI-compatible response
                response_text = (
                    data.get("choices", [{}])[0]
                    .get("message", {})
                    .get("content", "")
                    .strip()
                )

                if not response_text:
                    return "I did not get a response. Please try again. 🔄"

                return response_text

    except aiohttp.ClientConnectorError:
        logger.error("❌ Could not connect to AI API.")
        return "Connection to AI service failed. Please try again later. 📡"
    except Exception as e:
        logger.error(f"💥 AI API error: {e}")
        return "An unexpected error occurred. Please try again. ⚠️"
