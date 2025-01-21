let tg = window.Telegram.WebApp;
tg.expand();

// Конфигурация API
const config = {
    // В продакшене замените на ваш домен
    API_BASE_URL: 'https://your-api-domain.com/api',
    BOT_USERNAME: 'your_bot_username',
    BOT_PASSWORD: 'your_bot_password'
};

let cart = {};
let menuData = null;

// Инициализация приложения
async function initApp() {
    try {
        showSkeletonLoading();
        await loadMenu();
        setupEventListeners();
        setupMainButton();
    } catch (error) {
        showError('Ошибка при инициализации приложения');
        console.error('Init error:', error);
    } finally {
        hideSkeletonLoading();
    }
}

// Загрузка меню
async function loadMenu() {
    try {
        const response = await fetch(`${config.API_BASE_URL}/menu/today`, {
            headers: {
                'Authorization': 'Basic ' + btoa(`${config.BOT_USERNAME}:${config.BOT_PASSWORD}`)
            }
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        menuData = data.menu;
        displayMenu(menuData);
    } catch (error) {
        showError('Ошибка при загрузке меню');
        console.error('Menu loading error:', error);
    }
}

// Отображение меню
function displayMenu(menu) {
    const menuContainer = document.getElementById('menu-items');
    menuContainer.innerHTML = '';

    menu.forEach(item => {
        const menuItem = createMenuItem(item);
        menuContainer.appendChild(menuItem);
    });
}

// Создание элемента меню
function createMenuItem(item) {
    const menuItem = document.createElement('div');
    menuItem.className = 'menu-item';
    menuItem.innerHTML = `
        <h3>${item.name}</h3>
        <p>${item.description || ''}</p>
        <div class="menu-item-price">${item.selling_price} ₽</div>
        <div class="quantity-controls">
            <button class="quantity-button" onclick="updateQuantity(${item.id}, -1)">-</button>
            <span id="quantity-${item.id}">0</span>
            <button class="quantity-button" onclick="updateQuantity(${item.id}, 1)">+</button>
        </div>
    `;
    return menuItem;
}

// Обновление количества товара
function updateQuantity(itemId, change) {
    cart[itemId] = (cart[itemId] || 0) + change;
    if (cart[itemId] < 0) cart[itemId] = 0;
    
    document.getElementById(`quantity-${itemId}`).textContent = cart[itemId];
    updateCart();
    updateMainButton();
}

// Обновление корзины
function updateCart() {
    const cartContainer = document.getElementById('cart-items');
    cartContainer.innerHTML = '';
    let total = 0;

    Object.entries(cart).forEach(([itemId, quantity]) => {
        if (quantity > 0) {
            const item = menuData.find(i => i.id === parseInt(itemId));
            if (item) {
                const itemTotal = item.selling_price * quantity;
                total += itemTotal;
                
                const cartItem = document.createElement('div');
                cartItem.className = 'cart-item';
                cartItem.innerHTML = `
                    <span>${item.name} x ${quantity}</span>
                    <span>${itemTotal} ₽</span>
                `;
                cartContainer.appendChild(cartItem);
            }
        }
    });

    document.getElementById('total-amount').textContent = `${total} ₽`;
}

// Настройка главной кнопки Telegram
function setupMainButton() {
    tg.MainButton.setParams({
        text: 'Оформить заказ',
        color: '#31b545'
    });
    
    tg.MainButton.onClick(async () => {
        try {
            await submitOrder();
        } catch (error) {
            showError('Ошибка при оформлении заказа');
            console.error('Order submission error:', error);
        }
    });
    
    updateMainButton();
}

// Обновление состояния главной кнопки
function updateMainButton() {
    const hasItems = Object.values(cart).some(quantity => quantity > 0);
    if (hasItems) {
        tg.MainButton.show();
    } else {
        tg.MainButton.hide();
    }
}

// Отправка заказа
async function submitOrder() {
    const orderItems = Object.entries(cart)
        .filter(([_, quantity]) => quantity > 0)
        .map(([itemId, quantity]) => ({
            dish_id: parseInt(itemId),
            quantity: quantity
        }));

    if (orderItems.length === 0) {
        showError('Добавьте товары в корзину');
        return;
    }

    try {
        const response = await fetch(`${config.API_BASE_URL}/orders`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': 'Basic ' + btoa(`${config.BOT_USERNAME}:${config.BOT_PASSWORD}`)
            },
            body: JSON.stringify({
                items: orderItems,
                customer_name: tg.initDataUnsafe.user.first_name,
                phone_number: '', // Будет заполнено в боте
                delivery_address: '' // Будет заполнено в боте
            })
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const orderData = await response.json();
        // Отправляем данные заказа обратно в бот
        tg.sendData(JSON.stringify({
            action: 'order_created',
            order_id: orderData.id
        }));
        tg.close();
    } catch (error) {
        showError('Ошибка при создании заказа');
        console.error('Order creation error:', error);
    }
}

// Управление скелетной загрузкой
function showSkeletonLoading() {
    const menuContainer = document.getElementById('menu-items');
    menuContainer.innerHTML = '';
    
    for (let i = 0; i < 4; i++) {
        const skeleton = document.createElement('div');
        skeleton.className = 'menu-item skeleton';
        skeleton.innerHTML = `
            <div class="skeleton-title"></div>
            <div class="skeleton-description"></div>
            <div class="skeleton-price"></div>
            <div class="skeleton-controls"></div>
        `;
        menuContainer.appendChild(skeleton);
    }
}

function hideSkeletonLoading() {
    const skeletons = document.querySelectorAll('.skeleton');
    skeletons.forEach(skeleton => skeleton.remove());
}

// Отображение ошибок
function showError(message) {
    const errorDiv = document.createElement('div');
    errorDiv.className = 'error-message';
    errorDiv.textContent = message;
    document.body.appendChild(errorDiv);
    
    setTimeout(() => {
        errorDiv.remove();
    }, 3000);
}

// Настройка обработчиков событий
function setupEventListeners() {
    // Добавьте здесь дополнительные обработчики событий
    document.addEventListener('DOMContentLoaded', () => {
        tg.ready();
    });
}

// Запуск приложения
initApp();
