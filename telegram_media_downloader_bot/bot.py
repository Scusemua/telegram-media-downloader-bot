import os
import logging
from typing import List, Optional
import uuid
import yt_dlp
from telegram import Update
from telegram.ext import MessageHandler, CommandHandler, ContextTypes, filters, Application
from telegram import Update

LOGGER_FORMAT:str = '%(asctime)s | %(levelname)s | %(message)s | %(name)s | %(funcName)s'

"""
auth - /auth <password> or /auth <chat_id> <password>: authenticate the chat so that it can be used with the bot.
download - /download <url>: download the specified media.
metrics - /metrics: return the total number of downloads.
"""

class MediaDownloaderBot(object):
    valid_url_prefixes: List[str] = [
        "youtube.com/shorts/",
        "youtu.be/shorts/",
        'instagram.com/reel/',
        'instagram.com/p/'
    ]
    
    def __init__(
        self, 
        token: str = "",
        password: Optional[str] = "", 
        preauth_chat_ids: Optional[List[str]] = None, 
        admin_user_id: str = "",
        logger_format:str = LOGGER_FORMAT
    ):
        self._authenticated_chats = set()
        self._user_to_group = {}

        self._admin_user_id: str = admin_user_id
        self._token: str = token
        self._password: Optional[str] = password
        self._preauth_chat_ids: List[str] = preauth_chat_ids or []
        
        self._num_downloads: int = 0

        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG)

        # Create a handler and set the formatter
        handler = logging.StreamHandler()
        formatter = logging.Formatter(logger_format)
        handler.setFormatter(formatter)

        # Add the handler to the logger
        self.logger.addHandler(handler)

        for preauth_chat_id in self._preauth_chat_ids:
            self.logger.debug(f'Pre-autenticating chat "{preauth_chat_id}"')
            self.authenticate_chat(preauth_chat_id)

    def init_handlers(self, app: Application) -> None:
        """
        Initialize command handlers for Telegram app.
        """
        app.add_handler(CommandHandler("auth", self.auth_command))
        app.add_handler(CommandHandler("download", self.download_command))
        app.add_handler(CommandHandler("metrics", self.metrics_command))
        app.add_handler(CommandHandler("exit", self.exit_handler))
        app.add_handler(CommandHandler("clear_auth", self.clear_auth_handler))

        app.add_handler(MessageHandler(
            filters.TEXT & ~filters.COMMAND, self.handle_message))

        # app.add_handler(InlineQueryHandler(self.inline_download_command))
        app.add_error_handler(self.error_handler)
        
    async def clear_auth_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Handler for the /clear_auth command.
        
        Clears all authorized chats. Re-adds the pre-specified chats.
        
        Only works if sent by the admin user.
        """
        if not update.effective_user or str(update.effective_user.id) != self._admin_user_id:
            return 
        
        self.logger.info("/clear_auth: clearing all authenticated chat IDs.")
        
        self._authenticated_chats.clear()

        for preauth_chat_id in self._preauth_chat_ids:
            self.logger.debug(f'Pre-autenticating chat "{preauth_chat_id}"')
            self.authenticate_chat(preauth_chat_id)
    
    async def exit_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Exit command handler.
        
        /exit
        
        Only works if sent by the admin user.
        """
        if not update.effective_user or str(update.effective_user.id) != self._admin_user_id:
            return 
        
        self.logger.info("Received 'exit' command from admin. Goodbye!")
        
        exit(0)

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
        self.logger.error("Exception while handling an update:",
                          exc_info=context.error)
    
    def authenticate_chat(self, chat_id: str | int) -> None:
        """
        Authenticate the specified chat.

        :param chat_id: the ID of the Telegram chat to be authenticated.
        """
        self._authenticated_chats.add(str(chat_id))

    # Command handler for /auth
    async def auth_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Authenticate a chat so that the bot may be used in the chat.
        
        If the bot password was unspecified, then this is essentially a no-op. 
        """
        assert update.message

        if self._password is None or self._password == "":
            await update.message.reply_text("✅ Authentication is not required! You're good to go.")
            return

        args = context.args

        if not args:
            await update.message.reply_text("❌ Please provide a password. Usage: /auth <password>")
            return
        
        assert update.effective_chat
        if len(args) == 2:
            chat_id: str = args[0]
            password: str = args[1] 
        elif len(args) == 1:
            password: str = args[0]
            chat_id: str = str(update.effective_chat.id)
        else:
            await update.message.reply_text("❌ Invalid command. Usage: `/auth <password>` or `/auth <chat_id> <password>`.")
            return 
        
        if password != self._password:
            await update.message.reply_text("❌ Incorrect password.")
            return 
        

        self.authenticate_chat(chat_id)
        self.logger.info(
            f'Authenticated chat: "{chat_id}"')
        
        if chat_id == str(update.effective_chat.id):
            await update.message.reply_text("✅ This chat has been authenticated!")
        else:
            await update.message.reply_text("✅ Successfully authenticated the specified chat!")

    async def download_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Inspect messages to see if they are a link to an Instagram reel or YouTube short.
        If so, download them, and reply to the message with the downloaded media. 
        """
        if not update.message or not update.message.text:
            return

        text: str = update.message.text.strip()
        splits: list[str] = text.split(" ")

        if len(splits) <= 1:
            return

        text = splits[1]

        self.logger.info(f'Received /download command: "{text}"')

        await self._handle_download_request(text, update)
        
    async def metrics_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        assert update.message
        await update.message.reply_text(f"⬇️ Total number of downloads: {self._num_downloads}")

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Message handler. Inspect messages to see if they are a link to an Instagram reel or YouTube short.
        If so, download them, and reply to the message with the downloaded media. 
        """
        if not update.message or not update.message.text:
            return

        text = update.message.text.strip()

        self.logger.info(f'Received message: "{text}"')

        await self._handle_download_request(text, update)
    
    async def _handle_download_request(self, text:str, update: Update):
        """
        Generic handler for messages and download commands.
        """
        if not update.message or not update.message.text:
            return
        
        assert update.effective_chat
        assert update.effective_user
        if update.effective_chat.type in ["group", "supergroup"]:
            self._user_to_group[update.effective_user.id] = update.effective_chat.id

        if self._password and str(update.effective_chat.id) not in self._authenticated_chats:
            self.logger.info(
                f'Unauthenticated chat: "{update.effective_chat.id}"')
            return

        for prefix in MediaDownloaderBot.valid_url_prefixes:
            if prefix in text:
                try:
                    # Download the video
                    video_path = f"{str(uuid.uuid4())}.mp4"
                    self.logger.info(f'\nWill save reel to file "{video_path}"\n')
                    self.download_media(text, output_path=video_path)
                    self.logger.info("Successfully downloaded Instagram reel.\n\n")
                    await update.message.reply_video(video=open(video_path, 'rb'), reply_to_message_id=update.message.message_id)
                    os.remove(video_path)
                    self._num_downloads += 1

                except Exception as e:
                    self.logger.error(f"Error: {e}")
                
                return 

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
