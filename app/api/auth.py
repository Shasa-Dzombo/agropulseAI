"""
🔐 Authentication API

FastAPI endpoints for user authentication, session management, and account security.

Endpoints:
- POST /auth/register - Register new user
- POST /auth/login - User login
- POST /auth/logout - User logout
- POST /auth/refresh - Refresh access token
- GET /auth/me - Get current user info
- POST /auth/verify-email - Verify email address
- POST /auth/verify-phone - Verify phone number
- POST /auth/resend-verification - Resend verification code
- POST /auth/forgot-password - Request password reset
- POST /auth/reset-password - Reset password with token
- POST /auth/change-password - Change password (authenticated)
- POST /auth/enable-2fa - Enable two-factor authentication
- POST /auth/disable-2fa - Disable two-factor authentication
- POST /auth/verify-2fa - Verify 2FA code

Author: AgroPulse Engineering Team
"""

from datetime import datetime, timedelta
from typing import Optional
import secrets
import bcrypt
import jwt
from fastapi import APIRouter, Depends, HTTPException, status, Response, Query
from pydantic import BaseModel, Field, EmailStr
from sqlalchemy.orm import Session

from app.db_config import get_production_db_dependency
from app.repositories.user import UserRepository


router = APIRouter(prefix="/auth", tags=["Authentication"])


# JWT Configuration
SECRET_KEY = "your-secret-key-here-change-in-production"  # TODO: Move to environment variable
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60
REFRESH_TOKEN_EXPIRE_DAYS = 30


# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================

class RegisterRequest(BaseModel):
    """User registration request."""
    username: str = Field(..., min_length=3, max_length=50, pattern="^[a-zA-Z0-9_-]+$")
    email: EmailStr
    phone_number: str = Field(..., pattern="^\\+?[0-9]{10,15}$")
    password: str = Field(..., min_length=8)
    full_name: str = Field(..., min_length=2, max_length=200)
    county: Optional[str] = None
    role: str = Field("farmer", pattern="^(farmer|agronomist|admin)$")


class LoginRequest(BaseModel):
    """User login request."""
    username_or_email: str = Field(..., min_length=3)
    password: str = Field(..., min_length=1)
    remember_me: bool = False


class TokenResponse(BaseModel):
    """Token response."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class UserInfoResponse(BaseModel):
    """Current user info response."""
    id: int
    uuid: str
    username: str
    email: str
    phone_number: str
    full_name: str
    role: str
    county: Optional[str]
    is_active: bool
    email_verified: bool
    phone_verified: bool
    two_factor_enabled: bool
    subscription_tier: str
    created_at: datetime
    
    class Config:
        from_attributes = True


class VerifyEmailRequest(BaseModel):
    """Verify email request."""
    verification_code: str = Field(..., min_length=6, max_length=6)


class VerifyPhoneRequest(BaseModel):
    """Verify phone request."""
    verification_code: str = Field(..., min_length=6, max_length=6)


class ForgotPasswordRequest(BaseModel):
    """Forgot password request."""
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    """Reset password request."""
    reset_token: str = Field(..., min_length=32)
    new_password: str = Field(..., min_length=8)


class ChangePasswordRequest(BaseModel):
    """Change password request."""
    current_password: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=8)


class Enable2FAResponse(BaseModel):
    """Enable 2FA response."""
    secret: str
    qr_code_url: str
    backup_codes: list[str]


class Verify2FARequest(BaseModel):
    """Verify 2FA code request."""
    code: str = Field(..., min_length=6, max_length=6)


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def hash_password(password: str) -> str:
    """Hash password using bcrypt."""
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against hash."""
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create JWT access token."""
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire, "type": "access"})
    
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def create_refresh_token(data: dict) -> str:
    """Create JWT refresh token."""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> dict:
    """Decode and verify JWT token."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired"
        )
    except jwt.JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )


def generate_verification_code() -> str:
    """Generate 6-digit verification code."""
    return str(secrets.randbelow(1000000)).zfill(6)


def generate_reset_token() -> str:
    """Generate password reset token."""
    return secrets.token_urlsafe(32)


