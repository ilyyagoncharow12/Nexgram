from flask import Blueprint, request, session, jsonify
from app.models import Channel, ChannelSubscriber, ChannelAdmin, Message, User
from app import db
from app.utils.decorators import api_login_required
from datetime import datetime

channel_bp = Blueprint('channel', __name__)


@channel_bp.route('/create', methods=['POST'])
@api_login_required
def create_channel():
    """Create a new channel"""
    data = request.get_json()
    name = data.get('name')
    description = data.get('description', '')
    is_public = data.get('is_public', True)

    if not name:
        return jsonify({'success': False, 'error': 'Название обязательно'}), 400

    channel = Channel(
        name=name,
        description=description,
        owner_id=session['user_id'],
        is_public=is_public,
        invite_link=Channel.generate_invite_link()
    )
    db.session.add(channel)
    db.session.commit()

    # Auto-subscribe owner
    subscriber = ChannelSubscriber(
        channel_id=channel.id,
        user_id=session['user_id']
    )
    db.session.add(subscriber)
    db.session.commit()

    return jsonify({
        'success': True,
        'channel_id': channel.id,
        'invite_link': channel.invite_link
    })


@channel_bp.route('/<int:channel_id>')
@api_login_required
def get_channel(channel_id):
    """Get channel details with messages"""
    channel = Channel.query.get(channel_id)
    if not channel:
        return jsonify({'error': 'Channel not found'}), 404

    # Check if subscribed
    subscriber = ChannelSubscriber.query.filter_by(
        channel_id=channel_id,
        user_id=session['user_id']
    ).first()

    if not subscriber:
        return jsonify({'error': 'Not subscribed'}), 403

    # Get messages
    messages = Message.query.filter_by(
        channel_id=channel_id,
        is_deleted=False
    ).order_by(Message.created_at.desc()).limit(50).all()

    # Check if user can post
    can_post = can_user_post(channel_id, session['user_id'])

    return jsonify({
        'channel': channel_to_dict(channel),
        'messages': [message_to_dict(m) for m in reversed(messages)],
        'can_post': can_post
    })


@channel_bp.route('/<int:channel_id>/update', methods=['POST'])
@api_login_required
def update_channel(channel_id):
    """Update channel settings"""
    data = request.get_json()

    channel = Channel.query.get(channel_id)
    if not channel:
        return jsonify({'error': 'Channel not found'}), 404

    if channel.owner_id != session['user_id']:
        return jsonify({'success': False, 'error': 'Недостаточно прав'}), 403

    if 'name' in data:
        channel.name = data['name']
    if 'description' in data:
        channel.description = data['description']
    if 'is_public' in data:
        channel.is_public = data['is_public']

    db.session.commit()

    return jsonify({'success': True, 'channel': channel_to_dict(channel)})


@channel_bp.route('/<int:channel_id>/delete', methods=['POST'])
@api_login_required
def delete_channel(channel_id):
    """Delete channel (owner only)"""
    channel = Channel.query.get(channel_id)
    if not channel:
        return jsonify({'error': 'Channel not found'}), 404

    if channel.owner_id != session['user_id']:
        return jsonify({'success': False, 'error': 'Только владелец может удалить канал'}), 403

    db.session.delete(channel)
    db.session.commit()

    return jsonify({'success': True})


@channel_bp.route('/subscribe/<invite_link>')
@api_login_required
def subscribe_by_link(invite_link):
    """Subscribe to channel by invite link"""
    channel = Channel.query.filter_by(invite_link=invite_link).first()
    if not channel:
        return jsonify({'success': False, 'error': 'Канал не найден'}), 404

    existing = ChannelSubscriber.query.filter_by(
        channel_id=channel.id,
        user_id=session['user_id']
    ).first()

    if existing:
        return jsonify({
            'success': True,
            'already_subscribed': True,
            'channel_id': channel.id
        })

    if not channel.is_public:
        return jsonify({'success': False, 'error': 'Канал приватный'}), 403

    subscriber = ChannelSubscriber(
        channel_id=channel.id,
        user_id=session['user_id']
    )
    db.session.add(subscriber)
    db.session.commit()

    return jsonify({
        'success': True,
        'channel_id': channel.id,
        'channel': channel_to_dict(channel)
    })


