import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler,
    ContextTypes, filters
)
from yt_dlp import YoutubeDL

# Bot and Webhook config
BOT_TOKEN = os.getenv("BOT_TOKEN", "6007538473:AAGPWq9MJMwMtt7csnLpJgmDOq99rTDvBZE").rstrip('/')
BOT_URL = os.getenv("BOT_URL", "https://onlinegrassper.onrender.com").rstrip('/')  # Replace with your actual URL

# Logging setup
logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)

DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

def get_video_options(url):
    try:
        ydl_opts = {"quiet": True}
        if os.path.exists("cookies.txt"):
            logging.info("✅ Using cookies.txt")
            ydl_opts["cookies"] = "cookies.txt"

        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            formats = info.get("formats", [])
            options = [
                (f"{f['format_note']} - {f['ext']} ({round(f['filesize'] / 1024 / 1024, 1)}MB)" if f.get("filesize") else f"{f['format_note']} - {f['ext']}", f["format_id"])
                for f in formats
                if f.get("vcodec") != "none" and f.get("acodec") != "none"
            ]
            return options
    except Exception as e:
        logging.error(f"Error in get_video_options: {e}")
        return None

def download_video(url, format_id):
    ydl_opts = {
        "format": format_id,
        "outtmpl": os.path.join(DOWNLOAD_DIR, "%(title)s.%(ext)s"),
        "quiet": True,
    }
    if os.path.exists("cookies.txt"):
        ydl_opts["cookies"] = "cookies.txt"

    try:
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            return ydl.prepare_filename(info)
    except Exception as e:
        logging.error(f"Download error: {e}")
        return None

# Command Handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📥 Send me a YouTube link to download.")

async def handle_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()
    context.user_data["video_url"] = url
    await update.message.reply_text("🔍 Getting video info...")

    options = get_video_options(url)
    if not options:
        await update.message.reply_text("❌ Couldn't retrieve video options. It might be restricted or blocked.")
        return

    buttons = [
        [InlineKeyboardButton(text=label, callback_data=format_id)]
        for label, format_id in options[:10]
    ]
    markup = InlineKeyboardMarkup(buttons)
    await update.message.reply_text("🎥 Choose video quality:", reply_markup=markup)

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    format_id = query.data
    url = context.user_data.get("video_url")
    await query.edit_message_text("📥 Downloading... Please wait.")

    filename = download_video(url, format_id)
    if not filename or not os.path.exists(filename):
        await query.message.reply_text("❌ Download failed.")
        return

    with open(filename, "rb") as f:
        await query.message.reply_video(video=f)

    os.remove(filename)

# Entry point for webhook-based bot
def run_bot_webhook():
    from flask import Flask, request
    from telegram import Update

    app = Flask(__name__)
    application = ApplicationBuilder().token(BOT_TOKEN).build()

    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(handle_callback))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_link))

    @app.route('/')
    def home():
        return '🚀 Bot is running with webhook.'

    @app.route('/webhook', methods=['POST'])
    def webhook():
        update = Update.de_json(request.get_json(force=True), application.bot)
        application.update_queue.put(update)
        return "ok", 200

    # Start Flask + Telegram webhook listener
    import threading
    threading.Thread(target=lambda: application.run_webhook(
        listen="0.0.0.0",
        port=int(os.environ.get("PORT", 8080)),
        webhook_url=f"{BOT_URL}/webhook"
    )).start()

    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))

