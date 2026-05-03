from flask import Blueprint, render_template, request, session, jsonify, redirect, url_for
from app.models import VideoCall, VideoCallParticipant
from app import db
from app.utils.decorators import login_required, api_login_required
from app.config import Config
from datetime import datetime
import secrets

video_bp = Blueprint('video', __name__)


def generate_room_id():
    """Generate unique room ID"""
    return secrets.token_urlsafe(12)[:16]


@video_bp.route('/create_room', methods=['POST'])
@api_login_required
def create_room():
    """Create a new video call room"""
    data = request.get_json() or {}
    call_type = data.get('call_type', 'video')

    room_id = generate_room_id()

    video_call = VideoCall(
        room_id=room_id,
        creator_id=session['user_id'],
        call_type=call_type
    )
    db.session.add(video_call)
    db.session.commit()

    return jsonify({
        'success': True,
        'room_id': room_id,
        'call_id': video_call.id,
        'video_server_url': Config.VIDEO_SERVER_URL
    })


@video_bp.route('/<room_id>')
@login_required
def video_room(room_id):
    """Video call room page"""
    video_call = VideoCall.query.filter_by(
        room_id=room_id,
        is_active=True
    ).first()

    if not video_call:
        return render_template('errors/404.html'), 404

    return render_template('video/room.html',
                           room_id=room_id,
                           call_type=video_call.call_type,
                           creator_id=video_call.creator_id,
                           video_server_url=Config.VIDEO_SERVER_URL)


@video_bp.route('/join/<room_id>', methods=['POST'])
@api_login_required
def join_room(room_id):
    """Join a video call room"""
    video_call = VideoCall.query.filter_by(
        room_id=room_id,
        is_active=True
    ).first()

    if not video_call:
        return jsonify({'success': False, 'error': 'Room not found'}), 404

    data = request.get_json() or {}
    audio_only = data.get('audio_only', False)

    # Add participant
    participant = VideoCallParticipant(
        call_id=video_call.id,
        user_id=session['user_id'],
        audio_only=audio_only
    )
    db.session.add(participant)
    db.session.commit()

    return jsonify({
        'success': True,
        'room_id': room_id,
        'call_type': video_call.call_type,
        'video_server_url': Config.VIDEO_SERVER_URL
    })


@video_bp.route('/<room_id>/leave', methods=['POST'])
@api_login_required
def leave_room(room_id):
    """Leave a video call room"""
    video_call = VideoCall.query.filter_by(
        room_id=room_id,
        is_active=True
    ).first()

    if video_call:
        participant = VideoCallParticipant.query.filter_by(
            call_id=video_call.id,
            user_id=session['user_id'],
            left_at=None
        ).first()

        if participant:
            participant.left_at = datetime.utcnow()
            db.session.commit()

    return jsonify({'success': True})


@video_bp.route('/<room_id>/end', methods=['POST'])
@api_login_required
def end_room(room_id):
    """End a video call (creator only)"""
    video_call = VideoCall.query.filter_by(
        room_id=room_id,
        is_active=True
    ).first()

    if not video_call:
        return jsonify({'error': 'Room not found'}), 404

    if video_call.creator_id != session['user_id']:
        return jsonify({'success': False, 'error': 'Not authorized'}), 403

    video_call.is_active = False
    video_call.ended_at = datetime.utcnow()

    # Mark all participants as left
    VideoCallParticipant.query.filter_by(
        call_id=video_call.id,
        left_at=None
    ).update({'left_at': datetime.utcnow()})

    db.session.commit()

    return jsonify({'success': True})


@video_bp.route('/<room_id>/participants')
@api_login_required
def get_participants(room_id):
    """Get room participants"""
    video_call = VideoCall.query.filter_by(
        room_id=room_id,
        is_active=True
    ).first()

    if not video_call:
        return jsonify({'error': 'Room not found'}), 404

    participants = VideoCallParticipant.query.filter_by(
        call_id=video_call.id,
        left_at=None
    ).all()

    from app.models import User

    participants_data = []
    for p in participants:
        user = User.query.get(p.user_id)
        if user:
            participants_data.append({
                'user_id': user.id,
                'username': user.username,
                'display_name': user.display_name,
                'avatar': user.avatar,
                'audio_only': p.audio_only
            })

    return jsonify({'participants': participants_data})


@video_bp.route('/active_calls')
@api_login_required
def get_active_calls():
    """Get active video calls"""
    active_calls = VideoCall.query.filter_by(is_active=True).all()

    return jsonify([{
        'id': c.id,
        'room_id': c.room_id,
        'creator_id': c.creator_id,
        'call_type': c.call_type,
        'created_at': c.created_at.isoformat() if c.created_at else None
    } for c in active_calls])