@channel_bp.route('/<int:channel_id>/unsubscribe', methods=['POST'])
@api_login_required
def unsubscribe(channel_id):
    """Unsubscribe from channel"""
    channel = Channel.query.get(channel_id)
    if not channel:
        return jsonify({'error': 'Channel not found'}), 404

    if channel.owner_id == session['user_id']:
        return jsonify({'success': False, 'error': 'Владелец не может отписаться'}), 400

    subscriber = ChannelSubscriber.query.filter_by(
        channel_id=channel_id,
        user_id=session['user_id']
    ).first()

    if subscriber:
        db.session.delete(subscriber)
        db.session.commit()

    return jsonify({'success': True})


@channel_bp.route('/<int:channel_id>/subscribers')
@api_login_required
def get_subscribers(channel_id):
    """Get channel subscribers"""
    subscribers = ChannelSubscriber.query.filter_by(channel_id=channel_id).all()
    return jsonify([subscriber_to_dict(s) for s in subscribers])


@channel_bp.route('/<int:channel_id>/admins')
@api_login_required
def get_admins(channel_id):
    """Get channel admins"""
    admins = ChannelAdmin.query.filter_by(channel_id=channel_id).all()
    return jsonify([admin_to_dict(a) for a in admins])


@channel_bp.route('/<int:channel_id>/add_admin', methods=['POST'])
@api_login_required
def add_admin(channel_id):
    """Add admin to channel"""
    data = request.get_json()
    user_id = data.get('user_id')
    can_post = data.get('can_post', True)
    can_edit = data.get('can_edit', False)
    can_delete = data.get('can_delete', False)
    can_add_admins = data.get('can_add_admins', False)

    channel = Channel.query.get(channel_id)
    if not channel:
        return jsonify({'error': 'Channel not found'}), 404

    if channel.owner_id != session['user_id']:
        return jsonify({'success': False, 'error': 'Только владелец может назначать админов'}), 403

    existing = ChannelAdmin.query.filter_by(
        channel_id=channel_id,
        user_id=user_id
    ).first()

    if existing:
        return jsonify({'success': False, 'error': 'Уже админ'}), 400

    admin = ChannelAdmin(
        channel_id=channel_id,
        user_id=user_id,
        can_post=can_post,
        can_edit=can_edit,
        can_delete=can_delete,
        can_add_admins=can_add_admins
    )
    db.session.add(admin)
    db.session.commit()

    return jsonify({'success': True})


@channel_bp.route('/<int:channel_id>/remove_admin', methods=['POST'])
@api_login_required
def remove_admin(channel_id):
    """Remove admin from channel"""
    data = request.get_json()
    user_id = data.get('user_id')

    channel = Channel.query.get(channel_id)
    if not channel:
        return jsonify({'error': 'Channel not found'}), 404

    if channel.owner_id != session['user_id']:
        return jsonify({'success': False, 'error': 'Только владелец может удалять админов'}), 403

    admin = ChannelAdmin.query.filter_by(
        channel_id=channel_id,
        user_id=user_id
    ).first()

    if admin:
        db.session.delete(admin)
        db.session.commit()

    return jsonify({'success': True})


@channel_bp.route('/search')
@api_login_required
def search_channels():
    """Search for public channels"""
    query = request.args.get('q', '').strip()
    if len(query) < 2:
        return jsonify([])

    channels = Channel.query.filter(
        Channel.name.ilike(f'%{query}%'),
        Channel.is_public == True
    ).limit(20).all()

    return jsonify([channel_to_dict(c) for c in channels])


