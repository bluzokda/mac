# main.py — с явным health-check

import os
import logging
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes
)
from flask import Flask, request

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "https://your-project.up.railway.app")

if not BOT_TOKEN:
    logger.error("❌ BOT_TOKEN not found!")
    exit(1)

if not WEBHOOK_URL:
    logger.error("❌ WEBHOOK_URL not set!")
    exit(1)

app = Flask(__name__)
application = None

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("✅ Бот работает!")

async def init_bot():
    global application
    application = Application.builder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    
    webhook_full_url = f"{WEBHOOK_URL}/webhook/{BOT_TOKEN}"
    await application.bot.set_webhook(url=webhook_full_url)
    logger.info(f"🔗 Webhook установлен: {webhook_full_url}")

@app.route('/')
def home():
    logger.info("🌍 / accessed")
    return "🤖 OSINT Bot is running!"

@app.route('/health')
def health():
    logger.info("✅ /health accessed")
    return "✅ OK"

@app.route(f'/webhook/{BOT_TOKEN}', methods=['POST'])
def telegram_webhook():
    if application:
        try:
            update = Update.de_json(request.get_json(force=True), application.bot)
            application.update_queue.put_nowait(update)
            logger.info(f"📩 Обновление получено: {update}")
        except Exception as e:
            logger.error(f"❌ Ошибка обработки webhook: {e}")
    return 'OK'

if __name__ == "__main__":
    import asyncio
    asyncio.run(init_bot())
    port = int(os.environ.get("PORT", 5000))
    logger.info(f"🚀 Запуск Flask на порту {port}")
    app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)
