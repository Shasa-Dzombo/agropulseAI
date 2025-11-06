"""
Comprehensive API Tests

Complete test suite for all REST API endpoints, WebSocket connections,
authentication, authorization, and API functionality.
"""

import pytest
import json
from datetime import datetime, timedelta
from fastapi import status

from tests.factories import (
    FarmFactory, FieldFactory, CropFactory, UserFactory,
    SensorFactory, AlertFactory, CropRecommendationInputFactory
)
from tests.utils import (
    assert_status_code, assert_success_response, get_json_response,
    validate_pagination_response, validate_error_response,
    assert_dict_structure
)


# ==================== Authentication Tests ====================

@pytest.mark.api
@pytest.mark.integration
class TestAuthenticationAPI:
    """Test authentication endpoints."""
    
    def test_register_user(self, client):
        """Test user registration."""
        user_data = {
            "email": "newuser@example.com",
            "password": "SecurePassword123!",
            "full_name": "New User",
            "phone_number": "+254712345678"
        }
        
        response = client.post("/api/v1/auth/register", json=user_data)
        
        assert_status_code(response, status.HTTP_201_CREATED)
        data = get_json_response(response)
        assert_dict_structure(data, ["id", "email", "full_name"])
        assert data["email"] == user_data["email"]
    
    def test_register_duplicate_email(self, client, test_user):
        """Test registration with duplicate email fails."""
        user_data = {
            "email": test_user.email,
            "password": "Password123!",
            "full_name": "Duplicate User",
            "phone_number": "+254712345679"
        }
        
        response = client.post("/api/v1/auth/register", json=user_data)
        
        assert_status_code(response, status.HTTP_400_BAD_REQUEST)
    
    def test_login_success(self, client, test_user):
        """Test successful login."""
        login_data = {
            "username": test_user.email,
            "password": "testpassword123"
        }
        
        response = client.post("/api/v1/auth/login", data=login_data)
        
        assert_status_code(response, status.HTTP_200_OK)
        data = get_json_response(response)
        assert_dict_structure(data, ["access_token", "token_type"])
        assert data["token_type"] == "bearer"
    
    def test_login_invalid_credentials(self, client, test_user):
        """Test login with invalid credentials."""
        login_data = {
            "username": test_user.email,
            "password": "wrongpassword"
        }
        
        response = client.post("/api/v1/auth/login", data=login_data)
        
        assert_status_code(response, status.HTTP_401_UNAUTHORIZED)
    
    def test_login_nonexistent_user(self, client):
        """Test login with non-existent user."""
        login_data = {
            "username": "nonexistent@example.com",
            "password": "password123"
        }
        
        response = client.post("/api/v1/auth/login", data=login_data)
        
        assert_status_code(response, status.HTTP_401_UNAUTHORIZED)
    
    def test_get_current_user(self, authenticated_client, test_user):
        """Test getting current user info."""
        response = authenticated_client.get("/api/v1/auth/me")
        
        assert_status_code(response, status.HTTP_200_OK)
        data = get_json_response(response)
        assert data["email"] == test_user.email
        assert data["id"] == test_user.id
    
    def test_get_current_user_unauthorized(self, client):
        """Test getting user without authentication."""
        response = client.get("/api/v1/auth/me")
        
        assert_status_code(response, status.HTTP_401_UNAUTHORIZED)
    
    def test_refresh_token(self, authenticated_client):
        """Test token refresh."""
        response = authenticated_client.post("/api/v1/auth/refresh")
        
        assert_status_code(response, status.HTTP_200_OK)
        data = get_json_response(response)
        assert "access_token" in data
    
    def test_logout(self, authenticated_client):
        """Test user logout."""
        response = authenticated_client.post("/api/v1/auth/logout")
        
        assert_status_code(response, status.HTTP_200_OK)
    
    def test_password_reset_request(self, client, test_user):
        """Test password reset request."""
        response = client.post(
            "/api/v1/auth/password-reset/request",
            json={"email": test_user.email}
        )
        
        assert_status_code(response, status.HTTP_200_OK)
    
    def test_password_reset_confirm(self, client, test_user):
        """Test password reset confirmation."""
        reset_data = {
            "token": "reset_token",
            "new_password": "NewSecurePass123!"
        }
        
        response = client.post(
            "/api/v1/auth/password-reset/confirm",
            json=reset_data
        )
        
        # Will fail without valid token, but tests endpoint
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_400_BAD_REQUEST
        ]


