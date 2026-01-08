#!/usr/bin/env python3
"""Debug registration process with full logging."""

import sys
import os
import io
import contextlib
from datetime import datetime

# Add paths
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)
sys.path.append(os.path.join(current_dir, 'scripts'))
sys.path.append(os.path.join(current_dir, 'web'))
sys.path.append(os.path.join(current_dir, 'web/services'))

from auth_service import AuthService

def debug_register():
    """Test registration with full debug output capture."""

    # Create log file
    log_file = f"/tmp/registration_debug_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

    with open(log_file, 'w') as f:
        # Redirect stdout/stderr to capture all output
        original_stdout = sys.stdout
        original_stderr = sys.stderr

        try:
            # Capture output
            output = io.StringIO()
            sys.stdout = output
            sys.stderr = output

            print(f"=== REGISTRATION DEBUG LOG - {datetime.now()} ===")
            print("Testing registration for joy@maurinventures.com")
            print()

            # Test registration
            try:
                result = AuthService.register_user("Joy Test", "joy@maurinventures.com", "testpassword123")
                print(f"Registration result: {result}")
                print()

                # Test email sending separately
                print("=== TESTING EMAIL SENDING SEPARATELY ===")
                if result.get('success'):
                    print("Registration successful, testing email send...")
                    # We don't have the verification token from result, so get it from DB
                    from db import DatabaseSession, User
                    with DatabaseSession() as db_session:
                        user = db_session.query(User).filter(User.email == "joy@maurinventures.com").first()
                        if user and user.verification_token:
                            email_result = AuthService.send_verification_email("joy@maurinventures.com", "Joy Test", user.verification_token)
                            print(f"Separate email test result: {email_result}")
                        else:
                            print("Could not find user or verification token in database")
                else:
                    print("Registration failed, cannot test email")

            except Exception as e:
                print(f"Registration exception: {e}")
                import traceback
                traceback.print_exc()

            print()
            print("=== END DEBUG LOG ===")

            # Get the output
            captured_output = output.getvalue()

            # Restore stdout/stderr
            sys.stdout = original_stdout
            sys.stderr = original_stderr

            # Write to file and also print to console
            f.write(captured_output)
            print(captured_output)

            print(f"\nDEBUG LOG SAVED TO: {log_file}")
            return log_file

        except Exception as e:
            # Restore stdout/stderr in case of error
            sys.stdout = original_stdout
            sys.stderr = original_stderr
            f.write(f"Error during debug: {e}\n")
            print(f"Error during debug: {e}")
            return log_file

if __name__ == "__main__":
    debug_register()