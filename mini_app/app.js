let tg = window.Telegram.WebApp;
tg.expand();

const API_BASE_URL = 'http://localhost:9966/api';
const BOT_USERNAME = 'your_bot_username';
const BOT_PASSWORD = 'your_bot_password';

let cart = {};

// Загрузка меню
async function loadMenu() {
    try {
        const response = await fetch(`${API_BASE_URL}/menu/today`, {
            headers: {
                'Authorization': 'Basic ' + btoa(`${BOT_USERNAME}:${BOT_PASSWORD}`)
            }
        });
        const data = await response.json();
        displayMenu(data.menu);
    } catch (error) {
        console.error('Ошибка при загрузке меню:', error);
    }
}

// Отображение меню
function displayMenu(menu) {
    const menuContainer = document.getElementById('menu-items');
    menuContainer.innerHTML = '';

    menu.forEach(item => {
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
        menuContainer.appendChild(menuItem);
    });
}

// Обновление количества товара
function updateQuantity(itemId, change) {
    cart[itemId] = (cart[itemId] || 0) + change;
    if (cart[itemId] < 0) cart[itemId] = 0;
    
    document.getElementById(`quantity-${itemId}`).textContent = cart[itemId];
    updateCart();
}

// Обновление корзины
function updateCart() {
    const cartContainer = document.getElementById('cart-items');
    cartContainer.innerHTML = '';
    let total = 0;

    Object.entries(cart).forEach(([itemId, quantity]) => {
        if (quantity > 0) {
            const menuItem = document.querySelector(`#menu-items div:nth-child(${parseInt(itemId)})`);
            const name = menuItem.querySelector('h3').textContent;
            const price = parseFloat(menuItem.querySelector('.menu-item-price').textContent);
            
            const cartItem = document.createElement('div');
            cartItem.className = 'cart-item';
            cartItem.innerHTML = `
                <span>${name} x ${quantity}</span>
                <span>${price * quantity} ₽</span>
            `;
            cartContainer.appendChild(cartItem);
            
            total += price * quantity;
        }
    });

    document.getElementById('total-amount').textContent = `${total} ₽`;
}

// Оформление заказа
document.getElementById('checkout-button').addEventListener('click', async () => {
    const orderItems = Object.entries(cart)
        .filter(([_, quantity]) => quantity > 0)
        .map(([itemId, quantity]) => ({
            dish_id: parseInt(itemId),
            quantity: quantity
        }));

    if (orderItems.length === 0) {
        alert('Добавьте товары в корзину');
        return;
    }

    // Отправляем данные в Telegram
    tg.MainButton.text = "Оформить заказ";
    tg.MainButton.show();
    
    tg.onEvent('mainButtonClicked', async () => {
        try {
            const response = await fetch(`${API_BASE_URL}/orders`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': 'Basic ' + btoa(`${BOT_USERNAME}:${BOT_PASSWORD}`)
                },
                body: JSON.stringify({
                    items: orderItems,
                    customer_name: tg.initDataUnsafe.user.first_name,
                    phone_number: '', // Будет заполнено в боте
                    delivery_address: '' // Будет заполнено в боте
                })
            });

            if (response.ok) {
                const orderData = await response.json();
                // Отправляем данные заказа обратно в бот
                tg.sendData(JSON.stringify({
                    action: 'order_created',
                    order_id: orderData.id
                }));
                tg.close();
            } else {
                throw new Error('Ошибка при создании заказа');
            }
        } catch (error) {
            console.error('Ошибка:', error);
            alert('Произошла ошибка при оформлении заказа');
        }
    });
});

// Загружаем меню при запуске
loadMenu();
