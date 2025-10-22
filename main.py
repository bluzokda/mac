# main.py — с явным health-check и fallback

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
application = None

# === Обработчики Telegram ===

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await update.message.reply_text(
        f"👋 Привет, {user.first_name}!\nОтправь мне IP-адрес (например: 8.8.8.8)"
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
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
        await update.message.reply_text("🔄 Запрашиваю информацию...")
        response = requests.get(f"https://ipapi.co/{ip}/json/", timeout=10)
        if response.status_code == 200:
            data = response.json()
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
            await update.message.reply_text("❌ Не удалось получить данные.")
    except Exception as e:
        logger.error(f"Ошибка при запросе IP: {e}")
        await update.message.reply_text("❌ Произошла ошибка.")

# === Flask маршруты ===

@app.route("/")
def home():
    logger.info("🌍 / accessed")
    return "🤖 OSINT Bot is running!"

@app.route("/health")
def health():
    logger.info("✅ /health accessed")
    return "✅ OK"

@app.route(f"/webhook/{BOT_TOKEN}", methods=["POST"])
def telegram_webhook():
    if application:
        try:
            update = Update.de_json(request.get_json(force=True), application.bot)
            application.update_queue.put_nowait(update)
            logger.info(f"📩 Обновление получено: {update}")
        except Exception as e:
            logger.error(f"❌ Ошибка обработки webhook: {e}")
    return "OK"

# === Инициализация бота ===

async def init_bot():
    global application
    application = Application.builder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Устанавливаем webhook через RAILWAY_PUBLIC_DOMAIN
    domain = os.getenv("RAILWAY_PUBLIC_DOMAIN")
    if domain:
        webhook_url = f"https://{domain}/webhook/{BOT_TOKEN}"
        await application.bot.set_webhook(url=webhook_url)
        logger.info(f"🔗 Webhook установлен: {webhook_url}")
    else:
        logger.warning("⚠️ RAILWAY_PUBLIC_DOMAIN не найден. Webhook не установлен.")

# === Запуск ===

if __name__ == "__main__":
    import asyncio
    asyncio.run(init_bot())
    
    port = int(os.environ.get("PORT", 5000))
    logger.info(f"🚀 Запуск Flask на порту {port}")
    app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)
