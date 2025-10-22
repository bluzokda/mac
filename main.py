# main.py — OSINT бот с проверкой ссылок, email и телефона

import os
import logging
import requests
import re
import ipaddress
import phonenumbers
from phonenumbers import geocoder, carrier
import dns.resolver
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

# Логирование
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

# === Валидаторы ===

def is_ip(text):
    try:
        ipaddress.ip_address(text)
        return True
    except ValueError:
        return False

def is_email(text):
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, text))

def is_phone_number(text):
    cleaned = re.sub(r'[^\d+]', '', text)
    return bool(re.match(r'^\+?[1-9]\d{1,14}$', cleaned))

def is_social_link(text):
    # Поддерживаем: vk.com, t.me, instagram.com, facebook.com, twitter.com, youtube.com
    social_patterns = [
        r'https?://(www\.)?vk\.com/[\w.-]+',
        r'https?://(www\.)?t\.me/[\w._-]+',
        r'https?://(www\.)?instagram\.com/[\w._-]+',
        r'https?://(www\.)?facebook\.com/[\w._-]+',
        r'https?://(www\.)?twitter\.com/[\w._-]+',
        r'https?://(www\.)?youtube\.com/@[\w._-]+'
    ]
    return any(re.match(pattern, text, re.IGNORECASE) for pattern in social_patterns)

# === Обработчики ===

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    keyboard_text = """
🔍 Отправь:
• IP-адрес (8.8.8.8)
• Email (user@example.com)
• Телефон (+79991234567)
• Ссылку на соцсеть (https://vk.com/id123)
"""
    await update.message.reply_text(
        f"👋 Привет, {user.first_name}!\n{keyboard_text}"
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    logger.info(f"📨 Получено: '{text}' от {update.effective_user.id}")

    if is_ip(text):
        await get_ip_info(update, text)
    elif is_email(text):
        await get_email_info(update, text)
    elif is_phone_number(text):
        await get_phone_info(update, text)
    elif is_social_link(text):
        await get_social_info(update, text)
    else:
        await update.message.reply_text("❌ Не распознал. Отправь IP, email, телефон или ссылку на соцсеть.")

# === OSINT функции ===

async def get_ip_info(update: Update, ip: str):
    try:
        await update.message.reply_text("🔄 Анализирую IP...")
        r = requests.get(f"https://ipapi.co/{ip}/json/", timeout=10)
        if r.status_code == 200:
            d = r.json()
            if d.get("error"):
                await update.message.reply_text("❌ Приватный или недопустимый IP.")
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
        await update.message.reply_text("❌ Ошибка при анализе IP")

async def get_email_info(update: Update, email: str):
    try:
        await update.message.reply_text("📧 Анализирую email...")
        domain = email.split('@')[1]
        
        # Проверка MX-записей
        try:
            mx_records = dns.resolver.resolve(domain, 'MX')
            mx_list = [str(mx.exchange) for mx in mx_records]
            mx_text = "\n".join(mx_list[:3])  # Первые 3 записи
        except:
            mx_text = "Нет MX-записей"
        
        info = f"""
📧 Email: {email}
🌐 Домен: {domain}
📬 MX-серверы:
{mx_text}
"""
        await update.message.reply_text(info)
    except Exception as e:
        logger.error(f"Email error: {e}")
        await update.message.reply_text("❌ Ошибка при анализе email")

async def get_phone_info(update: Update, phone: str):
    try:
        await update.message.reply_text("📞 Анализирую номер...")
        parsed = phonenumbers.parse(phone, None)
        country = geocoder.description_for_number(parsed, "ru")
        operator = carrier.name_for_number(parsed, "ru")
        is_valid = phonenumbers.is_valid_number(parsed)
        formatted = phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.INTERNATIONAL)
        
        info = f"""
📞 Номер: {formatted}
📍 Страна: {country or 'N/A'}
📡 Оператор: {operator or 'N/A'}
✅ Валиден: {'Да' if is_valid else 'Нет'}
"""
        await update.message.reply_text(info)
    except Exception as e:
        logger.error(f"Phone error: {e}")
        await update.message.reply_text("❌ Ошибка при анализе номера")

async def get_social_info(update: Update, link: str):
    try:
        await update.message.reply_text("🔍 Анализирую ссылку...")
        
        # Извлекаем платформу
        if "vk.com" in link:
            platform = "VK"
        elif "t.me" in link:
            platform = "Telegram"
        elif "instagram.com" in link:
            platform = "Instagram"
        elif "facebook.com" in link:
            platform = "Facebook"
        elif "twitter.com" in link:
            platform = "Twitter/X"
        elif "youtube.com" in link:
            platform = "YouTube"
        else:
            platform = "Неизвестно"
        
        info = f"""
🔗 Ссылка: {link}
📱 Платформа: {platform}
💡 Подсказка: Для глубокого анализа нужны API или ручной OSINT
"""
        await update.message.reply_text(info)
    except Exception as e:
        logger.error(f"Social link error: {e}")
        await update.message.reply_text("❌ Ошибка при анализе ссылки")

# === Flask ===

@app.route("/")
def home():
    return "🤖 OSINT Bot is running!"

@app.route("/health")
def health():
    return "✅ OK"

# === Запуск бота ===

def run_bot():
    application = Application.builder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    logger.info("▶️ Бот запущен в режиме polling...")
    application.run_polling(drop_pending_updates=True)

# === Точка входа ===

if __name__ == "__main__":
    # Flask в фоне
    flask_thread = threading.Thread(
        target=lambda: app.run(
            host="0.0.0.0",
            port=int(os.environ.get("PORT", 5000)),
            debug=False,
            use_reloader=False
        ),
        daemon=True
    )
    flask_thread.start()
    logger.info("🌐 Flask запущен в фоне")
    
    # Бот в основном потоке
    run_bot()
