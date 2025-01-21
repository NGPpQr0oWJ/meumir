from app2 import db
from sqlalchemy import text

def upgrade():
    # Создаем временную таблицу
    db.session.execute(text('''
        CREATE TABLE weekly_menu_new (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            day_of_week INTEGER NOT NULL,
            dish_id INTEGER NOT NULL,
            position INTEGER NOT NULL DEFAULT 0,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(dish_id) REFERENCES dish(id)
        )
    '''))
    
    # Копируем данные
    db.session.execute(text('''
        INSERT INTO weekly_menu_new (id, day_of_week, dish_id)
        SELECT id, day_of_week, dish_id FROM weekly_menu
    '''))
    
    # Удаляем старую таблицу
    db.session.execute(text('DROP TABLE weekly_menu'))
    
    # Переименовываем новую таблицу
    db.session.execute(text('ALTER TABLE weekly_menu_new RENAME TO weekly_menu'))
    
    db.session.commit()

def downgrade():
    # Создаем временную таблицу без новых полей
    db.session.execute(text('''
        CREATE TABLE weekly_menu_old (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            day_of_week INTEGER NOT NULL,
            dish_id INTEGER NOT NULL,
            FOREIGN KEY(dish_id) REFERENCES dish(id)
        )
    '''))
    
    # Копируем данные
    db.session.execute(text('''
        INSERT INTO weekly_menu_old (id, day_of_week, dish_id)
        SELECT id, day_of_week, dish_id FROM weekly_menu
    '''))
    
    # Удаляем новую таблицу
    db.session.execute(text('DROP TABLE weekly_menu'))
    
    # Переименовываем старую таблицу
    db.session.execute(text('ALTER TABLE weekly_menu_old RENAME TO weekly_menu'))
    
    db.session.commit()
