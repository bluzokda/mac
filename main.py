import os
import logging
import requests
import re
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext
from flask import Flask

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Flask app для здоровья
app = Flask(__name__)

@app.route('/')
def home():
    return "🤖 OSINT Bot is running!"

@app.route('/health')
def health():
    return "✅ OK"

# Получаем токен
BOT_TOKEN = os.getenv('BOT_TOKEN')

if not BOT_TOKEN:
    logger.error("❌ BOT_TOKEN not found!")
    # Для Railway просто выходим, так как без токена бот не может работать
    exit(1)
else:
    logger.info("✅ BOT_TOKEN found")

# Клавиатура
keyboard = [['/start', '/help'], ['IP Info', 'Domain Check']]

async def start(update: Update, context: CallbackContext) -> None:
    user = update.effective_user
    await update.message.reply_text(
        f"👋 Привет, {user.first_name}!\n\nЯ OSINT бот. Отправь мне:\n• IP адрес\n• Домен\n• Email\n• Номер телефона",
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    )

async def help_command(update: Update, context: CallbackContext) -> None:
    help_text = """
📖 Доступные команды:

🔍 IP Info - информация об IP
🌐 Domain Check - проверка домена  
📧 Email - базовая проверка
📞 Phone - информация о номере

Просто отправь данные для анализа!
"""
    await update.message.reply_text(help_text)

async def handle_message(update: Update, context: CallbackContext) -> None:
    text = update.message.text.strip()
    
    if text == 'IP Info':
        await update.message.reply_text("🔍 Отправь IP адрес (например: 8.8.8.8)")
    elif text == 'Domain Check':
        await update.message.reply_text("🌐 Отправь домен (например: google.com)")
    elif is_ip_address(text):
        await get_ip_info(update, text)
    elif is_domain(text):
        await get_domain_info(update, text)
    elif is_email(text):
        await get_email_info(update, text)
    elif is_phone_number(text):
        await get_phone_info(update, text)
    else:
        await update.message.reply_text("❌ Не понял запрос. Используй кнопки или отправь данные для анализа")

def is_ip_address(text: str) -> bool:
    pattern = r'^(\d{1,3}\.){3}\d{1,3}$'
    if re.match(pattern, text):
        return all(0 <= int(part) <= 255 for part in text.split('.'))
    return False

def is_phone_number(text: str) -> bool:
    pattern = r'^\+?[1-9]\d{1,14}$'
    return bool(re.match(pattern, text.replace(' ', '')))

def is_domain(text: str) -> bool:
    pattern = r'^[a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z]{2,})+$'
    return bool(re.match(pattern, text))

def is_email(text: str) -> bool:
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, text))

async def get_ip_info(update: Update, ip: str) -> None:
    try:
        await update.message.reply_text("🔄 Анализирую IP...")
        response = requests.get(f'http://ipapi.co/{ip}/json/', timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            info = f"""
🌐 IP: {ip}
📍 Страна: {data.get('country_name', 'N/A')}
🏙️ Город: {data.get('city', 'N/A')}
📡 Провайдер: {data.get('org', 'N/A')}
⏰ Часовой пояс: {data.get('timezone', 'N/A')}
"""
            await update.message.reply_text(info)
        else:
            await update.message.reply_text("❌ Не удалось получить информацию об IP")
            
    except Exception as e:
        logger.error(f"Error getting IP info: {e}")
        await update.message.reply_text("❌ Ошибка при анализе IP")

async def get_domain_info(update: Update, domain: str) -> None:
    try:
        await update.message.reply_text("🔄 Проверяю домен...")
        
        info = f"""
🌐 Домен: {domain}
✅ Формат: Корректный
💡 Для детальной WHOIS информации требуется дополнительная настройка
"""
        await update.message.reply_text(info)
        
    except Exception as e:
        logger.error(f"Error getting domain info: {e}")
        await update.message.reply_text("❌ Ошибка при проверке домена")

async def get_email_info(update: Update, email: str) -> None:
    try:
        await update.message.reply_text("🔄 Анализирую email...")
        domain = email.split('@')[1] if '@' in email else ''
        
        info = f"""
📧 Email: {email}
🌐 Домен: {domain}
✅ Формат: Корректный
"""
        await update.message.reply_text(info)
        
    except Exception as e:
        logger.error(f"Error getting email info: {e}")
        await update.message.reply_text("❌ Ошибка при анализе email")

async def get_phone_info(update: Update, phone: str) -> None:
    try:
        await update.message.reply_text("🔄 Анализирую номер...")
        cleaned = phone.replace('+', '').replace(' ', '')
        
        info = f"""
📞 Номер: {phone}
🔢 Формат: +{cleaned}
📏 Длина: {len(cleaned)} цифр
"""
        await update.message.reply_text(info)
        
    except Exception as e:
        logger.error(f"Error getting phone info: {e}")
        await update.message.reply_text("❌ Ошибка при анализе номера")

def run_bot():
    """Запуск бота"""
    try:
        application = Application.builder().token(BOT_TOKEN).build()
        
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("help", help_command))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
        
        logger.info("🤖 Бот запускается...")
        application.run_polling(drop_pending_updates=True)
        
    except Exception as e:
        logger.error(f"❌ Ошибка запуска бота: {e}")

if __name__ == '__main__':
    import threading
    
    # Запускаем бота в отдельном потоке
    bot_thread = threading.Thread(target=run_bot, daemon=True)
    bot_thread.start()
    logger.info("🤖 Bot thread started")
    
    # Запускаем Flask для Railway
    port = int(os.environ.get('PORT', 5000))
    logger.info(f"🚀 Starting Flask on port {port}")
    app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)
