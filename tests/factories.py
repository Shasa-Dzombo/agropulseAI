"""
Test Data Factories

Factory classes for generating test data using Factory Boy pattern.
Provides consistent, realistic test data generation.
"""

import factory
from factory import fuzzy
from datetime import datetime, timedelta
import random
from typing import Optional


class UserFactory(factory.Factory):
    """Factory for creating User instances."""
    
    class Meta:
        model = dict
    
    email = factory.Sequence(lambda n: f"user{n}@example.com")
    full_name = factory.Faker("name")
    phone_number = factory.Sequence(lambda n: f"+25471234{n:04d}")
    role = fuzzy.FuzzyChoice(["farmer", "agronomist", "supplier", "admin"])
    is_active = True
    is_verified = True
    specialization = factory.LazyAttribute(
        lambda o: "crop_management" if o.role == "agronomist" else None
    )


class FarmFactory(factory.Factory):
    """Factory for creating Farm instances."""
    
    class Meta:
        model = dict
    
    name = factory.Faker("company")
    location = factory.Faker("city")
    size_hectares = fuzzy.FuzzyFloat(1.0, 100.0, precision=2)
    latitude = fuzzy.FuzzyFloat(-4.0, 4.0, precision=6)
    longitude = fuzzy.FuzzyFloat(34.0, 42.0, precision=6)
    soil_type = fuzzy.FuzzyChoice([
        "clay", "sandy", "loam", "sandy_loam", "clay_loam", "silt_loam"
    ])
    water_source = fuzzy.FuzzyChoice([
        "borehole", "river", "rain_fed", "irrigation", "dam"
    ])
    is_active = True


class FieldFactory(factory.Factory):
    """Factory for creating Field instances."""
    
    class Meta:
        model = dict
    
    name = factory.Sequence(lambda n: f"Field {n}")
    size_hectares = fuzzy.FuzzyFloat(0.5, 20.0, precision=2)
    soil_type = fuzzy.FuzzyChoice([
        "clay", "sandy", "loam", "sandy_loam", "clay_loam"
    ])
    current_crop = fuzzy.FuzzyChoice([
        "maize", "beans", "potatoes", "tomatoes", "kale", "wheat"
    ])
    planting_date = factory.LazyFunction(
        lambda: datetime.utcnow() - timedelta(days=random.randint(10, 60))
    )
    expected_harvest_date = factory.LazyFunction(
        lambda: datetime.utcnow() + timedelta(days=random.randint(60, 120))
    )
    is_active = True


class CropFactory(factory.Factory):
    """Factory for creating Crop instances."""
    
    class Meta:
        model = dict
    
    crop_type = fuzzy.FuzzyChoice([
        "maize", "beans", "potatoes", "tomatoes", "kale", "cabbage", "wheat"
    ])
    variety = factory.LazyAttribute(
        lambda o: {
            "maize": random.choice(["H614", "H513", "DH04"]),
            "beans": random.choice(["KK8", "Rosecoco", "GLP2"]),
            "potatoes": random.choice(["Shangi", "Dutch Robjin", "Tigoni"]),
            "tomatoes": random.choice(["Anna F1", "Kilele F1", "Eden F1"]),
        }.get(o.crop_type, "Standard")
    )
    planting_date = factory.LazyFunction(
        lambda: datetime.utcnow() - timedelta(days=random.randint(5, 45))
    )
    expected_harvest_date = factory.LazyFunction(
        lambda: datetime.utcnow() + timedelta(days=random.randint(70, 150))
    )
    expected_yield_kg = fuzzy.FuzzyInteger(500, 5000)
    growth_stage = fuzzy.FuzzyChoice([
        "germination", "vegetative", "flowering", "fruiting", "maturity"
    ])
    health_status = fuzzy.FuzzyChoice([
        "excellent", "healthy", "fair", "stressed", "diseased"
    ])
    is_active = True


class SensorFactory(factory.Factory):
    """Factory for creating Sensor instances."""
    
    class Meta:
        model = dict
    
    sensor_type = fuzzy.FuzzyChoice([
        "soil_moisture", "temperature", "humidity", "ph", "npk"
    ])
    sensor_id = factory.Sequence(lambda n: f"SENSOR-{n:06d}")
    location = fuzzy.FuzzyChoice([
        "north", "south", "east", "west", "center", "corner"
    ])
    is_active = True
    installation_date = factory.LazyFunction(
        lambda: datetime.utcnow() - timedelta(days=random.randint(30, 365))
    )


