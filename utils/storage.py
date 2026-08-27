import os
import uuid
import shutil
from werkzeug.utils import secure_filename
from config import Config
from utils.security import is_safe_path, sanitize_filename_custom

# Mapping of file extensions to categories
EXTENSION_CATEGORY_MAP = {
    # PDF
    '.pdf': 'PDF Documents',
    
    # AutoCAD
    '.dwg': 'AutoCAD Drawings',
    '.dxf': 'AutoCAD Drawings',
    '.dwt': 'AutoCAD Drawings',
    
    # SolidWorks & 3D CAD
    '.sldprt': 'SolidWorks Files',
    '.sldasm': 'SolidWorks Files',
    '.slddrw': 'SolidWorks Files',
    '.prt': 'SolidWorks Files',
    '.asm': 'SolidWorks Files',
    '.drw': 'SolidWorks Files',
    '.step': 'SolidWorks Files',
    '.stp': 'SolidWorks Files',
    '.iges': 'SolidWorks Files',
    '.igs': 'SolidWorks Files',
    '.x_t': 'SolidWorks Files',
    '.x_b': 'SolidWorks Files',
    '.sat': 'SolidWorks Files',
    
    # Engineering Documents & Office Word/Presentations
    '.doc': 'Engineering Documents',
    '.docx': 'Engineering Documents',
    '.ppt': 'Engineering Documents',
    '.pptx': 'Engineering Documents',
    '.odt': 'Engineering Documents',
    '.rtf': 'Engineering Documents',
    '.vsd': 'Engineering Documents',
    '.vsdx': 'Engineering Documents',
    '.pdf': 'PDF Documents',
    
    # Excel / BOQ / BOM
    '.xls': 'Excel / BOQ / BOM',
    '.xlsx': 'Excel / BOQ / BOM',
    '.xlsm': 'Excel / BOQ / BOM',
    '.csv': 'Excel / BOQ / BOM',
    '.tsv': 'Excel / BOQ / BOM',
    '.ods': 'Excel / BOQ / BOM',
    
    # Images
    '.jpg': 'Images',
    '.jpeg': 'Images',
    '.png': 'Images',
    '.webp': 'Images',
    '.gif': 'Images',
    '.svg': 'Images',
    '.bmp': 'Images',
    '.ico': 'Images',
    '.tiff': 'Images',
    '.tif': 'Images',
    
    # Programming & Code
    '.c': 'Programming',
    '.cpp': 'Programming',
    '.h': 'Programming',
    '.hpp': 'Programming',
    '.py': 'Programming',
    '.html': 'Programming',
    '.htm': 'Programming',
    '.css': 'Programming',
    '.js': 'Programming',
    '.ts': 'Programming',
    '.jsx': 'Programming',
    '.tsx': 'Programming',
    '.json': 'Programming',
    '.xml': 'Programming',
    '.yaml': 'Programming',
    '.yml': 'Programming',
    '.sql': 'Programming',
    '.sh': 'Programming',
    '.bat': 'Programming',
    '.ps1': 'Programming',
    '.java': 'Programming',
    '.rs': 'Programming',
    '.go': 'Programming',
    '.php': 'Programming',
    '.rb': 'Programming',
    '.md': 'Programming',
    '.txt': 'Engineering Documents',
    
    # Archives
    '.zip': 'Other',
    '.rar': 'Other',
    '.7z': 'Other',
    '.tar': 'Other',
    '.gz': 'Other',
}


def category_to_slug(category_name: str) -> str:
    """Convert human readable category to a clean folder slug."""
    clean = category_name.lower().replace('/', '_').replace(' ', '_').replace('-', '_')
    while '__' in clean:
        clean = clean.replace('__', '_')
    return clean.strip('_')


def detect_category(filename: str, explicit_category: str = None) -> str:
    """Detect category from extension or return explicit category if valid."""
    if explicit_category and explicit_category in Config.DEFAULT_CATEGORIES:
        return explicit_category
        
    _, ext = os.path.splitext(filename)
    ext_lower = ext.lower()
    return EXTENSION_CATEGORY_MAP.get(ext_lower, 'Other')


def get_user_storage_path(user_id: int, category: str = None) -> str:
    """Get absolute directory path for a user's category storage."""
    user_dir = os.path.join(Config.USERS_STORAGE_DIR, str(user_id))
    if category:
        cat_slug = category_to_slug(category)
        user_dir = os.path.join(user_dir, cat_slug)
    os.makedirs(user_dir, exist_ok=True)
    return user_dir


def save_file_to_storage(file_obj, user_id: int, original_filename: str, category: str):
    """
    Saves an uploaded file to the user's categorized directory with a secure unique stored name.
    Returns (stored_name, absolute_path, relative_path, file_size, extension)
    """
    sanitized_original = sanitize_filename_custom(original_filename)
    _, ext = os.path.splitext(sanitized_original)
    ext_lower = ext.lower()
    
    # Generate unique stored name using UUID + safe original filename
    unique_prefix = uuid.uuid4().hex
    safe_disk_name = f"{unique_prefix}_{secure_filename(sanitized_original) or 'file' + ext_lower}"
    
    target_dir = get_user_storage_path(user_id, category)
    target_path = os.path.join(target_dir, safe_disk_name)
    
    # Save the file stream
    file_obj.save(target_path)
    
    # Get actual size on disk
    file_size = os.path.getsize(target_path)
    
    # Compute relative path from STORAGE_DIR
    relative_path = os.path.relpath(target_path, Config.BASE_DIR)
    
    return safe_disk_name, target_path, relative_path, file_size, ext_lower


def delete_file_from_storage(user_id: int, file_path_rel: str) -> bool:
    """Safely delete file from storage ensuring no path traversal."""
    abs_path = os.path.join(Config.BASE_DIR, file_path_rel)
    user_base = os.path.join(Config.USERS_STORAGE_DIR, str(user_id))
    
    if not is_safe_path(user_base, abs_path):
        return False
        
    if os.path.exists(abs_path) and os.path.isfile(abs_path):
        try:
            os.remove(abs_path)
            return True
        except Exception:
            return False
    return False


def get_absolute_file_path(user_id: int, file_path_rel: str) -> str:
    """Return verified absolute file path or None if traversal/non-existent."""
    abs_path = os.path.join(Config.BASE_DIR, file_path_rel)
    user_base = os.path.join(Config.USERS_STORAGE_DIR, str(user_id))
    if not is_safe_path(user_base, abs_path):
        return None
    if os.path.exists(abs_path) and os.path.isfile(abs_path):
        return abs_path
    return None
