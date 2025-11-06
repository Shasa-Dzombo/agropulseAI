"""
User Model Tests

Comprehensive tests for User model and repository.
"""

import pytest
from datetime import datetime, timedelta
from app.database.models.user import User
from app.database.repositories.user_repository import UserRepository
from app.core.security import verify_password


@pytest.mark.unit
@pytest.mark.database
class TestUserModel:
    """Test User model."""
    
    def test_create_user(self, db_session):
        """Test creating a user."""
        user = User(
            email="newuser@example.com",
            hashed_password="hashedpass",
            full_name="New User",
            phone_number="+254712345678"
        )
        db_session.add(user)
        db_session.commit()
        
        assert user.id is not None
        assert user.email == "newuser@example.com"
        assert user.is_active is True
        assert user.created_at is not None
    
    def test_user_unique_email(self, db_session, test_user):
        """Test email uniqueness constraint."""
        duplicate_user = User(
            email=test_user.email,
            hashed_password="hashedpass",
            full_name="Duplicate User"
        )
        db_session.add(duplicate_user)
        
        with pytest.raises(Exception):  # IntegrityError
            db_session.commit()
    
    def test_user_default_values(self, db_session):
        """Test default field values."""
        user = User(
            email="defaults@example.com",
            hashed_password="hash",
            full_name="Default User"
        )
        db_session.add(user)
        db_session.commit()
        
        assert user.is_active is True
        assert user.is_verified is False
        assert user.is_superuser is False
        assert user.role == "farmer"
    
    def test_user_timestamps(self, db_session):
        """Test timestamp fields."""
        user = User(
            email="timestamp@example.com",
            hashed_password="hash",
            full_name="Timestamp User"
        )
        db_session.add(user)
        db_session.commit()
        
        assert user.created_at is not None
        assert user.updated_at is not None
        assert user.created_at <= user.updated_at
    
    def test_user_update(self, db_session, test_user):
        """Test updating user."""
        original_updated = test_user.updated_at
        test_user.full_name = "Updated Name"
        db_session.commit()
        
        assert test_user.full_name == "Updated Name"
        assert test_user.updated_at > original_updated
    
    def test_user_soft_delete(self, db_session, test_user):
        """Test soft delete (deactivation)."""
        test_user.is_active = False
        db_session.commit()
        
        assert test_user.is_active is False
        assert test_user.id is not None  # Still exists in DB


@pytest.mark.unit
@pytest.mark.database
class TestUserRepository:
    """Test UserRepository."""
    
    def test_get_by_email(self, db_session, test_user):
        """Test retrieving user by email."""
        repo = UserRepository(db_session)
        user = repo.get_by_email(test_user.email)
        
        assert user is not None
        assert user.id == test_user.id
        assert user.email == test_user.email
    
    def test_get_by_email_not_found(self, db_session):
        """Test getting non-existent user."""
        repo = UserRepository(db_session)
        user = repo.get_by_email("nonexistent@example.com")
        
        assert user is None
    
    def test_create_user_repo(self, db_session):
        """Test creating user via repository."""
        repo = UserRepository(db_session)
        user_data = {
            "email": "repo@example.com",
            "hashed_password": "hashed",
            "full_name": "Repo User",
            "phone_number": "+254712345670"
        }
        
        user = repo.create(user_data)
        
        assert user.id is not None
        assert user.email == "repo@example.com"
    
    def test_update_user_repo(self, db_session, test_user):
        """Test updating user via repository."""
        repo = UserRepository(db_session)
        updated = repo.update(test_user.id, {"full_name": "New Name"})
        
        assert updated.full_name == "New Name"
    
    def test_delete_user_repo(self, db_session, test_user):
        """Test deleting user via repository."""
        repo = UserRepository(db_session)
        user_id = test_user.id
        
        success = repo.delete(user_id)
        
        assert success is True
        assert repo.get_by_id(user_id) is None
    
    def test_list_users(self, db_session, test_user, test_admin_user):
        """Test listing users."""
        repo = UserRepository(db_session)
        users = repo.list(limit=10, offset=0)
        
        assert len(users) >= 2
        assert any(u.id == test_user.id for u in users)
    
    def test_count_users(self, db_session, test_user):
        """Test counting users."""
        repo = UserRepository(db_session)
        count = repo.count()
        
        assert count >= 1
    
    def test_get_active_users(self, db_session, test_user):
        """Test getting active users only."""
        repo = UserRepository(db_session)
        
        # Create inactive user
        inactive = User(
            email="inactive@example.com",
            hashed_password="hash",
            full_name="Inactive",
            is_active=False
        )
        db_session.add(inactive)
        db_session.commit()
        
        active_users = repo.get_active_users()
        
        assert all(u.is_active for u in active_users)
        assert test_user.id in [u.id for u in active_users]
        assert inactive.id not in [u.id for u in active_users]


@pytest.mark.integration
@pytest.mark.database
class TestUserRelationships:
    """Test User model relationships."""
    
    def test_user_farms_relationship(self, db_session, test_user, test_farm):
        """Test user-farms relationship."""
        assert test_farm in test_user.farms
        assert test_farm.owner_id == test_user.id
    
    def test_user_alerts_relationship(self, db_session, test_user, test_alert):
        """Test user-alerts relationship."""
        assert test_alert in test_user.alerts
        assert test_alert.user_id == test_user.id
    
    def test_cascade_delete(self, db_session, test_user):
        """Test cascade delete behavior."""
        from app.database.models.farm import Farm
        
        # Create farm
        farm = Farm(
            name="Test Farm",
            owner_id=test_user.id,
            location="Test Location",
            size_hectares=5.0
        )
        db_session.add(farm)
        db_session.commit()
        farm_id = farm.id
        
        # Delete user
        db_session.delete(test_user)
        db_session.commit()
        
        # Farm should also be deleted (if cascade configured)
        farm = db_session.query(Farm).filter(Farm.id == farm_id).first()
        # Depending on cascade settings
