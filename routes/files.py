import os
import io
import zipfile
from datetime import datetime, timezone
from flask import Blueprint, render_template, request, jsonify, g, send_file, Response
from database import db
from models import FileRecord, Folder, ActivityLog
from utils.security import login_required, sanitize_filename_custom
from utils.storage import detect_category, save_file_to_storage, delete_file_from_storage, get_absolute_file_path
from utils.helpers import format_file_size, format_relative_time, is_previewable_text, is_previewable_image, is_previewable_pdf, is_cad_file, get_cad_details

files_bp = Blueprint('files', __name__)

@files_bp.route('/vault', methods=['GET'])
@login_required
def vault_page():
    return render_template('vault.html', user=g.current_user)


@files_bp.route('/api/files', methods=['GET'])
@login_required
def list_files():
    user_id = g.current_user.id
    query = FileRecord.query.filter_by(user_id=user_id)

    # Search query
    search = request.args.get('search', '').strip()
    if search:
        search_pattern = f"%{search}%"
        query = query.filter(
            db.or_(
                FileRecord.original_name.ilike(search_pattern),
                FileRecord.description.ilike(search_pattern),
                FileRecord.tags.ilike(search_pattern),
                FileRecord.file_extension.ilike(search_pattern)
            )
        )

    # Category filter
    category = request.args.get('category', '').strip()
    if category and category != 'all':
        query = query.filter(FileRecord.category == category)

    # Extension / Type filter chip
    ext_filter = request.args.get('type', '').strip().lower()
    if ext_filter and ext_filter != 'all':
        if ext_filter == 'pdf':
            query = query.filter(FileRecord.file_extension == '.pdf')
        elif ext_filter == 'dwg':
            query = query.filter(FileRecord.file_extension == '.dwg')
        elif ext_filter == 'dxf':
            query = query.filter(FileRecord.file_extension == '.dxf')
        elif ext_filter == 'sldprt':
            query = query.filter(FileRecord.file_extension == '.sldprt')
        elif ext_filter == 'sldasm':
            query = query.filter(FileRecord.file_extension == '.sldasm')
        elif ext_filter == 'slddrw':
            query = query.filter(FileRecord.file_extension == '.slddrw')
        elif ext_filter == 'images':
            query = query.filter(FileRecord.file_extension.in_(['.jpg', '.jpeg', '.png', '.webp', '.gif', '.svg', '.bmp']))
        elif ext_filter == 'documents':
            query = query.filter(FileRecord.file_extension.in_(['.doc', '.docx', '.ppt', '.pptx', '.xls', '.xlsx', '.txt', '.pdf']))
        elif ext_filter == 'cad':
            query = query.filter(FileRecord.file_extension.in_(['.dwg', '.dxf', '.sldprt', '.sldasm', '.slddrw', '.step', '.stp', '.iges', '.igs']))
        elif ext_filter == 'code':
            query = query.filter(FileRecord.file_extension.in_(['.py', '.c', '.cpp', '.h', '.js', '.html', '.css', '.json', '.sql', '.java']))

    # Folder filter
    folder_param = request.args.get('folder_id')
    if folder_param is not None and folder_param != '':
        if folder_param == 'root':
            query = query.filter(FileRecord.folder_id.is_(None))
        else:
            try:
                folder_id = int(folder_param)
                query = query.filter(FileRecord.folder_id == folder_id)
            except ValueError:
                pass

    # Favorites filter
    favorite_only = request.args.get('favorite')
    if favorite_only in ['true', '1', 'yes']:
        query = query.filter(FileRecord.is_favorite == True)

    # Sorting
    sort = request.args.get('sort', 'date_desc')
    if sort == 'name_asc':
        query = query.order_by(FileRecord.original_name.asc())
    elif sort == 'name_desc':
        query = query.order_by(FileRecord.original_name.desc())
    elif sort == 'date_asc':
        query = query.order_by(FileRecord.uploaded_at.asc())
    elif sort == 'size_desc':
        query = query.order_by(FileRecord.file_size.desc())
    elif sort == 'size_asc':
        query = query.order_by(FileRecord.file_size.asc())
    else:  # date_desc
        query = query.order_by(FileRecord.uploaded_at.desc())

    files = query.all()
    results = []
    for f in files:
        item = f.to_dict()
        item['formatted_size'] = format_file_size(f.file_size)
        item['relative_date'] = format_relative_time(f.uploaded_at)
        item['is_pdf'] = is_previewable_pdf(f.file_extension)
        item['is_image'] = is_previewable_image(f.file_extension)
        item['is_text'] = is_previewable_text(f.file_extension)
        item['is_cad'] = is_cad_file(f.file_extension)
        results.append(item)

    return jsonify({
        'success': True,
        'count': len(results),
        'files': results
    })


