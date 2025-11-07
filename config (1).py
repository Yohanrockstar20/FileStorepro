import logging
from logging.handlers import RotatingFileHandler

# Bot Configuration
LOG_FILE_NAME = "bot.log"
PORT = '5010'
OWNER_ID = 1997486779

MSG_EFFECT = 5046509860389126442

SHORT_URL = "gplinks.com" # shortner url 
SHORT_API = "03a1f31a88c44180200c606b9903b37404440f16" 
SHORT_TUT = "https://t.me/How_to_Download_7x/26"

# Bot Configuration
SESSION = "yato"
TOKEN = "8223283552:AAHkl36gfQTVmvdJGyfy3ndX82oMSw2AM88"
API_ID = "21835136"
API_HASH = "3417178f776bb4877425fe1d60a75205"
WORKERS = 5

DB_URI = "mongodb+srv://Yohanrock:yohanrockstar@cluster0.v8tewcp.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
DB_NAME = "yato"

FSUBS = [[-1001759223130, True, 10]] # Force Subscription Channels [channel_id, request_enabled, timer_in_minutes]
# Database Channel (Primary)
DB_CHANNEL =-1002928480913   # just put channel id dont add ""
# Multiple Database Channels (can be set via bot settings)
# DB_CHANNELS = {
#     "-1002595092736": {"name": "Primary DB", "is_primary": True, "is_active": True},
#     "-1001234567890": {"name": "Secondary DB", "is_primary": False, "is_active": True}
# }
# Auto Delete Timer (seconds)
AUTO_DEL = 300
# Admin IDs
ADMINS = [865764383]
# Bot Settings
DISABLE_BTN = False
PROTECT = False

# Messages Configuration
MESSAGES = {
    "START": "<b>›› ʜᴇʏ!!, {first} ~ <blockquote>ʟᴏᴠᴇ ᴘᴏʀɴʜᴡᴀ? ɪ ᴀᴍ ᴍᴀᴅᴇ ᴛᴏ ʜᴇʟᴘ ʏᴏᴜ ᴛᴏ ғɪɴᴅ ᴡʜᴀᴛ ʏᴏᴜ aʀᴇ ʟᴏᴏᴋɪɴɢ ꜰᴏʀ.</blockquote></b>",
    "FSUB": "<b><blockquote>›› ʜᴇʏ ×</blockquote>\n  ʏᴏᴜʀ ғɪʟᴇ ɪs ʀᴇᴀᴅʏ ‼️ ʟᴏᴏᴋs ʟɪᴋᴇ ʏᴏᴜ ʜᴀᴠᴇɴ'ᴛ sᴜʙsᴄʀɪʙᴇᴅ ᴛᴏ ᴏᴜʀ ᴄʜᴀɴɴᴇʟs ʏᴇᴛ, sᴜʙsᴄʀɪʙᴇ ɴᴏᴡ ᴛᴏ ɢᴇᴛ ʏᴏᴜʀ ғɪʟᴇs</b>",
    "ABOUT": "<b>›› ғᴏʀ ᴍᴏʀᴇ: @Nova_Flix \n <blockquote expandable>›› ᴜᴘᴅᴀᴛᴇs ᴄʜᴀɴɴᴇʟ: <a href='https://t.me/codeflix_bots'>Cʟɪᴄᴋ ʜᴇʀᴇ</a> \n›› ᴏᴡɴᴇʀ: @ProYato\n›› ʟᴀɴɢᴜᴀɢᴇ: <a href='https://docs.python.org/3/'>Pʏᴛʜᴏɴ 3</a> \n›› ʟɪʙʀᴀʀʏ: <a href='https://docs.pyrogram.org/'>Pʏʀᴏɢʀᴀᴍ ᴠ2</a> \n›› ᴅᴀᴛᴀʙᴀsᴇ: <a href='https://www.mongodb.com/docs/'>Mᴏɴɢᴏ ᴅʙ</a> \n›› ᴅᴇᴠᴇʟᴏᴘᴇʀ: @cosmic_freak</b></blockquote>",
    "REPLY": "<b>For More Join - @Hanime_Arena</b>",
    "SHORT_MSG": "<b>📊 ʜᴇʏ {first}, \n\n‼️ ɢᴇᴛ ᴀʟʟ ꜰɪʟᴇꜱ ɪɴ ᴀ ꜱɪɴɢʟᴇ ʟɪɴᴋ ‼️\n\n ⌯ ʏᴏᴜʀ ʟɪɴᴋ ɪꜱ ʀᴇᴀᴅʏ, ᴋɪɴᴅʟʏ ᴄʟɪᴄᴋ ᴏɴ ᴏᴘᴇɴ ʟɪɴᴋ ʙᴜᴛᴛᴏɴ..</b>",
    "START_PHOTO": "https://graph.org/file/510affa3d4b6c911c12e3.jpg",
    "FSUB_PHOTO": "https://telegra.ph/file/7a16ef7abae23bd238c82-b8fbdcb05422d71974.jpg",
    "SHORT_PIC": "https://telegra.ph/file/7a16ef7abae23bd238c82-b8fbdcb05422d71974.jpg",
    "SHORT": "https://telegra.ph/file/8aaf4df8c138c6685dcee-05d3b183d4978ec347.jpg"
}

def LOGGER(name: str, client_name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    formatter = logging.Formatter(
        f"[%(asctime)s - %(levelname)s] - {client_name} - %(name)s - %(message)s",
        datefmt='%d-%b-%y %H:%M:%S'
    )
    file_handler = RotatingFileHandler(LOG_FILE_NAME, maxBytes=50_000_000, backupCount=10)
    file_handler.setFormatter(formatter)
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    logger.setLevel(logging.INFO)
    logger.addHandler(file_handler)
    logger.addHandler(stream_handler)

    return logger
