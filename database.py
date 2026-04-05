import sqlite3
import hashlib
import os
from datetime import datetime, timedelta
from PIL import Image

DB_PATH = 'swillgram.db'

def get_db():
    """Возвращает соединение с БД с row_factory=sqlite3.Row"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Инициализация базы данных: создание всех таблиц и добавление недостающих колонок"""
    conn = get_db()
    cursor = conn.cursor()

    # ----- Таблица users -----
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            phone TEXT UNIQUE NOT NULL,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            avatar TEXT,
            bio TEXT,
            birthday TEXT,
            last_seen DATETIME,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # ----- Таблица chats -----
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS chats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user1_id INTEGER NOT NULL,
            user2_id INTEGER NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user1_id, user2_id)
        )
    ''')

    # ----- Таблица messages -----
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER NOT NULL,
            sender_id INTEGER NOT NULL,
            content TEXT,
            file_type TEXT,
            file_path TEXT,
            file_name TEXT,
            file_size INTEGER,
            is_read BOOLEAN DEFAULT 0,
            is_deleted BOOLEAN DEFAULT 0,
            deleted_for_all BOOLEAN DEFAULT 0,
            edited_at DATETIME,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # ----- Таблица contacts -----
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS contacts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            contact_id INTEGER NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id, contact_id)
        )
    ''')

    # ----- Таблица contact_names (пользовательские имена контактов) -----
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS contact_names (
            user_id INTEGER NOT NULL,
            contact_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            PRIMARY KEY (user_id, contact_id)
        )
    ''')

    # ----- Таблица favorites (избранное / облачное хранилище) -----
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS favorites (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            file_type TEXT,
            file_path TEXT,
            file_name TEXT,
            note TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # ----- Таблица calls (звонки) -----
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS calls (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            caller_id INTEGER NOT NULL,
            receiver_id INTEGER NOT NULL,
            call_type TEXT,
            status TEXT,
            duration INTEGER DEFAULT 0,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # ----- Таблица user_sessions (сессии) -----
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            session_token TEXT UNIQUE NOT NULL,
            device TEXT,
            ip TEXT,
            location TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            last_active DATETIME
        )
    ''')

    # ----- Таблица stories -----
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS stories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            file_type TEXT,
            file_path TEXT,
            caption TEXT,
            music TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            expires_at DATETIME
        )
    ''')

    # ----- Таблица story_interactions (просмотры, лайки, ответы) -----
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS story_interactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            story_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            type TEXT,
            reply_text TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(story_id, user_id, type)
        )
    ''')

    # ----- Таблица story_privacy (настройки приватности историй) -----
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS story_privacy (
            story_id INTEGER PRIMARY KEY,
            privacy_type TEXT,
            FOREIGN KEY (story_id) REFERENCES stories(id) ON DELETE CASCADE
        )
    ''')

    # ----- Таблица story_allowed_users (выбранные пользователи для приватности) -----
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS story_allowed_users (
            story_id INTEGER,
            user_id INTEGER,
            PRIMARY KEY (story_id, user_id)
        )
    ''')

    # ----- Безопасное добавление недостающих колонок в таблицу users -----
    cursor.execute("PRAGMA table_info(users)")
    existing_columns = [col[1] for col in cursor.fetchall()]

    columns_to_add = {
        'privacy_last_seen': "TEXT DEFAULT 'everyone'",
        'privacy_photo': "TEXT DEFAULT 'everyone'",
        'privacy_forward': "TEXT DEFAULT 'everyone'",
        'privacy_calls': "TEXT DEFAULT 'everyone'",
        'privacy_messages': "TEXT DEFAULT 'everyone'",
        'theme': "TEXT DEFAULT 'light'",
        'font_size': "INTEGER DEFAULT 14",
        'bubble_radius': "INTEGER DEFAULT 18",
        'wallpaper': "TEXT DEFAULT ''",
        'email': "TEXT",
        'google_id': "TEXT",
        'yandex_id': "TEXT"
    }

    for col, col_type in columns_to_add.items():
        if col not in existing_columns:
            try:
                cursor.execute(f"ALTER TABLE users ADD COLUMN {col} {col_type}")
            except sqlite3.OperationalError:
                pass  # колонка уже существует

    conn.commit()
    conn.close()

