# main.py — стабильная версия для Railway + Python 3.13 + python-telegram-bot 21.0.1

import os
import logging
import requests
import re
import ipaddress
from telegram import Update, Bot
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes
)
from flask import Flask
import threading

# Логирование
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Flask для health-check
app_flask = Flask(__name__)

@app_flask.route('/')
def home():
    return "🤖 OSINT Bot is running!"

@app_flask.route('/health')
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
        f"👋 Привет, {user.first_name}!\n\nЯ OSINT бот. Отправь мне:\n• IP\n• Домен\n• Email\n• Телефон",
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
        await update.message.reply_text("✅ Данные приняты (анализ пока базовый).")

def is_ip(text):
    try:
        ipaddress.ip_address(text)
        return True
    except ValueError:
        return False

async def get_ip_info(update: Update, ip: str):
    try:
        await update.message.reply_text("🔄 Запрос к ipapi.co...")
        r = requests.get(f"https://ipapi.co/{ip}/json/", timeout=10)
        if r.status_code == 200:
            d = r.json()
            if d.get("error"):
                await update.message.reply_text("❌ Приватный или неверный IP.")
            else:
                msg = f"""
🌐 IP: {ip}
📍 Страна: {d.get('country_name', 'N/A')}
🏙️ Город: {d.get('city', 'N/A')}
📡 Провайдер: {d.get('org', 'N/A')}
"""
                await update.message.reply_text(msg)
        else:
            await update.message.reply_text("❌ Ошибка API")
    except Exception as e:
        logger.error(f"IP error: {e}")
        await update.message.reply_text("❌ Ошибка при запросе IP")

# --- Запуск бота (СИНХРОННЫЙ) ---

def run_bot():
    """Запуск бота — СИНХРОННАЯ функция"""
    try:
        # Удаляем webhook через синхронный вызов
        bot = Bot(token=BOT_TOKEN)
        # Используем run для асинхронного вызова внутри синхронной функции
        import asyncio
        asyncio.run(bot.delete_webhook(drop_pending_updates=True))
        logger.info("🧹 Webhook удалён")

        # Создаём и запускаем приложение
        application = Application.builder().token(BOT_TOKEN).build()
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("help", help_command))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
        
        logger.info("🤖 Бот запускается...")
        application.run_polling(drop_pending_updates=True)  # <-- это блокирующий вызов
        
    except Exception as e:
        logger.error(f"❌ Ошибка запуска бота: {e}")
        raise

# --- Flask в фоне ---

def run_flask():
    port = int(os.environ.get("PORT", 5000))
    app_flask.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)

# --- Точка входа ---

if __name__ == "__main__":
    # Запускаем Flask в фоне
    threading.Thread(target=run_flask, daemon=True).start()
    logger.info("🌐 Flask запущен в фоне")
    
    # Запускаем бота в основном потоке (блокирующий вызов)
    run_bot()