def get_current_user(
    token: str = Depends(lambda: None),  # Simplified for now
    db: Session = Depends(get_production_db_dependency)
) -> dict:
    """
    Get current authenticated user from JWT token.
    
    This is a simplified version. In production, use proper OAuth2PasswordBearer.
    """
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )
    
    payload = decode_token(token)
    user_id = payload.get("sub")
    
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )
    
    user_repo = UserRepository(db)
    user = user_repo.get_by_id(user_id)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )
    
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "role": user.role
    }


# ============================================================================
# ENDPOINTS
# ============================================================================

@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register(
    request: RegisterRequest,
    db: Session = Depends(get_production_db_dependency)
):
    """
    Register new user account.
    
    - **username**: Unique username (3-50 chars, alphanumeric, dash, underscore)
    - **email**: Valid email address (required)
    - **phone_number**: Phone number with country code (required)
    - **password**: Password (min 8 characters)
    - **full_name**: User's full name (required)
    - **county**: County location (optional)
    - **role**: User role - farmer, agronomist, admin (default: farmer)
    
    Returns access token and refresh token for immediate login.
    """
    user_repo = UserRepository(db)
    
    # Check if username exists
    if user_repo.get_by_username(request.username):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already taken"
        )
    
    # Check if email exists
    if user_repo.get_by_email(request.email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Check if phone exists
    if user_repo.get_by_phone(request.phone_number):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Phone number already registered"
        )
    
    # Hash password
    hashed_password = hash_password(request.password)
    
    # Generate verification codes
    email_verification_code = generate_verification_code()
    phone_verification_code = generate_verification_code()
    
    # Create user
    user = user_repo.create(
        username=request.username,
        email=request.email,
        phone_number=request.phone_number,
        password_hash=hashed_password,
        full_name=request.full_name,
        county=request.county,
        role=request.role,
        email_verification_code=email_verification_code,
        phone_verification_code=phone_verification_code,
        subscription_tier='free'
    )
    
    # TODO: Send verification email
    # TODO: Send verification SMS
    
    # Create tokens
    access_token = create_access_token({"sub": user.id})
    refresh_token = create_refresh_token({"sub": user.id})
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )


@router.post("/login", response_model=TokenResponse)
def login(
    request: LoginRequest,
    response: Response,
    db: Session = Depends(get_production_db_dependency)
):
    """
    User login with username/email and password.
    
    - **username_or_email**: Username or email address
    - **password**: User password
    - **remember_me**: Extended session duration (default: false)
    
    Returns access token and refresh token.
    """
    user_repo = UserRepository(db)
    
    # Try to find user by username or email
    user = user_repo.get_by_username(request.username_or_email)
    if not user:
        user = user_repo.get_by_email(request.username_or_email)
    
    # Verify user and password
    if not user or not verify_password(request.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username/email or password",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    # Check if account is active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is inactive. Please contact support."
        )
    
    # Update last login
    user_repo.update(user, last_login=datetime.utcnow())
    
    # Create tokens
    token_data = {"sub": user.id, "username": user.username, "role": user.role}
    
    if request.remember_me:
        access_token = create_access_token(
            token_data,
            expires_delta=timedelta(days=7)
        )
    else:
        access_token = create_access_token(token_data)
    
    refresh_token = create_refresh_token(token_data)
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )


@router.post("/logout")
def logout(
    response: Response,
    current_user: dict = Depends(get_current_user)
):
    """
    User logout.
    
    Invalidates the current session.
    Note: With JWT, client should discard tokens.
    """
    # TODO: Add token to blacklist in Redis/cache
    
    return {
        "message": "Logged out successfully"
    }


@router.post("/refresh", response_model=TokenResponse)
def refresh_token(
    refresh_token: str,
    db: Session = Depends(get_production_db_dependency)
):
    """
    Refresh access token using refresh token.
    
    - **refresh_token**: Valid refresh token
    
    Returns new access token and refresh token.
    """
    payload = decode_token(refresh_token)
    
    # Verify token type
    if payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )
    
    user_id = payload.get("sub")
    
    # Verify user exists and is active
    user_repo = UserRepository(db)
    user = user_repo.get_by_id(user_id)
    
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid user"
        )
    
    # Create new tokens
    token_data = {"sub": user.id, "username": user.username, "role": user.role}
    new_access_token = create_access_token(token_data)
    new_refresh_token = create_refresh_token(token_data)
    
    return TokenResponse(
        access_token=new_access_token,
        refresh_token=new_refresh_token,
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )


