from flask import Blueprint, render_template, jsonify, g
from database import db
from models import FileRecord, Folder, ActivityLog
from utils.security import login_required
from utils.helpers import format_file_size, format_relative_time

dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route('/', methods=['GET'])
@login_required
def root():
    return render_template('dashboard.html', user=g.current_user)


@dashboard_bp.route('/dashboard', methods=['GET'])
@login_required
def dashboard_page():
    return render_template('dashboard.html', user=g.current_user)


@dashboard_bp.route('/download-app', methods=['GET'])
def download_app_page():
    return render_template('download_app.html')


@dashboard_bp.route('/api/dashboard/stats', methods=['GET'])
@login_required
def dashboard_stats():
    user_id = g.current_user.id
    
    # Base user files query
    user_files = FileRecord.query.filter_by(user_id=user_id)
    
    total_files = user_files.count()
    total_bytes = db.session.query(db.func.coalesce(db.func.sum(FileRecord.file_size), 0))\
        .filter(FileRecord.user_id == user_id).scalar()
    
    # Specific category / file type statistics
    pdf_count = user_files.filter(FileRecord.category == 'PDF Documents').count()
    pdf_bytes = db.session.query(db.func.coalesce(db.func.sum(FileRecord.file_size), 0))\
        .filter(FileRecord.user_id == user_id, FileRecord.category == 'PDF Documents').scalar()

    autocad_count = user_files.filter(FileRecord.category == 'AutoCAD Drawings').count()
    autocad_bytes = db.session.query(db.func.coalesce(db.func.sum(FileRecord.file_size), 0))\
        .filter(FileRecord.user_id == user_id, FileRecord.category == 'AutoCAD Drawings').scalar()

    solidworks_count = user_files.filter(FileRecord.category == 'SolidWorks Files').count()
    solidworks_bytes = db.session.query(db.func.coalesce(db.func.sum(FileRecord.file_size), 0))\
        .filter(FileRecord.user_id == user_id, FileRecord.category == 'SolidWorks Files').scalar()

    images_count = user_files.filter(FileRecord.category == 'Images').count()
    images_bytes = db.session.query(db.func.coalesce(db.func.sum(FileRecord.file_size), 0))\
        .filter(FileRecord.user_id == user_id, FileRecord.category == 'Images').scalar()

    excel_bom_count = user_files.filter(FileRecord.category == 'Excel / BOQ / BOM').count()
    excel_bom_bytes = db.session.query(db.func.coalesce(db.func.sum(FileRecord.file_size), 0))\
        .filter(FileRecord.user_id == user_id, FileRecord.category == 'Excel / BOQ / BOM').scalar()

    eng_docs_count = user_files.filter(FileRecord.category.in_(['Engineering Documents', 'Programming', 'Personal', 'Other'])).count()
    other_docs_count = user_files.filter(~FileRecord.category.in_(['PDF Documents', 'AutoCAD Drawings', 'SolidWorks Files', 'Images'])).count()
    other_docs_bytes = db.session.query(db.func.coalesce(db.func.sum(FileRecord.file_size), 0))\
        .filter(FileRecord.user_id == user_id, ~FileRecord.category.in_(['PDF Documents', 'AutoCAD Drawings', 'SolidWorks Files', 'Images'])).scalar()

    folders_count = Folder.query.filter_by(user_id=user_id).count()

    # Recent files (uploaded)
    recent_uploads = user_files.order_by(FileRecord.uploaded_at.desc()).limit(8).all()
    recent_uploads_data = []
    for f in recent_uploads:
        item = f.to_dict()
        item['formatted_size'] = format_file_size(f.file_size)
        item['relative_date'] = format_relative_time(f.uploaded_at)
        recent_uploads_data.append(item)

    # Recent opened files
    recent_opened = user_files.filter(FileRecord.last_opened_at.isnot(None))\
        .order_by(FileRecord.last_opened_at.desc()).limit(8).all()
    recent_opened_data = []
    for f in recent_opened:
        item = f.to_dict()
        item['formatted_size'] = format_file_size(f.file_size)
        item['relative_date'] = format_relative_time(f.last_opened_at)
        recent_opened_data.append(item)

    # Favorite files
    favorite_files = user_files.filter_by(is_favorite=True).order_by(FileRecord.uploaded_at.desc()).limit(8).all()
    favorite_files_data = []
    for f in favorite_files:
        item = f.to_dict()
        item['formatted_size'] = format_file_size(f.file_size)
        item['relative_date'] = format_relative_time(f.uploaded_at)
        favorite_files_data.append(item)

    return jsonify({
        'success': True,
        'stats': {
            'total_files': total_files,
            'total_storage_bytes': total_bytes,
            'total_storage_formatted': format_file_size(total_bytes),
            'pdf': {
                'count': pdf_count,
                'bytes': pdf_bytes,
                'formatted_size': format_file_size(pdf_bytes)
            },
            'autocad': {
                'count': autocad_count,
                'bytes': autocad_bytes,
                'formatted_size': format_file_size(autocad_bytes)
            },
            'solidworks': {
                'count': solidworks_count,
                'bytes': solidworks_bytes,
                'formatted_size': format_file_size(solidworks_bytes)
            },
            'images': {
                'count': images_count,
                'bytes': images_bytes,
                'formatted_size': format_file_size(images_bytes)
            },
            'excel_bom': {
                'count': excel_bom_count,
                'bytes': excel_bom_bytes,
                'formatted_size': format_file_size(excel_bom_bytes)
            },
            'other_docs': {
                'count': other_docs_count,
                'bytes': other_docs_bytes,
                'formatted_size': format_file_size(other_docs_bytes)
            },
            'folders_count': folders_count
        },
        'recent_uploads': recent_uploads_data,
        'recent_opened': recent_opened_data,
        'favorite_files': favorite_files_data
    })