class SensorReadingFactory(factory.Factory):
    """Factory for creating SensorReading instances."""
    
    class Meta:
        model = dict
    
    timestamp = factory.LazyFunction(
        lambda: datetime.utcnow() - timedelta(hours=random.randint(0, 72))
    )
    value = fuzzy.FuzzyFloat(20.0, 80.0, precision=2)
    unit = factory.LazyAttribute(
        lambda o: {
            "soil_moisture": "percentage",
            "temperature": "celsius",
            "humidity": "percentage",
            "ph": "ph",
            "npk": "ppm"
        }.get(o.sensor_type, "units")
    )
    quality_score = fuzzy.FuzzyFloat(0.85, 1.0, precision=2)


class WeatherDataFactory(factory.Factory):
    """Factory for creating WeatherData instances."""
    
    class Meta:
        model = dict
    
    timestamp = factory.LazyFunction(datetime.utcnow)
    temperature = fuzzy.FuzzyFloat(15.0, 35.0, precision=1)
    humidity = fuzzy.FuzzyFloat(40.0, 90.0, precision=1)
    rainfall = fuzzy.FuzzyFloat(0.0, 50.0, precision=1)
    wind_speed = fuzzy.FuzzyFloat(0.0, 30.0, precision=1)
    pressure = fuzzy.FuzzyFloat(1005.0, 1025.0, precision=2)
    conditions = fuzzy.FuzzyChoice([
        "clear", "partly_cloudy", "cloudy", "rainy", "stormy"
    ])


class AlertFactory(factory.Factory):
    """Factory for creating Alert instances."""
    
    class Meta:
        model = dict
    
    alert_type = fuzzy.FuzzyChoice([
        "pest_detection", "disease_detection", "weather_alert",
        "irrigation_needed", "harvest_ready", "sensor_malfunction"
    ])
    severity = fuzzy.FuzzyChoice(["low", "medium", "high", "critical"])
    title = factory.Faker("sentence", nb_words=4)
    message = factory.Faker("paragraph", nb_sentences=2)
    is_read = False
    is_resolved = False
    created_at = factory.LazyFunction(datetime.utcnow)


class MLModelFactory(factory.Factory):
    """Factory for creating MLModel instances."""
    
    class Meta:
        model = dict
    
    name = factory.Sequence(lambda n: f"Model-{n}")
    model_type = fuzzy.FuzzyChoice([
        "crop_recommendation", "pest_detection", "yield_prediction",
        "disease_detection", "price_prediction"
    ])
    version = factory.Sequence(lambda n: f"1.{n}.0")
    accuracy = fuzzy.FuzzyFloat(0.75, 0.95, precision=3)
    precision = fuzzy.FuzzyFloat(0.70, 0.95, precision=3)
    recall = fuzzy.FuzzyFloat(0.70, 0.95, precision=3)
    f1_score = fuzzy.FuzzyFloat(0.70, 0.95, precision=3)
    is_active = True
    training_date = factory.LazyFunction(
        lambda: datetime.utcnow() - timedelta(days=random.randint(1, 30))
    )


class PredictionFactory(factory.Factory):
    """Factory for creating Prediction instances."""
    
    class Meta:
        model = dict
    
    model_type = fuzzy.FuzzyChoice([
        "crop_recommendation", "yield_prediction", "price_prediction"
    ])
    input_data = factory.LazyFunction(
        lambda: {
            "nitrogen": random.randint(20, 100),
            "phosphorus": random.randint(20, 100),
            "potassium": random.randint(20, 100),
            "temperature": random.uniform(15, 35),
            "humidity": random.uniform(40, 90),
            "ph": random.uniform(5.5, 8.0),
            "rainfall": random.randint(200, 1500)
        }
    )
    prediction_result = factory.LazyFunction(
        lambda: {
            "recommended_crop": random.choice(["maize", "beans", "potatoes"]),
            "confidence": random.uniform(0.7, 0.95),
            "alternatives": random.sample(["wheat", "rice", "tomatoes"], 2)
        }
    )
    confidence_score = fuzzy.FuzzyFloat(0.6, 0.98, precision=3)
    created_at = factory.LazyFunction(datetime.utcnow)


