#!/usr/bin/env python3
"""
Migration script to add starred column to conversations table.
This script uses the application's database configuration to safely apply the migration.
"""

import sys
import os

# Add the project root to the path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

# Now import from scripts module
from scripts.db import DatabaseSession
from sqlalchemy import text

def main():
    """Apply the starred column migration."""
    print("Applying starred column migration...")

    try:
        with DatabaseSession() as session:
            # Check if column already exists
            result = session.execute(text("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name='conversations' AND column_name='starred'
            """))

            if result.fetchone():
                print("✅ Starred column already exists, skipping migration.")
                return

            # Add the starred column
            session.execute(text("""
                ALTER TABLE conversations
                ADD COLUMN starred BOOLEAN DEFAULT FALSE
            """))

            # Update existing conversations to have starred = FALSE
            session.execute(text("""
                UPDATE conversations SET starred = FALSE WHERE starred IS NULL
            """))

            # Add comment
            session.execute(text("""
                COMMENT ON COLUMN conversations.starred IS 'Whether this conversation is starred by the user'
            """))

            session.commit()
            print("✅ Successfully added starred column to conversations table.")

    except Exception as e:
        print(f"❌ Error applying migration: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()