@channel_bp.route('/my')
@api_login_required
def my_channels():
    """Get user's subscribed channels"""
    subscriptions = ChannelSubscriber.query.filter_by(
        user_id=session['user_id']
    ).all()

    channels_data = []
    for sub in subscriptions:
        channel = Channel.query.get(sub.channel_id)
        if channel:
            channel_info = channel_to_dict(channel)
            channel_info['is_owner'] = channel.owner_id == session['user_id']
            channel_info['subscribed_at'] = sub.subscribed_at.isoformat() if sub.subscribed_at else None
            channels_data.append(channel_info)

    return jsonify(channels_data)


@channel_bp.route('/<int:channel_id>/messages')
@api_login_required
def get_messages(channel_id):
    """Get channel messages with pagination"""
    subscriber = ChannelSubscriber.query.filter_by(
        channel_id=channel_id,
        user_id=session['user_id']
    ).first()

    if not subscriber:
        return jsonify({'error': 'Not subscribed'}), 403

    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)

    messages = Message.query.filter_by(
        channel_id=channel_id,
        is_deleted=False
    ).order_by(
        Message.created_at.desc()
    ).paginate(page=page, per_page=per_page, error_out=False)

    return jsonify({
        'messages': [message_to_dict(m) for m in messages.items],
        'has_next': messages.has_next,
        'total': messages.total
    })


def can_user_post(channel_id, user_id):
    """Check if user can post in channel"""
    channel = Channel.query.get(channel_id)
    if not channel:
        return False

    if channel.owner_id == user_id:
        return True

    admin = ChannelAdmin.query.filter_by(
        channel_id=channel_id,
        user_id=user_id
    ).first()

    if admin and admin.can_post:
        return True

    return False


def channel_to_dict(channel):
    """Convert channel object to dictionary"""
    subscribers_count = ChannelSubscriber.query.filter_by(channel_id=channel.id).count()

    return {
        'id': channel.id,
        'name': channel.name,
        'description': channel.description,
        'owner_id': channel.owner_id,
        'avatar': channel.avatar,
        'invite_link': channel.invite_link,
        'is_public': channel.is_public,
        'subscribers_count': subscribers_count,
        'created_at': channel.created_at.isoformat() if channel.created_at else None
    }


def subscriber_to_dict(subscriber):
    """Convert subscriber object to dictionary"""
    user = User.query.get(subscriber.user_id)
    return {
        'id': subscriber.id,
        'user_id': subscriber.user_id,
        'username': user.username if user else None,
        'display_name': user.display_name if user else None,
        'avatar': user.avatar if user else None,
        'subscribed_at': subscriber.subscribed_at.isoformat() if subscriber.subscribed_at else None
    }


def admin_to_dict(admin):
    """Convert admin object to dictionary"""
    user = User.query.get(admin.user_id)
    return {
        'id': admin.id,
        'user_id': admin.user_id,
        'username': user.username if user else None,
        'display_name': user.display_name if user else None,
        'avatar': user.avatar if user else None,
        'can_post': admin.can_post,
        'can_edit': admin.can_edit,
        'can_delete': admin.can_delete,
        'can_add_admins': admin.can_add_admins
    }


def message_to_dict(message):
    """Convert message object to dictionary"""
    sender = User.query.get(message.sender_id)

    return {
        'id': message.id,
        'channel_id': message.channel_id,
        'sender_id': message.sender_id,
        'sender_name': sender.display_name or sender.username if sender else 'Unknown',
        'sender_avatar': sender.avatar if sender else None,
        'content': message.content,
        'file_type': message.file_type,
        'file_path': message.file_path,
        'file_name': message.file_name,
        'file_size': message.file_size,
        'reply_to_id': message.reply_to_id,
        'is_edited': message.is_edited,
        'is_deleted': message.is_deleted,
        'created_at': message.created_at.isoformat() if message.created_at else None,
        'updated_at': message.updated_at.isoformat() if message.updated_at else None
    }