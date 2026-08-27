from datetime import datetime, timezone
from werkzeug.security import generate_password_hash, check_password_hash
from database import db

def utc_now():
    return datetime.now(timezone.utc)

class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=utc_now)
    last_login = db.Column(db.DateTime, nullable=True)

    # Relationships
    files = db.relationship('FileRecord', backref='owner', lazy='dynamic', cascade='all, delete-orphan')
    folders = db.relationship('Folder', backref='owner', lazy='dynamic', cascade='all, delete-orphan')
    activity_logs = db.relationship('ActivityLog', backref='user', lazy='dynamic', cascade='all, delete-orphan')

    def set_password(self, password: str):
        self.password_hash = generate_password_hash(password, method='scrypt')

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_login': self.last_login.isoformat() if self.last_login else None
        }


class Folder(db.Model):
    __tablename__ = 'folders'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    folder_name = db.Column(db.String(150), nullable=False)
    parent_folder_id = db.Column(db.Integer, db.ForeignKey('folders.id', ondelete='CASCADE'), nullable=True, index=True)
    created_at = db.Column(db.DateTime, default=utc_now)

    # Relationships
    subfolders = db.relationship('Folder', backref=db.backref('parent', remote_side=[id]), cascade='all, delete-orphan')
    files = db.relationship('FileRecord', backref='folder_rel', lazy='dynamic')

    def get_full_path(self) -> str:
        """Compute the full breadcrumb path like Engineering / AutoCAD / Panel."""
        path_parts = [self.folder_name]
        curr = self.parent
        while curr:
            path_parts.append(curr.folder_name)
            curr = curr.parent
        return " / ".join(reversed(path_parts))

    def to_dict(self, include_counts=True):
        data = {
            'id': self.id,
            'user_id': self.user_id,
            'folder_name': self.folder_name,
            'parent_folder_id': self.parent_folder_id,
            'full_path': self.get_full_path(),
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
        if include_counts:
            data['file_count'] = self.files.count()
            data['subfolder_count'] = len(self.subfolders)
        return data


class FileRecord(db.Model):
    __tablename__ = 'files'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    original_name = db.Column(db.String(255), nullable=False, index=True)
    stored_name = db.Column(db.String(255), unique=True, nullable=False)
    file_path = db.Column(db.String(500), nullable=False)
    file_extension = db.Column(db.String(20), nullable=False, index=True)
    file_size = db.Column(db.BigInteger, nullable=False)
    category = db.Column(db.String(50), nullable=False, index=True)
    folder_id = db.Column(db.Integer, db.ForeignKey('folders.id', ondelete='SET NULL'), nullable=True, index=True)
    description = db.Column(db.Text, nullable=True)
    tags = db.Column(db.String(255), nullable=True)
    is_favorite = db.Column(db.Boolean, default=False, index=True)
    uploaded_at = db.Column(db.DateTime, default=utc_now, index=True)
    updated_at = db.Column(db.DateTime, default=utc_now, onupdate=utc_now)
    last_opened_at = db.Column(db.DateTime, nullable=True, index=True)

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'original_name': self.original_name,
            'stored_name': self.stored_name,
            'file_extension': self.file_extension,
            'file_size': self.file_size,
            'category': self.category,
            'folder_id': self.folder_id,
            'folder_name': self.folder_rel.folder_name if self.folder_rel else 'Root',
            'folder_path': self.folder_rel.get_full_path() if self.folder_rel else '/',
            'description': self.description or '',
            'tags': [t.strip() for t in self.tags.split(',') if t.strip()] if self.tags else [],
            'tags_raw': self.tags or '',
            'is_favorite': bool(self.is_favorite),
            'uploaded_at': self.uploaded_at.isoformat() if self.uploaded_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'last_opened_at': self.last_opened_at.isoformat() if self.last_opened_at else None
        }


class ActivityLog(db.Model):
    __tablename__ = 'activity_logs'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    file_id = db.Column(db.Integer, db.ForeignKey('files.id', ondelete='SET NULL'), nullable=True)
    action = db.Column(db.String(50), nullable=False)
    details = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=utc_now)

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'file_id': self.file_id,
            'action': self.action,
            'details': self.details,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
