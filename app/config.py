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

    # Email (SMTP) configuration for certificate notification emails.
    # Edit these values directly (on the server) to enable email sending.
    # The "your-..." placeholders keep sending DISABLED until replaced.
    # WARNING: do not commit real credentials to git - replace the
    # placeholders only on the deployed copy of this file.
    MAIL_SERVER = 'mailserverlink       '
    MAIL_PORT = 465
    MAIL_USE_TLS = False  # STARTTLS (port 587) - off for port 465
    MAIL_USE_SSL = True   # implicit SSL (port 465)
    MAIL_USERNAME = 'username'
    MAIL_PASSWORD = 'password'
    # Display name only - the email address is added automatically
    MAIL_SENDER_NAME = 'ACM VIT Chennai'
    # From address; falls back to MAIL_USERNAME when empty
    MAIL_DEFAULT_SENDER = ''
    # Seconds to wait between consecutive emails (rate-limit protection)
    MAIL_SEND_DELAY = 1.0


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
