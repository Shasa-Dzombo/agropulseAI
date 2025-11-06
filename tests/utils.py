"""
Test Utilities

Helper functions and utilities for testing.
"""

import json
import numpy as np
from typing import Dict, Any, List, Optional
from datetime import datetime
import hashlib


# ==================== Assertion Utilities ====================

def assert_dict_structure(data: Dict, expected_keys: List[str], strict: bool = False):
    """
    Assert that dictionary has expected keys.
    
    Args:
        data: Dictionary to check
        expected_keys: List of expected keys
        strict: If True, dict must have exactly these keys
    """
    assert isinstance(data, dict), f"Expected dict, got {type(data)}"
    
    for key in expected_keys:
        assert key in data, f"Missing key '{key}' in response"
    
    if strict:
        actual_keys = set(data.keys())
        expected_set = set(expected_keys)
        extra_keys = actual_keys - expected_set
        assert not extra_keys, f"Unexpected keys: {extra_keys}"


def assert_list_not_empty(data: List, message: str = "List is empty"):
    """Assert that list is not empty."""
    assert isinstance(data, list), f"Expected list, got {type(data)}"
    assert len(data) > 0, message


def assert_valid_uuid(uuid_string: str):
    """Assert that string is a valid UUID."""
    import uuid
    try:
        uuid.UUID(uuid_string)
    except (ValueError, AttributeError):
        raise AssertionError(f"Invalid UUID: {uuid_string}")


def assert_valid_iso_datetime(dt_string: str):
    """Assert that string is valid ISO datetime."""
    try:
        datetime.fromisoformat(dt_string.replace('Z', '+00:00'))
    except (ValueError, AttributeError):
        raise AssertionError(f"Invalid ISO datetime: {dt_string}")


def assert_in_range(value: float, min_val: float, max_val: float, name: str = "Value"):
    """Assert that value is within specified range."""
    assert min_val <= value <= max_val, \
        f"{name} {value} not in range [{min_val}, {max_val}]"


def assert_percentage(value: float, name: str = "Value"):
    """Assert that value is a valid percentage (0-100)."""
    assert_in_range(value, 0.0, 100.0, name)


def assert_probability(value: float, name: str = "Value"):
    """Assert that value is a valid probability (0-1)."""
    assert_in_range(value, 0.0, 1.0, name)


# ==================== Data Validation Utilities ====================

def validate_pagination_response(data: Dict):
    """Validate paginated response structure."""
    assert_dict_structure(data, [
        "items", "total", "page", "page_size", "pages"
    ])
    assert isinstance(data["items"], list)
    assert isinstance(data["total"], int)
    assert isinstance(data["page"], int)
    assert isinstance(data["page_size"], int)
    assert isinstance(data["pages"], int)
    assert data["page"] > 0
    assert data["page_size"] > 0
    assert data["total"] >= 0


def validate_error_response(data: Dict):
    """Validate error response structure."""
    assert_dict_structure(data, ["detail"])
    assert isinstance(data["detail"], (str, dict, list))


def validate_ml_prediction_response(data: Dict):
    """Validate ML prediction response structure."""
    assert_dict_structure(data, [
        "prediction", "confidence", "model_version"
    ])
    assert_probability(data["confidence"], "Confidence score")


# ==================== Test Data Helpers ====================

def create_mock_image_bytes(width: int = 224, height: int = 224) -> bytes:
    """Create mock image bytes for testing."""
    from PIL import Image
    import io
    
    img_array = np.random.randint(0, 255, (height, width, 3), dtype=np.uint8)
    img = Image.fromarray(img_array)
    
    img_bytes = io.BytesIO()
    img.save(img_bytes, format='JPEG')
    img_bytes.seek(0)
    
    return img_bytes.read()


def create_multipart_file(content: bytes, filename: str, content_type: str):
    """Create multipart file data for upload testing."""
    import io
    return (filename, io.BytesIO(content), content_type)


def generate_mock_csv_data(rows: int = 100, columns: int = 5) -> str:
    """Generate mock CSV data."""
    import csv
    import io
    
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Header
    header = [f"column_{i}" for i in range(columns)]
    writer.writerow(header)
    
    # Data rows
    for _ in range(rows):
        row = [np.random.random() for _ in range(columns)]
        writer.writerow(row)
    
    return output.getvalue()


# ==================== Database Utilities ====================

def count_records(session, model):
    """Count total records in a table."""
    return session.query(model).count()


def clear_table(session, model):
    """Delete all records from a table."""
    session.query(model).delete()
    session.commit()


def create_test_record(session, model, **kwargs):
    """Create a test database record."""
    record = model(**kwargs)
    session.add(record)
    session.commit()
    session.refresh(record)
    return record


# ==================== API Testing Utilities ====================

def assert_status_code(response, expected_code: int):
    """Assert API response status code."""
    assert response.status_code == expected_code, \
        f"Expected {expected_code}, got {response.status_code}. " \
        f"Response: {response.text}"


