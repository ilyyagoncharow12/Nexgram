import os
import uuid
import re
import secrets
from datetime import datetime, timedelta
from flask import Flask, render_template, request, redirect, url_for, session, jsonify, send_file
from flask_socketio import SocketIO, emit, join_room, leave_room
from werkzeug.utils import secure_filename
from PIL import Image

from database import (
    get_db, init_db, hash_password, resize_and_crop_image, generate_unique_id,
    create_user_initial, complete_registration, check_phone_exists, check_username_available,
    get_user_by_id, get_user_by_unique_id, get_user_by_username, get_user_by_phone,
    verify_user, update_last_seen, update_user_settings, delete_user_account,
    get_or_create_chat, get_user_chats, send_message, get_messages,
    edit_message, delete_message, forward_message,
    get_contacts, add_contact, rename_contact, search_users,
    add_to_favorites, get_favorites,
    add_call, update_call_status, get_call_history,
    add_session, get_user_sessions, delete_session, delete_all_sessions_except,
    create_story, get_stories_for_user, add_story_interaction, add_story_reaction, add_story_view,
    get_story_likes, get_story_viewers, get_story_reactions, delete_expired_stories,
    get_user_settings, get_privacy_settings, update_privacy_settings,
    pin_chat, unpin_chat, get_pinned_chats,
    create_group, get_group_by_id, get_group_by_invite_link, get_user_groups,
    add_group_member, remove_group_member, get_group_members, is_group_member, delete_group,
    update_group_member_role, update_group_settings, get_group_permissions, update_group_permissions,
    create_channel, get_channel_by_id, get_channel_by_invite_link, get_user_channels,
    subscribe_to_channel, unsubscribe_from_channel, get_channel_subscribers,
    is_channel_subscriber, can_post_in_channel, delete_channel, add_channel_admin,
    remove_channel_admin, update_channel_settings,
    add_reaction, get_message_reactions, get_user_reactions,
    search_groups, search_channels, add_recent_search, get_recent_searches,
    create_video_call, add_video_call_participant, remove_video_call_participant,
    end_video_call, get_active_video_call, get_video_call_participants,
    get_preloaded_avatars, get_deleted_avatar,
    block_user, unblock_user, is_user_blocked, get_blocked_users, get_user_profile, clear_chat, reply_to_story
)

app = Flask(__name__)
app.config['SECRET_KEY'] = 'swillgram-secret-key-v3'
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=30)

socketio = SocketIO(app, cors_allowed_origins="*", ping_timeout=60, ping_interval=25)

# Создаём папки
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(os.path.join(app.config['UPLOAD_FOLDER'], 'avatars'), exist_ok=True)
os.makedirs(os.path.join(app.config['UPLOAD_FOLDER'], 'files'), exist_ok=True)
os.makedirs(os.path.join(app.config['UPLOAD_FOLDER'], 'photos'), exist_ok=True)
os.makedirs(os.path.join(app.config['UPLOAD_FOLDER'], 'videos'), exist_ok=True)
os.makedirs(os.path.join(app.config['UPLOAD_FOLDER'], 'audio'), exist_ok=True)
os.makedirs(os.path.join(app.config['UPLOAD_FOLDER'], 'wallpapers'), exist_ok=True)
os.makedirs(os.path.join(app.config['UPLOAD_FOLDER'], 'stories'), exist_ok=True)
os.makedirs(os.path.join(app.config['UPLOAD_FOLDER'], 'story_music'), exist_ok=True)
os.makedirs(os.path.join('static', 'avatar-swg'), exist_ok=True)

# Копируем аватарки если их нет
default_avatar_files = ['avatar1.jpg', 'avatar2.jpg', 'avatar3.jpg', 'avatar4.jpg',
                        'avatar5.png', 'avatar6.png', 'avatar7.png', 'avatar8.png', 'deleted.png']
for ava in default_avatar_files:
    ava_path = os.path.join('static', 'avatar-swg', ava)
    if not os.path.exists(ava_path):
        from PIL import Image, ImageDraw

        img = Image.new('RGB', (500, 500), color='#667eea')
        draw = ImageDraw.Draw(img)
        draw.text((250, 250), ava.split('.')[0][6:], fill='white', anchor='mm')
        img.save(ava_path)

video_rooms = {}


def generate_room_id():
    return secrets.token_urlsafe(12)[:16]


# ---------------------- ЕДИНАЯ АВТОРИЗАЦИЯ ----------------------
@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('chat_page'))
    return redirect(url_for('auth'))


@app.route('/auth', methods=['GET', 'POST'])
def auth():
    """Единая страница входа и начала регистрации"""
    if request.method == 'POST':
        action = request.form.get('action')
        phone = request.form.get('phone')
        password = request.form.get('password')
        remember = request.form.get('remember')

        if action == 'login':
            user = verify_user(phone, password)
            if user:
                if user['is_deleted']:
                    return render_template('auth.html', error='Аккаунт удалён', mode='login')
                if not user['registration_complete']:
                    session['temp_user_id'] = user['id']
                    session['temp_phone'] = user['phone']
                    return redirect(url_for('complete_registration_page'))
                return complete_login(user, remember)
            return render_template('auth.html', error='Неверный логин или пароль', mode='login')

        elif action == 'check_phone':
            existing = check_phone_exists(phone)
            if existing:
                return jsonify({'exists': True, 'registration_complete': existing['registration_complete']})
            return jsonify({'exists': False})

        elif action == 'register_step1':
            if len(password) < 8:
                return render_template('auth.html', error='Пароль минимум 8 символов', mode='register', phone=phone)

            existing = check_phone_exists(phone)
            if existing:
                if existing['registration_complete']:
                    return render_template('auth.html', error='Пользователь уже существует', mode='login')
                else:
                    session['temp_user_id'] = existing['id']
                    session['temp_phone'] = phone
                    return redirect(url_for('complete_registration_page'))

            user_id = create_user_initial(phone, password)
            if user_id:
                session['temp_user_id'] = user_id
                session['temp_phone'] = phone
                return redirect(url_for('complete_registration_page'))
            return render_template('auth.html', error='Ошибка регистрации', mode='register')

    mode = request.args.get('mode', 'login')
    return render_template('auth.html', mode=mode)


