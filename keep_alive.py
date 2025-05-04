from flask import Flask
import threading

app = Flask('')

@app.route('/')
def home():
    return "Bot is running!"

def keep_alive():
    threading.Thread(target=app.run, kwargs={'host': '0.0.0.0', 'port': 8080}).start()
from flask import Flask, request
from telegram import Update
from telegram.ext import Application, ApplicationBuilder, ContextTypes

import os

app = Flask(__name__)
BOT_TOKEN = os.environ.get("BOT_TOKEN")
BOT_URL = os.environ.get("BOT_URL")  # e.g., https://your-bot.onrender.com

application: Application = None  # We'll initialize this from outside

@app.route('/')
def home():
    return 'Bot is alive (Webhook active)'

@app.route('/webhook', methods=['POST'])
def webhook():
    if request.method == 'POST':
        update = Update.de_json(request.get_json(force=True), application.bot)
        application.update_queue.put(update)
        return 'Webhook received', 200
