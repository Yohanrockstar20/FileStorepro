# ===============================================================
# LINK GENERATOR MODULE (with built-in shortener)
# Works for any shortener site (anyshorturl.com, gplinks, tnshort, etc.)
# ===============================================================

from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from config import LOGGER, SHORT_URL, SHORT_API
import requests, asyncio, random, string

# ===============================================================
# UNIVERSAL SHORTENER FUNCTION (from VJ logic)
# ===============================================================
def create_shortlink(long_url: str) -> str:
    """
    Generate a short link using any shortener site that supports:
    https://domain/api?api=<API_KEY>&url=<URL>
    """
    short_url = SHORT_URL
    short_api = SHORT_API
    api_endpoint = f"https://{short_url}/api?api={short_api}&url={long_url}"

    try:
        res = requests.get(api_endpoint, timeout=10)
        data = res.json()

        # Detect correct field automatically
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
    Handles any media message from a user:
    1. Forwards it to the DB/log channel.
    2. Builds a Telegram t.me link.
    3. Shortens it using the configured shortener API.
    4. Sends the final short link with a button.
    """

    try:
        wait_msg = await message.reply_text("🔁 Uploading your file... please wait.", quote=True)

        # Get DB/log channel
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

                # Public channel
                if getattr(db_chat_obj, "username", None):
                    file_url = f"https://t.me/{db_chat_obj.username}/{fwd_id}"
                else:
                    # Private channel (no username)
                    cid = str(db_chat).replace("-100", "")
                    file_url = f"https://t.me/c/{cid}/{fwd_id}"

            except Exception as e:
                LOGGER(__name__, client.name).warning(f"Forward failed: {e}")

        # 2️⃣ Fallback: no DB or forward failed
        if not file_url:
            bot_me = await client.get_me()
            token = ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(10))
            file_url = f"https://t.me/{bot_me.username}?start={token}"

        # 3️⃣ Create short link (directly via API)
        short_link = await asyncio.get_event_loop().run_in_executor(None, lambda: create_shortlink(file_url))

        # 4️⃣ Send link to user
        text = "🔴 HERE IS YOUR LINK:"
        buttons = InlineKeyboardMarkup(
            [[InlineKeyboardButton("🔗 CLICK HERE TO OPEN", url=short_link)]]
        )

        await wait_msg.delete()
        await message.reply_text(text, reply_markup=buttons, quote=True)

    except Exception as e:
        await message.reply_text(f"❌ Failed to generate link: {e}", quote=True)
