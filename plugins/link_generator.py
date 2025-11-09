# ===============================================================
# LINK GENERATOR (Deep-Link Mode)
# Stores files privately, shares encoded bot-start links via shortener
# ===============================================================

from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from config import LOGGER, SHORT_URL, SHORT_API
import asyncio, requests, base64

# ------------------------------
# Helper: universal shortener
# ------------------------------
def create_shortlink(short_url, short_api, long_url):
    """Create short link using ?api=&url= API format"""
    api_endpoint = f"https://{short_url}/api?api={short_api}&url={long_url}"
    try:
        res = requests.get(api_endpoint, timeout=10)
        data = res.json()
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


# ===============================================================
# MAIN HANDLER: receive media → save → create deep link → shorten
# ===============================================================
@Client.on_message((filters.document | filters.video | filters.audio | filters.photo) & filters.private)
async def deep_link_generator(client: Client, message: Message):
    """
    1. Copy media to DB channel (no forward tag)
    2. Encode deep link (start=Z2V0-<file_id>)
    3. Shorten link via configured shortener
    4. Reply with short link button
    """

    try:
        wait_msg = await message.reply_text("🔁 Saving your file... please wait.", quote=True)

        db_chat = getattr(client, "primary_db_channel", None) or getattr(client, "db", None)
        if not db_chat:
            await wait_msg.edit("❌ DB/Log channel not configured!")
            return

        # 1️⃣ Copy the message (no forward tag)
        copied = await message.copy(db_chat)
        file_id = copied.id

        # 2️⃣ Encode deep link like filestorerobot
        encoded = base64.urlsafe_b64encode(f"get-{file_id}".encode()).decode().strip("=")
        bot_me = await client.get_me()
        deep_link = f"https://t.me/{bot_me.username}?start={encoded}"

        # 3️⃣ Optional share link for DB channel
        share_url = f"https://telegram.me/share/url?url={deep_link}"

        # 4️⃣ Create short link
        short_link = await asyncio.get_event_loop().run_in_executor(
            None, lambda: create_shortlink(SHORT_URL, SHORT_API, deep_link)
        )

        # 5️⃣ Edit waiting message
        text = "🔴 HERE IS YOUR LINK:"
        buttons = InlineKeyboardMarkup(
            [[InlineKeyboardButton("🔗 CLICK HERE TO OPEN", url=short_link)]]
        )
        await wait_msg.delete()
        await message.reply_text(text, reply_markup=buttons, quote=True)

        # 6️⃣ Optionally add share link inside DB channel message
        try:
            caption = f"📦 File stored.\n\n🔗 Deep Link:\n{deep_link}\n\n📤 Share:\n{share_url}"
            await copied.edit_caption(caption)
        except Exception:
            pass

    except Exception as e:
        await message.reply_text(f"❌ Error: {e}", quote=True)
