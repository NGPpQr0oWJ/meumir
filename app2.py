from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from forms import DishForm, WeeklyMenuForm, LoginForm
import logging
import sys
from decimal import Decimal
from flask_cors import CORS
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
import os
from dotenv import load_dotenv
from utils import get_server_time

# Загружаем переменные окружения
load_dotenv()

# Проверяем наличие необходимых переменных окружения
required_env_vars = ['BOT_USERNAME', 'BOT_PASSWORD', 'ADMIN_USERNAME', 'ADMIN_PASSWORD', 'FLASK_SECRET_KEY']
for var in required_env_vars:
    value = os.getenv(var)
    if not value:
        raise ValueError(f"Отсутствует обязательная переменная окружения: {var}")
    else:
        print(f"Загружена переменная окружения: {var}")

# Настройка логирования
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

app = Flask(__name__, static_folder='static', static_url_path='/static')
CORS(app, resources={
    r"/*": {
        "origins": ["http://127.0.0.1:9966", "https://api-maps.yandex.ru"],
        "methods": ["GET", "POST", "OPTIONS"],
        "allow_headers": ["Content-Type"]
    }
})

app.config['SECRET_KEY'] = os.getenv('FLASK_SECRET_KEY', 'default-secret-key')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///crm.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
app.debug = True  # Включаем отладочный режим

# Инициализация Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    return response

# Models
class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    code = db.Column(db.String(20), nullable=False, unique=True)
    dishes = db.relationship('Dish', backref='category', lazy=True)

