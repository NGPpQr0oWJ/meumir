import os
import logging
from datetime import datetime
import requests
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes, ConversationHandler
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils import get_server_time

# Загружаем переменные окружения
load_dotenv()

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Состояния разговора
MENU, QUANTITY, PHONE, ADDRESS, CONFIRM = range(5)

# API URL
API_BASE_URL = 'http://localhost:9966/api'

class OrderData:
    def __init__(self):
        self.items = {}  # {dish_id: {'quantity': int, 'name': str, 'price': float}}
        self.customer_name = ""
        self.phone_number = ""
        self.delivery_address = ""
        self.current_dish_id = None  # Для хранения ID блюда при выборе количества

# Хранилище данных заказов
user_orders = {}
# Кэш меню
menu_cache = {
    'data': None,
    'timestamp': None
}

def get_cached_menu():
    """Получает меню из кэша или обновляет его"""
    current_time = get_server_time()
    
    # Если кэш пустой или прошло больше 5 минут, обновляем
    if (menu_cache['data'] is None or 
        menu_cache['timestamp'] is None or 
        (current_time - menu_cache['timestamp']).seconds > 300):
        try:
            response = requests.get(
                f'{API_BASE_URL}/menu/today',
                auth=(os.getenv('BOT_USERNAME'), os.getenv('BOT_PASSWORD'))
            )
            if response.status_code == 200:
                menu_cache['data'] = response.json()['menu']
                menu_cache['timestamp'] = current_time
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching menu: {str(e)}")
            if menu_cache['data'] is None:
                return []
    
    return menu_cache['data']

def create_main_keyboard():
    """Создает основную клавиатуру с командами"""
    keyboard = ReplyKeyboardMarkup([
        ['/menu 📋'],
        ['/start 🏠']
    ], resize_keyboard=True)
    return keyboard

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начало работы с ботом"""
    user = update.effective_user
    name = user.first_name if user.first_name else "Дорогой гость"
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("Перейти к меню 📋", callback_data="show_menu")],
        [InlineKeyboardButton("Помощь ❓", callback_data="help"),
         InlineKeyboardButton("О нас ℹ️", callback_data="about")]
    ])
    
    welcome_message = (
        f"👋 Здравствуйте, {name}!\n\n"
        "Мы рады приветствовать вас в нашем сервисе доставки еды! 🎉\n"
        "У нас вы найдете разнообразные блюда, приготовленные с любовью и заботой.\n\n"
        "Чтобы начать заказ, нажмите кнопку ниже 👇"
    )
    
    if update.message:
        await update.message.reply_text(
            welcome_message,
            reply_markup=keyboard
        )
    elif update.callback_query:
        await update.callback_query.message.edit_text(
            welcome_message,
            reply_markup=keyboard
        )
    
    return MENU

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик кнопки Помощь"""
    help_text = (
        "🆘 *Помощь по использованию бота*\n\n"
        "1. Для заказа еды нажмите 'Перейти к меню'\n"
        "2. Выберите интересующие блюда\n"
        "3. Укажите количество порций\n"
        "4. Введите контактные данные\n"
        "5. Подтвердите заказ\n\n"
        "При возникновении проблем свяжитесь с нами по телефону: +7-(989)-132-83-44"
    )
    await update.callback_query.message.edit_text(
        help_text,
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("◀️ Назад", callback_data="back_to_start")
        ]])
    )

