import os
import logging
from typing import List 

from dotenv import load_dotenv

from telegram import Update
from telegram.ext import ApplicationBuilder, Application

from bot import MediaDownloaderBot 

# Enable logging
logging.basicConfig(
    level=logging.INFO,  # Set the minimum log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',  # Customize log format
    datefmt='%Y-%m-%d %H:%M:%S',  # Customize datetime format
    handlers=[logging.StreamHandler()]  # Explicitly send to console
)
logger = logging.getLogger(__name__)

load_dotenv()

TELEGRAM_BOT_TOKEN: str = os.environ.get("TELEGRAM_BOT_TOKEN", "")
BOT_PASSWORD: str = os.environ.get("BOT_PASSWORD", "")
PREAUTHENTICATED_CHAT_IDS: str = os.environ.get("CHAT_IDS", "")

if TELEGRAM_BOT_TOKEN == "":
    raise ValueError("No Telegram bot token specified")

app: Application = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

if PREAUTHENTICATED_CHAT_IDS is not None and PREAUTHENTICATED_CHAT_IDS != "":
    preauthenticated_chat_ids: List[str] = PREAUTHENTICATED_CHAT_IDS.split(",")
else:
    preauthenticated_chat_ids: List[str] = []

bot: MediaDownloaderBot = MediaDownloaderBot(
    token=TELEGRAM_BOT_TOKEN,
    password=BOT_PASSWORD,
    preauth_chat_ids=preauthenticated_chat_ids,
)

bot.init_handlers(app)

logger.info("Bot is running...")
app.run_polling(allowed_updates=Update.ALL_TYPES)