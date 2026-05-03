from flask import Blueprint, request, session, jsonify
from app.models import User, Chat, Message, Contact
from app import db
from app.utils.decorators import api_login_required
from datetime import datetime

chat_bp = Blueprint('chat', __name__)


@chat_bp.route('/chat/<int:user_id>')
@api_login_required
def get_chat(user_id):
    current_user_id = session['user_id']

    # Create or get existing chat
    chat = Chat.query.filter(
        ((Chat.user1_id == current_user_id) & (Chat.user2_id == user_id)) |
        ((Chat.user1_id == user_id) & (Chat.user2_id == current_user_id))
    ).first()

    if not chat:
        chat = Chat(user1_id=current_user_id, user2_id=user_id)
        db.session.add(chat)
        db.session.commit()

    messages = Message.query.filter_by(
        chat_id=chat.id,
        is_deleted=False
    ).order_by(Message.created_at.asc()).all()

    other_user = User.query.get(user_id)

    return jsonify({
        'chat_id': chat.id,
        'other_user': {
            'id': other_user.id,
            'username': other_user.username,
            'display_name': other_user.display_name,
            'avatar': other_user.avatar,
            'last_seen': other_user.last_seen.isoformat() if other_user.last_seen else None
        },
        'messages': [message_to_dict(m) for m in messages]
    })


@chat_bp.route('/send_message', methods=['POST'])
@api_login_required
def send_message():
    chat_id = request.form.get('chat_id')
    content = request.form.get('content', '')
    reply_to_id = request.form.get('reply_to_id')

    message = Message(
        chat_id=chat_id,
        sender_id=session['user_id'],
        content=content,
        reply_to_id=reply_to_id
    )
    db.session.add(message)
    db.session.commit()

    return jsonify({'success': True, 'message': message_to_dict(message)})


@chat_bp.route('/edit_message', methods=['POST'])
@api_login_required
def edit_message():
    data = request.get_json()
    message_id = data.get('message_id')
    new_content = data.get('content')

    message = Message.query.get(message_id)
    if message and message.sender_id == session['user_id']:
        message.content = new_content
        message.is_edited = True
        message.updated_at = datetime.utcnow()
        db.session.commit()
        return jsonify({'success': True})

    return jsonify({'error': 'Unauthorized'}), 403


@chat_bp.route('/delete_message', methods=['POST'])
@api_login_required
def delete_message():
    data = request.get_json()
    message_id = data.get('message_id')

    message = Message.query.get(message_id)
    if message and message.sender_id == session['user_id']:
        message.is_deleted = True
        db.session.commit()
        return jsonify({'success': True})

    return jsonify({'error': 'Unauthorized'}), 403


@chat_bp.route('/forward_message', methods=['POST'])
@api_login_required
def forward_message():
    data = request.get_json()
    message_id = data.get('message_id')
    to_chat_id = data.get('to_chat_id')

    original = Message.query.get(message_id)
    if not original:
        return jsonify({'error': 'Message not found'}), 404

    forwarded = Message(
        chat_id=to_chat_id,
        sender_id=session['user_id'],
        content=f"↪️ {original.content}",
        file_type=original.file_type,
        file_path=original.file_path,
        file_name=original.file_name
    )
    db.session.add(forwarded)
    db.session.commit()

    return jsonify({'success': True, 'message': message_to_dict(forwarded)})


@chat_bp.route('/add_reaction', methods=['POST'])
@api_login_required
def add_reaction():
    from app.models import MessageReaction

    data = request.get_json()
    message_id = data.get('message_id')
    reaction = data.get('reaction')

    # Limit 3 reactions per user per message
    user_reactions = MessageReaction.query.filter_by(
        message_id=message_id,
        user_id=session['user_id']
    ).count()

    if user_reactions >= 3:
        return jsonify({'error': 'Maximum 3 reactions per message'}), 400

    existing = MessageReaction.query.filter_by(
        message_id=message_id,
        user_id=session['user_id'],
        reaction=reaction
    ).first()

    if existing:
        db.session.delete(existing)
    else:
        reaction_obj = MessageReaction(
            message_id=message_id,
            user_id=session['user_id'],
            reaction=reaction
        )
        db.session.add(reaction_obj)

    db.session.commit()

    reactions = MessageReaction.query.filter_by(message_id=message_id).all()
    return jsonify({
        'success': True,
        'reactions': [{'reaction': r.reaction, 'count': 1} for r in reactions]
    })


@chat_bp.route('/get_chats_list')
@api_login_required
def get_chats_list():
    chats = Chat.query.filter(
        (Chat.user1_id == session['user_id']) | (Chat.user2_id == session['user_id'])
    ).all()

    return jsonify([chat_to_dict(c) for c in chats])


@chat_bp.route('/search_users')
@api_login_required
def search_users():
    query = request.args.get('q', '').strip()
    if len(query) < 2:
        return jsonify([])

    users = User.query.filter(
        (User.username.ilike(f'%{query}%')) |
        (User.display_name.ilike(f'%{query}%')) |
        (User.phone.ilike(f'%{query}%')) |
        (User.unique_id.ilike(f'%{query}%'))
    ).filter(
        User.id != session['user_id'],
        User.is_deleted == False,
        User.registration_complete == True
    ).limit(20).all()

    return jsonify([user_to_dict(u) for u in users])


@chat_bp.route('/clear_chat', methods=['POST'])
@api_login_required
def clear_chat():
    data = request.get_json()
    chat_id = data.get('chat_id')

    Message.query.filter_by(chat_id=chat_id).update({'is_deleted': True})
    db.session.commit()

    return jsonify({'success': True})


def message_to_dict(message):
    return {
        'id': message.id,
        'chat_id': message.chat_id,
        'sender_id': message.sender_id,
        'content': message.content,
        'file_type': message.file_type,
        'file_path': message.file_path,
        'file_name': message.file_name,
        'reply_to_id': message.reply_to_id,
        'is_edited': message.is_edited,
        'is_deleted': message.is_deleted,
        'created_at': message.created_at.isoformat(),
        'reactions': get_message_reactions(message.id)
    }


def chat_to_dict(chat):
    other_user_id = chat.user2_id if chat.user1_id == session['user_id'] else chat.user1_id
    other_user = User.query.get(other_user_id)

    last_message = Message.query.filter_by(
        chat_id=chat.id,
        is_deleted=False
    ).order_by(Message.created_at.desc()).first()

    return {
        'id': chat.id,
        'is_pinned': chat.is_pinned,
        'other_user': user_to_dict(other_user),
        'last_message': message_to_dict(last_message) if last_message else None
    }


def user_to_dict(user):
    return {
        'id': user.id,
        'unique_id': user.unique_id,
        'username': user.username,
        'display_name': user.display_name,
        'avatar': user.avatar,
        'last_seen': user.last_seen.isoformat() if user.last_seen else None,
        'is_online': (datetime.utcnow() - user.last_seen).seconds < 300 if user.last_seen else False
    }


def get_message_reactions(message_id):
    from app.models import MessageReaction
    from sqlalchemy import func

    reactions = db.session.query(
        MessageReaction.reaction,
        func.count(MessageReaction.id).label('count')
    ).filter_by(
        message_id=message_id
    ).group_by(MessageReaction.reaction).all()

    return [{'reaction': r.reaction, 'count': r.count} for r in reactions]