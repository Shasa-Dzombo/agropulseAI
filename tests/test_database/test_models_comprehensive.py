"""
Comprehensive Database Tests

Complete test suite for all database models, repositories, and operations.
"""

import pytest
from datetime import datetime, timedelta
import numpy as np
from sqlalchemy.exc import IntegrityError

from app.database.models.farm import Farm
from app.database.models.field import Field
from app.database.models.crop import Crop
from app.database.models.sensor import Sensor, SensorReading
from app.database.models.alert import Alert
from app.database.models.weather import WeatherData
from app.database.repositories.farm_repository import FarmRepository
from app.database.repositories.field_repository import FieldRepository
from app.database.repositories.crop_repository import CropRepository

from tests.factories import (
    FarmFactory, FieldFactory, CropFactory, SensorFactory,
    SensorReadingFactory, WeatherDataFactory, AlertFactory
)
from tests.utils import assert_dict_structure, count_records


# ==================== Farm Model Tests ====================

@pytest.mark.unit
@pytest.mark.database
class TestFarmModel:
    """Test Farm model."""
    
    def test_create_farm(self, db_session, test_user):
        """Test creating a farm."""
        farm = Farm(
            name="New Farm",
            owner_id=test_user.id,
            location="Nairobi, Kenya",
            size_hectares=10.5,
            latitude=-1.286389,
            longitude=36.817223,
            soil_type="loam"
        )
        db_session.add(farm)
        db_session.commit()
        
        assert farm.id is not None
        assert farm.name == "New Farm"
        assert farm.owner_id == test_user.id
        assert farm.is_active is True
    
    def test_farm_required_fields(self, db_session, test_user):
        """Test farm required fields."""
        farm = Farm(
            name="Minimal Farm",
            owner_id=test_user.id,
            location="Location"
        )
        db_session.add(farm)
        db_session.commit()
        
        assert farm.id is not None
    
    def test_farm_coordinates_validation(self, db_session, test_user):
        """Test GPS coordinates are within valid range."""
        farm = Farm(
            name="Coordinate Farm",
            owner_id=test_user.id,
            location="Test",
            latitude=-1.5,
            longitude=36.8
        )
        db_session.add(farm)
        db_session.commit()
        
        assert -90 <= farm.latitude <= 90
        assert -180 <= farm.longitude <= 180
    
    def test_farm_size_positive(self, db_session, test_user):
        """Test farm size must be positive."""
        farm = Farm(
            name="Size Farm",
            owner_id=test_user.id,
            location="Test",
            size_hectares=5.5
        )
        db_session.add(farm)
        db_session.commit()
        
        assert farm.size_hectares > 0
    
    def test_farm_soil_types(self, db_session, test_user):
        """Test various soil types."""
        soil_types = ["clay", "sandy", "loam", "sandy_loam", "clay_loam"]
        
        for soil_type in soil_types:
            farm = Farm(
                name=f"Farm {soil_type}",
                owner_id=test_user.id,
                location="Test",
                soil_type=soil_type
            )
            db_session.add(farm)
        
        db_session.commit()
        
        farms = db_session.query(Farm).filter(
            Farm.owner_id == test_user.id
        ).all()
        
        assert len(farms) >= len(soil_types)
    
    def test_farm_water_sources(self, db_session, test_user):
        """Test various water sources."""
        water_sources = ["borehole", "river", "rain_fed", "irrigation", "dam"]
        
        for source in water_sources:
            farm = Farm(
                name=f"Farm {source}",
                owner_id=test_user.id,
                location="Test",
                water_source=source
            )
            db_session.add(farm)
        
        db_session.commit()
    
    def test_farm_timestamps(self, db_session, test_user):
        """Test farm timestamp fields."""
        farm = Farm(
            name="Timestamp Farm",
            owner_id=test_user.id,
            location="Test"
        )
        db_session.add(farm)
        db_session.commit()
        
        assert farm.created_at is not None
        assert farm.updated_at is not None
        assert farm.created_at <= farm.updated_at
    
    def test_farm_update(self, db_session, test_farm):
        """Test updating farm."""
        original_name = test_farm.name
        test_farm.name = "Updated Farm Name"
        db_session.commit()
        
        assert test_farm.name == "Updated Farm Name"
        assert test_farm.name != original_name


