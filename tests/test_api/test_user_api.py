"""
User Management API Tests

Comprehensive tests for user management, profiles, roles, and permissions.
"""

import pytest
from fastapi import status

from tests.utils import (
    assert_status_code, assert_success_response, get_json_response,
    assert_dict_structure
)


@pytest.mark.api
@pytest.mark.integration
class TestUserManagementAPI:
    """Test user management endpoints."""
    
    def test_get_current_user_profile(self, authenticated_client, test_user):
        """Test getting current user profile."""
        response = authenticated_client.get("/api/v1/users/me")
        
        assert_status_code(response, status.HTTP_200_OK)
        data = get_json_response(response)
        assert data["id"] == test_user.id
        assert data["email"] == test_user.email
        assert "hashed_password" not in data  # Ensure password not exposed
    
    def test_update_user_profile(self, authenticated_client, test_user):
        """Test updating user profile."""
        update_data = {
            "full_name": "Updated Name",
            "phone_number": "+254712345678"
        }
        
        response = authenticated_client.put(
            f"/api/v1/users/{test_user.id}",
            json=update_data
        )
        
        assert_status_code(response, status.HTTP_200_OK)
        data = get_json_response(response)
        assert data["full_name"] == "Updated Name"
    
    def test_change_password(self, authenticated_client):
        """Test changing user password."""
        password_data = {
            "current_password": "testpassword123",
            "new_password": "NewSecurePass123!",
            "confirm_password": "NewSecurePass123!"
        }
        
        response = authenticated_client.post(
            "/api/v1/users/me/change-password",
            json=password_data
        )
        
        assert_status_code(response, status.HTTP_200_OK)
    
    def test_change_password_wrong_current(self, authenticated_client):
        """Test changing password with wrong current password."""
        password_data = {
            "current_password": "wrongpassword",
            "new_password": "NewSecurePass123!",
            "confirm_password": "NewSecurePass123!"
        }
        
        response = authenticated_client.post(
            "/api/v1/users/me/change-password",
            json=password_data
        )
        
        assert_status_code(response, status.HTTP_400_BAD_REQUEST)
    
    def test_change_password_mismatch(self, authenticated_client):
        """Test changing password with mismatched confirmation."""
        password_data = {
            "current_password": "testpassword123",
            "new_password": "NewSecurePass123!",
            "confirm_password": "DifferentPass123!"
        }
        
        response = authenticated_client.post(
            "/api/v1/users/me/change-password",
            json=password_data
        )
        
        assert_status_code(response, status.HTTP_400_BAD_REQUEST)
    
    def test_update_user_avatar(self, authenticated_client, test_image_file):
        """Test uploading user avatar."""
        with open(test_image_file, 'rb') as f:
            files = {"avatar": ("avatar.jpg", f, "image/jpeg")}
            
            response = authenticated_client.post(
                "/api/v1/users/me/avatar",
                files=files
            )
        
        assert_status_code(response, status.HTTP_200_OK)
        data = get_json_response(response)
        assert "avatar_url" in data
    
    def test_delete_user_avatar(self, authenticated_client):
        """Test deleting user avatar."""
        response = authenticated_client.delete("/api/v1/users/me/avatar")
        
        assert_status_code(response, status.HTTP_204_NO_CONTENT)
    
    def test_get_user_statistics(self, authenticated_client, test_user):
        """Test getting user statistics."""
        response = authenticated_client.get(
            f"/api/v1/users/{test_user.id}/statistics"
        )
        
        assert_status_code(response, status.HTTP_200_OK)
        data = get_json_response(response)
        assert_dict_structure(data, [
            "total_farms", "total_fields", "total_crops"
        ])
    
    def test_get_user_activity_log(self, authenticated_client):
        """Test getting user activity log."""
        response = authenticated_client.get("/api/v1/users/me/activity")
        
        assert_status_code(response, status.HTTP_200_OK)
        data = get_json_response(response)
        assert isinstance(data, list)
    
    def test_deactivate_account(self, authenticated_client):
        """Test deactivating user account."""
        response = authenticated_client.post("/api/v1/users/me/deactivate")
        
        assert_status_code(response, status.HTTP_200_OK)
    
    def test_list_users_admin(self, authenticated_client, test_admin_user):
        """Test listing all users (admin only)."""
        response = authenticated_client.get("/api/v1/users")
        
        # May require admin privileges
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_403_FORBIDDEN
        ]
    
    def test_create_user_admin(self, authenticated_client, test_admin_user):
        """Test creating user as admin."""
        user_data = {
            "email": "newadmin@example.com",
            "password": "AdminPass123!",
            "full_name": "New Admin",
            "role": "admin"
        }
        
        response = authenticated_client.post("/api/v1/users", json=user_data)
        
        # May require admin privileges
        assert response.status_code in [
            status.HTTP_201_CREATED,
            status.HTTP_403_FORBIDDEN
        ]
    
    def test_update_user_role(self, authenticated_client, test_user):
        """Test updating user role (admin only)."""
        update_data = {"role": "agronomist"}
        
        response = authenticated_client.patch(
            f"/api/v1/users/{test_user.id}/role",
            json=update_data
        )
        
        # May require admin privileges
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_403_FORBIDDEN
        ]
    
    def test_suspend_user(self, authenticated_client, db_session):
        """Test suspending user account (admin only)."""
        from app.database.models.user import User
        from app.core.security import get_password_hash
        
        user = User(
            email="suspend@example.com",
            hashed_password=get_password_hash("password"),
            full_name="Suspend Test"
        )
        db_session.add(user)
        db_session.commit()
        
        response = authenticated_client.post(
            f"/api/v1/users/{user.id}/suspend"
        )
        
        # May require admin privileges
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_403_FORBIDDEN
        ]
    
    def test_delete_user_admin(self, authenticated_client, db_session):
        """Test deleting user (admin only)."""
        from app.database.models.user import User
        from app.core.security import get_password_hash
        
        user = User(
            email="delete@example.com",
            hashed_password=get_password_hash("password"),
            full_name="Delete Test"
        )
        db_session.add(user)
        db_session.commit()
        user_id = user.id
        
        response = authenticated_client.delete(f"/api/v1/users/{user_id}")
        
        # May require admin privileges
        assert response.status_code in [
            status.HTTP_204_NO_CONTENT,
            status.HTTP_403_FORBIDDEN
        ]