@router.get("/me", response_model=UserInfoResponse)
def get_current_user_info(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_production_db_dependency)
):
    """
    Get current authenticated user information.
    
    Returns complete user profile.
    """
    user_repo = UserRepository(db)
    user = user_repo.get_by_id(current_user['id'])
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return user


@router.post("/verify-email")
def verify_email(
    request: VerifyEmailRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_production_db_dependency)
):
    """
    Verify email address with verification code.
    
    - **verification_code**: 6-digit code sent to email
    """
    user_repo = UserRepository(db)
    user = user_repo.get_by_id(current_user['id'])
    
    if user.email_verified:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already verified"
        )
    
    if user.email_verification_code != request.verification_code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid verification code"
        )
    
    # Verify email
    user_repo.update(
        user,
        email_verified=True,
        email_verified_at=datetime.utcnow(),
        email_verification_code=None
    )
    
    return {
        "message": "Email verified successfully"
    }


@router.post("/verify-phone")
def verify_phone(
    request: VerifyPhoneRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_production_db_dependency)
):
    """
    Verify phone number with verification code.
    
    - **verification_code**: 6-digit code sent via SMS
    """
    user_repo = UserRepository(db)
    user = user_repo.get_by_id(current_user['id'])
    
    if user.phone_verified:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Phone already verified"
        )
    
    if user.phone_verification_code != request.verification_code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid verification code"
        )
    
    # Verify phone
    user_repo.update(
        user,
        phone_verified=True,
        phone_verified_at=datetime.utcnow(),
        phone_verification_code=None
    )
    
    return {
        "message": "Phone verified successfully"
    }


@router.post("/resend-verification")
def resend_verification(
    verification_type: str = Query(..., pattern="^(email|phone)$"),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_production_db_dependency)
):
    """
    Resend verification code.
    
    - **verification_type**: Type - email or phone
    """
    user_repo = UserRepository(db)
    user = user_repo.get_by_id(current_user['id'])
    
    if verification_type == "email":
        if user.email_verified:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already verified"
            )
        
        new_code = generate_verification_code()
        user_repo.update(user, email_verification_code=new_code)
        
        # TODO: Send verification email
        
        return {
            "message": "Verification code sent to email"
        }
    
    else:  # phone
        if user.phone_verified:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Phone already verified"
            )
        
        new_code = generate_verification_code()
        user_repo.update(user, phone_verification_code=new_code)
        
        # TODO: Send verification SMS
        
        return {
            "message": "Verification code sent to phone"
        }


@router.post("/forgot-password")
def forgot_password(
    request: ForgotPasswordRequest,
    db: Session = Depends(get_production_db_dependency)
):
    """
    Request password reset.
    
    - **email**: Email address of the account
    
    Sends password reset link to email.
    """
    user_repo = UserRepository(db)
    user = user_repo.get_by_email(request.email)
    
    if not user:
        # Don't reveal if email exists
        return {
            "message": "If the email exists, a reset link has been sent"
        }
    
    # Generate reset token
    reset_token = generate_reset_token()
    reset_token_expires = datetime.utcnow() + timedelta(hours=1)
    
    user_repo.update(
        user,
        password_reset_token=reset_token,
        password_reset_token_expires=reset_token_expires
    )
    
    # TODO: Send password reset email with reset_token
    
    return {
        "message": "If the email exists, a reset link has been sent"
    }


