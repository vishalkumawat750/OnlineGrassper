import os
import yt_dlp
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, filters
)
from asyncio import Lock

BOT_TOKEN = '6007538473:AAGPWq9MJMwMtt7csnLpJgmDOq99rTDvBZE'  # 🔁 Replace with your actual bot token

user_video_data = {}
user_locks = {}  # Lock per user

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🎥 Send a YouTube link to begin.")

async def get_video_options(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()
    chat_id = update.effective_chat.id

    try:
        ydl_opts = {'quiet': True, 'skip_download': True}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)

        formats = [
            f for f in info['formats']
            if f.get('ext') == 'mp4' and f.get('acodec') != 'none' and f.get('vcodec') != 'none'
        ]

        if not formats:
            await update.message.reply_text("❌ No valid MP4 formats found.")
            return

        video_options = {}
        buttons = []

        for f in formats:
            res = f.get('format_note') or f.get('height')
            size = f.get('filesize') or 0
            size_mb = round(size / 1024 / 1024, 1) if size else '?'
            label = f"{res} - {size_mb} MB"
            itag = str(f['format_id'])
            video_options[itag] = f
            buttons.append([InlineKeyboardButton(label, callback_data=itag)])

        user_video_data[chat_id] = {'url': url, 'formats': video_options}

        await update.message.reply_text("📥 Choose video quality:", reply_markup=InlineKeyboardMarkup(buttons))

    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    chat_id = query.message.chat.id
    itag = query.data

    # Disable buttons immediately to avoid double-click
    await query.edit_message_reply_markup(reply_markup=None)

    # Ensure per-user locking
    if chat_id not in user_locks:
        user_locks[chat_id] = Lock()

    async with user_locks[chat_id]:
        try:
            user_data = user_video_data.get(chat_id)
            if not user_data:
                await query.edit_message_text("⚠️ Session expired. Please send the link again.")
                return

            video_format = user_data['formats'].get(itag)
            url = user_data['url']

            ydl_opts = {
                'quiet': True,
                'format': itag,
                'outtmpl': 'downloaded_video.%(ext)s'
            }

            # Show progress message
            await query.edit_message_text("⬇️ Downloading, please wait...")

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])

            file_path = "downloaded_video.mp4"
            file_size = os.path.getsize(file_path)

            if file_size > 50 * 1024 * 1024:
                await query.edit_message_text("⚠️ File is large, sending as document...")
            else:
                await query.edit_message_text("📤 Uploading...")

            with open(file_path, 'rb') as f:
                await context.bot.send_document(chat_id=chat_id, document=f, filename="video.mp4")

            await query.edit_message_text("✅ Video sent!")
            os.remove(file_path)

        except Exception as e:
            print("Download error:", e)
            await query.edit_message_text(f"❌ Error during download: {str(e)}")

# 🔧 Global error handler
async def error_handler(update, context):
    print("❗ GLOBAL ERROR:", context.error)

# 🔧 Initialize bot
app = ApplicationBuilder().token(BOT_TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, get_video_options))
app.add_handler(CallbackQueryHandler(button_handler))
app.add_error_handler(error_handler)

print("🤖 Bot is running...")
app.run_polling()