async def about_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик кнопки О нас"""
    about_text = (
        "🍽 *Вкусные обеды с доставкой!*\n\n"
        "Мы готовим с любовью и заботой, чтобы ваш обед был не просто приемом пищи, "
        "а настоящим гастрономическим удовольствием! 😊\n\n"
        "*Как это работает:*\n"
        "🕙 Принимаем заказы: до 13:00\n"
        "🚚 Доставляем: с 11:00 до 14:00\n"
        "👨‍🍳 Наши повара готовят из свежих продуктов\n"
        "♨️ Доставляем горячим в удобных контейнерах\n\n"
        "Порадуйте себя вкусным домашним обедом! 🎉"
    )
    await update.callback_query.message.edit_text(
        about_text,
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("◀️ Назад", callback_data="back_to_start")
        ]])
    )

async def show_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает меню"""
    query = update.callback_query
    if query:
        await query.answer()
        message = query.message
    else:
        message = update.message

    try:
        menu_data = get_cached_menu()
        if not menu_data:
            await message.reply_text('На сегодня меню пока не доступно.')
            return ConversationHandler.END

        # Создаем новый заказ для пользователя
        user_id = update.effective_user.id
        if user_id not in user_orders:
            user_orders[user_id] = OrderData()
        
        # Группируем блюда по категориям
        menu_by_category = {}
        for item in menu_data:
            category = item.get('category', 'Без категории')
            if category not in menu_by_category:
                menu_by_category[category] = []
            menu_by_category[category].append(item)

        # Формируем сообщение с меню
        message_text = "🍽 Меню на сегодня:\n\n"
        keyboard = []

        for category, items in menu_by_category.items():
            message_text += f"*{category}*\n"
            for item in items:
                message_text += f"• {item['name']} - {item['price']}₽\n"
                if user_id in user_orders and item['id'] in user_orders[user_id].items:
                    current_qty = user_orders[user_id].items[item['id']]['quantity']
                    keyboard.append([
                        InlineKeyboardButton("➖", callback_data=f"dec_{item['id']}"),
                        InlineKeyboardButton(f"{item['name']} - {current_qty} порц.", callback_data=f"info_{item['id']}"),
                        InlineKeyboardButton("➕", callback_data=f"inc_{item['id']}")
                    ])
                else:
                    keyboard.append([
                        InlineKeyboardButton(f"Добавить {item['name']}", callback_data=f"select_{item['id']}")
                    ])

        # Добавляем кнопки оформления заказа и возврата назад
        bottom_buttons = []
        if user_orders[user_id].items:
            bottom_buttons.append(InlineKeyboardButton("💳 Оформить заказ", callback_data="checkout"))
        bottom_buttons.append(InlineKeyboardButton("◀️ Назад", callback_data="back_to_start"))
        keyboard.append(bottom_buttons)

        # Добавляем текущий заказ к сообщению
        if user_orders[user_id].items:
            message_text += "\n" + format_order_summary(user_orders[user_id])

        reply_markup = InlineKeyboardMarkup(keyboard)
        
        if query:
            await query.message.edit_text(message_text, reply_markup=reply_markup, parse_mode='Markdown')
        else:
            await message.reply_text(message_text, reply_markup=reply_markup, parse_mode='Markdown')
        return MENU

    except Exception as e:
        logger.error(f"Error in show_menu: {str(e)}")
        await message.reply_text('Произошла ошибка. Пожалуйста, попробуйте позже.')
        return ConversationHandler.END