# ---------------------- ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ----------------------
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def resize_and_crop_image(image_path, size=(500, 500)):
    """Обрезает и ресайзит изображение в квадрат"""
    img = Image.open(image_path)
    min_size = min(img.size)
    left = (img.size[0] - min_size) / 2
    top = (img.size[1] - min_size) / 2
    right = (img.size[0] + min_size) / 2
    bottom = (img.size[1] + min_size) / 2
    img = img.crop((left, top, right, bottom))
    img = img.resize(size, Image.Resampling.LANCZOS)
    img.save(image_path)

# ---------------------- ПОЛЬЗОВАТЕЛИ ----------------------
def create_user(phone, username, password, email=None):
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute(
            'INSERT INTO users (phone, username, password, last_seen, email) VALUES (?, ?, ?, ?, ?)',
            (phone, username, hash_password(password), datetime.now(), email)
        )
        conn.commit()
        user_id = cursor.lastrowid
        # Чат "Избранное" (сам с собой)
        cursor.execute('INSERT INTO chats (user1_id, user2_id) VALUES (?, ?)', (user_id, user_id))
        conn.commit()
        return user_id
    except:
        return None
    finally:
        conn.close()

def get_user_by_id(user_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,))
    user = cursor.fetchone()
    conn.close()
    return user

def get_user_by_username(username):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE username = ?', (username,))
    user = cursor.fetchone()
    conn.close()
    return user

def get_user_by_phone(phone):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE phone = ?', (phone,))
    user = cursor.fetchone()
    conn.close()
    return user

def get_user_by_email(email):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE email = ?', (email,))
    user = cursor.fetchone()
    conn.close()
    return user

def verify_user(phone, password):
    user = get_user_by_phone(phone)
    if user and user['password'] == hash_password(password):
        return user
    return None

