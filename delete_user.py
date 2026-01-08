#!/usr/bin/env python3
"""Delete user for testing purposes."""

import sys
import os

# Add both scripts and web to path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)
sys.path.append(os.path.join(current_dir, 'scripts'))
sys.path.append(os.path.join(current_dir, 'web'))

from db import DatabaseSession, User

def delete_user(email):
    """Delete user by email."""
    with DatabaseSession() as db_session:
        user = db_session.query(User).filter(User.email == email).first()
        if user:
            print(f"Deleting user: {email} (ID: {user.id})")
            db_session.delete(user)
            db_session.commit()
            print("User deleted successfully")
        else:
            print(f"User not found: {email}")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python delete_user.py <email>")
        sys.exit(1)

    email = sys.argv[1]
    delete_user(email)