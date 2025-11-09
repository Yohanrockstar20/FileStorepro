from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from config import LOGGER, SHORT_URL, SHORT_API
import asyncio, random, string, requests

# =============================================================== #
# UNIVERSAL SHORTENER SYSTEM WITH AUTO ALIAS SUPPORT
# Works for any shortener domain that follows the API format:
# https://<domain>/api?api=<API_KEY>&url=<LONG_URL>&alias=<ALIAS>
# =============================================================== #

def generate_alias():
    """Generate alias like ___A7b9Kd___"""
    chars = string.ascii_letters + string.digits
    rand_str = ''.join(random.choice(chars) for _ in range(random.randint(6, 10)))
    return f"___{rand_str}___"

def create_shortlink(short_url, short_api, long_url):
    """Generic shortener API request that works for any provider"""
    alias = generate_alias()
    api_endpoint = f"https://{short_url}/api?api={short_api}&url={long_url}&alias={alias}"
    try:
        res = requests.get(api_endpoint, timeout=10)
        data = res.json()
        if data.get("status") == "success":
            return data.get("shortenedUrl", long_url)
        else:
            LOGGER("link_generator", "bot").warning(f"Shortener failed: {data}")
            return long_url
    except Exception as e:
        LOGGER("link_generator", "bot").warning(f"Shortener error: {e}")
        return long_url

@Client.on_message(filters.private & (filters.photo | filters.video | filters.document | filters.audio | filters.animation))
async def media_auto_shortener(client: Client, message: Message):
    """Auto shortener that adapts to any shortener + alias system"""
    try:
        wait_msg = await message.reply_text("🔁 Processing your file... please wait", quote=True)
        db_chat = getattr(client, "primary_db_channel", None) or getattr(client, "db", None)
        file_url = None

        # 1️⃣ Forward file to DB/public channel
        if db_chat:
            try:
                forwarded = await client.forward_messages(
                    chat_id=db_chat,
                    from_chat_id=message.chat.id,
                    message_ids=[message.id]
                )
                fwd_msg = forwarded[0] if isinstance(forwarded, list) else forwarded
                fwd_id = getattr(fwd_msg, "id", None) or getattr(fwd_msg, "message_id", None)
                db_chat_obj = await client.get_chat(db_chat)

                if getattr(db_chat_obj, "username", None):
                    file_url = f"https://t.me/{db_chat_obj.username}/{fwd_id}"
                else:
                    cid = str(db_chat).replace("-100", "")
                    file_url = f"https://t.me/c/{cid}/{fwd_id}"
            except Exception as e:
                LOGGER(__name__, client.name).warning(f"Forward failed: {e}")

        # 2️⃣ Fallback link if DB channel unavailable
        if not file_url:
            bot_me = await client.get_me()
            token = ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(10))
            file_url = f"https://t.me/{bot_me.username}?start={token}"

        # 3️⃣ Get shortener settings dynamically
        # (from DB if available, else fallback to config.py)
        try:
            db_settings = await client.mongodb.get_shortner_settings()
            short_url = db_settings.get("short_url", SHORT_URL)
            short_api = db_settings.get("short_api", SHORT_API)
            short_enabled = db_settings.get("enabled", True)
        except Exception:
            short_url, short_api, short_enabled = SHORT_URL, SHORT_API, True

        # 4️⃣ Create short link
        short_link = file_url
        if short_enabled and short_url and short_api:
            short_link = await asyncio.get_event_loop().run_in_executor(
                None, lambda: create_shortlink(short_url, short_api, file_url)
            )

        # 5️⃣ Reply with button
        text = "🔴 HERE IS YOUR LINK:"
        buttons = InlineKeyboardMarkup(
            [[InlineKeyboardButton("🔗 CLICK HERE TO OPEN", url=short_link)]]
        )
        await wait_msg.delete()
        await message.reply_text(text, reply_markup=buttons, quote=True)

    except Exception as e:
        await message.reply_text(f"❌ Failed to generate short link: {e}", quote=True)