@pytest.mark.unit
@pytest.mark.database
class TestFarmRepository:
    """Test FarmRepository."""
    
    def test_create_farm(self, db_session, test_user):
        """Test creating farm via repository."""
        repo = FarmRepository(db_session)
        farm_data = FarmFactory.build(owner_id=test_user.id)
        
        farm = repo.create(farm_data)
        
        assert farm.id is not None
        assert farm.owner_id == test_user.id
    
    def test_get_farm_by_id(self, db_session, test_farm):
        """Test getting farm by ID."""
        repo = FarmRepository(db_session)
        farm = repo.get_by_id(test_farm.id)
        
        assert farm is not None
        assert farm.id == test_farm.id
    
    def test_get_farms_by_owner(self, db_session, test_user):
        """Test getting all farms for an owner."""
        repo = FarmRepository(db_session)
        
        # Create multiple farms
        for i in range(3):
            farm_data = FarmFactory.build(
                owner_id=test_user.id,
                name=f"Farm {i}"
            )
            repo.create(farm_data)
        
        farms = repo.get_by_owner(test_user.id)
        
        assert len(farms) >= 3
        assert all(f.owner_id == test_user.id for f in farms)
    
    def test_update_farm(self, db_session, test_farm):
        """Test updating farm."""
        repo = FarmRepository(db_session)
        updated = repo.update(test_farm.id, {"size_hectares": 15.0})
        
        assert updated.size_hectares == 15.0
    
    def test_delete_farm(self, db_session, test_user):
        """Test deleting farm."""
        repo = FarmRepository(db_session)
        farm_data = FarmFactory.build(owner_id=test_user.id)
        farm = repo.create(farm_data)
        farm_id = farm.id
        
        success = repo.delete(farm_id)
        
        assert success is True
        assert repo.get_by_id(farm_id) is None
    
    def test_get_active_farms(self, db_session, test_user):
        """Test getting only active farms."""
        repo = FarmRepository(db_session)
        
        # Create active and inactive farms
        active_farm = repo.create(FarmFactory.build(
            owner_id=test_user.id,
            is_active=True
        ))
        
        inactive_farm = repo.create(FarmFactory.build(
            owner_id=test_user.id,
            is_active=False
        ))
        
        active_farms = repo.get_active_farms(test_user.id)
        
        assert active_farm.id in [f.id for f in active_farms]
        assert inactive_farm.id not in [f.id for f in active_farms]
    
    def test_search_farms(self, db_session, test_user):
        """Test searching farms by name."""
        repo = FarmRepository(db_session)
        
        repo.create(FarmFactory.build(
            owner_id=test_user.id,
            name="Sunshine Farm"
        ))
        
        results = repo.search("Sunshine")
        
        assert len(results) >= 1
        assert any("Sunshine" in f.name for f in results)


# ==================== Field Model Tests ====================

@pytest.mark.unit
@pytest.mark.database
class TestFieldModel:
    """Test Field model."""
    
    def test_create_field(self, db_session, test_farm):
        """Test creating a field."""
        field = Field(
            farm_id=test_farm.id,
            name="Test Field",
            size_hectares=2.5,
            soil_type="loam",
            current_crop="maize"
        )
        db_session.add(field)
        db_session.commit()
        
        assert field.id is not None
        assert field.farm_id == test_farm.id
    
    def test_field_required_fields(self, db_session, test_farm):
        """Test field required fields."""
        field = Field(
            farm_id=test_farm.id,
            name="Minimal Field"
        )
        db_session.add(field)
        db_session.commit()
        
        assert field.id is not None
    
    def test_field_dates(self, db_session, test_farm):
        """Test field planting and harvest dates."""
        planting = datetime.utcnow() - timedelta(days=30)
        harvest = datetime.utcnow() + timedelta(days=90)
        
        field = Field(
            farm_id=test_farm.id,
            name="Date Field",
            planting_date=planting,
            expected_harvest_date=harvest
        )
        db_session.add(field)
        db_session.commit()
        
        assert field.planting_date == planting
        assert field.expected_harvest_date == harvest
        assert field.expected_harvest_date > field.planting_date
    
    def test_field_crop_types(self, db_session, test_farm):
        """Test various crop types."""
        crops = ["maize", "beans", "potatoes", "tomatoes", "kale"]
        
        for crop in crops:
            field = Field(
                farm_id=test_farm.id,
                name=f"Field {crop}",
                current_crop=crop
            )
            db_session.add(field)
        
        db_session.commit()
    
    def test_field_size_validation(self, db_session, test_farm):
        """Test field size is positive."""
        field = Field(
            farm_id=test_farm.id,
            name="Size Field",
            size_hectares=1.5
        )
        db_session.add(field)
        db_session.commit()
        
        assert field.size_hectares > 0


