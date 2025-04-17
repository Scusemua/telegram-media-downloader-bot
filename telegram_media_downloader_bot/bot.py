import asyncio
import os
import logging
from datetime import datetime, timedelta
import traceback
from typing import List, Optional, Dict, Any
import uuid
import yt_dlp
from telegram import InlineQueryResultArticle, InlineQueryResultCachedVideo, InlineQueryResultsButton, InputTextMessageContent, Update
from telegram.ext import MessageHandler, CommandHandler, ContextTypes, filters, Application, InlineQueryHandler
from telegram import Update
import threading

LOGGER_FORMAT: str = '%(asctime)s | %(levelname)s | %(message)s | %(name)s | %(funcName)s'

"""
auth - /auth <password> or /auth <chat_id> <password>: authenticate the chat so that it can be used with the bot.
download - /download <url>: download the specified media.
metrics - /metrics: return the total number of downloads.
"""

DEFAULT_AUTH_TIMEOUT: int = 15  # seconds


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
        bot_user_id: str = "",
        public_ipv4: str = "",
        http_port: int = 8081,
        log_file: str = "telegram_bot.log",
        auth_timeout: int = DEFAULT_AUTH_TIMEOUT,
        logger_format: str = LOGGER_FORMAT
    ):
        self._authenticated_chats = set()
        self._user_to_group: Dict[str, str] = {}
        self._user_to_chat_id: Dict[str, str] = {}

        self._http_port: int = http_port
        self._bot_user_id: str = bot_user_id
        self._auth_timeout: int = auth_timeout
        self._admin_user_id: str = admin_user_id
        self._token: str = token
        self._password: Optional[str] = password
        self._public_ipv4: str = public_ipv4
        self._preauth_chat_ids: List[str] = preauth_chat_ids or []

        # Dictionary to track group join times
        self._group_auth_timers: Dict[str, Any] = {}

        self._num_downloads: int = 0

        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG)

        # Create a handler and set the formatter
        stream_handler = logging.StreamHandler()
        formatter = logging.Formatter(logger_format)
        stream_handler.setFormatter(formatter)

        # Add the handler to the logger
        self.logger.addHandler(stream_handler)

        if log_file:
            file_handler = logging.FileHandler(log_file)
            file_handler.setFormatter(formatter)
            self.logger.addHandler(file_handler)

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
        app.add_handler(CommandHandler("exit", self.exit_command))
        app.add_handler(CommandHandler("start", self.start_command))
        app.add_handler(CommandHandler("clear_auth", self.clear_auth_command))

        app.add_handler(MessageHandler(
            filters.TEXT & ~filters.COMMAND, self.handle_message))
        app.add_handler(MessageHandler(
            filters.StatusUpdate.NEW_CHAT_MEMBERS, self.handle_new_chat))

        app.add_handler(InlineQueryHandler(self.inline_download_command))
        app.add_error_handler(self.error_handler)

    # Handler for /start
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        assert update.effective_chat
        assert update.effective_user

        chat_id = str(update.effective_chat.id)
        user_id = str(update.effective_user.id)

        self._user_to_chat_id[user_id] = chat_id

        self.logger.debug(
            f'Registerd chat ID "{chat_id}" for user "{user_id}".')

        if update.message:
            await update.message.reply_text("🚀 Thanks! You can now use inline queries.")

    # Handler for /clear_auth
    async def clear_auth_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
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

    # Handler for /exit
    async def exit_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Exit command handler.

        /exit

        Only works if sent by the admin user.
        """
        if not update.effective_user or str(update.effective_user.id) != self._admin_user_id:
            return

        self.logger.info("Received 'exit' command from admin. Goodbye!")

        exit(0)

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
        assert update.effective_user

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

        # Check if the group is in the auth timer list
        if chat_id in self._authenticated_chats:
            await update.message.reply_text("No authentication required or already processed.")
            return

        if chat_id in self._group_auth_timers:
            self._group_auth_timers[chat_id]["authenticated"] = True

        self.authenticate_chat(chat_id)
        self.logger.info(f'Authenticated chat: "{chat_id}"')

        await update.message.reply_text(f"✅ Authentication successful! Thanks {update.effective_user.first_name}.")

    # Command handler for /download
    async def download_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> Optional[str]:
        """
        Inspect messages to see if they are a link to an Instagram reel or YouTube short.
        If so, download them, and reply to the message with the downloaded media. 
        """
        if not update.message or not update.message.text:
            return None

        text: str = update.message.text.strip()
        splits: list[str] = text.split(" ")

        if len(splits) <= 1:
            return None

        text = splits[1]

        self.logger.info(f'Received /download command: "{text}"')

        return await self._handle_download_request(text, update)

    # Command handler for /metrics
    async def metrics_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        assert update.message
        await update.message.reply_text(f"⬇️ Total number of downloads: {self._num_downloads}")

    # General message handler.
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> Optional[str]:
        """
        Message handler. Inspect messages to see if they are a link to an Instagram reel or YouTube short.
        If so, download them, and reply to the message with the downloaded media. 
        """
        if not update.message or not update.message.text:
            return

        text = update.message.text.strip()

        self.logger.info(f'Received message: "{text}"')

        return await self._handle_download_request(text, update)

    # Handler for being added to a new chat.
    async def handle_new_chat(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle when the bot is added to a new group."""
        chat = update.effective_chat
        assert chat

        if not self._password or not update.message or chat.type not in ["group", "supergroup"]:
            return

        new_chat_participant: Optional[Dict[str, Any]] = update.message.api_kwargs.get(
            "new_chat_participant", None)
        if not new_chat_participant:
            return

        new_chat_participant_id: str = str(new_chat_participant.get("id", ""))
        if new_chat_participant_id == "" or new_chat_participant_id != self._bot_user_id:
            return

        chat_id = chat.id
        self.logger.info(
            f"TelegramMediaDownloaderBot added to new group: {chat.title} (ID: {chat_id})")

        # Send welcome message with instructions
        await context.bot.send_message(
            chat_id=chat_id,
            text="🤖 Hello! I'm a protected bot. "
            f"Please authenticate me within {self._auth_timeout} second(s) by sending:\n"
            f"/auth <password>\n\n"
            "Otherwise I'll automatically leave this group."
        )

        # Set the removal time (current time + timeout)
        removal_time = datetime.now() + timedelta(seconds=self._auth_timeout)
        self._group_auth_timers[str(chat_id)] = {
            "removal_time": removal_time,
            "authenticated": False
        }

        # Schedule a check for this group
        asyncio.create_task(self._check_group_auth(chat_id, context))

    # Inline command handler.
    async def inline_download_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        assert update.inline_query is not None
        query = update.inline_query.query

        self.logger.debug(f"update: {update}")

        self.logger.debug(f"context: {context}")

        user_id = str(update.inline_query.from_user.id)
        if user_id not in self._user_to_chat_id:
            self.logger.debug(f"_user_to_chat_id: {self._user_to_chat_id}")
            # User hasn't started a private chat with the bot
            await update.inline_query.answer(
                [],
                button=InlineQueryResultsButton(
                    "Start the bot first", start_parameter="arg"),
                cache_time=1,
                is_personal=True,
            )
            return
        private_chat_id: str = self._user_to_chat_id[user_id]

        if "?" in query:
            query = query[0:query.index("?")]

        self.logger.info(f'Received inline download query: "{query}"')
        self.logger.info(update)

        if not query:  # empty query should not be handled
            return

        self.logger.info(f'Received inline download query: "{query}"')
        
        split_query: List[str] = query.split(" ")
        url: str = split_query[0]

        found: bool = False
        for prefix in MediaDownloaderBot.valid_url_prefixes:
            if prefix in url:
                found = True
                break

        if not found:
            return

        try:
            # Download the video
            video_id: str = str(uuid.uuid4())
            video_path: str = os.path.join("./video", f"{video_id}.mp4")
            self.logger.info(f'Will save reel to file "{video_path}"\n')
            self._download_media(url, output_path=video_path)
            self.logger.info(
                f'Successfully downloaded Instagram reel to file "{video_path}"\n\n')
        except Exception as ex:
            self.logger.error(f'Failed to download video at URL "{url}"')
            self.logger.error(ex)
            self.logger.error(traceback.format_exc())

            results = []

            if "Restricted Video" in str(ex):
                results.append(InlineQueryResultArticle(
                    id=str(uuid.uuid4()),
                    title='Error: Age Restricted Video',
                    description='Failed to download specified video due to age restriction.',
                    input_message_content=InputTextMessageContent(
                        message_text='Error: failed to download specified video due to age restriction.',
                    )
                ))
            else:
                results.append(InlineQueryResultArticle(
                    id=str(uuid.uuid4()),
                    title='Error: Failed to Download Video',
                    description='The requested video could not be downloaded. Sorry!',
                    input_message_content=InputTextMessageContent(
                        message_text='Error: the requested video could not be downloaded. Sorry!',
                    )
                ))

            await update.inline_query.answer(results)

            return

        message = await context.bot.send_video(
            chat_id=private_chat_id,
            video=open(video_path, "rb")
        )

        assert message.video

        # Use get_file() to retrieve the File object
        file = await message.video.get_file()

        # You now have access to file.file_id
        file_id = file.file_id
        
        if len(split_query) > 1:
            caption:str = split_query[1]
        else:
            caption:str = ""

        results = [
            InlineQueryResultCachedVideo(
                id="inline-video-1",
                video_file_id=file_id,
                title="Pre-uploaded video",
                caption=caption,
                description=caption,
            ),
        ]

        await update.inline_query.answer(results)

        async def clean_up():
            await asyncio.sleep(2)
            self.logger.debug("Cleaning up.")
            os.remove(video_path)
            await context.bot.delete_message(chat_id=private_chat_id, message_id=message.message_id)

        # Delete it after 2 seconds
        asyncio.create_task(clean_up())

    async def _check_group_auth(self, chat_id: int, context: ContextTypes.DEFAULT_TYPE):
        """Check if a group has been authenticated after the timeout period."""
        await asyncio.sleep(self._auth_timeout)

        # Check if group is still in the timer dict and not authenticated
        if str(chat_id) in self._group_auth_timers and not self._group_auth_timers[str(chat_id)]["authenticated"]:
            self.logger.info(
                f"Group {chat_id} failed to authenticate in time. Leaving...")
            try:
                await context.bot.send_message(
                    chat_id=chat_id,
                    text="⏰ Authentication timeout. Goodbye!"
                )
                await context.bot.leave_chat(chat_id)
            except Exception as e:
                self.logger.error(f"Error leaving group {chat_id}: {e}")
            finally:
                # Clean up
                if str(chat_id) in self._group_auth_timers:
                    del self._group_auth_timers[str(chat_id)]

    def _download_media(self, url: str, output_path: str = "./") -> None:
        """
        Download the specified media to the specified path.

        :param url: URL of the Instagram reel or YouTube short to download.
        :param output_path: File path of downloaded file.
        """
        ydl_opts = {
            'outtmpl': f'{output_path}',
            'format': 'mp4',
            'quiet': False,
            'age_limit': 21,
            'ignoreerrors': False,
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            download_retcode = ydl.download([url])
            self.logger.debug(
                f'Download return code for URL "{url}": {download_retcode}')

        self._num_downloads += 1

        self.logger.debug(f'Created file: "{output_path}"')

    async def _handle_download_request(self, text: str, update: Update, delete_after_reply: bool = True) -> Optional[str]:
        """
        Generic handler for messages and download commands.
        """
        if not update.message or not update.message.text:
            return

        assert update.effective_chat
        assert update.effective_user
        if update.effective_chat.type in ["group", "supergroup"]:
            self._user_to_group[str(update.effective_user.id)] = str(
                update.effective_chat.id)

        if self._password and str(update.effective_chat.id) not in self._authenticated_chats:
            self.logger.info(
                f'Unauthenticated chat: "{update.effective_chat.id}"')
            return

        for prefix in MediaDownloaderBot.valid_url_prefixes:
            if prefix in text:
                try:
                    # Download the video
                    video_path = f"./{str(uuid.uuid4())}.mp4"
                    self.logger.info(
                        f'Will save reel to file "{video_path}"\n')
                    self._download_media(text, output_path=video_path)
                    self.logger.info(
                        f'Successfully downloaded Instagram reel "{text}" to file "{video_path}".\n\n')
                except Exception as ex:
                    self.logger.error(
                        f'Failed to download video at URL "{text}"')
                    self.logger.error(ex)
                    self.logger.error(traceback.format_exc())

                    if "Restricted Video" in str(ex):
                        await update.message.reply_text(f"⚠️ Failed to download the requested video. Video is age restricted, and downloading age restricted videos is not supported at this time. Sorry!",
                                                        reply_to_message_id=update.message.message_id)
                    else:
                        await update.message.reply_text(f"⚠️ Failed to download the requested video. Sorry!",
                                                        reply_to_message_id=update.message.message_id)

                    return None

                try:
                    await update.message.reply_video(video=open(video_path, 'rb'), reply_to_message_id=update.message.message_id)
                except Exception as e:
                    self.logger.error(f"Error: {e}")
                    return None

                try:
                    if delete_after_reply:
                        os.remove(video_path)
                except Exception as e:
                    self.logger.error(f"Error: {e}")
                    return video_path

                return video_path
