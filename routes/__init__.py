# Routes package
from routes.auth import auth_bp
from routes.dashboard import dashboard_bp
from routes.files import files_bp
from routes.folders import folders_bp
from routes.settings import settings_bp

__all__ = ['auth_bp', 'dashboard_bp', 'files_bp', 'folders_bp', 'settings_bp']
