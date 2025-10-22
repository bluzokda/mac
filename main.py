# main.py — продвинутый OSINT бот

import os
import logging
import requests
import re
import ipaddress
import phonenumbers
from phonenumbers import geocoder, carrier
import dns.resolver
from bs4 import BeautifulSoup
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
HIBP_API_KEY = os.getenv("HIBP_API_KEY")  # Optional

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
    return bool(re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', text))

def is_phone_number(text):
    cleaned = re.sub(r'[^\d+]', '', text)
    return bool(re.match(r'^\+?[1-9]\d{1,14}$', cleaned))

def is_vk_link(text):
    return bool(re.match(r'https?://(www\.)?vk\.com/[\w.-]+', text, re.IGNORECASE))

# === OSINT функции ===

async def get_ip_info(update: Update, ip: str):
    await update.message.reply_text("🔄 Анализирую IP...")
    
    # Попробуем ipapi.co
    try:
        r = requests.get(f"https://ipapi.co/{ip}/json/", timeout=8)
        if r.status_code == 200:
            d = r.json()
            if not d.get("error"):
                msg = f"""
🌐 IP: {ip}
📍 Страна: {d.get('country_name', 'N/A')}
🏙️ Город: {d.get('city', 'N/A')}
📡 Провайдер: {d.get('org', 'N/A')}
🕒 Часовой пояс: {d.get('timezone', 'N/A')}
"""
                await update.message.reply_text(msg)
                return
    except:
        pass
    
    # Fallback на ipinfo.io
    try:
        r = requests.get(f"https://ipinfo.io/{ip}/json", timeout=8)
        if r.status_code == 200:
            d = r.json()
            msg = f"""
🌐 IP: {ip}
📍 Страна: {d.get('country', 'N/A')}
🏙️ Город: {d.get('city', 'N/A')}
📡 Провайдер: {d.get('org', 'N/A')}
"""
            await update.message.reply_text(msg)
            return
    except:
        pass
    
    await update.message.reply_text("❌ Не удалось получить данные об IP")

async def get_phone_info(update: Update, phone: str):
    await update.message.reply_text("📞 Анализирую номер...")
    
    try:
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
⚠️ Примечание: Данные о владельце недоступны публично
"""
        await update.message.reply_text(info)
    except Exception as e:
        logger.error(f"Phone error: {e}")
        await update.message.reply_text("❌ Ошибка при анализе номера")

async def get_email_info(update: Update, email: str):
    await update.message.reply_text("📧 Анализирую email...")
    
    domain = email.split('@')[1]
    
    # MX записи
    try:
        mx_records = dns.resolver.resolve(domain, 'MX')
        mx_list = [str(mx.exchange) for mx in mx_records]
        mx_text = "\n".join(mx_list[:3])
    except:
        mx_text = "Нет MX-записей"
    
    # Проверка в утечках (если есть API ключ)
    breach_info = "🔍 Утечки: Не проверялось (нужен HIBP_API_KEY)"
    if HIBP_API_KEY:
        try:
            headers = {"hibp-api-key": HIBP_API_KEY}
            r = requests.get(f"https://haveibeenpwned.com/api/v3/breachedaccount/{email}", headers=headers, timeout=10)
            if r.status_code == 200:
                breaches = r.json()
                breach_names = [b['Name'] for b in breaches[:3]]
                breach_info = f"🔍 Утечки: {', '.join(breach_names)}"
            elif r.status_code == 404:
                breach_info = "✅ Утечек не найдено"
        except:
            breach_info = "⚠️ Ошибка проверки утечек"
    
    info = f"""
📧 Email: {email}
🌐 Домен: {domain}
📬 MX-серверы:
{mx_text}

{breach_info}

💡 Примечание: Данные о владельце недоступны публично
"""
    await update.message.reply_text(info)

async def get_vk_info(update: Update, link: str):
    await update.message.reply_text("🕵️‍♂️ Анализирую профиль ВК...")
    
    # Извлекаем ID или короткое имя
    username = link.split('/')[-1]
    if '?' in username:
        username = username.split('?')[0]
    
    try:
        url = f"https://vk.com/{username}"
        headers = {"User-Agent": "Mozilla/5.0"}
        r = requests.get(url, headers=headers, timeout=10)
        
        if r.status_code == 200:
            soup = BeautifulSoup(r.text, 'html.parser')
            title = soup.find('title')
            if title and "not found" not in title.text.lower():
                profile_info = f"""
🔗 Профиль: {url}
📝 Заголовок: {title.text if title else 'N/A'}

🔍 Примечание: 
• Полные данные недоступны без авторизации
• Если профиль закрыт — видна только публичная информация
• Для глубокого анализа нужны специальные инструменты
"""
                await update.message.reply_text(profile_info)
            else:
                await update.message.reply_text("❌ Профиль не найден или закрыт")
        else:
            await update.message.reply_text("❌ Не удалось получить данные ВК")
    except Exception as e:
        logger.error(f"VK error: {e}")
        await update.message.reply_text("❌ Ошибка при анализе ВК")

# === Обработчики ===

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    text = """
🔍 OSINT Бот v2.0

Отправь:
• IP-адрес
• Email 
• Телефон (+79991234567)
• Ссылку ВК (https://vk.com/id123)

⚠️ Важно: Многие данные недоступны публично из-за приватности
"""
    await update.message.reply_text(f"👋 Привет, {user.first_name}!\n{text}")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    logger.info(f"📨 Получено: '{text}'")

    if is_ip(text):
        await get_ip_info(update, text)
    elif is_email(text):
        await get_email_info(update, text)
    elif is_phone_number(text):
        await get_phone_info(update, text)
    elif is_vk_link(text):
        await get_vk_info(update, text)
    else:
        await update.message.reply_text("❌ Не распознал. Отправь IP, email, телефон или ссылку ВК.")

# === Flask ===

@app.route("/")
def home():
    return "🤖 OSINT Bot is running!"

@app.route("/health")
def health():
    return "✅ OK"

# === Запуск ===

def run_bot():
    application = Application.builder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    # Установим переменные для парсинга
    os.environ.setdefault('SCRAPY_SETTINGS_MODULE', 'settings')
    
    flask_thread = threading.Thread(
        target=lambda: app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=False, use_reloader=False),
        daemon=True
    )
    flask_thread.start()
    logger.info("🌐 Flask запущен")
    run_bot()
