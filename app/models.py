from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app import db, login_manager
import uuid
import secrets


# Association tables - these are ONLY for many-to-many relationships
# Remove duplicate table definitions

# Remove these - they're defined as classes below
# message_reactions = db.Table(...)  # DELETE THIS

class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    unique_id = db.Column(db.String(20), unique=True, nullable=False)
    phone = db.Column(db.String(20), unique=True, nullable=False)
    username = db.Column(db.String(50), unique=True)
    display_name = db.Column(db.String(100))
    password_hash = db.Column(db.String(200))
    avatar = db.Column(db.String(200))
    bio = db.Column(db.Text)
    birthday = db.Column(db.Date)
    theme = db.Column(db.String(20), default='light')
    font_size = db.Column(db.Integer, default=14)
    bubble_radius = db.Column(db.Integer, default=18)
    font_family = db.Column(db.String(100), default="'Unbounded', cursive")
    my_message_color = db.Column(db.String(20))
    their_message_color = db.Column(db.String(20))
    wallpaper = db.Column(db.String(50))
    wallpaper_image = db.Column(db.String(200))
    registration_complete = db.Column(db.Boolean, default=False)
    is_deleted = db.Column(db.Boolean, default=False)
    last_seen = db.Column(db.DateTime, default=datetime.utcnow)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Privacy settings
    privacy_last_seen = db.Column(db.String(20), default='everyone')
    privacy_profile_photo = db.Column(db.String(20), default='everyone')
    privacy_forward_messages = db.Column(db.String(20), default='everyone')
    privacy_calls = db.Column(db.String(20), default='everyone')
    privacy_messages = db.Column(db.String(20), default='everyone')

    # Relationships
    contacts = db.relationship('Contact', foreign_keys='Contact.user_id',
                               backref='user', lazy='dynamic')
    sessions = db.relationship('UserSession', backref='user', lazy='dynamic')
    stories = db.relationship('Story', backref='author', lazy='dynamic')
    blocked_users = db.relationship('BlockedUser', foreign_keys='BlockedUser.blocker_id',
                                    backref='blocker', lazy='dynamic')
    blocked_by = db.relationship('BlockedUser', foreign_keys='BlockedUser.blocked_id',
                                 backref='blocked', lazy='dynamic')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @staticmethod
    def generate_unique_id():
        while True:
            uid = secrets.token_hex(4)[:8]
            if not User.query.filter_by(unique_id=uid).first():
                return uid


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


class UserSession(db.Model):
    __tablename__ = 'user_sessions'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    session_token = db.Column(db.String(100), unique=True)
    ip_address = db.Column(db.String(45))
    user_agent = db.Column(db.Text)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_activity = db.Column(db.DateTime, default=datetime.utcnow)


class Chat(db.Model):
    __tablename__ = 'chats'

    id = db.Column(db.Integer, primary_key=True)
    user1_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    user2_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_pinned = db.Column(db.Boolean, default=False)
    pinned_at = db.Column(db.DateTime)

    user1 = db.relationship('User', foreign_keys=[user1_id])
    user2 = db.relationship('User', foreign_keys=[user2_id])
    messages = db.relationship('Message', backref='chat', lazy='dynamic')


class Message(db.Model):
    __tablename__ = 'messages'

    id = db.Column(db.Integer, primary_key=True)
    chat_id = db.Column(db.Integer, db.ForeignKey('chats.id'))
    group_id = db.Column(db.Integer, db.ForeignKey('groups.id'))
    channel_id = db.Column(db.Integer, db.ForeignKey('channels.id'))
    sender_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    content = db.Column(db.Text)
    file_type = db.Column(db.String(20))
    file_path = db.Column(db.String(200))
    file_name = db.Column(db.String(200))
    file_size = db.Column(db.Integer)
    reply_to_id = db.Column(db.Integer, db.ForeignKey('messages.id'))
    is_edited = db.Column(db.Boolean, default=False)
    is_deleted = db.Column(db.Boolean, default=False)
    is_forwarded = db.Column(db.Boolean, default=False)
    forwarded_from = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow)

    sender = db.relationship('User', backref='messages', foreign_keys=[sender_id])
    reply_to = db.relationship('Message', remote_side=[id], backref='replies')
    forwarded_user = db.relationship('User', foreign_keys=[forwarded_from])
    reactions = db.relationship('MessageReaction', backref='message', lazy='dynamic',
                                cascade='all, delete-orphan')


