#!/usr/bin/env python3
"""
Database Migration Script v2
Adds Protected Events and Archived Events fields to the Event table.

This script safely adds new columns without affecting existing data.
All new columns have safe defaults so existing events continue to work.

Run: python migrate_v2.py
"""
import os
import sys
import shutil
from datetime import datetime

# Add the app directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.models import db

# Migration SQL statements (SQLite compatible)
MIGRATIONS = [
    {
        'name': 'is_protected',
        'sql': 'ALTER TABLE events ADD COLUMN is_protected BOOLEAN DEFAULT 0',
        'check': "SELECT name FROM pragma_table_info('events') WHERE name='is_protected'"
    },
    {
        'name': 'access_token',
        'sql': 'ALTER TABLE events ADD COLUMN access_token VARCHAR(64)',
        'check': "SELECT name FROM pragma_table_info('events') WHERE name='access_token'"
    },
    {
        'name': 'is_archived',
        'sql': 'ALTER TABLE events ADD COLUMN is_archived BOOLEAN DEFAULT 0',
        'check': "SELECT name FROM pragma_table_info('events') WHERE name='is_archived'"
    },
    {
        'name': 'show_in_archive',
        'sql': 'ALTER TABLE events ADD COLUMN show_in_archive BOOLEAN DEFAULT 0',
        'check': "SELECT name FROM pragma_table_info('events') WHERE name='show_in_archive'"
    },
    {
        'name': 'archived_at',
        'sql': 'ALTER TABLE events ADD COLUMN archived_at DATETIME',
        'check': "SELECT name FROM pragma_table_info('events') WHERE name='archived_at'"
    },
]


def backup_database(db_path):
    """Create a backup of the database before migration."""
    if not os.path.exists(db_path):
        print(f"Database file not found at {db_path}")
        return None
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_path = f"{db_path}.backup_{timestamp}"
    shutil.copy2(db_path, backup_path)
    print(f"✓ Database backed up to: {backup_path}")
    return backup_path


def column_exists(cursor, column_name):
    """Check if a column already exists in the events table."""
    cursor.execute(f"SELECT name FROM pragma_table_info('events') WHERE name='{column_name}'")
    return cursor.fetchone() is not None


def run_migrations():
    """Run all pending migrations."""
    app = create_app()
    
    with app.app_context():
        # Get database path from URI
        db_uri = app.config['SQLALCHEMY_DATABASE_URI']
        
        if db_uri.startswith('sqlite:///'):
            db_path = db_uri.replace('sqlite:///', '')
            print(f"Database path: {db_path}")
            
            # Backup the database
            backup_path = backup_database(db_path)
            if not backup_path and os.path.exists(db_path):
                print("Warning: Could not create backup")
        else:
            print(f"Database URI: {db_uri}")
            print("Note: Backup is only automatic for SQLite databases")
        
        # Get raw connection
        connection = db.engine.raw_connection()
        cursor = connection.cursor()
        
        try:
            migrations_run = 0
            migrations_skipped = 0
            
            for migration in MIGRATIONS:
                if column_exists(cursor, migration['name']):
                    print(f"⊙ Column '{migration['name']}' already exists, skipping")
                    migrations_skipped += 1
                else:
                    print(f"→ Adding column '{migration['name']}'...")
                    cursor.execute(migration['sql'])
                    migrations_run += 1
                    print(f"✓ Column '{migration['name']}' added successfully")
            
            connection.commit()
            
            print("\n" + "=" * 50)
            print("Migration Summary:")
            print(f"  - Migrations run: {migrations_run}")
            print(f"  - Migrations skipped (already exist): {migrations_skipped}")
            print("=" * 50)
            
            if migrations_run > 0:
                print("\n✓ Migration completed successfully!")
            else:
                print("\n✓ Database is already up to date!")
            
            return True
            
        except Exception as e:
            connection.rollback()
            print(f"\n✗ Migration failed: {e}")
            print("Database has been rolled back. Your backup is still available.")
            return False
            
        finally:
            cursor.close()
            connection.close()


def verify_migration():
    """Verify that all columns were added correctly."""
    app = create_app()
    
    with app.app_context():
        connection = db.engine.raw_connection()
        cursor = connection.cursor()
        
        print("\nVerifying migration...")
        all_ok = True
        
        for migration in MIGRATIONS:
            if column_exists(cursor, migration['name']):
                print(f"  ✓ {migration['name']}")
            else:
                print(f"  ✗ {migration['name']} - MISSING!")
                all_ok = False
        
        cursor.close()
        connection.close()
        
        if all_ok:
            print("\n✓ All columns verified successfully!")
        else:
            print("\n✗ Some columns are missing!")
        
        return all_ok


if __name__ == '__main__':
    print("=" * 50)
    print("Certificate Portal - Database Migration v2")
    print("Protected Events & Archived Events")
    print("=" * 50)
    print()
    
    success = run_migrations()
    
    if success:
        verify_migration()
    
    sys.exit(0 if success else 1)