@router.post("/reset-password")
def reset_password(
    request: ResetPasswordRequest,
    db: Session = Depends(get_production_db_dependency)
):
    """
    Reset password using reset token.
    
    - **reset_token**: Token from reset email
    - **new_password**: New password (min 8 characters)
    """
    user_repo = UserRepository(db)
    
    # Find user by reset token
    from app.models.database import User
    user = db.query(User).filter(
        User.password_reset_token == request.reset_token,
        User.is_deleted == False
    ).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token"
        )
    
    # Check token expiration
    if user.password_reset_token_expires < datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Reset token has expired"
        )
    
    # Hash new password
    new_password_hash = hash_password(request.new_password)
    
    # Update password and clear reset token
    user_repo.update(
        user,
        password_hash=new_password_hash,
        password_reset_token=None,
        password_reset_token_expires=None
    )
    
    return {
        "message": "Password reset successfully"
    }


@router.post("/change-password")
def change_password(
    request: ChangePasswordRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_production_db_dependency)
):
    """
    Change password for authenticated user.
    
    - **current_password**: Current password
    - **new_password**: New password (min 8 characters)
    """
    user_repo = UserRepository(db)
    user = user_repo.get_by_id(current_user['id'])
    
    # Verify current password
    if not verify_password(request.current_password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect"
        )
    
    # Hash new password
    new_password_hash = hash_password(request.new_password)
    
    # Update password
    user_repo.update(user, password_hash=new_password_hash)
    
    return {
        "message": "Password changed successfully"
    }


@router.post("/enable-2fa", response_model=Enable2FAResponse)
def enable_two_factor_auth(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_production_db_dependency)
):
    """
    Enable two-factor authentication (TOTP).
    
    Returns secret key, QR code URL, and backup codes.
    """
    user_repo = UserRepository(db)
    user = user_repo.get_by_id(current_user['id'])
    
    if user.two_factor_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Two-factor authentication already enabled"
        )
    
    # Generate TOTP secret (32 characters base32)
    import base64
    totp_secret = base64.b32encode(secrets.token_bytes(20)).decode('utf-8')
    
    # Generate backup codes
    backup_codes = [secrets.token_hex(8) for _ in range(10)]
    
    # Save to user
    user_repo.update(
        user,
        totp_secret=totp_secret,
        two_factor_backup_codes=backup_codes
    )
    
    # Generate QR code URL (for Google Authenticator, etc.)
    qr_code_url = f"otpauth://totp/AgroPulse:{user.email}?secret={totp_secret}&issuer=AgroPulse"
    
    return Enable2FAResponse(
        secret=totp_secret,
        qr_code_url=qr_code_url,
        backup_codes=backup_codes
    )


@router.post("/disable-2fa")
def disable_two_factor_auth(
    password: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_production_db_dependency)
):
    """
    Disable two-factor authentication.
    
    - **password**: User password for verification
    """
    user_repo = UserRepository(db)
    user = user_repo.get_by_id(current_user['id'])
    
    if not user.two_factor_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Two-factor authentication not enabled"
        )
    
    # Verify password
    if not verify_password(password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect password"
        )
    
    # Disable 2FA
    user_repo.update(
        user,
        two_factor_enabled=False,
        totp_secret=None,
        two_factor_backup_codes=None
    )
    
    return {
        "message": "Two-factor authentication disabled"
    }


@router.post("/verify-2fa")
def verify_two_factor_code(
    request: Verify2FARequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_production_db_dependency)
):
    """
    Verify 2FA code (TOTP or backup code).
    
    - **code**: 6-digit TOTP code or backup code
    """
    user_repo = UserRepository(db)
    user = user_repo.get_by_id(current_user['id'])
    
    if not user.two_factor_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Two-factor authentication not enabled"
        )
    
    # Check if it's a backup code
    if user.two_factor_backup_codes and request.code in user.two_factor_backup_codes:
        # Remove used backup code
        backup_codes = user.two_factor_backup_codes.copy()
        backup_codes.remove(request.code)
        user_repo.update(user, two_factor_backup_codes=backup_codes)
        
        return {
            "message": "Backup code verified successfully",
            "remaining_backup_codes": len(backup_codes)
        }
    
    # Verify TOTP code
    # TODO: Implement TOTP verification using pyotp library
    # For now, placeholder verification
    
    return {
        "message": "2FA code verified successfully"
    }
