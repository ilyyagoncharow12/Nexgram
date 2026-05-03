from flask import Blueprint, request, session, jsonify
from app.models import Call, User
from app import db
from app.utils.decorators import api_login_required
from datetime import datetime

call_bp = Blueprint('call', __name__)


@call_bp.route('/make', methods=['POST'])
@api_login_required
def make_call():
    """Initiate a call"""
    data = request.get_json()
    receiver_id = data.get('receiver_id')
    call_type = data.get('call_type', 'audio')

    if not receiver_id:
        return jsonify({'error': 'receiver_id required'}), 400

    receiver = User.query.get(receiver_id)
    if not receiver:
        return jsonify({'error': 'Receiver not found'}), 404

    call = Call(
        caller_id=session['user_id'],
        receiver_id=receiver_id,
        call_type=call_type,
        status='ringing'
    )
    db.session.add(call)
    db.session.commit()

    return jsonify({
        'success': True,
        'call_id': call.id,
        'call': call_to_dict(call)
    })


@call_bp.route('/<int:call_id>/answer', methods=['POST'])
@api_login_required
def answer_call(call_id):
    """Answer an incoming call"""
    call = Call.query.get(call_id)
    if not call:
        return jsonify({'error': 'Call not found'}), 404

    if call.receiver_id != session['user_id']:
        return jsonify({'error': 'Not authorized'}), 403

    call.status = 'answered'
    call.started_at = datetime.utcnow()
    db.session.commit()

    return jsonify({'success': True, 'call': call_to_dict(call)})


@call_bp.route('/<int:call_id>/end', methods=['POST'])
@api_login_required
def end_call(call_id):
    """End a call"""
    data = request.get_json()
    duration = data.get('duration', 0)

    call = Call.query.get(call_id)
    if not call:
        return jsonify({'error': 'Call not found'}), 404

    if call.caller_id != session['user_id'] and call.receiver_id != session['user_id']:
        return jsonify({'error': 'Not authorized'}), 403

    call.status = 'ended'
    call.duration = duration
    call.ended_at = datetime.utcnow()
    db.session.commit()

    return jsonify({'success': True, 'call': call_to_dict(call)})


@call_bp.route('/<int:call_id>/miss', methods=['POST'])
@api_login_required
def miss_call(call_id):
    """Mark call as missed"""
    call = Call.query.get(call_id)
    if not call:
        return jsonify({'error': 'Call not found'}), 404

    if call.receiver_id != session['user_id']:
        return jsonify({'error': 'Not authorized'}), 403

    call.status = 'missed'
    db.session.commit()

    return jsonify({'success': True, 'call': call_to_dict(call)})


@call_bp.route('/history')
@api_login_required
def call_history():
    """Get call history"""
    calls = Call.query.filter(
        (Call.caller_id == session['user_id']) | (Call.receiver_id == session['user_id'])
    ).order_by(Call.created_at.desc()).limit(50).all()

    return jsonify([call_to_dict(c) for c in calls])


@call_bp.route('/<int:call_id>')
@api_login_required
def get_call(call_id):
    """Get call details"""
    call = Call.query.get(call_id)
    if not call:
        return jsonify({'error': 'Call not found'}), 404

    if call.caller_id != session['user_id'] and call.receiver_id != session['user_id']:
        return jsonify({'error': 'Not authorized'}), 403

    return jsonify(call_to_dict(call))


def call_to_dict(call):
    """Convert call object to dictionary"""
    caller = User.query.get(call.caller_id)
    receiver = User.query.get(call.receiver_id)

    return {
        'id': call.id,
        'caller_id': call.caller_id,
        'caller_name': caller.display_name or caller.username if caller else 'Unknown',
        'caller_avatar': caller.avatar if caller else None,
        'receiver_id': call.receiver_id,
        'receiver_name': receiver.display_name or receiver.username if receiver else 'Unknown',
        'receiver_avatar': receiver.avatar if receiver else None,
        'call_type': call.call_type,
        'status': call.status,
        'duration': call.duration,
        'started_at': call.started_at.isoformat() if call.started_at else None,
        'ended_at': call.ended_at.isoformat() if call.ended_at else None,
        'created_at': call.created_at.isoformat() if call.created_at else None
    }