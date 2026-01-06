#!/usr/bin/env python3
"""
Create user account for joy@maurinventures.com
"""

import hashlib
import sys
import os

# Add the scripts directory to the path so we can import db
sys.path.append(os.path.join(os.path.dirname(__file__), 'scripts'))

try:
    from db import User, DatabaseSession
    print("✅ Database imports successful")
except Exception as e:
    print(f"❌ Database import failed: {e}")
    sys.exit(1)

def create_user_account():
    """Create user account with email verification already enabled."""

    email = "joy@maurinventures.com"
    name = "Joy"
    password = "temppass123"  # You can change this after first login

    print(f"🔑 Creating account for {email}")
    print("=" * 40)

    try:
        with DatabaseSession() as db_session:
            # Check if user already exists
            existing = db_session.query(User).filter(User.email == email).first()
            if existing:
                print(f"⚠️  User {email} already exists!")
                return False

            # Create password hash
            password_hash = hashlib.sha256(password.encode()).hexdigest()

            # Create user with email already verified
            user = User(
                email=email,
                name=name,
                password_hash=password_hash,
                is_active=1,
                email_verified=1,  # Skip email verification
                totp_enabled=0,    # Disable 2FA for now
                verification_token=None,
                verification_token_expires=None
            )

            db_session.add(user)
            db_session.commit()

            print(f"✅ Successfully created user account!")
            print(f"📧 Email: {email}")
            print(f"👤 Name: {name}")
            print(f"🔑 Password: {password}")
            print(f"")
            print(f"🌐 Now you can login at: http://localhost:3000")
            print(f"")
            print(f"💡 Remember to change your password after first login!")

            return True

    except Exception as e:
        print(f"❌ Failed to create user: {str(e)}")
        return False

if __name__ == "__main__":
    success = create_user_account()
    if success:
        print(f"\n🎉 Account creation complete!")
    else:
        print(f"\n❌ Account creation failed!")
        sys.exit(1)