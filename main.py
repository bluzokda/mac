import os
import logging
import requests
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext
from dotenv import load_dotenv

# Загрузка переменных окружения
load_dotenv()

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Токен бота из переменных окружения
BOT_TOKEN = os.getenv('BOT_TOKEN')
IPINFO_TOKEN = os.getenv('IPINFO_TOKEN')

# Клавиатура с командами
keyboard = [
    ['/start', '/help'],
    ['IP Info', 'Phone Info'],
    ['Whois Lookup', 'Email Check']
]

async def start(update: Update, context: CallbackContext) -> None:
    """Обработчик команды /start"""
    user = update.effective_user
    welcome_text = f"""
👋 Привет, {user.first_name}!

Я OSINT бот для сбора информации из открытых источников.

📋 Доступные команды:
• /start - начать работу
• /help - помощь
• IP Info - информация об IP адресе
• Phone Info - информация о номере телефона
• Whois Lookup - информация о домене
• Email Check - проверка email

Просто выбери опцию на клавиатуре или отправь мне данные для анализа!
    """
    await update.message.reply_text(
        welcome_text,
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    )

async def help_command(update: Update, context: CallbackContext) -> None:
    """Обработчик команды /help"""
    help_text = """
📖 Справка по использованию бота:

🔍 IP Info:
Отправь IP адрес для получения информации о геолокации, провайдере и т.д.

📞 Phone Info:
Отправь номер телефона для проверки (формат: +79123456789)

🌐 Whois Lookup:
Отправь домен для получения whois информации

📧 Email Check:
Отправь email адрес для базовой проверки

Примеры использования:
• 8.8.8.8
• +79123456789  
• google.com
• test@example.com
    """
    await update.message.reply_text(help_text)

async def handle_message(update: Update, context: CallbackContext) -> None:
    """Обработка текстовых сообщений"""
    text = update.message.text
    user_input = update.message.text.strip()
    
    # Определяем тип введенных данных
    if is_ip_address(user_input):
        await get_ip_info(update, user_input)
    elif is_phone_number(user_input):
        await get_phone_info(update, user_input)
    elif is_domain(user_input):
        await get_whois_info(update, user_input)
    elif is_email(user_input):
        await get_email_info(update, user_input)
    elif text in ['IP Info', 'Phone Info', 'Whois Lookup', 'Email Check']:
        await handle_button(update, text)
    else:
        await update.message.reply_text(
            "❌ Не могу определить тип данных. Отправь:\n"
            "• IP адрес (8.8.8.8)\n"
            "• Номер телефона (+79123456789)\n" 
            "• Домен (google.com)\n"
            "• Email (test@example.com)\n\n"
            "Или используй кнопки на клавиатуре 👆"
        )

async def handle_button(update: Update, button_text: str) -> None:
    """Обработка нажатий кнопок"""
    responses = {
        'IP Info': '🔍 Отправь мне IP адрес для анализа (например: 8.8.8.8)',
        'Phone Info': '📞 Отправь номер телефона (формат: +79123456789)',
        'Whois Lookup': '🌐 Отправь домен для whois проверки (например: google.com)',
        'Email Check': '📧 Отправь email адрес для проверки'
    }
    await update.message.reply_text(responses.get(button_text, 'Выбери опцию'))

# Функции проверки типов данных
def is_ip_address(text: str) -> bool:
    import re
    ip_pattern = r'^(\d{1,3}\.){3}\d{1,3}$'
    if re.match(ip_pattern, text):
        parts = text.split('.')
        return all(0 <= int(part) <= 255 for part in parts)
    return False

def is_phone_number(text: str) -> bool:
    import re
    phone_pattern = r'^\+?[1-9]\d{1,14}$'
    return bool(re.match(phone_pattern, text.replace(' ', '')))

def is_domain(text: str) -> bool:
    import re
    domain_pattern = r'^[a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z]{2,})+$'
    return bool(re.match(domain_pattern, text))

def is_email(text: str) -> bool:
    import re
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(email_pattern, text))