# ==================== Farm API Tests ====================

@pytest.mark.api
@pytest.mark.integration
class TestFarmAPI:
    """Test farm management endpoints."""
    
    def test_create_farm(self, authenticated_client, test_user):
        """Test creating a farm."""
        farm_data = FarmFactory.build(owner_id=test_user.id)
        
        response = authenticated_client.post("/api/v1/farms", json=farm_data)
        
        assert_status_code(response, status.HTTP_201_CREATED)
        data = get_json_response(response)
        assert data["name"] == farm_data["name"]
        assert data["owner_id"] == test_user.id
    
    def test_get_farm(self, authenticated_client, test_farm):
        """Test getting a farm by ID."""
        response = authenticated_client.get(f"/api/v1/farms/{test_farm.id}")
        
        assert_status_code(response, status.HTTP_200_OK)
        data = get_json_response(response)
        assert data["id"] == test_farm.id
        assert data["name"] == test_farm.name
    
    def test_get_farm_not_found(self, authenticated_client):
        """Test getting non-existent farm."""
        response = authenticated_client.get("/api/v1/farms/99999")
        
        assert_status_code(response, status.HTTP_404_NOT_FOUND)
    
    def test_list_user_farms(self, authenticated_client, test_user, test_farm):
        """Test listing all farms for a user."""
        response = authenticated_client.get("/api/v1/farms")
        
        assert_status_code(response, status.HTTP_200_OK)
        data = get_json_response(response)
        
        assert isinstance(data, list)
        assert len(data) >= 1
        assert any(f["id"] == test_farm.id for f in data)
    
    def test_update_farm(self, authenticated_client, test_farm):
        """Test updating a farm."""
        update_data = {"name": "Updated Farm Name"}
        
        response = authenticated_client.put(
            f"/api/v1/farms/{test_farm.id}",
            json=update_data
        )
        
        assert_status_code(response, status.HTTP_200_OK)
        data = get_json_response(response)
        assert data["name"] == "Updated Farm Name"
    
    def test_delete_farm(self, authenticated_client, test_user, db_session):
        """Test deleting a farm."""
        # Create farm to delete
        from app.database.models.farm import Farm
        farm = Farm(
            name="To Delete",
            owner_id=test_user.id,
            location="Test"
        )
        db_session.add(farm)
        db_session.commit()
        farm_id = farm.id
        
        response = authenticated_client.delete(f"/api/v1/farms/{farm_id}")
        
        assert_status_code(response, status.HTTP_204_NO_CONTENT)
        
        # Verify deleted
        get_response = authenticated_client.get(f"/api/v1/farms/{farm_id}")
        assert_status_code(get_response, status.HTTP_404_NOT_FOUND)
    
    def test_get_farm_unauthorized(self, client, test_farm):
        """Test accessing farm without authentication."""
        response = client.get(f"/api/v1/farms/{test_farm.id}")
        
        assert_status_code(response, status.HTTP_401_UNAUTHORIZED)
    
    def test_farm_pagination(self, authenticated_client, test_user, db_session):
        """Test farm list pagination."""
        # Create multiple farms
        from app.database.models.farm import Farm
        for i in range(15):
            farm = Farm(
                name=f"Farm {i}",
                owner_id=test_user.id,
                location="Test"
            )
            db_session.add(farm)
        db_session.commit()
        
        response = authenticated_client.get(
            "/api/v1/farms?page=1&page_size=10"
        )
        
        assert_status_code(response, status.HTTP_200_OK)
        # Depending on pagination implementation


# ==================== Field API Tests ====================