def assert_success_response(response):
    """Assert successful API response (2xx)."""
    assert 200 <= response.status_code < 300, \
        f"Expected success (2xx), got {response.status_code}. " \
        f"Response: {response.text}"


def get_json_response(response) -> Dict:
    """Get JSON from response with error handling."""
    assert_success_response(response)
    try:
        return response.json()
    except json.JSONDecodeError as e:
        raise AssertionError(f"Invalid JSON response: {e}")


def create_auth_headers(token: str) -> Dict[str, str]:
    """Create authentication headers."""
    return {"Authorization": f"Bearer {token}"}


# ==================== ML Testing Utilities ====================

def calculate_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> Dict[str, float]:
    """Calculate classification metrics."""
    from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
    
    return {
        "accuracy": accuracy_score(y_true, y_pred),
        "precision": precision_score(y_true, y_pred, average='weighted', zero_division=0),
        "recall": recall_score(y_true, y_pred, average='weighted', zero_division=0),
        "f1_score": f1_score(y_true, y_pred, average='weighted', zero_division=0)
    }


def create_mock_model_weights() -> Dict[str, np.ndarray]:
    """Create mock model weights for testing."""
    return {
        "layer1": np.random.randn(128, 64),
        "layer2": np.random.randn(64, 32),
        "output": np.random.randn(32, 10)
    }


def assert_model_performance(metrics: Dict[str, float], min_accuracy: float = 0.7):
    """Assert ML model meets minimum performance."""
    assert "accuracy" in metrics
    assert metrics["accuracy"] >= min_accuracy, \
        f"Model accuracy {metrics['accuracy']:.3f} below minimum {min_accuracy}"


# ==================== Data Generation Utilities ====================

def generate_random_coordinates(
    lat_range: tuple = (-4.0, 4.0),
    lon_range: tuple = (34.0, 42.0)
) -> Dict[str, float]:
    """Generate random GPS coordinates in Kenya."""
    return {
        "latitude": np.random.uniform(*lat_range),
        "longitude": np.random.uniform(*lon_range)
    }


def generate_soil_data(soil_type: str = "loam") -> Dict[str, Any]:
    """Generate realistic soil data."""
    base_values = {
        "clay": {"nitrogen": 70, "phosphorus": 40, "potassium": 50, "ph": 6.8},
        "loam": {"nitrogen": 80, "phosphorus": 50, "potassium": 60, "ph": 6.5},
        "sandy": {"nitrogen": 50, "phosphorus": 30, "potassium": 40, "ph": 6.0},
        "sandy_loam": {"nitrogen": 65, "phosphorus": 40, "potassium": 50, "ph": 6.3},
    }
    
    base = base_values.get(soil_type, base_values["loam"])
    
    return {
        "nitrogen": base["nitrogen"] + np.random.randint(-10, 10),
        "phosphorus": base["phosphorus"] + np.random.randint(-10, 10),
        "potassium": base["potassium"] + np.random.randint(-10, 10),
        "ph": base["ph"] + np.random.uniform(-0.3, 0.3),
        "organic_matter": np.random.uniform(2.0, 5.0),
        "moisture": np.random.uniform(30, 70)
    }


def generate_weather_data(season: str = "rainy") -> Dict[str, Any]:
    """Generate realistic weather data."""
    if season == "rainy":
        temp_range = (18, 28)
        humidity_range = (60, 90)
        rainfall_range = (5, 40)
    elif season == "dry":
        temp_range = (20, 35)
        humidity_range = (30, 60)
        rainfall_range = (0, 5)
    else:  # transitional
        temp_range = (18, 32)
        humidity_range = (40, 80)
        rainfall_range = (0, 20)
    
    return {
        "temperature": np.random.uniform(*temp_range),
        "humidity": np.random.uniform(*humidity_range),
        "rainfall": np.random.uniform(*rainfall_range),
        "wind_speed": np.random.uniform(5, 25),
        "pressure": np.random.uniform(1005, 1020)
    }