# OSINT функции
async def get_ip_info(update: Update, ip: str) -> None:
    """Получение информации об IP адресе"""
    try:
        await update.message.reply_text("🔄 Получаю информацию об IP...")
        
        # Используем ipapi.co (бесплатно до 1000 запросов в день)
        response = requests.get(f'http://ipapi.co/{ip}/json/')
        data = response.json()
        
        if 'error' in data:
            await update.message.reply_text("❌ Ошибка при получении информации об IP")
            return
            
        info_text = f"""
🌐 Информация об IP: {ip}

📍 **Геолокация:**
• Страна: {data.get('country_name', 'N/A')}
• Регион: {data.get('region', 'N/A')}
• Город: {data.get('city', 'N/A')}
• Почтовый индекс: {data.get('postal', 'N/A')}

📡 **Провайдер:**
• Организация: {data.get('org', 'N/A')}
• ASN: {data.get('asn', 'N/A')}

📊 **Техническая информация:**
• Часовой пояс: {data.get('timezone', 'N/A')}
• Валюта: {data.get('currency', 'N/A')}
• Язык: {data.get('languages', 'N/A')}
        """
        await update.message.reply_text(info_text)
        
    except Exception as e:
        logger.error(f"Error getting IP info: {e}")
        await update.message.reply_text("❌ Произошла ошибка при получении информации об IP")

async def get_phone_info(update: Update, phone: str) -> None:
    """Получение информации о номере телефона"""
    try:
        await update.message.reply_text("🔄 Анализирую номер телефона...")
        
        # Базовая информация о номере
        cleaned_phone = phone.replace('+', '').replace(' ', '')
        
        info_text = f"""
📞 Информация о номере: {phone}

📱 **Базовая информация:**
• Международный формат: +{cleaned_phone}
• Длина номера: {len(cleaned_phone)} цифр

💡 **Примечание:** 
Для расширенной анализа номера телефона требуется подключение 
к платным API (NumVerify, AbstractAPI и др.)
        """
        await update.message.reply_text(info_text)
        
    except Exception as e:
        logger.error(f"Error getting phone info: {e}")
        await update.message.reply_text("❌ Ошибка при анализе номера телефона")

async def get_whois_info(update: Update, domain: str) -> None:
    """Получение WHOIS информации о домене"""
    try:
        await update.message.reply_text("🔄 Получаю WHOIS информацию...")
        
        # Используем whoisxmlapi.com (бесплатно до 1000 запросов в месяц)
        # Для использования нужно зарегистрироваться и получить API ключ
        # Пока используем базовую информацию
        
        import whois
        try:
            domain_info = whois.whois(domain)
            
            info_text = f"""
🌐 WHOIS информация для: {domain}

📅 **Даты:**
• Создан: {domain_info.creation_date if domain_info.creation_date else 'N/A'}
• Истекает: {domain_info.expiration_date if domain_info.expiration_date else 'N/A'}
• Обновлен: {domain_info.updated_date if domain_info.updated_date else 'N/A'}

👤 **Регистратор:**
• Registrar: {domain_info.registrar if domain_info.registrar else 'N/A'}
• WHOIS сервер: {domain_info.whois_server if domain_info.whois_server else 'N/A'}

🔒 **Статусы:**
{chr(10).join(f'• {status}' for status in domain_info.statuses) if domain_info.statuses else '• N/A'}
            """
            await update.message.reply_text(info_text)
            
        except Exception as whois_error:
            await update.message.reply_text(f"""
🌐 Базовая информация для: {domain}

❌ Детальная WHOIS информация недоступна.
Для полной функциональности требуется:
1. Установка whois: pip install python-whois
2. Или подключение WHOIS API

📋 Можно проверить вручную:
whois {domain}
            """)
            
    except Exception as e:
        logger.error(f"Error getting WHOIS info: {e}")
        await update.message.reply_text("❌ Ошибка при получении WHOIS информации")

async def get_email_info(update: Update, email: str) -> None:
    """Базовая проверка email"""
    try:
        await update.message.reply_text("🔄 Анализирую email...")
        
        # Базовая проверка формата и домена
        domain = email.split('@')[1] if '@' in email else ''
        
        info_text = f"""
📧 Анализ email: {email}

📋 **Базовая информация:**
• Домен: {domain if domain else 'N/A'}
• Формат: {'✅ Корректный' if is_email(email) else '❌ Некорректный'}

💡 **Примечание:**
Для расширенной проверки email (HIBP, Hunter.io) 
требуется подключение к специализированным API
        """
        await update.message.reply_text(info_text)
        
    except Exception as e:
        logger.error(f"Error getting email info: {e}")
        await update.message.reply_text("❌ Ошибка при анализе email")

async def error_handler(update: Update, context: CallbackContext) -> None:
    """Обработчик ошибок"""
    logger.error(f"Update {update} caused error {context.error}")
    if update and update.message:
        await update.message.reply_text("❌ Произошла ошибка при обработке запроса")

def main() -> None:
    """Запуск бота"""
    if not BOT_TOKEN:
        logger.error("BOT_TOKEN not found in environment variables")
        return
    
    # Создаем приложение
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Добавляем обработчики
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_error_handler(error_handler)
    
    # Запускаем бота
    logger.info("Bot is starting...")
    application.run_polling()

if __name__ == '__main__':
    main()