def complete_login(user, remember=False):
    session['user_id'] = user['id']
    session['unique_id'] = user['unique_id']
    session['username'] = user['username']
    session['display_name'] = user['display_name'] or user['username']
    session['phone'] = user['phone']

    if remember:
        session.permanent = True

    update_last_seen(user['id'])
    session_token = str(uuid.uuid4())
    add_session(user['id'], session_token, request.headers.get('User-Agent', 'Unknown'), request.remote_addr)
    session['session_token'] = session_token
    return redirect(url_for('chat_page'))


@app.route('/complete-registration', methods=['GET', 'POST'])
def complete_registration_page():
    """Второй этап - выбор username, display_name и аватарки"""
    if 'temp_user_id' not in session:
        return redirect(url_for('auth'))

    avatars = get_preloaded_avatars()

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        display_name = request.form.get('display_name', '').strip()
        avatar = request.form.get('avatar', '')

        if len(username) < 3:
            return render_template('complete_registration.html', avatars=avatars,
                                   error='Имя пользователя минимум 3 символа')
        if not re.match(r'^[a-zA-Z0-9_]+$', username):
            return render_template('complete_registration.html', avatars=avatars, error='Только латиница, цифры и _')
        if not check_username_available(username):
            return render_template('complete_registration.html', avatars=avatars, error='Имя пользователя занято')

        if complete_registration(session['temp_user_id'], username, display_name, avatar):
            user = get_user_by_id(session['temp_user_id'])
            session.clear()
            return complete_login(user)

        return render_template('complete_registration.html', avatars=avatars, error='Ошибка')

    return render_template('complete_registration.html', avatars=avatars)


@app.route('/logout')
def logout():
    if 'user_id' in session:
        update_last_seen(session['user_id'])
        if 'session_token' in session:
            delete_session(session['session_token'])
    session.clear()
    return redirect(url_for('auth'))


# ---------------------- ЧАТ ----------------------
@app.route('/chat')
def chat_page():
    if 'user_id' not in session:
        return redirect(url_for('auth'))

    user = get_user_by_id(session['user_id'])
    if not user or user['is_deleted']:
        session.clear()
        return redirect(url_for('auth'))

    chats = get_user_chats(session['user_id'])
    contacts = get_contacts(session['user_id'])
    call_history = get_call_history(session['user_id'])
    favorites = get_favorites(session['user_id'])
    groups = get_user_groups(session['user_id'])
    channels = get_user_channels(session['user_id'])
    avatars = get_preloaded_avatars()

    return render_template('chat.html',
                           user=dict(user),
                           chats=[dict(chat) for chat in chats] if chats else [],
                           contacts=[dict(c) for c in contacts] if contacts else [],
                           call_history=[dict(c) for c in call_history] if call_history else [],
                           favorites=[dict(f) for f in favorites] if favorites else [],
                           groups=[dict(group) for group in groups] if groups else [],
                           channels=[dict(channel) for channel in channels] if channels else [],
                           avatars=[dict(a) for a in avatars] if avatars else [])


# ---------------------- API МАРШРУТЫ ----------------------
@app.route('/api/check_username', methods=['POST'])
def api_check_username():
    if 'user_id' not in session and 'temp_user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    data = request.get_json()
    username = data.get('username', '').strip()

    if len(username) < 3:
        return jsonify({'available': False, 'error': 'Минимум 3 символа'})

    if not re.match(r'^[a-zA-Z0-9_]+$', username):
        return jsonify({'available': False, 'error': 'Только латиница, цифры и _'})

    current_id = session.get('user_id') or session.get('temp_user_id')
    available = check_username_available(username, current_id)
    return jsonify({'available': available})


@app.route('/api/get_groups')
def api_get_groups():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    groups = get_user_groups(session['user_id'])
    return jsonify([dict(g) for g in groups])


@app.route('/api/get_channels')
def api_get_channels():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    channels = get_user_channels(session['user_id'])
    return jsonify([dict(c) for c in channels])


@app.route('/api/update_last_seen', methods=['POST'])
def api_update_last_seen():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    update_last_seen(session['user_id'])
    return jsonify({'success': True})


@app.route('/api/edit_message', methods=['POST'])
def api_edit_message():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    data = request.get_json()
    message_id = data.get('message_id')
    new_content = data.get('content')

    edit_message(message_id, new_content)

    socketio.emit('message_edited', {
        'message_id': message_id,
        'new_content': new_content
    })

    return jsonify({'success': True})


@app.route('/api/delete_message', methods=['POST'])
def api_delete_message():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    data = request.get_json()
    message_id = data.get('message_id')
    delete_for_all = data.get('delete_for_all', False)

    delete_message(message_id, session['user_id'], delete_for_all)

    socketio.emit('message_deleted', {'message_id': message_id})

    return jsonify({'success': True})


@app.route('/api/clear_chat', methods=['POST'])
def api_clear_chat():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    data = request.get_json()
    chat_id = data.get('chat_id')
    group_id = data.get('group_id')
    channel_id = data.get('channel_id')

    clear_chat(chat_id, group_id, channel_id)

    return jsonify({'success': True})


