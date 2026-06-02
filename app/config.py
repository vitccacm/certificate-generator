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

    # Secret used to derive certificate-verification QR tokens (HMAC of recipient email).
    # Set VERIFY_TOKEN_SECRET in the production deployment. If unset it falls back to
    # SECRET_KEY (also mandatory in prod) so there is never a silent empty-key path that
    # would let anyone forge verification tokens. Rotating this value invalidates all
    # previously issued verification QR links.
    VERIFY_TOKEN_SECRET = os.environ.get('VERIFY_TOKEN_SECRET') or SECRET_KEY
    
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
    ALLOWED_EXTENSIONS = {'png'}
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
