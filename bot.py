import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler,
    ContextTypes, filters
)
from yt_dlp import YoutubeDL
import logging

BOT_TOKEN = "YOUR_TELEGRAM_BOT_TOKEN"

logging.basicConfig(level=logging.INFO)

# Get available video formats
def get_video_options(url):
    try:
        ydl_opts = {}
        if os.path.exists("cookies.txt"):
            ydl_opts['cookies'] = "cookies.txt"

        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            formats = info.get("formats", [])
            options = [
                (f"{f['format_note']} - {f['ext']}", f['format_id'])
                for f in formats if f.get("vcodec") != "none" and f.get("acodec") != "none"
            ]
            return options
    except Exception as e:
        logging.error(f"Error in get_video_options: {e}")
        return None

# Download video
def download_video(url, format_id):
    ydl_opts = {
        "format": format_id,
        "outtmpl": "downloads/%(title)s.%(ext)s"
    }

    if os.path.exists("cookies.txt"):
        ydl_opts['cookies'] = "cookies.txt"

    try:
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            return ydl.prepare_filename(info)
    except Exception as e:
        logging.error(f"Download error: {e}")
        return None

# Handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📥 Send me a YouTube link to download.")

async def handle_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()
    context.user_data["video_url"] = url

    options = get_video_options(url)
    if not options:
        await update.message.reply_text("❌ Couldn't get video info.")
        return

    buttons = [
        [InlineKeyboardButton(text=label, callback_data=format_id)]
        for label, format_id in options[:10]
    ]
    markup = InlineKeyboardMarkup(buttons)
    await update.message.reply_text("Choose quality:", reply_markup=markup)

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    format_id = query.data
    url = context.user_data.get("video_url")

    await query.edit_message_text("📥 Downloading...")
    filename = download_video(url, format_id)

    if not filename:
        await query.message.reply_text("❌ Download failed.")
        return

    with open(filename, "rb") as f:
        await query.message.reply_video(video=f)

    os.remove(filename)

# Run the bot
def run_bot():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_link))
    app.run_polling()
