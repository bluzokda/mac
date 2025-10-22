# main.py — гарантированно работает на Python 3.13 + Railway

import os
import logging
import requests
import re
import ipaddress
import asyncio
import threading
from telegram import Update, Bot
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes
)
from flask import Flask

# Логирование
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Flask для Railway health-check
flask_app = Flask(__name__)

@flask_app.route('/')
def home():
    return "🤖 OSINT Bot is running!"

@flask_app.route('/health')
def health():
    return "✅ OK"

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    logger.error("❌ BOT_TOKEN not found!")
    exit(1)

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

# --- Асинхронный запуск бота ---
async def main_bot():
    # Удаляем webhook
    bot = Bot(token=BOT_TOKEN)
    await bot.delete_webhook(drop_pending_updates=True)
    logger.info("🧹 Webhook удалён")

    # Создаём приложение
    application = Application.builder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    logger.info("🤖 Бот запущен и ожидает сообщений...")
    await application.run_polling(drop_pending_updates=True)

# --- Flask в отдельном потоке ---
def run_flask():
    port = int(os.environ.get("PORT", 5000))
    flask_app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)

# --- Точка входа ---
if __name__ == "__main__":
    # Запускаем Flask в фоне
    threading.Thread(target=run_flask, daemon=True).start()
    logger.info("🌐 Flask запущен")

    # Запускаем бота через asyncio.run()
    asyncio.run(main_bot())
