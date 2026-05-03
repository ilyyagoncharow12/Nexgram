from flask import Blueprint, render_template, request, session, redirect, url_for, jsonify
from app.models import User, UserSession, PreloadedAvatar
from app import db
from datetime import datetime, timedelta
import uuid
import re

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/', methods=['GET', 'POST'])
def auth_page():
    if request.method == 'POST':
        action = request.form.get('action')
        phone = request.form.get('phone', '').strip()
        password = request.form.get('password', '')
        remember = request.form.get('remember') == 'on'

        if action == 'login':
            return handle_login(phone, password, remember)
        elif action == 'check_phone':
            return handle_check_phone(phone)
        elif action == 'register_step1':
            return handle_register_step1(phone, password, remember)

    mode = request.args.get('mode', 'login')
    phone = request.args.get('phone', '')
    return render_template('auth.html', mode=mode, phone=phone)


@auth_bp.route('/complete-registration', methods=['GET', 'POST'])
def complete_registration():
    if 'temp_user_id' not in session:
        return redirect(url_for('auth.auth_page'))

    avatars = PreloadedAvatar.query.all()

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        display_name = request.form.get('display_name', '').strip()
        avatar = request.form.get('avatar', '')

        if len(username) < 3:
            return render_template('complete_registration.html', error='Минимум 3 символа')
        if not re.match(r'^[a-zA-Z0-9_]+$', username):
            return render_template('complete_registration.html', error='Только латиница, цифры и _')

        existing = User.query.filter_by(username=username).first()
        if existing and existing.id != session['temp_user_id']:
            return render_template('complete_registration.html', error='Имя занято')

        user = User.query.get(session['temp_user_id'])
        if not user:
            return redirect(url_for('auth.auth_page'))

        user.username = username
        user.display_name = display_name or username
        user.avatar = avatar
        user.registration_complete = True
        db.session.commit()

        session.clear()
        return complete_login(user)

    return render_template('complete_registration.html', avatars=avatars)


@auth_bp.route('/logout')
def logout():
    if 'user_id' in session:
        user = User.query.get(session['user_id'])
        if user:
            user.last_seen = datetime.utcnow()
            db.session.commit()

        if 'session_token' in session:
            UserSession.query.filter_by(session_token=session['session_token']).delete()
            db.session.commit()

    session.clear()
    return redirect(url_for('auth.auth_page'))


def handle_login(phone, password, remember):
    if not phone or not password:
        return render_template('auth.html', error='Заполните все поля', mode='login')

    user = User.query.filter_by(phone=phone).first()

    if not user or not user.check_password(password):
        return render_template('auth.html', error='Неверный номер или пароль', mode='login', phone=phone)

    if user.is_deleted:
        return render_template('auth.html', error='Аккаунт удалён', mode='login')

    if not user.registration_complete:
        session['temp_user_id'] = user.id
        session['temp_phone'] = user.phone
        return redirect(url_for('auth.complete_registration'))

    return complete_login(user, remember)


def handle_check_phone(phone):
    existing = User.query.filter_by(phone=phone).first()
    return jsonify({
        'exists': existing is not None,
        'registration_complete': bool(existing.registration_complete) if existing else False
    })


def handle_register_step1(phone, password, remember):
    if len(password) < 8:
        return render_template('auth.html', error='Пароль минимум 8 символов', mode='register', phone=phone)

    existing = User.query.filter_by(phone=phone).first()

    if existing and existing.registration_complete:
        return render_template('auth.html', error='Номер зарегистрирован. Войдите.', mode='login', phone=phone)

    if existing and not existing.registration_complete:
        session['temp_user_id'] = existing.id
        session['temp_phone'] = phone
        return redirect(url_for('auth.complete_registration'))

    user = User(
        unique_id=User.generate_unique_id(),
        phone=phone,
        registration_complete=False
    )
    user.set_password(password)
    db.session.add(user)
    db.session.commit()

    session['temp_user_id'] = user.id
    session['temp_phone'] = phone
    return redirect(url_for('auth.complete_registration'))


def complete_login(user, remember=False):
    session['user_id'] = user.id
    session['unique_id'] = user.unique_id
    session['username'] = user.username
    session['display_name'] = user.display_name or user.username
    session['phone'] = user.phone

    if remember:
        session.permanent = True

    user.last_seen = datetime.utcnow()

    session_token = str(uuid.uuid4())
    user_session = UserSession(
        user_id=user.id,
        session_token=session_token,
        ip_address=request.remote_addr,
        user_agent=request.headers.get('User-Agent', 'Unknown')
    )
    db.session.add(user_session)
    db.session.commit()

    session['session_token'] = session_token
    return redirect(url_for('main.chat_page'))