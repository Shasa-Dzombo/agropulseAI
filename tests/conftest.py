"""
Pytest Configuration and Fixtures

Central configuration for all tests with shared fixtures,
database setup, API client configuration, and test utilities.
"""

import pytest
import asyncio
from typing import Generator, AsyncGenerator
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient
from datetime import datetime, timedelta
import tempfile
import shutil
import os

# Import application components
from app.database.base import Base
from app.database.session import get_db
from app.api.main import app
from app.core.config import settings
from app.core.security import create_access_token


# ==================== Database Fixtures ====================

@pytest.fixture(scope="session")
def test_db_engine():
    """
    Create test database engine with in-memory SQLite.
    Session-scoped to share across all tests.
    """
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    
    # Create all tables
    Base.metadata.create_all(bind=engine)
    
    yield engine
    
    # Cleanup
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture(scope="function")
def db_session(test_db_engine) -> Generator[Session, None, None]:
    """
    Create a new database session for each test.
    Automatically rolls back changes after test completion.
    """
    connection = test_db_engine.connect()
    transaction = connection.begin()
    
    TestSessionLocal = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=connection
    )
    session = TestSessionLocal()
    
    yield session
    
    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture(scope="function")
def override_get_db(db_session):
    """
    Override the get_db dependency with test database session.
    """
    def _get_test_db():
        try:
            yield db_session
        finally:
            pass
    
    app.dependency_overrides[get_db] = _get_test_db
    yield
    app.dependency_overrides.clear()


# ==================== API Client Fixtures ====================

@pytest.fixture(scope="function")
def client(override_get_db) -> Generator[TestClient, None, None]:
    """
    FastAPI test client for API testing.
    """
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(scope="function")
def authenticated_client(client, test_user) -> TestClient:
    """
    Authenticated test client with valid JWT token.
    """
    access_token = create_access_token(
        data={"sub": test_user.email},
        expires_delta=timedelta(minutes=30)
    )
    client.headers = {
        **client.headers,
        "Authorization": f"Bearer {access_token}"
    }
    return client


# ==================== User Fixtures ====================