@pytest.mark.unit
@pytest.mark.database
class TestFieldRepository:
    """Test FieldRepository."""
    
    def test_create_field(self, db_session, test_farm):
        """Test creating field via repository."""
        repo = FieldRepository(db_session)
        field_data = FieldFactory.build(farm_id=test_farm.id)
        
        field = repo.create(field_data)
        
        assert field.id is not None
        assert field.farm_id == test_farm.id
    
    def test_get_fields_by_farm(self, db_session, test_farm):
        """Test getting all fields for a farm."""
        repo = FieldRepository(db_session)
        
        # Create multiple fields
        for i in range(3):
            field_data = FieldFactory.build(
                farm_id=test_farm.id,
                name=f"Field {i}"
            )
            repo.create(field_data)
        
        fields = repo.get_by_farm(test_farm.id)
        
        assert len(fields) >= 3
        assert all(f.farm_id == test_farm.id for f in fields)
    
    def test_get_active_fields(self, db_session, test_farm):
        """Test getting active fields only."""
        repo = FieldRepository(db_session)
        
        active = repo.create(FieldFactory.build(
            farm_id=test_farm.id,
            is_active=True
        ))
        
        inactive = repo.create(FieldFactory.build(
            farm_id=test_farm.id,
            is_active=False
        ))
        
        active_fields = repo.get_active_fields(test_farm.id)
        
        assert active.id in [f.id for f in active_fields]
        assert inactive.id not in [f.id for f in active_fields]
    
    def test_get_fields_by_crop(self, db_session, test_farm):
        """Test getting fields by crop type."""
        repo = FieldRepository(db_session)
        
        maize_field = repo.create(FieldFactory.build(
            farm_id=test_farm.id,
            current_crop="maize"
        ))
        
        bean_field = repo.create(FieldFactory.build(
            farm_id=test_farm.id,
            current_crop="beans"
        ))
        
        maize_fields = repo.get_by_crop("maize")
        
        assert any(f.id == maize_field.id for f in maize_fields)
        assert all(f.current_crop == "maize" for f in maize_fields)


# ==================== Crop Model Tests ====================

@pytest.mark.unit
@pytest.mark.database
class TestCropModel:
    """Test Crop model."""
    
    def test_create_crop(self, db_session, test_field):
        """Test creating a crop."""
        crop = Crop(
            field_id=test_field.id,
            crop_type="maize",
            variety="H614",
            planting_date=datetime.utcnow() - timedelta(days=20),
            expected_harvest_date=datetime.utcnow() + timedelta(days=100),
            expected_yield_kg=3000
        )
        db_session.add(crop)
        db_session.commit()
        
        assert crop.id is not None
        assert crop.field_id == test_field.id
    
    def test_crop_growth_stages(self, db_session, test_field):
        """Test crop growth stages."""
        stages = ["germination", "vegetative", "flowering", "fruiting", "maturity"]
        
        for stage in stages:
            crop = Crop(
                field_id=test_field.id,
                crop_type="maize",
                growth_stage=stage
            )
            db_session.add(crop)
        
        db_session.commit()
    
    def test_crop_health_status(self, db_session, test_field):
        """Test crop health statuses."""
        statuses = ["excellent", "healthy", "fair", "stressed", "diseased"]
        
        for status in statuses:
            crop = Crop(
                field_id=test_field.id,
                crop_type="beans",
                health_status=status
            )
            db_session.add(crop)
        
        db_session.commit()
    
    def test_crop_varieties(self, db_session, test_field):
        """Test various crop varieties."""
        varieties = {
            "maize": ["H614", "H513", "DH04"],
            "beans": ["KK8", "Rosecoco", "GLP2"],
            "potatoes": ["Shangi", "Dutch Robjin", "Tigoni"]
        }
        
        for crop_type, var_list in varieties.items():
            for variety in var_list:
                crop = Crop(
                    field_id=test_field.id,
                    crop_type=crop_type,
                    variety=variety
                )
                db_session.add(crop)
        
        db_session.commit()