class IrrigationEventFactory(factory.Factory):
    """Factory for creating IrrigationEvent instances."""
    
    class Meta:
        model = dict
    
    irrigation_date = factory.LazyFunction(
        lambda: datetime.utcnow() - timedelta(days=random.randint(0, 14))
    )
    water_amount_mm = fuzzy.FuzzyFloat(10.0, 50.0, precision=1)
    duration_minutes = fuzzy.FuzzyInteger(30, 240)
    method = fuzzy.FuzzyChoice(["sprinkler", "drip", "furrow", "flood"])
    notes = factory.Faker("sentence")


class FertilizerApplicationFactory(factory.Factory):
    """Factory for creating FertilizerApplication instances."""
    
    class Meta:
        model = dict
    
    application_date = factory.LazyFunction(
        lambda: datetime.utcnow() - timedelta(days=random.randint(0, 60))
    )
    fertilizer_type = fuzzy.FuzzyChoice([
        "NPK 17-17-17", "Urea 46-0-0", "DAP 18-46-0", "CAN 26-0-0"
    ])
    amount_kg = fuzzy.FuzzyFloat(50.0, 500.0, precision=1)
    application_method = fuzzy.FuzzyChoice([
        "broadcast", "banding", "side_dressing", "foliar"
    ])
    cost = fuzzy.FuzzyFloat(2000.0, 20000.0, precision=2)


class PestObservationFactory(factory.Factory):
    """Factory for creating PestObservation instances."""
    
    class Meta:
        model = dict
    
    observation_date = factory.LazyFunction(datetime.utcnow)
    pest_type = fuzzy.FuzzyChoice([
        "fall_armyworm", "aphids", "whiteflies", "cutworms", "beetles"
    ])
    severity = fuzzy.FuzzyChoice(["low", "medium", "high", "severe"])
    affected_area_pct = fuzzy.FuzzyFloat(1.0, 50.0, precision=1)
    action_taken = factory.Faker("sentence")
    notes = factory.Faker("paragraph", nb_sentences=1)


class DiseaseObservationFactory(factory.Factory):
    """Factory for creating DiseaseObservation instances."""
    
    class Meta:
        model = dict
    
    observation_date = factory.LazyFunction(datetime.utcnow)
    disease_type = fuzzy.FuzzyChoice([
        "late_blight", "early_blight", "fusarium_wilt", "bacterial_wilt"
    ])
    severity = fuzzy.FuzzyChoice(["low", "medium", "high", "critical"])
    symptoms = factory.LazyFunction(
        lambda: random.sample([
            "leaf_spots", "wilting", "yellowing", "stunting", "fruit_rot"
        ], 2)
    )
    treatment = factory.Faker("sentence")


class HarvestFactory(factory.Factory):
    """Factory for creating Harvest instances."""
    
    class Meta:
        model = dict
    
    harvest_date = factory.LazyFunction(datetime.utcnow)
    quantity_kg = fuzzy.FuzzyFloat(500.0, 5000.0, precision=1)
    quality_grade = fuzzy.FuzzyChoice(["A", "B", "C"])
    market_price_per_kg = fuzzy.FuzzyFloat(20.0, 150.0, precision=2)
    total_revenue = factory.LazyAttribute(
        lambda o: o.quantity_kg * o.market_price_per_kg
    )
    buyer = factory.Faker("company")
    notes = factory.Faker("sentence")


class ExpenseFactory(factory.Factory):
    """Factory for creating Expense instances."""
    
    class Meta:
        model = dict
    
    expense_date = factory.LazyFunction(
        lambda: datetime.utcnow() - timedelta(days=random.randint(0, 90))
    )
    category = fuzzy.FuzzyChoice([
        "seeds", "fertilizer", "pesticides", "labor", "irrigation",
        "equipment", "transport", "other"
    ])
    amount = fuzzy.FuzzyFloat(500.0, 10000.0, precision=2)
    description = factory.Faker("sentence")
    paid_to = factory.Faker("company")


# ==================== Batch Factories ====================

def create_user_batch(count: int = 5, **kwargs):
    """Create a batch of users."""
    return [UserFactory.build(**kwargs) for _ in range(count)]


def create_farm_batch(count: int = 3, **kwargs):
    """Create a batch of farms."""
    return [FarmFactory.build(**kwargs) for _ in range(count)]


def create_field_batch(count: int = 5, **kwargs):
    """Create a batch of fields."""
    return [FieldFactory.build(**kwargs) for _ in range(count)]


def create_sensor_readings_batch(count: int = 24, **kwargs):
    """Create a batch of sensor readings (e.g., 24 hours)."""
    readings = []
    for i in range(count):
        reading = SensorReadingFactory.build(**kwargs)
        reading["timestamp"] = datetime.utcnow() - timedelta(hours=i)
        readings.append(reading)
    return readings