def update_last_seen(user_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('UPDATE users SET last_seen = ? WHERE id = ?', (datetime.now(), user_id))
    conn.commit()
    conn.close()

def update_user_settings(user_id, **kwargs):
    conn = get_db()
    cursor = conn.cursor()
    for key, value in kwargs.items():
        if value is not None:
            cursor.execute(f'UPDATE users SET {key} = ? WHERE id = ?', (value, user_id))
    conn.commit()
    conn.close()

def delete_user(user_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM users WHERE id = ?', (user_id,))
    cursor.execute('DELETE FROM contacts WHERE user_id = ? OR contact_id = ?', (user_id, user_id))
    cursor.execute('DELETE FROM chats WHERE user1_id = ? OR user2_id = ?', (user_id, user_id))
    cursor.execute('DELETE FROM messages WHERE sender_id = ?', (user_id,))
    cursor.execute('DELETE FROM calls WHERE caller_id = ? OR receiver_id = ?', (user_id, user_id))
    cursor.execute('DELETE FROM favorites WHERE user_id = ?', (user_id,))
    cursor.execute('DELETE FROM user_sessions WHERE user_id = ?', (user_id,))
    conn.commit()
    conn.close()

# ---------------------- ЧАТЫ ----------------------
def get_or_create_chat(user1_id, user2_id):
    if user1_id == user2_id:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('SELECT id FROM chats WHERE user1_id = ? AND user2_id = ?', (user1_id, user1_id))
        chat = cursor.fetchone()
        conn.close()
        return chat['id'] if chat else None

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        'SELECT id FROM chats WHERE (user1_id = ? AND user2_id = ?) OR (user1_id = ? AND user2_id = ?)',
        (user1_id, user2_id, user2_id, user1_id)
    )
    chat = cursor.fetchone()
    if chat:
        conn.close()
        return chat['id']

    cursor.execute('INSERT INTO chats (user1_id, user2_id) VALUES (?, ?)', (user1_id, user2_id))
    conn.commit()
    chat_id = cursor.lastrowid
    conn.close()
    return chat_id

def get_user_chats(user_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT c.id as chat_id, 
               CASE WHEN c.user1_id = ? THEN c.user2_id ELSE c.user1_id END as other_user_id,
               CASE WHEN c.user1_id = c.user2_id THEN 'Избранное'
                    ELSE COALESCE(cn.name, u.username) END as username,
               u.avatar,
               u.phone,
               u.last_seen,
               m.content as last_message,
               m.file_type as last_file_type,
               m.created_at as last_message_time,
               (SELECT COUNT(*) FROM messages WHERE chat_id = c.id AND sender_id != ? AND is_read = 0 AND is_deleted = 0) as unread_count
        FROM chats c
        LEFT JOIN users u ON (CASE WHEN c.user1_id = ? THEN c.user2_id ELSE c.user1_id END) = u.id
        LEFT JOIN contact_names cn ON cn.user_id = ? AND cn.contact_id = u.id
        LEFT JOIN messages m ON m.id = (SELECT id FROM messages WHERE chat_id = c.id AND is_deleted = 0 ORDER BY created_at DESC LIMIT 1)
        WHERE (c.user1_id = ? OR c.user2_id = ?)
        ORDER BY CASE WHEN c.user1_id = c.user2_id THEN 0 ELSE 1 END, m.created_at DESC
    ''', (user_id, user_id, user_id, user_id, user_id, user_id))

    chats = cursor.fetchall()
    conn.close()
    result = []
    for chat in chats:
        result.append({
            'id': chat['chat_id'],
            'user_id': chat['other_user_id'],
            'username': chat['username'] if chat['username'] else 'Избранное',
            'avatar': chat['avatar'],
            'phone': chat['phone'],
            'last_seen': chat['last_seen'],
            'last_message': chat['last_message'],
            'last_file_type': chat['last_file_type'],
            'last_message_time': chat['last_message_time'],
            'unread_count': chat['unread_count']
        })
    return result

# ---------------------- СООБЩЕНИЯ ----------------------
def send_message(chat_id, sender_id, content, file_type=None, file_path=None, file_name=None, file_size=None):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO messages (chat_id, sender_id, content, file_type, file_path, file_name, file_size)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (chat_id, sender_id, content, file_type, file_path, file_name, file_size))
    conn.commit()
    message_id = cursor.lastrowid
    cursor.execute('''
        SELECT m.*, u.username, u.avatar 
        FROM messages m
        LEFT JOIN users u ON m.sender_id = u.id
        WHERE m.id = ?
    ''', (message_id,))
    message = cursor.fetchone()
    conn.close()
    return message

def get_messages(chat_id, user_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('UPDATE messages SET is_read = 1 WHERE chat_id = ? AND sender_id != ?', (chat_id, user_id))
    conn.commit()
    cursor.execute('''
        SELECT m.*, u.username, u.avatar 
        FROM messages m
        LEFT JOIN users u ON m.sender_id = u.id
        WHERE m.chat_id = ? AND m.is_deleted = 0
        ORDER BY m.created_at ASC
    ''', (chat_id,))
    messages = cursor.fetchall()
    conn.close()
    return messages

def edit_message(message_id, new_content):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('UPDATE messages SET content = ?, edited_at = ? WHERE id = ?',
                   (new_content, datetime.now(), message_id))
    conn.commit()
    conn.close()

def delete_message(message_id, user_id, delete_for_all=False):
    conn = get_db()
    cursor = conn.cursor()
    if delete_for_all:
        cursor.execute('UPDATE messages SET is_deleted = 1, deleted_for_all = 1 WHERE id = ?', (message_id,))
    else:
        cursor.execute('UPDATE messages SET is_deleted = 1 WHERE id = ?', (message_id,))
    conn.commit()
    conn.close()

def forward_message(message_id, to_chat_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM messages WHERE id = ?', (message_id,))
    msg = cursor.fetchone()
    if msg:
        cursor.execute('''
            INSERT INTO messages (chat_id, sender_id, content, file_type, file_path, file_name, file_size)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (to_chat_id, msg['sender_id'], msg['content'], msg['file_type'], msg['file_path'], msg['file_name'], msg['file_size']))
        conn.commit()
        new_id = cursor.lastrowid
        conn.close()
        return new_id
    conn.close()
    return None

# ---------------------- КОНТАКТЫ ----------------------
def get_contacts(user_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT u.*, cn.name as custom_name FROM contacts c
        JOIN users u ON c.contact_id = u.id
        LEFT JOIN contact_names cn ON cn.user_id = ? AND cn.contact_id = u.id
        WHERE c.user_id = ?
        ORDER BY COALESCE(cn.name, u.username)
    ''', (user_id, user_id))
    contacts = cursor.fetchall()
    conn.close()
    return contacts

def add_contact(user_id, contact_id):
    if user_id == contact_id:
        return False
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute('INSERT INTO contacts (user_id, contact_id) VALUES (?, ?)', (user_id, contact_id))
        conn.commit()
        return True
    except:
        return False
    finally:
        conn.close()

def rename_contact(user_id, contact_id, new_name):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('INSERT OR REPLACE INTO contact_names (user_id, contact_id, name) VALUES (?, ?, ?)',
                   (user_id, contact_id, new_name))
    conn.commit()
    conn.close()

def search_users(query, current_user_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT id, username, phone, avatar, bio, last_seen
        FROM users
        WHERE (username LIKE ? OR phone LIKE ?) AND id != ?
        LIMIT 20
    ''', (f'%{query}%', f'%{query}%', current_user_id))
    users = cursor.fetchall()
    conn.close()
    return users

# ---------------------- ИЗБРАННОЕ (FAVORITES) ----------------------
def add_to_favorites(user_id, file_type, file_path, file_name, note=None):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO favorites (user_id, file_type, file_path, file_name, note)
        VALUES (?, ?, ?, ?, ?)
    ''', (user_id, file_type, file_path, file_name, note))
    conn.commit()
    fav_id = cursor.lastrowid
    conn.close()
    return fav_id

def get_favorites(user_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM favorites WHERE user_id = ? ORDER BY created_at DESC', (user_id,))
    favorites = cursor.fetchall()
    conn.close()
    return favorites

# ---------------------- ЗВОНКИ ----------------------
def add_call(caller_id, receiver_id, call_type, status):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO calls (caller_id, receiver_id, call_type, status)
        VALUES (?, ?, ?, ?)
    ''', (caller_id, receiver_id, call_type, status))
    conn.commit()
    call_id = cursor.lastrowid
    conn.close()
    return call_id

