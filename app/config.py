"""
Application Configuration
Supports SQLite (default), MySQL, and PostgreSQL
"""
import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    """Base configuration"""
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    
    # Database configuration
    # Default: SQLite
    # For MySQL: mysql+pymysql://user:password@localhost/dbname
    # For PostgreSQL: postgresql://user:password@localhost/dbname
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(os.path.dirname(os.path.dirname(__file__)), 'instance', 'certificates.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # File upload configuration
    UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'uploads')
    CERTIFICATES_FOLDER = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'certificates')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB max upload
    ALLOWED_EXTENSIONS = {'pdf'}
    ALLOWED_BULK_EXTENSIONS = {'csv', 'xlsx', 'xls'}
    
    # CAPTCHA configuration
    CAPTCHA_LENGTH = 6
    CAPTCHA_WIDTH = 200
    CAPTCHA_HEIGHT = 70


class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True


class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    # In production, ensure SECRET_KEY is set via environment variable


class TestingConfig(Config):
    """Testing configuration"""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'


# Configuration dictionary
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}
