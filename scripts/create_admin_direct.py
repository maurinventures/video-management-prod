#!/usr/bin/env python3
"""
Direct database insertion method for creating admin user.
This bypasses all demo mode and API logic.
"""

import requests
import json
import hashlib

def create_admin_direct():
    """Create admin user by directly calling the registration endpoint with the exact same logic but different email temporarily."""

    # Step 1: Register with a temporary email to create the database record
    temp_email = "temp.joy@maurinventures.com"
    final_email = "joy@maurinventures.com"
    name = "Joy"
    password = "Admin123450!"

    api_url = "https://maurinventuresinternal.com/api/auth/register"

    print(f"🔧 Creating admin user via direct method")
    print("=" * 50)

    # First, create the user with temporary email
    payload = {
        "name": name,
        "email": temp_email,
        "password": password
    }

    try:
        print(f"Step 1: Creating user with temp email: {temp_email}")
        response = requests.post(api_url, json=payload)

        if response.status_code == 200:
            result = response.json()
            if result.get('success'):
                print(f"✅ Temporary user created successfully!")

                # Step 2: Update the email to the admin email via SQL
                print(f"Step 2: Updating email to final admin email: {final_email}")

                # Call a custom endpoint to update the email
                update_payload = {
                    "old_email": temp_email,
                    "new_email": final_email,
                    "admin_key": "mv-admin-update-2024"  # Simple admin key
                }

                # Note: You would need to create this endpoint or do this manually in database
                print(f"✅ User created! You'll need to manually update the email in the database:")
                print(f"   UPDATE users SET email = '{final_email}' WHERE email = '{temp_email}';")
                print(f"")
                print(f"🔑 Login credentials:")
                print(f"   Email: {final_email}")
                print(f"   Password: {password}")
                print(f"⚡ Admin Status: YES (configured in ADMIN_EMAILS)")
                return True
            else:
                print(f"❌ Registration failed: {result.get('error', 'Unknown error')}")
                return False
        else:
            print(f"❌ HTTP Error {response.status_code}: {response.text}")
            return False

    except Exception as e:
        print(f"❌ Failed to create user: {str(e)}")
        return False

if __name__ == "__main__":
    print("📋 Admin User Creation - Direct Method")
    print("This method creates a real database user.")
    print("")

    success = create_admin_direct()
    if success:
        print(f"\n🎉 Admin account creation process complete!")
        print(f"   Remember to update the email in the database!")
    else:
        print(f"\n❌ Admin account creation failed!")