def update_call_status(call_id, status, duration=0):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('UPDATE calls SET status = ?, duration = ? WHERE id = ?', (status, duration, call_id))
    conn.commit()
    conn.close()

def get_call_history(user_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT c.*,
               CASE WHEN c.caller_id = ? THEN u2.username ELSE u1.username END as contact_name,
               CASE WHEN c.caller_id = ? THEN u2.id ELSE u1.id END as contact_id,
               c.caller_id = ? as is_outgoing
        FROM calls c
        JOIN users u1 ON c.caller_id = u1.id
        JOIN users u2 ON c.receiver_id = u2.id
        WHERE c.caller_id = ? OR c.receiver_id = ?
        ORDER BY c.created_at DESC
        LIMIT 50
    ''', (user_id, user_id, user_id, user_id, user_id))
    calls = cursor.fetchall()
    conn.close()
    return calls

# ---------------------- СЕССИИ ----------------------
def add_session(user_id, session_token, device, ip):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO user_sessions (user_id, session_token, device, ip, last_active)
        VALUES (?, ?, ?, ?, ?)
    ''', (user_id, session_token, device, ip, datetime.now()))
    conn.commit()
    conn.close()

def get_user_sessions(user_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM user_sessions WHERE user_id = ? ORDER BY created_at DESC', (user_id,))
    sessions = cursor.fetchall()
    conn.close()
    return sessions

def delete_session(session_token):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM user_sessions WHERE session_token = ?', (session_token,))
    conn.commit()
    conn.close()

def delete_all_sessions_except(user_id, current_token):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM user_sessions WHERE user_id = ? AND session_token != ?', (user_id, current_token))
    conn.commit()
    conn.close()

# ---------------------- ИСТОРИИ ----------------------
def create_story(user_id, file_type, file_path, caption, music_path, privacy, selected_users=None):
    expires_at = datetime.now() + timedelta(hours=24)
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO stories (user_id, file_type, file_path, caption, music, expires_at)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (user_id, file_type, file_path, caption, music_path, expires_at))
    story_id = cursor.lastrowid
    cursor.execute('INSERT INTO story_privacy (story_id, privacy_type) VALUES (?, ?)', (story_id, privacy))
    if privacy == 'selected' and selected_users:
        for uid in selected_users:
            cursor.execute('INSERT INTO story_allowed_users (story_id, user_id) VALUES (?, ?)', (story_id, uid))
    conn.commit()
    conn.close()
    return story_id