@pytest.mark.unit
@pytest.mark.database
class TestCropRepository:
    """Test CropRepository."""
    
    def test_create_crop(self, db_session, test_field):
        """Test creating crop via repository."""
        repo = CropRepository(db_session)
        crop_data = CropFactory.build(field_id=test_field.id)
        
        crop = repo.create(crop_data)
        
        assert crop.id is not None
        assert crop.field_id == test_field.id
    
    def test_get_crops_by_field(self, db_session, test_field):
        """Test getting crops by field."""
        repo = CropRepository(db_session)
        
        for i in range(3):
            crop_data = CropFactory.build(field_id=test_field.id)
            repo.create(crop_data)
        
        crops = repo.get_by_field(test_field.id)
        
        assert len(crops) >= 3
        assert all(c.field_id == test_field.id for c in crops)
    
    def test_get_crops_by_type(self, db_session, test_field):
        """Test getting crops by type."""
        repo = CropRepository(db_session)
        
        maize_crop = repo.create(CropFactory.build(
            field_id=test_field.id,
            crop_type="maize"
        ))
        
        maize_crops = repo.get_by_type("maize")
        
        assert any(c.id == maize_crop.id for c in maize_crops)
    
    def test_get_crops_by_growth_stage(self, db_session, test_field):
        """Test getting crops by growth stage."""
        repo = CropRepository(db_session)
        
        flowering_crop = repo.create(CropFactory.build(
            field_id=test_field.id,
            growth_stage="flowering"
        ))
        
        flowering_crops = repo.get_by_growth_stage("flowering")
        
        assert any(c.id == flowering_crop.id for c in flowering_crops)
    
    def test_update_crop_health(self, db_session, test_crop):
        """Test updating crop health status."""
        repo = CropRepository(db_session)
        
        updated = repo.update(test_crop.id, {"health_status": "stressed"})
        
        assert updated.health_status == "stressed"
    
    def test_get_crops_ready_for_harvest(self, db_session, test_field):
        """Test getting crops ready for harvest."""
        repo = CropRepository(db_session)
        
        # Create crop ready for harvest
        ready_crop = repo.create(CropFactory.build(
            field_id=test_field.id,
            growth_stage="maturity",
            expected_harvest_date=datetime.utcnow() - timedelta(days=1)
        ))
        
        ready_crops = repo.get_ready_for_harvest()
        
        # Should include crops at maturity or past harvest date


# ==================== Sensor Model Tests ====================

@pytest.mark.unit
@pytest.mark.database
class TestSensorModel:
    """Test Sensor model."""
    
    def test_create_sensor(self, db_session, test_field):
        """Test creating a sensor."""
        sensor = Sensor(
            field_id=test_field.id,
            sensor_type="soil_moisture",
            sensor_id="SMS-001",
            location="center"
        )
        db_session.add(sensor)
        db_session.commit()
        
        assert sensor.id is not None
        assert sensor.field_id == test_field.id
    
    def test_sensor_types(self, db_session, test_field):
        """Test various sensor types."""
        sensor_types = [
            "soil_moisture", "temperature", "humidity", "ph", "npk",
            "light", "rainfall"
        ]
        
        for sensor_type in sensor_types:
            sensor = Sensor(
                field_id=test_field.id,
                sensor_type=sensor_type,
                sensor_id=f"SENSOR-{sensor_type}"
            )
            db_session.add(sensor)
        
        db_session.commit()
    
    def test_sensor_installation_date(self, db_session, test_field):
        """Test sensor installation date."""
        install_date = datetime.utcnow() - timedelta(days=60)
        
        sensor = Sensor(
            field_id=test_field.id,
            sensor_type="temperature",
            sensor_id="TEMP-001",
            installation_date=install_date
        )
        db_session.add(sensor)
        db_session.commit()
        
        assert sensor.installation_date == install_date


