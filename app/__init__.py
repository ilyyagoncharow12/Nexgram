from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from app.config import Config
import os

db = SQLAlchemy()
login_manager = LoginManager()


def create_app():
    app = Flask(__name__,
                template_folder='../templates',
                static_folder='../static')
    app.config.from_object(Config)

    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.auth_page'

    # Create upload directories
    create_upload_dirs(app)

    # Import models
    with app.app_context():
        from app import models
        db.create_all()

    # Register blueprints
    from app.routes.auth import auth_bp
    from app.routes.chat import chat_bp
    from app.routes.group import group_bp
    from app.routes.channel import channel_bp
    from app.routes.story import story_bp
    from app.routes.call import call_bp
    from app.routes.profile import profile_bp
    from app.routes.file import file_bp
    from app.routes.main import main_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(chat_bp, url_prefix='/api')
    app.register_blueprint(group_bp, url_prefix='/api')
    app.register_blueprint(channel_bp, url_prefix='/api')
    app.register_blueprint(story_bp, url_prefix='/api')
    app.register_blueprint(call_bp, url_prefix='/api')
    app.register_blueprint(profile_bp, url_prefix='/api')
    app.register_blueprint(file_bp, url_prefix='/api')

    # Error handlers
    from app.errors import register_error_handlers
    register_error_handlers(app)

    return app


def create_upload_dirs(app):
    dirs = ['avatars', 'files', 'photos', 'videos', 'audio',
            'wallpapers', 'stories', 'story_music']
    for dir_name in dirs:
        path = os.path.join(app.config['UPLOAD_FOLDER'], dir_name)
        os.makedirs(path, exist_ok=True)

    avatar_swg = os.path.join(app.static_folder, 'avatar-swg')
    os.makedirs(avatar_swg, exist_ok=True)