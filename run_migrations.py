from app2 import app, db
import importlib.util
import os

def run_migrations():
    migrations_dir = 'migrations'
    
    # Получаем список всех файлов миграций
    migration_files = []
    for filename in os.listdir(migrations_dir):
        if filename.endswith('.py'):
            migration_files.append(filename)
    
    # Сортируем файлы по имени
    migration_files.sort()
    
    # Применяем каждую миграцию
    for filename in migration_files:
        print(f"Applying migration: {filename}")
        
        # Загружаем модуль миграции
        spec = importlib.util.spec_from_file_location(
            filename[:-3],
            os.path.join(migrations_dir, filename)
        )
        migration = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(migration)
        
        # Выполняем миграцию
        with app.app_context():
            migration.upgrade()
        
        print(f"Successfully applied migration: {filename}")

if __name__ == '__main__':
    run_migrations()
