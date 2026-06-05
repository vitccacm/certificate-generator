#!/usr/bin/env python3
"""
Database Migration Script v4
Adds the email_logs table for certificate notification emails.

This script safely creates the new table without affecting existing data.

Run: python migrate_v4.py
"""
import os
import sys
import shutil
from datetime import datetime

# Add the app directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.models import db

TABLE_NAME = 'email_logs'

CREATE_TABLE_SQL = """
CREATE TABLE email_logs (
    id INTEGER NOT NULL PRIMARY KEY,
    participant_id INTEGER NOT NULL REFERENCES participants (id),
    admin_id INTEGER REFERENCES admins (id),
    sent_at DATETIME,
    status VARCHAR(10) NOT NULL DEFAULT 'sent',
    error TEXT
)
"""


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


def table_exists(cursor, table_name):
    """Check if a table already exists."""
    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
        (table_name,)
    )
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
            if table_exists(cursor, TABLE_NAME):
                print(f"⊙ Table '{TABLE_NAME}' already exists, skipping")
            else:
                print(f"→ Creating table '{TABLE_NAME}'...")
                cursor.execute(CREATE_TABLE_SQL)
                print(f"✓ Table '{TABLE_NAME}' created successfully")

            connection.commit()
            print("\n✓ Migration completed successfully!")
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
    """Verify that the table was created correctly."""
    app = create_app()

    with app.app_context():
        connection = db.engine.raw_connection()
        cursor = connection.cursor()

        print("\nVerifying migration...")
        ok = table_exists(cursor, TABLE_NAME)
        print(f"  {'✓' if ok else '✗'} {TABLE_NAME}{'' if ok else ' - MISSING!'}")

        cursor.close()
        connection.close()

        if ok:
            print("\n✓ Table verified successfully!")
        else:
            print("\n✗ Table is missing!")

        return ok


if __name__ == '__main__':
    print("=" * 50)
    print("Certificate Portal - Database Migration v4")
    print("Certificate notification emails (email_logs)")
    print("=" * 50)
    print()

    success = run_migrations()

    if success:
        verify_migration()

    sys.exit(0 if success else 1)
