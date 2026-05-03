from flask import Blueprint, request, session, jsonify
from app.models import Group, GroupMember, GroupPermission, Message, User
from app import db
from app.utils.decorators import api_login_required
from datetime import datetime

group_bp = Blueprint('group', __name__)


@group_bp.route('/create', methods=['POST'])
@api_login_required
def create_group():
    """Create a new group"""
    data = request.get_json()
    name = data.get('name')
    description = data.get('description', '')
    is_public = data.get('is_public', True)

    if not name:
        return jsonify({'success': False, 'error': 'Название обязательно'}), 400

    group = Group(
        name=name,
        description=description,
        owner_id=session['user_id'],
        is_public=is_public,
        invite_link=Group.generate_invite_link()
    )
    db.session.add(group)
    db.session.commit()

    # Add creator as owner/member
    member = GroupMember(
        group_id=group.id,
        user_id=session['user_id'],
        role='owner'
    )
    db.session.add(member)

    # Create default permissions
    admin_perms = GroupPermission(
        group_id=group.id,
        role='admin',
        can_send_messages=True,
        can_add_members=True,
        can_remove_members=True,
        can_pin_messages=True,
        can_delete_messages=True,
        can_edit_group=True
    )

    member_perms = GroupPermission(
        group_id=group.id,
        role='member',
        can_send_messages=True,
        can_add_members=False,
        can_remove_members=False,
        can_pin_messages=False,
        can_delete_messages=False,
        can_edit_group=False
    )

    db.session.add(admin_perms)
    db.session.add(member_perms)
    db.session.commit()

    return jsonify({
        'success': True,
        'group_id': group.id,
        'invite_link': group.invite_link
    })


@group_bp.route('/<int:group_id>')
@api_login_required
def get_group(group_id):
    """Get group details with messages and members"""
    group = Group.query.get(group_id)
    if not group:
        return jsonify({'error': 'Group not found'}), 404

    # Check if user is member
    member = GroupMember.query.filter_by(
        group_id=group_id,
        user_id=session['user_id']
    ).first()

    if not member:
        return jsonify({'error': 'Not a member'}), 403

    # Get messages
    messages = Message.query.filter_by(
        group_id=group_id,
        is_deleted=False
    ).order_by(Message.created_at.desc()).limit(50).all()

    # Get members
    members = GroupMember.query.filter_by(group_id=group_id).all()

    # Get permissions for user's role
    permissions = GroupPermission.query.filter_by(
        group_id=group_id,
        role=member.role
    ).first()

    return jsonify({
        'group': group_to_dict(group),
        'messages': [message_to_dict(m) for m in reversed(messages)],
        'members': [member_to_dict(m) for m in members],
        'user_role': member.role,
        'permissions': permission_to_dict(permissions) if permissions else None
    })


@group_bp.route('/<int:group_id>/update', methods=['POST'])
@api_login_required
def update_group(group_id):
    """Update group settings"""
    data = request.get_json()

    # Check permissions
    member = GroupMember.query.filter_by(
        group_id=group_id,
        user_id=session['user_id']
    ).first()

    if not member or member.role not in ['owner', 'admin']:
        return jsonify({'success': False, 'error': 'Недостаточно прав'}), 403

    # Check if role can edit group
    permissions = GroupPermission.query.filter_by(
        group_id=group_id,
        role=member.role
    ).first()

    if member.role != 'owner' and permissions and not permissions.can_edit_group:
        return jsonify({'success': False, 'error': 'Недостаточно прав'}), 403

    group = Group.query.get(group_id)
    if not group:
        return jsonify({'error': 'Group not found'}), 404

    if 'name' in data:
        group.name = data['name']
    if 'description' in data:
        group.description = data['description']
    if 'is_public' in data:
        group.is_public = data['is_public']

    db.session.commit()

    return jsonify({'success': True, 'group': group_to_dict(group)})


