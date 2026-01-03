"""
Database Models for Certificate Download Portal
"""
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()


class Admin(db.Model):
    """Admin user model for authentication"""
    __tablename__ = 'admins'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    is_super_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime, nullable=True)
    
    # Relationship to admin logs
    logs = db.relationship('AdminLog', backref='admin', lazy='dynamic',
                          cascade='all, delete-orphan')
    
    def set_password(self, password):
        """Hash and set password using pbkdf2 (compatible with Python 3.7)"""
        self.password_hash = generate_password_hash(password, method='pbkdf2:sha256')
    
    def check_password(self, password):
        """Verify password against hash"""
        return check_password_hash(self.password_hash, password)
    
    def __repr__(self):
        return f'<Admin {self.username}>'


class AdminLog(db.Model):
    """Admin activity log for tracking actions"""
    __tablename__ = 'admin_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    admin_id = db.Column(db.Integer, db.ForeignKey('admins.id'), nullable=True)
    action = db.Column(db.String(100), nullable=False)
    details = db.Column(db.Text, nullable=True)
    ip_address = db.Column(db.String(50), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<AdminLog {self.action} at {self.created_at}>'


class Event(db.Model):
    """Event model for organizing certificates"""
    __tablename__ = 'events'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    event_date = db.Column(db.Date, nullable=True)
    is_visible = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Template-based certificate generation fields
    template_filename = db.Column(db.String(500), nullable=True)  # PDF template file
    name_position_x = db.Column(db.Float, nullable=True)  # X position (percentage 0-100)
    name_position_y = db.Column(db.Float, nullable=True)  # Y position (percentage 0-100)
    font_size = db.Column(db.Integer, default=36)  # Font size for name
    font_color = db.Column(db.String(20), default='#000000')  # Hex color for name
    font_name = db.Column(db.String(50), default='helv')  # Font name for certificate
    
    # Protected event fields (signed URL access only)
    is_protected = db.Column(db.Boolean, default=False)
    access_token = db.Column(db.String(64), nullable=True)
    
    # Archived event fields
    is_archived = db.Column(db.Boolean, default=False)
    show_in_archive = db.Column(db.Boolean, default=False)
    archived_at = db.Column(db.DateTime, nullable=True)
    
    # Relationship to participants
    participants = db.relationship('Participant', backref='event', lazy='dynamic',
                                   cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Event {self.name}>'
    
    @property
    def has_template(self):
        """Check if event uses template-based certificates"""
        return self.template_filename is not None
    
    @property
    def participant_count(self):
        """Get total number of participants"""
        return self.participants.count()
    
    @property
    def total_downloads(self):
        """Get total downloads across all participants"""
        return sum(p.download_count for p in self.participants)
    
    def generate_access_token(self):
        """Generate a new access token for protected events"""
        import secrets
        self.access_token = secrets.token_hex(32)
        return self.access_token
    
    def get_signed_url(self, base_url=''):
        """Get the signed URL for protected event access"""
        if not self.is_protected or not self.access_token:
            return None
        return f"{base_url}/event/{self.id}?token={self.access_token}"


class Participant(db.Model):
    """Participant/Certificate record model"""
    __tablename__ = 'participants'
    
    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.Integer, db.ForeignKey('events.id'), nullable=False)
    name = db.Column(db.String(200), nullable=False)
    email = db.Column(db.String(200), nullable=False)
    certificate_filename = db.Column(db.String(500), nullable=True)  # Nullable for template-based events
    download_count = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship to download logs
    download_logs = db.relationship('DownloadLog', backref='participant', lazy='dynamic',
                                    cascade='all, delete-orphan')
    
    # Unique constraint: one certificate per email per event
    __table_args__ = (
        db.UniqueConstraint('event_id', 'email', name='unique_event_email'),
    )
    
    def __repr__(self):
        return f'<Participant {self.email} - Event {self.event_id}>'
    
    def increment_download(self, ip_address=None):
        """Increment download count and log the download"""
        self.download_count += 1
        log = DownloadLog(participant_id=self.id, ip_address=ip_address)
        db.session.add(log)


class DownloadLog(db.Model):
    """Download log for tracking certificate downloads"""
    __tablename__ = 'download_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    participant_id = db.Column(db.Integer, db.ForeignKey('participants.id'), nullable=False)
    downloaded_at = db.Column(db.DateTime, default=datetime.utcnow)
    ip_address = db.Column(db.String(50), nullable=True)
    
    def __repr__(self):
        return f'<DownloadLog {self.participant_id} at {self.downloaded_at}>'


def log_admin_action(admin_id, action, details=None, ip_address=None):
    """Helper function to create admin log entry"""
    log = AdminLog(
        admin_id=admin_id,
        action=action,
        details=details,
        ip_address=ip_address
    )
    db.session.add(log)
    return log
