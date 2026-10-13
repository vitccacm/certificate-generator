#!/usr/bin/env python3
"""
Database Migration Script v5
Adds the qr_on_custom_certificates column to events table for
adding verification QR codes to custom uploaded certificates.

This script safely adds the new column without affecting existing data.

Run: python migrate_v5.py
"""
import os
import sys
import shutil
from datetime import datetime

# Add the app directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.models import db

TABLE_NAME = 'events'
COLUMN_NAME = 'qr_on_custom_certificates'

ADD_COLUMN_SQL = f"""
ALTER TABLE {TABLE_NAME} ADD COLUMN {COLUMN_NAME} BOOLEAN DEFAULT 0 NOT NULL;
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


def column_exists(cursor, table_name, column_name):
    """Check if a column already exists in a table."""
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = cursor.fetchall()
    return any(col[1] == column_name for col in columns)


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
            if column_exists(cursor, TABLE_NAME, COLUMN_NAME):
                print(f"⊙ Column '{COLUMN_NAME}' already exists in '{TABLE_NAME}', skipping")
            else:
                print(f"→ Adding column '{COLUMN_NAME}' to '{TABLE_NAME}'...")
                cursor.execute(ADD_COLUMN_SQL)
                print(f"✓ Column '{COLUMN_NAME}' added successfully")

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
    """Verify that the column was added correctly."""
    app = create_app()

    with app.app_context():
        connection = db.engine.raw_connection()
        cursor = connection.cursor()

        print("\nVerifying migration...")
        ok = column_exists(cursor, TABLE_NAME, COLUMN_NAME)
        print(f"  {'✓' if ok else '✗'} {TABLE_NAME}.{COLUMN_NAME}{'' if ok else ' - MISSING!'}")

        cursor.close()
        connection.close()

        if ok:
            print("\n✓ Column verified successfully!")
        else:
            print("\n✗ Column is missing!")

        return ok


if __name__ == '__main__':
    print("=" * 50)
    print("Certificate Portal - Database Migration v5")
    print("Add QR on custom certificates option")
    print("=" * 50)
    print()

    success = run_migrations()

    if success:
        verify_migration()

    sys.exit(0 if success else 1)