@app.route('/api/block_user', methods=['POST'])
def api_block_user():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    data = request.get_json()
    blocked_id = data.get('user_id')

    if block_user(session['user_id'], blocked_id):
        socketio.emit('user_blocked', {
            'blocker_id': session['user_id'],
            'blocked_id': blocked_id
        }, room=f"user_{blocked_id}")
        return jsonify({'success': True})
    return jsonify({'success': False}), 400


@app.route('/api/unblock_user', methods=['POST'])
def api_unblock_user():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    data = request.get_json()
    blocked_id = data.get('user_id')

    unblock_user(session['user_id'], blocked_id)
    return jsonify({'success': True})


@app.route('/api/is_user_blocked/<int:user_id>')
def api_is_user_blocked(user_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    is_blocked = is_user_blocked(session['user_id'], user_id)
    return jsonify({'is_blocked': is_blocked})


@app.route('/api/set_username', methods=['POST'])
def api_set_username():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    data = request.get_json()
    username = data.get('username', '').strip()

    if len(username) < 3:
        return jsonify({'success': False, 'error': 'Минимум 3 символа'})

    if not re.match(r'^[a-zA-Z0-9_]+$', username):
        return jsonify({'success': False, 'error': 'Только латиница, цифры и _'})

    if not check_username_available(username, session['user_id']):
        return jsonify({'success': False, 'error': 'Имя занято'})

    update_user_settings(session['user_id'], username=username)
    session['username'] = username

    return jsonify({'success': True, 'username': username})


@app.route('/api/search_all')
def api_search_all():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    query = request.args.get('q', '')
    if len(query) < 2:
        return jsonify({'users': [], 'groups': [], 'channels': []})

    users = search_users(query, session['user_id'])
    groups = search_groups(query, session['user_id'])
    channels = search_channels(query, session['user_id'])

    add_recent_search(session['user_id'], query)

    return jsonify({
        'users': [dict(u) for u in users],
        'groups': [dict(g) for g in groups],
        'channels': [dict(c) for c in channels]
    })


@app.route('/api/recent_searches')
def api_recent_searches():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    searches = get_recent_searches(session['user_id'])
    return jsonify([dict(s) for s in searches])


@app.route('/api/search_users')
def api_search_users():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    query = request.args.get('q', '').strip()
    if len(query) < 2:
        return jsonify([])

    users = search_users(query, session['user_id'])
    return jsonify([dict(u) for u in users])


@app.route('/api/get_chats_list')
def api_get_chats_list():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    chats = get_user_chats(session['user_id'])
    return jsonify(chats)


@app.route('/api/get_group/<int:group_id>')
def api_get_group(group_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    if not is_group_member(group_id, session['user_id']):
        return jsonify({'error': 'Not a member'}), 403

    group = get_group_by_id(group_id)
    messages = get_messages(group_id=group_id, user_id=session['user_id'])
    members = get_group_members(group_id)
    permissions = get_group_permissions(group_id, is_group_member(group_id, session['user_id']))

    return jsonify({
        'group': dict(group) if group else None,
        'messages': [dict(m) for m in messages],
        'members': [dict(m) for m in members],
        'user_role': is_group_member(group_id, session['user_id']),
        'permissions': dict(permissions) if permissions else None
    })


@app.route('/api/get_channel/<int:channel_id>')
def api_get_channel(channel_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    if not is_channel_subscriber(channel_id, session['user_id']):
        return jsonify({'error': 'Not subscribed'}), 403

    channel = get_channel_by_id(channel_id)
    messages = get_messages(channel_id=channel_id, user_id=session['user_id'])
    subscribers = get_channel_subscribers(channel_id)

    return jsonify({
        'channel': dict(channel) if channel else None,
        'messages': [dict(m) for m in messages],
        'subscribers': [dict(s) for s in subscribers],
        'can_post': can_post_in_channel(channel_id, session['user_id'])
    })


# main.py

@app.route('/api/get_chat/<int:user_id>')
def api_get_chat(user_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    current_user_id = session['user_id']

    chat_id = get_or_create_chat(current_user_id, user_id)
    messages = get_messages(chat_id=chat_id, user_id=current_user_id)

    # Проверяем, это чат с самим собой (Избранное)?
    if user_id == current_user_id:
        my_user = get_user_by_id(current_user_id)
        return jsonify({
            'chat_id': chat_id,
            'is_favorites': True,
            'other_user': {
                'id': current_user_id,
                'unique_id': my_user['unique_id'],
                'username': my_user['username'],
                'display_name': 'Избранное',
                'avatar': my_user['avatar'],
                'is_favorites': True
            },
            'messages': [dict(m) for m in messages]
        })

    # Обычный чат с другим пользователем
    other_user = get_user_profile(user_id, current_user_id)
    if not other_user:
        return jsonify({'error': 'User not found'}), 404

    return jsonify({
        'chat_id': chat_id,
        'is_favorites': False,
        'other_user': other_user,
        'messages': [dict(m) for m in messages]
    })


@app.route('/api/send_message', methods=['POST'])
def api_send_message():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    try:
        chat_id = request.form.get('chat_id')
        group_id = request.form.get('group_id')
        channel_id = request.form.get('channel_id')
        content = request.form.get('content', '')
        reply_to_id = request.form.get('reply_to_id')

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

        message = send_message(
            chat_id=chat_id,
            group_id=group_id,
            channel_id=channel_id,
            sender_id=session['user_id'],
            content=content,
            file_type=file_type,
            file_path=file_path,
            file_name=file_name,
            file_size=file_size,
            reply_to_id=reply_to_id
        )

        if message:
            room = f"chat_{chat_id}" if chat_id else f"group_{group_id}" if group_id else f"channel_{channel_id}"
            socketio.emit('new_message', {'room': room, 'message': dict(message)}, room=room)

        return jsonify({'success': True, 'message': dict(message) if message else None})
    except Exception as e:
        print(f"Error sending message: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/forward_message', methods=['POST'])
def api_forward_message():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    data = request.get_json()
    message_id = data.get('message_id')
    to_chat_id = data.get('to_chat_id')
    to_group_id = data.get('to_group_id')
    to_channel_id = data.get('to_channel_id')

    # Если пересылаем в личный чат, нужно получить или создать chat_id
    if to_chat_id:
        # to_chat_id здесь - это ID пользователя, с которым чат
        chat_id = get_or_create_chat(session['user_id'], to_chat_id)
        new_id = forward_message(
            message_id=message_id,
            to_chat_id=chat_id,
            to_group_id=None,
            to_channel_id=None,
            sender_id=session['user_id']
        )
    else:
        new_id = forward_message(
            message_id=message_id,
            to_chat_id=None,
            to_group_id=to_group_id,
            to_channel_id=to_channel_id,
            sender_id=session['user_id']
        )

    if new_id:
        # Отправляем уведомление через сокет
        if to_chat_id:
            socketio.emit('new_message', {'chat_id': chat_id}, room=f"chat_{chat_id}")
        elif to_group_id:
            socketio.emit('new_message', {'group_id': to_group_id}, room=f"group_{to_group_id}")
        elif to_channel_id:
            socketio.emit('new_message', {'channel_id': to_channel_id}, room=f"channel_{to_channel_id}")

        return jsonify({'success': True, 'message_id': new_id})

    return jsonify({'success': False}), 400


@app.route('/api/add_reaction', methods=['POST'])
def api_add_reaction():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    data = request.get_json()
    message_id = data.get('message_id')
    reaction = data.get('reaction')

    add_reaction(message_id, session['user_id'], reaction)

    socketio.emit('reaction_update', {
        'message_id': message_id,
        'reactions': [dict(r) for r in get_message_reactions(message_id)]
    })

    return jsonify({'success': True})


@app.route('/api/get_reactions/<int:message_id>')
def api_get_reactions(message_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    reactions = get_message_reactions(message_id)
    user_reactions = get_user_reactions(message_id, session['user_id'])

    return jsonify({
        'reactions': [dict(r) for r in reactions],
        'user_reactions': user_reactions
    })


# ---------------------- ГРУППЫ ----------------------
@app.route('/api/create_group', methods=['POST'])
def api_create_group():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    data = request.get_json()
    name = data.get('name')
    description = data.get('description')
    is_public = data.get('is_public', True)

    if not name:
        return jsonify({'success': False, 'error': 'Название обязательно'}), 400

    group_id = create_group(name, session['user_id'], description, is_public)

    if group_id:
        return jsonify({'success': True, 'group_id': group_id})

    return jsonify({'success': False, 'error': 'Ошибка создания'}), 500


@app.route('/api/update_group/<int:group_id>', methods=['POST'])
def api_update_group(group_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    role = is_group_member(group_id, session['user_id'])
    if role not in ['owner', 'admin']:
        return jsonify({'success': False, 'error': 'Недостаточно прав'}), 403

    data = request.get_json()
    updates = {}
    if 'name' in data:
        updates['name'] = data['name']
    if 'description' in data:
        updates['description'] = data['description']
    if 'is_public' in data:
        updates['is_public'] = data['is_public']

    if updates:
        update_group_settings(group_id, **updates)

    return jsonify({'success': True})


@app.route('/api/update_group_member_role/<int:group_id>', methods=['POST'])
def api_update_group_member_role(group_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    user_role = is_group_member(group_id, session['user_id'])
    if user_role not in ['owner', 'admin']:
        return jsonify({'success': False, 'error': 'Недостаточно прав'}), 403

    data = request.get_json()
    target_user_id = data.get('user_id')
    new_role = data.get('role')

    if new_role == 'owner':
        return jsonify({'success': False, 'error': 'Нельзя назначить владельца'}), 400

    target_role = is_group_member(group_id, target_user_id)
    if target_role == 'owner':
        return jsonify({'success': False, 'error': 'Нельзя изменить роль владельца'}), 400

    update_group_member_role(group_id, target_user_id, new_role)
    return jsonify({'success': True})


@app.route('/api/update_group_permissions/<int:group_id>', methods=['POST'])
def api_update_group_permissions(group_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    user_role = is_group_member(group_id, session['user_id'])
    if user_role != 'owner':
        return jsonify({'success': False, 'error': 'Только владелец может менять права'}), 403

    data = request.get_json()
    role = data.get('role')
    permissions = data.get('permissions', {})

    update_group_permissions(group_id, role, **permissions)
    return jsonify({'success': True})


@app.route('/api/join_group/<invite_link>')
def api_join_group(invite_link):
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    group = get_group_by_invite_link(invite_link)
    if not group:
        return jsonify({'success': False, 'error': 'Группа не найдена'}), 404

    if is_group_member(group['id'], session['user_id']):
        return jsonify({'success': True, 'already_member': True, 'group_id': group['id']})

    add_group_member(group['id'], session['user_id'])
    return jsonify({'success': True, 'group_id': group['id']})


@app.route('/api/leave_group/<int:group_id>', methods=['POST'])
def api_leave_group(group_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    role = is_group_member(group_id, session['user_id'])
    if role == 'owner':
        return jsonify({'success': False, 'error': 'Владелец не может покинуть группу'}), 400

    remove_group_member(group_id, session['user_id'])
    return jsonify({'success': True})


@app.route('/api/delete_group/<int:group_id>', methods=['POST'])
def api_delete_group(group_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    if delete_group(group_id, session['user_id']):
        socketio.emit('group_deleted', {'group_id': group_id}, room=f"group_{group_id}")
        return jsonify({'success': True})

    return jsonify({'success': False, 'error': 'Недостаточно прав'}), 403


# ---------------------- КАНАЛЫ ----------------------
@app.route('/api/create_channel', methods=['POST'])
def api_create_channel():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    data = request.get_json()
    name = data.get('name')
    description = data.get('description')
    is_public = data.get('is_public', True)

    if not name:
        return jsonify({'success': False, 'error': 'Название обязательно'}), 400

    channel_id = create_channel(name, session['user_id'], description, is_public)

    if channel_id:
        return jsonify({'success': True, 'channel_id': channel_id})

    return jsonify({'success': False, 'error': 'Ошибка создания'}), 500


@app.route('/api/update_channel/<int:channel_id>', methods=['POST'])
def api_update_channel(channel_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    channel = get_channel_by_id(channel_id)
    if not channel or channel['owner_id'] != session['user_id']:
        return jsonify({'success': False, 'error': 'Недостаточно прав'}), 403

    data = request.get_json()
    updates = {}
    if 'name' in data:
        updates['name'] = data['name']
    if 'description' in data:
        updates['description'] = data['description']
    if 'is_public' in data:
        updates['is_public'] = data['is_public']

    if updates:
        update_channel_settings(channel_id, **updates)

    return jsonify({'success': True})


@app.route('/api/add_channel_admin/<int:channel_id>', methods=['POST'])
def api_add_channel_admin(channel_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    channel = get_channel_by_id(channel_id)
    if not channel or channel['owner_id'] != session['user_id']:
        return jsonify({'success': False, 'error': 'Недостаточно прав'}), 403

    data = request.get_json()
    user_id = data.get('user_id')
    permissions = data.get('permissions', {})

    add_channel_admin(channel_id, user_id, **permissions)
    return jsonify({'success': True})


@app.route('/api/remove_channel_admin/<int:channel_id>', methods=['POST'])
def api_remove_channel_admin(channel_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    channel = get_channel_by_id(channel_id)
    if not channel or channel['owner_id'] != session['user_id']:
        return jsonify({'success': False, 'error': 'Недостаточно прав'}), 403

    data = request.get_json()
    user_id = data.get('user_id')

    remove_channel_admin(channel_id, user_id)
    return jsonify({'success': True})


@app.route('/api/subscribe_channel/<invite_link>')
def api_subscribe_channel(invite_link):
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    channel = get_channel_by_invite_link(invite_link)
    if not channel:
        return jsonify({'success': False, 'error': 'Канал не найден'}), 404

    subscribe_to_channel(channel['id'], session['user_id'])
    return jsonify({'success': True, 'channel_id': channel['id']})


@app.route('/api/unsubscribe_channel/<int:channel_id>', methods=['POST'])
def api_unsubscribe_channel(channel_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    channel = get_channel_by_id(channel_id)
    if channel and channel['owner_id'] == session['user_id']:
        return jsonify({'success': False, 'error': 'Владелец не может отписаться'}), 400

    unsubscribe_from_channel(channel_id, session['user_id'])
    return jsonify({'success': True})


@app.route('/api/delete_channel/<int:channel_id>', methods=['POST'])
def api_delete_channel(channel_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    if delete_channel(channel_id, session['user_id']):
        socketio.emit('channel_deleted', {'channel_id': channel_id}, room=f"channel_{channel_id}")
        return jsonify({'success': True})

    return jsonify({'success': False, 'error': 'Недостаточно прав'}), 403


# ---------------------- ВИДЕОЧАТ ----------------------
@app.route('/api/video/create_room', methods=['POST'])
def api_video_create_room():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    room_id = generate_room_id()
    call_type = request.json.get('call_type', 'video') if request.is_json else 'video'

    video_rooms[room_id] = {
        'creator_id': session['user_id'],
        'creator_name': session.get('display_name', session['username']),
        'participants': {},
        'created_at': datetime.now().isoformat(),
        'call_type': call_type
    }

    create_video_call(room_id, session['user_id'], call_type)

    return jsonify({
        'success': True,
        'room_id': room_id,
        'join_url': f"/video/{room_id}"
    })


@app.route('/api/video/join/<room_id>', methods=['POST'])
def api_video_join_room(room_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    if room_id not in video_rooms:
        return jsonify({'success': False, 'error': 'Комната не найдена'}), 404

    audio_only = request.json.get('audio_only', False) if request.is_json else False

    add_video_call_participant(room_id, session['user_id'], audio_only)

    return jsonify({
        'success': True,
        'room': {
            'room_id': room_id,
            'creator_name': video_rooms[room_id]['creator_name'],
            'call_type': video_rooms[room_id]['call_type']
        }
    })


@app.route('/api/video/end/<room_id>', methods=['POST'])
def api_video_end_room(room_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    if room_id in video_rooms:
        if video_rooms[room_id]['creator_id'] == session['user_id']:
            end_video_call(room_id)
            socketio.emit('room_ended', {'room_id': room_id}, room=f"video_{room_id}")
            del video_rooms[room_id]
            return jsonify({'success': True})

    return jsonify({'success': False, 'error': 'Недостаточно прав'}), 403


@app.route('/video/<room_id>')
def video_room_page(room_id):
    if 'user_id' not in session:
        return redirect(url_for('auth'))

    if room_id not in video_rooms:
        return render_template('room_not_found.html', room_id=room_id)

    return render_template('video_room.html',
                           room_id=room_id,
                           username=session.get('display_name', session['username']),
                           user_id=session['user_id'])


# ---------------------- ИСТОРИИ ----------------------
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

        story_id = create_story(
            session['user_id'],
            file_type,
            f"uploads/stories/{filename}",
            caption,
            music_path,
            privacy,
            selected_users
        )

        socketio.emit('new_story', {'user_id': session['user_id']})

        return jsonify({'success': True, 'story_id': story_id})

    except Exception as e:
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
    story_id = data['story_id']

    add_story_view(story_id, session['user_id'])
    add_story_interaction(story_id, session['user_id'], 'view')

    return jsonify({'success': True})


@app.route('/api/story_like', methods=['POST'])
def api_story_like():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    data = request.get_json()
    story_id = data['story_id']

    add_story_interaction(story_id, session['user_id'], 'like')

    return jsonify({'success': True})


@app.route('/api/story_reaction', methods=['POST'])
def api_story_reaction():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    data = request.get_json()
    story_id = data['story_id']
    reaction = data['reaction']

    add_story_reaction(story_id, session['user_id'], reaction)

    # Отправляем сообщение автору истории
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT user_id FROM stories WHERE id = ?', (story_id,))
    story = cursor.fetchone()
    conn.close()

    if story and story['user_id'] != session['user_id']:
        chat_id = get_or_create_chat(session['user_id'], story['user_id'])
        reaction_names = {'❤️': 'сердечко', '🔥': 'огонь', '👎': 'дизлайк', '👍': 'лайк'}
        reaction_text = reaction_names.get(reaction, reaction)
        message_content = f"📱 {reaction} на вашу историю"

        message = send_message(
            chat_id=chat_id,
            sender_id=session['user_id'],
            content=message_content
        )

        if message:
            socketio.emit('new_message', {
                'chat_id': chat_id,
                'message': dict(message)
            }, room=f"chat_{chat_id}")

    return jsonify({'success': True})


@app.route('/api/story_reply', methods=['POST'])
def api_story_reply():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    try:
        data = request.get_json()
        story_id = data['story_id']
        reply_text = data.get('reply_text', '')

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('SELECT user_id FROM stories WHERE id = ?', (story_id,))
        story = cursor.fetchone()
        conn.close()

        if not story:
            return jsonify({'success': False, 'error': 'Story not found'}), 404

        chat_id = get_or_create_chat(session['user_id'], story['user_id'])
        message_content = f"📱 Ответ на историю: {reply_text}" if reply_text else "📱 Ответ на историю"
        message = send_message(
            chat_id=chat_id,
            sender_id=session['user_id'],
            content=message_content
        )

        if message:
            socketio.emit('new_message', {
                'chat_id': chat_id,
                'message': dict(message)
            }, room=f"chat_{chat_id}")

        add_story_interaction(story_id, session['user_id'], 'reply', reply_text)

        return jsonify({'success': True, 'chat_id': chat_id, 'message': dict(message) if message else None})

    except Exception as e:
        print(f"Error in story_reply: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/get_story_info/<int:story_id>')
def api_get_story_info(story_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT s.*, u.username, u.display_name, u.avatar
        FROM stories s
        JOIN users u ON s.user_id = u.id
        WHERE s.id = ?
    ''', (story_id,))
    story = cursor.fetchone()

    viewers = get_story_viewers(story_id)
    likes = get_story_likes(story_id)
    reactions = get_story_reactions(story_id)

    conn.close()

    return jsonify({
        'story': dict(story) if story else None,
        'viewers': [dict(v) for v in viewers],
        'likes': [dict(l) for l in likes],
        'reactions': [dict(r) for r in reactions]
    })


# ---------------------- ПРОФИЛЬ ----------------------
@app.route('/api/get_my_user')
def api_get_my_user():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    user = get_user_by_id(session['user_id'])
    if user:
        return jsonify({
            'id': user['id'],
            'unique_id': user['unique_id'],
            'username': user['username'],
            'display_name': user['display_name'],
            'phone': user['phone'],
            'avatar': user['avatar'],
            'bio': user['bio'] or '',
            'birthday': user['birthday'] or ''
        })
    return jsonify({'error': 'User not found'}), 404


@app.route('/api/get_user/<int:user_id>')
def api_get_user(user_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    user = get_user_by_id(user_id)
    if user and not user['is_deleted']:
        return jsonify({
            'id': user['id'],
            'unique_id': user['unique_id'],
            'username': user['username'],
            'display_name': user['display_name'],
            'phone': user['phone'],
            'avatar': user['avatar'],
            'bio': user['bio'] or '',
            'birthday': user['birthday'] or '',
            'last_seen': user['last_seen']
        })
    return jsonify({'error': 'User not found'}), 404


@app.route('/api/get_user_profile/<int:user_id>')
def api_get_user_profile(user_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    user = get_user_profile(user_id, session['user_id'])
    if user:
        return jsonify(user)
    return jsonify({'error': 'User not found'}), 404


@app.route('/api/update_profile', methods=['POST'])
def api_update_profile():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    username = request.form.get('username')
    display_name = request.form.get('display_name')
    bio = request.form.get('bio')
    birthday = request.form.get('birthday')

    updates = {}

    if username:
        if not check_username_available(username, session['user_id']):
            return jsonify({'success': False, 'error': 'Username already taken'}), 400
        updates['username'] = username
        session['username'] = username

    if display_name is not None:
        updates['display_name'] = display_name
        session['display_name'] = display_name

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


@app.route('/api/update_profile_avatar', methods=['POST'])
def api_update_profile_avatar():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    data = request.get_json()
    avatar_url = data.get('avatar_url')

    if avatar_url:
        update_user_settings(session['user_id'], avatar=avatar_url)
        return jsonify({'success': True})

    return jsonify({'success': False}), 400


@app.route('/api/delete_account', methods=['POST'])
def api_delete_account():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    data = request.get_json()
    confirmation = data.get('confirmation', '')
    user = get_user_by_id(session['user_id'])

    if confirmation == user['phone'] or confirmation == user['username']:
        delete_user_account(session['user_id'])
        session.clear()
        return jsonify({'success': True})

    return jsonify({'success': False}), 400


# ---------------------- НАСТРОЙКИ ----------------------
@app.route('/api/get_settings')
def api_get_settings():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    settings = get_user_settings(session['user_id'])
    return jsonify(settings or {})


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


@app.route('/api/update_font_family', methods=['POST'])
def api_update_font_family():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    data = request.get_json()
    update_user_settings(session['user_id'], font_family=data.get('font_family', "'Unbounded', cursive"))
    return jsonify({'success': True})


@app.route('/api/update_message_colors', methods=['POST'])
def api_update_message_colors():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    data = request.get_json()
    updates = {}
    if 'my_message_color' in data:
        updates['my_message_color'] = data['my_message_color']
    if 'their_message_color' in data:
        updates['their_message_color'] = data['their_message_color']

    if updates:
        update_user_settings(session['user_id'], **updates)

    return jsonify({'success': True})


@app.route('/api/update_wallpaper', methods=['POST'])
def api_update_wallpaper():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    if 'wallpaper' in request.files:
        file = request.files['wallpaper']
        if file and file.filename:
            ext = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else 'jpg'
            unique_name = f"{uuid.uuid4().hex}.{ext}"
            folder = os.path.join(app.config['UPLOAD_FOLDER'], 'wallpapers')
            os.makedirs(folder, exist_ok=True)
            file_path = os.path.join(folder, unique_name)
            file.save(file_path)
            update_user_settings(session['user_id'], wallpaper_image=f"uploads/wallpapers/{unique_name}", wallpaper='')
            return jsonify({'success': True, 'wallpaper_image': f"uploads/wallpapers/{unique_name}"})

    data = request.get_json()
    if data and 'wallpaper' in data:
        update_user_settings(session['user_id'], wallpaper=data['wallpaper'], wallpaper_image='')
        return jsonify({'success': True})

    return jsonify({'success': False}), 400


@app.route('/api/get_privacy')
def api_get_privacy():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    settings = get_privacy_settings(session['user_id'])
    return jsonify(settings or {})


@app.route('/api/update_privacy', methods=['POST'])
def api_update_privacy():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    data = request.get_json()
    update_privacy_settings(
        session['user_id'],
        data.get('last_seen', 'everyone'),
        data.get('profile_photo', 'everyone'),
        data.get('forward_messages', 'everyone'),
        data.get('calls', 'everyone'),
        data.get('messages', 'everyone')
    )
    return jsonify({'success': True})


# ---------------------- ЗАКРЕПЛЕНИЕ ЧАТОВ ----------------------
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


# ---------------------- КОНТАКТЫ ----------------------
@app.route('/api/get_contacts')
def api_get_contacts():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    contacts = get_contacts(session['user_id'])
    return jsonify([dict(c) for c in contacts])


@app.route('/api/add_contact', methods=['POST'])
def api_add_contact():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    data = request.get_json()
    contact_id = data.get('contact_id')
    if add_contact(session['user_id'], contact_id):
        return jsonify({'success': True})
    return jsonify({'success': False}), 400


# ---------------------- ЗВОНКИ ----------------------
@app.route('/api/make_call', methods=['POST'])
def api_make_call():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    data = request.get_json()
    receiver_id = data.get('receiver_id')
    call_type = data.get('call_type', 'audio')

    if not receiver_id:
        return jsonify({'error': 'receiver_id required'}), 400

    call_id = add_call(session['user_id'], receiver_id, call_type, 'ringing')

    receiver = get_user_by_id(receiver_id)
    if receiver:
        socketio.emit('incoming_call', {
            'call_id': call_id,
            'caller_id': session['user_id'],
            'caller_name': session.get('display_name', session['username']),
            'call_type': call_type
        }, room=f"user_{receiver_id}")

    return jsonify({'success': True, 'call_id': call_id})


@app.route('/api/answer_call', methods=['POST'])
def api_answer_call():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    data = request.get_json()
    update_call_status(data.get('call_id'), 'answered')
    return jsonify({'success': True})


@app.route('/api/end_call', methods=['POST'])
def api_end_call():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    data = request.get_json()
    update_call_status(data.get('call_id'), 'ended', data.get('duration', 0))
    return jsonify({'success': True})


@app.route('/api/get_call_history')
def api_get_call_history():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    calls = get_call_history(session['user_id'])
    return jsonify([dict(c) for c in calls])


# ---------------------- ПРЕДЗАГРУЗОЧНЫЕ АВАТАРКИ ----------------------
@app.route('/api/preloaded_avatars')
def api_preloaded_avatars():
    avatars = get_preloaded_avatars()
    return jsonify([dict(a) for a in avatars])


# ---------------------- СЕССИИ ----------------------
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
    delete_session(data.get('session_token'))
    return jsonify({'success': True})


@app.route('/api/terminate_all_sessions', methods=['POST'])
def api_terminate_all_sessions():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    delete_all_sessions_except(session['user_id'], session.get('session_token', ''))
    return jsonify({'success': True})


# ---------------------- ЗАГРУЗКА ФАЙЛОВ ----------------------
@app.route('/uploads/<path:filename>')
def uploaded_file(filename):
    return send_file(os.path.join(app.config['UPLOAD_FOLDER'], filename))


@app.route('/static/avatar-swg/<path:filename>')
def static_avatar(filename):
    return send_file(os.path.join('static', 'avatar-swg', filename))


# ---------------------- SOCKETIO ----------------------
@socketio.on('connect')
def handle_connect():
    if 'user_id' in session:
        join_room(f"user_{session['user_id']}")
        update_last_seen(session['user_id'])
        emit('connected', {'user_id': session['user_id']})


@socketio.on('disconnect')
def handle_disconnect():
    if 'user_id' in session:
        update_last_seen(session['user_id'])
        for room_id, room_data in list(video_rooms.items()):
            if request.sid in room_data.get('participants', {}):
                del video_rooms[room_id]['participants'][request.sid]
                remove_video_call_participant(room_id, session['user_id'])
                emit('participant_left', {'sid': request.sid}, room=f"video_{room_id}")


@socketio.on('join_chat')
def handle_join_chat(data):
    if 'user_id' in session:
        room = f"chat_{data.get('chat_id')}"
        join_room(room)


@socketio.on('join_group')
def handle_join_group(data):
    if 'user_id' in session:
        room = f"group_{data.get('group_id')}"
        join_room(room)


@socketio.on('join_channel')
def handle_join_channel(data):
    if 'user_id' in session:
        room = f"channel_{data.get('channel_id')}"
        join_room(room)


@socketio.on('typing')
def handle_typing(data):
    if 'user_id' in session:
        room = data.get('room')
        if room:
            emit('user_typing', {
                'user_id': session['user_id'],
                'username': session.get('display_name', session['username'])
            }, room=room, include_self=False)


# ---------------------- WEBRTC СИГНАЛИНГ ----------------------
@socketio.on('join_video')
def handle_join_video(data):
    if 'user_id' not in session:
        return

    room_id = data.get('room_id')
    audio_only = data.get('audio_only', False)

    if room_id not in video_rooms:
        emit('error', {'message': 'Комната не найдена'})
        return

    room = f"video_{room_id}"
    join_room(room)

    if 'participants' not in video_rooms[room_id]:
        video_rooms[room_id]['participants'] = {}

    video_rooms[room_id]['participants'][request.sid] = {
        'user_id': session['user_id'],
        'username': session.get('display_name', session['username']),
        'audio_only': audio_only
    }

    add_video_call_participant(room_id, session['user_id'], audio_only)

    emit('user_joined_video', {
        'sid': request.sid,
        'user_id': session['user_id'],
        'username': session.get('display_name', session['username']),
        'audio_only': audio_only
    }, room=room, include_self=False)

    existing = []
    for sid, p in video_rooms[room_id]['participants'].items():
        if sid != request.sid:
            existing.append({
                'sid': sid,
                'user_id': p['user_id'],
                'username': p['username'],
                'audio_only': p['audio_only']
            })

    emit('existing_participants', {'participants': existing}, room=request.sid)


@socketio.on('leave_video')
def handle_leave_video(data):
    if 'user_id' not in session:
        return

    room_id = data.get('room_id')
    room = f"video_{room_id}"
    leave_room(room)

    if room_id in video_rooms and request.sid in video_rooms[room_id].get('participants', {}):
        del video_rooms[room_id]['participants'][request.sid]
        remove_video_call_participant(room_id, session['user_id'])
        emit('participant_left', {
            'sid': request.sid,
            'user_id': session['user_id']
        }, room=room)

        if len(video_rooms[room_id]['participants']) == 0:
            end_video_call(room_id)
            del video_rooms[room_id]


@socketio.on('video_offer')
def handle_video_offer(data):
    emit('video_offer', {
        'offer': data['offer'],
        'from': request.sid,
        'from_username': session.get('display_name', session['username'])
    }, room=data['to'])


@socketio.on('video_answer')
def handle_video_answer(data):
    emit('video_answer', {
        'answer': data['answer'],
        'from': request.sid
    }, room=data['to'])


@socketio.on('ice_candidate')
def handle_ice_candidate(data):
    emit('ice_candidate', {
        'candidate': data['candidate'],
        'from': request.sid
    }, room=data['to'])


# ---------------------- ЗАПУСК ----------------------
def get_local_ip():
    try:
        import socket
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "127.0.0.1"


def schedule_story_cleanup():
    import threading
    import time

    def cleanup_job():
        while True:
            time.sleep(3600)
            deleted = delete_expired_stories()
            if deleted > 0:
                print(f"🗑️ Удалено {deleted} устаревших историй")

    thread = threading.Thread(target=cleanup_job, daemon=True)
    thread.start()


if __name__ == '__main__':
    print("\n" + "=" * 60)
    print("🔷 SWILLGRAM v3.0 ЗАПУЩЕН!")
    print("=" * 60)

    local_ip = get_local_ip()

    print(f"\n📱 Доступные адреса:")
    print(f"   • Локальный: http://localhost:5000")
    print(f"   • Локальный: http://127.0.0.1:5000")
    if local_ip != "127.0.0.1":
        print(f"   • Сеть:      http://{local_ip}:5000")

    print("\n✨ Функции v3.0:")
    print("   • Единая авторизация Вход/Регистрация")
    print("   • Простой поиск по телефону/username")
    print("   • Блокировка/разблокировка пользователей")
    print("   • Максимум 3 реакции на сообщение")
    print("   • Реакции на истории (❤️🔥👎👍)")
    print("   • Права администраторов в группах/каналах")
    print("   • Публичные/частные группы и каналы")

    print("\n" + "=" * 60 + "\n")

    schedule_story_cleanup()
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)