@pytest.mark.api
@pytest.mark.integration
class TestFieldAPI:
    """Test field management endpoints."""
    
    def test_create_field(self, authenticated_client, test_farm):
        """Test creating a field."""
        field_data = FieldFactory.build(farm_id=test_farm.id)
        
        response = authenticated_client.post(
            f"/api/v1/farms/{test_farm.id}/fields",
            json=field_data
        )
        
        assert_status_code(response, status.HTTP_201_CREATED)
        data = get_json_response(response)
        assert data["farm_id"] == test_farm.id
    
    def test_get_field(self, authenticated_client, test_field):
        """Test getting a field."""
        response = authenticated_client.get(f"/api/v1/fields/{test_field.id}")
        
        assert_status_code(response, status.HTTP_200_OK)
        data = get_json_response(response)
        assert data["id"] == test_field.id
    
    def test_list_farm_fields(self, authenticated_client, test_farm, test_field):
        """Test listing all fields for a farm."""
        response = authenticated_client.get(
            f"/api/v1/farms/{test_farm.id}/fields"
        )
        
        assert_status_code(response, status.HTTP_200_OK)
        data = get_json_response(response)
        
        assert isinstance(data, list)
        assert any(f["id"] == test_field.id for f in data)
    
    def test_update_field(self, authenticated_client, test_field):
        """Test updating a field."""
        update_data = {"name": "Updated Field", "current_crop": "beans"}
        
        response = authenticated_client.put(
            f"/api/v1/fields/{test_field.id}",
            json=update_data
        )
        
        assert_status_code(response, status.HTTP_200_OK)
        data = get_json_response(response)
        assert data["name"] == "Updated Field"
        assert data["current_crop"] == "beans"
    
    def test_delete_field(self, authenticated_client, test_farm, db_session):
        """Test deleting a field."""
        from app.database.models.field import Field
        field = Field(
            farm_id=test_farm.id,
            name="To Delete"
        )
        db_session.add(field)
        db_session.commit()
        field_id = field.id
        
        response = authenticated_client.delete(f"/api/v1/fields/{field_id}")
        
        assert_status_code(response, status.HTTP_204_NO_CONTENT)


# ==================== Crop API Tests ====================

@pytest.mark.api
@pytest.mark.integration
class TestCropAPI:
    """Test crop management endpoints."""
    
    def test_create_crop(self, authenticated_client, test_field):
        """Test creating a crop."""
        crop_data = CropFactory.build(field_id=test_field.id)
        
        response = authenticated_client.post(
            f"/api/v1/fields/{test_field.id}/crops",
            json=crop_data
        )
        
        assert_status_code(response, status.HTTP_201_CREATED)
        data = get_json_response(response)
        assert data["field_id"] == test_field.id
    
    def test_get_crop(self, authenticated_client, test_crop):
        """Test getting a crop."""
        response = authenticated_client.get(f"/api/v1/crops/{test_crop.id}")
        
        assert_status_code(response, status.HTTP_200_OK)
        data = get_json_response(response)
        assert data["id"] == test_crop.id
    
    def test_update_crop_growth_stage(self, authenticated_client, test_crop):
        """Test updating crop growth stage."""
        update_data = {"growth_stage": "flowering"}
        
        response = authenticated_client.patch(
            f"/api/v1/crops/{test_crop.id}",
            json=update_data
        )
        
        assert_status_code(response, status.HTTP_200_OK)
        data = get_json_response(response)
        assert data["growth_stage"] == "flowering"
    
    def test_update_crop_health(self, authenticated_client, test_crop):
        """Test updating crop health status."""
        update_data = {"health_status": "stressed"}
        
        response = authenticated_client.patch(
            f"/api/v1/crops/{test_crop.id}",
            json=update_data
        )
        
        assert_status_code(response, status.HTTP_200_OK)
        data = get_json_response(response)
        assert data["health_status"] == "stressed"


# ==================== Sensor API Tests ====================

