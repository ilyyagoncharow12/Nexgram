from flask import Blueprint, request, session, jsonify, send_file
from app.config import Config
from app.utils.decorators import api_login_required
import os
import uuid
from werkzeug.utils import secure_filename
from PIL import Image

file_bp = Blueprint('file', __name__)


@file_bp.route('/upload', methods=['POST'])
@api_login_required
def upload_file():
    """Upload a file"""
    if 'file' not in request.files:
        return jsonify({'error': 'No file'}), 400

    file = request.files['file']
    if not file.filename:
        return jsonify({'error': 'No file selected'}), 400

    ext = file.filename.rsplit('.', 1)[1].lower()
    filename = secure_filename(file.filename)
    unique_name = f"{uuid.uuid4().hex}.{ext}"

    # Determine file type and folder
    if ext in Config.ALLOWED_EXTENSIONS['image']:
        folder = 'photos'
        file_type = 'photo'
    elif ext in Config.ALLOWED_EXTENSIONS['video']:
        folder = 'videos'
        file_type = 'video'
    elif ext in Config.ALLOWED_EXTENSIONS['audio']:
        folder = 'audio'
        file_type = 'audio'
    else:
        folder = 'files'
        file_type = 'document'

    file_path = os.path.join(Config.UPLOAD_FOLDER, folder, unique_name)
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    file.save(file_path)

    file_size = os.path.getsize(file_path)

    # Generate thumbnail for images
    thumbnail_path = None
    if file_type == 'photo':
        try:
            img = Image.open(file_path)
            img.thumbnail((200, 200))
            thumb_name = f"thumb_{unique_name}"
            thumb_path = os.path.join(Config.UPLOAD_FOLDER, 'photos', thumb_name)
            img.save(thumb_path)
            thumbnail_path = f"uploads/photos/{thumb_name}"
        except:
            pass

    return jsonify({
        'success': True,
        'file_type': file_type,
        'file_path': f"uploads/{folder}/{unique_name}",
        'file_name': filename,
        'file_size': file_size,
        'thumbnail': thumbnail_path
    })


@file_bp.route('/download/<path:filename>')
def download_file(filename):
    """Download a file"""
    file_path = os.path.join(Config.UPLOAD_FOLDER, filename)
    if not os.path.exists(file_path):
        return jsonify({'error': 'File not found'}), 404
    return send_file(file_path)


@file_bp.route('/upload_wallpaper', methods=['POST'])
@api_login_required
def upload_wallpaper():
    """Upload chat wallpaper"""
    if 'wallpaper' not in request.files:
        return jsonify({'error': 'No file'}), 400

    file = request.files['wallpaper']
    if not file.filename:
        return jsonify({'error': 'No file selected'}), 400

    ext = file.filename.rsplit('.', 1)[1].lower()
    if ext not in Config.ALLOWED_EXTENSIONS['image']:
        return jsonify({'error': 'Invalid file type'}), 400

    unique_name = f"{uuid.uuid4().hex}.{ext}"
    file_path = os.path.join(Config.UPLOAD_FOLDER, 'wallpapers', unique_name)
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    file.save(file_path)

    return jsonify({
        'success': True,
        'wallpaper_image': f"uploads/wallpapers/{unique_name}"
    })