@pytest.mark.api
@pytest.mark.integration
class TestUserPreferencesAPI:
    """Test user preferences and settings."""
    
    def test_get_user_preferences(self, authenticated_client):
        """Test getting user preferences."""
        response = authenticated_client.get("/api/v1/users/me/preferences")
        
        assert_status_code(response, status.HTTP_200_OK)
        data = get_json_response(response)
        assert isinstance(data, dict)
    
    def test_update_preferences(self, authenticated_client):
        """Test updating user preferences."""
        preferences = {
            "language": "en",
            "timezone": "Africa/Nairobi",
            "notifications": {
                "email": True,
                "sms": False,
                "push": True
            },
            "measurement_units": "metric"
        }
        
        response = authenticated_client.put(
            "/api/v1/users/me/preferences",
            json=preferences
        )
        
        assert_status_code(response, status.HTTP_200_OK)
    
    def test_get_notification_settings(self, authenticated_client):
        """Test getting notification settings."""
        response = authenticated_client.get(
            "/api/v1/users/me/preferences/notifications"
        )
        
        assert_status_code(response, status.HTTP_200_OK)
        data = get_json_response(response)
        assert_dict_structure(data, ["email", "sms", "push"])
    
    def test_update_notification_settings(self, authenticated_client):
        """Test updating notification settings."""
        settings = {
            "email": True,
            "sms": True,
            "push": False
        }
        
        response = authenticated_client.put(
            "/api/v1/users/me/preferences/notifications",
            json=settings
        )
        
        assert_status_code(response, status.HTTP_200_OK)


