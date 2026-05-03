from flask import Blueprint, request, session, jsonify
from app.models import Story, StoryView, StoryReaction, User
from app import db
from app.utils.decorators import api_login_required
from app.config import Config
from datetime import datetime, timedelta
import uuid
import os

story_bp = Blueprint('story', __name__)


@story_bp.route('/upload', methods=['POST'])
@api_login_required
def upload_story():
    file = request.files.get('file')
    caption = request.form.get('caption', '')
    music = request.files.get('music')
    privacy = request.form.get('privacy', 'everyone')

    if not file:
        return jsonify({'error': 'No file'}), 400

    ext = file.filename.rsplit('.', 1)[1].lower()
    filename = f"{uuid.uuid4().hex}.{ext}"
    file_path = os.path.join(Config.STORY_FOLDER, filename)
    file.save(file_path)

    music_path = None
    if music and music.filename:
        music_ext = music.filename.rsplit('.', 1)[1].lower()
        music_name = f"{uuid.uuid4().hex}.{music_ext}"
        music_path = os.path.join(Config.STORY_MUSIC_FOLDER, music_name)
        music.save(music_path)

    file_type = 'video' if ext in Config.ALLOWED_EXTENSIONS['video'] else 'photo'

    story = Story(
        user_id=session['user_id'],
        file_type=file_type,
        file_path=f"uploads/stories/{filename}",
        caption=caption,
        music_path=f"uploads/story_music/{music_name}" if music_path else None,
        privacy=privacy,
        expires_at=datetime.utcnow() + timedelta(hours=24)
    )
    db.session.add(story)
    db.session.commit()

    return jsonify({'success': True, 'story_id': story.id})


@story_bp.route('/get_stories')
@api_login_required
def get_stories():
    stories = Story.query.filter(
        Story.expires_at > datetime.utcnow()
    ).order_by(Story.created_at.desc()).all()

    return jsonify([story_to_dict(s) for s in stories])


@story_bp.route('/view', methods=['POST'])
@api_login_required
def view_story():
    data = request.get_json()
    story_id = data['story_id']

    view = StoryView(
        story_id=story_id,
        user_id=session['user_id']
    )
    db.session.add(view)
    db.session.commit()

    return jsonify({'success': True})


@story_bp.route('/react', methods=['POST'])
@api_login_required
def react_story():
    data = request.get_json()
    story_id = data['story_id']
    reaction = data['reaction']

    existing = StoryReaction.query.filter_by(
        story_id=story_id,
        user_id=session['user_id']
    ).first()

    if existing:
        existing.reaction = reaction
    else:
        story_reaction = StoryReaction(
            story_id=story_id,
            user_id=session['user_id'],
            reaction=reaction
        )
        db.session.add(story_reaction)

    db.session.commit()

    return jsonify({'success': True})


def story_to_dict(story):
    user = User.query.get(story.user_id)
    return {
        'id': story.id,
        'user_id': story.user_id,
        'username': user.username,
        'display_name': user.display_name,
        'avatar': user.avatar,
        'file_type': story.file_type,
        'file_path': story.file_path,
        'caption': story.caption,
        'music_path': story.music_path,
        'created_at': story.created_at.isoformat(),
        'expires_at': story.expires_at.isoformat(),
        'views_count': story.views.count(),
        'reactions': [{'reaction': r.reaction, 'user_id': r.user_id} for r in story.reactions]
    }