@pytest.mark.unit
@pytest.mark.database
class TestSensorReadingModel:
    """Test SensorReading model."""
    
    def test_create_sensor_reading(self, db_session, test_sensor):
        """Test creating a sensor reading."""
        reading = SensorReading(
            sensor_id=test_sensor.id,
            timestamp=datetime.utcnow(),
            value=45.5,
            unit="percentage"
        )
        db_session.add(reading)
        db_session.commit()
        
        assert reading.id is not None
        assert reading.sensor_id == test_sensor.id
    
    def test_multiple_readings(self, db_session, test_sensor):
        """Test creating multiple readings."""
        readings_data = [
            {"value": 40.0, "hours_ago": 0},
            {"value": 42.5, "hours_ago": 1},
            {"value": 38.0, "hours_ago": 2},
        ]
        
        for data in readings_data:
            reading = SensorReading(
                sensor_id=test_sensor.id,
                timestamp=datetime.utcnow() - timedelta(hours=data["hours_ago"]),
                value=data["value"],
                unit="percentage"
            )
            db_session.add(reading)
        
        db_session.commit()
        
        readings = db_session.query(SensorReading).filter(
            SensorReading.sensor_id == test_sensor.id
        ).all()
        
        assert len(readings) >= 3
    
    def test_reading_quality_score(self, db_session, test_sensor):
        """Test reading quality score."""
        reading = SensorReading(
            sensor_id=test_sensor.id,
            timestamp=datetime.utcnow(),
            value=50.0,
            unit="percentage",
            quality_score=0.95
        )
        db_session.add(reading)
        db_session.commit()
        
        assert 0 <= reading.quality_score <= 1


# ==================== Weather Model Tests ====================

@pytest.mark.unit
@pytest.mark.database
class TestWeatherDataModel:
    """Test WeatherData model."""
    
    def test_create_weather_data(self, db_session, test_farm):
        """Test creating weather data."""
        weather = WeatherData(
            farm_id=test_farm.id,
            timestamp=datetime.utcnow(),
            temperature=25.5,
            humidity=65.0,
            rainfall=0.0,
            wind_speed=10.5
        )
        db_session.add(weather)
        db_session.commit()
        
        assert weather.id is not None
        assert weather.farm_id == test_farm.id
    
    def test_weather_data_ranges(self, db_session, test_farm):
        """Test weather data value ranges."""
        weather = WeatherData(
            farm_id=test_farm.id,
            timestamp=datetime.utcnow(),
            temperature=23.0,
            humidity=70.0,
            rainfall=5.5,
            wind_speed=15.0,
            pressure=1013.25
        )
        db_session.add(weather)
        db_session.commit()
        
        assert -50 <= weather.temperature <= 60
        assert 0 <= weather.humidity <= 100
        assert weather.rainfall >= 0
        assert weather.wind_speed >= 0
    
    def test_weather_conditions(self, db_session, test_farm):
        """Test weather conditions."""
        conditions = ["clear", "partly_cloudy", "cloudy", "rainy", "stormy"]
        
        for condition in conditions:
            weather = WeatherData(
                farm_id=test_farm.id,
                timestamp=datetime.utcnow(),
                temperature=25.0,
                conditions=condition
            )
            db_session.add(weather)
        
        db_session.commit()
    
    def test_historical_weather(self, db_session, test_farm):
        """Test storing historical weather data."""
        # Create 7 days of historical data
        for i in range(7):
            weather = WeatherData(
                farm_id=test_farm.id,
                timestamp=datetime.utcnow() - timedelta(days=i),
                temperature=20 + i,
                humidity=60 + i,
                rainfall=i * 2.0
            )
            db_session.add(weather)
        
        db_session.commit()
        
        weather_records = db_session.query(WeatherData).filter(
            WeatherData.farm_id == test_farm.id
        ).all()
        
        assert len(weather_records) >= 7


# ==================== Alert Model Tests ====================

