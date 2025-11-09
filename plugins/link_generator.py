from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from config import SHORT_URL, SHORT_API, LOGGER
import asyncio, random, string, requests

# =============================================================== #
# AUTO SHORTENER WITH GPLINKS + CUSTOM ALIAS
# =============================================================== #

def generate_alias():
    """Generate alias like ___A7b9Kd___"""
    chars = string.ascii_letters + string.digits
    rand_str = ''.join(random.choice(chars) for _ in range(random.randint(6, 10)))
    return f"___{rand_str}___"

def create_shortlink_gplinks(long_url):
    """Send request to GPLINKS API with alias and return short URL"""
    alias = generate_alias()
    api_endpoint = f"https://{SHORT_URL}/api?api={SHORT_API}&url={long_url}&alias={alias}"
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
    """Auto shortener that creates GPLINKS link with alias"""
    try:
        wait_msg = await message.reply_text("🔁 Processing your file... please wait", quote=True)
        db_chat = getattr(client, "primary_db_channel", None) or getattr(client, "db", None)
        file_url = None

        # 1️⃣ Try to forward file to DB/public channel
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

        # 2️⃣ Fallback (if no DB or forward fails)
        if not file_url:
            bot_me = await client.get_me()
            token = ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(10))
            file_url = f"https://t.me/{bot_me.username}?start={token}"

        # 3️⃣ Create short link using GPLINKS
        short_link = await asyncio.get_event_loop().run_in_executor(None, lambda: create_shortlink_gplinks(file_url))

        # 4️⃣ Send button message
        text = "🔴 HERE IS YOUR LINK:"
        buttons = InlineKeyboardMarkup(
            [[InlineKeyboardButton("🔗 CLICK HERE TO OPEN", url=short_link)]]
        )
        await wait_msg.delete()
        await message.reply_text(text, reply_markup=buttons, quote=True)

    except Exception as e:
        await message.reply_text(f"❌ Failed to generate short link: {e}", quote=True)
