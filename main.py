import os
import logging
import requests
import re
import ipaddress
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from flask import Flask
import threading

# Логирование
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Flask для Railway
app = Flask(__name__)

@app.route('/')
def home():
    return "🤖 OSINT Bot is running!"

@app.route('/health')
def health():
    return "✅ OK"

BOT_TOKEN = os.getenv('BOT_TOKEN')
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
    await update.message.reply_text("📖 Отправь IP, домен, email или телефон для анализа.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if text == 'IP Info':
        await update.message.reply_text("🔍 Отправь IP (например: 8.8.8.8)")
    elif text == 'Domain Check':
        await update.message.reply_text("🌐 Отправь домен (например: google.com)")
    elif is_ip(text):
        await get_ip_info(update, text)
    elif is_domain(text):
        await update.message.reply_text(f"🌐 Домен {text} — формат корректен.")
    elif is_email(text):
        await update.message.reply_text(f"📧 Email {text} — формат корректен.")
    elif is_phone(text):
        await update.message.reply_text(f"📞 Номер {text} — формат корректен.")
    else:
        await update.message.reply_text("❌ Не распознал. Используй кнопки.")

def is_ip(text):
    try:
        ipaddress.ip_address(text)
        return True
    except:
        return False

def is_domain(text):
    return bool(re.match(r'^[a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z]{2,})+$', text))

def is_email(text):
    return bool(re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', text))

def is_phone(text):
    clean = re.sub(r'[^\d+]', '', text)
    return bool(re.match(r'^\+?[1-9]\d{1,14}$', clean))

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

def run_flask():
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)

def run_bot():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    logger.info("🤖 Бот запускается...")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    # Flask в фоне
    threading.Thread(target=run_flask, daemon=True).start()
    logger.info("🌐 Flask запущен в фоне")
    # Бот в основном потоке
    run_bot()
