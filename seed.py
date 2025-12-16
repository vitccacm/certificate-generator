#!/usr/bin/env python
"""
Database Seed Script
Creates required folders, initializes SQLite database, and adds default admin user.

Usage:
    python seed.py
"""
import os
import sys
from datetime import date

# Add project root to path
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_ROOT)


def create_directories():
    """Create required directories if they don't exist."""
    directories = [
        os.path.join(PROJECT_ROOT, 'instance'),
        os.path.join(PROJECT_ROOT, 'certificates'),
        os.path.join(PROJECT_ROOT, 'uploads'),
    ]
    
    for directory in directories:
        if not os.path.exists(directory):
            os.makedirs(directory)
            print(f"✓ Created directory: {directory}")
        else:
            print(f"✓ Directory exists: {directory}")


def seed_database():
    """Initialize database and create seed data."""
    # Create directories first
    print("=" * 50)
    print("Certificate Portal - Database Setup")
    print("=" * 50)
    print()
    
    print("[1/3] Creating directories...")
    create_directories()
    print()
    
    print("[2/3] Initializing database...")
    from app import create_app
    from app.models import db, Admin, Event
    
    app = create_app()
    
    with app.app_context():
        # Create all tables
        db.create_all()
        print("✓ SQLite database created")
        print(f"  Location: {app.config['SQLALCHEMY_DATABASE_URI']}")
        print()
        
        print("[3/3] Seeding data...")
        
        # Check if admin already exists
        existing_admin = Admin.query.filter_by(username='admin').first()
        
        if existing_admin:
            print("✓ Admin user already exists")
        else:
            # Create default admin user (super admin)
            admin = Admin(username='admin', is_super_admin=True)
            admin.set_password('admin123')
            db.session.add(admin)
            db.session.commit()
            print("✓ Default super admin user created")
            print("  ┌─────────────────────────────────┐")
            print("  │  Username: admin                │")
            print("  │  Password: admin123             │")
            print("  └─────────────────────────────────┘")
        
        # Create a sample event (optional)
        if Event.query.count() == 0:
            sample_event = Event(
                name='Sample Tech Workshop 2024',
                description='This is a sample event demonstrating the certificate portal. You can edit or delete it from the admin panel.',
                event_date=date(2024, 12, 15),
                is_visible=True
            )
            db.session.add(sample_event)
            db.session.commit()
            print("✓ Sample event created")
        
        print()
        print("=" * 50)
        print("✓ Setup Complete!")
        print("=" * 50)
        print()
        print("Next steps:")
        print("  1. Run the server:  flask run --debug --port 5000")
        print("  2. Open browser:    http://localhost:5000/")
        print("  3. Admin panel:     http://localhost:5000/admin")
        print()
        print("⚠️  Remember to change the default password!")
        print()


if __name__ == '__main__':
    seed_database()
