#!/usr/bin/env python3
"""
Alternative method to create admin user using the registration API endpoint.
This can be used if the direct database method doesn't work.
"""

import requests
import hashlib

def create_admin_via_api():
    """Create admin user via the registration API endpoint."""

    # User details
    email = "joy@maurinventures.com"
    name = "Joy"
    password = "Admin123450!"

    # API endpoint (correct endpoint from Flask app)
    api_url = "https://maurinventuresinternal.com/api/auth/register"

    print(f"🌐 Creating admin user via API: {email}")
    print("=" * 50)

    payload = {
        "name": name,
        "email": email,
        "password": password
    }

    try:
        response = requests.post(api_url, json=payload)

        if response.status_code == 200:
            result = response.json()
            if result.get('success'):
                print(f"✅ Successfully created admin user account!")
                print(f"📧 Email: {email}")
                print(f"👤 Name: {name}")
                print(f"🔑 Password: {password}")
                print(f"⚡ Admin Status: YES (configured in ADMIN_EMAILS)")
                print(f"")
                print(f"🌐 Login at: https://maurinventuresinternal.com")
                print(f"")
                print(f"🛡️ This user has admin privileges in the system!")
                return True
            else:
                print(f"❌ Registration failed: {result.get('error', 'Unknown error')}")
                return False
        else:
            print(f"❌ HTTP Error {response.status_code}: {response.text}")
            return False

    except Exception as e:
        print(f"❌ Failed to create user via API: {str(e)}")
        return False

if __name__ == "__main__":
    print("📋 Admin User Creation - API Method")
    print("This method uses the registration API endpoint.")
    print("")

    success = create_admin_via_api()
    if success:
        print(f"\n🎉 Admin account creation complete!")
    else:
        print(f"\n❌ Admin account creation failed!")