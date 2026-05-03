from datetime import datetime
from app.models import User


def init_helpers(app):
    """Initialize helper functions"""

    @app.context_processor
    def utility_processor():
        return {
            'now': datetime.utcnow,
            'get_user': get_user_by_id
        }


def get_user_by_id(user_id):
    """Get user by ID"""
    return User.query.get(user_id)


def format_datetime(dt):
    """Format datetime for display"""
    if not dt:
        return ''

    now = datetime.utcnow()
    diff = now - dt

    if diff.days == 0:
        if diff.seconds < 60:
            return 'Just now'
        elif diff.seconds < 3600:
            return f'{diff.seconds // 60}m ago'
        else:
            return f'{diff.seconds // 3600}h ago'
    elif diff.days == 1:
        return 'Yesterday'
    elif diff.days < 7:
        return f'{diff.days}d ago'
    else:
        return dt.strftime('%d.%m.%Y')