import os
import sys
import uuid
import re
import sqlite3
import hashlib
from datetime import datetime, timedelta
from flask import Flask, render_template, request, redirect, url_for, session, jsonify, send_file
from flask_socketio import SocketIO, emit, join_room, leave_room
from werkzeug.utils import secure_filename
from PIL import Image

# В самом начале main.py, после всех импортов
import sqlite3
import os

# Принудительно создаем таблицу pinned_chats ДО всего остального
def ensure_pinned_chats_table():
    """Гарантированно создает таблицу pinned_chats"""
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS pinned_chats (
                user_id INTEGER NOT NULL,
                chat_id INTEGER NOT NULL,
                pinned_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (user_id, chat_id)
            )
        ''')
        conn.commit()
        conn.close()
        print("✅ Таблица pinned_chats проверена/создана")
    except Exception as e:
        print(f"⚠️ Ошибка при создании pinned_chats: {e}")

# Вызываем сразу после определения DATABASE_PATH
DATABASE_PATH = 'swillgram.db'
ensure_pinned_chats_table()

# Затем инициализируем остальную БД


from database import (
    get_db, init_db, hash_password, resize_and_crop_image,
    create_user, get_user_by_id, get_user_by_username, get_user_by_phone,
    verify_user, update_last_seen, update_user_settings,
    get_or_create_chat, get_user_chats, send_message, get_messages,
    edit_message, delete_message, forward_message,
    get_contacts, add_contact, rename_contact, search_users,
    add_to_favorites, get_favorites,
    add_call, update_call_status, get_call_history,
    add_session, get_user_sessions, delete_session, delete_all_sessions_except,
    create_story, get_stories_for_user, add_story_interaction,
    get_story_likes_count, get_story_viewers, can_user_interact,
    get_user_settings, get_privacy_settings,
    pin_chat, unpin_chat, get_pinned_chats  # <- эти функции должны быть в database.py
)



app = Flask(__name__)
app.config['SECRET_KEY'] = 'swillgram-secret-key'
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=30)

socketio = SocketIO(app, cors_allowed_origins="*")

# Создаем папки
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(os.path.join(app.config['UPLOAD_FOLDER'], 'avatars'), exist_ok=True)
os.makedirs(os.path.join(app.config['UPLOAD_FOLDER'], 'files'), exist_ok=True)
os.makedirs(os.path.join(app.config['UPLOAD_FOLDER'], 'photos'), exist_ok=True)
os.makedirs(os.path.join(app.config['UPLOAD_FOLDER'], 'videos'), exist_ok=True)
os.makedirs(os.path.join(app.config['UPLOAD_FOLDER'], 'audio'), exist_ok=True)
os.makedirs(os.path.join(app.config['UPLOAD_FOLDER'], 'wallpapers'), exist_ok=True)
os.makedirs(os.path.join(app.config['UPLOAD_FOLDER'], 'stories'), exist_ok=True)
os.makedirs(os.path.join(app.config['UPLOAD_FOLDER'], 'story_music'), exist_ok=True)

DATABASE_PATH = 'swillgram.db'


def get_db():
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    cursor = conn.cursor()

    # Users table
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

    # Chats table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS chats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user1_id INTEGER NOT NULL,
            user2_id INTEGER NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user1_id, user2_id)
        )
    ''')

    # Messages table
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

    # Contacts table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS contacts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            contact_id INTEGER NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id, contact_id)
        )
    ''')

    # Contact names table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS contact_names (
            user_id INTEGER NOT NULL,
            contact_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            PRIMARY KEY (user_id, contact_id)
        )
    ''')

    # Favorites table
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

    # Calls table
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

    # User sessions table
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

    # Stories table
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

    # Story interactions table
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

    # Story privacy table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS story_privacy (
            story_id INTEGER PRIMARY KEY,
            privacy_type TEXT,
            FOREIGN KEY (story_id) REFERENCES stories(id) ON DELETE CASCADE
        )
    ''')

    # Story allowed users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS story_allowed_users (
            story_id INTEGER,
            user_id INTEGER,
            PRIMARY KEY (story_id, user_id)
        )
    ''')

    # Add missing columns to users table
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
                pass

    conn.commit()
    conn.close()


init_db()


def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()


