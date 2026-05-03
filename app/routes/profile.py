from flask import Blueprint, request, session, jsonify
from app.models import User, Contact, BlockedUser, UserSession
from app import db
from app.utils.decorators import api_login_required
from app.config import Config
from datetime import datetime
import os
import uuid

profile_bp = Blueprint('profile', __name__)


@profile_bp.route('/me')
@api_login_required
def get_my_profile():
    """Get current user profile"""
    user = User.query.get(session['user_id'])
    if not user:
        return jsonify({'error': 'User not found'}), 404

    return jsonify(user_to_dict(user, include_private=True))


@profile_bp.route('/<int:user_id>')
@api_login_required
def get_user_profile(user_id):
    """Get user profile"""
    user = User.query.get(user_id)
    if not user or user.is_deleted:
        return jsonify({'error': 'User not found'}), 404

    is_blocked = BlockedUser.query.filter_by(
        blocker_id=session['user_id'],
        blocked_id=user_id
    ).first() is not None

    is_contact = Contact.query.filter_by(
        user_id=session['user_id'],
        contact_id=user_id
    ).first() is not None

    return jsonify({
        **user_to_dict(user),
        'is_blocked': is_blocked,
        'is_contact': is_contact
    })


@profile_bp.route('/update', methods=['POST'])
@api_login_required
def update_profile():
    """Update user profile"""
    user = User.query.get(session['user_id'])
    if not user:
        return jsonify({'error': 'User not found'}), 404

    # Check if it's JSON or form data
    if request.is_json:
        data = request.get_json()

        # Update text fields
        if 'username' in data:
            username = data['username'].strip()
            existing = User.query.filter(User.username == username, User.id != user.id).first()
            if existing:
                return jsonify({'success': False, 'error': 'Username already taken'}), 400
            user.username = username
            session['username'] = username

        if 'display_name' in data:
            user.display_name = data['display_name']
            session['display_name'] = data['display_name']

        if 'bio' in data:
            user.bio = data['bio']

        if 'birthday' in data and data['birthday']:
            try:
                user.birthday = datetime.strptime(data['birthday'], '%Y-%m-%d').date()
            except:
                pass
    else:
        # Form data
        if 'username' in request.form:
            username = request.form['username'].strip()
            existing = User.query.filter(User.username == username, User.id != user.id).first()
            if existing:
                return jsonify({'success': False, 'error': 'Username already taken'}), 400
            user.username = username
            session['username'] = username

        if 'display_name' in request.form:
            user.display_name = request.form['display_name']
            session['display_name'] = request.form['display_name']

        if 'bio' in request.form:
            user.bio = request.form['bio']

        if 'birthday' in request.form and request.form['birthday']:
            try:
                user.birthday = datetime.strptime(request.form['birthday'], '%Y-%m-%d').date()
            except:
                pass

        # Handle avatar upload
        if 'avatar' in request.files:
            file = request.files['avatar']
            if file and file.filename:
                ext = file.filename.rsplit('.', 1)[1].lower()
                filename = f"{uuid.uuid4().hex}.{ext}"
                filepath = os.path.join(Config.UPLOAD_FOLDER, 'avatars', filename)
                os.makedirs(os.path.dirname(filepath), exist_ok=True)
                file.save(filepath)
                user.avatar = f"uploads/avatars/{filename}"

    db.session.commit()

    return jsonify({
        'success': True,
        'user': user_to_dict(user, include_private=True)
    })


@profile_bp.route('/update_avatar', methods=['POST'])
@api_login_required
def update_avatar():
    """Update avatar from preloaded avatars"""
    data = request.get_json()
    avatar_url = data.get('avatar_url')

    if avatar_url:
        user = User.query.get(session['user_id'])
        if user:
            user.avatar = avatar_url
            db.session.commit()
            return jsonify({'success': True})

    return jsonify({'success': False}), 400


@profile_bp.route('/settings')
@api_login_required
def get_settings():
    """Get user settings"""
    user = User.query.get(session['user_id'])
    if not user:
        return jsonify({'error': 'User not found'}), 404

    return jsonify({
        'theme': user.theme or 'light',
        'font_size': user.font_size or 14,
        'bubble_radius': user.bubble_radius or 18,
        'font_family': user.font_family or 'Unbounded, cursive',
        'my_message_color': user.my_message_color,
        'their_message_color': user.their_message_color,
        'wallpaper': user.wallpaper,
        'wallpaper_image': user.wallpaper_image
    })


