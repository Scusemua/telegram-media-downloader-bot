# 📥 Telegram Media Downloader Bot

A simple and lightweight **Telegram bot** that provides an interface to the [yt-dlp](https://github.com/yt-dlp/yt-dlp) Python module, enabling users to download **YouTube Shorts** and **Instagram Reels** directly within Telegram.

## 🚀 Features

- 🎥 Download **YouTube Shorts** by simply sending a link
- 📸 Download **Instagram Reels** from share links
- 🧠 Built using Python and [yt-dlp](https://github.com/yt-dlp/yt-dlp).
- 🤖 Clean Telegram Bot interface for ease of use

## 🛠 Requirements

- Python 3.8+
- Telegram Bot Token from [@BotFather](https://t.me/BotFather)
- `ffmpeg` (ensure it's installed and available in your system path)

## 📦 Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/telegram-media-downloader.git
   cd telegram-media-downloader

2. Create a virtual environment (optional but recommended)

```sh
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies
``` sh
pip install -r requirements.txt
```

4. Set up environment variables.

Create a .env file in the root directory with the following required environment variable:
``` sh
TELEGRAM_BOT_TOKEN="<your_bot_token_here>"
```

The `TELEGRAM_BOT_TOKEN` is used to specify the [Telegram Bot Token](https://core.telegram.org/bots/api#authorizing-your-bot) for the bot.

Optionally, you may also specify a `CHAT_IDS` environment variable and a `BOT_PASSWORD` environment variable:
``` sh
TELEGRAM_BOT_TOKEN="<your_bot_token_here>"
BOT_PASSWORD="<bot_password_here>"
CHAT_IDS="000000001,000000002,000000003"
```

The `BOT_PASSWORD` is an optional password that, when specified, will prevent the bot from responding to links from chats that haven't been authenticated.

To authenticate a chat, use the `/auth <bot_password>` command in the Telegram chat.

The `CHAT_IDS` environment variable enables you to "pre-authenticate" some Telegram group chats/private message chats that will work immediately, without having to first use the bot's `/auth <bot_password>` command.

# ▶️ Usage

Start the bot with:
``` sh
python bot.py
```

Then, open Telegram, find your bot, and send a YouTube Shorts or Instagram Reels link. The bot will reply with the downloadable video.

# 📁 Project Structure

``` 
telegram-media-downloader/
├── __main__.py            # Entrypoint
├── bot.py                 # Main Telegram bot logic
├── requirements.txt       # Python dependencies
├── .env                   # Bot configuration (not tracked)
└── README.md              # This file
```

# ✅ Supported URLs
- https://www.youtube.com/shorts/<video_id>
- https://www.instagram.com/reel/<reel_id>
- https://www.instagram.com/p/<reel_id>

# 🔒 Disclaimer
This project is for educational purposes only. Downloading content from YouTube or Instagram may violate their terms of service. Use responsibly.

# 📄 License
MIT License