@pytest.fixture(scope="function")
def test_user(db_session):
    """
    Create a test user.
    """
    from app.database.models.user import User
    from app.core.security import get_password_hash
    
    user = User(
        email="testuser@example.com",
        hashed_password=get_password_hash("testpassword123"),
        full_name="Test User",
        is_active=True,
        is_verified=True,
        phone_number="+254712345678",
        role="farmer"
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    
    return user


@pytest.fixture(scope="function")
def test_admin_user(db_session):
    """
    Create a test admin user.
    """
    from app.database.models.user import User
    from app.core.security import get_password_hash
    
    user = User(
        email="admin@example.com",
        hashed_password=get_password_hash("adminpass123"),
        full_name="Admin User",
        is_active=True,
        is_verified=True,
        phone_number="+254712345679",
        role="admin",
        is_superuser=True
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    
    return user


@pytest.fixture(scope="function")
def test_agronomist_user(db_session):
    """
    Create a test agronomist user.
    """
    from app.database.models.user import User
    from app.core.security import get_password_hash
    
    user = User(
        email="agronomist@example.com",
        hashed_password=get_password_hash("agropass123"),
        full_name="Agronomist User",
        is_active=True,
        is_verified=True,
        phone_number="+254712345677",
        role="agronomist",
        specialization="crop_management"
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    
    return user


# ==================== Farm Fixtures ====================

@pytest.fixture(scope="function")
def test_farm(db_session, test_user):
    """
    Create a test farm.
    """
    from app.database.models.farm import Farm
    
    farm = Farm(
        name="Test Farm",
        owner_id=test_user.id,
        location="Test Location, Kenya",
        size_hectares=5.0,
        latitude=-1.286389,
        longitude=36.817223,
        soil_type="loam",
        water_source="borehole",
        is_active=True
    )
    db_session.add(farm)
    db_session.commit()
    db_session.refresh(farm)
    
    return farm


@pytest.fixture(scope="function")
def test_field(db_session, test_farm):
    """
    Create a test field.
    """
    from app.database.models.field import Field
    
    field = Field(
        farm_id=test_farm.id,
        name="Test Field 1",
        size_hectares=2.0,
        soil_type="sandy_loam",
        current_crop="maize",
        planting_date=datetime.utcnow() - timedelta(days=30),
        expected_harvest_date=datetime.utcnow() + timedelta(days=90),
        is_active=True
    )
    db_session.add(field)
    db_session.commit()
    db_session.refresh(field)
    
    return field


# ==================== Crop Fixtures ====================

@pytest.fixture(scope="function")
def test_crop(db_session, test_field):
    """
    Create a test crop record.
    """
    from app.database.models.crop import Crop
    
    crop = Crop(
        field_id=test_field.id,
        crop_type="maize",
        variety="H614",
        planting_date=datetime.utcnow() - timedelta(days=30),
        expected_harvest_date=datetime.utcnow() + timedelta(days=90),
        expected_yield_kg=4000,
        growth_stage="vegetative",
        health_status="healthy",
        is_active=True
    )
    db_session.add(crop)
    db_session.commit()
    db_session.refresh(crop)
    
    return crop


# ==================== Sensor Fixtures ====================

@pytest.fixture(scope="function")
def test_sensor(db_session, test_field):
    """
    Create a test sensor.
    """
    from app.database.models.sensor import Sensor
    
    sensor = Sensor(
        field_id=test_field.id,
        sensor_type="soil_moisture",
        sensor_id="SMS-001",
        location="center",
        is_active=True,
        installation_date=datetime.utcnow() - timedelta(days=60)
    )
    db_session.add(sensor)
    db_session.commit()
    db_session.refresh(sensor)
    
    return sensor


@pytest.fixture(scope="function")
def test_sensor_readings(db_session, test_sensor):
    """
    Create test sensor readings.
    """
    from app.database.models.sensor import SensorReading
    
    readings = []
    for i in range(10):
        reading = SensorReading(
            sensor_id=test_sensor.id,
            timestamp=datetime.utcnow() - timedelta(hours=i),
            value=45.0 + i * 2,
            unit="percentage",
            quality_score=0.95
        )
        db_session.add(reading)
        readings.append(reading)
    
    db_session.commit()
    
    return readings


# ==================== Alert Fixtures ====================

@pytest.fixture(scope="function")
def test_alert(db_session, test_user, test_farm):
    """
    Create a test alert.
    """
    from app.database.models.alert import Alert
    
    alert = Alert(
        user_id=test_user.id,
        farm_id=test_farm.id,
        alert_type="pest_detection",
        severity="medium",
        title="Pest Detected",
        message="Fall armyworm detected in maize field",
        is_read=False,
        is_resolved=False
    )
    db_session.add(alert)
    db_session.commit()
    db_session.refresh(alert)
    
    return alert


# ==================== Weather Fixtures ====================

@pytest.fixture(scope="function")
def test_weather_data(db_session, test_farm):
    """
    Create test weather data.
    """
    from app.database.models.weather import WeatherData
    
    weather = WeatherData(
        farm_id=test_farm.id,
        timestamp=datetime.utcnow(),
        temperature=25.5,
        humidity=65.0,
        rainfall=0.0,
        wind_speed=10.5,
        pressure=1013.25,
        conditions="partly_cloudy"
    )
    db_session.add(weather)
    db_session.commit()
    db_session.refresh(weather)
    
    return weather


# ==================== ML Model Fixtures ====================

@pytest.fixture(scope="function")
def test_ml_model(db_session):
    """
    Create a test ML model record.
    """
    from app.database.models.ml_model import MLModel
    
    model = MLModel(
        name="Test Crop Recommender",
        model_type="crop_recommendation",
        version="1.0.0",
        accuracy=0.85,
        precision=0.82,
        recall=0.88,
        f1_score=0.85,
        is_active=True,
        training_date=datetime.utcnow() - timedelta(days=7)
    )
    db_session.add(model)
    db_session.commit()
    db_session.refresh(model)
    
    return model


# ==================== File System Fixtures ====================

@pytest.fixture(scope="function")
def temp_directory():
    """
    Create a temporary directory for file operations.
    Automatically cleaned up after test.
    """
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture(scope="function")
def test_image_file(temp_directory):
    """
    Create a test image file for image processing tests.
    """
    from PIL import Image
    import numpy as np
    
    # Create a simple test image
    img_array = np.random.randint(0, 255, (224, 224, 3), dtype=np.uint8)
    img = Image.fromarray(img_array)
    
    file_path = os.path.join(temp_directory, "test_image.jpg")
    img.save(file_path)
    
    return file_path


# ==================== Async Fixtures ====================

@pytest.fixture(scope="session")
def event_loop():
    """
    Create an event loop for async tests.
    """
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# ==================== Mock Data Fixtures ====================

@pytest.fixture(scope="function")
def mock_weather_api_response():
    """
    Mock weather API response data.
    """
    return {
        "location": {
            "name": "Nairobi",
            "country": "Kenya",
            "lat": -1.286389,
            "lon": 36.817223
        },
        "current": {
            "temp_c": 23.5,
            "humidity": 65,
            "wind_kph": 12.5,
            "pressure_mb": 1013.25,
            "condition": {
                "text": "Partly cloudy"
            },
            "precip_mm": 0.0
        },
        "forecast": {
            "forecastday": [
                {
                    "date": "2025-11-01",
                    "day": {
                        "maxtemp_c": 28.0,
                        "mintemp_c": 18.0,
                        "avgtemp_c": 23.0,
                        "totalprecip_mm": 2.5,
                        "avghumidity": 70
                    }
                }
            ]
        }
    }


@pytest.fixture(scope="function")
def mock_crop_recommendation_data():
    """
    Mock crop recommendation input data.
    """
    return {
        "nitrogen": 80,
        "phosphorus": 45,
        "potassium": 60,
        "temperature": 25.5,
        "humidity": 70.0,
        "ph": 6.5,
        "rainfall": 800,
        "location": "Nairobi",
        "soil_type": "loam",
        "farm_size_ha": 5.0
    }


@pytest.fixture(scope="function")
def mock_pest_detection_result():
    """
    Mock pest detection result.
    """
    return {
        "pest_detected": True,
        "pest_type": "fall_armyworm",
        "confidence": 0.92,
        "severity": "medium",
        "affected_area_pct": 15.0,
        "recommendations": [
            "Apply neem-based pesticide",
            "Scout fields daily",
            "Remove and destroy infected plants"
        ]
    }


# ==================== Parametrized Test Data ====================

@pytest.fixture(params=["maize", "beans", "potatoes", "tomatoes"])
def crop_types(request):
    """
    Parametrized fixture for different crop types.
    """
    return request.param


@pytest.fixture(params=["loam", "clay", "sand", "sandy_loam"])
def soil_types(request):
    """
    Parametrized fixture for different soil types.
    """
    return request.param


@pytest.fixture(params=["low", "medium", "high", "critical"])
def severity_levels(request):
    """
    Parametrized fixture for severity levels.
    """
    return request.param


# ==================== Performance Testing Fixtures ====================

@pytest.fixture(scope="function")
def performance_timer():
    """
    Timer fixture for performance testing.
    """
    import time
    
    class Timer:
        def __init__(self):
            self.start_time = None
            self.end_time = None
        
        def start(self):
            self.start_time = time.time()
        
        def stop(self):
            self.end_time = time.time()
        
        def elapsed(self):
            if self.start_time and self.end_time:
                return self.end_time - self.start_time
            return None
    
    return Timer()


# ==================== Test Markers ====================

def pytest_configure(config):
    """
    Register custom pytest markers.
    """
    config.addinivalue_line(
        "markers", "unit: Unit tests for individual components"
    )
    config.addinivalue_line(
        "markers", "integration: Integration tests for component interactions"
    )
    config.addinivalue_line(
        "markers", "e2e: End-to-end tests for complete workflows"
    )
    config.addinivalue_line(
        "markers", "slow: Tests that take significant time to run"
    )
    config.addinivalue_line(
        "markers", "performance: Performance and load tests"
    )
    config.addinivalue_line(
        "markers", "ml: Machine learning model tests"
    )
    config.addinivalue_line(
        "markers", "api: API endpoint tests"
    )
    config.addinivalue_line(
        "markers", "database: Database operation tests"
    )


# ==================== Test Utilities ====================

@pytest.fixture(scope="function")
def assert_response_schema():
    """
    Utility to assert API response schema.
    """
    def _assert_schema(response_data, expected_keys):
        assert isinstance(response_data, dict)
        for key in expected_keys:
            assert key in response_data, f"Key '{key}' not found in response"
    
    return _assert_schema


@pytest.fixture(scope="function")
def assert_datetime_recent():
    """
    Utility to assert datetime is recent (within last minute).
    """
    def _assert_recent(dt_string, max_seconds=60):
        dt = datetime.fromisoformat(dt_string.replace('Z', '+00:00'))
        now = datetime.utcnow()
        diff = (now - dt).total_seconds()
        assert diff < max_seconds, f"Timestamp not recent: {diff} seconds old"
    
    return _assert_recent
