# Modified by ChatGPT for universal shortener support
# Based on original by @VJ_Botz

import re, os, json, base64, requests
from pyrogram import Client, filters
from pyrogram.errors.exceptions.bad_request_400 import ChannelInvalid, UsernameInvalid, UsernameNotModified
from config import ADMINS, LOG_CHANNEL, PUBLIC_FILE_STORE, WEBSITE_URL, WEBSITE_URL_MODE, SHORT_URL, SHORT_API
from plugins.users_api import get_user
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# --- Helper for permission check ---
async def allowed(_, __, message):
    if PUBLIC_FILE_STORE:
        return True
    if message.from_user and message.from_user.id in ADMINS:
        return True
    return False


# --- Universal shortener (no alias) ---
def create_shortlink(short_url, short_api, long_url):
    """Generic shortener API call for anyshorturl/gplinks/tnshort"""
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
    except Exception:
        return long_url


# =============================================================== #
# 🔹 Generate short link for uploaded files (direct link)
# =============================================================== #

@Client.on_message((filters.document | filters.video | filters.audio) & filters.private & filters.create(allowed))
async def incoming_gen_link(bot, message):
    username = (await bot.get_me()).username
    post = await message.copy(LOG_CHANNEL)
    file_id = str(post.id)
    encoded = base64.urlsafe_b64encode(f"file_{file_id}".encode("ascii")).decode().strip("=")

    user_id = message.from_user.id
    user = await get_user(user_id)

    # Determine base link
    if WEBSITE_URL_MODE:
        long_link = f"{WEBSITE_URL}?Tech_VJ={encoded}"
    else:
        long_link = f"https://t.me/{username}?start={encoded}"

    # Generate short link using user API or fallback config
    short_url = user.get("base_site") or SHORT_URL
    short_api = user.get("shortener_api") or SHORT_API

    short_link = create_shortlink(short_url, short_api, long_link)

    text = "🔴 HERE IS YOUR LINK:"
    buttons = InlineKeyboardMarkup([[InlineKeyboardButton("🔗 CLICK HERE TO OPEN", url=short_link)]])
    await message.reply_text(text, reply_markup=buttons, quote=True)


# =============================================================== #
# 🔹 /link command — manual reply-based generation
# =============================================================== #

@Client.on_message(filters.command(['link']) & filters.create(allowed))
async def gen_link_s(bot, message):
    username = (await bot.get_me()).username
    replied = message.reply_to_message
    if not replied:
        return await message.reply('Reply to a message to get a shareable link.')

    post = await replied.copy(LOG_CHANNEL)
    file_id = str(post.id)
    encoded = base64.urlsafe_b64encode(f"file_{file_id}".encode("ascii")).decode().strip("=")

    user_id = message.from_user.id
    user = await get_user(user_id)

    if WEBSITE_URL_MODE:
        long_link = f"{WEBSITE_URL}?Tech_VJ={encoded}"
    else:
        long_link = f"https://t.me/{username}?start={encoded}"

    short_url = user.get("base_site") or SHORT_URL
    short_api = user.get("shortener_api") or SHORT_API
    short_link = create_shortlink(short_url, short_api, long_link)

    text = "🔴 HERE IS YOUR LINK:"
    buttons = InlineKeyboardMarkup([[InlineKeyboardButton("🔗 CLICK HERE TO OPEN", url=short_link)]])
    await message.reply_text(text, reply_markup=buttons, quote=True)
