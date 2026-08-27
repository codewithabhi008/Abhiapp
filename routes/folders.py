from datetime import datetime
from flask import Blueprint, render_template, request, jsonify, g
from database import db
from models import Folder, FileRecord, ActivityLog
from utils.security import login_required, sanitize_folder_name
from utils.helpers import format_file_size, format_relative_time

folders_bp = Blueprint('folders', __name__)

@folders_bp.route('/folders', methods=['GET'])
@login_required
def folders_page():
    return render_template('folders.html', user=g.current_user)


def build_folder_tree(folders_by_parent, parent_id=None):
    """Recursively constructs a nested JSON tree of folders."""
    tree = []
    children = folders_by_parent.get(parent_id, [])
    for folder in children:
        node = folder.to_dict(include_counts=True)
        node['children'] = build_folder_tree(folders_by_parent, folder.id)
        tree.append(node)
    return tree


@folders_bp.route('/api/folders', methods=['GET'])
@login_required
def list_folders():
    user_id = g.current_user.id
    all_folders = Folder.query.filter_by(user_id=user_id).order_by(Folder.folder_name.asc()).all()

    # Build map by parent_id
    folders_by_parent = {}
    flat_list = []
    for f in all_folders:
        flat_list.append(f.to_dict(include_counts=True))
        p_id = f.parent_folder_id
        if p_id not in folders_by_parent:
            folders_by_parent[p_id] = []
        folders_by_parent[p_id].append(f)

    tree = build_folder_tree(folders_by_parent, parent_id=None)

    return jsonify({
        'success': True,
        'folders': flat_list,
        'tree': tree
    })


@folders_bp.route('/api/folders', methods=['POST'])
@login_required
def create_folder():
    user_id = g.current_user.id
    data = request.get_json(silent=True) or {}
    folder_name = sanitize_folder_name(data.get('folder_name', ''))
    parent_id = data.get('parent_folder_id')

    if not folder_name:
        return jsonify({'success': False, 'error': 'Folder name cannot be empty.'}), 400

    if parent_id is not None and parent_id != 'root':
        try:
            parent_id = int(parent_id)
            parent = Folder.query.filter_by(id=parent_id, user_id=user_id).first()
            if not parent:
                return jsonify({'success': False, 'error': 'Parent folder does not exist.'}), 404
        except ValueError:
            parent_id = None
    else:
        parent_id = None

    # Check duplicate folder name in same parent
    existing = Folder.query.filter_by(user_id=user_id, folder_name=folder_name, parent_folder_id=parent_id).first()
    if existing:
        return jsonify({'success': False, 'error': f"A folder named '{folder_name}' already exists here."}), 409

    new_folder = Folder(user_id=user_id, folder_name=folder_name, parent_folder_id=parent_id)
    db.session.add(new_folder)
    db.session.flush()

    log = ActivityLog(user_id=user_id, action='CREATE_FOLDER', details=f"Created folder '{new_folder.get_full_path()}'")
    db.session.add(log)
    db.session.commit()

    return jsonify({
        'success': True,
        'message': f"Folder '{folder_name}' created successfully.",
        'folder': new_folder.to_dict()
    }), 201


@folders_bp.route('/api/folders/<int:folder_id>', methods=['GET'])
@login_required
def get_folder_details(folder_id: int):
    user_id = g.current_user.id
    folder = Folder.query.filter_by(id=folder_id, user_id=user_id).first()
    if not folder:
        return jsonify({'success': False, 'error': 'Folder not found.'}), 404

    # Build breadcrumb trail
    breadcrumbs = []
    curr = folder
    while curr:
        breadcrumbs.append({'id': curr.id, 'name': curr.folder_name})
        curr = curr.parent
    breadcrumbs.reverse()

    # Subfolders
    subfolders = [sf.to_dict(include_counts=True) for sf in folder.subfolders]

    # Files inside this folder
    files = FileRecord.query.filter_by(user_id=user_id, folder_id=folder_id).order_by(FileRecord.uploaded_at.desc()).all()
    files_data = []
    for f in files:
        item = f.to_dict()
        item['formatted_size'] = format_file_size(f.file_size)
        item['relative_date'] = format_relative_time(f.uploaded_at)
        files_data.append(item)

    return jsonify({
        'success': True,
        'folder': folder.to_dict(include_counts=True),
        'breadcrumbs': breadcrumbs,
        'subfolders': subfolders,
        'files': files_data
    })


@folders_bp.route('/api/folders/<int:folder_id>', methods=['PUT'])
@login_required
def rename_folder(folder_id: int):
    user_id = g.current_user.id
    folder = Folder.query.filter_by(id=folder_id, user_id=user_id).first()
    if not folder:
        return jsonify({'success': False, 'error': 'Folder not found.'}), 404

    data = request.get_json(silent=True) or {}
    new_name = sanitize_folder_name(data.get('folder_name', ''))

    if not new_name:
        return jsonify({'success': False, 'error': 'Folder name cannot be empty.'}), 400

    old_name = folder.folder_name
    folder.folder_name = new_name

    log = ActivityLog(user_id=user_id, action='RENAME_FOLDER', details=f"Renamed folder '{old_name}' to '{new_name}'")
    db.session.add(log)
    db.session.commit()

    return jsonify({
        'success': True,
        'message': f"Folder renamed to '{new_name}'.",
        'folder': folder.to_dict()
    })


@folders_bp.route('/api/folders/<int:folder_id>', methods=['DELETE'])
@login_required
def delete_folder(folder_id: int):
    user_id = g.current_user.id
    folder = Folder.query.filter_by(id=folder_id, user_id=user_id).first()
    if not folder:
        return jsonify({'success': False, 'error': 'Folder not found.'}), 404

    # Move files inside this folder (and child subfolders) to root or delete
    # To keep user files safe from accidental deletion, we reassign direct files to root
    FileRecord.query.filter_by(user_id=user_id, folder_id=folder_id).update({'folder_id': None})
    
    # Recursive reassignment for subfolders' files
    def reassign_children_files(f_id):
        sub_list = Folder.query.filter_by(user_id=user_id, parent_folder_id=f_id).all()
        for sub in sub_list:
            FileRecord.query.filter_by(user_id=user_id, folder_id=sub.id).update({'folder_id': None})
            reassign_children_files(sub.id)

    reassign_children_files(folder_id)

    folder_name = folder.folder_name
    db.session.delete(folder)
    log = ActivityLog(user_id=user_id, action='DELETE_FOLDER', details=f"Deleted folder '{folder_name}' (files preserved at root level)")
    db.session.add(log)
    db.session.commit()

    return jsonify({
        'success': True,
        'message': f"Folder '{folder_name}' deleted. Contained files have been moved to Root for safety."
    })
