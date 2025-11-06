"""
🧑‍🌾 User Repository

Specialized repository for User model with authentication, profile management,
and referral tracking.

Features:
- User authentication and verification
- Profile management and completion tracking
- Subscription management
- Referral system
- Activity tracking
- Security features (account locking, 2FA)

Author: AgroPulse Engineering Team
"""

from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_

from app.models.database import User
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    """Repository for User model with authentication and profile management."""
    
    def __init__(self, db: Session):
        """
        Initialize user repository.
        
        Args:
            db: Database session
        """
        super().__init__(User, db)
    
    # ========================================================================
    # AUTHENTICATION METHODS
    # ========================================================================
    
    def get_by_email(self, email: str) -> Optional[User]:
        """
        Get user by email address.
        
        Args:
            email: User's email address
            
        Returns:
            User if found, None otherwise
        """
        return self.get_by_field('email', email)
    
    def get_by_phone(self, phone_number: str) -> Optional[User]:
        """
        Get user by phone number.
        
        Args:
            phone_number: User's phone number
            
        Returns:
            User if found, None otherwise
        """
        return self.get_by_field('phone_number', phone_number)
    
    def get_by_national_id(self, national_id: str) -> Optional[User]:
        """
        Get user by national ID.
        
        Args:
            national_id: User's national ID number
            
        Returns:
            User if found, None otherwise
        """
        return self.get_by_field('national_id', national_id)
    
    def authenticate(
        self, 
        email: str, 
        password_hash: str
    ) -> Optional[User]:
        """
        Authenticate user by email and password.
        
        Args:
            email: User's email
            password_hash: Hashed password to verify
            
        Returns:
            User if authenticated, None otherwise
        """
        user = self.get_by_email(email)
        if not user:
            return None
        
        # Check if account is locked
        if user.account_locked_until:
            if user.account_locked_until > datetime.utcnow():
                return None
            else:
                # Unlock account
                user.account_locked_until = None
                user.failed_login_attempts = 0
                self.db.commit()
        
        # Verify password (you'd use bcrypt.verify here)
        if user.password_hash == password_hash:
            # Update login tracking
            user.last_login_at = datetime.utcnow()
            user.login_count += 1
            user.failed_login_attempts = 0
            self.db.commit()
            return user
        else:
            # Track failed attempt
            user.failed_login_attempts += 1
            user.last_failed_login_at = datetime.utcnow()
            
            # Lock account after 5 failed attempts
            if user.failed_login_attempts >= 5:
                user.account_locked_until = datetime.utcnow() + timedelta(hours=1)
            
            self.db.commit()
            return None
    
    def verify_email(self, user_id: int) -> bool:
        """
        Mark user's email as verified.
        
        Args:
            user_id: User ID
            
        Returns:
            True if successful, False otherwise
        """
        user = self.get_by_id(user_id)
        if not user:
            return False
        
        user.email_verified = True
        user.is_verified = user.email_verified and user.phone_verified
        self.db.commit()
        return True
    
    def verify_phone(self, user_id: int) -> bool:
        """
        Mark user's phone as verified.
        
        Args:
            user_id: User ID
            
        Returns:
            True if successful, False otherwise
        """
        user = self.get_by_id(user_id)
        if not user:
            return False
        
        user.phone_verified = True
        user.is_verified = user.email_verified and user.phone_verified
        self.db.commit()
        return True
    
    def enable_2fa(
        self, 
        user_id: int, 
        secret: str
    ) -> bool:
        """
        Enable two-factor authentication for user.
        
        Args:
            user_id: User ID
            secret: TOTP secret
            
        Returns:
            True if successful, False otherwise
        """
        user = self.get_by_id(user_id)
        if not user:
            return False
        
        user.two_factor_secret = secret
        user.two_factor_enabled = True
        self.db.commit()
        return True
    
    def disable_2fa(self, user_id: int) -> bool:
        """
        Disable two-factor authentication for user.
        
        Args:
            user_id: User ID
            
        Returns:
            True if successful, False otherwise
        """
        user = self.get_by_id(user_id)
        if not user:
            return False
        
        user.two_factor_secret = None
        user.two_factor_enabled = False
        self.db.commit()
        return True
    
    # ========================================================================
    # PROFILE MANAGEMENT
    # ========================================================================
    
    def update_profile(
        self, 
        user_id: int, 
        **kwargs
    ) -> Optional[User]:
        """
        Update user profile fields.
        
        Args:
            user_id: User ID
            **kwargs: Fields to update
            
        Returns:
            Updated user if successful, None otherwise
        """
        user = self.get_by_id(user_id)
        if not user:
            return None
        
        # Update allowed fields
        allowed_fields = [
            'first_name', 'last_name', 'middle_name', 'display_name',
            'date_of_birth', 'gender', 'national_id',
            'alternate_phone', 'whatsapp_number',
            'address_line1', 'address_line2', 'city', 'county',
            'postal_code', 'country',
            'latitude', 'longitude', 'altitude',
            'avatar_url', 'cover_photo_url',
            'language_preference', 'timezone', 'theme_preference'
        ]
        
        for field, value in kwargs.items():
            if field in allowed_fields and hasattr(user, field):
                setattr(user, field, value)
        
        # Recalculate profile completion
        user.profile_completion_percentage = self._calculate_profile_completion(user)
        
        self.db.commit()
        self.db.refresh(user)
        return user
    
    def _calculate_profile_completion(self, user: User) -> float:
        """
        Calculate profile completion percentage.
        
        Args:
            user: User object
            
        Returns:
            Completion percentage (0-100)
        """
        required_fields = [
            'first_name', 'last_name', 'email', 'phone_number',
            'date_of_birth', 'gender', 'county',
            'avatar_url'
        ]
        
        completed = sum(1 for field in required_fields if getattr(user, field, None))
        return (completed / len(required_fields)) * 100
    
    def complete_onboarding(
        self, 
        user_id: int
    ) -> Optional[User]:
        """
        Mark user onboarding as complete.
        
        Args:
            user_id: User ID
            
        Returns:
            Updated user if successful, None otherwise
        """
        user = self.get_by_id(user_id)
        if not user:
            return None
        
        user.onboarding_completed = True
        user.onboarding_step = 0
        self.db.commit()
        self.db.refresh(user)
        return user
    
    # ========================================================================
    # SUBSCRIPTION MANAGEMENT
    # ========================================================================
    
    def update_subscription(
        self,
        user_id: int,
        tier: str,
        expires_at: datetime,
        diagnoses_remaining: int = None
    ) -> Optional[User]:
        """
        Update user subscription.
        
        Args:
            user_id: User ID
            tier: Subscription tier (free, basic, premium, enterprise)
            expires_at: Subscription expiry date
            diagnoses_remaining: Number of diagnoses remaining
            
        Returns:
            Updated user if successful, None otherwise
        """
        user = self.get_by_id(user_id)
        if not user:
            return None
        
        user.subscription_tier = tier
        user.subscription_expires_at = expires_at
        
        if diagnoses_remaining is not None:
            user.diagnoses_remaining = diagnoses_remaining
        
        self.db.commit()
        self.db.refresh(user)
        return user
    
    def decrement_diagnoses(
        self, 
        user_id: int
    ) -> Optional[User]:
        """
        Decrement user's remaining diagnoses count.
        
        Args:
            user_id: User ID
            
        Returns:
            Updated user if successful, None otherwise
        """
        user = self.get_by_id(user_id)
        if not user:
            return None
        
        if user.diagnoses_remaining > 0:
            user.diagnoses_remaining -= 1
            self.db.commit()
            self.db.refresh(user)
        
        return user
    
    def get_expiring_subscriptions(
        self, 
        days: int = 7
    ) -> List[User]:
        """
        Get users with expiring subscriptions.
        
        Args:
            days: Number of days until expiry
            
        Returns:
            List of users with expiring subscriptions
        """
        expiry_date = datetime.utcnow() + timedelta(days=days)
        return self.db.query(User).filter(
            and_(
                User.subscription_expires_at.isnot(None),
                User.subscription_expires_at <= expiry_date,
                User.subscription_expires_at > datetime.utcnow(),
                User.is_deleted == False
            )
        ).all()
    
    # ========================================================================
    # REFERRAL SYSTEM
    # ========================================================================
    
    def get_by_referral_code(
        self, 
        referral_code: str
    ) -> Optional[User]:
        """
        Get user by referral code.
        
        Args:
            referral_code: Referral code
            
        Returns:
            User if found, None otherwise
        """
        return self.get_by_field('referral_code', referral_code)
    
    def get_referrals(
        self, 
        user_id: int
    ) -> List[User]:
        """
        Get all users referred by a user.
        
        Args:
            user_id: Referrer's user ID
            
        Returns:
            List of referred users
        """
        return self.db.query(User).filter(
            User.referred_by_id == user_id
        ).all()
    
    def increment_referral_count(
        self, 
        user_id: int
    ) -> Optional[User]:
        """
        Increment user's referral count.
        
        Args:
            user_id: User ID
            
        Returns:
            Updated user if successful, None otherwise
        """
        user = self.get_by_id(user_id)
        if not user:
            return None
        
        user.referral_count += 1
        self.db.commit()
        self.db.refresh(user)
        return user
    
    def add_referral_earnings(
        self,
        user_id: int,
        amount: float
    ) -> Optional[User]:
        """
        Add to user's referral earnings.
        
        Args:
            user_id: User ID
            amount: Amount to add
            
        Returns:
            Updated user if successful, None otherwise
        """
        user = self.get_by_id(user_id)
        if not user:
            return None
        
        user.referral_earnings_ksh += amount
        self.db.commit()
        self.db.refresh(user)
        return user
    
    # ========================================================================
    # USER QUERIES
    # ========================================================================
    
    def get_by_role(
        self, 
        role: str,
        skip: int = 0,
        limit: int = 100
    ) -> List[User]:
        """
        Get users by role.
        
        Args:
            role: User role (farmer, agronomist, admin, etc.)
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List of users with specified role
        """
        return self.filter({'role': role}, skip=skip, limit=limit)
    
    def get_by_county(
        self,
        county: str,
        skip: int = 0,
        limit: int = 100
    ) -> List[User]:
        """
        Get users by county.
        
        Args:
            county: County name
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List of users in specified county
        """
        return self.filter({'county': county}, skip=skip, limit=limit)
    
    def get_active_farmers(
        self,
        skip: int = 0,
        limit: int = 100
    ) -> List[User]:
        """
        Get active farmer users.
        
        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List of active farmers
        """
        return self.filter({
            'role': 'farmer',
            'status': 'active',
            'is_deleted': False
        }, skip=skip, limit=limit)
    
    def get_verified_users(
        self,
        skip: int = 0,
        limit: int = 100
    ) -> List[User]:
        """
        Get verified users.
        
        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List of verified users
        """
        return self.filter({
            'is_verified': True,
            'is_deleted': False
        }, skip=skip, limit=limit)
    
    def get_premium_users(
        self,
        skip: int = 0,
        limit: int = 100
    ) -> List[User]:
        """
        Get premium subscription users.
        
        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List of premium users
        """
        return self.db.query(User).filter(
            and_(
                User.subscription_tier.in_(['premium', 'enterprise']),
                User.subscription_expires_at > datetime.utcnow(),
                User.is_deleted == False
            )
        ).offset(skip).limit(limit).all()
    
    def search_users(
        self,
        search_term: str,
        skip: int = 0,
        limit: int = 50
    ) -> List[User]:
        """
        Search users by name, email, or phone.
        
        Args:
            search_term: Search term
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List of matching users
        """
        return self.search(
            search_term,
            ['first_name', 'last_name', 'email', 'phone_number'],
            skip=skip,
            limit=limit
        )
    
    # ========================================================================
    # STATISTICS & ANALYTICS
    # ========================================================================
    
    def get_user_statistics(self) -> Dict[str, Any]:
        """
        Get user statistics.
        
        Returns:
            Dictionary with user statistics
        """
        total = self.count()
        active = self.count({'status': 'active'})
        verified = self.count({'is_verified': True})
        farmers = self.count({'role': 'farmer'})
        agronomists = self.count({'role': 'agronomist'})
        
        return {
            'total_users': total,
            'active_users': active,
            'verified_users': verified,
            'farmers': farmers,
            'agronomists': agronomists,
            'pending_verification': total - verified
        }
    
    def get_subscription_breakdown(self) -> Dict[str, int]:
        """
        Get subscription tier breakdown.
        
        Returns:
            Dictionary with subscription counts
        """
        result = self.db.query(
            User.subscription_tier,
            func.count(User.id)
        ).filter(
            User.is_deleted == False
        ).group_by(User.subscription_tier).all()
        
        return {tier: count for tier, count in result}
    
    def get_top_referrers(self, limit: int = 10) -> List[User]:
        """
        Get top users by referral count.
        
        Args:
            limit: Number of users to return
            
        Returns:
            List of top referrers
        """
        return self.db.query(User).filter(
            User.is_deleted == False
        ).order_by(
            User.referral_count.desc()
        ).limit(limit).all()
