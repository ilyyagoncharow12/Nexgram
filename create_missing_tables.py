import sqlite3
import os


def create_missing_tables():
    db_path = 'swillgram.db'

    # Проверяем существование базы данных
    if not os.path.exists(db_path):
        print(f"База данных {db_path} не найдена, будет создана новая")

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Создаем таблицу pinned_chats
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS pinned_chats (
            user_id INTEGER NOT NULL,
            chat_id INTEGER NOT NULL,
            pinned_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (user_id, chat_id)
        )
    ''')

    # Проверяем другие необходимые таблицы
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = cursor.fetchall()

    print("✅ Таблица pinned_chats создана/проверена!")
    print("\n📋 Существующие таблицы:")
    for table in tables:
        print(f"  - {table[0]}")

    conn.commit()
    conn.close()
    print("\n✅ Готово!")


if __name__ == '__main__':
    create_missing_tables()