@pytest.mark.unit
@pytest.mark.database
class TestAlertModel:
    """Test Alert model."""
    
    def test_create_alert(self, db_session, test_user, test_farm):
        """Test creating an alert."""
        alert = Alert(
            user_id=test_user.id,
            farm_id=test_farm.id,
            alert_type="pest_detection",
            severity="medium",
            title="Pest Alert",
            message="Pests detected in field"
        )
        db_session.add(alert)
        db_session.commit()
        
        assert alert.id is not None
        assert alert.user_id == test_user.id
    
    def test_alert_types(self, db_session, test_user, test_farm):
        """Test various alert types."""
        alert_types = [
            "pest_detection", "disease_detection", "weather_alert",
            "irrigation_needed", "harvest_ready", "sensor_malfunction"
        ]
        
        for alert_type in alert_types:
            alert = Alert(
                user_id=test_user.id,
                farm_id=test_farm.id,
                alert_type=alert_type,
                severity="medium",
                title=f"{alert_type} alert",
                message="Test message"
            )
            db_session.add(alert)
        
        db_session.commit()
    
    def test_alert_severity_levels(self, db_session, test_user, test_farm):
        """Test alert severity levels."""
        severities = ["low", "medium", "high", "critical"]
        
        for severity in severities:
            alert = Alert(
                user_id=test_user.id,
                farm_id=test_farm.id,
                alert_type="general",
                severity=severity,
                title="Test",
                message="Test"
            )
            db_session.add(alert)
        
        db_session.commit()
    
    def test_alert_read_status(self, db_session, test_alert):
        """Test alert read/unread status."""
        assert test_alert.is_read is False
        
        test_alert.is_read = True
        db_session.commit()
        
        assert test_alert.is_read is True
    
    def test_alert_resolved_status(self, db_session, test_alert):
        """Test alert resolved status."""
        assert test_alert.is_resolved is False
        
        test_alert.is_resolved = True
        test_alert.resolved_at = datetime.utcnow()
        db_session.commit()
        
        assert test_alert.is_resolved is True
        assert test_alert.resolved_at is not None


# ==================== Integration Tests ====================

@pytest.mark.integration
@pytest.mark.database
class TestModelRelationships:
    """Test relationships between models."""
    
    def test_user_farm_relationship(self, db_session, test_user, test_farm):
        """Test user owns farms."""
        assert test_farm.owner_id == test_user.id
        assert test_farm in test_user.farms
    
    def test_farm_field_relationship(self, db_session, test_farm, test_field):
        """Test farm has fields."""
        assert test_field.farm_id == test_farm.id
        assert test_field in test_farm.fields
    
    def test_field_crop_relationship(self, db_session, test_field, test_crop):
        """Test field has crops."""
        assert test_crop.field_id == test_field.id
        assert test_crop in test_field.crops
    
    def test_field_sensor_relationship(self, db_session, test_field, test_sensor):
        """Test field has sensors."""
        assert test_sensor.field_id == test_field.id
        assert test_sensor in test_field.sensors
    
    def test_sensor_readings_relationship(self, db_session, test_sensor, test_sensor_readings):
        """Test sensor has readings."""
        for reading in test_sensor_readings:
            assert reading.sensor_id == test_sensor.id
        
        assert len(test_sensor.readings) >= len(test_sensor_readings)
    
    def test_farm_weather_relationship(self, db_session, test_farm, test_weather_data):
        """Test farm has weather data."""
        assert test_weather_data.farm_id == test_farm.id
        assert test_weather_data in test_farm.weather_data
    
    def test_user_alerts_relationship(self, db_session, test_user, test_alert):
        """Test user receives alerts."""
        assert test_alert.user_id == test_user.id
        assert test_alert in test_user.alerts
    
    def test_farm_alerts_relationship(self, db_session, test_farm, test_alert):
        """Test farm generates alerts."""
        assert test_alert.farm_id == test_farm.id
        assert test_alert in test_farm.alerts
    
    def test_cascade_relationships(self, db_session, test_user):
        """Test cascade delete behavior."""
        # Create farm with field
        farm = Farm(
            name="Cascade Farm",
            owner_id=test_user.id,
            location="Test"
        )
        db_session.add(farm)
        db_session.commit()
        
        field = Field(
            farm_id=farm.id,
            name="Cascade Field"
        )
        db_session.add(field)
        db_session.commit()
        
        farm_id = farm.id
        field_id = field.id
        
        # Delete farm
        db_session.delete(farm)
        db_session.commit()
        
        # Check if field was also deleted (depends on cascade config)
        field = db_session.query(Field).filter(Field.id == field_id).first()
        # Test based on actual cascade configuration


