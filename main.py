# main.py — polling версия для Railway

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
from flask import Flask
import threading

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    logger.error("❌ BOT_TOKEN не задан!")
    exit(1)

app = Flask(__name__)

# === Обработчики Telegram ===

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    logger.info(f"👤 Пользователь {user.id} вызвал /start")
    await update.message.reply_text(
        f"👋 Привет, {user.first_name}!\nОтправь мне IP-адрес (например: 8.8.8.8)"
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    logger.info(f"📨 Получено сообщение от {update.effective_user.id}: '{text}'")
    
    if is_ip(text):
        await get_ip_info(update, text)
    else:
        await update.message.reply_text("🔍 Пожалуйста, отправь корректный IP-адрес.")

def is_ip(text):
    try:
        ipaddress.ip_address(text)
        return True
    except ValueError:
        return False

async def get_ip_info(update: Update, ip: str):
    try:
        logger.info(f"🌐 Запрос информации для IP: {ip}")
        await update.message.reply_text("🔄 Запрашиваю информацию...")
        
        response = requests.get(f"https://ipapi.co/{ip}/json/", timeout=10)
        if response.status_code == 200:
            data = response.json()
            logger.info(f"✅ Получены данные для IP {ip}: {data}")
            
            if data.get("error"):
                await update.message.reply_text("❌ Это приватный или недопустимый IP.")
            else:
                msg = (
                    f"🌐 IP: {ip}\n"
                    f"📍 Страна: {data.get('country_name', 'N/A')}\n"
                    f"🏙️ Город: {data.get('city', 'N/A')}\n"
                    f"📡 Провайдер: {data.get('org', 'N/A')}"
                )
                await update.message.reply_text(msg)
        else:
            logger.warning(f"⚠️ Ошибка API для IP {ip}: статус {response.status_code}")
            await update.message.reply_text("❌ Не удалось получить данные.")
            
    except Exception as e:
        logger.error(f"💥 Ошибка при запросе IP {ip}: {e}")
        await update.message.reply_text("❌ Произошла ошибка.")

# === Flask маршруты ===

@app.route("/")
def home():
    return "🤖 OSINT Bot is running!"

@app.route("/health")
def health():
    return "✅ OK"

# === Запуск бота ===

def run_bot():
    """Запускает Telegram бота в основном потоке"""
    application = Application.builder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    logger.info("▶️ Запуск бота в режиме polling...")
    application.run_polling(drop_pending_updates=True)

# === Точка входа ===

if __name__ == "__main__":
    # Запускаем Flask в фоновом потоке
    flask_thread = threading.Thread(target=lambda: app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 5000)),
        debug=False,
        use_reloader=False
    ), daemon=True)
    flask_thread.start()
    logger.info("🌐 Flask запущен в фоновом потоке")
    
    # Запускаем бота в основном потоке
    run_bot()