@profile_bp.route('/update_settings', methods=['POST'])
@api_login_required
def update_settings():
    """Update user settings"""
    data = request.get_json()
    user = User.query.get(session['user_id'])

    if not user:
        return jsonify({'error': 'User not found'}), 404

    settings_fields = [
        'theme', 'font_size', 'bubble_radius', 'font_family',
        'my_message_color', 'their_message_color', 'wallpaper', 'wallpaper_image'
    ]

    for field in settings_fields:
        if field in data:
            setattr(user, field, data[field])

    db.session.commit()

    return jsonify({'success': True})


@profile_bp.route('/privacy')
@api_login_required
def get_privacy():
    """Get privacy settings"""
    user = User.query.get(session['user_id'])
    if not user:
        return jsonify({'error': 'User not found'}), 404

    return jsonify({
        'last_seen': user.privacy_last_seen or 'everyone',
        'profile_photo': user.privacy_profile_photo or 'everyone',
        'forward_messages': user.privacy_forward_messages or 'everyone',
        'calls': user.privacy_calls or 'everyone',
        'messages': user.privacy_messages or 'everyone'
    })


@profile_bp.route('/update_privacy', methods=['POST'])
@api_login_required
def update_privacy():
    """Update privacy settings"""
    data = request.get_json()
    user = User.query.get(session['user_id'])

    if not user:
        return jsonify({'error': 'User not found'}), 404

    privacy_map = {
        'last_seen': 'privacy_last_seen',
        'profile_photo': 'privacy_profile_photo',
        'forward_messages': 'privacy_forward_messages',
        'calls': 'privacy_calls',
        'messages': 'privacy_messages'
    }

    for key, attr in privacy_map.items():
        if key in data:
            setattr(user, attr, data[key])

    db.session.commit()

    return jsonify({'success': True})


@profile_bp.route('/delete_account', methods=['POST'])
@api_login_required
def delete_account():
    """Delete user account"""
    data = request.get_json()
    confirmation = data.get('confirmation', '')

    user = User.query.get(session['user_id'])

    if user and (confirmation == user.phone or confirmation == user.username):
        user.is_deleted = True
        db.session.commit()
        session.clear()
        return jsonify({'success': True})

    return jsonify({'success': False, 'error': 'Invalid confirmation'}), 400


@profile_bp.route('/sessions')
@api_login_required
def get_sessions():
    """Get active sessions"""
    sessions = UserSession.query.filter_by(
        user_id=session['user_id'],
        is_active=True
    ).all()

    return jsonify([{
        'id': s.id,
        'session_token': s.session_token[:20] + '...' if len(s.session_token) > 20 else s.session_token,
        'ip_address': s.ip_address,
        'user_agent': s.user_agent,
        'is_current': s.session_token == session.get('session_token'),
        'created_at': s.created_at.isoformat() if s.created_at else None,
        'last_activity': s.last_activity.isoformat() if s.last_activity else None
    } for s in sessions])


@profile_bp.route('/terminate_session', methods=['POST'])
@api_login_required
def terminate_session():
    """Terminate a specific session"""
    data = request.get_json()
    session_token = data.get('session_token')

    if session_token:
        UserSession.query.filter_by(
            user_id=session['user_id'],
            session_token=session_token
        ).delete()
        db.session.commit()
        return jsonify({'success': True})

    return jsonify({'success': False}), 400


@profile_bp.route('/terminate_all_sessions', methods=['POST'])
@api_login_required
def terminate_all_sessions():
    """Terminate all other sessions"""
    UserSession.query.filter(
        UserSession.user_id == session['user_id'],
        UserSession.session_token != session.get('session_token')
    ).delete()
    db.session.commit()

    return jsonify({'success': True})


@profile_bp.route('/block/<int:user_id>', methods=['POST'])
@api_login_required
def block_user(user_id):
    """Block a user"""
    if user_id == session['user_id']:
        return jsonify({'success': False, 'error': 'Cannot block yourself'}), 400

    existing = BlockedUser.query.filter_by(
        blocker_id=session['user_id'],
        blocked_id=user_id
    ).first()

    if not existing:
        block = BlockedUser(
            blocker_id=session['user_id'],
            blocked_id=user_id
        )
        db.session.add(block)
        db.session.commit()

    return jsonify({'success': True})