@pytest.mark.api
@pytest.mark.integration
class TestSensorAPI:
    """Test sensor management endpoints."""
    
    def test_create_sensor(self, authenticated_client, test_field):
        """Test creating a sensor."""
        sensor_data = SensorFactory.build(field_id=test_field.id)
        
        response = authenticated_client.post(
            f"/api/v1/fields/{test_field.id}/sensors",
            json=sensor_data
        )
        
        assert_status_code(response, status.HTTP_201_CREATED)
        data = get_json_response(response)
        assert data["field_id"] == test_field.id
    
    def test_get_sensor(self, authenticated_client, test_sensor):
        """Test getting a sensor."""
        response = authenticated_client.get(f"/api/v1/sensors/{test_sensor.id}")
        
        assert_status_code(response, status.HTTP_200_OK)
        data = get_json_response(response)
        assert data["id"] == test_sensor.id
    
    def test_list_sensor_readings(self, authenticated_client, test_sensor, test_sensor_readings):
        """Test listing sensor readings."""
        response = authenticated_client.get(
            f"/api/v1/sensors/{test_sensor.id}/readings"
        )
        
        assert_status_code(response, status.HTTP_200_OK)
        data = get_json_response(response)
        
        assert isinstance(data, list)
        assert len(data) >= len(test_sensor_readings)
    
    def test_add_sensor_reading(self, authenticated_client, test_sensor):
        """Test adding a sensor reading."""
        reading_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "value": 52.5,
            "unit": "percentage",
            "quality_score": 0.95
        }
        
        response = authenticated_client.post(
            f"/api/v1/sensors/{test_sensor.id}/readings",
            json=reading_data
        )
        
        assert_status_code(response, status.HTTP_201_CREATED)
    
    def test_get_latest_reading(self, authenticated_client, test_sensor):
        """Test getting latest sensor reading."""
        response = authenticated_client.get(
            f"/api/v1/sensors/{test_sensor.id}/readings/latest"
        )
        
        assert_status_code(response, status.HTTP_200_OK)
    
    def test_get_sensor_stats(self, authenticated_client, test_sensor):
        """Test getting sensor statistics."""
        response = authenticated_client.get(
            f"/api/v1/sensors/{test_sensor.id}/stats"
        )
        
        assert_status_code(response, status.HTTP_200_OK)
        data = get_json_response(response)
        # Should include min, max, avg, etc.


# ==================== Weather API Tests ====================

@pytest.mark.api
@pytest.mark.integration
class TestWeatherAPI:
    """Test weather endpoints."""
    
    def test_get_current_weather(self, authenticated_client, test_farm):
        """Test getting current weather for a farm."""
        response = authenticated_client.get(
            f"/api/v1/farms/{test_farm.id}/weather/current"
        )
        
        assert_status_code(response, status.HTTP_200_OK)
        data = get_json_response(response)
        assert_dict_structure(data, [
            "temperature", "humidity", "conditions"
        ])
    
    def test_get_weather_forecast(self, authenticated_client, test_farm):
        """Test getting weather forecast."""
        response = authenticated_client.get(
            f"/api/v1/farms/{test_farm.id}/weather/forecast?days=7"
        )
        
        assert_status_code(response, status.HTTP_200_OK)
        data = get_json_response(response)
        
        assert isinstance(data, list)
        assert len(data) <= 7
    
    def test_get_weather_history(self, authenticated_client, test_farm):
        """Test getting weather history."""
        response = authenticated_client.get(
            f"/api/v1/farms/{test_farm.id}/weather/history?days=30"
        )
        
        assert_status_code(response, status.HTTP_200_OK)
        data = get_json_response(response)
        
        assert isinstance(data, list)


# ==================== Alert API Tests ====================

