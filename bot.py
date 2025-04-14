from telegram import InlineQueryResultArticle, InputTextMessageContent, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import InlineQueryHandler
from uuid import uuid4
import json 
import os
import logging
import requests
from typing import List, Dict, Optional
import uuid 
from bs4 import BeautifulSoup
import yt_dlp
from telegram import Update, Bot
from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, ContextTypes, filters, Application
from telegram import InlineQueryResultVideo, Update
from telegram.ext import InlineQueryHandler, Updater, CallbackContext, CallbackQueryHandler

class MediaDownloaderBot(object):
    def __init__(self, token: str = "", password: Optional[str] = "", preauth_chat_ids: Optional[List[str]] = None):
        self._authenticated_chats = set()
        self._user_to_group = {}
        
        self._token: str = token
        self._password: Optional[str] = password
        self._preauth_chat_ids: List[str] = preauth_chat_ids or []

        self.logger = logging.getLogger(__name__)

        for preauth_chat_id in self._preauth_chat_ids:
            self.logger.debug(f'Pre-autenticating chat "{preauth_chat_id}"')
            self.authenticate_chat(preauth_chat_id)

    def init_handlers(self, app: Application) -> None:
        """
        Initialize command handlers for Telegram app.
        """
        app.add_handler(CommandHandler("auth", self.auth_command))
        app.add_handler(CommandHandler("download", self.download_command))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
        app.add_handler(InlineQueryHandler(self.inline_download_command))
        app.add_error_handler(self.error_handler)

    def download_media(self, url: str, output_path: str = "./") -> None:
        """
        Download the specified media to the specified path.
        
        :param url: URL of the Instagram reel or YouTube short to download.
        :param output_path: File path of downloaded file.
        """
        ydl_opts = {
            'outtmpl': f'{output_path}',
            'format': 'mp4',
            'quiet': False,
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

    async def error_handler(self, update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Log the error and send a telegram message to notify the developer."""
        # Log the error before we do anything else, so we can see it even if something breaks.
        self.logger.error("Exception while handling an update:", exc_info=context.error)
    
    def authenticate_chat(self, chat_id: str) -> None:
        """
        Authenticate the specified chat.
        
        :param chat_id: the ID of the Telegram chat to be authenticated.
        """
        self._authenticated_chats.add(chat_id)

    # Command handler for /auth
    async def auth_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if self._password is None or self._password == "":
            await update.message.reply_text("✅ Authentication is not required! You're good to go.")
            return 

        args = context.args

        if not args:
            await update.message.reply_text("❌ Please provide a password. Usage: /auth <password>")
            return

        if args[0] == Bot.PASSWORD:
            self.authenticate_chat(update.effective_chat.id)
            self.logger.info(f'Authenticated chat: "{update.effective_chat.id}"')
            await update.message.reply_text("✅ This chat has been authenticated!")
        else:
            await update.message.reply_text("❌ Incorrect password.")
    
    async def download_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not update.message:
            return 
        
        text: str = update.message.text.strip()
        splits: list[str] = text.split(" ")
        
        if len(splits) <= 1:
            return 
        
        text = splits[1]
        
        self.logger.info(f'Received message: "{text}"')

        if update.effective_chat.type in ["group", "supergroup"]:
            self._user_to_group[update.effective_user.id] = update.effective_chat.id
        
        if update.effective_chat.id not in self._authenticated_chats:
            return 

        if 'instagram.com/reel/' in text or 'instagram.com/p/' in text:            
            try:
                # Download the video
                video_path = f"{str(uuid.uuid4())}.mp4"
                self.logger.info(f'\nWill save reel to file "{video_path}"\n')
                self.download_media(text, output_path=video_path)
                self.logger.info("Successfully downloaded Instagram reel.\n\n")
                await update.message.reply_video(video=open(video_path, 'rb'), reply_to_message_id=update.message.message_id)
                os.remove(video_path)

            except Exception as e:
                self.logger.error(f"Error: {e}")

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not update.message:
            return 
        
        text = update.message.text.strip()
        
        self.logger.info(f'Received message: "{text}"')

        if update.effective_chat.type in ["group", "supergroup"]:
            self._user_to_group[update.effective_user.id] = update.effective_chat.id
        
        if update.effective_chat.id not in self._authenticated_chats:
            self.logger.info(f'Unauthenticated chat: "{update.effective_chat.id}"')
            return 

        if 'instagram.com/reel/' in text or 'instagram.com/p/' in text:            
            try:
                # Download the video
                video_path = f"{str(uuid.uuid4())}.mp4"
                self.logger.info(f'\nWill save reel to file "{video_path}"\n')
                self.download_media(text, output_path=video_path)
                self.logger.info("Successfully downloaded Instagram reel.\n\n")
                await update.message.reply_video(video=open(video_path, 'rb'), reply_to_message_id=update.message.message_id)
                os.remove(video_path)

            except Exception as e:
                self.logger.error(f"Error: {e}")

    # async def inline_download_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    #     query = update.inline_query.query

    #     print(f'Received inline download query: "{query}"')

    #     if not query:  # empty query should not be handled
    #         return

    #     self.logger.info(f'Received inline download query: "{query}"')

    #     if 'instagram.com/reel/' not in query and 'instagram.com/p/' not in query:
    #         return 

    #     try:
    #         # Download the video
    #         video_id:str = str(uuid.uuid4())
    #         video_path:str = f"./http_server/videos/{video_id}.mp4"
    #         self.logger.info(f'\nWill save reel to file "{video_path}"\n')
    #         self.download_media(query, output_path=video_path)
    #         self.logger.info(f'Successfully downloaded Instagram reel to file "{video_path}"\n\n')
    #     except Exception as e:
    #         self.logger.error(f"Error: {e}")

    #     video_url:str=f"http://{PUBLIC_IPV4}:8080/videos/{video_id}.mp4"
    #     self.logger.info(f'Returning video URL: "{video_url}"')

    #     results = [
    #         InlineQueryResultVideo(
    #             '1',
    #             video_url,
    #             'video/mp4', 
    #             'https://raw.githubusercontent.com/eternnoir/pyTelegramBotAPI/master/examples/detailed_example/rooster.jpg',
    #             'Title'
    #         )
    #     ]

    #     await update.inline_query.answer(results)