import os
import logging
from argparse import ArgumentParser
from typing import List

from dotenv import load_dotenv

from telegram import Update
from telegram.ext import ApplicationBuilder, Application

from telegram_media_downloader_bot.bot import MediaDownloaderBot

load_dotenv()

parser = ArgumentParser()
parser.add_argument("-t", "--token", type = str, default = "", help = "Telegram bot token. You may also specify this via the `TELEGRAM_BOT_TOKEN` environment variable.")
parser.add_argument("-p", "--password", type = str, default = "", help = "Telegram bot password. If specified, only chats authenticated with this password (via the /auth <password> command) will be able to use the bot. You may also specify this via the `BOT_PASSWORD` environment variable.")
parser.add_argument("-c", "--chat-ids", type = str, nargs = "*", default=[], help = "List of Telegram chat IDs to authenticate immediately (i.e., without needing to use the /auth <password> command from the chat). You may also specify this via the `PREAUTHENTICATED_CHAT_IDS` environment variable as a comma-separated list.")
parser.add_argument("-a", "--admin-user-id", type = str, default = "", help = "Telegram user ID of the admin. To get your own Telegram user ID, send a message to @userinfobot.")
parser.add_argument("-b", "--bot-user-id", type = str, default = "", help = "Telegram user ID of the bot. Accessible by viewing the bot's page within Telegram.")

args = parser.parse_args()

token: str = os.environ.get("TELEGRAM_BOT_TOKEN", args.token)
if token == "":
    raise ValueError("No Telegram bot token specified")

admin_user_id: str = os.environ.get("ADMIN_USER_ID", args.admin_user_id)
bot_password: str = os.environ.get("BOT_PASSWORD", args.password)
preauthenticated_chat_ids: str | List[str] = os.environ.get("CHAT_IDS", args.chat_ids)
bot_user_id: str = os.environ.get("BOT_USER_ID", args.bot_user_id)
if bot_user_id == "":
    raise ValueError("No Telegram bot user ID specified")

app: Application = ApplicationBuilder().token(token).build()

if preauthenticated_chat_ids is not None and isinstance(preauthenticated_chat_ids, str) and preauthenticated_chat_ids != "":
    preauthenticated_chat_ids = preauthenticated_chat_ids.split(",")
else:
    preauthenticated_chat_ids = []

bot: MediaDownloaderBot = MediaDownloaderBot(
    token=token,
    password=bot_password,
    preauth_chat_ids=preauthenticated_chat_ids,
    admin_user_id=admin_user_id,
    bot_user_id=bot_user_id,
)

bot.init_handlers(app)

print("🤖 Bot is running...")
app.run_polling(allowed_updates=Update.ALL_TYPES)