class MessageReaction(db.Model):
    __tablename__ = 'message_reactions'

    id = db.Column(db.Integer, primary_key=True)
    message_id = db.Column(db.Integer, db.ForeignKey('messages.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    reaction = db.Column(db.String(10))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', backref='message_reactions')

    __table_args__ = (
        db.UniqueConstraint('message_id', 'user_id', 'reaction', name='unique_reaction'),
    )


class Contact(db.Model):
    __tablename__ = 'contacts'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    contact_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    display_name = db.Column(db.String(100))
    is_favorite = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    contact = db.relationship('User', foreign_keys=[contact_id])


class BlockedUser(db.Model):
    __tablename__ = 'blocked_users'

    id = db.Column(db.Integer, primary_key=True)
    blocker_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    blocked_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    blocked_user = db.relationship('User', foreign_keys=[blocked_id])

    __table_args__ = (
        db.UniqueConstraint('blocker_id', 'blocked_id', name='unique_block'),
    )


class Group(db.Model):
    __tablename__ = 'groups'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    owner_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    avatar = db.Column(db.String(200))
    invite_link = db.Column(db.String(100), unique=True)
    is_public = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    owner = db.relationship('User', backref='owned_groups')
    members = db.relationship('GroupMember', backref='group', lazy='dynamic',
                              cascade='all, delete-orphan')
    messages = db.relationship('Message', backref='group', lazy='dynamic')

    @staticmethod
    def generate_invite_link():
        while True:
            link = secrets.token_urlsafe(16)[:24]
            if not Group.query.filter_by(invite_link=link).first():
                return link


class GroupMember(db.Model):
    __tablename__ = 'group_members'

    id = db.Column(db.Integer, primary_key=True)
    group_id = db.Column(db.Integer, db.ForeignKey('groups.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    role = db.Column(db.String(20), default='member')
    joined_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', backref='group_memberships')

    __table_args__ = (
        db.UniqueConstraint('group_id', 'user_id', name='unique_group_member'),
    )


class GroupPermission(db.Model):
    __tablename__ = 'group_permissions'

    id = db.Column(db.Integer, primary_key=True)
    group_id = db.Column(db.Integer, db.ForeignKey('groups.id'))
    role = db.Column(db.String(20))
    can_send_messages = db.Column(db.Boolean, default=True)
    can_add_members = db.Column(db.Boolean, default=False)
    can_remove_members = db.Column(db.Boolean, default=False)
    can_pin_messages = db.Column(db.Boolean, default=False)
    can_delete_messages = db.Column(db.Boolean, default=False)
    can_edit_group = db.Column(db.Boolean, default=False)

    group = db.relationship('Group', backref='permissions')

    __table_args__ = (
        db.UniqueConstraint('group_id', 'role', name='unique_group_role_permission'),
    )


class Channel(db.Model):
    __tablename__ = 'channels'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    owner_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    avatar = db.Column(db.String(200))
    invite_link = db.Column(db.String(100), unique=True)
    is_public = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    owner = db.relationship('User', backref='owned_channels')
    subscribers = db.relationship('ChannelSubscriber', backref='channel', lazy='dynamic',
                                  cascade='all, delete-orphan')
    admins = db.relationship('ChannelAdmin', backref='channel', lazy='dynamic',
                             cascade='all, delete-orphan')
    messages = db.relationship('Message', backref='channel', lazy='dynamic')

    @staticmethod
    def generate_invite_link():
        while True:
            link = secrets.token_urlsafe(16)[:24]
            if not Channel.query.filter_by(invite_link=link).first():
                return link


class ChannelSubscriber(db.Model):
    __tablename__ = 'channel_subscribers'

    id = db.Column(db.Integer, primary_key=True)
    channel_id = db.Column(db.Integer, db.ForeignKey('channels.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    subscribed_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', backref='channel_subscriptions')

    __table_args__ = (
        db.UniqueConstraint('channel_id', 'user_id', name='unique_subscriber'),
    )


class ChannelAdmin(db.Model):
    __tablename__ = 'channel_admins'

    id = db.Column(db.Integer, primary_key=True)
    channel_id = db.Column(db.Integer, db.ForeignKey('channels.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    can_post = db.Column(db.Boolean, default=True)
    can_edit = db.Column(db.Boolean, default=False)
    can_delete = db.Column(db.Boolean, default=False)
    can_add_admins = db.Column(db.Boolean, default=False)
    added_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', backref='admin_channels')

    __table_args__ = (
        db.UniqueConstraint('channel_id', 'user_id', name='unique_admin'),
    )


class Story(db.Model):
    __tablename__ = 'stories'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    file_type = db.Column(db.String(20))
    file_path = db.Column(db.String(200))
    caption = db.Column(db.Text)
    music_path = db.Column(db.String(200))
    privacy = db.Column(db.String(20), default='everyone')
    selected_users = db.Column(db.Text)  # JSON string of user IDs
    expires_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    views = db.relationship('StoryView', backref='story', lazy='dynamic',
                            cascade='all, delete-orphan')
    reactions = db.relationship('StoryReaction', backref='story', lazy='dynamic',
                                cascade='all, delete-orphan')
    interactions = db.relationship('StoryInteraction', backref='story', lazy='dynamic',
                                   cascade='all, delete-orphan')


class StoryView(db.Model):
    __tablename__ = 'story_views'

    id = db.Column(db.Integer, primary_key=True)
    story_id = db.Column(db.Integer, db.ForeignKey('stories.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    viewed_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', backref='story_views')

    __table_args__ = (
        db.UniqueConstraint('story_id', 'user_id', name='unique_view'),
    )


class StoryReaction(db.Model):
    __tablename__ = 'story_reactions'

    id = db.Column(db.Integer, primary_key=True)
    story_id = db.Column(db.Integer, db.ForeignKey('stories.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    reaction = db.Column(db.String(10))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', backref='story_reactions')


class StoryInteraction(db.Model):
    __tablename__ = 'story_interactions'

    id = db.Column(db.Integer, primary_key=True)
    story_id = db.Column(db.Integer, db.ForeignKey('stories.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    interaction_type = db.Column(db.String(20))
    content = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', backref='story_interactions')


class Call(db.Model):
    __tablename__ = 'calls'

    id = db.Column(db.Integer, primary_key=True)
    caller_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    receiver_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    call_type = db.Column(db.String(20))
    status = db.Column(db.String(20))
    duration = db.Column(db.Integer, default=0)
    started_at = db.Column(db.DateTime)
    ended_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    caller = db.relationship('User', foreign_keys=[caller_id], backref='calls_made')
    receiver = db.relationship('User', foreign_keys=[receiver_id], backref='calls_received')


class VideoCall(db.Model):
    __tablename__ = 'video_calls'

    id = db.Column(db.Integer, primary_key=True)
    room_id = db.Column(db.String(50), unique=True)
    creator_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    call_type = db.Column(db.String(20))
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    ended_at = db.Column(db.DateTime)

    creator = db.relationship('User', backref='video_calls_created')
    participants = db.relationship('VideoCallParticipant', backref='call', lazy='dynamic',
                                   cascade='all, delete-orphan')


class VideoCallParticipant(db.Model):
    __tablename__ = 'video_call_participants'

    id = db.Column(db.Integer, primary_key=True)
    call_id = db.Column(db.Integer, db.ForeignKey('video_calls.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    audio_only = db.Column(db.Boolean, default=False)
    joined_at = db.Column(db.DateTime, default=datetime.utcnow)
    left_at = db.Column(db.DateTime)

    user = db.relationship('User', backref='video_participations')


class PreloadedAvatar(db.Model):
    __tablename__ = 'preloaded_avatars'

    id = db.Column(db.Integer, primary_key=True)
    file_name = db.Column(db.String(100))
    name = db.Column(db.String(100))
    category = db.Column(db.String(50))
    url = db.Column(db.String(200))


class RecentSearch(db.Model):
    __tablename__ = 'recent_searches'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    query = db.Column(db.String(200))
    search_type = db.Column(db.String(20))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', backref='recent_searches')