class Dish(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    cost_price = db.Column(db.Float, nullable=False)
    selling_price = db.Column(db.Float, nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'), nullable=False)
    weekly_menus = db.relationship('WeeklyMenu', backref='dish', lazy=True)
    created_at = db.Column(db.DateTime, default=get_server_time)
    updated_at = db.Column(db.DateTime, default=get_server_time, onupdate=get_server_time)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'cost_price': float(self.cost_price),
            'selling_price': float(self.selling_price),
            'category_id': self.category_id
        }

class WeeklyMenu(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    day_of_week = db.Column(db.Integer, nullable=False)  # 0-6 (Понедельник-Воскресенье)
    dish_id = db.Column(db.Integer, db.ForeignKey('dish.id'), nullable=False)
    position = db.Column(db.Integer, nullable=False, default=0)  # Позиция блюда в дне
    created_at = db.Column(db.DateTime, default=get_server_time)

    def to_dict(self):
        return {
            'id': self.id,
            'day_of_week': self.day_of_week,
            'dish_id': self.dish_id,
            'position': self.position
        }

class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    customer_name = db.Column(db.String(100), nullable=False)
    phone_number = db.Column(db.String(20), nullable=False)
    delivery_address = db.Column(db.String(200), nullable=False)
    order_date = db.Column(db.DateTime, nullable=False, default=get_server_time)
    items = db.relationship('OrderItem', backref='order', lazy=True, cascade='all, delete-orphan')

    def to_dict(self):
        return {
            'id': self.id,
            'customer_name': self.customer_name,
            'phone_number': self.phone_number,
            'delivery_address': self.delivery_address,
            'order_date': self.order_date.strftime('%d.%m.%Y %H:%M'),
            'items': [item.to_dict() for item in self.items],
            'total': get_order_total(self)
        }

class OrderItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'), nullable=False)
    dish_id = db.Column(db.Integer, db.ForeignKey('dish.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    ordered_dish = db.relationship('Dish')

    @property
    def price(self):
        return self.ordered_dish.selling_price if self.ordered_dish else 0

    def to_dict(self):
        return {
            'id': self.id,
            'dish_id': self.dish_id,
            'dish_name': self.ordered_dish.name if self.ordered_dish else '',
            'quantity': self.quantity,
            'price': self.price,
            'subtotal': self.price * self.quantity
        }

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    form = LoginForm()
    if form.validate_on_submit():
        if form.username.data == os.getenv('ADMIN_USERNAME') and form.password.data == os.getenv('ADMIN_PASSWORD'):
            user = User.query.filter_by(username=form.username.data).first()
            if not user:
                user = User(username=form.username.data, password=form.password.data)
                db.session.add(user)
                db.session.commit()
            login_user(user)
            flash('Вы успешно вошли в систему!', 'success')
            return redirect(url_for('index'))
        flash('Неправильное имя пользователя или пароль', 'error')
    return render_template('login.html', form=form)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/')
@login_required
def index():
    return redirect(url_for('dishes'))

@app.route('/dishes')
@login_required
def dishes():
    dishes = Dish.query.all()
    return render_template('dishes.html', dishes=dishes)

@app.route('/dishes/add', methods=['GET', 'POST'])
@login_required
def add_dish():
    form = DishForm()
    
    # Получаем список категорий из базы данных
    categories = Category.query.all()
    form.category.choices = [(str(cat.id), cat.name) for cat in categories]
    
    if form.validate_on_submit():
        try:
            dish = Dish(
                name=form.name.data,
                description=form.description.data,
                category_id=int(form.category.data),
                cost_price=form.cost_price.data,
                selling_price=form.selling_price.data
            )
            db.session.add(dish)
            db.session.commit()
            flash('Блюдо успешно добавлено', 'success')
            return redirect(url_for('dishes'))
        except Exception as e:
            db.session.rollback()
            flash(f'Ошибка при добавлении блюда: {str(e)}', 'error')
            return render_template('_dish_form.html', form=form, action=url_for('add_dish'))
    
    if form.errors:
        return render_template('_dish_form.html', form=form, action=url_for('add_dish'))
    
    return render_template('_dish_form.html', form=form, action=url_for('add_dish'))

@app.route('/dishes/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_dish(id):
    dish = Dish.query.get_or_404(id)
    form = DishForm()
    
    # Получаем список категорий из базы данных
    categories = Category.query.all()
    form.category.choices = [(str(cat.id), cat.name) for cat in categories]
    
    if form.validate_on_submit():
        try:
            dish.name = form.name.data
            dish.description = form.description.data
            dish.category_id = int(form.category.data)
            dish.cost_price = form.cost_price.data
            dish.selling_price = form.selling_price.data
            dish.updated_at = get_server_time()
            
            db.session.commit()
            flash('Блюдо успешно обновлено', 'success')
            return redirect(url_for('dishes'))
        except Exception as e:
            db.session.rollback()
            flash(f'Ошибка при обновлении блюда: {str(e)}', 'error')
            return render_template('_dish_form.html', form=form, action=url_for('edit_dish', id=id))
    
    if form.errors:
        return render_template('_dish_form.html', form=form, action=url_for('edit_dish', id=id))
    
    # Заполняем форму текущими данными
    form.name.data = dish.name
    form.description.data = dish.description
    form.category.data = str(dish.category_id)
    form.cost_price.data = dish.cost_price
    form.selling_price.data = dish.selling_price
    
    return render_template('_dish_form.html', form=form, action=url_for('edit_dish', id=id))

@app.route('/dishes/delete/<int:id>', methods=['POST'])
@login_required
def delete_dish(id):
    dish = Dish.query.get_or_404(id)
    
    # Проверяем, используется ли блюдо в меню
    if dish.weekly_menus:
        flash('Невозможно удалить блюдо, так как оно используется в меню. Сначала удалите его из меню.', 'error')
        return redirect(url_for('dishes'))
    
    # Проверяем, используется ли блюдо в заказах
    order_items = OrderItem.query.filter_by(dish_id=id).first()
    if order_items:
        flash('Невозможно удалить блюдо, так как оно используется в заказах.', 'error')
        return redirect(url_for('dishes'))
    
    try:
        db.session.delete(dish)
        db.session.commit()
        flash('Блюдо успешно удалено', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Ошибка при удалении блюда: {str(e)}', 'error')
    
    return redirect(url_for('dishes'))

@app.route('/menu')
@login_required
def menu():
    # Получаем все блюда для формы
    dishes = Dish.query.all()
    form = WeeklyMenuForm()
    form.dish.choices = [(str(dish.id), dish.name) for dish in dishes]

    # Получаем текущее меню на неделю и группируем по дням
    menu_items = WeeklyMenu.query.order_by(WeeklyMenu.position).all()
    menu_dict = {}
    for item in menu_items:
        if item.day_of_week not in menu_dict:
            menu_dict[item.day_of_week] = []
        menu_dict[item.day_of_week].append(item)

    # Подсчитываем уникальные блюда
    unique_dishes = set(item.dish_id for item in menu_items)
    unique_dishes_count = len(unique_dishes)

    # Подсчитываем общее количество блюд
    total_dishes = len(menu_items)

    return render_template('menu/index.html', 
                         menu_items=menu_dict,
                         unique_dishes_count=unique_dishes_count,
                         total_dishes=total_dishes,
                         form=form)

@app.route('/menu/add', methods=['POST'])
def add_menu_item():
    form = WeeklyMenuForm()
    dishes = Dish.query.all()
    form.dish.choices = [(str(dish.id), dish.name) for dish in dishes]

    if form.validate_on_submit():
        # Получаем максимальную позицию для этого дня
        max_position = db.session.query(db.func.max(WeeklyMenu.position)).filter_by(
            day_of_week=int(form.day_of_week.data)
        ).scalar() or -1

        menu_item = WeeklyMenu(
            day_of_week=int(form.day_of_week.data),
            dish_id=int(form.dish.data),
            position=max_position + 1
        )
        db.session.add(menu_item)
        db.session.commit()
        flash('Блюдо добавлено в меню', 'success')
        return redirect(url_for('menu'))

    flash('Ошибка при обновлении меню', 'error')
    return redirect(url_for('menu'))

@app.route('/menu/reorder', methods=['POST'])
def reorder_menu_items():
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400

    try:
        for day_num, items in data.items():
            for position, item_id in enumerate(items):
                menu_item = WeeklyMenu.query.get(item_id)
                if menu_item:
                    menu_item.day_of_week = int(day_num)
                    menu_item.position = position
        
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/menu/<int:id>/edit', methods=['POST'])
def edit_menu_item(id):
    menu_item = WeeklyMenu.query.get_or_404(id)
    form = WeeklyMenuForm()
    dishes = Dish.query.all()
    form.dish.choices = [(str(dish.id), dish.name) for dish in dishes]

    if form.validate_on_submit():
        # Если день недели изменился, проверяем конфликты
        new_day = int(form.day_of_week.data)
        if new_day != menu_item.day_of_week:
            existing_item = WeeklyMenu.query.filter_by(day_of_week=new_day).first()
            if existing_item and existing_item.id != id:
                db.session.delete(existing_item)

        menu_item.day_of_week = new_day
        menu_item.dish_id = int(form.dish.data)
        db.session.commit()
        flash('Меню успешно обновлено', 'success')
        return redirect(url_for('menu'))

    flash('Ошибка при обновлении меню', 'error')
    return redirect(url_for('menu'))

@app.route('/menu/<int:id>/delete', methods=['POST'])
def delete_menu_item(id):
    menu_item = WeeklyMenu.query.get_or_404(id)
    db.session.delete(menu_item)
    db.session.commit()
    flash('Блюдо удалено из меню', 'success')
    return redirect(url_for('menu'))

# Маршруты для заказов
@app.route('/orders')
@login_required
def orders():
    orders = Order.query.order_by(Order.order_date.desc()).all()
    # Получаем текущий день недели (0 = понедельник, 6 = воскресенье)
    current_day = datetime.now().weekday()
    
    # Получаем только блюда из текущего меню
    menu_items = WeeklyMenu.query.filter_by(day_of_week=current_day).all()
    dishes = [menu_item.dish for menu_item in menu_items]
    
    return render_template('orders/index.html', orders=orders, dishes=dishes)

@app.route('/orders/add', methods=['POST'])
def add_order():
    try:
        data = request.get_json()
        print("Получены данные заказа:", data)

        if not data or 'items' not in data:
            print("Ошибка: нет данных или позиций в заказе")
            return jsonify({'success': False, 'error': 'Неверные данные заказа'})

        if not data['items']:
            print("Ошибка: нет позиций в заказе")
            return jsonify({'success': False, 'error': 'Добавьте хотя бы одно блюдо в заказ'})

        # Получаем текущий день недели (0 = понедельник, 6 = воскресенье)
        current_day = datetime.now().weekday()

        # Создаем заказ
        order = Order(
            customer_name=data['customer_name'],
            phone_number=data['phone_number'],
            delivery_address=data['delivery_address']
        )
        db.session.add(order)
        db.session.flush()  # Получаем ID заказа

        print(f"Создан заказ ID {order.id}")

        # Добавляем позиции заказа
        for item in data['items']:
            dish = Dish.query.get(item['dish_id'])
            if not dish:
                print(f"Ошибка: блюдо с ID {item['dish_id']} не найдено")
                continue

            # Проверяем, есть ли блюдо в меню текущего дня
            menu_item = WeeklyMenu.query.filter_by(
                dish_id=dish.id,
                day_of_week=current_day
            ).first()

            if not menu_item:
                print(f"Ошибка: блюдо {dish.name} не находится в меню на сегодня")
                return jsonify({
                    'success': False,
                    'error': f'Блюдо "{dish.name}" недоступно в меню на сегодня'
                })

            order_item = OrderItem(
                order_id=order.id,
                dish_id=dish.id,
                quantity=item['quantity']
            )
            db.session.add(order_item)
            print(f"Добавлена позиция: блюдо {dish.name}, количество {item['quantity']}")

        db.session.commit()
        print("Заказ успешно сохранен")
        return jsonify({'success': True})

    except Exception as e:
        db.session.rollback()
        print("Ошибка при сохранении заказа:", str(e))
        return jsonify({'success': False, 'error': str(e)})

@app.route('/orders/<int:id>')
def get_order(id):
    order = Order.query.get_or_404(id)
    return jsonify(order.to_dict())

@app.route('/orders/<int:id>', methods=['DELETE'])
def delete_order(id):
    try:
        order = Order.query.get_or_404(id)
        db.session.delete(order)
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)})

# API endpoints для телеграм-бота
@app.route('/api/auth', methods=['POST'])
def api_auth():
    auth = request.authorization
    logger.info(f"Auth attempt - Username: {auth.username if auth else 'None'}")
    logger.info(f"Expected username: {os.getenv('BOT_USERNAME')}")
    
    if not auth or not auth.username or not auth.password:
        logger.error("No authorization provided")
        return jsonify({'message': 'Необходима авторизация'}), 401
    
    if auth.username != os.getenv('BOT_USERNAME') or auth.password != os.getenv('BOT_PASSWORD'):
        logger.error(f"Invalid credentials. Got username: {auth.username}")
        return jsonify({'message': 'Неверные учетные данные'}), 401
    
    logger.info("Successful authentication")
    return jsonify({'message': 'Успешная авторизация'}), 200

@app.route('/api/menu/today', methods=['GET'])
def api_menu_today():
    auth = request.authorization
    if not auth or not auth.username or not auth.password:
        return jsonify({'message': 'Необходима авторизация'}), 401
    
    if auth.username != os.getenv('BOT_USERNAME') or auth.password != os.getenv('BOT_PASSWORD'):
        return jsonify({'message': 'Неверные учетные данные'}), 401

    # Получаем текущий день недели (0 = понедельник, 6 = воскресенье)
    current_day = datetime.now().weekday()
    
    # Получаем меню на текущий день
    menu_items = WeeklyMenu.query.filter_by(day_of_week=current_day).order_by(WeeklyMenu.position).all()
    
    # Формируем список блюд
    menu = []
    for item in menu_items:
        dish = Dish.query.get(item.dish_id)
        if dish:
            menu.append({
                'id': dish.id,
                'name': dish.name,
                'price': float(dish.selling_price),
                'description': dish.description,
                'category': dish.category.name if dish.category else None
            })
    
    return jsonify({'menu': menu})

@app.route('/api/orders', methods=['POST'])
def api_create_order():
    auth = request.authorization
    if not auth or not auth.username or not auth.password:
        return jsonify({'message': 'Необходима авторизация'}), 401
    
    if auth.username != os.getenv('BOT_USERNAME') or auth.password != os.getenv('BOT_PASSWORD'):
        return jsonify({'message': 'Неверные учетные данные'}), 401

    data = request.get_json()
    
    if not data or not all(key in data for key in ['customer_name', 'phone_number', 'delivery_address', 'items']):
        return jsonify({'message': 'Неполные данные заказа'}), 400
    
    try:
        # Создаем новый заказ
        order = Order(
            customer_name=data['customer_name'],
            phone_number=data['phone_number'],
            delivery_address=data['delivery_address']
        )
        db.session.add(order)
        
        # Добавляем позиции заказа
        for item in data['items']:
            if not all(key in item for key in ['dish_id', 'quantity']):
                return jsonify({'message': 'Неверный формат позиций заказа'}), 400
            
            dish = Dish.query.get(item['dish_id'])
            if not dish:
                return jsonify({'message': f'Блюдо с id {item["dish_id"]} не найдено'}), 404
            
            order_item = OrderItem(
                order=order,
                dish_id=item['dish_id'],
                quantity=item['quantity']
            )
            db.session.add(order_item)
        
        db.session.commit()
        return jsonify({
            'message': 'Заказ успешно создан',
            'order_id': order.id
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': f'Ошибка при создании заказа: {str(e)}'}), 500

@app.route('/api/user/addresses', methods=['GET'])
def api_user_addresses():
    """Получение списка предыдущих адресов доставки пользователя"""
    phone_number = request.args.get('phone')
    if not phone_number:
        return jsonify({'error': 'Phone number is required'}), 400

    # Получаем уникальные адреса доставки для номера телефона
    addresses = db.session.query(Order.delivery_address)\
        .filter(Order.phone_number == phone_number)\
        .distinct()\
        .order_by(Order.order_date.desc())\
        .limit(5)\
        .all()
    
    return jsonify({
        'addresses': [addr[0] for addr in addresses]
    })

# Маршруты для отчетов
@app.route('/reports')
@login_required
def reports():
    return render_template('reports.html')

@app.route('/reports/sales', methods=['GET'])
@login_required
def sales_report():
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    if start_date and end_date:
        start_date = datetime.strptime(start_date, '%Y-%m-%d')
        end_date = datetime.strptime(end_date, '%Y-%m-%d').replace(hour=23, minute=59, second=59)
        
        # Получаем все заказы за период
        orders = Order.query.filter(
            Order.order_date.between(start_date, end_date)
        ).order_by(Order.order_date.desc()).all()
        
        # Общие показатели
        total_revenue = sum(sum(item.quantity * item.ordered_dish.selling_price for item in order.items) for order in orders)
        total_cost = sum(sum(item.quantity * item.ordered_dish.cost_price for item in order.items) for order in orders)
        profit = total_revenue - total_cost
        profitability = (profit / total_cost * 100) if total_cost > 0 else 0
        
        # Создаем полный список дат за период
        from datetime import timedelta
        date_list = []
        current_date = start_date
        while current_date <= end_date:
            date_list.append(current_date.strftime('%Y-%m-%d'))
            current_date += timedelta(days=1)
        
        # Группируем данные по дням
        daily_stats = {date: {'revenue': 0, 'cost': 0, 'orders': 0} for date in date_list}
        
        for order in orders:
            day = order.order_date.strftime('%Y-%m-%d')
            daily_stats[day]['orders'] += 1
            for item in order.items:
                daily_stats[day]['revenue'] += item.quantity * item.ordered_dish.selling_price
                daily_stats[day]['cost'] += item.quantity * item.ordered_dish.cost_price
        
        # Преобразуем в список и сортируем по дате
        daily_data = [
            {
                'date': day,
                'revenue': float(stats['revenue']),
                'cost': float(stats['cost']),
                'profit': float(stats['revenue'] - stats['cost']),
                'orders': stats['orders'],
                'profitability': float((stats['revenue'] - stats['cost']) / stats['cost'] * 100) if stats['cost'] > 0 else 0
            }
            for day, stats in daily_stats.items()
        ]
        daily_data.sort(key=lambda x: x['date'])
        
        return jsonify({
            'orders_count': len(orders),
            'total_revenue': format_price(total_revenue),
            'total_cost': format_price(total_cost),
            'profit': format_price(profit),
            'profitability': round(profitability, 2),
            'daily_data': daily_data
        })
    
    return jsonify({'error': 'Укажите даты для отчета'})

@app.route('/reports/popular-dishes', methods=['GET'])
@login_required
def popular_dishes_report():
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    if start_date and end_date:
        start_date = datetime.strptime(start_date, '%Y-%m-%d')
        end_date = datetime.strptime(end_date, '%Y-%m-%d').replace(hour=23, minute=59, second=59)
        
        # Подзапрос для подсчета количества заказов каждого блюда
        dish_orders = db.session.query(
            OrderItem.dish_id,
            Dish.name,
            Dish.selling_price,
            Dish.cost_price,
            db.func.sum(OrderItem.quantity).label('total_quantity'),
            db.func.sum(OrderItem.quantity * Dish.selling_price).label('total_revenue'),
            db.func.sum(OrderItem.quantity * Dish.cost_price).label('total_cost')
        ).join(Order).join(Dish).filter(
            Order.order_date.between(start_date, end_date)
        ).group_by(
            OrderItem.dish_id,
            Dish.name,
            Dish.selling_price,
            Dish.cost_price
        ).order_by(db.text('total_quantity DESC')).all()
        
        return jsonify({
            'dishes': [{
                'name': dish.name,
                'quantity': dish.total_quantity,
                'revenue': format_price(dish.total_revenue),
                'cost': format_price(dish.total_cost),
                'profit': format_price(dish.total_revenue - dish.total_cost),
                'profitability': round(((dish.total_revenue - dish.total_cost) / dish.total_cost * 100) if dish.total_cost > 0 else 0, 2)
            } for dish in dish_orders]
        })
    
    return jsonify({'error': 'Укажите даты для отчета'})

@app.route('/reports/categories', methods=['GET'])
@login_required
def categories_report():
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    if start_date and end_date:
        start_date = datetime.strptime(start_date, '%Y-%m-%d')
        end_date = datetime.strptime(end_date, '%Y-%m-%d').replace(hour=23, minute=59, second=59)
        
        # Подзапрос для подсчета выручки по категориям
        category_sales = db.session.query(
            Category.name,
            db.func.sum(OrderItem.quantity).label('total_quantity'),
            db.func.sum(OrderItem.quantity * Dish.selling_price).label('total_revenue'),
            db.func.sum(OrderItem.quantity * Dish.cost_price).label('total_cost')
        ).join(Dish, Category.id == Dish.category_id
        ).join(OrderItem, Dish.id == OrderItem.dish_id
        ).join(Order, OrderItem.order_id == Order.id
        ).filter(Order.order_date.between(start_date, end_date)
        ).group_by(Category.name
        ).order_by(db.text('total_revenue DESC')).all()
        
        return jsonify({
            'categories': [{
                'name': cat.name,
                'quantity': cat.total_quantity,
                'revenue': format_price(cat.total_revenue),
                'cost': format_price(cat.total_cost),
                'profit': format_price(cat.total_revenue - cat.total_cost),
                'profitability': round(((cat.total_revenue - cat.total_cost) / cat.total_cost * 100) if cat.total_cost > 0 else 0, 2)
            } for cat in category_sales]
        })
    
    return jsonify({'error': 'Укажите даты для отчета'})

def restart_bot():
    try:
        # Получаем путь к директории бота
        current_dir = os.path.dirname(os.path.abspath(__file__))
        bot_path = os.path.join(current_dir, 'bot', 'bot.py')
        
        # Запускаем бота в новом окне
        os.system(f'start cmd /c "python {bot_path}"')
        logger.info("Bot restart initiated")
    except Exception as e:
        logger.error(f"Error restarting bot: {str(e)}")

@app.route('/menu/update', methods=['POST'])
@login_required
def update_menu():
    try:
        # Получаем данные из формы
        day = int(request.form.get('day'))
        selected_dishes = request.form.getlist('dishes[]')
        
        # Удаляем старые записи для этого дня
        WeeklyMenu.query.filter_by(day_of_week=day).delete()
        
        # Добавляем новые записи
        for dish_id in selected_dishes:
            menu_item = WeeklyMenu(day_of_week=day, dish_id=int(dish_id))
            db.session.add(menu_item)
        
        db.session.commit()
        flash('Меню успешно обновлено', 'success')
        
        # Перезапускаем бота
        restart_bot()
        
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)})

# Вспомогательные функции
def get_order_total(order):
    return sum(item.price * item.quantity for item in order.items)

def format_price(value):
    return "{:.2f}".format(float(value))

@app.context_processor
def utility_processor():
    return {
        'get_order_total': get_order_total,
        'format_price': format_price
    }

if __name__ == '__main__':
    with app.app_context():
        # Создаем базу данных и начальные категории
        db.create_all()
        
        # Добавляем категории, если их нет
        categories = [
            {'name': 'Первые блюда', 'code': 'first'},
            {'name': 'Вторые блюда', 'code': 'second'},
            {'name': 'Напитки', 'code': 'drinks'},
            {'name': 'Прочее', 'code': 'other'}
        ]
        
        for cat_data in categories:
            category = Category.query.filter_by(code=cat_data['code']).first()
            if not category:
                category = Category(name=cat_data['name'], code=cat_data['code'])
                db.session.add(category)
        
        db.session.commit()
    
    app.run(host='0.0.0.0', port=9966)
