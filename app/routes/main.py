from flask import Blueprint, render_template, session, redirect, url_for
from app.models import User

main_bp = Blueprint('main', __name__)


@main_bp.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('main.chat_page'))
    return redirect(url_for('auth.auth_page'))


@main_bp.route('/chat')
def chat_page():
    if 'user_id' not in session:
        return redirect(url_for('auth.auth_page'))

    user = User.query.get(session['user_id'])
    if not user or user.is_deleted:
        session.clear()
        return redirect(url_for('auth.auth_page'))

    return render_template('chat.html', user=user)