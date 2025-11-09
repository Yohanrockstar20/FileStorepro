from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from helper.helper_func import encode, get_message_id
from config import LOGGER, SHORT_URL, SHORT_API
import requests, asyncio

# ===============================================================
# UNIVERSAL SHORTENER FUNCTION (from VJ gen.py)
# ===============================================================
def create_shortlink(short_url, short_api, long_url):
    """
    Generic shortener that works with any provider supporting:
    https://domain/api?api=<API_KEY>&url=<URL>
    """
    if not short_url or not short_api:
        return long_url
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
        LOGGER(__name__, "Shortener").warning(f"Shortener error: {e}")
        return long_url


# ===============================================================
# EXISTING DATABASE CHANNEL INFO FUNCTION (unchanged)
# ===============================================================
async def get_db_channels_info(client):
    """Get formatted database channels information with links"""
    db_channels = getattr(client, 'db_channels', {})
    primary_db = getattr(client, 'primary_db_channel', client.db)
    
    if not db_channels:
        try:
            primary_chat = await client.get_chat(primary_db)
            if hasattr(primary_chat, 'invite_link') and primary_chat.invite_link:
                return f"<blockquote>✦ ᴘʀɪᴍᴀʀʏ ᴅʙ ᴄʜᴀɴɴᴇʟ: <a href='{primary_chat.invite_link}'>{primary_chat.title}</a></blockquote>"
            else:
                return f"<blockquote>✦ ᴘʀɪᴍᴀʀʏ ᴅʙ ᴄʜᴀɴɴᴇʟ: {primary_chat.title} (`{primary_db}`)</blockquote>"
        except:
            return f"<blockquote>✦ ᴘʀɪᴍᴀʀʏ ᴅʙ ᴄʜᴀɴɴᴇʟ: `{primary_db}`</blockquote>"
    
    channels_info = ["<blockquote>✦ ᴀᴠᴀɪʟᴀʙʟᴇ ᴅᴀᴛᴀʙᴀsᴇ ᴄʜᴀɴɴᴇʟs:</blockquote>"]
    for channel_id_str, channel_data in db_channels.items():
        channel_name = channel_data.get('name', 'ᴜɴᴋɴᴏᴡɴ')
        is_primary_text = "✦ ᴘʀɪᴍᴀʀʏ" if channel_data.get('is_primary', False) else "• sᴇᴄᴏɴᴅᴀʀʏ"
        try:
            chat = await client.get_chat(int(channel_id_str))
            if hasattr(chat, 'invite_link') and chat.invite_link:
                channels_info.append(f"{is_primary_text}: <a href='{chat.invite_link}'>{channel_name}</a>")
            else:
                channels_info.append(f"{is_primary_text}: {channel_name} (`{channel_id_str}`)")
        except:
            channels_info.append(f"{is_primary_text}: {channel_name} (`{channel_id_str}`)")
    return "\n".join(channels_info)


