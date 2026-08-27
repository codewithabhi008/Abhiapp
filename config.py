import os
from datetime import timedelta

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

class Config:
    """Application configuration."""
    BASE_DIR = BASE_DIR
    SECRET_KEY = os.environ.get('SECRET_KEY', 'abhiapp_super_secret_vault_key_2026_x89a#$')
    
    # SQLite Database location (easily migratable to PostgreSQL/MySQL via SQLALCHEMY_DATABASE_URI env var)
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        'DATABASE_URL', 
        f"sqlite:///{os.path.join(BASE_DIR, 'abhiapp_vault.db')}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Storage Configuration
    STORAGE_DIR = os.path.join(BASE_DIR, 'storage')
    USERS_STORAGE_DIR = os.path.join(STORAGE_DIR, 'users')
    
    # Upload limits: 1024 MB (1 GB) per request max
    MAX_CONTENT_LENGTH = 1024 * 1024 * 1024 
    
    # Session security
    PERMANENT_SESSION_LIFETIME = timedelta(days=14)
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    SESSION_COOKIE_SECURE = False  # Set to True in HTTPS production
    
    # Default Categories
    DEFAULT_CATEGORIES = [
        "PDF Documents",
        "AutoCAD Drawings",
        "SolidWorks Files",
        "Engineering Documents",
        "Excel / BOQ / BOM",
        "Images",
        "Programming",
        "Personal",
        "Other"
    ]