def generate_crop_cycle_data(crop_type: str) -> Dict[str, Any]:
    """Generate complete crop cycle data."""
    from datetime import timedelta
    
    crop_params = {
        "maize": {"cycle_days": 120, "yield_range": (2000, 6000)},
        "beans": {"cycle_days": 90, "yield_range": (800, 2000)},
        "potatoes": {"cycle_days": 110, "yield_range": (15000, 40000)},
        "tomatoes": {"cycle_days": 100, "yield_range": (20000, 50000)},
    }
    
    params = crop_params.get(crop_type, crop_params["maize"])
    planting_date = datetime.utcnow() - timedelta(days=np.random.randint(10, 50))
    
    return {
        "crop_type": crop_type,
        "planting_date": planting_date.isoformat(),
        "expected_harvest_date": (
            planting_date + timedelta(days=params["cycle_days"])
        ).isoformat(),
        "expected_yield_kg": np.random.uniform(*params["yield_range"]),
        "growth_stages": [
            {"stage": "germination", "days": 7},
            {"stage": "vegetative", "days": params["cycle_days"] // 3},
            {"stage": "flowering", "days": params["cycle_days"] // 4},
            {"stage": "maturity", "days": params["cycle_days"] // 3},
        ]
    }


# ==================== Performance Testing Utilities ====================

class PerformanceMonitor:
    """Monitor performance metrics during tests."""
    
    def __init__(self):
        self.measurements = []
    
    def measure(self, func, *args, **kwargs):
        """Measure function execution time."""
        import time
        start = time.time()
        result = func(*args, **kwargs)
        elapsed = time.time() - start
        
        self.measurements.append({
            "function": func.__name__,
            "elapsed": elapsed,
            "timestamp": datetime.utcnow()
        })
        
        return result
    
    def get_average_time(self, func_name: Optional[str] = None) -> float:
        """Get average execution time."""
        if func_name:
            measurements = [m for m in self.measurements if m["function"] == func_name]
        else:
            measurements = self.measurements
        
        if not measurements:
            return 0.0
        
        return sum(m["elapsed"] for m in measurements) / len(measurements)
    
    def assert_performance(self, func_name: str, max_time: float):
        """Assert function meets performance requirement."""
        avg_time = self.get_average_time(func_name)
        assert avg_time <= max_time, \
            f"{func_name} average time {avg_time:.3f}s exceeds {max_time}s"


# ==================== Mock Utilities ====================

class MockWeatherAPI:
    """Mock weather API for testing."""
    
    def __init__(self):
        self.call_count = 0
    
    def get_current_weather(self, lat: float, lon: float):
        """Mock current weather endpoint."""
        self.call_count += 1
        return generate_weather_data()
    
    def get_forecast(self, lat: float, lon: float, days: int = 7):
        """Mock forecast endpoint."""
        self.call_count += 1
        return [generate_weather_data() for _ in range(days)]


class MockMLModel:
    """Mock ML model for testing."""
    
    def __init__(self, accuracy: float = 0.85):
        self.accuracy = accuracy
        self.prediction_count = 0
    
    def predict(self, features: np.ndarray) -> np.ndarray:
        """Mock prediction."""
        self.prediction_count += 1
        # Return random predictions with specified accuracy
        n_samples = len(features)
        predictions = np.random.randint(0, 10, n_samples)
        return predictions
    
    def predict_proba(self, features: np.ndarray) -> np.ndarray:
        """Mock probability prediction."""
        self.prediction_count += 1
        n_samples = len(features)
        n_classes = 10
        probs = np.random.dirichlet(np.ones(n_classes), n_samples)
        return probs


# ==================== Comparison Utilities ====================

def assert_dict_almost_equal(
    dict1: Dict[str, float],
    dict2: Dict[str, float],
    tolerance: float = 0.01
):
    """Assert two dictionaries are approximately equal."""
    assert set(dict1.keys()) == set(dict2.keys()), "Dictionary keys don't match"
    
    for key in dict1.keys():
        val1, val2 = dict1[key], dict2[key]
        if isinstance(val1, (int, float)) and isinstance(val2, (int, float)):
            assert abs(val1 - val2) <= tolerance, \
                f"Values for '{key}' differ: {val1} vs {val2}"
        else:
            assert val1 == val2, f"Values for '{key}' don't match"


def assert_arrays_close(
    arr1: np.ndarray,
    arr2: np.ndarray,
    rtol: float = 1e-5,
    atol: float = 1e-8
):
    """Assert numpy arrays are close."""
    np.testing.assert_allclose(arr1, arr2, rtol=rtol, atol=atol)


# ==================== File Utilities ====================

def calculate_file_hash(file_path: str) -> str:
    """Calculate SHA256 hash of file."""
    sha256 = hashlib.sha256()
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b''):
            sha256.update(chunk)
    return sha256.hexdigest()


def create_temp_file(content: str, suffix: str = '.txt') -> str:
    """Create temporary file with content."""
    import tempfile
    fd, path = tempfile.mkstemp(suffix=suffix)
    with open(fd, 'w') as f:
        f.write(content)
    return path


# ==================== Retry Utilities ====================

def retry_on_failure(max_attempts: int = 3, delay: float = 0.1):
    """Decorator to retry function on failure."""
    import time
    
    def decorator(func):
        def wrapper(*args, **kwargs):
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_attempts - 1:
                        raise
                    time.sleep(delay)
            return None
        return wrapper
    return decorator


# ==================== Logging Utilities ====================

class TestLogger:
    """Logger for capturing test output."""
    
    def __init__(self):
        self.logs = []
    
    def log(self, level: str, message: str):
        """Log a message."""
        self.logs.append({
            "level": level,
            "message": message,
            "timestamp": datetime.utcnow()
        })
    
    def info(self, message: str):
        """Log info message."""
        self.log("INFO", message)
    
    def error(self, message: str):
        """Log error message."""
        self.log("ERROR", message)
    
    def get_logs(self, level: Optional[str] = None) -> List[Dict]:
        """Get logs, optionally filtered by level."""
        if level:
            return [log for log in self.logs if log["level"] == level]
        return self.logs
    
    def clear(self):
        """Clear all logs."""
        self.logs = []
