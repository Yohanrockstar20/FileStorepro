# ===============================================================
# LINK GENERATOR MODULE (Dynamic shortener + config fallback)
# ===============================================================

from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from config import LOGGER, SHORT_URL, SHORT_API
import requests, asyncio, random, string

# ===============================================================
# UNIVERSAL SHORTENER FUNCTION
# ===============================================================
def create_shortlink(short_url: str, short_api: str, long_url: str) -> str:
    """Generic API request for any shortener that supports ?api=<KEY>&url=<URL>"""
    api_endpoint = f"https://{short_url}/api?api={short_api}&url={long_url}"

    try:
        res = requests.get(api_endpoint, timeout=10)
        data = res.json()

        # Detect correct response key automatically
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
# AUTO LINK GENERATOR HANDLER
# ===============================================================
@Client.on_message((filters.document | filters.video | filters.audio | filters.photo) & filters.private)
async def link_generator(client: Client, message: Message):
    """
    When a user sends media:
    1. Forwards it to the DB/log channel.
    2. Builds a Telegram link.
    3. Looks for user shortener in DB (fallback to config.py).
    4. Shortens the link.
    5. Sends the short link as a button.
    """

    try:
        wait_msg = await message.reply_text("🔁 Uploading your file... please wait.", quote=True)

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

        # 2️⃣ Fallback
        if not file_url:
            bot_me = await client.get_me()
            token = ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(10))
            file_url = f"https://t.me/{bot_me.username}?start={token}"

        # 3️⃣ Load shortener settings (user-based, fallback to config)
        try:
            # If your project already uses MongoDB or users_api for settings:
            db_settings = await client.mongodb.get_shortner_settings()
            short_url = db_settings.get("short_url", SHORT_URL)
            short_api = db_settings.get("short_api", SHORT_API)
            short_enabled = db_settings.get("enabled", True)
        except Exception:
            # If DB not present or fails, fallback
            short_url, short_api, short_enabled = SHORT_URL, SHORT_API, True

        # 4️⃣ Generate short link
        short_link = file_url
        if short_enabled and short_url and short_api:
            short_link = await asyncio.get_event_loop().run_in_executor(
                None, lambda: create_shortlink(short_url, short_api, file_url)
            )

        # 5️⃣ Send result
        text = "🔴 HERE IS YOUR LINK:"
        buttons = InlineKeyboardMarkup(
            [[InlineKeyboardButton("🔗 CLICK HERE TO OPEN", url=short_link)]]
        )
        await wait_msg.delete()
        await message.reply_text(text, reply_markup=buttons, quote=True)

    except Exception as e:
        await message.reply_text(f"❌ Failed to generate link: {e}", quote=True)
