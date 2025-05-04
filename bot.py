import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler,
    ContextTypes, filters
)
from yt_dlp import YoutubeDL

# Replace with your actual bot token
BOT_TOKEN = os.getenv("BOT_TOKEN", "6007538473:AAGPWq9MJMwMtt7csnLpJgmDOq99rTDvBZE")

# Logging setup
logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)

DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# Get video format options
def get_video_options(url):
    try:
        ydl_opts = {
            "quiet": True,
        }

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

# Download video in selected quality
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

# Start command handler
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📥 Send me a YouTube link to download.")

# Handle messages with YouTube links
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

# Handle quality button click
async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    format_id = query.data
    url = context.user_data.get("video_url")
    await query.edit_message_text("📥 Downloading... Please wait.")

    try:
        filename = download_video(url, format_id)
        if not filename or not os.path.exists(filename):
            await query.message.reply_text("❌ Download failed.")
            return

        # Send video
        with open(filename, "rb") as f:
            await query.message.reply_video(video=f)

        os.remove(filename)
    except Exception as e:
        logging.error(f"Error during callback handling: {e}")
        await query.message.reply_text("❌ An error occurred while processing your request.")

# Run the bot
def run_bot():
    try:
        app = ApplicationBuilder().token(BOT_TOKEN).build()
        app.add_handler(CommandHandler("start", start))
        app.add_handler(CallbackQueryHandler(handle_callback))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_link))
        app.run_polling()
    except Exception as e:
        logging.error(f"Error in bot execution: {e}")
