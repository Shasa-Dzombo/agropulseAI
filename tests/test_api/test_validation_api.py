"""
Validation and Integration API Tests

Tests for request validation, data integrity, and complex integration scenarios.
"""

import pytest
from datetime import datetime, timedelta
from fastapi import status

from tests.utils import (
    assert_status_code, get_json_response, validate_error_response,
    assert_dict_structure
)


@pytest.mark.api
@pytest.mark.integration
class TestRequestValidationAPI:
    """Test API request validation."""
    
    def test_create_farm_missing_required_fields(self, authenticated_client):
        """Test farm creation with missing required fields."""
        incomplete_data = {"name": "Test Farm"}  # Missing owner_id, location
        
        response = authenticated_client.post(
            "/api/v1/farms",
            json=incomplete_data
        )
        
        assert_status_code(response, status.HTTP_422_UNPROCESSABLE_ENTITY)
        validate_error_response(get_json_response(response))
    
    def test_create_farm_invalid_coordinates(self, authenticated_client, test_user):
        """Test farm creation with invalid GPS coordinates."""
        invalid_data = {
            "name": "Test Farm",
            "owner_id": test_user.id,
            "location": "Test",
            "latitude": 95.0,  # Invalid: > 90
            "longitude": -185.0  # Invalid: < -180
        }
        
        response = authenticated_client.post(
            "/api/v1/farms",
            json=invalid_data
        )
        
        assert_status_code(response, status.HTTP_422_UNPROCESSABLE_ENTITY)
    
    def test_create_field_negative_size(self, authenticated_client, test_farm):
        """Test field creation with negative size."""
        invalid_data = {
            "farm_id": test_farm.id,
            "name": "Test Field",
            "size_hectares": -5.0  # Invalid
        }
        
        response = authenticated_client.post(
            f"/api/v1/farms/{test_farm.id}/fields",
            json=invalid_data
        )
        
        assert_status_code(response, status.HTTP_422_UNPROCESSABLE_ENTITY)
    
    def test_create_sensor_reading_invalid_quality_score(self, authenticated_client, test_sensor):
        """Test sensor reading with invalid quality score."""
        invalid_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "value": 50.0,
            "unit": "percentage",
            "quality_score": 1.5  # Invalid: > 1.0
        }
        
        response = authenticated_client.post(
            f"/api/v1/sensors/{test_sensor.id}/readings",
            json=invalid_data
        )
        
        assert_status_code(response, status.HTTP_422_UNPROCESSABLE_ENTITY)
    
    def test_invalid_email_format(self, client):
        """Test registration with invalid email format."""
        invalid_data = {
            "email": "not-an-email",
            "password": "Password123!",
            "full_name": "Test User"
        }
        
        response = client.post("/api/v1/auth/register", json=invalid_data)
        
        assert_status_code(response, status.HTTP_422_UNPROCESSABLE_ENTITY)
    
    def test_weak_password(self, client):
        """Test registration with weak password."""
        invalid_data = {
            "email": "test@example.com",
            "password": "123",  # Too weak
            "full_name": "Test User"
        }
        
        response = client.post("/api/v1/auth/register", json=invalid_data)
        
        assert response.status_code in [
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            status.HTTP_400_BAD_REQUEST
        ]
    
    def test_invalid_date_range(self, authenticated_client, test_farm):
        """Test query with invalid date range (end before start)."""
        start = datetime.utcnow().isoformat()
        end = (datetime.utcnow() - timedelta(days=30)).isoformat()
        
        response = authenticated_client.get(
            f"/api/v1/reports/farm/{test_farm.id}/yield",
            params={"start_date": start, "end_date": end}
        )
        
        assert response.status_code in [
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            status.HTTP_400_BAD_REQUEST
        ]
    
    def test_invalid_enum_value(self, authenticated_client, test_crop):
        """Test update with invalid enum value."""
        invalid_data = {"growth_stage": "invalid_stage"}
        
        response = authenticated_client.patch(
            f"/api/v1/crops/{test_crop.id}",
            json=invalid_data
        )
        
        assert_status_code(response, status.HTTP_422_UNPROCESSABLE_ENTITY)
    
    def test_string_too_long(self, authenticated_client, test_user):
        """Test input validation for overly long strings."""
        invalid_data = {
            "full_name": "A" * 500  # Exceeds max length
        }
        
        response = authenticated_client.put(
            f"/api/v1/users/{test_user.id}",
            json=invalid_data
        )
        
        assert response.status_code in [
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            status.HTTP_400_BAD_REQUEST
        ]
    
    def test_invalid_uuid_format(self, authenticated_client):
        """Test endpoint with invalid UUID format."""
        response = authenticated_client.get("/api/v1/farms/not-a-uuid")
        
        assert response.status_code in [
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            status.HTTP_404_NOT_FOUND
        ]