def get_stories_for_user(viewer_id):
    """Возвращает истории, которые имеет право видеть viewer_id"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT s.*, u.username, u.avatar,
               (SELECT COUNT(*) FROM story_interactions WHERE story_id = s.id AND type='like') as likes_count
        FROM stories s
        JOIN users u ON s.user_id = u.id
        WHERE s.expires_at > datetime('now')
          AND (
              s.user_id = ?
              OR EXISTS (
                  SELECT 1 FROM story_privacy sp
                  WHERE sp.story_id = s.id AND (
                      sp.privacy_type = 'everyone'
                      OR (sp.privacy_type = 'contacts' AND EXISTS (
                          SELECT 1 FROM contacts WHERE (user_id = ? AND contact_id = s.user_id) OR (user_id = s.user_id AND contact_id = ?)
                      ))
                      OR (sp.privacy_type = 'selected' AND EXISTS (
                          SELECT 1 FROM story_allowed_users WHERE story_id = s.id AND user_id = ?
                      ))
                  )
              )
          )
        ORDER BY s.created_at DESC
    ''', (viewer_id, viewer_id, viewer_id, viewer_id))
    stories = cursor.fetchall()
    conn.close()
    return stories

def add_story_interaction(story_id, user_id, interaction_type, reply_text=None):
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT INTO story_interactions (story_id, user_id, type, reply_text)
            VALUES (?, ?, ?, ?)
        ''', (story_id, user_id, interaction_type, reply_text))
        conn.commit()
    except sqlite3.IntegrityError:
        pass  # уже существует
    finally:
        conn.close()

def get_story_likes_count(story_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM story_interactions WHERE story_id = ? AND type="like"', (story_id,))
    count = cursor.fetchone()[0]
    conn.close()
    return count

# ---------------------- НАСТРОЙКИ ----------------------
def get_user_settings(user_id):
    user = get_user_by_id(user_id)
    if not user:
        return None
    return {
        'theme': user['theme'],
        'font_size': user['font_size'],
        'bubble_radius': user['bubble_radius'],
        'wallpaper': user['wallpaper']
    }

def get_privacy_settings(user_id):
    user = get_user_by_id(user_id)
    if not user:
        return None
    return {
        'last_seen': user['privacy_last_seen'],
        'profile_photo': user['privacy_photo'],
        'forward_messages': user['privacy_forward'],
        'calls': user['privacy_calls'],
        'messages': user['privacy_messages']
    }

def update_privacy_settings(user_id, last_seen, profile_photo, forward_messages, calls, messages):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE users SET
            privacy_last_seen = ?,
            privacy_photo = ?,
            privacy_forward = ?,
            privacy_calls = ?,
            privacy_messages = ?
        WHERE id = ?
    ''', (last_seen, profile_photo, forward_messages, calls, messages, user_id))
    conn.commit()
    conn.close()

# ---------------------- ВСПОМОГАТЕЛЬНЫЕ ----------------------
def get_all_users():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT id, phone, username, avatar, bio, last_seen, created_at FROM users ORDER BY id')
    users = cursor.fetchall()
    conn.close()
    return users