@group_bp.route('/<int:group_id>/delete', methods=['POST'])
@api_login_required
def delete_group(group_id):
    """Delete group (owner only)"""
    member = GroupMember.query.filter_by(
        group_id=group_id,
        user_id=session['user_id']
    ).first()

    if not member or member.role != 'owner':
        return jsonify({'success': False, 'error': 'Только владелец может удалить группу'}), 403

    group = Group.query.get(group_id)
    if not group:
        return jsonify({'error': 'Group not found'}), 404

    db.session.delete(group)
    db.session.commit()

    return jsonify({'success': True})


@group_bp.route('/join/<invite_link>')
@api_login_required
def join_group(invite_link):
    """Join group by invite link"""
    group = Group.query.filter_by(invite_link=invite_link).first()
    if not group:
        return jsonify({'success': False, 'error': 'Группа не найдена'}), 404

    # Check if already member
    existing = GroupMember.query.filter_by(
        group_id=group.id,
        user_id=session['user_id']
    ).first()

    if existing:
        return jsonify({
            'success': True,
            'already_member': True,
            'group_id': group.id
        })

    # Check if group is public or user is invited
    if not group.is_public:
        return jsonify({'success': False, 'error': 'Группа приватная'}), 403

    # Add member
    member = GroupMember(
        group_id=group.id,
        user_id=session['user_id'],
        role='member'
    )
    db.session.add(member)
    db.session.commit()

    return jsonify({
        'success': True,
        'group_id': group.id,
        'group': group_to_dict(group)
    })


@group_bp.route('/<int:group_id>/leave', methods=['POST'])
@api_login_required
def leave_group(group_id):
    """Leave group"""
    member = GroupMember.query.filter_by(
        group_id=group_id,
        user_id=session['user_id']
    ).first()

    if not member:
        return jsonify({'error': 'Not a member'}), 404

    if member.role == 'owner':
        return jsonify(
            {'success': False, 'error': 'Владелец не может покинуть группу. Удалите группу или передайте права.'}), 400

    db.session.delete(member)
    db.session.commit()

    return jsonify({'success': True})


@group_bp.route('/<int:group_id>/members')
@api_login_required
def get_members(group_id):
    """Get group members"""
    member = GroupMember.query.filter_by(
        group_id=group_id,
        user_id=session['user_id']
    ).first()

    if not member:
        return jsonify({'error': 'Not a member'}), 403

    members = GroupMember.query.filter_by(group_id=group_id).all()
    return jsonify([member_to_dict(m) for m in members])


@group_bp.route('/<int:group_id>/add_member', methods=['POST'])
@api_login_required
def add_member(group_id):
    """Add member to group"""
    data = request.get_json()
    user_id = data.get('user_id')

    # Check permissions
    member = GroupMember.query.filter_by(
        group_id=group_id,
        user_id=session['user_id']
    ).first()

    if not member:
        return jsonify({'error': 'Not a member'}), 403

    permissions = GroupPermission.query.filter_by(
        group_id=group_id,
        role=member.role
    ).first()

    if member.role not in ['owner', 'admin'] or (permissions and not permissions.can_add_members):
        return jsonify({'success': False, 'error': 'Недостаточно прав'}), 403

    # Check if user already member
    existing = GroupMember.query.filter_by(
        group_id=group_id,
        user_id=user_id
    ).first()

    if existing:
        return jsonify({'success': False, 'error': 'Пользователь уже в группе'}), 400

    # Add user
    new_member = GroupMember(
        group_id=group_id,
        user_id=user_id,
        role='member'
    )
    db.session.add(new_member)
    db.session.commit()

    return jsonify({'success': True})


