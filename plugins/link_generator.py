from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from helper.helper_func import encode, get_message_id
from config import LOGGER, SHORT_URL, SHORT_API
import base64, requests, asyncio

# ===============================================================
# UNIVERSAL SHORTENER (VJ-style)
# ===============================================================
def create_shortlink(short_url: str, short_api: str, long_url: str) -> str:
    """Works with any shortener using ?api=&url= pattern."""
    if not short_url or not short_api:
        return long_url
    api = f"https://{short_url}/api?api={short_api}&url={long_url}"
    try:
        r = requests.get(api, timeout=10)
        data = r.json() if r.headers.get("content-type", "").startswith("application/json") else {}
        if isinstance(data, dict):
            if data.get("status") == "success" and data.get("shortenedUrl"):
                return data["shortenedUrl"]
            for k in ("shortenedUrl", "shortlink", "short"):
                if k in data and isinstance(data[k], str):
                    return data[k]
        return long_url
    except Exception as e:
        LOGGER(__name__, "Shortener").warning(f"Shortener error: {e}")
        return long_url

async def load_shortener_settings(client: Client):
    """Pull shortener settings from DB (/settings) or fallback to config.py."""
    enabled, short_url, short_api = True, None, None
    try:
        if hasattr(client, "mongodb") and hasattr(client.mongodb, "get_shortner_settings"):
            s = await client.mongodb.get_shortner_settings()
            if isinstance(s, dict):
                enabled = s.get("enabled", True)
                short_url = s.get("short_url") or short_url
                short_api = s.get("short_api") or short_api
    except Exception as e:
        LOGGER(__name__, client.name).warning(f"DB shortener settings error: {e}")
    short_url = short_url or getattr(client, "short_url", None)
    short_api = short_api or getattr(client, "short_api", None)
    if hasattr(client, "shortner_enabled"):
        enabled = bool(getattr(client, "shortner_enabled"))
    short_url = short_url or SHORT_URL
    short_api = short_api or SHORT_API
    return enabled, short_url, short_api

def build_deeplink_token(file_id: int) -> str:
    """Encode 'get-<file_id>' as base64 (no padding)."""
    return base64.urlsafe_b64encode(f"get-{file_id}".encode()).decode().rstrip("=")

# ===============================================================
# ONLY ADMINS CAN TRIGGER AUTOMATIC SHORTENER
# ===============================================================
@Client.on_message((filters.document | filters.video | filters.audio | filters.photo) & filters.private)
async def auto_deeplink_and_shorten(client: Client, message: Message):
    """Admins only: copy file -> deep link -> short link -> reply + share link in DB."""
    try:
        # ✅ Admin check
        if message.from_user.id not in getattr(client, "admins", []):
            return await message.reply_text(
                "⚠️ Sorry, only the bot owner or admins can generate links.",
                quote=True
            )

        wait = await message.reply_text("🔁 Saving your file... please wait.", quote=True)
        db_chat = getattr(client, "primary_db_channel", None) or getattr(client, "db", None)
        if not db_chat:
            await wait.edit("❌ DB/Log channel not configured.")
            return

        # 1️⃣ Copy file (no forward tag)
        stored = await message.copy(db_chat)
        file_id = getattr(stored, "id", None)
        if not file_id:
            await wait.edit("❌ Could not store file in DB channel.")
            return

        # 2️⃣ Build bot deep-link
        me = await client.get_me()
        token = build_deeplink_token(file_id)
        deep_link = f"https://t.me/{me.username}?start={token}"

        # 3️⃣ Load shortener settings and (maybe) shorten
        enabled, short_url, short_api = await load_shortener_settings(client)
        if enabled and short_url and short_api:
            short_link = await asyncio.get_event_loop().run_in_executor(
                None, lambda: create_shortlink(short_url, short_api, deep_link)
            )
        else:
            short_link = deep_link  # shortener disabled or missing

        # 4️⃣ Send result to admin
        await wait.delete()
        await message.reply_text(
            "🔴 HERE IS YOUR LINK:",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("🔗 CLICK HERE TO OPEN", url=short_link)]]
            ),
            quote=True
        )

        # 5️⃣ Add caption with share link to DB copy
        try:
            share_url = f"https://telegram.me/share/url?url={deep_link}"
            cap = f"📦 File saved by admin.\n\n🔗 Deep Link:\n{deep_link}\n\n📤 Share:\n{share_url}"
            await stored.edit_caption(cap)
        except Exception:
            pass

    except Exception as e:
        await message.reply_text(f"❌ Error: {e}", quote=True)

# ===============================================================
# ADMIN COMMANDS: /genlink /batch /nbatch (unchanged but admin-limited)
# ===============================================================
@Client.on_message(filters.private & filters.command('genlink'))
async def link_generator(client: Client, message: Message):
    if message.from_user.id not in getattr(client, "admins", []):
        return await message.reply_text("⚠️ Only admins can use this command.", quote=True)

    db_channels_info = await get_db_channels_info(client)
    while True:
        try:
            channel_message = await client.ask(
                text=f"""<blockquote>Forward a message from your DB channel (with quotes)..</blockquote>

{db_channels_info}""",
                chat_id=message.from_user.id,
                filters=(filters.forwarded | (filters.text & ~filters.forwarded)),
                timeout=60
            )
        except:
            return
        msg_id, source_channel_id = await get_message_id(client, channel_message)
        if msg_id:
            break
        await channel_message.reply("Invalid DB message.", quote=True)

    base64_string = await encode(f"get-{msg_id * abs(source_channel_id)}")
    deep_link = f"https://t.me/{client.username}?start={base64_string}"

    enabled, short_url, short_api = await load_shortener_settings(client)
    if enabled and short_url and short_api:
        short_link = await asyncio.get_event_loop().run_in_executor(
            None, lambda: create_shortlink(short_url, short_api, deep_link)
        )
    else:
        short_link = deep_link

    await channel_message.reply_text(
        "🔴 HERE IS YOUR LINK:",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔗 CLICK HERE TO OPEN", url=short_link)]]),
        quote=True
    )

# ===============================================================
# Helper: Show DB channel info (same as before)
# ===============================================================
async def get_db_channels_info(client):
    db_channels = getattr(client, 'db_channels', {})
    primary_db = getattr(client, 'primary_db_channel', client.db)
    if not db_channels:
        try:
            chat = await client.get_chat(primary_db)
            title = getattr(chat, "title", "Unknown")
            return f"<blockquote>✦ Primary DB Channel: {title}</blockquote>"
        except:
            return f"<blockquote>✦ Primary DB Channel ID: `{primary_db}`</blockquote>"
    text = ["<blockquote>✦ Available DB Channels:</blockquote>"]
    for cid, data in db_channels.items():
        name = data.get("name", "Unknown")
        is_primary = "Primary" if data.get("is_primary", False) else "Secondary"
        text.append(f"{is_primary}: {name} (`{cid}`)")
    return "\n".join(text)