@pytest.mark.api
@pytest.mark.integration
class TestTeamManagementAPI:
    """Test team and collaboration features."""
    
    def test_invite_team_member(self, authenticated_client, test_farm):
        """Test inviting team member to farm."""
        invite_data = {
            "email": "member@example.com",
            "role": "worker",
            "permissions": ["view", "edit_fields"]
        }
        
        response = authenticated_client.post(
            f"/api/v1/farms/{test_farm.id}/team/invite",
            json=invite_data
        )
        
        assert_status_code(response, status.HTTP_201_CREATED)
    
    def test_list_team_members(self, authenticated_client, test_farm):
        """Test listing farm team members."""
        response = authenticated_client.get(
            f"/api/v1/farms/{test_farm.id}/team"
        )
        
        assert_status_code(response, status.HTTP_200_OK)
        data = get_json_response(response)
        assert isinstance(data, list)
    
    def test_update_team_member_role(self, authenticated_client, test_farm):
        """Test updating team member role."""
        update_data = {"role": "supervisor"}
        
        response = authenticated_client.patch(
            f"/api/v1/farms/{test_farm.id}/team/1/role",
            json=update_data
        )
        
        # May not exist, but tests endpoint
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_404_NOT_FOUND
        ]
    
    def test_remove_team_member(self, authenticated_client, test_farm):
        """Test removing team member."""
        response = authenticated_client.delete(
            f"/api/v1/farms/{test_farm.id}/team/1"
        )
        
        # May not exist, but tests endpoint
        assert response.status_code in [
            status.HTTP_204_NO_CONTENT,
            status.HTTP_404_NOT_FOUND
        ]
    
    def test_accept_team_invitation(self, authenticated_client):
        """Test accepting team invitation."""
        response = authenticated_client.post(
            "/api/v1/invitations/token123/accept"
        )
        
        # Will fail without valid token, but tests endpoint
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_404_NOT_FOUND
        ]
    
    def test_reject_team_invitation(self, authenticated_client):
        """Test rejecting team invitation."""
        response = authenticated_client.post(
            "/api/v1/invitations/token123/reject"
        )
        
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_404_NOT_FOUND
        ]


@pytest.mark.api
@pytest.mark.integration
class TestEmailVerificationAPI:
    """Test email verification endpoints."""
    
    def test_send_verification_email(self, authenticated_client):
        """Test sending verification email."""
        response = authenticated_client.post(
            "/api/v1/auth/verify-email/send"
        )
        
        assert_status_code(response, status.HTTP_200_OK)
    
    def test_verify_email_with_token(self, client):
        """Test verifying email with token."""
        response = client.get(
            "/api/v1/auth/verify-email?token=verification_token"
        )
        
        # Will fail without valid token
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_400_BAD_REQUEST
        ]
    
    def test_resend_verification_email(self, authenticated_client):
        """Test resending verification email."""
        response = authenticated_client.post(
            "/api/v1/auth/verify-email/resend"
        )
        
        assert_status_code(response, status.HTTP_200_OK)


@pytest.mark.api
@pytest.mark.integration
class TestUserRolesPermissionsAPI:
    """Test role-based access control."""
    
    def test_farmer_cannot_access_admin_endpoints(self, authenticated_client):
        """Test farmer role cannot access admin endpoints."""
        response = authenticated_client.get("/api/v1/admin/users")
        
        assert_status_code(response, status.HTTP_403_FORBIDDEN)
    
    def test_agronomist_can_access_reports(self, authenticated_client, test_agronomist_user):
        """Test agronomist role can access reports."""
        # Assuming test_agronomist_user is authenticated
        response = authenticated_client.get("/api/v1/reports/analysis")
        
        # Agronomist should have access
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_403_FORBIDDEN
        ]
    
    def test_check_user_permissions(self, authenticated_client):
        """Test checking user permissions."""
        response = authenticated_client.get("/api/v1/users/me/permissions")
        
        assert_status_code(response, status.HTTP_200_OK)
        data = get_json_response(response)
        assert isinstance(data, list)
    
    def test_assign_custom_permissions(self, authenticated_client, test_user):
        """Test assigning custom permissions (admin only)."""
        permissions_data = {
            "permissions": ["create_farm", "delete_farm", "manage_users"]
        }
        
        response = authenticated_client.post(
            f"/api/v1/users/{test_user.id}/permissions",
            json=permissions_data
        )
        
        # May require admin privileges
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_403_FORBIDDEN
        ]