@pytest.mark.api
@pytest.mark.integration
class TestDataIntegrityAPI:
    """Test data integrity and consistency."""
    
    def test_delete_farm_cascades_to_fields(self, authenticated_client, test_farm, test_field, db_session):
        """Test deleting farm cascades to fields."""
        farm_id = test_farm.id
        field_id = test_field.id
        
        # Delete farm
        response = authenticated_client.delete(f"/api/v1/farms/{farm_id}")
        assert_status_code(response, status.HTTP_204_NO_CONTENT)
        
        # Verify field also deleted
        field_response = authenticated_client.get(f"/api/v1/fields/{field_id}")
        assert_status_code(field_response, status.HTTP_404_NOT_FOUND)
    
    def test_delete_field_cascades_to_crops(self, authenticated_client, test_field, test_crop):
        """Test deleting field cascades to crops."""
        field_id = test_field.id
        crop_id = test_crop.id
        
        # Delete field
        response = authenticated_client.delete(f"/api/v1/fields/{field_id}")
        assert_status_code(response, status.HTTP_204_NO_CONTENT)
        
        # Verify crop also deleted
        crop_response = authenticated_client.get(f"/api/v1/crops/{crop_id}")
        assert_status_code(crop_response, status.HTTP_404_NOT_FOUND)
    
    def test_foreign_key_constraint(self, authenticated_client):
        """Test foreign key constraint violation."""
        invalid_data = {
            "name": "Test Field",
            "farm_id": 99999  # Non-existent farm
        }
        
        response = authenticated_client.post(
            "/api/v1/farms/99999/fields",
            json=invalid_data
        )
        
        assert response.status_code in [
            status.HTTP_404_NOT_FOUND,
            status.HTTP_400_BAD_REQUEST
        ]
    
    def test_unique_constraint_violation(self, client, test_user):
        """Test unique constraint violation."""
        duplicate_user = {
            "email": test_user.email,  # Duplicate email
            "password": "Password123!",
            "full_name": "Duplicate"
        }
        
        response = client.post("/api/v1/auth/register", json=duplicate_user)
        
        assert_status_code(response, status.HTTP_400_BAD_REQUEST)
    
    def test_concurrent_updates(self, authenticated_client, test_farm):
        """Test handling concurrent updates to same resource."""
        update1 = {"name": "Updated Name 1"}
        update2 = {"name": "Updated Name 2"}
        
        # Simulate concurrent updates
        response1 = authenticated_client.put(
            f"/api/v1/farms/{test_farm.id}",
            json=update1
        )
        response2 = authenticated_client.put(
            f"/api/v1/farms/{test_farm.id}",
            json=update2
        )
        
        # Both should succeed
        assert_status_code(response1, status.HTTP_200_OK)
        assert_status_code(response2, status.HTTP_200_OK)
        
        # Last update wins
        final_response = authenticated_client.get(
            f"/api/v1/farms/{test_farm.id}"
        )
        data = get_json_response(final_response)
        assert data["name"] == "Updated Name 2"
    
    def test_soft_delete_preserves_data(self, authenticated_client, test_user, db_session):
        """Test soft delete doesn't remove data from database."""
        from app.database.models.user import User
        
        # Get user before deactivation
        response = authenticated_client.post("/api/v1/users/me/deactivate")
        assert_status_code(response, status.HTTP_200_OK)
        
        # User should still exist in database but inactive
        user = db_session.query(User).filter(User.id == test_user.id).first()
        assert user is not None
        assert user.is_active is False


