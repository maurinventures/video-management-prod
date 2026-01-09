#!/usr/bin/env python3
"""Check user verification status."""

import sys
import os

# Add paths
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)
sys.path.append(os.path.join(current_dir, 'scripts'))
sys.path.append(os.path.join(current_dir, 'web'))

from db import DatabaseSession, User

def check_user(email):
    """Check user verification status."""
    with DatabaseSession() as db_session:
        user = db_session.query(User).filter(User.email == email).first()
        if user:
            print(f"User found: {email}")
            print(f"  ID: {user.id}")
            print(f"  Name: {user.name}")
            print(f"  Email verified: {user.email_verified}")
            print(f"  Verification token: {user.verification_token}")
            print(f"  Token expires: {user.verification_token_expires}")
            print(f"  Created: {user.created_at}")
        else:
            print(f"User not found: {email}")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python check_user.py <email>")
        sys.exit(1)

    email = sys.argv[1]
    check_user(email)