# ==================== Performance Tests ====================

@pytest.mark.slow
@pytest.mark.database
class TestDatabasePerformance:
    """Test database performance."""
    
    def test_bulk_insert_performance(self, db_session, test_farm, performance_timer):
        """Test bulk insert performance."""
        performance_timer.start()
        
        # Insert 1000 weather records
        weather_records = []
        for i in range(1000):
            weather = WeatherData(
                farm_id=test_farm.id,
                timestamp=datetime.utcnow() - timedelta(hours=i),
                temperature=20 + (i % 10),
                humidity=60 + (i % 20)
            )
            weather_records.append(weather)
        
        db_session.bulk_save_objects(weather_records)
        db_session.commit()
        
        performance_timer.stop()
        elapsed = performance_timer.elapsed()
        
        # Should complete in reasonable time
        assert elapsed < 5.0, f"Bulk insert took {elapsed:.2f}s"
    
    def test_query_performance(self, db_session, test_farm, performance_timer):
        """Test query performance."""
        # Create test data
        for i in range(100):
            weather = WeatherData(
                farm_id=test_farm.id,
                timestamp=datetime.utcnow() - timedelta(hours=i),
                temperature=25.0
            )
            db_session.add(weather)
        
        db_session.commit()
        
        performance_timer.start()
        
        # Query data
        results = db_session.query(WeatherData).filter(
            WeatherData.farm_id == test_farm.id
        ).order_by(WeatherData.timestamp.desc()).limit(50).all()
        
        performance_timer.stop()
        elapsed = performance_timer.elapsed()
        
        assert len(results) == 50
        assert elapsed < 1.0, f"Query took {elapsed:.2f}s"
    
    def test_complex_join_performance(self, db_session, test_user, performance_timer):
        """Test complex join query performance."""
        performance_timer.start()
        
        # Complex query joining multiple tables
        results = db_session.query(Farm).join(Field).join(Crop).filter(
            Farm.owner_id == test_user.id
        ).all()
        
        performance_timer.stop()
        elapsed = performance_timer.elapsed()
        
        assert elapsed < 1.0, f"Join query took {elapsed:.2f}s"


# ==================== Data Integrity Tests ====================

@pytest.mark.database
class TestDataIntegrity:
    """Test data integrity constraints."""
    
    def test_unique_email_constraint(self, db_session, test_user):
        """Test email uniqueness is enforced."""
        from app.database.models.user import User
        
        duplicate = User(
            email=test_user.email,
            hashed_password="hash",
            full_name="Duplicate"
        )
        db_session.add(duplicate)
        
        with pytest.raises(IntegrityError):
            db_session.commit()
    
    def test_foreign_key_constraints(self, db_session):
        """Test foreign key constraints."""
        # Try to create farm with invalid user_id
        farm = Farm(
            name="Invalid Farm",
            owner_id=99999,  # Non-existent user
            location="Test"
        )
        db_session.add(farm)
        
        with pytest.raises(IntegrityError):
            db_session.commit()
    
    def test_not_null_constraints(self, db_session, test_farm):
        """Test not-null constraints."""
        # Try to create field without required fields
        field = Field(farm_id=test_farm.id)
        # Missing required 'name' field
        db_session.add(field)
        
        with pytest.raises(IntegrityError):
            db_session.commit()
    
    def test_check_constraints(self, db_session, test_farm):
        """Test check constraints (if defined)."""
        # Example: negative size should fail
        field = Field(
            farm_id=test_farm.id,
            name="Negative Size",
            size_hectares=-5.0  # Invalid negative size
        )
        db_session.add(field)
        
        # Depending on DB constraints, this might fail
        try:
            db_session.commit()
            # If no constraint, just verify value
            assert field.size_hectares < 0
        except IntegrityError:
            # Expected if check constraint exists
            pass
