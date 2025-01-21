from app2 import db
from sqlalchemy import text

def upgrade():
    # Добавляем колонку description в таблицу dish
    db.session.execute(text('ALTER TABLE dish ADD COLUMN description TEXT'))
    db.session.commit()

def downgrade():
    # Удаляем колонку description из таблицы dish
    db.session.execute(text('ALTER TABLE dish DROP COLUMN description'))
    db.session.commit()
