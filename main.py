# main.py — webhook версия с корректным await

import os
import logging
import requests
import re
import ipaddress
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes
)
from flask import Flask, request
import asyncio

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    logger.error("❌ BOT_TOKEN not found!")
    exit(1)

# Получаем URL из переменной (ты должен установить её в Railway)
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
if not WEBHOOK_URL:
    logger.error("❌ WEBHOOK_URL not set! Please add it in Railway Variables.")
    exit(1)

# Flask app
flask_app = Flask(__name__)

# Telegram application
application = None

# === Обработчики ===
keyboard = [['/start', '/help'], ['IP Info', 'Domain Check']]

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await update.message.reply_text(
        f"👋 Привет, {user.first_name}!\nОтправь IP, домен, email или телефон.",
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📖 Просто отправь данные для анализа.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if text == 'IP Info':
        await update.message.reply_text("🔍 Отправь IP (например: 8.8.8.8)")
    elif text == 'Domain Check':
        await update.message.reply_text("🌐 Отправь домен (например: google.com)")
    elif is_ip(text):
        await get_ip_info(update, text)
    else:
        await update.message.reply_text("✅ Данные получены.")

def is_ip(text):
    try:
        ipaddress.ip_address(text)
        return True
    except ValueError:
        return False

async def get_ip_info(update: Update, ip: str):
    try:
        await update.message.reply_text("🔄 Запрос...")
        r = requests.get(f"https://ipapi.co/{ip}/json/", timeout=10)
        if r.status_code == 200:
            d = r.json()
            msg = f"🌐 IP: {ip}\n📍 Страна: {d.get('country_name', 'N/A')}"
            await update.message.reply_text(msg)
        else:
            await update.message.reply_text("❌ Ошибка API")
    except Exception as e:
        logger.error(f"IP error: {e}")
        await update.message.reply_text("❌ Ошибка")

# === Flask routes ===
@flask_app.route('/')
def home():
    return "🤖 OSINT Bot is running!"

@flask_app.route('/health')
def health():
    return "✅ OK"

@flask_app.route(f'/webhook/{BOT_TOKEN}', methods=['POST'])
def telegram_webhook():
    if application:
        application.update_queue.put_nowait(
            Update.de_json(request.get_json(force=True), application.bot)
        )
    return 'OK'

# === Инициализация бота (асинхронная) ===
async def init_bot():
    global application
    application = Application.builder().token(BOT_TOKEN).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Устанавливаем webhook АСИНХРОННО
    webhook_full_url = f"{WEBHOOK_URL}/webhook/{BOT_TOKEN}"
    await application.bot.set_webhook(url=webhook_full_url)
    logger.info(f"🔗 Webhook успешно установлен: {webhook_full_url}")

# === Запуск ===
if __name__ == "__main__":
    # Запускаем инициализацию бота
    asyncio.run(init_bot())
    
    # Запускаем Flask
    port = int(os.environ.get("PORT", 5000))
    logger.info(f"🚀 Запуск Flask на порту {port}")
    flask_app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)