@group_bp.route('/<int:group_id>/remove_member', methods=['POST'])
@api_login_required
def remove_member(group_id):
    """Remove member from group"""
    data = request.get_json()
    user_id = data.get('user_id')

    # Check permissions
    member = GroupMember.query.filter_by(
        group_id=group_id,
        user_id=session['user_id']
    ).first()

    if not member:
        return jsonify({'error': 'Not a member'}), 403

    permissions = GroupPermission.query.filter_by(
        group_id=group_id,
        role=member.role
    ).first()

    if member.role not in ['owner', 'admin'] or (permissions and not permissions.can_remove_members):
        return jsonify({'success': False, 'error': 'Недостаточно прав'}), 403

    # Cannot remove owner
    target = GroupMember.query.filter_by(
        group_id=group_id,
        user_id=user_id
    ).first()

    if not target:
        return jsonify({'error': 'User not found in group'}), 404

    if target.role == 'owner':
        return jsonify({'success': False, 'error': 'Нельзя удалить владельца'}), 400

    db.session.delete(target)
    db.session.commit()

    return jsonify({'success': True})


@group_bp.route('/<int:group_id>/update_role', methods=['POST'])
@api_login_required
def update_member_role(group_id):
    """Update member role (owner/admin/member)"""
    data = request.get_json()
    user_id = data.get('user_id')
    new_role = data.get('role')

    if new_role not in ['admin', 'member']:
        return jsonify({'success': False, 'error': 'Неверная роль'}), 400

    # Only owner can change roles
    member = GroupMember.query.filter_by(
        group_id=group_id,
        user_id=session['user_id']
    ).first()

    if not member or member.role != 'owner':
        return jsonify({'success': False, 'error': 'Только владелец может менять роли'}), 403

    target = GroupMember.query.filter_by(
        group_id=group_id,
        user_id=user_id
    ).first()

    if not target:
        return jsonify({'error': 'User not found in group'}), 404

    if target.role == 'owner':
        return jsonify({'success': False, 'error': 'Нельзя изменить роль владельца'}), 400

    target.role = new_role
    db.session.commit()

    return jsonify({'success': True})


@group_bp.route('/<int:group_id>/transfer_ownership', methods=['POST'])
@api_login_required
def transfer_ownership(group_id):
    """Transfer group ownership to another member"""
    data = request.get_json()
    new_owner_id = data.get('user_id')

    # Only owner can transfer
    member = GroupMember.query.filter_by(
        group_id=group_id,
        user_id=session['user_id']
    ).first()

    if not member or member.role != 'owner':
        return jsonify({'success': False, 'error': 'Только владелец может передать права'}), 403

    # Get new owner
    new_owner = GroupMember.query.filter_by(
        group_id=group_id,
        user_id=new_owner_id
    ).first()

    if not new_owner:
        return jsonify({'error': 'User not found in group'}), 404

    # Update group owner
    group = Group.query.get(group_id)
    group.owner_id = new_owner_id

    # Update roles
    member.role = 'admin'
    new_owner.role = 'owner'

    db.session.commit()

    return jsonify({'success': True})


@group_bp.route('/<int:group_id>/permissions', methods=['GET', 'POST'])
@api_login_required
def manage_permissions(group_id):
    """Get or update group permissions"""
    member = GroupMember.query.filter_by(
        group_id=group_id,
        user_id=session['user_id']
    ).first()

    if not member or member.role != 'owner':
        return jsonify({'success': False, 'error': 'Только владелец может управлять правами'}), 403

    if request.method == 'GET':
        permissions = GroupPermission.query.filter_by(group_id=group_id).all()
        return jsonify([permission_to_dict(p) for p in permissions])

    # POST - Update permissions
    data = request.get_json()
    role = data.get('role')

    if role not in ['admin', 'member']:
        return jsonify({'success': False, 'error': 'Неверная роль'}), 400

    permissions = GroupPermission.query.filter_by(
        group_id=group_id,
        role=role
    ).first()

    if not permissions:
        permissions = GroupPermission(group_id=group_id, role=role)
        db.session.add(permissions)

    # Update fields
    for field in ['can_send_messages', 'can_add_members', 'can_remove_members',
                  'can_pin_messages', 'can_delete_messages', 'can_edit_group']:
        if field in data:
            setattr(permissions, field, data[field])

    db.session.commit()

    return jsonify({'success': True, 'permissions': permission_to_dict(permissions)})


