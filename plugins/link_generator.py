# Simple Direct Link Generator with Universal Shortener Support
# Clean and minimal — works with any shortener like anyshorturl.com / gplinks / tnshort etc.

import requests, random, string
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from config import LOG_CHANNEL, SHORT_URL, SHORT_API, ADMINS

# -----------------------------------------
# Helper: check if user is allowed
# -----------------------------------------
async def allowed(_, __, message):
    if message.from_user and message.from_user.id in ADMINS:
        return True
    return False


# -----------------------------------------
# Helper: shortener API (no alias)
# -----------------------------------------
def create_shortlink(short_url, short_api, long_url):
    """Generic shortener for any site supporting ?api=<API_KEY>&url=<URL>"""
    api_endpoint = f"https://{short_url}/api?api={short_api}&url={long_url}"
    try:
        res = requests.get(api_endpoint, timeout=10)
        data = res.json()
        # Try to detect correct key name automatically
        if data.get("status") == "success":
            return data.get("shortenedUrl", long_url)
        elif "shortenedUrl" in data:
            return data["shortenedUrl"]
        elif "shortlink" in data:
            return data["shortlink"]
        elif "short" in data:
            return data["short"]
        else:
            return long_url
    except Exception as e:
        print(f"[Shortener Error] {e}")
        return long_url


# -----------------------------------------
# Main: handle files and generate links
# -----------------------------------------
@Client.on_message((filters.document | filters.video | filters.audio | filters.photo) & filters.private & filters.create(allowed))
async def shortener_gen(bot, message):
    try:
        waiting = await message.reply_text("🔁 Uploading your file... please wait.", quote=True)
        # Copy message to your log/db channel
        post = await message.copy(LOG_CHANNEL)
        file_id = post.id

        # Build direct Telegram message link
        chat = await bot.get_chat(LOG_CHANNEL)
        if getattr(chat, "username", None):
            long_url = f"https://t.me/{chat.username}/{file_id}"
        else:
            cid = str(LOG_CHANNEL).replace("-100", "")
            long_url = f"https://t.me/c/{cid}/{file_id}"

        # Generate short link
        short_link = create_shortlink(SHORT_URL, SHORT_API, long_url)

        # Reply to user
        text = "🔴 HERE IS YOUR LINK:"
        buttons = InlineKeyboardMarkup([[InlineKeyboardButton("🔗 CLICK HERE TO OPEN", url=short_link)]])
        await waiting.delete()
        await message.reply_text(text, reply_markup=buttons, quote=True)

    except Exception as e:
        await message.reply_text(f"❌ Error: {e}", quote=True)