# ===============================================================
# GENLINK COMMAND (VJ-style + shortener)
# ===============================================================
@Client.on_message(filters.private & filters.command('genlink'))
async def link_generator(client: Client, message: Message):
    if message.from_user.id not in client.admins:
        return await message.reply(client.reply_text)

    db_channels_info = await get_db_channels_info(client)
    
    while True:
        try:
            channel_message = await client.ask(
                text=f"""<blockquote>ꜰᴏʀᴡᴀʀᴅ ᴍᴇssᴀɢᴇ ꜰʀᴏᴍ ᴛʜᴇ ᴅʙ ᴄʜᴀɴɴᴇʟ (ᴡɪᴛʜ ǫᴜᴏᴛᴇs)..</blockquote>

{db_channels_info}

<blockquote>ᴏʀ sᴇɴᴅ ᴛʜᴇ ᴅʙ ᴄʜᴀɴɴᴇʟ ᴘᴏsᴛ ʟɪɴᴋ</blockquote>""",
                chat_id=message.from_user.id,
                filters=(filters.forwarded | (filters.text & ~filters.forwarded)),
                timeout=60
            )
        except:
            return
        msg_id, source_channel_id = await get_message_id(client, channel_message)
        if msg_id:
            break
        else:
            await channel_message.reply("<blockquote>✗ ᴇʀʀᴏʀ</blockquote>\n\nᴛʜɪs ꜰᴏʀᴡᴀʀᴅᴇᴅ ᴘᴏsᴛ ɪs ɴᴏᴛ ꜰʀᴏᴍ ᴍʏ ᴅʙ ᴄʜᴀɴɴᴇʟ ᴏʀ ᴛʜɪs ʟɪɴᴋ ɪs ɴᴏᴛ ᴛᴀᴋᴇɴ ꜰʀᴏᴍ ᴅʙ ᴄʜᴀɴɴᴇʟ", quote=True)
            continue

    base64_string = await encode(f"get-{msg_id * abs(source_channel_id)}")
    deep_link = f"https://t.me/{client.username}?start={base64_string}"

    # -------------- Shortener Section --------------
    try:
        db_settings = await client.mongodb.get_shortner_settings()
        short_url = db_settings.get("short_url", SHORT_URL)
        short_api = db_settings.get("short_api", SHORT_API)
        enabled = db_settings.get("enabled", True)
    except Exception:
        short_url, short_api, enabled = SHORT_URL, SHORT_API, True

    if enabled and short_url and short_api:
        short_link = await asyncio.get_event_loop().run_in_executor(
            None, lambda: create_shortlink(short_url, short_api, deep_link)
        )
    else:
        short_link = deep_link
    # -----------------------------------------------

    reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton("🔗 CLICK HERE TO OPEN", url=short_link)]])
    await channel_message.reply_text(
        f"<blockquote>✓ ʜᴇʀᴇ ɪs ʏᴏᴜʀ ʟɪɴᴋ</blockquote>\n\n<code>{short_link}</code>",
        quote=True,
        reply_markup=reply_markup
    )


# ===============================================================
# REMAINING COMMANDS (unchanged)
# ===============================================================
@Client.on_message(filters.private & filters.command('batch'))
async def batch(client: Client, message: Message):
    if message.from_user.id not in client.admins:
        return await message.reply(client.reply_text)
    
    db_channels_info = await get_db_channels_info(client)
    while True:
        try:
            first_message = await client.ask(
                text=f"""<blockquote>ꜰᴏʀᴡᴀʀᴅ ᴛʜᴇ ꜰɪʀsᴛ ᴍᴇssᴀɢᴇ ꜰʀᴏᴍ ᴅʙ ᴄʜᴀɴɴᴇʟ (ᴡɪᴛʜ ǫᴜᴏᴛᴇs)..</blockquote>
{db_channels_info}""",
                chat_id=message.from_user.id,
                filters=(filters.forwarded | (filters.text & ~filters.forwarded)),
                timeout=60
            )
        except:
            return
        f_msg_id, source_channel_id = await get_message_id(client, first_message)
        if f_msg_id:
            break
        else:
            await first_message.reply("Invalid post.", quote=True)
            continue

    while True:
        try:
            second_message = await client.ask(
                text="Forward the last message from DB channel (with quotes)...",
                chat_id=message.from_user.id,
                filters=(filters.forwarded | (filters.text & ~filters.forwarded)),
                timeout=60
            )
        except:
            return
        s_msg_id, _ = await get_message_id(client, second_message)
        if s_msg_id:
            break
        else:
            await second_message.reply("Invalid post.", quote=True)
            continue

    string = f"get-{f_msg_id * abs(source_channel_id)}-{s_msg_id * abs(source_channel_id)}"
    base64_string = await encode(string)
    link = f"https://t.me/{client.username}?start={base64_string}"
    reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton("🔗 CLICK HERE TO OPEN", url=link)]])
    await second_message.reply_text(f"<blockquote>✓ ʜᴇʀᴇ ɪs ʏᴏᴜʀ ʙᴀᴛᴄʜ ʟɪɴᴋ</blockquote>\n\n<code>{link}</code>", quote=True, reply_markup=reply_markup)
