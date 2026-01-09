#!/usr/bin/env python3
"""Test email sending directly."""

import sys
import os

# Add paths
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)
sys.path.append(os.path.join(current_dir, 'scripts'))
sys.path.append(os.path.join(current_dir, 'web'))
sys.path.append(os.path.join(current_dir, 'web/services'))

from auth_service import AuthService

def test_email():
    """Test sending verification email."""
    try:
        print("Testing email sending...")
        result = AuthService.send_verification_email("joy@maurinventures.com", "Joy Test", "767524")
        print(f"Email send result: {result}")
        return result
    except Exception as e:
        print(f"Email sending failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_email()