from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from config import LOGGER, SHORT_URL, SHORT_API
import asyncio, requests, random, string

# =============================================================== #
# UNIVERSAL SHORTENER (No Alias / Only After Upload)
# =============================================================== #

def create_shortlink(short_url, short_api, long_url):
    """Generic shortener API call that works for most providers"""
    api_endpoint = f"https://{short_url}/api?api={short_api}&url={long_url}"
    try:
        res = requests.get(api_endpoint, timeout=10)
        data = res.json()
        # Adjust key if your shortener uses a different one
        if data.get("status") == "success":
            return data.get("shortenedUrl", long_url)
        elif "shortenedUrl" in data:
            return data["shortenedUrl"]
        elif "shortlink" in data:
            return data["shortlink"]
        elif "short" in data:
            return data["short"]
        else:
            LOGGER("link_generator", "bot").warning(f"Unexpected API response: {data}")
            return long_url
    except Exception as e:
        LOGGER("link_generator", "bot").warning(f"Shortener error: {e}")
        return long_url


@Client.on_message(filters.private & (filters.photo | filters.video | filters.document | filters.audio | filters.animation))
async def media_shortener(client: Client, message: Message):
    """Forward media to DB/public channel, then generate short link after upload."""
    try:
        wait_msg = await message.reply_text("🔁 Uploading your file... please wait", quote=True)
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

                # Build real Telegram file link
                if getattr(db_chat_obj, "username", None):
                    file_url = f"https://t.me/{db_chat_obj.username}/{fwd_id}"
                else:
                    cid = str(db_chat).replace("-100", "")
                    file_url = f"https://t.me/c/{cid}/{fwd_id}"

            except Exception as e:
                LOGGER(__name__, client.name).warning(f"Forward failed: {e}")

        # 2️⃣ Fallback if DB unavailable
        if not file_url:
            bot_me = await client.get_me()
            token = ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(10))
            file_url = f"https://t.me/{bot_me.username}?start={token}"

        # 3️⃣ Get shortener info from config
        short_url = getattr(client, "short_url", SHORT_URL)
        short_api = getattr(client, "short_api", SHORT_API)

        # 4️⃣ Create short link directly (no alias)
        short_link = await asyncio.get_event_loop().run_in_executor(
            None, lambda: create_shortlink(short_url, short_api, file_url)
        )

        # 5️⃣ Send final link button
        text = "🔴 HERE IS YOUR LINK:"
        buttons = InlineKeyboardMarkup(
            [[InlineKeyboardButton("🔗 CLICK HERE TO OPEN", url=short_link)]]
        )

        await wait_msg.delete()
        await message.reply_text(text, reply_markup=buttons, quote=True)

    except Exception as e:
        await message.reply_text(f"❌ Failed to create short link: {e}", quote=True)
