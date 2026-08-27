from datetime import datetime, timezone
from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for, g
from database import db
from models import User, Folder
from utils.security import login_required

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET'])
def login_page():
    if session.get('user_id'):
        return redirect(url_for('dashboard.dashboard_page'))
    return render_template('login.html')


@auth_bp.route('/api/auth/login', methods=['POST'])
def api_login():
    data = request.get_json(silent=True) or request.form
    identifier = data.get('identifier', '').strip()
    password = data.get('password', '')
    remember = bool(data.get('remember', False))

    if not identifier or not password:
        return jsonify({'success': False, 'error': 'Please provide your username/email and password.'}), 400

    # Lookup user by username or email (case-insensitive)
    user = User.query.filter(
        (db.func.lower(User.username) == identifier.lower()) | 
        (db.func.lower(User.email) == identifier.lower())
    ).first()

    if not user or not user.check_password(password):
        return jsonify({'success': False, 'error': 'Invalid username/email or password.'}), 401

    # Update last login
    user.last_login = datetime.now(timezone.utc)
    db.session.commit()

    # Store in session
    session.clear()
    session['user_id'] = user.id
    session['username'] = user.username
    session['email'] = user.email
    if remember:
        session.permanent = True

    return jsonify({
        'success': True,
        'message': f'Welcome back to AbhiApp, {user.username}!',
        'user': user.to_dict(),
        'redirect': url_for('dashboard.dashboard_page')
    })


@auth_bp.route('/api/auth/register', methods=['POST'])
def api_register():
    data = request.get_json(silent=True) or request.form
    username = data.get('username', '').strip()
    email = data.get('email', '').strip().lower()
    password = data.get('password', '')

    if not username or not email or not password:
        return jsonify({'success': False, 'error': 'Username, email, and password are required.'}), 400

    if len(username) < 3:
        return jsonify({'success': False, 'error': 'Username must be at least 3 characters.'}), 400

    if len(password) < 6:
        return jsonify({'success': False, 'error': 'Password must be at least 6 characters.'}), 400

    # Check uniqueness
    if User.query.filter(db.func.lower(User.username) == username.lower()).first():
        return jsonify({'success': False, 'error': 'Username is already taken.'}), 409

    if User.query.filter(db.func.lower(User.email) == email).first():
        return jsonify({'success': False, 'error': 'Email address is already registered.'}), 409

    # Create new user
    new_user = User(username=username, email=email)
    new_user.set_password(password)
    new_user.last_login = datetime.now(timezone.utc)
    db.session.add(new_user)
    db.session.commit()

    # Seed standard default folder hierarchy for the new user
    try:
        eng_folder = Folder(user_id=new_user.id, folder_name='Engineering')
        db.session.add(eng_folder)
        db.session.flush()

        acad_folder = Folder(user_id=new_user.id, folder_name='AutoCAD', parent_folder_id=eng_folder.id)
        sw_folder = Folder(user_id=new_user.id, folder_name='SolidWorks', parent_folder_id=eng_folder.id)
        pdf_folder = Folder(user_id=new_user.id, folder_name='PDF', parent_folder_id=eng_folder.id)
        bom_folder = Folder(user_id=new_user.id, folder_name='BOM', parent_folder_id=eng_folder.id)
        db.session.add_all([acad_folder, sw_folder, pdf_folder, bom_folder])
        db.session.flush()

        # AutoCAD subfolders
        panel_f = Folder(user_id=new_user.id, folder_name='Panel', parent_folder_id=acad_folder.id)
        busbar_f = Folder(user_id=new_user.id, folder_name='Busbar', parent_folder_id=acad_folder.id)
        fab_f = Folder(user_id=new_user.id, folder_name='Fabrication', parent_folder_id=acad_folder.id)

        # SolidWorks subfolders
        parts_f = Folder(user_id=new_user.id, folder_name='Parts', parent_folder_id=sw_folder.id)
        assy_f = Folder(user_id=new_user.id, folder_name='Assembly', parent_folder_id=sw_folder.id)
        draw_f = Folder(user_id=new_user.id, folder_name='Drawing', parent_folder_id=sw_folder.id)

        db.session.add_all([panel_f, busbar_f, fab_f, parts_f, assy_f, draw_f])
        db.session.commit()
    except Exception:
        db.session.rollback()

    # Log in automatically
    session.clear()
    session['user_id'] = new_user.id
    session['username'] = new_user.username
    session['email'] = new_user.email

    return jsonify({
        'success': True,
        'message': 'Account created successfully!',
        'user': new_user.to_dict(),
        'redirect': url_for('dashboard.dashboard_page')
    }), 201


@auth_bp.route('/logout', methods=['GET', 'POST'])
def logout():
    session.clear()
    if request.is_json or request.path.startswith('/api/'):
        return jsonify({'success': True, 'message': 'Logged out successfully', 'redirect': url_for('auth.login_page')})
    return redirect(url_for('auth.login_page'))


@auth_bp.route('/api/auth/me', methods=['GET'])
@login_required
def api_me():
    return jsonify({
        'success': True,
        'user': g.current_user.to_dict()
    })
