"""
User Service Module

This service handles all business logic related to user management, including:
- User registration and onboarding
- Profile management
- Subscription handling
- Referral system
- Account verification
- User analytics
- Role management

The service encapsulates complex business rules and coordinates between
multiple repositories and external services.
"""

from sqlalchemy.orm import Session
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from decimal import Decimal
import secrets
import hashlib

from app.services.base import (
    BaseService,
    ValidationException,
    BusinessRuleException,
    ResourceNotFoundException,
    InsufficientPermissionsException
)
from app.repositories.user import UserRepository
from app.repositories.farm import FarmRepository
from app.models.database import User, SubscriptionTier


class UserService(BaseService):
    """
    Service class for user-related business logic.
    
    This service provides high-level operations for user management,
    implementing business rules and coordinating repository operations.
    """
    
    def __init__(self, db: Session):
        """
        Initialize the user service.
        
        Args:
            db: SQLAlchemy database session
        """
        super().__init__(db)
        self.user_repo = UserRepository(db)
        self.farm_repo = FarmRepository(db)
    
    # ========================================================================
    # User Registration and Onboarding
    # ========================================================================
    
    def register_user(
        self,
        username: str,
        email: str,
        password: str,
        full_name: str,
        phone: Optional[str] = None,
        county: Optional[str] = None,
        referral_code: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Register a new user with complete onboarding workflow.
        
        Business Rules:
        - Username must be unique
        - Email must be unique and valid format
        - Phone must be unique if provided
        - Password must meet security requirements
        - Referral code must be valid if provided
        - New users start with 'basic' subscription
        - Generate unique referral code for new user
        
        Args:
            username: Unique username
            email: User's email address
            password: Plain text password (will be hashed)
            full_name: User's full name
            phone: Phone number (optional)
            county: County/location (optional)
            referral_code: Referral code from another user (optional)
            
        Returns:
            Dictionary with user info and onboarding details
            
        Raises:
            ValidationException: If validation fails
            BusinessRuleException: If business rules are violated
        """
        with self.transaction():
            # Validate inputs
            self.validate_username(username)
            self.validate_email_format(email)
            self.validate_password_strength(password)
            
            if phone:
                self.validate_phone_format(phone)
            
            # Check uniqueness
            if self.user_repo.get_by_username(username):
                raise ValidationException("Username already exists", field="username")
            
            if self.user_repo.get_by_email(email):
                raise ValidationException("Email already exists", field="email")
            
            if phone and self.user_repo.get_by_phone(phone):
                raise ValidationException("Phone number already exists", field="phone")
            
            # Process referral code
            referrer_id = None
            if referral_code:
                referrer = self.user_repo.get_by_referral_code(referral_code)
                if not referrer:
                    raise ValidationException("Invalid referral code", field="referral_code")
                referrer_id = referrer.id
            
            # Generate unique referral code for new user
            new_referral_code = self.generate_referral_code(username)
            
            # Create user
            user_data = {
                "username": username,
                "email": email,
                "password_hash": password,  # Repository will hash it
                "full_name": full_name,
                "phone": phone,
                "county": county,
                "role": "user",
                "subscription_tier": SubscriptionTier.BASIC,
                "referral_code": new_referral_code,
                "referred_by_id": referrer_id,
                "is_active": True,
                "email_verified": False,
                "phone_verified": False
            }
            
            user = self.user_repo.create(user_data)
            
            # Update referrer's referral count
            if referrer_id:
                self.increment_referral_count(referrer_id)
            
            # Log activity
            self.log_activity("user_registered", user.id, {
                "username": username,
                "email": email,
                "referred_by": referrer_id
            })
            
            return {
                "user_id": user.id,
                "username": user.username,
                "email": user.email,
                "referral_code": user.referral_code,
                "subscription_tier": user.subscription_tier.value,
                "referred_by": referrer_id,
                "message": "User registered successfully"
            }
    
    def validate_username(self, username: str):
        """Validate username format and length."""
        self.validate_string_length(username, 3, 50, "username")
        
        import re
        if not re.match(r'^[a-zA-Z0-9_]+$', username):
            raise ValidationException(
                "Username can only contain letters, numbers, and underscores",
                field="username"
            )
    
    def validate_password_strength(self, password: str):
        """
        Validate password meets security requirements.
        
        Requirements:
        - At least 8 characters
        - Contains at least one uppercase letter
        - Contains at least one lowercase letter
        - Contains at least one number
        """
        if len(password) < 8:
            raise ValidationException(
                "Password must be at least 8 characters",
                field="password"
            )
        
        import re
        if not re.search(r'[A-Z]', password):
            raise ValidationException(
                "Password must contain at least one uppercase letter",
                field="password"
            )
        
        if not re.search(r'[a-z]', password):
            raise ValidationException(
                "Password must contain at least one lowercase letter",
                field="password"
            )
        
        if not re.search(r'\d', password):
            raise ValidationException(
                "Password must contain at least one number",
                field="password"
            )
    
    def generate_referral_code(self, username: str) -> str:
        """
        Generate a unique referral code based on username and random string.
        
        Args:
            username: User's username
            
        Returns:
            Unique referral code
        """
        random_part = secrets.token_hex(4).upper()
        username_part = username[:4].upper()
        return f"{username_part}{random_part}"
    
    def increment_referral_count(self, user_id: int):
        """Increment user's total referrals count."""
        user = self.user_repo.get_by_id(user_id)
        if user:
            current_count = user.total_referrals or 0
            self.user_repo.update(user, total_referrals=current_count + 1)
    
    # ========================================================================
    # Profile Management
    # ========================================================================
    
    def update_profile(
        self,
        user_id: int,
        full_name: Optional[str] = None,
        phone: Optional[str] = None,
        county: Optional[str] = None,
        bio: Optional[str] = None,
        avatar_url: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Update user profile information.
        
        Args:
            user_id: ID of user to update
            full_name: New full name (optional)
            phone: New phone number (optional)
            county: New county (optional)
            bio: User biography (optional)
            avatar_url: Avatar image URL (optional)
            
        Returns:
            Updated user information
            
        Raises:
            ResourceNotFoundException: If user not found
            ValidationException: If validation fails
        """
        user = self.check_resource_exists(
            self.user_repo.get_by_id(user_id),
            "User",
            user_id
        )
        
        update_data = {}
        
        if full_name is not None:
            self.validate_string_length(full_name, 2, 100, "full_name")
            update_data["full_name"] = full_name
        
        if phone is not None:
            self.validate_phone_format(phone)
            # Check phone uniqueness
            existing_user = self.user_repo.get_by_phone(phone)
            if existing_user and existing_user.id != user_id:
                raise ValidationException("Phone number already in use", field="phone")
            update_data["phone"] = phone
            update_data["phone_verified"] = False  # Reset verification
        
        if county is not None:
            update_data["county"] = county
        
        if bio is not None:
            self.validate_string_length(bio, 0, 500, "bio")
            update_data["bio"] = bio
        
        if avatar_url is not None:
            update_data["avatar_url"] = avatar_url
        
        updated_user = self.user_repo.update(user, **update_data)
        
        self.log_activity("profile_updated", user_id, update_data)
        
        return self._format_user_response(updated_user)
    
    def change_password(
        self,
        user_id: int,
        current_password: str,
        new_password: str
    ) -> Dict[str, str]:
        """
        Change user's password.
        
        Args:
            user_id: ID of user
            current_password: Current password
            new_password: New password
            
        Returns:
            Success message
            
        Raises:
            ResourceNotFoundException: If user not found
            ValidationException: If current password is wrong or new password is weak
        """
        user = self.check_resource_exists(
            self.user_repo.get_by_id(user_id),
            "User",
            user_id
        )
        
        # Verify current password
        if not self.user_repo.verify_password(user, current_password):
            raise ValidationException("Current password is incorrect", field="current_password")
        
        # Validate new password
        self.validate_password_strength(new_password)
        
        # Check password is different
        if current_password == new_password:
            raise ValidationException(
                "New password must be different from current password",
                field="new_password"
            )
        
        # Update password
        self.user_repo.update_password(user, new_password)
        
        self.log_activity("password_changed", user_id)
        
        return {"message": "Password changed successfully"}
    
    # ========================================================================
    # Subscription Management
    # ========================================================================
    
    def upgrade_subscription(
        self,
        user_id: int,
        new_tier: str,
        payment_reference: str
    ) -> Dict[str, Any]:
        """
        Upgrade user's subscription tier.
        
        Business Rules:
        - Can only upgrade to higher tiers
        - Payment reference must be provided
        - Subscription starts immediately and lasts 30 days
        - Premium features are activated
        
        Args:
            user_id: ID of user
            new_tier: New subscription tier (premium, enterprise)
            payment_reference: Payment transaction reference
            
        Returns:
            Updated subscription information
            
        Raises:
            ResourceNotFoundException: If user not found
            ValidationException: If tier is invalid
            BusinessRuleException: If business rules are violated
        """
        user = self.check_resource_exists(
            self.user_repo.get_by_id(user_id),
            "User",
            user_id
        )
        
        # Validate tier
        valid_tiers = [tier.value for tier in SubscriptionTier]
        if new_tier not in valid_tiers:
            raise ValidationException(
                f"Invalid subscription tier. Must be one of: {', '.join(valid_tiers)}",
                field="new_tier"
            )
        
        new_tier_enum = SubscriptionTier(new_tier)
        
        # Check upgrade is valid
        tier_hierarchy = {
            SubscriptionTier.BASIC: 1,
            SubscriptionTier.PREMIUM: 2,
            SubscriptionTier.ENTERPRISE: 3
        }
        
        current_level = tier_hierarchy[user.subscription_tier]
        new_level = tier_hierarchy[new_tier_enum]
        
        if new_level <= current_level:
            raise BusinessRuleException(
                "Can only upgrade to a higher tier",
                rule="subscription_upgrade",
                details={
                    "current_tier": user.subscription_tier.value,
                    "requested_tier": new_tier
                }
            )
        
        # Set subscription period (30 days)
        subscription_start = datetime.utcnow()
        subscription_end = subscription_start + timedelta(days=30)
        
        # Update subscription
        updated_user = self.user_repo.update(
            user,
            subscription_tier=new_tier_enum,
            subscription_start=subscription_start,
            subscription_end=subscription_end
        )
        
        self.log_activity("subscription_upgraded", user_id, {
            "from_tier": user.subscription_tier.value,
            "to_tier": new_tier,
            "payment_reference": payment_reference,
            "expires_at": subscription_end.isoformat()
        })
        
        return {
            "user_id": user_id,
            "subscription_tier": updated_user.subscription_tier.value,
            "subscription_start": subscription_start.isoformat(),
            "subscription_end": subscription_end.isoformat(),
            "days_remaining": 30,
            "message": f"Subscription upgraded to {new_tier} successfully"
        }
    
    def check_subscription_active(self, user_id: int) -> bool:
        """
        Check if user's subscription is still active.
        
        Args:
            user_id: ID of user
            
        Returns:
            True if subscription is active, False otherwise
        """
        user = self.user_repo.get_by_id(user_id)
        if not user:
            return False
        
        if user.subscription_tier == SubscriptionTier.BASIC:
            return True  # Basic is always active
        
        if not user.subscription_end:
            return False
        
        return datetime.utcnow() < user.subscription_end
    
    def get_subscription_days_remaining(self, user_id: int) -> Optional[int]:
        """
        Get number of days remaining in user's subscription.
        
        Args:
            user_id: ID of user
            
        Returns:
            Days remaining, or None if basic tier or expired
        """
        user = self.user_repo.get_by_id(user_id)
        if not user or user.subscription_tier == SubscriptionTier.BASIC:
            return None
        
        if not user.subscription_end:
            return None
        
        days_remaining = self.calculate_days_between(datetime.utcnow(), user.subscription_end)
        return max(0, days_remaining)
    
    # ========================================================================
    # Referral System
    # ========================================================================
    
    def get_referral_stats(self, user_id: int) -> Dict[str, Any]:
        """
        Get user's referral statistics.
        
        Args:
            user_id: ID of user
            
        Returns:
            Dictionary with referral statistics
            
        Raises:
            ResourceNotFoundException: If user not found
        """
        user = self.check_resource_exists(
            self.user_repo.get_by_id(user_id),
            "User",
            user_id
        )
        
        # Get referred users
        referred_users = self.user_repo.get_by_referrer(user_id)
        
        # Calculate statistics
        total_referrals = len(referred_users)
        active_referrals = len([u for u in referred_users if u.is_active])
        premium_referrals = len([
            u for u in referred_users
            if u.subscription_tier != SubscriptionTier.BASIC
        ])
        
        return {
            "user_id": user_id,
            "referral_code": user.referral_code,
            "total_referrals": total_referrals,
            "active_referrals": active_referrals,
            "premium_referrals": premium_referrals,
            "referral_rate": self.calculate_percentage(active_referrals, total_referrals),
            "referred_users": [
                {
                    "id": u.id,
                    "username": u.username,
                    "full_name": u.full_name,
                    "subscription_tier": u.subscription_tier.value,
                    "created_at": u.created_at.isoformat()
                }
                for u in referred_users
            ]
        }
    
    def calculate_referral_rewards(self, user_id: int) -> Dict[str, Any]:
        """
        Calculate referral rewards for a user.
        
        Reward Structure:
        - 100 points per active referral
        - 500 bonus points per premium referral
        - 1000 bonus for 10+ referrals
        
        Args:
            user_id: ID of user
            
        Returns:
            Reward calculation details
        """
        stats = self.get_referral_stats(user_id)
        
        base_points = stats["active_referrals"] * 100
        premium_bonus = stats["premium_referrals"] * 500
        milestone_bonus = 1000 if stats["total_referrals"] >= 10 else 0
        
        total_points = base_points + premium_bonus + milestone_bonus
        
        return {
            "user_id": user_id,
            "base_points": base_points,
            "premium_bonus": premium_bonus,
            "milestone_bonus": milestone_bonus,
            "total_points": total_points,
            "next_milestone": 10 if stats["total_referrals"] < 10 else 25
        }
    
    # ========================================================================
    # Account Verification
    # ========================================================================
    
    def verify_email(self, user_id: int) -> Dict[str, str]:
        """
        Mark user's email as verified.
        
        Args:
            user_id: ID of user
            
        Returns:
            Success message
            
        Raises:
            ResourceNotFoundException: If user not found
        """
        user = self.check_resource_exists(
            self.user_repo.get_by_id(user_id),
            "User",
            user_id
        )
        
        if user.email_verified:
            return {"message": "Email already verified"}
        
        self.user_repo.update(user, email_verified=True)
        
        self.log_activity("email_verified", user_id)
        
        return {"message": "Email verified successfully"}
    
    def verify_phone(self, user_id: int) -> Dict[str, str]:
        """
        Mark user's phone as verified.
        
        Args:
            user_id: ID of user
            
        Returns:
            Success message
            
        Raises:
            ResourceNotFoundException: If user not found
        """
        user = self.check_resource_exists(
            self.user_repo.get_by_id(user_id),
            "User",
            user_id
        )
        
        if user.phone_verified:
            return {"message": "Phone already verified"}
        
        self.user_repo.update(user, phone_verified=True)
        
        self.log_activity("phone_verified", user_id)
        
        return {"message": "Phone verified successfully"}
    
    # ========================================================================
    # User Analytics
    # ========================================================================
    
    def get_user_analytics(self, user_id: int) -> Dict[str, Any]:
        """
        Get comprehensive analytics for a user.
        
        Args:
            user_id: ID of user
            
        Returns:
            Dictionary with user analytics
            
        Raises:
            ResourceNotFoundException: If user not found
        """
        user = self.check_resource_exists(
            self.user_repo.get_by_id(user_id),
            "User",
            user_id
        )
        
        # Get related data
        farms = self.farm_repo.get_by_owner(user_id)
        referral_stats = self.get_referral_stats(user_id)
        
        # Calculate account age
        account_age_days = self.calculate_days_between(user.created_at, datetime.utcnow())
        
        # Calculate subscription status
        subscription_active = self.check_subscription_active(user_id)
        days_remaining = self.get_subscription_days_remaining(user_id)
        
        return {
            "user_id": user_id,
            "username": user.username,
            "account_age_days": account_age_days,
            "subscription": {
                "tier": user.subscription_tier.value,
                "active": subscription_active,
                "days_remaining": days_remaining,
                "start_date": user.subscription_start.isoformat() if user.subscription_start else None,
                "end_date": user.subscription_end.isoformat() if user.subscription_end else None
            },
            "verification": {
                "email_verified": user.email_verified,
                "phone_verified": user.phone_verified
            },
            "farms": {
                "total_farms": len(farms),
                "verified_farms": len([f for f in farms if f.verified]),
                "total_farm_size": sum(f.size for f in farms)
            },
            "referrals": {
                "total": referral_stats["total_referrals"],
                "active": referral_stats["active_referrals"],
                "premium": referral_stats["premium_referrals"]
            },
            "activity": {
                "last_login": user.last_login.isoformat() if user.last_login else None,
                "is_active": user.is_active
            }
        }
    
    # ========================================================================
    # Role Management
    # ========================================================================
    
    def update_user_role(
        self,
        user_id: int,
        new_role: str,
        updated_by_id: int
    ) -> Dict[str, Any]:
        """
        Update user's role (admin only operation).
        
        Args:
            user_id: ID of user to update
            new_role: New role (user, agronomist, admin)
            updated_by_id: ID of admin performing the update
            
        Returns:
            Updated user information
            
        Raises:
            ResourceNotFoundException: If user not found
            ValidationException: If role is invalid
            InsufficientPermissionsException: If updater is not admin
        """
        # Check updater is admin
        updater = self.user_repo.get_by_id(updated_by_id)
        self.check_permission(updater.role, "admin")
        
        user = self.check_resource_exists(
            self.user_repo.get_by_id(user_id),
            "User",
            user_id
        )
        
        # Validate role
        valid_roles = ["user", "agronomist", "admin"]
        if new_role not in valid_roles:
            raise ValidationException(
                f"Invalid role. Must be one of: {', '.join(valid_roles)}",
                field="new_role"
            )
        
        # Update role
        updated_user = self.user_repo.update(user, role=new_role)
        
        self.log_activity("role_updated", user_id, {
            "from_role": user.role,
            "to_role": new_role,
            "updated_by": updated_by_id
        })
        
        return self._format_user_response(updated_user)
    
    def deactivate_user(self, user_id: int, reason: str) -> Dict[str, str]:
        """
        Deactivate a user account.
        
        Args:
            user_id: ID of user to deactivate
            reason: Reason for deactivation
            
        Returns:
            Success message
            
        Raises:
            ResourceNotFoundException: If user not found
        """
        user = self.check_resource_exists(
            self.user_repo.get_by_id(user_id),
            "User",
            user_id
        )
        
        self.user_repo.update(user, is_active=False)
        
        self.log_activity("user_deactivated", user_id, {"reason": reason})
        
        return {"message": "User deactivated successfully"}
    
    def reactivate_user(self, user_id: int) -> Dict[str, str]:
        """
        Reactivate a deactivated user account.
        
        Args:
            user_id: ID of user to reactivate
            
        Returns:
            Success message
            
        Raises:
            ResourceNotFoundException: If user not found
        """
        user = self.check_resource_exists(
            self.user_repo.get_by_id(user_id),
            "User",
            user_id
        )
        
        self.user_repo.update(user, is_active=True)
        
        self.log_activity("user_reactivated", user_id)
        
        return {"message": "User reactivated successfully"}
    
    # ========================================================================
    # Helper Methods
    # ========================================================================
    
    def _format_user_response(self, user: User) -> Dict[str, Any]:
        """Format user object as API response dictionary."""
        return {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "full_name": user.full_name,
            "phone": user.phone,
            "county": user.county,
            "role": user.role,
            "subscription_tier": user.subscription_tier.value,
            "is_active": user.is_active,
            "email_verified": user.email_verified,
            "phone_verified": user.phone_verified,
            "avatar_url": user.avatar_url,
            "bio": user.bio,
            "referral_code": user.referral_code,
            "total_referrals": user.total_referrals,
            "created_at": user.created_at.isoformat(),
            "last_login": user.last_login.isoformat() if user.last_login else None
        }