@files_bp.route('/api/files/upload', methods=['POST'])
@login_required
def upload_files():
    user_id = g.current_user.id
    uploaded_files = request.files.getlist('files')
    
    if not uploaded_files or len(uploaded_files) == 0 or (len(uploaded_files) == 1 and uploaded_files[0].filename == ''):
        return jsonify({'success': False, 'error': 'No files provided for upload.'}), 400

    folder_id = request.form.get('folder_id')
    folder_id = int(folder_id) if (folder_id and folder_id.isdigit() and int(folder_id) > 0) else None

    # Validate folder ownership if folder_id is provided
    if folder_id:
        folder = Folder.query.filter_by(id=folder_id, user_id=user_id).first()
        if not folder:
            folder_id = None

    explicit_category = request.form.get('category', '').strip()
    description = request.form.get('description', '').strip()
    tags = request.form.get('tags', '').strip()

    saved_records = []
    errors = []

    for file_obj in uploaded_files:
        if not file_obj or file_obj.filename == '':
            continue
        try:
            original_filename = file_obj.filename
            category = detect_category(original_filename, explicit_category)

            # Save to user storage
            stored_name, abs_path, rel_path, file_size, ext = save_file_to_storage(
                file_obj=file_obj,
                user_id=user_id,
                original_filename=original_filename,
                category=category
            )

            # Create DB record
            record = FileRecord(
                user_id=user_id,
                original_name=original_filename,
                stored_name=stored_name,
                file_path=rel_path,
                file_extension=ext,
                file_size=file_size,
                category=category,
                folder_id=folder_id,
                description=description if description else None,
                tags=tags if tags else None,
                is_favorite=False,
                uploaded_at=datetime.now(timezone.utc)
            )
            db.session.add(record)
            db.session.flush()

            # Log Activity
            log = ActivityLog(
                user_id=user_id,
                file_id=record.id,
                action='UPLOAD',
                details=f"Uploaded {original_filename} ({format_file_size(file_size)})"
            )
            db.session.add(log)

            item = record.to_dict()
            item['formatted_size'] = format_file_size(file_size)
            item['relative_date'] = 'Just now'
            saved_records.append(item)

        except Exception as e:
            errors.append(f"Failed to upload '{getattr(file_obj, 'filename', 'unknown')}': {str(e)}")

    if saved_records:
        db.session.commit()

    return jsonify({
        'success': True if saved_records else False,
        'uploaded_count': len(saved_records),
        'files': saved_records,
        'errors': errors
    }), 201 if saved_records else 400


@files_bp.route('/api/files/<int:file_id>', methods=['GET'])
@login_required
def get_file_details(file_id: int):
    record = FileRecord.query.filter_by(id=file_id, user_id=g.current_user.id).first()
    if not record:
        return jsonify({'success': False, 'error': 'File not found or permission denied.'}), 404

    data = record.to_dict()
    data['formatted_size'] = format_file_size(record.file_size)
    data['relative_date'] = format_relative_time(record.uploaded_at)
    data['is_pdf'] = is_previewable_pdf(record.file_extension)
    data['is_image'] = is_previewable_image(record.file_extension)
    data['is_text'] = is_previewable_text(record.file_extension)
    data['is_cad'] = is_cad_file(record.file_extension)
    if data['is_cad']:
        data['cad_details'] = get_cad_details(record.file_extension)
    return jsonify({'success': True, 'file': data})


@files_bp.route('/api/files/<int:file_id>/download', methods=['GET'])
@login_required
def download_file(file_id: int):
    user_id = g.current_user.id
    record = FileRecord.query.filter_by(id=file_id, user_id=user_id).first()
    if not record:
        return jsonify({'success': False, 'error': 'File not found or access denied.'}), 404

    abs_path = get_absolute_file_path(user_id, record.file_path)
    if not abs_path:
        return jsonify({'success': False, 'error': 'File physical resource is missing on server.'}), 404

    # Update last opened timestamp
    record.last_opened_at = datetime.now(timezone.utc)
    log = ActivityLog(user_id=user_id, file_id=record.id, action='DOWNLOAD', details=f"Downloaded {record.original_name}")
    db.session.add(log)
    db.session.commit()

    return send_file(
        abs_path,
        as_attachment=True,
        download_name=record.original_name
    )


