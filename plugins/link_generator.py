from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from helper.helper_func import encode, get_message_id
from config import LOGGER
from plugins.shortner import get_short
import asyncio, random, string, requests

# =============================================================== #
# AUTO SHORTENER FOR MEDIA WITH CUSTOM ALIAS
# =============================================================== #

def generate_alias():
    """Generate random alias like ___jajyfj___"""
    chars = string.ascii_letters + string.digits
    rand_str = ''.join(random.choice(chars) for _ in range(random.randint(6, 10)))
    return f"___{rand_str}___"

@Client.on_message(filters.private & (filters.photo | filters.video | filters.document | filters.audio | filters.animation))
async def media_auto_shortener(client: Client, message: Message):
    """
    When a user sends media in private, forward it to DB/public channel (if configured)
    and generate a short link immediately using get_short(...).
    """
    try:
        wait_msg = await message.reply_text("🔁 Processing your file... please wait", quote=True)
        db_chat = getattr(client, "primary_db_channel", None) or getattr(client, "db", None)
        file_url = None

        # Try forwarding to DB/public channel first
        if db_chat:
            try:
                forwarded = await client.forward_messages(
                    chat_id=db_chat,
                    from_chat_id=message.chat.id,
                    message_ids=message.message_id
                )
                fwd = forwarded[0] if isinstance(forwarded, (list, tuple)) else forwarded
                db_chat_obj = await client.get_chat(db_chat)

                # Public channel → https://t.me/username/msgid
                if getattr(db_chat_obj, "username", None):
                    file_url = f"https://t.me/{db_chat_obj.username}/{fwd.message_id}"
                else:
                    # Private channel → https://t.me/c/<id>/<msgid>
                    cid = str(db_chat).replace("-100", "")
                    file_url = f"https://t.me/c/{cid}/{fwd.message_id}"
            except Exception as e:
                LOGGER(__name__, client.name).warning(f"Forward failed: {e}")

        # If no DB or forward failed, fallback pseudo link
        if not file_url:
            bot_me = await client.get_me()
            token = ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(10))
            file_url = f"https://t.me/{bot_me.username}?start={token}"

        # Build shortener API call manually (to include custom alias)
        alias = generate_alias()
        short_url = getattr(client, "short_url", None)
        short_api = getattr(client, "short_api", None)
        shortner_enabled = getattr(client, "shortner_enabled", True)

        short_link = file_url  # default fallback
        if shortner_enabled and short_url and short_api:
            try:
                api_endpoint = f"https://{short_url}/api?api={short_api}&url={file_url}&alias={alias}"
                response = requests.get(api_endpoint, timeout=10)
                data = response.json()
                if data.get("status") == "success":
                    short_link = data.get("shortenedUrl", file_url)
                else:
                    LOGGER(__name__, client.name).warning(f"Shortener failed: {data}")
            except Exception as e:
                LOGGER(__name__, client.name).warning(f"Shortener request failed: {e}")

        # Send final result (button only)
        text = "🔴 HERE IS YOUR LINK:"
        buttons = InlineKeyboardMarkup(
            [[InlineKeyboardButton("🔗 CLICK HERE TO OPEN", url=short_link)]]
        )

        await wait_msg.delete()
        await message.reply_text(text, reply_markup=buttons, quote=True)

    except Exception as e:
        await message.reply_text(f"❌ Failed to generate short link: {e}", quote=True)
