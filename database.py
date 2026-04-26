import sqlite3
import hashlib
import os
from datetime import datetime, timedelta
from PIL import Image

DB_PATH = 'nexgram.db'


def get_db():
    """Возвращает соединение с БД с row_factory=sqlite3.Row"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Инициализация базы данных: создание всех таблиц"""
    conn = get_db()
    cursor = conn.cursor()

    # Таблица users
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            unique_id INTEGER UNIQUE NOT NULL,
            phone TEXT UNIQUE NOT NULL,
            username TEXT UNIQUE,
            display_name TEXT,
            password TEXT NOT NULL,
            avatar TEXT,
            bio TEXT,
            birthday TEXT,
            last_seen DATETIME,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            privacy_last_seen TEXT DEFAULT 'everyone',
            privacy_photo TEXT DEFAULT 'everyone',
            privacy_forward TEXT DEFAULT 'everyone',
            privacy_calls TEXT DEFAULT 'everyone',
            privacy_messages TEXT DEFAULT 'everyone',
            theme TEXT DEFAULT 'light',
            font_size INTEGER DEFAULT 14,
            bubble_radius INTEGER DEFAULT 18,
            font_family TEXT DEFAULT "'Unbounded', cursive",
            my_message_color TEXT DEFAULT '#667eea',
            their_message_color TEXT DEFAULT '#f3f4f6',
            wallpaper TEXT DEFAULT '',
            wallpaper_image TEXT,
            email TEXT,
            is_deleted BOOLEAN DEFAULT 0,
            deleted_at DATETIME,
            registration_complete BOOLEAN DEFAULT 0
        )
    ''')

    # Таблица chats
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS chats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user1_id INTEGER NOT NULL,
            user2_id INTEGER NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user1_id, user2_id)
        )
    ''')

    # Таблица messages
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER,
            group_id INTEGER,
            channel_id INTEGER,
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
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            reply_to_id INTEGER,
            forwarded_from_id INTEGER,
            forwarded_from_user_id INTEGER,
            forwarded_from_username TEXT,
            forwarded_from_display_name TEXT
        )
    ''')

    # Таблица contacts
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS contacts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            contact_id INTEGER NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id, contact_id)
        )
    ''')

    # Таблица contact_names
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS contact_names (
            user_id INTEGER NOT NULL,
            contact_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            PRIMARY KEY (user_id, contact_id)
        )
    ''')

    # Таблица favorites
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

    # Таблица calls
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

    # Таблица video_calls
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS video_calls (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            room_id TEXT UNIQUE NOT NULL,
            creator_id INTEGER NOT NULL,
            call_type TEXT DEFAULT 'video',
            status TEXT DEFAULT 'active',
            started_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            ended_at DATETIME,
            duration INTEGER DEFAULT 0,
            participant_count INTEGER DEFAULT 1
        )
    ''')

    # Таблица video_call_participants
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS video_call_participants (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            call_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            joined_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            left_at DATETIME,
            audio_only BOOLEAN DEFAULT 0,
            screensharing BOOLEAN DEFAULT 0
        )
    ''')

    # Таблица user_sessions
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

    # Таблица stories
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

    # Таблица story_interactions
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

    # Таблица story_privacy
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS story_privacy (
            story_id INTEGER PRIMARY KEY,
            privacy_type TEXT,
            FOREIGN KEY (story_id) REFERENCES stories(id) ON DELETE CASCADE
        )
    ''')

    # Таблица story_allowed_users
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS story_allowed_users (
            story_id INTEGER,
            user_id INTEGER,
            PRIMARY KEY (story_id, user_id)
        )
    ''')

    # Таблица pinned_chats
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS pinned_chats (
            user_id INTEGER NOT NULL,
            chat_id INTEGER NOT NULL,
            pinned_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (user_id, chat_id)
        )
    ''')

    # Таблица groups
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS groups (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT,
            owner_id INTEGER NOT NULL,
            is_public BOOLEAN DEFAULT 1,
            invite_link TEXT UNIQUE,
            avatar TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (owner_id) REFERENCES users(id)
        )
    ''')

    # Таблица group_members
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS group_members (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            group_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            role TEXT DEFAULT 'member',
            joined_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(group_id, user_id),
            FOREIGN KEY (group_id) REFERENCES groups(id) ON DELETE CASCADE,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')

    # Таблица group_permissions
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS group_permissions (
            group_id INTEGER NOT NULL,
            role TEXT NOT NULL,
            can_send_messages BOOLEAN DEFAULT 1,
            can_send_media BOOLEAN DEFAULT 1,
            can_add_members BOOLEAN DEFAULT 0,
            can_pin_messages BOOLEAN DEFAULT 0,
            can_change_info BOOLEAN DEFAULT 0,
            can_delete_messages BOOLEAN DEFAULT 0,
            can_ban_users BOOLEAN DEFAULT 0,
            PRIMARY KEY (group_id, role),
            FOREIGN KEY (group_id) REFERENCES groups(id) ON DELETE CASCADE
        )
    ''')

    # Таблица channels
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS channels (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT,
            owner_id INTEGER NOT NULL,
            is_public BOOLEAN DEFAULT 1,
            invite_link TEXT UNIQUE,
            avatar TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (owner_id) REFERENCES users(id)
        )
    ''')

    # Таблица channel_subscribers
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS channel_subscribers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            channel_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            subscribed_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(channel_id, user_id),
            FOREIGN KEY (channel_id) REFERENCES channels(id) ON DELETE CASCADE,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')

    # Таблица channel_admins
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS channel_admins (
            channel_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            can_post BOOLEAN DEFAULT 1,
            can_edit BOOLEAN DEFAULT 0,
            can_delete BOOLEAN DEFAULT 0,
            can_add_admins BOOLEAN DEFAULT 0,
            added_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (channel_id, user_id),
            FOREIGN KEY (channel_id) REFERENCES channels(id) ON DELETE CASCADE,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')

    # Таблица message_reactions
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS message_reactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            message_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            reaction TEXT NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(message_id, user_id, reaction)
        )
    ''')

    # Таблица recent_searches
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS recent_searches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            search_query TEXT NOT NULL,
            search_type TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Таблица preloaded_avatars
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS preloaded_avatars (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT UNIQUE NOT NULL,
            display_name TEXT,
            category TEXT DEFAULT 'default'
        )
    ''')

    # Таблица blocked_users
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS blocked_users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            blocked_user_id INTEGER NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id, blocked_user_id)
        )
    ''')

    # Таблица story_reactions
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS story_reactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            story_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            reaction TEXT NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(story_id, user_id, reaction)
        )
    ''')

    # Таблица story_views
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS story_views (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            story_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            viewed_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(story_id, user_id)
        )
    ''')

    # Индексы
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_blocked_users_user_id ON blocked_users(user_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_messages_chat_id ON messages(chat_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_messages_group_id ON messages(group_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_messages_channel_id ON messages(channel_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_messages_sender_id ON messages(sender_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_messages_created_at ON messages(created_at)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_users_unique_id ON users(unique_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_users_username ON users(username)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_users_phone ON users(phone)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_group_members_user_id ON group_members(user_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_channel_subscribers_user_id ON channel_subscribers(user_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_stories_user_id ON stories(user_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_stories_expires_at ON stories(expires_at)')

    # Заполняем предзагрузочные аватарки
    default_avatars = [
        ('avatar1.jpg', 'Аватар 1', 'default'),
        ('avatar2.jpg', 'Аватар 2', 'default'),
        ('avatar3.jpg', 'Аватар 3', 'default'),
        ('avatar4.jpg', 'Аватар 4', 'default'),
        ('avatar5.png', 'Аватар 5', 'default'),
        ('avatar6.png', 'Аватар 6', 'default'),
        ('avatar7.png', 'Аватар 7', 'default'),
        ('avatar8.png', 'Аватар 8', 'default'),
        ('deleted.png', 'Удалённый аккаунт', 'system')
    ]

    for ava in default_avatars:
        cursor.execute('''
            INSERT OR IGNORE INTO preloaded_avatars (filename, display_name, category)
            VALUES (?, ?, ?)
        ''', ava)

    # Начальные права для групп
    cursor.execute('''
        INSERT OR IGNORE INTO group_permissions (group_id, role, can_send_messages, can_send_media, 
            can_add_members, can_pin_messages, can_change_info, can_delete_messages, can_ban_users)
        SELECT id, 'owner', 1, 1, 1, 1, 1, 1, 1 FROM groups
    ''')

    cursor.execute('''
        INSERT OR IGNORE INTO group_permissions (group_id, role, can_send_messages, can_send_media, 
            can_add_members, can_pin_messages, can_change_info, can_delete_messages, can_ban_users)
        SELECT id, 'admin', 1, 1, 1, 1, 1, 1, 1 FROM groups
    ''')

    cursor.execute('''
        INSERT OR IGNORE INTO group_permissions (group_id, role, can_send_messages, can_send_media, 
            can_add_members, can_pin_messages, can_change_info, can_delete_messages, can_ban_users)
        SELECT id, 'member', 1, 1, 0, 0, 0, 0, 0 FROM groups
    ''')

    conn.commit()
    conn.close()


# ----- ФУНКЦИИ БЛОКИРОВКИ -----
def block_user(user_id, blocked_user_id):
    """Блокирует пользователя"""
    if user_id == blocked_user_id:
        return False
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT OR IGNORE INTO blocked_users (user_id, blocked_user_id)
            VALUES (?, ?)
        ''', (user_id, blocked_user_id))
        conn.commit()
        return True
    except:
        return False
    finally:
        conn.close()


def unblock_user(user_id, blocked_user_id):
    """Разблокирует пользователя"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        DELETE FROM blocked_users 
        WHERE user_id = ? AND blocked_user_id = ?
    ''', (user_id, blocked_user_id))
    conn.commit()
    conn.close()
    return True


def is_user_blocked(user_id, blocked_user_id):
    """Проверяет, заблокирован ли пользователь"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT id FROM blocked_users 
        WHERE user_id = ? AND blocked_user_id = ?
    ''', (user_id, blocked_user_id))
    result = cursor.fetchone()
    conn.close()
    return result is not None


def get_blocked_users(user_id):
    """Получает список заблокированных пользователей"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT u.id, u.unique_id, u.username, u.display_name, u.avatar
        FROM blocked_users bu
        JOIN users u ON bu.blocked_user_id = u.id
        WHERE bu.user_id = ?
    ''', (user_id,))
    blocked = cursor.fetchall()
    conn.close()
    return blocked


def get_user_profile(user_id, current_user_id):
    """Получает профиль пользователя с информацией о блокировке"""
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute('''
        SELECT id, unique_id, username, display_name, phone, avatar, bio, birthday, last_seen, is_deleted
        FROM users 
        WHERE id = ? AND is_deleted = 0
    ''', (user_id,))
    user = cursor.fetchone()
    conn.close()

    # Если пользователь не найден
    if not user:
        return None

    # Создаём словарь
    user_dict = dict(user)
    user_dict['is_blocked_by_me'] = is_user_blocked(current_user_id, user_id)
    user_dict['has_blocked_me'] = is_user_blocked(user_id, current_user_id)

    return user_dict


def clear_chat(chat_id=None, group_id=None, channel_id=None):
    """Очищает историю сообщений в чате"""
    conn = get_db()
    cursor = conn.cursor()

    if chat_id:
        cursor.execute('UPDATE messages SET is_deleted = 1 WHERE chat_id = ?', (chat_id,))
    elif group_id:
        cursor.execute('UPDATE messages SET is_deleted = 1 WHERE group_id = ?', (group_id,))
    elif channel_id:
        cursor.execute('UPDATE messages SET is_deleted = 1 WHERE channel_id = ?', (channel_id,))

    conn.commit()
    conn.close()
    return True


def reply_to_story(story_id, user_id, reply_text):
    """Отправляет ответ на историю"""
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute('SELECT user_id FROM stories WHERE id = ?', (story_id,))
    story = cursor.fetchone()

    if story:
        chat_id = get_or_create_chat(user_id, story['user_id'])
        message_content = f"📱 Ответ на историю: {reply_text}"
        send_message(chat_id=chat_id, sender_id=user_id, content=message_content)
        return chat_id

    conn.close()
    return None


# ----- ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ -----
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()


def resize_and_crop_image(image_path, size=(500, 500)):
    try:
        img = Image.open(image_path)
        min_size = min(img.size)
        left = (img.size[0] - min_size) / 2
        top = (img.size[1] - min_size) / 2
        right = (img.size[0] + min_size) / 2
        bottom = (img.size[1] + min_size) / 2
        img = img.crop((left, top, right, bottom))
        img = img.resize(size, Image.Resampling.LANCZOS)
        img.save(image_path)
        return True
    except:
        return False


def generate_unique_id():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT MAX(unique_id) as max_id FROM users')
    result = cursor.fetchone()
    conn.close()

    if result and result['max_id'] and result['max_id'] >= 1000000:
        return result['max_id'] + 1
    else:
        return 1000000


# ----- ПОЛЬЗОВАТЕЛИ -----
def create_user_initial(phone, password, email=None):
    """Первый этап регистрации"""
    conn = get_db()
    cursor = conn.cursor()
    try:
        unique_id = generate_unique_id()
        temp_username = f"user_{phone.replace('+', '').replace(' ', '')[:8]}"
        cursor.execute('''
            INSERT INTO users (unique_id, phone, username, display_name, password, last_seen, email, registration_complete)
            VALUES (?, ?, ?, ?, ?, ?, ?, 0)
        ''', (unique_id, phone, temp_username, temp_username, hash_password(password), datetime.now(), email))
        conn.commit()
        user_id = cursor.lastrowid

        cursor.execute('INSERT INTO chats (user1_id, user2_id) VALUES (?, ?)', (user_id, user_id))
        conn.commit()
        return user_id
    except Exception as e:
        print(f"Error creating user: {e}")
        return None
    finally:
        conn.close()


def complete_registration(user_id, username, display_name, avatar=None):
    """Второй этап регистрации"""
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            UPDATE users 
            SET username = ?, display_name = ?, avatar = ?, registration_complete = 1
            WHERE id = ?
        ''', (username, display_name or username, avatar, user_id))
        conn.commit()
        return True
    except Exception as e:
        print(f"Error completing registration: {e}")
        return False
    finally:
        conn.close()


def check_phone_exists(phone):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT id, registration_complete FROM users WHERE phone = ? AND is_deleted = 0', (phone,))
    user = cursor.fetchone()
    conn.close()
    return user


def get_user_by_id(user_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE id = ? AND is_deleted = 0', (user_id,))
    user = cursor.fetchone()
    conn.close()
    return user


def get_user_by_unique_id(unique_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE unique_id = ? AND is_deleted = 0', (unique_id,))
    user = cursor.fetchone()
    conn.close()
    return user


def get_user_by_username(username):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE username = ? AND is_deleted = 0', (username,))
    user = cursor.fetchone()
    conn.close()
    return user


def get_user_by_phone(phone):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE phone = ? AND is_deleted = 0', (phone,))
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


def delete_user_account(user_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT username FROM users WHERE id = ?', (user_id,))
    user = cursor.fetchone()

    if user:
        new_username = f"deleted_{user['username']}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        cursor.execute('''
            UPDATE users SET 
                is_deleted = 1,
                deleted_at = ?,
                username = ?,
                display_name = 'Удалённый аккаунт',
                avatar = 'static/avatar-swg/deleted.png',
                bio = NULL,
                phone = ?,
                password = ?
            WHERE id = ?
        ''', (datetime.now(), new_username, f"deleted_{user_id}", hash_password("deleted"), user_id))
        conn.commit()
    conn.close()
    return True


def check_username_available(username, current_user_id=None):
    conn = get_db()
    cursor = conn.cursor()

    if current_user_id:
        cursor.execute('SELECT id FROM users WHERE username = ? AND id != ? AND is_deleted = 0',
                       (username, current_user_id))
    else:
        cursor.execute('SELECT id FROM users WHERE username = ? AND is_deleted = 0', (username,))

    user = cursor.fetchone()
    conn.close()
    return user is None


# ----- ПОИСК (ПРОСТОЙ) -----
def search_users(query, current_user_id):
    """Простой поиск только по телефону или username"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT id, unique_id, username, display_name, phone, avatar, bio, last_seen
        FROM users
        WHERE (username = ? OR phone = ?) 
          AND id != ? 
          AND is_deleted = 0
          AND registration_complete = 1
        LIMIT 20
    ''', (query, query, current_user_id))
    users = cursor.fetchall()
    conn.close()
    return users


# ----- ГРУППЫ -----
def create_group(name, owner_id, description=None, is_public=True, avatar=None):
    conn = get_db()
    cursor = conn.cursor()
    try:
        import secrets
        invite_link = secrets.token_urlsafe(16)

        cursor.execute('''
            INSERT INTO groups (name, description, owner_id, is_public, invite_link, avatar)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (name, description, owner_id, is_public, invite_link, avatar))

        group_id = cursor.lastrowid

        cursor.execute('''
            INSERT INTO group_members (group_id, user_id, role)
            VALUES (?, ?, 'owner')
        ''', (group_id, owner_id))

        # Добавляем права для owner
        cursor.execute('''
            INSERT INTO group_permissions (group_id, role, can_send_messages, can_send_media, 
                can_add_members, can_pin_messages, can_change_info, can_delete_messages, can_ban_users)
            VALUES (?, 'owner', 1, 1, 1, 1, 1, 1, 1)
        ''', (group_id,))

        cursor.execute('''
            INSERT INTO group_permissions (group_id, role, can_send_messages, can_send_media, 
                can_add_members, can_pin_messages, can_change_info, can_delete_messages, can_ban_users)
            VALUES (?, 'admin', 1, 1, 1, 1, 1, 1, 1)
        ''', (group_id,))

        cursor.execute('''
            INSERT INTO group_permissions (group_id, role, can_send_messages, can_send_media, 
                can_add_members, can_pin_messages, can_change_info, can_delete_messages, can_ban_users)
            VALUES (?, 'member', 1, 1, 0, 0, 0, 0, 0)
        ''', (group_id,))

        conn.commit()
        return group_id
    except Exception as e:
        print(f"Error creating group: {e}")
        return None
    finally:
        conn.close()


def get_group_by_id(group_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT g.*, u.username as owner_username, u.display_name as owner_display_name,
               (SELECT COUNT(*) FROM group_members WHERE group_id = g.id) as member_count
        FROM groups g
        JOIN users u ON g.owner_id = u.id
        WHERE g.id = ?
    ''', (group_id,))
    group = cursor.fetchone()
    conn.close()
    return group


def get_group_by_invite_link(invite_link):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM groups WHERE invite_link = ?', (invite_link,))
    group = cursor.fetchone()
    conn.close()
    return group


def get_user_groups(user_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT g.*, gm.role,
               (SELECT COUNT(*) FROM group_members WHERE group_id = g.id) as member_count
        FROM groups g
        JOIN group_members gm ON g.id = gm.group_id
        WHERE gm.user_id = ?
        ORDER BY g.created_at DESC
    ''', (user_id,))
    groups = cursor.fetchall()
    conn.close()
    return groups


def add_group_member(group_id, user_id, role='member'):
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT OR IGNORE INTO group_members (group_id, user_id, role)
            VALUES (?, ?, ?)
        ''', (group_id, user_id, role))
        conn.commit()
        return True
    except:
        return False
    finally:
        conn.close()


def remove_group_member(group_id, user_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM group_members WHERE group_id = ? AND user_id = ? AND role != "owner"',
                   (group_id, user_id))
    conn.commit()
    conn.close()
    return True


def get_group_members(group_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT u.id, u.username, u.display_name, u.avatar, u.last_seen, gm.role, gm.joined_at
        FROM group_members gm
        JOIN users u ON gm.user_id = u.id
        WHERE gm.group_id = ? AND u.is_deleted = 0
        ORDER BY 
            CASE gm.role 
                WHEN 'owner' THEN 1 
                WHEN 'admin' THEN 2 
                ELSE 3 
            END,
            gm.joined_at ASC
    ''', (group_id,))
    members = cursor.fetchall()
    conn.close()
    return members


def is_group_member(group_id, user_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT role FROM group_members WHERE group_id = ? AND user_id = ?', (group_id, user_id))
    member = cursor.fetchone()
    conn.close()
    return member['role'] if member else None


def update_group_member_role(group_id, user_id, new_role):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('UPDATE group_members SET role = ? WHERE group_id = ? AND user_id = ? AND role != "owner"',
                   (new_role, group_id, user_id))
    conn.commit()
    conn.close()
    return True


def delete_group(group_id, user_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT owner_id FROM groups WHERE id = ?', (group_id,))
    group = cursor.fetchone()

    if group and group['owner_id'] == user_id:
        cursor.execute('DELETE FROM groups WHERE id = ?', (group_id,))
        conn.commit()
        conn.close()
        return True

    conn.close()
    return False


def update_group_settings(group_id, **kwargs):
    conn = get_db()
    cursor = conn.cursor()
    for key, value in kwargs.items():
        if value is not None:
            cursor.execute(f'UPDATE groups SET {key} = ? WHERE id = ?', (value, group_id))
    conn.commit()
    conn.close()


def get_group_permissions(group_id, role):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM group_permissions WHERE group_id = ? AND role = ?', (group_id, role))
    perms = cursor.fetchone()
    conn.close()
    return perms


def update_group_permissions(group_id, role, **kwargs):
    conn = get_db()
    cursor = conn.cursor()
    for key, value in kwargs.items():
        if value is not None:
            cursor.execute(f'UPDATE group_permissions SET {key} = ? WHERE group_id = ? AND role = ?',
                           (value, group_id, role))
    conn.commit()
    conn.close()


# ----- КАНАЛЫ -----
def create_channel(name, owner_id, description=None, is_public=True, avatar=None):
    conn = get_db()
    cursor = conn.cursor()
    try:
        import secrets
        invite_link = secrets.token_urlsafe(16)

        cursor.execute('''
            INSERT INTO channels (name, description, owner_id, is_public, invite_link, avatar)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (name, description, owner_id, is_public, invite_link, avatar))

        channel_id = cursor.lastrowid

        cursor.execute('''
            INSERT INTO channel_subscribers (channel_id, user_id)
            VALUES (?, ?)
        ''', (channel_id, owner_id))

        cursor.execute('''
            INSERT INTO channel_admins (channel_id, user_id, can_post, can_edit, can_delete, can_add_admins)
            VALUES (?, ?, 1, 1, 1, 1)
        ''', (channel_id, owner_id))

        conn.commit()
        return channel_id
    except Exception as e:
        print(f"Error creating channel: {e}")
        return None
    finally:
        conn.close()


def get_channel_by_id(channel_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT c.*, u.username as owner_username, u.display_name as owner_display_name,
               (SELECT COUNT(*) FROM channel_subscribers WHERE channel_id = c.id) as subscriber_count
        FROM channels c
        JOIN users u ON c.owner_id = u.id
        WHERE c.id = ?
    ''', (channel_id,))
    channel = cursor.fetchone()
    conn.close()
    return channel


def get_channel_by_invite_link(invite_link):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM channels WHERE invite_link = ?', (invite_link,))
    channel = cursor.fetchone()
    conn.close()
    return channel


def get_user_channels(user_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT c.*,
               (SELECT COUNT(*) FROM channel_subscribers WHERE channel_id = c.id) as subscriber_count
        FROM channels c
        JOIN channel_subscribers cs ON c.id = cs.channel_id
        WHERE cs.user_id = ?
        ORDER BY c.created_at DESC
    ''', (user_id,))
    channels = cursor.fetchall()
    conn.close()
    return channels


def subscribe_to_channel(channel_id, user_id):
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT OR IGNORE INTO channel_subscribers (channel_id, user_id)
            VALUES (?, ?)
        ''', (channel_id, user_id))
        conn.commit()
        return True
    except:
        return False
    finally:
        conn.close()


def unsubscribe_from_channel(channel_id, user_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM channel_subscribers WHERE channel_id = ? AND user_id = ?', (channel_id, user_id))
    conn.commit()
    conn.close()
    return True


def get_channel_subscribers(channel_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT u.id, u.username, u.display_name, u.avatar, cs.subscribed_at
        FROM channel_subscribers cs
        JOIN users u ON cs.user_id = u.id
        WHERE cs.channel_id = ? AND u.is_deleted = 0
        ORDER BY cs.subscribed_at DESC
    ''', (channel_id,))
    subscribers = cursor.fetchall()
    conn.close()
    return subscribers


def is_channel_subscriber(channel_id, user_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT id FROM channel_subscribers WHERE channel_id = ? AND user_id = ?', (channel_id, user_id))
    subscriber = cursor.fetchone()
    conn.close()
    return subscriber is not None


def can_post_in_channel(channel_id, user_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT owner_id FROM channels WHERE id = ?', (channel_id,))
    channel = cursor.fetchone()
    if channel and channel['owner_id'] == user_id:
        return True

    cursor.execute('SELECT can_post FROM channel_admins WHERE channel_id = ? AND user_id = ?', (channel_id, user_id))
    admin = cursor.fetchone()
    conn.close()
    return admin and admin['can_post']


def add_channel_admin(channel_id, user_id, **permissions):
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT OR REPLACE INTO channel_admins (channel_id, user_id, can_post, can_edit, can_delete, can_add_admins)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (channel_id, user_id,
              permissions.get('can_post', 1),
              permissions.get('can_edit', 0),
              permissions.get('can_delete', 0),
              permissions.get('can_add_admins', 0)))
        conn.commit()
        return True
    except:
        return False
    finally:
        conn.close()


def remove_channel_admin(channel_id, user_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM channel_admins WHERE channel_id = ? AND user_id = ?', (channel_id, user_id))
    conn.commit()
    conn.close()
    return True


def delete_channel(channel_id, user_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT owner_id FROM channels WHERE id = ?', (channel_id,))
    channel = cursor.fetchone()

    if channel and channel['owner_id'] == user_id:
        cursor.execute('DELETE FROM channels WHERE id = ?', (channel_id,))
        conn.commit()
        conn.close()
        return True

    conn.close()
    return False


def update_channel_settings(channel_id, **kwargs):
    conn = get_db()
    cursor = conn.cursor()
    for key, value in kwargs.items():
        if value is not None:
            cursor.execute(f'UPDATE channels SET {key} = ? WHERE id = ?', (value, channel_id))
    conn.commit()
    conn.close()


# ----- СООБЩЕНИЯ -----
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

    pinned_ids = get_pinned_chats(user_id)
    pinned_ids_str = ','.join(map(str, pinned_ids)) if pinned_ids else '0'

    cursor.execute(f'''
        SELECT 
            'personal' as chat_type,
            c.id as chat_id, 
            CASE WHEN c.user1_id = ? THEN c.user2_id ELSE c.user1_id END as other_user_id,
            CASE WHEN c.user1_id = c.user2_id THEN 'Избранное'
                 ELSE COALESCE(cn.name, u.display_name, u.username) END as name,
            u.avatar,
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
        WHERE (c.user1_id = ? OR c.user2_id = ?) AND u.is_deleted = 0
    ''', (user_id, user_id, user_id, user_id, user_id, user_id))

    personal_chats = cursor.fetchall()

    cursor.execute('''
        SELECT 
            'group' as chat_type,
            g.id as chat_id,
            g.id as group_id,
            g.name,
            g.avatar,
            NULL as last_seen,
            m.content as last_message,
            m.file_type as last_file_type,
            m.created_at as last_message_time,
            0 as unread_count,
            0 as is_pinned,
            (SELECT COUNT(*) FROM group_members WHERE group_id = g.id) as member_count
        FROM groups g
        JOIN group_members gm ON g.id = gm.group_id
        LEFT JOIN messages m ON m.id = (SELECT id FROM messages WHERE group_id = g.id AND is_deleted = 0 ORDER BY created_at DESC LIMIT 1)
        WHERE gm.user_id = ?
        ORDER BY m.created_at DESC
    ''', (user_id,))

    group_chats = cursor.fetchall()

    cursor.execute('''
        SELECT 
            'channel' as chat_type,
            c.id as chat_id,
            c.id as channel_id,
            c.name,
            c.avatar,
            NULL as last_seen,
            m.content as last_message,
            m.file_type as last_file_type,
            m.created_at as last_message_time,
            0 as unread_count,
            0 as is_pinned,
            (SELECT COUNT(*) FROM channel_subscribers WHERE channel_id = c.id) as subscriber_count
        FROM channels c
        JOIN channel_subscribers cs ON c.id = cs.channel_id
        LEFT JOIN messages m ON m.id = (SELECT id FROM messages WHERE channel_id = c.id AND is_deleted = 0 ORDER BY created_at DESC LIMIT 1)
        WHERE cs.user_id = ?
        ORDER BY m.created_at DESC
    ''', (user_id,))

    channel_chats = cursor.fetchall()

    conn.close()

    all_chats = []
    for chat in personal_chats:
        all_chats.append(dict(chat))
    for chat in group_chats:
        all_chats.append(dict(chat))
    for chat in channel_chats:
        all_chats.append(dict(chat))

    def get_sort_key(chat):
        time_val = chat.get('last_message_time')
        if time_val is None or time_val == '':
            return datetime.min
        if isinstance(time_val, str):
            try:
                return datetime.fromisoformat(time_val.replace('Z', '+00:00'))
            except:
                return datetime.min
        return time_val

    all_chats.sort(key=get_sort_key, reverse=True)
    return all_chats


def send_message(chat_id=None, group_id=None, channel_id=None, sender_id=None, content=None,
                 file_type=None, file_path=None, file_name=None, file_size=None,
                 reply_to_id=None, forwarded_from_id=None, forwarded_from_user_id=None,
                 forwarded_from_username=None, forwarded_from_display_name=None):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO messages (chat_id, group_id, channel_id, sender_id, content, file_type, file_path, file_name, file_size,
                             reply_to_id, forwarded_from_id, forwarded_from_user_id, forwarded_from_username, forwarded_from_display_name)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (chat_id, group_id, channel_id, sender_id, content, file_type, file_path, file_name, file_size,
          reply_to_id, forwarded_from_id, forwarded_from_user_id, forwarded_from_username, forwarded_from_display_name))
    conn.commit()
    message_id = cursor.lastrowid

    cursor.execute('''
        SELECT m.*, u.username, u.display_name, u.avatar 
        FROM messages m
        LEFT JOIN users u ON m.sender_id = u.id
        WHERE m.id = ?
    ''', (message_id,))
    message = cursor.fetchone()
    conn.close()
    return message


def get_messages(chat_id=None, group_id=None, channel_id=None, user_id=None, limit=100, offset=0):
    conn = get_db()
    cursor = conn.cursor()

    if chat_id:
        cursor.execute('UPDATE messages SET is_read = 1 WHERE chat_id = ? AND sender_id != ?', (chat_id, user_id))

    query = '''
        SELECT m.*, u.username, u.display_name, u.avatar,
               r.content as reply_content, r.sender_id as reply_sender_id,
               ru.username as reply_username, ru.display_name as reply_display_name
        FROM messages m
        LEFT JOIN users u ON m.sender_id = u.id
        LEFT JOIN messages r ON m.reply_to_id = r.id
        LEFT JOIN users ru ON r.sender_id = ru.id
        WHERE m.is_deleted = 0
    '''
    params = []

    if chat_id:
        query += ' AND m.chat_id = ?'
        params.append(chat_id)
    elif group_id:
        query += ' AND m.group_id = ?'
        params.append(group_id)
    elif channel_id:
        query += ' AND m.channel_id = ?'
        params.append(channel_id)

    query += ' ORDER BY m.created_at ASC LIMIT ? OFFSET ?'
    params.extend([limit, offset])

    cursor.execute(query, params)
    messages = cursor.fetchall()
    conn.commit()
    conn.close()
    return messages


def forward_message(message_id, to_chat_id=None, to_group_id=None, to_channel_id=None, sender_id=None):
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute('SELECT * FROM messages WHERE id = ?', (message_id,))
    msg = cursor.fetchone()

    if msg:
        forward_user = get_user_by_id(msg['sender_id'])
        cursor.execute('''
            INSERT INTO messages (chat_id, group_id, channel_id, sender_id, content, file_type, file_path, file_name, file_size,
                                 forwarded_from_id, forwarded_from_user_id, forwarded_from_username, forwarded_from_display_name)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (to_chat_id, to_group_id, to_channel_id, sender_id, msg['content'], msg['file_type'],
              msg['file_path'], msg['file_name'], msg['file_size'], msg['id'], msg['sender_id'],
              forward_user['username'] if forward_user else None,
              forward_user['display_name'] if forward_user else None))
        conn.commit()
        new_id = cursor.lastrowid
        conn.close()
        return new_id
    conn.close()
    return None


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


# ----- РЕАКЦИИ (максимум 3 на пользователя) -----
def add_reaction(message_id, user_id, reaction):
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute('SELECT reaction FROM message_reactions WHERE message_id = ? AND user_id = ?',
                       (message_id, user_id))
        user_reactions = [row['reaction'] for row in cursor.fetchall()]

        if reaction in user_reactions:
            cursor.execute('DELETE FROM message_reactions WHERE message_id = ? AND user_id = ? AND reaction = ?',
                           (message_id, user_id, reaction))
        else:
            if len(user_reactions) >= 3:
                cursor.execute('''
                    DELETE FROM message_reactions 
                    WHERE message_id = ? AND user_id = ? AND created_at = (
                        SELECT MIN(created_at) FROM message_reactions 
                        WHERE message_id = ? AND user_id = ?
                    )
                ''', (message_id, user_id, message_id, user_id))

            cursor.execute('''
                INSERT INTO message_reactions (message_id, user_id, reaction)
                VALUES (?, ?, ?)
            ''', (message_id, user_id, reaction))

        conn.commit()
        return True
    except Exception as e:
        print(f"Reaction error: {e}")
        return False
    finally:
        conn.close()


def get_message_reactions(message_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT reaction, COUNT(*) as count,
               GROUP_CONCAT(user_id) as user_ids
        FROM message_reactions
        WHERE message_id = ?
        GROUP BY reaction
    ''', (message_id,))
    reactions = cursor.fetchall()
    conn.close()
    return reactions


def get_user_reactions(message_id, user_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT reaction FROM message_reactions WHERE message_id = ? AND user_id = ?', (message_id, user_id))
    reactions = [row['reaction'] for row in cursor.fetchall()]
    conn.close()
    return reactions


# ----- ИСТОРИИ -----
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

    cursor.execute('''
        SELECT s.*, u.username, u.display_name, u.avatar,
               (SELECT COUNT(*) FROM story_interactions WHERE story_id = s.id AND type='like') as likes_count,
               (SELECT COUNT(*) FROM story_interactions WHERE story_id = s.id AND type='view') as views_count,
               (SELECT COUNT(*) FROM story_reactions WHERE story_id = s.id) as reactions_count
        FROM stories s
        JOIN users u ON s.user_id = u.id
        WHERE s.expires_at > datetime('now')
          AND u.is_deleted = 0
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
        ORDER BY 
            CASE WHEN s.user_id = ? THEN 0 ELSE 1 END,
            s.created_at DESC
    ''', (viewer_id, viewer_id, viewer_id, viewer_id, viewer_id))

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
        pass
    finally:
        conn.close()


def add_story_reaction(story_id, user_id, reaction):
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT OR IGNORE INTO story_reactions (story_id, user_id, reaction)
            VALUES (?, ?, ?)
        ''', (story_id, user_id, reaction))
        conn.commit()
        return True
    except:
        return False
    finally:
        conn.close()


def add_story_view(story_id, user_id):
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT OR IGNORE INTO story_views (story_id, user_id)
            VALUES (?, ?)
        ''', (story_id, user_id))
        conn.commit()
    except:
        pass
    finally:
        conn.close()


def get_story_reactions(story_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT reaction, COUNT(*) as count
        FROM story_reactions
        WHERE story_id = ?
        GROUP BY reaction
    ''', (story_id,))
    reactions = cursor.fetchall()
    conn.close()
    return reactions


def delete_expired_stories():
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute('SELECT file_path, music FROM stories WHERE expires_at < datetime("now")')
    expired = cursor.fetchall()

    for story in expired:
        for path in [story['file_path'], story['music']]:
            if path:
                try:
                    full_path = os.path.join('static', path)
                    if os.path.exists(full_path):
                        os.remove(full_path)
                except:
                    pass

    cursor.execute('DELETE FROM stories WHERE expires_at < datetime("now")')
    deleted = cursor.rowcount
    conn.commit()
    conn.close()
    return deleted


def get_story_viewers(story_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT u.id, u.username, u.display_name, u.avatar, sv.viewed_at
        FROM story_views sv
        JOIN users u ON sv.user_id = u.id
        WHERE sv.story_id = ?
        ORDER BY sv.viewed_at DESC
    ''', (story_id,))
    viewers = cursor.fetchall()
    conn.close()
    return viewers


def get_story_likes(story_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT u.id, u.username, u.display_name, u.avatar
        FROM story_interactions si
        JOIN users u ON si.user_id = u.id
        WHERE si.story_id = ? AND si.type = 'like'
    ''', (story_id,))
    likes = cursor.fetchall()
    conn.close()
    return likes


# ----- ЗАКРЕПЛЕННЫЕ ЧАТЫ -----
def pin_chat(user_id, chat_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('INSERT OR REPLACE INTO pinned_chats (user_id, chat_id, pinned_at) VALUES (?, ?, ?)',
                   (user_id, chat_id, datetime.now()))
    conn.commit()
    conn.close()


def unpin_chat(user_id, chat_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM pinned_chats WHERE user_id = ? AND chat_id = ?', (user_id, chat_id))
    conn.commit()
    conn.close()


def get_pinned_chats(user_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT chat_id FROM pinned_chats WHERE user_id = ? ORDER BY pinned_at DESC', (user_id,))
    pinned = [row['chat_id'] for row in cursor.fetchall()]
    conn.close()
    return pinned


# ----- ВИДЕОЗВОНКИ -----
def create_video_call(room_id, creator_id, call_type='video'):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO video_calls (room_id, creator_id, call_type)
        VALUES (?, ?, ?)
    ''', (room_id, creator_id, call_type))
    conn.commit()
    call_id = cursor.lastrowid

    cursor.execute('''
        INSERT INTO video_call_participants (call_id, user_id)
        VALUES (?, ?)
    ''', (call_id, creator_id))
    conn.commit()
    conn.close()
    return call_id


def add_video_call_participant(room_id, user_id, audio_only=False):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT id FROM video_calls WHERE room_id = ? AND status = "active"', (room_id,))
    call = cursor.fetchone()

    if call:
        cursor.execute('''
            INSERT OR IGNORE INTO video_call_participants (call_id, user_id, audio_only)
            VALUES (?, ?, ?)
        ''', (call['id'], user_id, audio_only))
        cursor.execute('''
            UPDATE video_calls 
            SET participant_count = (SELECT COUNT(*) FROM video_call_participants WHERE call_id = ? AND left_at IS NULL)
            WHERE id = ?
        ''', (call['id'], call['id']))
        conn.commit()

    conn.close()
    return call['id'] if call else None


def remove_video_call_participant(room_id, user_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT id FROM video_calls WHERE room_id = ? AND status = "active"', (room_id,))
    call = cursor.fetchone()

    if call:
        cursor.execute('''
            UPDATE video_call_participants 
            SET left_at = ?
            WHERE call_id = ? AND user_id = ?
        ''', (datetime.now(), call['id'], user_id))
        conn.commit()
    conn.close()


def end_video_call(room_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT id, started_at FROM video_calls WHERE room_id = ? AND status = "active"', (room_id,))
    call = cursor.fetchone()

    if call:
        duration = 0
        if call['started_at']:
            started = datetime.fromisoformat(call['started_at']) if isinstance(call['started_at'], str) else call[
                'started_at']
            duration = int((datetime.now() - started).total_seconds())

        cursor.execute('''
            UPDATE video_calls 
            SET status = "ended", ended_at = ?, duration = ?
            WHERE id = ?
        ''', (datetime.now(), duration, call['id']))
        cursor.execute('''
            UPDATE video_call_participants 
            SET left_at = ?
            WHERE call_id = ? AND left_at IS NULL
        ''', (datetime.now(), call['id']))
        conn.commit()
    conn.close()


def get_active_video_call(room_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM video_calls WHERE room_id = ? AND status = "active"', (room_id,))
    call = cursor.fetchone()
    conn.close()
    return call


def get_video_call_participants(room_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT u.id, u.username, u.display_name, u.avatar, vcp.audio_only, vcp.screensharing, vcp.joined_at
        FROM video_calls vc
        JOIN video_call_participants vcp ON vc.id = vcp.call_id
        JOIN users u ON vcp.user_id = u.id
        WHERE vc.room_id = ? AND vcp.left_at IS NULL
    ''', (room_id,))
    participants = cursor.fetchall()
    conn.close()
    return participants


# ----- ПОИСК -----
def search_groups(query, current_user_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT g.*, 
               (SELECT COUNT(*) FROM group_members WHERE group_id = g.id) as member_count,
               EXISTS(SELECT 1 FROM group_members WHERE group_id = g.id AND user_id = ?) as is_member
        FROM groups g
        WHERE g.name LIKE ? AND g.is_public = 1
        LIMIT 20
    ''', (current_user_id, f'%{query}%'))
    groups = cursor.fetchall()
    conn.close()
    return groups


def search_channels(query, current_user_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT c.*, 
               (SELECT COUNT(*) FROM channel_subscribers WHERE channel_id = c.id) as subscriber_count,
               EXISTS(SELECT 1 FROM channel_subscribers WHERE channel_id = c.id AND user_id = ?) as is_subscribed
        FROM channels c
        WHERE c.name LIKE ? AND c.is_public = 1
        LIMIT 20
    ''', (current_user_id, f'%{query}%'))
    channels = cursor.fetchall()
    conn.close()
    return channels


def add_recent_search(user_id, query, search_type='all'):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO recent_searches (user_id, search_query, search_type)
        VALUES (?, ?, ?)
    ''', (user_id, query, search_type))
    conn.commit()
    conn.close()


def get_recent_searches(user_id, limit=10):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT DISTINCT search_query, search_type, MAX(created_at) as last_searched
        FROM recent_searches
        WHERE user_id = ?
        GROUP BY search_query
        ORDER BY last_searched DESC
        LIMIT ?
    ''', (user_id, limit))
    searches = cursor.fetchall()
    conn.close()
    return searches


# ----- ЗВОНКИ -----
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
               CASE WHEN c.caller_id = ? THEN u2.display_name ELSE u1.display_name END as contact_name,
               CASE WHEN c.caller_id = ? THEN u2.username ELSE u1.username END as contact_username,
               CASE WHEN c.caller_id = ? THEN u2.id ELSE u1.id END as contact_id,
               c.caller_id = ? as is_outgoing
        FROM calls c
        JOIN users u1 ON c.caller_id = u1.id
        JOIN users u2 ON c.receiver_id = u2.id
        WHERE (c.caller_id = ? OR c.receiver_id = ?)
          AND (c.caller_id != c.receiver_id)
        ORDER BY c.created_at DESC
        LIMIT 50
    ''', (user_id, user_id, user_id, user_id, user_id, user_id))
    calls = cursor.fetchall()
    conn.close()
    return calls


# ----- КОНТАКТЫ -----
def get_contacts(user_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT u.*, cn.name as custom_name 
        FROM contacts c
        JOIN users u ON c.contact_id = u.id
        LEFT JOIN contact_names cn ON cn.user_id = ? AND cn.contact_id = u.id
        WHERE c.user_id = ? AND u.is_deleted = 0
        ORDER BY COALESCE(cn.name, u.display_name, u.username)
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


# ----- ИЗБРАННОЕ -----
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


# ----- СЕССИИ -----
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


# ----- ПРЕДЗАГРУЗОЧНЫЕ АВАТАРКИ -----
def get_preloaded_avatars():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM preloaded_avatars WHERE category != "system" ORDER BY id')
    avatars = cursor.fetchall()
    conn.close()
    return avatars


def get_deleted_avatar():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT filename FROM preloaded_avatars WHERE filename = "deleted.png"')
    avatar = cursor.fetchone()
    conn.close()
    return avatar['filename'] if avatar else 'static/avatar-swg/deleted.png'


# ----- НАСТРОЙКИ -----
def get_user_settings(user_id):
    user = get_user_by_id(user_id)
    if not user:
        return None
    return {
        'theme': user['theme'],
        'font_size': user['font_size'],
        'bubble_radius': user['bubble_radius'],
        'font_family': user['font_family'],
        'my_message_color': user['my_message_color'],
        'their_message_color': user['their_message_color'],
        'wallpaper': user['wallpaper'],
        'wallpaper_image': user['wallpaper_image']
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


# ----- НОВЫЕ ФУНКЦИИ ДЛЯ СТАТИСТИКИ ИСТОРИЙ И ПОИСКА В ЧАТЕ -----
def get_story_stats(story_id, user_id):
    """Получает полную статистику по истории (только для владельца)"""
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute('SELECT user_id FROM stories WHERE id = ?', (story_id,))
    story = cursor.fetchone()

    if not story or story['user_id'] != user_id:
        conn.close()
        return None

    cursor.execute('''
        SELECT u.id, u.unique_id, u.username, u.display_name, u.avatar, sv.viewed_at
        FROM story_views sv
        JOIN users u ON sv.user_id = u.id
        WHERE sv.story_id = ?
        ORDER BY sv.viewed_at DESC
    ''', (story_id,))
    viewers = cursor.fetchall()

    cursor.execute('''
        SELECT u.id, u.unique_id, u.username, u.display_name, u.avatar, si.created_at
        FROM story_interactions si
        JOIN users u ON si.user_id = u.id
        WHERE si.story_id = ? AND si.type = 'like'
        ORDER BY si.created_at DESC
    ''', (story_id,))
    likes = cursor.fetchall()

    cursor.execute('''
        SELECT u.id, u.unique_id, u.username, u.display_name, u.avatar, sr.reaction, sr.created_at
        FROM story_reactions sr
        JOIN users u ON sr.user_id = u.id
        WHERE sr.story_id = ?
        ORDER BY sr.created_at DESC
    ''', (story_id,))
    reactions = cursor.fetchall()

    cursor.execute('''
        SELECT u.id, u.unique_id, u.username, u.display_name, u.avatar, si.reply_text, si.created_at
        FROM story_interactions si
        JOIN users u ON si.user_id = u.id
        WHERE si.story_id = ? AND si.type = 'reply' AND si.reply_text IS NOT NULL
        ORDER BY si.created_at DESC
    ''', (story_id,))
    replies = cursor.fetchall()

    conn.close()

    return {
        'viewers': [dict(v) for v in viewers],
        'likes': [dict(l) for l in likes],
        'reactions': [dict(r) for r in reactions],
        'replies': [dict(r) for r in replies],
        'total_views': len(viewers),
        'total_likes': len(likes),
        'total_reactions': len(reactions),
        'total_replies': len(replies)
    }


def get_story_by_id(story_id):
    """Получает историю по ID"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT s.*, u.username, u.display_name, u.avatar
        FROM stories s
        JOIN users u ON s.user_id = u.id
        WHERE s.id = ?
    ''', (story_id,))
    story = cursor.fetchone()
    conn.close()
    return story


def search_messages_in_chat(chat_id, user_id, query):
    """Поиск сообщений в чате по ключевому слову"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT m.*, u.username, u.display_name, u.avatar,
               CASE WHEN m.sender_id = ? THEN 1 ELSE 0 END as is_mine
        FROM messages m
        LEFT JOIN users u ON m.sender_id = u.id
        WHERE m.chat_id = ? 
          AND m.is_deleted = 0
          AND (m.content LIKE ? OR m.file_name LIKE ?)
        ORDER BY m.created_at DESC
        LIMIT 100
    ''', (user_id, chat_id, f'%{query}%', f'%{query}%'))
    messages = cursor.fetchall()
    conn.close()
    return messages


# Инициализация БД при импорте
init_db()