"""
Authentication Service

Handles all authentication operations including login, registration, 2FA,
email verification, session management, and demo mode functionality.
"""

import re
import secrets
import hashlib
from datetime import datetime, timedelta
from uuid import UUID
from typing import Dict, Any, Optional, Tuple
import pyotp
import qrcode
import io
import base64

# Import database models and session
try:
    from scripts.db import DatabaseSession, User
    from scripts.config_loader import get_config
except ImportError:
    from ..scripts.db import DatabaseSession, User
    from ..scripts.config_loader import get_config

# Import boto3 for SES
try:
    import boto3
except ImportError:
    boto3 = None


def get_ses_client():
    """Get configured SES client."""
    config = get_config()
    return boto3.client(
        "ses",
        aws_access_key_id=config.secrets.get("aws", {}).get("access_key_id"),
        aws_secret_access_key=config.secrets.get("aws", {}).get("secret_access_key"),
        region_name="us-east-1",
    )


class AuthService:
    """Service for managing authentication and user operations."""

    # Demo mode configuration
    DEMO_EMAIL = 'demo@maurinventures.com'
    DEMO_USER_ID = 'demo-user-id'
    DEMO_USER_DATA = {
        'id': DEMO_USER_ID,
        'email': DEMO_EMAIL,
        'name': 'Joy',
        'email_verified': True,
        'is_active': True,
        'totp_enabled': False
    }

    @staticmethod
    def hash_password(password: str) -> str:
        """Hash password using SHA256."""
        return hashlib.sha256(password.encode()).hexdigest()

    @staticmethod
    def validate_email(email: str) -> bool:
        """Validate email format using regex."""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))

    @staticmethod
    def validate_password_strength(password: str) -> bool:
        """Validate password meets minimum requirements."""
        return len(password) >= 8

    @staticmethod
    def is_demo_mode(email: str) -> bool:
        """Check if request is for demo mode."""
        return email == AuthService.DEMO_EMAIL

    @staticmethod
    def authenticate_user(email: str, password: str) -> Dict[str, Any]:
        """
        Authenticate user credentials.

        Args:
            email: User email address
            password: User password

        Returns:
            Dictionary with authentication result and user data

        Raises:
            ValueError: If email or password is missing
        """
        if not email or not password:
            raise ValueError('Email and password are required')

        email = email.strip().lower()

        # Demo mode authentication
        if AuthService.is_demo_mode(email) and len(password) >= 8:
            return {
                'success': True,
                'is_demo': True,
                'user': AuthService.DEMO_USER_DATA.copy()
            }

        # Database authentication
        with DatabaseSession() as db_session:
            user = db_session.query(User).filter(User.email == email).first()
            if not user:
                return {'success': False, 'error': 'Invalid email or password'}

            # Check password
            password_hash = AuthService.hash_password(password)
            if user.password_hash != password_hash:
                return {'success': False, 'error': 'Invalid email or password'}

            if not user.is_active:
                return {'success': False, 'error': 'Account is disabled'}

            # Check if email is verified
            if not user.email_verified:
                return {'success': False, 'error': 'Please verify your email first. Check your inbox for the verification link.'}

            # Check 2FA status
            if user.totp_enabled == 1 and user.totp_secret:
                return {
                    'success': True,
                    'requires_2fa': True,
                    'user_id': str(user.id),
                    'user': {
                        'id': str(user.id),
                        'email': user.email,
                        'name': user.name
                    }
                }

            # 2FA not set up - force setup (mandatory for all users)
            return {
                'success': True,
                'requires_2fa_setup': True,
                'user_id': str(user.id),
                'user': {
                    'id': str(user.id),
                    'email': user.email,
                    'name': user.name
                }
            }

    @staticmethod
    def verify_2fa_token(user_id: str, token: str) -> Dict[str, Any]:
        """
        Verify 2FA TOTP token and complete authentication.

        Args:
            user_id: User ID for verification
            token: TOTP token from authenticator app

        Returns:
            Dictionary with verification result and user data
        """
        if not token:
            raise ValueError('Token is required')

        with DatabaseSession() as db_session:
            user = db_session.query(User).filter(User.id == UUID(user_id)).first()

            if not user or not user.totp_secret:
                return {'success': False, 'error': 'Invalid verification state'}

            # Verify TOTP code
            totp = pyotp.TOTP(user.totp_secret)
            if totp.verify(token, valid_window=1):
                # Update last login
                user.last_login = datetime.utcnow()
                db_session.commit()

                return {
                    'success': True,
                    'user': AuthService._serialize_user(user)
                }
            else:
                return {'success': False, 'error': 'Invalid code. Please try again.'}

    @staticmethod
    def setup_2fa_secret() -> Dict[str, Any]:
        """
        Generate new 2FA secret and QR code.

        Returns:
            Dictionary with secret and QR code data
        """
        secret = pyotp.random_base32()
        return {
            'secret': secret,
            'qr_code': AuthService._generate_qr_code(secret, 'Internal Platform')
        }

    @staticmethod
    def complete_2fa_setup(user_id: str, secret: str, token: str) -> Dict[str, Any]:
        """
        Complete 2FA setup by verifying token and saving secret.

        Args:
            user_id: User ID
            secret: TOTP secret
            token: Verification token from user

        Returns:
            Dictionary with setup result
        """
        if not token or not secret:
            raise ValueError('Token and secret are required')

        # Verify the token before enabling
        totp = pyotp.TOTP(secret)
        if not totp.verify(token, valid_window=1):
            return {'success': False, 'error': 'Invalid verification code'}

        with DatabaseSession() as db_session:
            user = db_session.query(User).filter(User.id == UUID(user_id)).first()
            if not user:
                return {'success': False, 'error': 'User not found'}

            user.totp_secret = secret
            user.totp_enabled = 1
            db_session.commit()

            return {'success': True, 'message': '2FA has been enabled successfully'}

    @staticmethod
    def register_user(name: str, email: str, password: str) -> Dict[str, Any]:
        """
        Register new user with email verification.

        Args:
            name: User's full name
            email: User's email address
            password: User's password

        Returns:
            Dictionary with registration result

        Raises:
            ValueError: If required fields are missing or invalid
        """
        if not name or not email or not password:
            raise ValueError('Name, email, and password are required')

        name = name.strip()
        email = email.strip().lower()

        # Check if email is in allowed list
        ALLOWED_EMAILS = {
            'joy@maurinventures.com',
            'branden@maurinventures.com',
            'stefanie@maurinventures.com',
            'dafneestardo@gmail.com',
            'chikiestardo143@gmail.com'
        }

        if email not in ALLOWED_EMAILS:
            raise ValueError('Registration is currently by invitation only. Please contact support if you need access.')

        # Validate email format
        if not AuthService.validate_email(email):
            raise ValueError('Invalid email format')

        # Validate password strength
        if not AuthService.validate_password_strength(password):
            raise ValueError('Password must be at least 8 characters long')

        # Demo mode registration
        if AuthService.is_demo_mode(email):
            return {
                'success': True,
                'is_demo': True,
                'user': {
                    **AuthService.DEMO_USER_DATA,
                    'name': name
                }
            }

        # Database registration
        with DatabaseSession() as db_session:
            # Check if email already exists
            existing = db_session.query(User).filter(User.email == email).first()
            if existing:
                raise ValueError('Email already registered')

            # Generate verification code (6 digits)
            verification_token = str(secrets.randbelow(900000) + 100000)  # 6-digit code
            expires_at = datetime.utcnow() + timedelta(hours=24)  # 24 hour expiry

            # Create user
            password_hash = AuthService.hash_password(password)
            user = User(
                email=email,
                name=name,
                password_hash=password_hash,
                is_active=1,
                email_verified=0,  # Require email verification
                totp_enabled=0,    # Will be set up after email verification
                verification_token=verification_token,
                verification_token_expires=expires_at
            )
            db_session.add(user)
            db_session.commit()

            # Send verification email
            AuthService.send_verification_email(email, name, verification_token)

            return {
                'success': True,
                'message': 'Registration successful. Please check your email to verify your account.',
                'user': AuthService._serialize_user(user)
            }

    @staticmethod
    def get_user_by_id(user_id: str, is_demo: bool = False) -> Optional[Dict[str, Any]]:
        """
        Get user information by ID.

        Args:
            user_id: User ID
            is_demo: Whether this is demo mode

        Returns:
            User data dictionary or None if not found
        """
        if is_demo and user_id == AuthService.DEMO_USER_ID:
            return AuthService.DEMO_USER_DATA.copy()

        try:
            user_uuid = UUID(user_id)
        except ValueError:
            # Invalid UUID format
            return None

        with DatabaseSession() as db_session:
            user = db_session.query(User).filter(User.id == user_uuid).first()
            if not user:
                return None

            return AuthService._serialize_user(user)

    @staticmethod
    def verify_email(token: str) -> Dict[str, Any]:
        """
        Verify email address using verification token.

        Args:
            token: Email verification token

        Returns:
            Dictionary with verification result
        """
        with DatabaseSession() as db_session:
            user = db_session.query(User).filter(
                User.verification_token == token,
                User.verification_token_expires > datetime.utcnow()
            ).first()

            if not user:
                return {'success': False, 'error': 'Invalid or expired verification token'}

            user.email_verified = 1
            user.verification_token = None
            user.verification_token_expires = None
            db_session.commit()

            return {
                'success': True,
                'message': 'Email verified successfully',
                'user': AuthService._serialize_user(user)
            }

    @staticmethod
    def resend_verification_email(email: str) -> Dict[str, Any]:
        """
        Resend email verification.

        Args:
            email: User's email address

        Returns:
            Dictionary with resend result
        """
        email = email.strip().lower()

        with DatabaseSession() as db_session:
            user = db_session.query(User).filter(User.email == email).first()
            if not user:
                return {'success': False, 'error': 'Email not found'}

            if user.email_verified:
                return {'success': False, 'error': 'Email already verified'}

            # Generate new verification code (6 digits)
            verification_token = str(secrets.randbelow(900000) + 100000)  # 6-digit code
            expires_at = datetime.utcnow() + timedelta(hours=24)

            user.verification_token = verification_token
            user.verification_token_expires = expires_at
            db_session.commit()

            # Send verification email
            AuthService.send_verification_email(email, user.name, verification_token)

            return {
                'success': True,
                'message': 'Verification email sent. Please check your inbox.'
            }

    @staticmethod
    def send_verification_email(to_email: str, name: str, verification_token: str) -> bool:
        """
        Send email verification link via AWS SES.

        Args:
            to_email: Recipient email
            name: Recipient name
            verification_token: Verification token

        Returns:
            True if email sent successfully, False otherwise
        """
        try:
            ses = get_ses_client()

            html_body = f"""
            <html>
            <body style="font-family: 'Inter', Arial, sans-serif; background-color: #f5f4ef; padding: 40px;">
                <div style="max-width: 500px; margin: 0 auto; background: white; padding: 40px; border-radius: 12px; box-shadow: 0 4px 20px rgba(0,0,0,0.08);">
                    <div style="text-align: center; margin-bottom: 30px;">
                        <div style="display: inline-block; width: 50px; height: 50px; background: #d97757; border-radius: 10px; line-height: 50px; color: white; font-size: 24px; font-weight: bold;">M</div>
                    </div>
                    <h1 style="color: #1a1a1a; font-size: 24px; margin-bottom: 20px; text-align: center;">Verify Your Email</h1>
                    <p style="color: #444; font-size: 16px; line-height: 1.6;">Hi {name},</p>
                    <p style="color: #444; font-size: 16px; line-height: 1.6;">Welcome to MV Internal! Please enter this verification code in the app:</p>
                    <div style="text-align: center; margin: 30px 0;">
                        <div style="display: inline-block; background: #f0f0f0; color: #333; padding: 20px 30px; border-radius: 8px; font-weight: bold; font-size: 32px; letter-spacing: 4px; font-family: 'Courier New', monospace;">{verification_token}</div>
                    </div>
                    <p style="color: #666; font-size: 14px; line-height: 1.6;">This code expires in 24 hours.</p>
                    <p style="color: #666; font-size: 14px; line-height: 1.6;">If you didn't create an account, you can safely ignore this email.</p>
                    <hr style="border: none; border-top: 1px solid #e5e4df; margin: 30px 0;">
                    <p style="color: #999; font-size: 12px; text-align: center;">MV Internal - Maurin Ventures</p>
                </div>
            </body>
            </html>
            """

            text_body = f"""
            Hi {name},

            Welcome to MV Internal! Please enter this verification code in the app:

            {verification_token}

            This code expires in 24 hours.

            If you didn't create an account, you can safely ignore this email.

            MV Internal - Maurin Ventures
            """

            response = ses.send_email(
                Source="ops@maurinventures.com",
                Destination={'ToAddresses': [to_email]},
                Message={
                    'Subject': {'Data': 'Verify Your Email - MV Internal'},
                    'Body': {
                        'Html': {'Data': html_body},
                        'Text': {'Data': text_body}
                    }
                }
            )

            return True

        except Exception as e:
            print(f"Email sending error: {e}")
            # Fallback: log verification code for development
            print(f"VERIFICATION CODE for {to_email}: {verification_token}")
            return False

    @staticmethod
    def _serialize_user(user) -> Dict[str, Any]:
        """
        Serialize user object to dictionary.

        Args:
            user: User model instance

        Returns:
            User data dictionary
        """
        return {
            'id': str(user.id),
            'name': user.name,
            'email': user.email,
            'is_active': bool(user.is_active),
            'email_verified': bool(user.email_verified),
            'totp_enabled': bool(user.totp_enabled),
            'created_at': user.created_at.isoformat(),
            'last_login': user.last_login.isoformat() if user.last_login else None,
        }

    @staticmethod
    def _generate_qr_code(secret: str, issuer: str) -> str:
        """
        Generate QR code for 2FA setup.

        Args:
            secret: TOTP secret
            issuer: Service name

        Returns:
            Base64 encoded QR code image
        """
        totp = pyotp.TOTP(secret)
        provisioning_uri = totp.provisioning_uri(
            name="user@maurinventuresinternal.com",
            issuer_name=issuer
        )

        # Generate QR code
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(provisioning_uri)
        qr.make(fit=True)

        img = qr.make_image(fill_color="black", back_color="white")

        # Convert to base64
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)
        img_str = base64.b64encode(buffer.getvalue()).decode()

        return f"data:image/png;base64,{img_str}"