def create_weather_forecast_batch(days: int = 7, **kwargs):
    """Create weather forecast for specified days."""
    forecast = []
    for i in range(days):
        weather = WeatherDataFactory.build(**kwargs)
        weather["timestamp"] = datetime.utcnow() + timedelta(days=i)
        forecast.append(weather)
    return forecast


# ==================== Specialized Factories ====================

class CropRecommendationInputFactory(factory.Factory):
    """Factory for crop recommendation input data."""
    
    class Meta:
        model = dict
    
    nitrogen = fuzzy.FuzzyInteger(20, 140)
    phosphorus = fuzzy.FuzzyInteger(5, 145)
    potassium = fuzzy.FuzzyInteger(5, 205)
    temperature = fuzzy.FuzzyFloat(10.0, 40.0, precision=1)
    humidity = fuzzy.FuzzyFloat(20.0, 100.0, precision=1)
    ph = fuzzy.FuzzyFloat(4.0, 9.0, precision=2)
    rainfall = fuzzy.FuzzyFloat(50.0, 3000.0, precision=1)
    location = fuzzy.FuzzyChoice([
        "Nairobi", "Mombasa", "Kisumu", "Nakuru", "Eldoret"
    ])


class YieldPredictionInputFactory(factory.Factory):
    """Factory for yield prediction input data."""
    
    class Meta:
        model = dict
    
    crop_type = fuzzy.FuzzyChoice(["maize", "beans", "potatoes", "wheat"])
    planting_date = factory.LazyFunction(
        lambda: (datetime.utcnow() - timedelta(days=45)).isoformat()
    )
    field_size_ha = fuzzy.FuzzyFloat(1.0, 20.0, precision=2)
    soil_nitrogen = fuzzy.FuzzyInteger(30, 120)
    soil_phosphorus = fuzzy.FuzzyInteger(10, 80)
    soil_potassium = fuzzy.FuzzyInteger(20, 100)
    avg_temperature = fuzzy.FuzzyFloat(18.0, 30.0, precision=1)
    total_rainfall = fuzzy.FuzzyFloat(300.0, 1200.0, precision=1)
    irrigation_applied = fuzzy.FuzzyChoice([True, False])
    fertilizer_applied = fuzzy.FuzzyChoice([True, False])


class PestDetectionInputFactory(factory.Factory):
    """Factory for pest detection input data."""
    
    class Meta:
        model = dict
    
    crop_type = fuzzy.FuzzyChoice(["maize", "tomatoes", "beans", "potatoes"])
    image_features = factory.LazyFunction(
        lambda: [random.uniform(0, 1) for _ in range(128)]
    )
    growth_stage = fuzzy.FuzzyChoice([
        "vegetative", "flowering", "fruiting", "maturity"
    ])
    temperature = fuzzy.FuzzyFloat(20.0, 35.0, precision=1)
    humidity = fuzzy.FuzzyFloat(50.0, 95.0, precision=1)
    location = fuzzy.FuzzyChoice(["field", "greenhouse", "storage"])


# ==================== Data Generators ====================

def generate_time_series_data(
    days: int = 30,
    base_value: float = 50.0,
    trend: float = 0.1,
    seasonality_amplitude: float = 10.0,
    noise_level: float = 2.0
):
    """
    Generate synthetic time series data with trend, seasonality, and noise.
    """
    import numpy as np
    
    time_points = np.arange(days)
    trend_component = base_value + trend * time_points
    seasonal_component = seasonality_amplitude * np.sin(2 * np.pi * time_points / 7)
    noise = np.random.normal(0, noise_level, days)
    
    values = trend_component + seasonal_component + noise
    
    return [
        {
            "timestamp": (datetime.utcnow() - timedelta(days=days-i)).isoformat(),
            "value": float(values[i])
        }
        for i in range(days)
    ]


def generate_npk_variations(base_n: int = 80, base_p: int = 50, base_k: int = 60):
    """Generate NPK variations for testing."""
    variations = []
    
    for n_mult in [0.5, 0.75, 1.0, 1.25, 1.5]:
        for p_mult in [0.5, 0.75, 1.0, 1.25, 1.5]:
            for k_mult in [0.5, 0.75, 1.0, 1.25, 1.5]:
                variations.append({
                    "nitrogen": int(base_n * n_mult),
                    "phosphorus": int(base_p * p_mult),
                    "potassium": int(base_k * k_mult)
                })
    
    return variations