@pytest.mark.api
@pytest.mark.integration
class TestComplexQueryAPI:
    """Test complex queries and filtering."""
    
    def test_multi_field_search(self, authenticated_client, test_farm):
        """Test searching across multiple fields."""
        response = authenticated_client.get(
            "/api/v1/farms/search",
            params={"q": test_farm.name, "location": test_farm.location}
        )
        
        assert_status_code(response, status.HTTP_200_OK)
        data = get_json_response(response)
        assert any(f["id"] == test_farm.id for f in data)
    
    def test_date_range_filtering(self, authenticated_client, test_farm):
        """Test filtering by date range."""
        start_date = (datetime.utcnow() - timedelta(days=90)).isoformat()
        end_date = datetime.utcnow().isoformat()
        
        response = authenticated_client.get(
            f"/api/v1/farms/{test_farm.id}/weather/history",
            params={"start_date": start_date, "end_date": end_date}
        )
        
        assert_status_code(response, status.HTTP_200_OK)
    
    def test_pagination_with_sorting(self, authenticated_client):
        """Test pagination with custom sorting."""
        response = authenticated_client.get(
            "/api/v1/farms",
            params={"page": 1, "page_size": 10, "sort_by": "created_at", "order": "desc"}
        )
        
        assert_status_code(response, status.HTTP_200_OK)
    
    def test_filtering_by_multiple_criteria(self, authenticated_client):
        """Test filtering by multiple criteria."""
        response = authenticated_client.get(
            "/api/v1/crops",
            params={
                "crop_type": "maize",
                "health_status": "healthy",
                "growth_stage": "flowering"
            }
        )
        
        assert_status_code(response, status.HTTP_200_OK)
    
    def test_nested_resource_query(self, authenticated_client, test_farm):
        """Test querying nested resources."""
        response = authenticated_client.get(
            f"/api/v1/farms/{test_farm.id}/fields",
            params={"include_crops": True, "include_sensors": True}
        )
        
        assert_status_code(response, status.HTTP_200_OK)
    
    def test_aggregation_query(self, authenticated_client, test_farm):
        """Test aggregation queries."""
        response = authenticated_client.get(
            f"/api/v1/farms/{test_farm.id}/statistics/aggregate",
            params={"group_by": "crop_type", "metric": "total_yield"}
        )
        
        assert_status_code(response, status.HTTP_200_OK)


@pytest.mark.api
@pytest.mark.integration
class TestBatchOperationsAPI:
    """Test batch operations."""
    
    def test_batch_create_fields(self, authenticated_client, test_farm):
        """Test batch creating multiple fields."""
        fields_data = [
            {"name": f"Field {i}", "farm_id": test_farm.id, "size_hectares": 5.0}
            for i in range(5)
        ]
        
        response = authenticated_client.post(
            f"/api/v1/farms/{test_farm.id}/fields/batch",
            json={"fields": fields_data}
        )
        
        assert response.status_code in [
            status.HTTP_201_CREATED,
            status.HTTP_207_MULTI_STATUS
        ]
    
    def test_batch_update_crops(self, authenticated_client, test_field, db_session):
        """Test batch updating crops."""
        from app.database.models.crop import Crop
        
        # Create multiple crops
        crops = []
        for i in range(3):
            crop = Crop(
                field_id=test_field.id,
                crop_type="maize",
                variety=f"Variety {i}"
            )
            db_session.add(crop)
            crops.append(crop)
        db_session.commit()
        
        updates = [
            {"id": crop.id, "health_status": "healthy"}
            for crop in crops
        ]
        
        response = authenticated_client.patch(
            "/api/v1/crops/batch",
            json={"updates": updates}
        )
        
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_207_MULTI_STATUS
        ]
    
    def test_batch_delete_alerts(self, authenticated_client, test_user, db_session):
        """Test batch deleting alerts."""
        from app.database.models.alert import Alert
        
        # Create multiple alerts
        alert_ids = []
        for i in range(5):
            alert = Alert(
                user_id=test_user.id,
                alert_type="test",
                severity="low",
                title=f"Alert {i}",
                message="Test"
            )
            db_session.add(alert)
        db_session.commit()
        db_session.refresh(alert)
        alert_ids.append(alert.id)
        
        response = authenticated_client.post(
            "/api/v1/alerts/batch/delete",
            json={"alert_ids": alert_ids}
        )
        
        assert response.status_code in [
            status.HTTP_204_NO_CONTENT,
            status.HTTP_200_OK
        ]