@files_bp.route('/api/files/<int:file_id>/preview', methods=['GET'])
@login_required
def preview_file(file_id: int):
    user_id = g.current_user.id
    record = FileRecord.query.filter_by(id=file_id, user_id=user_id).first()
    if not record:
        return jsonify({'success': False, 'error': 'File not found.'}), 404

    abs_path = get_absolute_file_path(user_id, record.file_path)
    if not abs_path:
        return jsonify({'success': False, 'error': 'File physical resource is missing.'}), 404

    # Update last opened timestamp
    record.last_opened_at = datetime.now(timezone.utc)
    db.session.commit()

    # Image preview
    if is_previewable_image(record.file_extension):
        return send_file(abs_path, mimetype=None)

    # PDF preview
    if is_previewable_pdf(record.file_extension):
        return send_file(abs_path, mimetype='application/pdf')

    # Text / Code syntax preview
    if is_previewable_text(record.file_extension):
        try:
            with open(abs_path, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read(500000)
            return jsonify({
                'success': True,
                'type': 'text',
                'file_name': record.original_name,
                'extension': record.file_extension,
                'content': content
            })
        except Exception as e:
            return jsonify({'success': False, 'error': f'Cannot read text: {str(e)}'}), 500

    # CAD File metadata preview
    if is_cad_file(record.file_extension):
        cad_info = get_cad_details(record.file_extension)
        return jsonify({
            'success': True,
            'type': 'cad',
            'file_name': record.original_name,
            'extension': record.file_extension,
            'size_formatted': format_file_size(record.file_size),
            'cad_details': cad_info,
            'category': record.category,
            'description': record.description or 'Technical CAD drawing/model stored in vault.',
            'uploaded_at': record.uploaded_at.strftime('%b %d, %Y %H:%M') if record.uploaded_at else 'N/A',
            'tags': [t.strip() for t in record.tags.split(',') if t.strip()] if record.tags else [],
            'download_url': f"/api/files/{record.id}/download"
        })

    return jsonify({
        'success': True,
        'type': 'generic',
        'file_name': record.original_name,
        'extension': record.file_extension,
        'size_formatted': format_file_size(record.file_size),
        'message': 'Binary document. Please download to view in native software.'
    })


@files_bp.route('/api/files/<int:file_id>/rename', methods=['PUT'])
@login_required
def rename_file(file_id: int):
    user_id = g.current_user.id
    record = FileRecord.query.filter_by(id=file_id, user_id=user_id).first()
    if not record:
        return jsonify({'success': False, 'error': 'File not found.'}), 404

    data = request.get_json(silent=True) or {}
    new_name = data.get('new_name', '').strip()

    if not new_name:
        return jsonify({'success': False, 'error': 'Please enter a valid file name.'}), 400

    new_name = sanitize_filename_custom(new_name)
    _, new_ext = os.path.splitext(new_name)
    if not new_ext:
        new_name = new_name + record.file_extension

    old_name = record.original_name
    record.original_name = new_name
    record.updated_at = datetime.now(timezone.utc)

    log = ActivityLog(user_id=user_id, file_id=record.id, action='RENAME', details=f"Renamed '{old_name}' to '{new_name}'")
    db.session.add(log)
    db.session.commit()

    return jsonify({
        'success': True,
        'message': f"File renamed to '{new_name}'.",
        'file': record.to_dict()
    })


@files_bp.route('/api/files/<int:file_id>/move', methods=['PUT'])
@login_required
def move_file(file_id: int):
    user_id = g.current_user.id
    record = FileRecord.query.filter_by(id=file_id, user_id=user_id).first()
    if not record:
        return jsonify({'success': False, 'error': 'File not found.'}), 404

    data = request.get_json(silent=True) or {}
    target_folder_id = data.get('folder_id')

    if target_folder_id is not None and target_folder_id != 'root':
        try:
            target_folder_id = int(target_folder_id)
            folder = Folder.query.filter_by(id=target_folder_id, user_id=user_id).first()
            if not folder:
                return jsonify({'success': False, 'error': 'Target folder not found.'}), 404
        except ValueError:
            target_folder_id = None
    else:
        target_folder_id = None

    record.folder_id = target_folder_id
    record.updated_at = datetime.now(timezone.utc)

    log = ActivityLog(user_id=user_id, file_id=record.id, action='MOVE', details=f"Moved '{record.original_name}' to folder ID {target_folder_id}")
    db.session.add(log)
    db.session.commit()

    return jsonify({
        'success': True,
        'message': 'File moved successfully.',
        'file': record.to_dict()
    })


@files_bp.route('/api/files/<int:file_id>/favorite', methods=['PUT'])
@login_required
def toggle_favorite(file_id: int):
    user_id = g.current_user.id
    record = FileRecord.query.filter_by(id=file_id, user_id=user_id).first()
    if not record:
        return jsonify({'success': False, 'error': 'File not found.'}), 404

    record.is_favorite = not record.is_favorite
    record.updated_at = datetime.now(timezone.utc)

    action_name = 'Added to favorites' if record.is_favorite else 'Removed from favorites'
    log = ActivityLog(user_id=user_id, file_id=record.id, action='FAVORITE', details=f"{action_name}: '{record.original_name}'")
    db.session.add(log)
    db.session.commit()

    return jsonify({
        'success': True,
        'is_favorite': record.is_favorite,
        'message': f"'{record.original_name}' {action_name.lower()}."
    })


@files_bp.route('/api/files/<int:file_id>/metadata', methods=['PUT'])
@login_required
def update_metadata(file_id: int):
    user_id = g.current_user.id
    record = FileRecord.query.filter_by(id=file_id, user_id=user_id).first()
    if not record:
        return jsonify({'success': False, 'error': 'File not found.'}), 404

    data = request.get_json(silent=True) or {}
    if 'description' in data:
        record.description = data['description'].strip() if data['description'] else None
    if 'tags' in data:
        record.tags = data['tags'].strip() if data['tags'] else None
    if 'category' in data and data['category'].strip():
        record.category = data['category'].strip()

    record.updated_at = datetime.now(timezone.utc)
    db.session.commit()

    return jsonify({
        'success': True,
        'message': 'File details updated.',
        'file': record.to_dict()
    })


@files_bp.route('/api/files/<int:file_id>', methods=['DELETE'])
@login_required
def delete_file(file_id: int):
    user_id = g.current_user.id
    record = FileRecord.query.filter_by(id=file_id, user_id=user_id).first()
    if not record:
        return jsonify({'success': False, 'error': 'File not found.'}), 404

    # Delete physical file from disk
    delete_file_from_storage(user_id, record.file_path)

    # Log Activity before deleting DB record
    log = ActivityLog(user_id=user_id, action='DELETE', details=f"Deleted file '{record.original_name}'")
    db.session.add(log)

    # Delete DB record
    db.session.delete(record)
    db.session.commit()

    return jsonify({
        'success': True,
        'message': f"'{record.original_name}' deleted permanently."
    })


@files_bp.route('/api/files/bulk', methods=['POST'])
@login_required
def bulk_operations():
    user_id = g.current_user.id
    data = request.get_json(silent=True) or {}
    action = data.get('action')
    file_ids = data.get('file_ids', [])

    if not action or not file_ids or not isinstance(file_ids, list):
        return jsonify({'success': False, 'error': 'Invalid bulk action parameters.'}), 400

    records = FileRecord.query.filter(FileRecord.id.in_(file_ids), FileRecord.user_id == user_id).all()
    if not records:
        return jsonify({'success': False, 'error': 'No matching files found.'}), 404

    # Bulk Delete
    if action == 'delete':
        deleted_count = 0
        for r in records:
            delete_file_from_storage(user_id, r.file_path)
            db.session.delete(r)
            deleted_count += 1

        log = ActivityLog(user_id=user_id, action='DELETE', details=f"Bulk deleted {deleted_count} files.")
        db.session.add(log)
        db.session.commit()

        return jsonify({'success': True, 'message': f"Successfully deleted {deleted_count} files."})

    # Bulk Move
    elif action == 'move':
        target_folder_id = data.get('folder_id')
        if target_folder_id is not None and target_folder_id != 'root':
            try:
                target_folder_id = int(target_folder_id)
                folder = Folder.query.filter_by(id=target_folder_id, user_id=user_id).first()
                if not folder:
                    return jsonify({'success': False, 'error': 'Target folder not found.'}), 404
            except ValueError:
                target_folder_id = None
        else:
            target_folder_id = None

        for r in records:
            r.folder_id = target_folder_id
            r.updated_at = datetime.now(timezone.utc)

        log = ActivityLog(user_id=user_id, action='MOVE', details=f"Bulk moved {len(records)} files.")
        db.session.add(log)
        db.session.commit()

        return jsonify({'success': True, 'message': f"Moved {len(records)} files successfully."})

    # Bulk Download as ZIP
    elif action == 'download':
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            used_names = set()
            for r in records:
                abs_path = get_absolute_file_path(user_id, r.file_path)
                if abs_path and os.path.exists(abs_path):
                    arcname = r.original_name
                    counter = 1
                    base, ext = os.path.splitext(arcname)
                    while arcname in used_names:
                        arcname = f"{base}_{counter}{ext}"
                        counter += 1
                    used_names.add(arcname)
                    zip_file.write(abs_path, arcname=arcname)

        zip_buffer.seek(0)
        timestamp = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
        return send_file(
            zip_buffer,
            mimetype='application/zip',
            as_attachment=True,
            download_name=f"AbhiApp_Vault_Export_{timestamp}.zip"
        )

    return jsonify({'success': False, 'error': 'Unsupported bulk action.'}), 400
