import os
import shutil
from flask import Blueprint, render_template, request, jsonify, g, session
from database import db
from models import User, FileRecord, Folder, ActivityLog
from utils.security import login_required
from utils.storage import Config
from utils.helpers import format_file_size

settings_bp = Blueprint('settings', __name__)

@settings_bp.route('/settings', methods=['GET'])
@login_required
def settings_page():
    return render_template('settings.html', user=g.current_user)


@settings_bp.route('/api/settings/profile', methods=['PUT'])
@login_required
def update_profile():
    user = g.current_user
    data = request.get_json(silent=True) or {}
    username = data.get('username', '').strip()
    email = data.get('email', '').strip().lower()

    if not username or not email:
        return jsonify({'success': False, 'error': 'Username and email cannot be empty.'}), 400

    # Uniqueness checks
    existing_username = User.query.filter(User.id != user.id, db.func.lower(User.username) == username.lower()).first()
    if existing_username:
        return jsonify({'success': False, 'error': 'Username is already taken by another account.'}), 409

    existing_email = User.query.filter(User.id != user.id, db.func.lower(User.email) == email.lower()).first()
    if existing_email:
        return jsonify({'success': False, 'error': 'Email address is already in use.'}), 409

    user.username = username
    user.email = email
    session['username'] = username
    session['email'] = email

    db.session.commit()

    return jsonify({
        'success': True,
        'message': 'Profile updated successfully.',
        'user': user.to_dict()
    })


@settings_bp.route('/api/settings/password', methods=['PUT'])
@login_required
def change_password():
    user = g.current_user
    data = request.get_json(silent=True) or {}
    current_password = data.get('current_password', '')
    new_password = data.get('new_password', '')

    if not current_password or not new_password:
        return jsonify({'success': False, 'error': 'Both current and new password are required.'}), 400

    if not user.check_password(current_password):
        return jsonify({'success': False, 'error': 'Incorrect current password.'}), 401

    if len(new_password) < 6:
        return jsonify({'success': False, 'error': 'New password must be at least 6 characters.'}), 400

    user.set_password(new_password)
    db.session.commit()

    return jsonify({
        'success': True,
        'message': 'Password changed successfully.'
    })


@settings_bp.route('/api/settings/storage', methods=['GET'])
@login_required
def storage_info():
    user_id = g.current_user.id
    
    # Calculate storage per category
    categories = Config.DEFAULT_CATEGORIES
    category_stats = []
    total_bytes = 0

    for cat in categories:
        count = FileRecord.query.filter_by(user_id=user_id, category=cat).count()
        cat_bytes = db.session.query(db.func.coalesce(db.func.sum(FileRecord.file_size), 0))\
            .filter(FileRecord.user_id == user_id, FileRecord.category == cat).scalar()
        total_bytes += cat_bytes
        category_stats.append({
            'category': cat,
            'count': count,
            'bytes': cat_bytes,
            'formatted_size': format_file_size(cat_bytes)
        })

    # Default quota benchmark (e.g., 20 GB for display)
    quota_limit_bytes = 20 * 1024 * 1024 * 1024
    percentage_used = round((total_bytes / quota_limit_bytes) * 100, 2) if quota_limit_bytes > 0 else 0

    return jsonify({
        'success': True,
        'total_storage_bytes': total_bytes,
        'total_storage_formatted': format_file_size(total_bytes),
        'quota_limit_bytes': quota_limit_bytes,
        'quota_limit_formatted': format_file_size(quota_limit_bytes),
        'percentage_used': percentage_used,
        'categories': category_stats
    })


@settings_bp.route('/api/settings/account', methods=['DELETE'])
@login_required
def delete_account():
    user_id = g.current_user.id
    user = g.current_user

    # Remove physical storage folder
    user_storage = os.path.join(Config.USERS_STORAGE_DIR, str(user_id))
    if os.path.exists(user_storage):
        shutil.rmtree(user_storage, ignore_errors=True)

    db.session.delete(user)
    db.session.commit()
    session.clear()

    return jsonify({
        'success': True,
        'message': 'Account and all vault data have been deleted permanently.',
        'redirect': '/login'
    })