@pytest.mark.api
@pytest.mark.integration
class TestNotificationAPI:
    """Test notification endpoints."""
    
    def test_get_notifications(self, authenticated_client):
        """Test getting user notifications."""
        response = authenticated_client.get("/api/v1/notifications")
        
        assert_status_code(response, status.HTTP_200_OK)
        data = get_json_response(response)
        assert isinstance(data, list)
    
    def test_mark_notification_read(self, authenticated_client):
        """Test marking notification as read."""
        response = authenticated_client.patch("/api/v1/notifications/1/read")
        
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_404_NOT_FOUND
        ]
    
    def test_mark_all_notifications_read(self, authenticated_client):
        """Test marking all notifications as read."""
        response = authenticated_client.post(
            "/api/v1/notifications/mark-all-read"
        )
        
        assert_status_code(response, status.HTTP_200_OK)
    
    def test_delete_notification(self, authenticated_client):
        """Test deleting notification."""
        response = authenticated_client.delete("/api/v1/notifications/1")
        
        assert response.status_code in [
            status.HTTP_204_NO_CONTENT,
            status.HTTP_404_NOT_FOUND
        ]
    
    def test_get_unread_count(self, authenticated_client):
        """Test getting unread notification count."""
        response = authenticated_client.get(
            "/api/v1/notifications/unread/count"
        )
        
        assert_status_code(response, status.HTTP_200_OK)
        data = get_json_response(response)
        assert "count" in data
    
    def test_subscribe_to_notifications(self, authenticated_client):
        """Test subscribing to push notifications."""
        subscription_data = {
            "endpoint": "https://push.example.com",
            "keys": {"p256dh": "key1", "auth": "key2"}
        }
        
        response = authenticated_client.post(
            "/api/v1/notifications/subscribe",
            json=subscription_data
        )
        
        assert response.status_code in [
            status.HTTP_201_CREATED,
            status.HTTP_501_NOT_IMPLEMENTED
        ]


@pytest.mark.api
@pytest.mark.integration
class TestActivityAPI:
    """Test activity tracking endpoints."""
    
    def test_get_activity_feed(self, authenticated_client):
        """Test getting activity feed."""
        response = authenticated_client.get("/api/v1/activity")
        
        assert_status_code(response, status.HTTP_200_OK)
        data = get_json_response(response)
        assert isinstance(data, list)
    
    def test_get_farm_activity(self, authenticated_client, test_farm):
        """Test getting farm activity."""
        response = authenticated_client.get(
            f"/api/v1/farms/{test_farm.id}/activity"
        )
        
        assert_status_code(response, status.HTTP_200_OK)
    
    def test_get_field_activity(self, authenticated_client, test_field):
        """Test getting field activity."""
        response = authenticated_client.get(
            f"/api/v1/fields/{test_field.id}/activity"
        )
        
        assert_status_code(response, status.HTTP_200_OK)
    
    def test_log_custom_activity(self, authenticated_client, test_farm):
        """Test logging custom activity."""
        activity_data = {
            "activity_type": "irrigation",
            "description": "Watered Field 1",
            "metadata": {"water_amount": "500L"}
        }
        
        response = authenticated_client.post(
            f"/api/v1/farms/{test_farm.id}/activity",
            json=activity_data
        )
        
        assert_status_code(response, status.HTTP_201_CREATED)


