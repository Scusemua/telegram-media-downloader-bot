from fileinput import FileInput
import os
from typing import Optional 
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from telegram import User, Chat, Message, Update
from telegram.ext import ContextTypes

from telegram_media_downloader_bot.bot import MediaDownloaderBot


@pytest.fixture
def bot():
    return MediaDownloaderBot(
        token="dummy",
        password="testpass",
        preauth_chat_ids=["1234"],
        admin_user_id="42",
        bot_user_id="9999",
        public_ipv4="1.2.3.4",
    )


@pytest.fixture
def fake_context():
    return MagicMock(spec=ContextTypes.DEFAULT_TYPE)


def make_update(user_id="1", chat_id="100", text=None, is_group=False):
    user = User(id=int(user_id), first_name="TestUser", is_bot=False)
    chat = Chat(id=int(chat_id), type="group" if is_group else "private")
    message = MagicMock(spec=Message)
    message.text = text
    message.chat = chat
    message.from_user = user
    message.reply_text = AsyncMock()
    update = MagicMock(spec=Update)
    update.effective_user = user
    update.effective_chat = chat
    update.message = message
    
    async def reply_video(
        video: FileInput,
        reply_to_message_id: Optional[int] = None,
    ):
        if video:
            video.close() 
    
    message.reply_video = reply_video
    
    return update


@pytest.mark.asyncio
async def test_start_command(bot, fake_context):
    update = make_update(text="/start")
    await bot.start_command(update, fake_context)
    update.message.reply_text.assert_called_once_with(
        "🚀 Thanks! You can now use inline queries.")


@pytest.mark.asyncio
async def test_auth_command_success(bot, fake_context):
    update = make_update(text="/auth testpass")
    fake_context.args = ["testpass"]
    await bot.auth_command(update, fake_context)
    update.message.reply_text.assert_called_with(
        "✅ Authentication successful! Thanks TestUser.")


@pytest.mark.asyncio
async def test_auth_command_failure(bot, fake_context):
    update = make_update(text="/auth wrongpass")
    fake_context.args = ["wrongpass"]
    await bot.auth_command(update, fake_context)
    update.message.reply_text.assert_called_with("❌ Incorrect password.")


@pytest.mark.asyncio
async def test_metrics_command(bot, fake_context):
    update = make_update(text="/metrics")
    await bot.metrics_command(update, fake_context)
    update.message.reply_text.assert_called_once_with(
        "⬇️ Total number of downloads: 0")


@pytest.mark.asyncio
@patch("telegram_media_downloader_bot.bot.MediaDownloaderBot._download_media")
async def test_download_command_valid_url(mock_download, bot, fake_context):
    bot.authenticate_chat("1000")
    update = make_update(
        text="/download https://www.youtube.com/shorts/2vAFkEhL2g4", chat_id="1000")
    await bot.download_command(update, fake_context)
    mock_download.assert_called_once()


@pytest.mark.asyncio
async def test_clear_auth_command_by_admin(bot, fake_context):
    update = make_update(user_id="42", text="/clear_auth")
    await bot.clear_auth_command(update, fake_context)
    assert "1234" in bot._authenticated_chats


@pytest.mark.asyncio
async def test_clear_auth_command_by_non_admin(bot, fake_context):
    update = make_update(user_id="2", text="/clear_auth")
    await bot.clear_auth_command(update, fake_context)
    # Should not modify authenticated chats
    assert "1234" in bot._authenticated_chats


@pytest.mark.asyncio
async def test_handle_message(bot, fake_context):
    chat_id: str = "1234"
    bot.authenticate_chat(chat_id)
    update = make_update(
        chat_id=chat_id, text="https://www.instagram.com/reel/DE9WkhAoLQJ/")
    output_path: str = await bot.handle_message(update, fake_context)


@pytest.mark.asyncio
async def test_download_media(bot, fake_context):
    chat_id: str = "1234"
    bot.authenticate_chat(chat_id)
    url:str = "https://www.instagram.com/reel/DE9WkhAoLQJ/"
    output_path:str = "test.mp4"
    bot._download_media(url, output_path)
    
    assert os.path.exists(output_path)
    assert os.path.isfile(output_path)

    os.remove(output_path)
    
    assert not os.path.exists(output_path)