def resize_and_crop_image(image_path, size=(500, 500)):
    img = Image.open(image_path)
    min_size = min(img.size)
    left = (img.size[0] - min_size) / 2
    top = (img.size[1] - min_size) / 2
    right = (img.size[0] + min_size) / 2
    bottom = (img.size[1] + min_size) / 2
    img = img.crop((left, top, right, bottom))
    img = img.resize(size, Image.Resampling.LANCZOS)
    img.save(image_path)


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

    # Получаем закрепленные чаты
    pinned_ids = get_pinned_chats(user_id)
    pinned_ids_str = ','.join(map(str, pinned_ids)) if pinned_ids else '0'

    cursor.execute(f'''
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
               (SELECT COUNT(*) FROM messages WHERE chat_id = c.id AND sender_id != ? AND is_read = 0 AND is_deleted = 0) as unread_count,
               c.id IN ({pinned_ids_str}) as is_pinned
        FROM chats c
        LEFT JOIN users u ON (CASE WHEN c.user1_id = ? THEN c.user2_id ELSE c.user1_id END) = u.id
        LEFT JOIN contact_names cn ON cn.user_id = ? AND cn.contact_id = u.id
        LEFT JOIN messages m ON m.id = (SELECT id FROM messages WHERE chat_id = c.id AND is_deleted = 0 ORDER BY created_at DESC LIMIT 1)
        WHERE (c.user1_id = ? OR c.user2_id = ?)
        ORDER BY is_pinned DESC, m.created_at DESC
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
            'unread_count': chat['unread_count'],
            'is_pinned': chat['is_pinned'] == 1
        })
    return result


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
        ''', (to_chat_id, msg['sender_id'], msg['content'], msg['file_type'], msg['file_path'], msg['file_name'],
              msg['file_size']))
        conn.commit()
        new_id = cursor.lastrowid
        conn.close()
        return new_id
    conn.close()
    return None


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
    conn = get_db()
    cursor = conn.cursor()

    # Сначала получаем истории
    cursor.execute('''
        SELECT s.*, u.username, u.avatar
        FROM stories s
        JOIN users u ON s.user_id = u.id
        WHERE s.expires_at > datetime('now')
          AND (
              s.user_id = ?
              OR EXISTS (
                  SELECT 1 FROM story_privacy sp
                  WHERE sp.story_id = s.id AND sp.privacy_type = 'everyone'
              )
              OR EXISTS (
                  SELECT 1 FROM story_privacy sp
                  WHERE sp.story_id = s.id AND sp.privacy_type = 'contacts'
                  AND EXISTS (
                      SELECT 1 FROM contacts 
                      WHERE (user_id = ? AND contact_id = s.user_id) 
                      OR (user_id = s.user_id AND contact_id = ?)
                  )
              )
              OR EXISTS (
                  SELECT 1 FROM story_privacy sp
                  WHERE sp.story_id = s.id AND sp.privacy_type = 'selected'
                  AND EXISTS (
                      SELECT 1 FROM story_allowed_users 
                      WHERE story_id = s.id AND user_id = ?
                  )
              )
          )
        ORDER BY s.created_at DESC
    ''', (viewer_id, viewer_id, viewer_id, viewer_id))

    stories = cursor.fetchall()
    result = []

    # Для каждой истории отдельно получаем лайки и просмотры
    for story in stories:
        story_dict = dict(story)

        # Получаем количество лайков
        cursor.execute('SELECT COUNT(*) FROM story_interactions WHERE story_id = ? AND type = "like"', (story['id'],))
        likes_count = cursor.fetchone()[0]
        story_dict['likes_count'] = likes_count

        # Получаем количество просмотров
        cursor.execute('SELECT COUNT(*) FROM story_interactions WHERE story_id = ? AND type = "view"', (story['id'],))
        views_count = cursor.fetchone()[0]
        story_dict['views_count'] = views_count

        # Получаем список просмотревших (максимум 10 для производительности)
        cursor.execute('''
            SELECT u.id, u.username, u.avatar
            FROM story_interactions si
            JOIN users u ON si.user_id = u.id
            WHERE si.story_id = ? AND si.type = "view"
            LIMIT 10
        ''', (story['id'],))
        viewers = cursor.fetchall()
        story_dict['viewers'] = [dict(v) for v in viewers]

        result.append(story_dict)

    conn.close()
    return result


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
        pass
    finally:
        conn.close()


