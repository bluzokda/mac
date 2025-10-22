# main.py — OSINT бот с полным логированием

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

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Получаем переменные окружения
BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

if not BOT_TOKEN:
    logger.error("❌ BOT_TOKEN не задан!")
    exit(1)

if not WEBHOOK_URL:
    logger.error("❌ WEBHOOK_URL не задан! Добавь его в Railway Variables.")
    exit(1)

# Flask app
app = Flask(__name__)
application = None

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
    logger.info("🌍 Запрос к корневому маршруту /")
    return "🤖 OSINT Bot is running!"

@app.route("/health")
def health():
    logger.info("✅ Health-check запрос")
    return "✅ OK"

@app.route(f"/webhook/{BOT_TOKEN}", methods=["POST"])
def telegram_webhook():
    try:
        data = request.get_json(force=True)
        logger.info(f"📩 Получено обновление от Telegram: {data}")
        
        if application:
            update = Update.de_json(data, application.bot)
            application.update_queue.put_nowait(update)
            logger.info(f"✅ Обновление передано в очередь обработки")
        else:
            logger.warning("⚠️ Application не инициализирован!")
            
    except Exception as e:
        logger.error(f"💥 Ошибка в webhook: {e}")
    
    return "OK"

# === Инициализация бота ===

async def init_bot():
    global application
    logger.info("🚀 Инициализация Telegram бота...")
    
    application = Application.builder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Устанавливаем webhook
    webhook_full_url = f"{WEBHOOK_URL}/webhook/{BOT_TOKEN}"
    await application.bot.set_webhook(url=webhook_full_url)
    logger.info(f"🔗 Webhook успешно установлен: {webhook_full_url}")

# === Запуск ===

if __name__ == "__main__":
    import asyncio
    asyncio.run(init_bot())
    
    port = int(os.environ.get("PORT", 5000))
    logger.info(f"🚀 Запуск Flask сервера на порту {port}")
    app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)
