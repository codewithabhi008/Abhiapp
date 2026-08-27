import mimetypes
from datetime import datetime, timezone

def format_file_size(size_bytes: int) -> str:
    """Formats bytes into human readable format like 4.2 MB or 850 KB."""
    if not size_bytes or size_bytes < 0:
        return "0 B"
        
    units = ['B', 'KB', 'MB', 'GB', 'TB', 'PB']
    unit_idx = 0
    size = float(size_bytes)
    
    while size >= 1024.0 and unit_idx < len(units) - 1:
        size /= 1024.0
        unit_idx += 1
        
    if unit_idx == 0:
        return f"{int(size)} B"
    elif size >= 100:
        return f"{size:.1f} {units[unit_idx]}"
    else:
        return f"{size:.2f} {units[unit_idx]}"


def format_relative_time(dt: datetime) -> str:
    """Formats a datetime into relative string like 'Today', 'Yesterday', '3 days ago'."""
    if not dt:
        return "N/A"
        
    now = datetime.now(timezone.utc)
    # Ensure dt is timezone-aware if compared with now
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
        
    diff = now - dt
    seconds = diff.total_seconds()
    if seconds < 60:
        return "Just now"
    elif seconds < 3600:
        mins = int(seconds // 60)
        return f"{mins} min{'s' if mins > 1 else ''} ago"
    elif seconds < 86400:
        hours = int(seconds // 3600)
        if dt.date() == now.date():
            return "Today"
        return f"{hours} hr{'s' if hours > 1 else ''} ago"
    elif seconds < 172800:
        return "Yesterday"
    elif diff.days < 7:
        return f"{diff.days} days ago"
    elif diff.days < 30:
        weeks = diff.days // 7
        return f"{weeks} week{'s' if weeks > 1 else ''} ago"
    elif diff.days < 365:
        months = diff.days // 30
        return f"{months} month{'s' if months > 1 else ''} ago"
    else:
        return dt.strftime("%b %d, %Y")


def get_cad_details(ext: str) -> dict:
    """Return technical metadata for CAD files."""
    ext_clean = ext.lower().lstrip('.')
    cad_info = {
        'dwg': {'type': 'AutoCAD 2D/3D Drawing Database', 'software': 'AutoDesk AutoCAD', 'nature': 'Vector Geometry & Layers'},
        'dxf': {'type': 'Drawing Exchange Format', 'software': 'AutoCAD / Generic CAD', 'nature': 'Interchange Vector Data'},
        'dwt': {'type': 'AutoCAD Drawing Template', 'software': 'AutoDesk AutoCAD', 'nature': 'CAD Template'},
        'sldprt': {'type': 'SolidWorks Part Model', 'software': 'Dassault Systèmes SolidWorks', 'nature': '3D Parametric Solid Part'},
        'sldasm': {'type': 'SolidWorks Assembly Model', 'software': 'Dassault Systèmes SolidWorks', 'nature': '3D Component Assembly'},
        'slddrw': {'type': 'SolidWorks Engineering Drawing', 'software': 'Dassault Systèmes SolidWorks', 'nature': '2D Fabrication Blueprint'},
        'step': {'type': 'STEP 3D CAD Model (ISO 10303)', 'software': 'Universal 3D CAD', 'nature': 'Neutral 3D Solid Model'},
        'stp': {'type': 'STEP 3D CAD Model', 'software': 'Universal 3D CAD', 'nature': 'Neutral 3D Solid Model'},
        'iges': {'type': 'IGES CAD Model', 'software': 'Universal CAD', 'nature': 'Surface & Wireframe Exchange'},
        'igs': {'type': 'IGES CAD Model', 'software': 'Universal CAD', 'nature': 'Surface & Wireframe Exchange'},
    }
    return cad_info.get(ext_clean, {'type': 'Engineering CAD File', 'software': 'Technical CAD Suite', 'nature': 'Engineering Model/Drawing'})


def is_previewable_text(ext: str) -> bool:
    """Check if file can be read and rendered in text/code syntax viewer."""
    text_extensions = {
        '.txt', '.md', '.markdown', '.py', '.c', '.cpp', '.h', '.hpp', '.java',
        '.js', '.ts', '.jsx', '.tsx', '.html', '.htm', '.css', '.scss', '.sass',
        '.json', '.xml', '.yaml', '.yml', '.sql', '.sh', '.bat', '.ps1', '.ini',
        '.cfg', '.conf', '.env', '.log', '.csv', '.tsv', '.rs', '.go', '.php',
        '.rb', '.r', '.m', '.swift', '.kt', '.dart', '.tex'
    }
    return ext.lower() in text_extensions


def is_previewable_image(ext: str) -> bool:
    """Check if file is an image natively viewable in browser."""
    image_extensions = {'.jpg', '.jpeg', '.png', '.webp', '.gif', '.svg', '.bmp', '.ico'}
    return ext.lower() in image_extensions


def is_previewable_pdf(ext: str) -> bool:
    return ext.lower() == '.pdf'


def is_cad_file(ext: str) -> bool:
    cad_extensions = {'.dwg', '.dxf', '.dwt', '.sldprt', '.sldasm', '.slddrw', '.prt', '.asm', '.drw', '.step', '.stp', '.iges', '.igs', '.x_t', '.x_b', '.sat'}
    return ext.lower() in cad_extensions
