# Telegram Mini App для доставки еды

Это веб-приложение представляет собой Telegram Mini App для сервиса доставки еды. Приложение интегрируется с существующим ботом и веб-системой для обработки заказов.

## Структура проекта

```
meumir/
├── bot/
│   ├── bot.py              # Основной бот
│   └── mini_app_bot.py     # Бот с поддержкой Mini App
├── mini_app/
│   ├── index.html          # Главная страница Mini App
│   ├── styles.css          # Стили
│   └── app.js             # JavaScript логика
├── requirements.txt        # Зависимости Python
└── README.md              # Документация
```

## Установка

1. Клонируйте репозиторий:
```bash
git clone https://github.com/your-username/meumir.git
cd meumir
```

2. Установите зависимости Python:
```bash
pip install -r requirements.txt
```

3. Создайте файл .env в корневой директории и добавьте необходимые переменные окружения:
```
TELEGRAM_BOT_TOKEN=your_bot_token
BOT_USERNAME=your_bot_username
BOT_PASSWORD=your_bot_password
FLASK_SECRET_KEY=your_secret_key
```

4. Разместите файлы из папки mini_app на вашем веб-сервере

5. Обновите конфигурацию в файлах:
   - В `mini_app/app.js` укажите правильный `API_BASE_URL`
   - В `bot/mini_app_bot.py` укажите URL вашего веб-приложения

## Запуск

1. Запустите бота:
```bash
python bot/mini_app_bot.py
```

2. Откройте бота в Telegram и нажмите кнопку "Открыть меню"

## Функционал

- Просмотр меню на текущий день
- Добавление блюд в корзину
- Оформление заказа
- Интеграция с существующей системой доставки

## Технологии

- Python (Telegram Bot API, Flask)
- JavaScript (Telegram Web App API)
- HTML/CSS
- SQLite

## Лицензия

MIT