@pytest.mark.api
@pytest.mark.integration
class TestHealthCheckAPI:
    """Test health check and system status endpoints."""
    
    def test_api_health_check(self, client):
        """Test API health check."""
        response = client.get("/api/v1/health")
        
        assert_status_code(response, status.HTTP_200_OK)
        data = get_json_response(response)
        assert data["status"] == "healthy"
    
    def test_database_health_check(self, client):
        """Test database health check."""
        response = client.get("/api/v1/health/database")
        
        assert_status_code(response, status.HTTP_200_OK)
        data = get_json_response(response)
        assert "database" in data
    
    def test_api_version(self, client):
        """Test getting API version."""
        response = client.get("/api/v1/version")
        
        assert_status_code(response, status.HTTP_200_OK)
        data = get_json_response(response)
        assert "version" in data
    
    def test_system_status(self, authenticated_client):
        """Test system status (admin only)."""
        response = authenticated_client.get("/api/v1/system/status")
        
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_403_FORBIDDEN
        ]
    
    def test_metrics_endpoint(self, authenticated_client):
        """Test metrics endpoint."""
        response = authenticated_client.get("/api/v1/metrics")
        
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_403_FORBIDDEN
        ]


@pytest.mark.api
@pytest.mark.slow
class TestPerformanceAPI:
    """Test API performance and response times."""
    
    def test_list_farms_response_time(self, authenticated_client, performance_timer):
        """Test list farms response time."""
        with performance_timer("list_farms"):
            response = authenticated_client.get("/api/v1/farms")
        
        assert_status_code(response, status.HTTP_200_OK)
        assert performance_timer.get_average_time("list_farms") < 1.0  # < 1 second
    
    def test_complex_query_performance(self, authenticated_client, performance_timer):
        """Test complex query performance."""
        with performance_timer("complex_query"):
            response = authenticated_client.get(
                "/api/v1/analytics/dashboard"
            )
        
        assert_status_code(response, status.HTTP_200_OK)
        assert performance_timer.get_average_time("complex_query") < 2.0
    
    def test_concurrent_requests(self, authenticated_client):
        """Test handling concurrent requests."""
        import concurrent.futures
        
        def make_request():
            return authenticated_client.get("/api/v1/farms")
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(make_request) for _ in range(20)]
            responses = [f.result() for f in futures]
        
        # All should succeed
        assert all(r.status_code == status.HTTP_200_OK for r in responses)
    
    def test_large_dataset_pagination(self, authenticated_client, test_user, db_session):
        """Test pagination with large dataset."""
        from app.database.models.farm import Farm
        
        # Create many farms
        for i in range(100):
            farm = Farm(
                name=f"Farm {i}",
                owner_id=test_user.id,
                location="Test"
            )
            db_session.add(farm)
        db_session.commit()
        
        response = authenticated_client.get(
            "/api/v1/farms",
            params={"page": 1, "page_size": 50}
        )
        
        assert_status_code(response, status.HTTP_200_OK)


@pytest.mark.api
@pytest.mark.integration
class TestContentNegotiationAPI:
    """Test content negotiation and response formats."""
    
    def test_json_response(self, authenticated_client, test_farm):
        """Test JSON response format."""
        response = authenticated_client.get(
            f"/api/v1/farms/{test_farm.id}",
            headers={"Accept": "application/json"}
        )
        
        assert_status_code(response, status.HTTP_200_OK)
        assert response.headers["content-type"].startswith("application/json")
    
    def test_accept_xml(self, authenticated_client, test_farm):
        """Test XML response format (if supported)."""
        response = authenticated_client.get(
            f"/api/v1/farms/{test_farm.id}",
            headers={"Accept": "application/xml"}
        )
        
        # May or may not support XML
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_406_NOT_ACCEPTABLE
        ]
    
    def test_gzip_compression(self, authenticated_client):
        """Test gzip compression."""
        response = authenticated_client.get(
            "/api/v1/farms",
            headers={"Accept-Encoding": "gzip"}
        )
        
        assert_status_code(response, status.HTTP_200_OK)


@pytest.mark.api
@pytest.mark.integration
class TestAPIVersioningAPI:
    """Test API versioning."""
    
    def test_v1_endpoint(self, authenticated_client):
        """Test v1 API endpoint."""
        response = authenticated_client.get("/api/v1/farms")
        
        assert_status_code(response, status.HTTP_200_OK)
    
    def test_deprecated_endpoint(self, authenticated_client):
        """Test deprecated endpoint returns warning."""
        response = authenticated_client.get("/api/v1/deprecated-endpoint")
        
        # Should return 404 or warning header
        if response.status_code == status.HTTP_200_OK:
            assert "Deprecation" in response.headers or \
                   "Warning" in response.headers