@profile_bp.route('/unblock/<int:user_id>', methods=['POST'])
@api_login_required
def unblock_user(user_id):
    """Unblock a user"""
    BlockedUser.query.filter_by(
        blocker_id=session['user_id'],
        blocked_id=user_id
    ).delete()
    db.session.commit()

    return jsonify({'success': True})


@profile_bp.route('/blocked')
@api_login_required
def get_blocked_users():
    """Get list of blocked users"""
    blocked = BlockedUser.query.filter_by(blocker_id=session['user_id']).all()
    users = []
    for block in blocked:
        user = User.query.get(block.blocked_id)
        if user and not user.is_deleted:
            users.append(user_to_dict(user))

    return jsonify(users)


@profile_bp.route('/contacts')
@api_login_required
def get_contacts():
    """Get user contacts"""
    contacts = Contact.query.filter_by(user_id=session['user_id']).all()
    contacts_data = []

    for contact in contacts:
        user = User.query.get(contact.contact_id)
        if user and not user.is_deleted:
            contacts_data.append({
                **user_to_dict(user),
                'display_name': contact.display_name,
                'is_favorite': contact.is_favorite,
                'added_at': contact.created_at.isoformat() if contact.created_at else None
            })

    return jsonify(contacts_data)


@profile_bp.route('/add_contact', methods=['POST'])
@api_login_required
def add_contact():
    """Add a contact"""
    data = request.get_json()
    contact_id = data.get('contact_id')
    display_name = data.get('display_name')

    if not contact_id:
        return jsonify({'success': False, 'error': 'Contact ID required'}), 400

    if contact_id == session['user_id']:
        return jsonify({'success': False, 'error': 'Cannot add yourself'}), 400

    existing = Contact.query.filter_by(
        user_id=session['user_id'],
        contact_id=contact_id
    ).first()

    if existing:
        if display_name:
            existing.display_name = display_name
            db.session.commit()
        return jsonify({'success': True, 'already_exists': True})

    contact = Contact(
        user_id=session['user_id'],
        contact_id=contact_id,
        display_name=display_name
    )
    db.session.add(contact)
    db.session.commit()

    return jsonify({'success': True})


@profile_bp.route('/remove_contact/<int:contact_id>', methods=['POST'])
@api_login_required
def remove_contact(contact_id):
    """Remove a contact"""
    Contact.query.filter_by(
        user_id=session['user_id'],
        contact_id=contact_id
    ).delete()
    db.session.commit()

    return jsonify({'success': True})


@profile_bp.route('/toggle_favorite/<int:contact_id>', methods=['POST'])
@api_login_required
def toggle_favorite(contact_id):
    """Toggle favorite status for a contact"""
    contact = Contact.query.filter_by(
        user_id=session['user_id'],
        contact_id=contact_id
    ).first()

    if contact:
        contact.is_favorite = not contact.is_favorite
        db.session.commit()
        return jsonify({'success': True, 'is_favorite': contact.is_favorite})

    return jsonify({'success': False, 'error': 'Contact not found'}), 404


def user_to_dict(user, include_private=False):
    """Convert user object to dictionary"""
    if not user:
        return {}

    data = {
        'id': user.id,
        'unique_id': user.unique_id,
        'username': user.username,
        'display_name': user.display_name,
        'avatar': user.avatar,
        'bio': user.bio,
        'last_seen': user.last_seen.isoformat() if user.last_seen else None,
        'is_online': (datetime.utcnow() - user.last_seen).seconds < 300 if user.last_seen else False,
        'created_at': user.created_at.isoformat() if user.created_at else None
    }

    if include_private:
        data.update({
            'phone': user.phone,
            'birthday': user.birthday.isoformat() if user.birthday else None,
            'theme': user.theme,
            'font_size': user.font_size,
            'bubble_radius': user.bubble_radius,
            'font_family': user.font_family,
            'my_message_color': user.my_message_color,
            'their_message_color': user.their_message_color,
            'wallpaper': user.wallpaper,
            'wallpaper_image': user.wallpaper_image
        })

    return data