def get_story_likes_count(story_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM story_interactions WHERE story_id = ? AND type="like"', (story_id,))
    count = cursor.fetchone()[0]
    conn.close()
    return count


def get_story_viewers(story_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT u.id, u.username, u.avatar
        FROM story_interactions si
        JOIN users u ON si.user_id = u.id
        WHERE si.story_id = ? AND si.type = 'view'
    ''', (story_id,))
    viewers = cursor.fetchall()
    conn.close()
    return viewers


def can_user_interact(story_id, user_id):
    """Проверяет, может ли пользователь взаимодействовать с историей"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT 1 FROM stories s
        WHERE s.id = ? AND s.expires_at > datetime('now')
          AND (
              s.user_id = ?
              OR EXISTS (
                  SELECT 1 FROM story_privacy sp
                  WHERE sp.story_id = s.id AND sp.privacy_type = 'everyone'
              )
              OR EXISTS (
                  SELECT 1 FROM story_privacy sp
                  WHERE sp.story_id = s.id AND sp.privacy_type = 'contacts'
                  AND EXISTS (
                      SELECT 1 FROM contacts 
                      WHERE (user_id = ? AND contact_id = s.user_id) 
                      OR (user_id = s.user_id AND contact_id = ?)
                  )
              )
              OR EXISTS (
                  SELECT 1 FROM story_privacy sp
                  WHERE sp.story_id = s.id AND sp.privacy_type = 'selected'
                  AND EXISTS (
                      SELECT 1 FROM story_allowed_users 
                      WHERE story_id = s.id AND user_id = ?
                  )
              )
          )
    ''', (story_id, user_id, user_id, user_id, user_id))
    result = cursor.fetchone()
    conn.close()
    return result is not None


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


def delete_expired_stories():
    """Удаляет истории, у которых истёк срок"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM stories WHERE expires_at < datetime("now")')
    deleted = cursor.rowcount
    conn.commit()
    conn.close()
    if deleted > 0:
        print(f"🗑️ Удалено {deleted} устаревших историй")
    return deleted

# Вызовите после init_db() и перед запуском сервера:
init_db()
delete_expired_stories()

import threading
import time


def schedule_story_cleanup():
    """Запускает очистку старых историй каждый час"""

    def cleanup_job():
        while True:
            time.sleep(3600)  # 1 час
            delete_expired_stories()

    thread = threading.Thread(target=cleanup_job, daemon=True)
    thread.start()


# В конце файла, перед socketio.run:
schedule_story_cleanup()


# ==================== МАРШРУТЫ ====================

@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('chat_page'))
    return redirect(url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        phone = request.form.get('phone')
        password = request.form.get('password')
        remember = request.form.get('remember')
        user = verify_user(phone, password)
        if user:
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['phone'] = user['phone']
            if remember:
                session.permanent = True
            update_last_seen(user['id'])
            session_token = str(uuid.uuid4())
            add_session(user['id'], session_token, request.headers.get('User-Agent', 'Unknown'), request.remote_addr)
            session['session_token'] = session_token
            return redirect(url_for('chat_page'))
        return render_template('login.html', error='Неверный логин или пароль')
    return render_template('login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        phone = request.form.get('phone')
        username = request.form.get('username')
        password = request.form.get('password')
        confirm = request.form.get('confirm_password')
        email = request.form.get('email')
        if len(password) < 8:
            return render_template('register.html', error='Пароль минимум 8 символов')
        if password != confirm:
            return render_template('register.html', error='Пароли не совпадают')
        if not re.match(r'^[a-zA-Z0-9_]+$', username):
            return render_template('register.html', error='Только латиница, цифры, _')
        user_id = create_user(phone, username, password, email)
        if user_id:
            session['user_id'] = user_id
            session['username'] = username
            session['phone'] = phone
            update_last_seen(user_id)
            return redirect(url_for('chat_page'))
        return render_template('register.html', error='Пользователь уже существует')
    return render_template('register.html')


@app.route('/api/get_story_viewers/<int:story_id>')
def api_get_story_viewers(story_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    # Проверяем, является ли пользователь владельцем истории
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT user_id FROM stories WHERE id = ?', (story_id,))
    story = cursor.fetchone()
    conn.close()

    if not story:
        return jsonify({'error': 'Story not found'}), 404

    # Только владелец может видеть просмотры
    if story['user_id'] != session['user_id']:
        return jsonify({'error': 'Access denied'}), 403

    viewers = get_story_viewers(story_id)
    return jsonify([dict(v) for v in viewers])



@app.route('/logout')
def logout():
    if 'user_id' in session:
        update_last_seen(session['user_id'])
        if 'session_token' in session:
            delete_session(session['session_token'])
    session.clear()
    return redirect(url_for('login'))





# ==================== API МАРШРУТЫ ====================

@app.route('/api/search_users')
def api_search_users():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    query = request.args.get('q', '')
    if len(query) < 2:
        return jsonify([])
    users = search_users(query, session['user_id'])
    return jsonify([dict(u) for u in users])


@app.route('/api/add_contact', methods=['POST'])
def api_add_contact():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    data = request.get_json()
    contact_id = data.get('contact_id')
    if add_contact(session['user_id'], contact_id):
        return jsonify({'success': True})
    return jsonify({'success': False}), 400


@app.route('/api/rename_contact', methods=['POST'])
def api_rename_contact():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    data = request.get_json()
    contact_id = data.get('contact_id')
    new_name = data.get('new_name')
    rename_contact(session['user_id'], contact_id, new_name)
    return jsonify({'success': True})


@app.route('/api/get_contacts')
def api_get_contacts():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    contacts = get_contacts(session['user_id'])
    return jsonify([dict(c) for c in contacts])


@app.route('/api/get_user/<int:user_id>')
def api_get_user(user_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    user = get_user_by_id(user_id)
    if user:
        return jsonify({
            'id': user['id'],
            'username': user['username'],
            'phone': user['phone'],
            'avatar': user['avatar'],
            'bio': user['bio'] or '',
            'birthday': user['birthday'] or '',
            'last_seen': user['last_seen']
        })
    return jsonify({'error': 'User not found'}), 404


@app.route('/api/get_my_user')
def api_get_my_user():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    user = get_user_by_id(session['user_id'])
    if user:
        return jsonify({
            'id': user['id'],
            'username': user['username'],
            'phone': user['phone'],
            'avatar': user['avatar'],
            'bio': user['bio'] or '',
            'birthday': user['birthday'] or ''
        })
    return jsonify({'error': 'User not found'}), 404


@app.route('/api/get_chat/<int:user_id>')
def api_get_chat(user_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    chat_id = get_or_create_chat(session['user_id'], user_id)
    messages = get_messages(chat_id, session['user_id'])
    other_user = get_user_by_id(user_id) if user_id != session['user_id'] else None
    return jsonify({
        'chat_id': chat_id,
        'other_user': {
            'id': user_id,
            'username': 'Избранное' if user_id == session['user_id'] else (
                other_user['username'] if other_user else ''),
            'phone': other_user['phone'] if other_user else '',
            'avatar': other_user['avatar'] if other_user else None,
            'bio': other_user['bio'] if other_user else 'Ваше облачное хранилище',
            'last_seen': other_user['last_seen'] if other_user else None
        } if user_id == session['user_id'] or other_user else None,
        'messages': [dict(m) for m in messages]
    })


@app.route('/api/send_message', methods=['POST'])
def api_send_message():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    chat_id = request.form.get('chat_id')
    content = request.form.get('content', '')
    file_type = None
    file_path = None
    file_name = None
    file_size = None
    if 'file' in request.files:
        file = request.files['file']
        if file and file.filename:
            file_name = secure_filename(file.filename)
            ext = file_name.rsplit('.', 1)[1].lower() if '.' in file_name else ''
            if ext in ['png', 'jpg', 'jpeg', 'gif', 'webp']:
                file_type = 'photo'
                folder = 'photos'
            elif ext in ['mp4', 'webm', 'avi', 'mov']:
                file_type = 'video'
                folder = 'videos'
            elif ext in ['mp3', 'wav', 'ogg', 'm4a']:
                file_type = 'audio'
                folder = 'audio'
            else:
                file_type = 'document'
                folder = 'files'
            os.makedirs(os.path.join(app.config['UPLOAD_FOLDER'], folder), exist_ok=True)
            unique_name = f"{uuid.uuid4().hex}.{ext}"
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], folder, unique_name)
            file.save(file_path)
            file_size = os.path.getsize(file_path)
            file_path = f"uploads/{folder}/{unique_name}"
    message = send_message(chat_id, session['user_id'], content, file_type, file_path, file_name, file_size)
    if message:
        socketio.emit('new_message', {'chat_id': chat_id, 'message': dict(message)}, room=f"chat_{chat_id}")
    return jsonify({'success': True})


@app.route('/api/edit_message', methods=['POST'])
def api_edit_message():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    data = request.get_json()
    edit_message(data.get('message_id'), data.get('content'))
    socketio.emit('message_edited', {'message_id': data.get('message_id'), 'new_content': data.get('content')},
                  broadcast=True)
    return jsonify({'success': True})


@app.route('/api/delete_message', methods=['POST'])
def api_delete_message():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    data = request.get_json()
    delete_message(data.get('message_id'), session['user_id'], data.get('delete_for_all', False))
    socketio.emit('message_edited', {...})
    socketio.emit('message_deleted', {...})
    return jsonify({'success': True})


@app.route('/api/forward_message', methods=['POST'])
def api_forward_message():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    data = request.get_json()
    new_id = forward_message(data.get('message_id'), data.get('to_chat_id'))
    return jsonify({'success': True, 'message_id': new_id}) if new_id else jsonify({'success': False}), 400


@app.route('/api/mark_read', methods=['POST'])
def api_mark_read():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    data = request.get_json()
    get_messages(data.get('chat_id'), session['user_id'])
    return jsonify({'success': True})


@app.route('/api/make_call', methods=['POST'])
def api_make_call():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    data = request.get_json()
    call_id = add_call(session['user_id'], data.get('receiver_id'), data.get('call_type'), 'ringing')
    return jsonify({'success': True, 'call_id': call_id})


@app.route('/api/answer_call', methods=['POST'])
def api_answer_call():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    data = request.get_json()
    update_call_status(data.get('call_id'), 'answered')
    return jsonify({'success': True})


@app.route('/api/webrtc_signal', methods=['POST'])
def api_webrtc_signal():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    data = request.get_json()
    target_user_id = data.get('target_user_id')
    signal_type = data.get('signal_type')
    signal_data = data.get('signal_data')

    # Отправляем сигнал через socketio
    socketio.emit('webrtc_signal', {
        'signal_type': signal_type,
        'signal_data': signal_data,
        'from_user_id': session['user_id']
    }, room=f"user_{target_user_id}")

    return jsonify({'success': True})


@app.route('/api/get_call_history')
def api_get_call_history():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    return jsonify([dict(c) for c in get_call_history(session['user_id'])])


@app.route('/api/add_to_favorites', methods=['POST'])
def api_add_to_favorites():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    note = request.form.get('note')
    file = request.files.get('file')
    file_type = file_path = file_name = None
    if file and file.filename:
        file_name = secure_filename(file.filename)
        ext = file_name.rsplit('.', 1)[1].lower() if '.' in file_name else ''
        file_type = 'photo' if ext in ['png', 'jpg', 'jpeg', 'gif', 'webp'] else 'video' if ext in ['mp4', 'webm',
                                                                                                    'avi',
                                                                                                    'mov'] else 'audio' if ext in [
            'mp3', 'wav', 'ogg', 'm4a'] else 'document'
        os.makedirs(os.path.join(app.config['UPLOAD_FOLDER'], 'favorites'), exist_ok=True)
        unique_name = f"{uuid.uuid4().hex}.{ext}"
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], 'favorites', unique_name)
        file.save(file_path)
        file_path = f"uploads/favorites/{unique_name}"
    fav_id = add_to_favorites(session['user_id'], file_type, file_path, file_name, note)
    if note:
        chat_id = get_or_create_chat(session['user_id'], session['user_id'])
        if chat_id:
            send_message(chat_id, session['user_id'], note, None, None, None, None)
    return jsonify({'success': True, 'favorite_id': fav_id})


@app.route('/api/get_favorites')
def api_get_favorites():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    return jsonify([dict(f) for f in get_favorites(session['user_id'])])


@app.route('/api/update_profile', methods=['POST'])
def api_update_profile():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    username = request.form.get('username')
    bio = request.form.get('bio')
    birthday = request.form.get('birthday')
    updates = {}
    if username:
        existing = get_user_by_username(username)
        if existing and existing['id'] != session['user_id']:
            return jsonify({'success': False, 'error': 'Username already taken'}), 400
        updates['username'] = username
        session['username'] = username
    if bio is not None:
        updates['bio'] = bio
    if birthday:
        updates['birthday'] = birthday
    if 'avatar' in request.files:
        file = request.files['avatar']
        if file and file.filename:
            ext = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else 'png'
            unique_name = f"{uuid.uuid4().hex}.{ext}"
            folder = os.path.join(app.config['UPLOAD_FOLDER'], 'avatars')
            os.makedirs(folder, exist_ok=True)
            file_path = os.path.join(folder, unique_name)
            file.save(file_path)
            resize_and_crop_image(file_path)
            updates['avatar'] = f"uploads/avatars/{unique_name}"
    if updates:
        update_user_settings(session['user_id'], **updates)
    return jsonify({'success': True, 'user': updates})


@app.route('/api/update_privacy', methods=['POST'])
def api_update_privacy():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    data = request.get_json()
    update_user_settings(session['user_id'],
                         privacy_last_seen=data.get('last_seen', 'everyone'),
                         privacy_photo=data.get('profile_photo', 'everyone'),
                         privacy_forward=data.get('forward_messages', 'everyone'),
                         privacy_calls=data.get('calls', 'everyone'),
                         privacy_messages=data.get('messages', 'everyone'))
    return jsonify({'success': True})


@app.route('/api/get_privacy')
def api_get_privacy():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    user = get_user_by_id(session['user_id'])
    return jsonify({
        'last_seen': user['privacy_last_seen'],
        'profile_photo': user['privacy_photo'],
        'forward_messages': user['privacy_forward'],
        'calls': user['privacy_calls'],
        'messages': user['privacy_messages']
    })


@app.route('/api/update_theme', methods=['POST'])
def api_update_theme():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    data = request.get_json()
    update_user_settings(session['user_id'], theme=data.get('theme', 'light'))
    return jsonify({'success': True})


@app.route('/api/update_font_size', methods=['POST'])
def api_update_font_size():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    data = request.get_json()
    update_user_settings(session['user_id'], font_size=data.get('font_size', 14))
    return jsonify({'success': True})


@app.route('/api/update_bubble_radius', methods=['POST'])
def api_update_bubble_radius():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    data = request.get_json()
    update_user_settings(session['user_id'], bubble_radius=data.get('bubble_radius', 18))
    return jsonify({'success': True})


@app.route('/api/update_wallpaper', methods=['POST'])
def api_update_wallpaper():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    data = request.get_json()
    update_user_settings(session['user_id'], wallpaper=data.get('wallpaper', ''))
    return jsonify({'success': True})


@app.route('/api/get_settings')
def api_get_settings():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    user = get_user_by_id(session['user_id'])
    return jsonify({
        'theme': user['theme'],
        'font_size': user['font_size'],
        'bubble_radius': user['bubble_radius'],
        'wallpaper': user['wallpaper']
    })


@app.route('/api/delete_account', methods=['POST'])
def api_delete_account():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    data = request.get_json()
    confirmation = data.get('confirmation', '')
    user = get_user_by_id(session['user_id'])
    if confirmation == user['phone'] or confirmation == user['username']:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM users WHERE id = ?', (session['user_id'],))
        cursor.execute('DELETE FROM chats WHERE user1_id = ? OR user2_id = ?', (session['user_id'], session['user_id']))
        cursor.execute('DELETE FROM messages WHERE sender_id = ?', (session['user_id'],))
        cursor.execute('DELETE FROM contacts WHERE user_id = ? OR contact_id = ?',
                       (session['user_id'], session['user_id']))
        cursor.execute('DELETE FROM favorites WHERE user_id = ?', (session['user_id'],))
        cursor.execute('DELETE FROM calls WHERE caller_id = ? OR receiver_id = ?',
                       (session['user_id'], session['user_id']))
        cursor.execute('DELETE FROM user_sessions WHERE user_id = ?', (session['user_id'],))
        conn.commit()
        conn.close()
        session.clear()
        return jsonify({'success': True})
    return jsonify({'success': False}), 400


@app.route('/api/get_sessions')
def api_get_sessions():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    sessions = get_user_sessions(session['user_id'])
    return jsonify([dict(s) for s in sessions])


@app.route('/api/terminate_session', methods=['POST'])
def api_terminate_session():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    data = request.get_json()
    session_id = data.get('session_id')
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM user_sessions WHERE id = ? AND user_id = ?', (session_id, session['user_id']))
    conn.commit()
    conn.close()
    return jsonify({'success': True})


@app.route('/api/terminate_all_sessions', methods=['POST'])
def api_terminate_all_sessions():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    delete_all_sessions_except(session['user_id'], session.get('session_token', ''))
    return jsonify({'success': True})


@app.route('/api/upload_story', methods=['POST'])
def api_upload_story():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    try:
        file = request.files.get('file')
        caption = request.form.get('caption', '')
        music = request.files.get('music')
        privacy = request.form.get('privacy', 'everyone')
        selected_users = request.form.getlist('selected_users')

        if not file:
            return jsonify({'error': 'No file'}), 400

        ext = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else 'png'
        file_type = 'photo' if ext in ['jpg', 'jpeg', 'png', 'gif', 'webp'] else 'video'
        filename = f"{uuid.uuid4().hex}.{ext}"
        folder = os.path.join(app.config['UPLOAD_FOLDER'], 'stories')
        os.makedirs(folder, exist_ok=True)
        file_path = os.path.join(folder, filename)
        file.save(file_path)

        music_path = None
        if music and music.filename:
            music_ext = music.filename.rsplit('.', 1)[1].lower() if '.' in music.filename else 'mp3'
            music_name = f"{uuid.uuid4().hex}.{music_ext}"
            music_folder = os.path.join(app.config['UPLOAD_FOLDER'], 'story_music')
            os.makedirs(music_folder, exist_ok=True)
            music_path = os.path.join(music_folder, music_name)
            music.save(music_path)
            music_path = f"uploads/story_music/{music_name}"

        expires_at = datetime.now() + timedelta(hours=24)

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO stories (user_id, file_type, file_path, caption, music, expires_at)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (session['user_id'], file_type, f"uploads/stories/{filename}", caption, music_path, expires_at))
        story_id = cursor.lastrowid

        cursor.execute('INSERT INTO story_privacy (story_id, privacy_type) VALUES (?, ?)', (story_id, privacy))
        if privacy == 'selected' and selected_users:
            for uid in selected_users:
                cursor.execute('INSERT INTO story_allowed_users (story_id, user_id) VALUES (?, ?)', (story_id, uid))

        conn.commit()
        conn.close()

        # Исправленный emit - без broadcast
        socketio.emit('new_story', {'user_id': session['user_id']})

        return jsonify({'success': True, 'story_id': story_id})

    except Exception as e:
        print(f"Ошибка при загрузке истории: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/get_stories')
def api_get_stories():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    stories = get_stories_for_user(session['user_id'])
    return jsonify([dict(s) for s in stories])


@app.route('/api/story_view', methods=['POST'])
def api_story_view():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    data = request.get_json()
    add_story_interaction(data['story_id'], session['user_id'], 'view')
    return jsonify({'success': True})


@app.route('/api/story_like', methods=['POST'])
def api_story_like():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    data = request.get_json()
    add_story_interaction(data['story_id'], session['user_id'], 'like')
    return jsonify({'success': True})


@app.route('/api/story_reply', methods=['POST'])
def api_story_reply():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    data = request.get_json()
    add_story_interaction(data['story_id'], session['user_id'], 'reply', data.get('reply_text'))
    return jsonify({'success': True})


@app.route('/uploads/<path:filename>')
def uploaded_file(filename):
    return send_file(os.path.join(app.config['UPLOAD_FOLDER'], filename))


@app.route('/api/update_profile_avatar', methods=['POST'])
def api_update_profile_avatar():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    data = request.get_json()
    avatar_url = data.get('avatar_url')

    if not avatar_url:
        return jsonify({'success': False, 'error': 'No avatar URL'}), 400

    # Ищем файл
    source_path = os.path.join('static', avatar_url)
    if not os.path.exists(source_path):
        source_path = os.path.join('static', 'avatar-swg', os.path.basename(avatar_url))

    if os.path.exists(source_path):
        # Копируем файл в папку пользователя
        ext = os.path.splitext(source_path)[1]
        new_filename = f"user_{session['user_id']}_avatar{ext}"
        dest_path = os.path.join(app.config['UPLOAD_FOLDER'], 'avatars', new_filename)

        import shutil
        shutil.copy2(source_path, dest_path)

        avatar_db_path = f"uploads/avatars/{new_filename}"
        update_user_settings(session['user_id'], avatar=avatar_db_path)
        return jsonify({'success': True})
    else:
        return jsonify({'success': False, 'error': 'File not found'}), 404





@app.route('/api/pin_chat', methods=['POST'])
def api_pin_chat():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    data = request.get_json()
    chat_id = data.get('chat_id')
    if chat_id:
        pin_chat(session['user_id'], chat_id)
        return jsonify({'success': True})
    return jsonify({'success': False}), 400

@app.route('/api/unpin_chat', methods=['POST'])
def api_unpin_chat():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    data = request.get_json()
    chat_id = data.get('chat_id')
    if chat_id:
        unpin_chat(session['user_id'], chat_id)
        return jsonify({'success': True})
    return jsonify({'success': False}), 400


@app.route('/chat')
def chat_page():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user = get_user_by_id(session['user_id'])

    if not user:
        session.clear()
        return redirect(url_for('login'))

    chats = get_user_chats(session['user_id'])
    contacts = get_contacts(session['user_id'])
    call_history = get_call_history(session['user_id'])
    favorites = get_favorites(session['user_id'])

    # Отладочный вывод
    print(f"DEBUG: user_id={session['user_id']}")
    print(f"DEBUG: chats count={len(chats)}")
    print(f"DEBUG: chats={chats}")

    return render_template('chat.html',
                           user=user,
                           chats=chats,
                           contacts=contacts,
                           call_history=call_history,
                           favorites=favorites)


@app.route('/api/get_chats_list')
def api_get_chats_list():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    chats = get_user_chats(session['user_id'])
    return jsonify(chats)


@app.route('/api/get_story_likes/<int:story_id>')
def api_get_story_likes(story_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    # Проверяем, является ли пользователь владельцем истории
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT user_id FROM stories WHERE id = ?', (story_id,))
    story = cursor.fetchone()
    conn.close()

    if not story:
        return jsonify({'error': 'Story not found'}), 404

    # Только владелец может видеть лайки
    if story['user_id'] != session['user_id']:
        return jsonify({'error': 'Access denied'}), 403

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT u.id, u.username, u.avatar
        FROM story_interactions si
        JOIN users u ON si.user_id = u.id
        WHERE si.story_id = ? AND si.type = 'like'
    ''', (story_id,))
    likes = cursor.fetchall()
    conn.close()
    return jsonify([dict(l) for l in likes])



@socketio.on('connect')
def handle_connect():
    if 'user_id' in session:
        join_room(f"user_{session['user_id']}")
        update_last_seen(session['user_id'])


@socketio.on('disconnect')
def handle_disconnect():
    if 'user_id' in session:
        update_last_seen(session['user_id'])


@socketio.on('join_chat')
def handle_join_chat(data):
    if 'user_id' in session:
        join_room(f"chat_{data.get('chat_id')}")


@socketio.on('typing')
def handle_typing(data):
    if 'user_id' in session:
        emit('user_typing', {'user_id': session['user_id'], 'username': session['username']},
             room=f"chat_{data.get('chat_id')}")


def get_local_ip():
    """Получает локальный IP адрес компьютера в сети"""
    try:
        import socket
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"

init_db()





if __name__ == '__main__':
    print("\n" + "=" * 60)
    print("🔌 SWILLGRAM ЗАПУЩЕН!")
    print("=" * 60)

    # Получаем локальный IP
    local_ip = get_local_ip()

    print("\n📱 Доступные адреса для подключения:")
    print(f"   • Локальный: http://localhost:5000")
    print(f"   • Локальный: http://127.0.0.1:5000")
    if local_ip != "127.0.0.1":
        print(f"   • Сеть:      http://{local_ip}:5000")

    print("\n💡 Инструкция:")
    print(f"   1. Убедитесь, что ваше устройство и компьютер в одной сети")
    print(f"   2. На другом устройстве откройте браузер")
    print(f"   3. Введите адрес: http://{local_ip}:5000")

    print("\n⚠️  Внимание:")
    print("   • Для доступа с других устройств отключите брандмауэр")
    print("   • Убедитесь, что порт 5000 открыт в настройках сети")
    print("   • Нажмите Ctrl+C для остановки сервера")

    print("\n" + "=" * 60 + "\n")

    # Запускаем сервер на всех интерфейсах
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)