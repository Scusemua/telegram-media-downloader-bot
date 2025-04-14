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

Create a .env file in the root directory:
``` sh
TELEGRAM_BOT_TOKEN=your_bot_token_here
```

# ▶️ Usage

Start the bot with:
``` sh
python bot.py
```

Then, open Telegram, find your bot, and send a YouTube Shorts or Instagram Reels link. The bot will reply with the downloadable video.

# 📁 Project Structure

``` 
telegram-media-downloader/
├── bot.py                 # Main Telegram bot logic
├── downloader.py          # Wrapper around YoutubeDownloader module
├── requirements.txt       # Python dependencies
├── .env                   # Bot configuration (not tracked)
└── README.md              # This file
```

# ✅ Supported URLs
- https://www.youtube.com/shorts/<video_id>
- https://www.instagram.com/reel/<reel_id>
- instagram.com/p/<reel_id>

# 🔒 Disclaimer
This project is for educational purposes only. Downloading content from YouTube or Instagram may violate their terms of service. Use responsibly.

# 📄 License
MIT License