@group_bp.route('/search')
@api_login_required
def search_groups():
    """Search for public groups"""
    query = request.args.get('q', '').strip()
    if len(query) < 2:
        return jsonify([])

    groups = Group.query.filter(
        Group.name.ilike(f'%{query}%'),
        Group.is_public == True
    ).limit(20).all()

    return jsonify([group_to_dict(g) for g in groups])


@group_bp.route('/my')
@api_login_required
def my_groups():
    """Get user's groups"""
    memberships = GroupMember.query.filter_by(
        user_id=session['user_id']
    ).all()

    groups_data = []
    for membership in memberships:
        group = Group.query.get(membership.group_id)
        if group:
            group_info = group_to_dict(group)
            group_info['my_role'] = membership.role
            groups_data.append(group_info)

    return jsonify(groups_data)


@group_bp.route('/<int:group_id>/messages')
@api_login_required
def get_messages(group_id):
    """Get group messages with pagination"""
    member = GroupMember.query.filter_by(
        group_id=group_id,
        user_id=session['user_id']
    ).first()

    if not member:
        return jsonify({'error': 'Not a member'}), 403

    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)

    messages = Message.query.filter_by(
        group_id=group_id,
        is_deleted=False
    ).order_by(
        Message.created_at.desc()
    ).paginate(page=page, per_page=per_page, error_out=False)

    return jsonify({
        'messages': [message_to_dict(m) for m in messages.items],
        'has_next': messages.has_next,
        'total': messages.total
    })


@group_bp.route('/<int:group_id>/search_messages')
@api_login_required
def search_group_messages(group_id):
    """Search messages in group"""
    member = GroupMember.query.filter_by(
        group_id=group_id,
        user_id=session['user_id']
    ).first()

    if not member:
        return jsonify({'error': 'Not a member'}), 403

    query = request.args.get('q', '').strip()
    if len(query) < 2:
        return jsonify({'messages': []})

    messages = Message.query.filter(
        Message.group_id == group_id,
        Message.is_deleted == False,
        Message.content.ilike(f'%{query}%')
    ).order_by(Message.created_at.desc()).limit(50).all()

    return jsonify({
        'messages': [message_to_dict(m) for m in messages]
    })


# Helper functions
def group_to_dict(group):
    """Convert group object to dictionary"""
    members_count = GroupMember.query.filter_by(group_id=group.id).count()

    return {
        'id': group.id,
        'name': group.name,
        'description': group.description,
        'owner_id': group.owner_id,
        'avatar': group.avatar,
        'invite_link': group.invite_link,
        'is_public': group.is_public,
        'members_count': members_count,
        'created_at': group.created_at.isoformat() if group.created_at else None
    }


def member_to_dict(member):
    """Convert member object to dictionary"""
    user = User.query.get(member.user_id)
    return {
        'id': member.id,
        'user_id': member.user_id,
        'username': user.username if user else None,
        'display_name': user.display_name if user else None,
        'avatar': user.avatar if user else None,
        'role': member.role,
        'joined_at': member.joined_at.isoformat() if member.joined_at else None
    }


def permission_to_dict(permission):
    """Convert permission object to dictionary"""
    return {
        'id': permission.id,
        'group_id': permission.group_id,
        'role': permission.role,
        'can_send_messages': permission.can_send_messages,
        'can_add_members': permission.can_add_members,
        'can_remove_members': permission.can_remove_members,
        'can_pin_messages': permission.can_pin_messages,
        'can_delete_messages': permission.can_delete_messages,
        'can_edit_group': permission.can_edit_group
    }


def message_to_dict(message):
    """Convert message object to dictionary"""
    sender = User.query.get(message.sender_id)

    return {
        'id': message.id,
        'group_id': message.group_id,
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
        'is_forwarded': message.is_forwarded,
        'created_at': message.created_at.isoformat() if message.created_at else None,
        'updated_at': message.updated_at.isoformat() if message.updated_at else None
    }