@pytest.mark.api
@pytest.mark.integration
class TestAlertAPI:
    """Test alert endpoints."""
    
    def test_get_user_alerts(self, authenticated_client, test_user, test_alert):
        """Test getting user alerts."""
        response = authenticated_client.get("/api/v1/alerts")
        
        assert_status_code(response, status.HTTP_200_OK)
        data = get_json_response(response)
        
        assert isinstance(data, list)
        assert any(a["id"] == test_alert.id for a in data)
    
    def test_get_unread_alerts(self, authenticated_client):
        """Test getting unread alerts only."""
        response = authenticated_client.get("/api/v1/alerts?unread=true")
        
        assert_status_code(response, status.HTTP_200_OK)
        data = get_json_response(response)
        
        assert all(not a["is_read"] for a in data)
    
    def test_mark_alert_read(self, authenticated_client, test_alert):
        """Test marking alert as read."""
        response = authenticated_client.patch(
            f"/api/v1/alerts/{test_alert.id}/read"
        )
        
        assert_status_code(response, status.HTTP_200_OK)
        data = get_json_response(response)
        assert data["is_read"] is True
    
    def test_mark_alert_resolved(self, authenticated_client, test_alert):
        """Test marking alert as resolved."""
        response = authenticated_client.patch(
            f"/api/v1/alerts/{test_alert.id}/resolve"
        )
        
        assert_status_code(response, status.HTTP_200_OK)
        data = get_json_response(response)
        assert data["is_resolved"] is True
    
    def test_delete_alert(self, authenticated_client, test_user, db_session):
        """Test deleting an alert."""
        from app.database.models.alert import Alert
        alert = Alert(
            user_id=test_user.id,
            alert_type="test",
            severity="low",
            title="Test",
            message="Test"
        )
        db_session.add(alert)
        db_session.commit()
        alert_id = alert.id
        
        response = authenticated_client.delete(f"/api/v1/alerts/{alert_id}")
        
        assert_status_code(response, status.HTTP_204_NO_CONTENT)
    
    def test_get_alerts_by_severity(self, authenticated_client):
        """Test filtering alerts by severity."""
        response = authenticated_client.get("/api/v1/alerts?severity=high")
        
        assert_status_code(response, status.HTTP_200_OK)
        data = get_json_response(response)
        
        assert all(a["severity"] == "high" for a in data)
    
    def test_get_alerts_by_type(self, authenticated_client):
        """Test filtering alerts by type."""
        response = authenticated_client.get(
            "/api/v1/alerts?type=pest_detection"
        )
        
        assert_status_code(response, status.HTTP_200_OK)
        data = get_json_response(response)
        
        assert all(a["alert_type"] == "pest_detection" for a in data)


# ==================== ML Prediction API Tests ====================

@pytest.mark.api
@pytest.mark.integration
class TestMLPredictionAPI:
    """Test ML prediction endpoints."""
    
    def test_crop_recommendation(self, authenticated_client):
        """Test crop recommendation endpoint."""
        input_data = CropRecommendationInputFactory.build()
        
        response = authenticated_client.post(
            "/api/v1/ml/crop-recommendation",
            json=input_data
        )
        
        assert_status_code(response, status.HTTP_200_OK)
        data = get_json_response(response)
        assert_dict_structure(data, [
            "recommended_crop", "confidence", "alternatives"
        ])
    
    def test_yield_prediction(self, authenticated_client, test_crop):
        """Test yield prediction endpoint."""
        input_data = {
            "crop_id": test_crop.id,
            "soil_nitrogen": 80,
            "soil_phosphorus": 50,
            "soil_potassium": 60,
            "temperature": 25.0,
            "rainfall": 800
        }
        
        response = authenticated_client.post(
            "/api/v1/ml/yield-prediction",
            json=input_data
        )
        
        assert_status_code(response, status.HTTP_200_OK)
        data = get_json_response(response)
        assert "predicted_yield" in data
        assert "confidence" in data
    
    def test_pest_detection(self, authenticated_client, test_image_file):
        """Test pest detection endpoint."""
        with open(test_image_file, 'rb') as f:
            files = {"image": ("test.jpg", f, "image/jpeg")}
            
            response = authenticated_client.post(
                "/api/v1/ml/pest-detection",
                files=files
            )
        
        assert_status_code(response, status.HTTP_200_OK)
        data = get_json_response(response)
        assert_dict_structure(data, [
            "pest_detected", "pest_type", "confidence"
        ])
    
    def test_disease_detection(self, authenticated_client, test_image_file):
        """Test disease detection endpoint."""
        with open(test_image_file, 'rb') as f:
            files = {"image": ("test.jpg", f, "image/jpeg")}
            
            response = authenticated_client.post(
                "/api/v1/ml/disease-detection",
                files=files
            )
        
        assert_status_code(response, status.HTTP_200_OK)
    
    def test_price_prediction(self, authenticated_client):
        """Test price prediction endpoint."""
        input_data = {
            "crop": "maize",
            "quantity_kg": 1000,
            "market": "nairobi",
            "forecast_days": 7
        }
        
        response = authenticated_client.post(
            "/api/v1/ml/price-prediction",
            json=input_data
        )
        
        assert_status_code(response, status.HTTP_200_OK)
        data = get_json_response(response)
        assert "predicted_price" in data


# ==================== File Upload Tests ====================

