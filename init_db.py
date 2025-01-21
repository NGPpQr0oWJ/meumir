from app import db, Category, app

def init_db():
    with app.app_context():
        # Создаем все таблицы
        db.drop_all()
        db.create_all()
        
        # Добавляем начальные категории
        categories = [
            {'name': 'Первые блюда', 'code': 'first'},
            {'name': 'Вторые блюда', 'code': 'second'},
            {'name': 'Напитки', 'code': 'drinks'},
            {'name': 'Прочее', 'code': 'other'}
        ]
        
        for cat_data in categories:
            category = Category(name=cat_data['name'], code=cat_data['code'])
            db.session.add(category)
        
        db.session.commit()
        print("База данных успешно инициализирована")

if __name__ == '__main__':
    init_db()