async def select_quantity(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка выбора количества порций"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    if user_id not in user_orders:
        user_orders[user_id] = OrderData()

    if query.data.startswith(('inc_', 'dec_', 'select_')):
        action, dish_id = query.data.split('_')
        dish_id = int(dish_id)
        
        # Получаем информацию о блюде из кэша
        menu_data = get_cached_menu()
        dish = next((item for item in menu_data if item['id'] == dish_id), None)
        
        if not dish:
            await query.edit_message_text("Ошибка: блюдо не найдено")
            return MENU

        # Обработка действий с количеством
        if action == 'select':
            # Добавляем блюдо в заказ с количеством 1
            user_orders[user_id].items[dish_id] = {
                'quantity': 1,
                'name': dish['name'],
                'price': dish['price']
            }
        elif action == 'inc':
            # Увеличиваем количество на 1
            if dish_id in user_orders[user_id].items:
                user_orders[user_id].items[dish_id]['quantity'] += 1
        elif action == 'dec':
            # Уменьшаем количество на 1 или удаляем, если станет 0
            if dish_id in user_orders[user_id].items:
                user_orders[user_id].items[dish_id]['quantity'] -= 1
                if user_orders[user_id].items[dish_id]['quantity'] <= 0:
                    del user_orders[user_id].items[dish_id]

        # Обновляем меню
        return await show_menu(update, context)

async def request_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Запрос номера телефона"""
    query = update.callback_query
    if query:
        await query.answer()
    
    user_id = update.effective_user.id
    if not user_orders[user_id].items:
        await update.effective_message.reply_text("Ваша корзина пуста. Добавьте блюда в заказ.")
        return await show_menu(update, context)

    # Создаем кнопку для отправки номера телефона
    keyboard = ReplyKeyboardMarkup([
        [KeyboardButton("📱 Поделиться номером телефона", request_contact=True)]
    ], resize_keyboard=True)

    # Показываем сводку заказа
    message = format_order_summary(user_orders[user_id])
    message += "\n\nДля оформления заказа нам нужен ваш номер телефона.\nЭто необходимо для связи с вами по заказу."
    
    if query:
        await query.message.reply_text(message, reply_markup=keyboard)
    else:
        await update.message.reply_text(message, reply_markup=keyboard)
    return PHONE

async def process_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка полученного номера телефона"""
    user_id = update.effective_user.id
    
    # Убираем клавиатуру с кнопкой телефона
    reply_markup = ReplyKeyboardRemove()
    
    if update.message.contact:
        phone = update.message.contact.phone_number
    else:
        phone = update.message.text
    
    # Сохраняем телефон в данных заказа
    if user_id not in user_orders:
        user_orders[user_id] = OrderData()
    user_orders[user_id].phone_number = phone

    # Отправляем сообщение о сохранении номера
    await update.message.reply_text(
        f"Спасибо! Номер телефона {phone} сохранен.",
        reply_markup=reply_markup
    )

    # Проверяем историю адресов асинхронно
    context.application.create_task(
        fetch_and_show_addresses(update, context, phone)
    )
    return ADDRESS

async def fetch_and_show_addresses(update, context, phone):
    """Асинхронная загрузка и отображение адресов"""
    try:
        response = requests.get(
            f'{API_BASE_URL}/user/addresses',
            params={'phone': phone},
            auth=(os.getenv('BOT_USERNAME'), os.getenv('BOT_PASSWORD'))
        )
        
        if response.status_code == 200:
            previous_addresses = response.json().get('addresses', [])
            if previous_addresses:
                # Сохраняем адреса в контексте для использования позже
                context.user_data['previous_addresses'] = previous_addresses
                
                # Создаем клавиатуру с предыдущими адресами
                keyboard = []
                for addr in previous_addresses:
                    keyboard.append([InlineKeyboardButton(f"📍 {addr}", callback_data=f"addr_{len(keyboard)}")])
                keyboard.append([InlineKeyboardButton("✏️ Ввести новый адрес", callback_data="new_address")])
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await update.message.reply_text(
                    "У вас есть предыдущие адреса доставки. Выберите один из них или введите новый:",
                    reply_markup=reply_markup
                )
                return

    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching previous addresses: {str(e)}")
    
    # Если нет предыдущих адресов или произошла ошибка, просим ввести адрес
    await request_address(update, context)

async def request_address(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Запрос адреса доставки"""
    query = update.callback_query
    
    if query:
        await query.answer()
        if query.data.startswith("addr_"):
            # Пользователь выбрал предыдущий адрес
            addr_index = int(query.data.split("_")[1])
            previous_addresses = context.user_data.get('previous_addresses', [])
            if 0 <= addr_index < len(previous_addresses):
                user_id = update.effective_user.id
                user_orders[user_id].delivery_address = previous_addresses[addr_index]
                # Переходим к подтверждению заказа
                await show_order_confirmation(update, context)
                return CONFIRM
            
        elif query.data == "new_address":
            # Пользователь хочет ввести новый адрес
            await query.message.reply_text(
                "Пожалуйста, введите адрес доставки:",
                reply_markup=ReplyKeyboardRemove()
            )
            return ADDRESS
    
    # Если это не ответ на кнопку или нет предыдущих адресов
    keyboard = ReplyKeyboardRemove()
    message = "Пожалуйста, введите адрес доставки:"
    
    if update.message:
        await update.message.reply_text(message, reply_markup=keyboard)
    else:
        await query.message.reply_text(message, reply_markup=keyboard)
    return ADDRESS

async def process_address(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка адреса доставки и оформление заказа"""
    user_id = update.effective_user.id
    
    # Если это текстовое сообщение с новым адресом
    if update.message and update.message.text:
        user_orders[user_id].delivery_address = update.message.text
        return await show_order_confirmation(update, context)
    
    return CONFIRM

async def show_order_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает подтверждение заказа"""
    user_id = update.effective_user.id
    order_data = user_orders[user_id]
    
    # Формируем сообщение с деталями заказа
    message = "📋 *Подтверждение заказа*\n\n"
    message += format_order_summary(order_data)
    message += f"\n\n📱 Телефон: {order_data.phone_number}"
    message += f"\n📍 Адрес доставки: {order_data.delivery_address}"
    
    # Создаем клавиатуру для подтверждения
    keyboard = [
        [InlineKeyboardButton("✅ Подтвердить заказ", callback_data="confirm_order")],
        [InlineKeyboardButton("❌ Отменить", callback_data="cancel_order")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Определяем, откуда пришел запрос (от сообщения или callback query)
    if update.message:
        await update.message.reply_text(message, reply_markup=reply_markup, parse_mode='Markdown')
    else:
        await update.callback_query.message.edit_text(message, reply_markup=reply_markup, parse_mode='Markdown')
    
    return CONFIRM

async def process_order_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка подтверждения заказа"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    user = update.effective_user
    
    if query.data == "cancel_order":
        await query.message.edit_text("❌ Заказ отменен")
        del user_orders[user_id]
        return ConversationHandler.END
    
    # Получаем имя пользователя
    user_orders[user_id].customer_name = user.username or user.first_name or "Клиент из Телеграм"
    
    # Формируем данные заказа
    order_data = {
        'customer_name': user_orders[user_id].customer_name,
        'phone_number': user_orders[user_id].phone_number,
        'delivery_address': user_orders[user_id].delivery_address,
        'items': [
            {'dish_id': dish_id, 'quantity': details['quantity']}
            for dish_id, details in user_orders[user_id].items.items()
        ]
    }

    try:
        # Отправляем заказ
        response = requests.post(
            f'{API_BASE_URL}/orders',
            auth=(os.getenv('BOT_USERNAME'), os.getenv('BOT_PASSWORD')),
            json=order_data
        )

        if response.status_code == 201:
            order_id = response.json()['order_id']
            message = (
                f"✅ Спасибо за заказ!\n"
                f"Номер вашего заказа: {order_id}\n\n"
                f"📞 Мы свяжемся с вами по номеру {order_data['phone_number']} для подтверждения.\n\n"
                f"🚚 Адрес доставки:\n{order_data['delivery_address']}\n\n"
                f"{format_order_summary(user_orders[user_id])}"
            )
            keyboard = [[InlineKeyboardButton("🔄 Вернуться в меню", callback_data="show_menu")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.message.edit_text(
                message,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
            
            # Отправляем уведомление в группу
            group_message = (
                f"✅✅✅ Новый заказ #{order_id}✅✅✅\n\n"
                f"👤 Клиент: {order_data['customer_name']}\n"
                f"📞 Телефон: {order_data['phone_number']}\n"
                f"🚚 Адрес доставки: {order_data['delivery_address']}\n\n"
                f"📋 Заказ:\n{format_order_summary(user_orders[user_id])}"
            )
            
            try:
                group_id = os.getenv('TELEGRAM_GROUP_ID')
                logger.info(f"Attempting to send message to group {group_id}")
                await context.bot.send_message(
                    chat_id=group_id,
                    text=group_message,
                    parse_mode='Markdown'
                )
                logger.info("Successfully sent message to group")
            except Exception as e:
                logger.error(f"Failed to send notification to group. Error type: {type(e).__name__}, Error details: {str(e)}")
        else:
            keyboard = [[InlineKeyboardButton("🔄 Вернуться в меню", callback_data="show_menu")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.message.edit_text(
                "Произошла ошибка при оформлении заказа. Пожалуйста, попробуйте позже.",
                reply_markup=reply_markup
            )
    except requests.exceptions.RequestException:
        keyboard = [[InlineKeyboardButton("🔄 Вернуться в меню", callback_data="show_menu")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.message.edit_text(
            "Сервис временно недоступен. Пожалуйста, попробуйте позже.",
            reply_markup=reply_markup
        )

    # Очищаем данные заказа
    del user_orders[user_id]
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отмена заказа"""
    user_id = update.effective_user.id
    if user_id in user_orders:
        del user_orders[user_id]
    
    # Создаем клавиатуру для возврата в меню
    keyboard = [[InlineKeyboardButton("🔄 Вернуться в меню", callback_data="show_menu")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    message = "❌ Заказ отменен. Вы можете начать новый заказ."
    
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.message.edit_text(
            message,
            reply_markup=reply_markup
        )
    else:
        await update.message.reply_text(
            message,
            reply_markup=reply_markup
        )
    
    return ConversationHandler.END

def format_order_summary(order_data: OrderData) -> str:
    """Форматирует сводку заказа"""
    total = 0
    message = "🛒 Ваш заказ:\n\n"
    
    if not order_data.items:
        return "Корзина пуста"
    
    for dish_id, details in order_data.items.items():
        subtotal = details['price'] * details['quantity']
        total += subtotal
        message += f"• {details['name']} - {details['quantity']} порц. = {subtotal}₽\n"
    
    message += f"\n💰 Итого: {total}₽"
    return message

def main():
    """Запуск бота"""
    load_dotenv()
    
    # Проверяем загрузку переменных окружения
    group_id = os.getenv('TELEGRAM_GROUP_ID')
    logger.info(f"Loaded TELEGRAM_GROUP_ID: {group_id}")
    
    application = Application.builder().token(os.getenv('TELEGRAM_BOT_TOKEN')).build()

    # Создаем обработчик разговора
    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler('start', start),
            CallbackQueryHandler(show_menu, pattern='^show_menu$')
        ],
        states={
            MENU: [
                CallbackQueryHandler(select_quantity, pattern='^select_'),
                CallbackQueryHandler(select_quantity, pattern='^inc_'),
                CallbackQueryHandler(select_quantity, pattern='^dec_'),
                CallbackQueryHandler(request_phone, pattern='^checkout$'),
                CallbackQueryHandler(show_menu, pattern='^show_menu$')
            ],
            PHONE: [
                MessageHandler(filters.CONTACT | filters.Regex(r'^\+7\d{10}$'), process_phone)
            ],
            ADDRESS: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, process_address),
                CallbackQueryHandler(request_address, pattern='^addr_'),
                CallbackQueryHandler(request_address, pattern='^new_address$'),
                CallbackQueryHandler(show_menu, pattern='^show_menu$')
            ],
            CONFIRM: [
                CallbackQueryHandler(process_order_confirmation, pattern='^confirm_order$'),
                CallbackQueryHandler(cancel, pattern='^cancel_order$'),
                CallbackQueryHandler(show_menu, pattern='^show_menu$')
            ]
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )

    # Добавляем обработчики
    application.add_handler(conv_handler)

    # Добавляем обработчик для логирования ID чата
    async def log_chat_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
        logger.info(f"Message received in chat ID: {update.effective_chat.id}")
        logger.info(f"Chat type: {update.effective_chat.type}")
        return

    application.add_handler(MessageHandler(filters.ALL, log_chat_id))

    # Добавляем обработчики callback-запросов для инлайн кнопок
    application.add_handler(CallbackQueryHandler(start, pattern="^back_to_start$"))
    application.add_handler(CallbackQueryHandler(help_command, pattern="^help$"))
    application.add_handler(CallbackQueryHandler(about_command, pattern="^about$"))

    # Запускаем бота
    application.run_polling()

if __name__ == '__main__':
    main()