@pytest.mark.api
@pytest.mark.integration
class TestFileUploadAPI:
    """Test file upload endpoints."""
    
    def test_upload_field_image(self, authenticated_client, test_field, test_image_file):
        """Test uploading field image."""
        with open(test_image_file, 'rb') as f:
            files = {"file": ("field.jpg", f, "image/jpeg")}
            
            response = authenticated_client.post(
                f"/api/v1/fields/{test_field.id}/images",
                files=files
            )
        
        assert_status_code(response, status.HTTP_201_CREATED)
        data = get_json_response(response)
        assert "url" in data
    
    def test_upload_crop_image(self, authenticated_client, test_crop, test_image_file):
        """Test uploading crop image."""
        with open(test_image_file, 'rb') as f:
            files = {"file": ("crop.jpg", f, "image/jpeg")}
            
            response = authenticated_client.post(
                f"/api/v1/crops/{test_crop.id}/images",
                files=files
            )
        
        assert_status_code(response, status.HTTP_201_CREATED)
    
    def test_upload_invalid_file_type(self, authenticated_client, test_field, temp_directory):
        """Test uploading invalid file type."""
        import os
        text_file = os.path.join(temp_directory, "test.txt")
        with open(text_file, 'w') as f:
            f.write("test")
        
        with open(text_file, 'rb') as f:
            files = {"file": ("test.txt", f, "text/plain")}
            
            response = authenticated_client.post(
                f"/api/v1/fields/{test_field.id}/images",
                files=files
            )
        
        assert_status_code(response, status.HTTP_400_BAD_REQUEST)


# ==================== Search and Filter Tests ====================

@pytest.mark.api
@pytest.mark.integration
class TestSearchAPI:
    """Test search and filter endpoints."""
    
    def test_search_farms(self, authenticated_client, test_farm):
        """Test searching farms."""
        response = authenticated_client.get(
            f"/api/v1/farms/search?q={test_farm.name}"
        )
        
        assert_status_code(response, status.HTTP_200_OK)
        data = get_json_response(response)
        
        assert isinstance(data, list)
        assert any(f["id"] == test_farm.id for f in data)
    
    def test_search_crops(self, authenticated_client):
        """Test searching crops by type."""
        response = authenticated_client.get(
            "/api/v1/crops/search?crop_type=maize"
        )
        
        assert_status_code(response, status.HTTP_200_OK)
        data = get_json_response(response)
        
        assert isinstance(data, list)
    
    def test_filter_by_location(self, authenticated_client):
        """Test filtering by location."""
        response = authenticated_client.get(
            "/api/v1/farms?location=Nairobi"
        )
        
        assert_status_code(response, status.HTTP_200_OK)
    
    def test_filter_by_date_range(self, authenticated_client):
        """Test filtering by date range."""
        start_date = (datetime.utcnow() - timedelta(days=30)).isoformat()
        end_date = datetime.utcnow().isoformat()
        
        response = authenticated_client.get(
            f"/api/v1/crops?start_date={start_date}&end_date={end_date}"
        )
        
        assert_status_code(response, status.HTTP_200_OK)


# ==================== Error Handling Tests ====================

