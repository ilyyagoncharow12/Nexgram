import os
from datetime import timedelta


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or '6TinlinG_+pO0IM9U98h87gb^Y9UBouVFTRDgnh;//,ijnuYTFDRSreHJydRsrxE'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///nexgram.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'app', 'uploads')
    MAX_CONTENT_LENGTH = 500 * 1024 * 1024
    PERMANENT_SESSION_LIFETIME = timedelta(days=30)

    # Video server URL for WebRTC signaling
    VIDEO_SERVER_URL = os.environ.get('VIDEO_SERVER_URL', 'http://localhost:5001')

    # File upload settings
    ALLOWED_EXTENSIONS = {
        'image': {'png', 'jpg', 'jpeg', 'gif', 'webp', 'bmp', 'tiff', 'svg'},
        'video': {'mp4', 'webm', 'avi', 'mov', 'mkv', 'flv', 'wmv', 'm4v', '3gp'},
        'audio': {'mp3', 'wav', 'ogg', 'm4a', 'aac', 'flac'},
        'document': {'pdf', 'doc', 'docx', 'txt', 'zip', 'rar', '7z'}
    }