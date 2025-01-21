import os
import json
import logging
from datetime import datetime
import requests
from dotenv import load_dotenv
from telegram import Update, WebAppInfo, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler, ContextTypes

# Загружаем переменные окружения
load_dotenv()

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# API URL
API_BASE_URL = 'http://localhost:9966/api'

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начало работы с ботом"""
    user = update.effective_user
    name = user.first_name if user.first_name else "Дорогой гость"
    
    # Создаем кнопку для открытия mini app
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(
            "Открыть меню 📋",
            web_app=WebAppInfo(url="https://your-domain.com/mini_app/")
        )],
        [InlineKeyboardButton("Помощь ❓", callback_data="help"),
         InlineKeyboardButton("О нас ℹ️", callback_data="about")]
    ])
    
    welcome_message = (
        f"👋 Здравствуйте, {name}!\n\n"
        "Мы рады приветствовать вас в нашем сервисе доставки еды! 🎉\n"
        "У нас вы найдете разнообразные блюда, приготовленные с любовью и заботой.\n\n"
        "Нажмите кнопку 'Открыть меню' чтобы сделать заказ 👇"
    )
    
    await update.message.reply_text(welcome_message, reply_markup=keyboard)

async def web_app_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка данных от mini app"""
    try:
        data = json.loads(update.message.web_app_data.data)
        
        if data.get('action') == 'order_created':
            order_id = data.get('order_id')
            if order_id:
                # Получаем информацию о заказе
                response = requests.get(
                    f'{API_BASE_URL}/orders/{order_id}',
                    auth=(os.getenv('BOT_USERNAME'), os.getenv('BOT_PASSWORD'))
                )
                
                if response.ok:
                    order = response.json()
                    # Запрашиваем номер телефона
                    await request_phone(update, context, order)
                else:
                    await update.message.reply_text(
                        "Произошла ошибка при получении информации о заказе. "
                        "Пожалуйста, попробуйте позже."
                    )
    except Exception as e:
        logger.error(f"Error processing web app data: {str(e)}")
        await update.message.reply_text(
            "Произошла ошибка при обработке заказа. "
            "Пожалуйста, попробуйте позже."
        )

async def request_phone(update: Update, context: ContextTypes.DEFAULT_TYPE, order):
    """Запрос номера телефона"""
    keyboard = ReplyKeyboardMarkup([
        [KeyboardButton("Отправить номер телефона 📱", request_contact=True)]
    ], resize_keyboard=True)
    
    await update.message.reply_text(
        "Для оформления заказа нам нужен ваш номер телефона. "
        "Нажмите на кнопку ниже, чтобы поделиться им.",
        reply_markup=keyboard
    )
    context.user_data['pending_order'] = order

def main():
    """Запуск бота"""
    # Создаем приложение
    application = Application.builder().token(os.getenv('TELEGRAM_BOT_TOKEN')).build()

    # Добавляем обработчики
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.StatusUpdate.WEB_APP_DATA, web_app_data))
    
    # Запускаем бота
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