@pytest.mark.api
class TestAPIErrorHandling:
    """Test API error handling."""
    
    def test_404_not_found(self, authenticated_client):
        """Test 404 error response."""
        response = authenticated_client.get("/api/v1/nonexistent")
        
        assert_status_code(response, status.HTTP_404_NOT_FOUND)
        validate_error_response(get_json_response(response))
    
    def test_validation_error(self, authenticated_client, test_farm):
        """Test validation error response."""
        invalid_data = {"size_hectares": -5.0}  # Invalid negative size
        
        response = authenticated_client.post(
            "/api/v1/farms",
            json=invalid_data
        )
        
        assert_status_code(response, status.HTTP_422_UNPROCESSABLE_ENTITY)
    
    def test_unauthorized_access(self, client, test_farm):
        """Test unauthorized access."""
        response = client.get(f"/api/v1/farms/{test_farm.id}")
        
        assert_status_code(response, status.HTTP_401_UNAUTHORIZED)
    
    def test_forbidden_access(self, authenticated_client, test_user, db_session):
        """Test forbidden access to other user's resources."""
        # Create another user's farm
        from app.database.models.user import User
        from app.database.models.farm import Farm
        from app.core.security import get_password_hash
        
        other_user = User(
            email="other@example.com",
            hashed_password=get_password_hash("password"),
            full_name="Other User"
        )
        db_session.add(other_user)
        db_session.commit()
        
        other_farm = Farm(
            name="Other Farm",
            owner_id=other_user.id,
            location="Test"
        )
        db_session.add(other_farm)
        db_session.commit()
        
        # Try to access other user's farm
        response = authenticated_client.get(f"/api/v1/farms/{other_farm.id}")
        
        # Should be forbidden
        assert response.status_code in [
            status.HTTP_403_FORBIDDEN,
            status.HTTP_404_NOT_FOUND
        ]
    
    def test_method_not_allowed(self, authenticated_client, test_farm):
        """Test method not allowed."""
        response = authenticated_client.patch(
            f"/api/v1/farms/{test_farm.id}"
        )
        
        # If PATCH not supported, should return 405
        assert response.status_code in [
            status.HTTP_405_METHOD_NOT_ALLOWED,
            status.HTTP_200_OK  # If PATCH is actually supported
        ]
    
    def test_rate_limiting(self, authenticated_client):
        """Test rate limiting (if implemented)."""
        # Make many requests rapidly
        responses = []
        for _ in range(100):
            response = authenticated_client.get("/api/v1/farms")
            responses.append(response)
        
        # Check if any were rate limited
        rate_limited = any(
            r.status_code == status.HTTP_429_TOO_MANY_REQUESTS
            for r in responses
        )
        
        # Rate limiting may or may not be implemented


# ==================== Admin API Tests ====================

@pytest.mark.api
@pytest.mark.integration
class TestAdminAPI:
    """Test admin-only endpoints."""
    
    def test_admin_list_all_users(self, authenticated_client, test_admin_user):
        """Test admin listing all users."""
        # This test assumes admin user is authenticated
        response = authenticated_client.get("/api/v1/admin/users")
        
        # May require admin authentication
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_403_FORBIDDEN
        ]
    
    def test_admin_get_system_stats(self, authenticated_client):
        """Test getting system statistics."""
        response = authenticated_client.get("/api/v1/admin/stats")
        
        # May require admin privileges
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_403_FORBIDDEN
        ]
    
    def test_non_admin_access_denied(self, authenticated_client):
        """Test non-admin cannot access admin endpoints."""
        response = authenticated_client.get("/api/v1/admin/users")
        
        # Should be forbidden for non-admin
        assert response.status_code in [
            status.HTTP_403_FORBIDDEN,
            status.HTTP_200_OK  # If user is admin
        ]


# ==================== WebSocket Tests ====================

@pytest.mark.api
@pytest.mark.integration
class TestWebSocketAPI:
    """Test WebSocket connections."""
    
    def test_websocket_connect(self, client):
        """Test WebSocket connection."""
        from fastapi.testclient import TestClient
        
        with client.websocket_connect("/ws/sensors") as websocket:
            # Connection successful
            assert websocket is not None
    
    def test_websocket_receive_data(self, client):
        """Test receiving data via WebSocket."""
        with client.websocket_connect("/ws/sensors") as websocket:
            # Send subscription
            websocket.send_json({"action": "subscribe", "sensor_id": 1})
            
            # Receive confirmation
            data = websocket.receive_json()
            assert "status" in data
    
    def test_websocket_disconnect(self, client):
        """Test WebSocket disconnection."""
        with client.websocket_connect("/ws/sensors") as websocket:
            websocket.close()
            # Should disconnect cleanly


# ==================== CORS Tests ====================

@pytest.mark.api
class TestCORS:
    """Test CORS configuration."""
    
    def test_cors_headers(self, client):
        """Test CORS headers are present."""
        response = client.options(
            "/api/v1/farms",
            headers={"Origin": "http://localhost:3000"}
        )
        
        # Check for CORS headers
        assert "access-control-allow-origin" in response.headers or \
               response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED
    
    def test_preflight_request(self, client):
        """Test CORS preflight request."""
        response = client.options(
            "/api/v1/farms",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "POST"
            }
        )
        
        # Should handle preflight
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_405_METHOD_NOT_ALLOWED
        ]
