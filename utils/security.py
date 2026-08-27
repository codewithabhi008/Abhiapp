import os
import re
from functools import wraps
from flask import session, jsonify, request, redirect, url_for, g
from database import db
from models import User

def login_required(f):
    """Decorator ensuring that only authenticated users can access the endpoint."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user_id = session.get('user_id')
        if not user_id:
            # Check if this is an API or AJAX request
            if request.is_json or request.path.startswith('/api/') or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'success': False, 'error': 'Authentication required. Please log in.'}), 401
            return redirect(url_for('auth.login_page', next=request.url))
        
        user = db.session.get(User, user_id)
        if not user:
            session.clear()
            if request.is_json or request.path.startswith('/api/'):
                return jsonify({'success': False, 'error': 'User session invalid. Please log in again.'}), 401
            return redirect(url_for('auth.login_page'))
            
        g.current_user = user
        return f(*args, **kwargs)
    return decorated_function


def is_safe_path(base_dir: str, path: str) -> bool:
    """Validate that target path is strictly contained within base_dir to prevent path traversal."""
    try:
        abs_base = os.path.abspath(base_dir)
        abs_target = os.path.abspath(path)
        return os.path.commonpath([abs_base]) == os.path.commonpath([abs_base, abs_target])
    except Exception:
        return False


def sanitize_filename_custom(filename: str) -> str:
    """
    Sanitizes user filename while preserving non-ASCII, spaces, and valid engineering naming.
    Strips dangerous characters like slashes, null bytes, etc.
    """
    if not filename:
        return 'unnamed_file'
    # Remove null bytes and path separators
    filename = filename.replace('\x00', '').replace('/', '_').replace('\\', '_')
    # Strip leading/trailing whitespaces and dots
    filename = filename.strip('. ')
    if not filename:
        return 'unnamed_file'
    return filename


def sanitize_folder_name(name: str) -> str:
    """Sanitize folder name."""
    if not name:
        return 'New Folder'
    # Replace dangerous characters with spaces or underscores
    clean = re.sub(r'[\\/*?:"<>|]', '', name).strip()
    return clean if clean else 'New Folder'
