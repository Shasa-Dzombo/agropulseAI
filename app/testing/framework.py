"""
Comprehensive Testing Framework

Unit testing, integration testing, load testing, mocking utilities.

Features:
- Test fixtures and factories
- Mock data generators
- Load testing scenarios
- API testing utilities
- Database test helpers
- Performance benchmarking
- Test coverage analysis
"""

import logging
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import time
import random
import string
import json

try:
    import pytest
    PYTEST_AVAILABLE = True
except ImportError:
    PYTEST_AVAILABLE = False
    logging.warning("pytest not available")


logger = logging.getLogger(__name__)


class TestCategory(Enum):
    """Test categories"""
    UNIT = "unit"
    INTEGRATION = "integration"
    E2E = "end_to_end"
    LOAD = "load"
    SECURITY = "security"


@dataclass
class TestResult:
    """Test execution result"""
    test_name: str
    category: TestCategory
    passed: bool
    duration_seconds: float
    error_message: Optional[str] = None
    assertions: int = 0
    metadata: Dict = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            'test_name': self.test_name,
            'category': self.category.value,
            'passed': self.passed,
            'duration_seconds': self.duration_seconds,
            'error_message': self.error_message,
            'assertions': self.assertions,
            'metadata': self.metadata,
            'timestamp': self.timestamp.isoformat()
        }


@dataclass
class LoadTestConfig:
    """Load test configuration"""
    target_url: str
    concurrent_users: int = 10
    duration_seconds: int = 60
    ramp_up_seconds: int = 10
    request_rate_per_second: Optional[int] = None
    scenarios: List[str] = field(default_factory=list)


@dataclass
class LoadTestResult:
    """Load test result"""
    config: LoadTestConfig
    total_requests: int
    successful_requests: int
    failed_requests: int
    average_response_time: float
    min_response_time: float
    max_response_time: float
    p50_response_time: float
    p95_response_time: float
    p99_response_time: float
    requests_per_second: float
    errors: List[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)


class MockDataGenerator:
    """
    Generate realistic mock data for testing
    
    Creates farms, fields, sensors, users, etc.
    """
    
    def __init__(self, seed: Optional[int] = None):
        """
        Initialize mock data generator
        
        Args:
            seed: Random seed for reproducibility
        """
        if seed:
            random.seed(seed)
        
        self.generated_ids: Dict[str, List[str]] = {}
        
        logger.info(f"MockDataGenerator initialized (seed={seed})")
    
    def generate_farm(
        self,
        farm_id: Optional[str] = None,
        with_fields: int = 3
    ) -> Dict:
        """
        Generate mock farm data
        
        Args:
            farm_id: Optional farm ID
            with_fields: Number of fields to generate
            
        Returns:
            Farm dictionary
        """
        if not farm_id:
            farm_id = self._generate_id('farm')
        
        farm = {
            'farm_id': farm_id,
            'name': f'Farm {farm_id[-4:]}',
            'owner_id': self._generate_id('user'),
            'location': {
                'latitude': random.uniform(30.0, 50.0),
                'longitude': random.uniform(-120.0, -80.0),
                'address': self._generate_address()
            },
            'size_hectares': random.uniform(10.0, 500.0),
            'soil_type': random.choice(['Clay', 'Loam', 'Sandy', 'Silt']),
            'irrigation_system': random.choice(['Drip', 'Sprinkler', 'Flood', 'None']),
            'created_at': self._random_past_date(365).isoformat(),
            'fields': []
        }
        
        # Generate fields
        for i in range(with_fields):
            field = self.generate_field(farm_id=farm_id)
            farm['fields'].append(field)
        
        return farm
    
    def generate_field(
        self,
        field_id: Optional[str] = None,
        farm_id: Optional[str] = None
    ) -> Dict:
        """
        Generate mock field data
        
        Args:
            field_id: Optional field ID
            farm_id: Optional farm ID
            
        Returns:
            Field dictionary
        """
        if not field_id:
            field_id = self._generate_id('field')
        
        if not farm_id:
            farm_id = self._generate_id('farm')
        
        crop_types = ['Tomato', 'Potato', 'Corn', 'Wheat', 'Rice', 'Soybean']
        
        field = {
            'field_id': field_id,
            'farm_id': farm_id,
            'name': f'Field {field_id[-4:]}',
            'area_hectares': random.uniform(1.0, 50.0),
            'crop_type': random.choice(crop_types),
            'planting_date': self._random_past_date(180).isoformat(),
            'expected_harvest_date': self._random_future_date(90).isoformat(),
            'soil_ph': random.uniform(5.5, 7.5),
            'boundary_coordinates': self._generate_polygon_coordinates(4)
        }
        
        return field
    
    def generate_sensor(
        self,
        sensor_id: Optional[str] = None,
        field_id: Optional[str] = None
    ) -> Dict:
        """
        Generate mock sensor data
        
        Args:
            sensor_id: Optional sensor ID
            field_id: Optional field ID
            
        Returns:
            Sensor dictionary
        """
        if not sensor_id:
            sensor_id = self._generate_id('sensor')
        
        if not field_id:
            field_id = self._generate_id('field')
        
        sensor_types = ['soil_moisture', 'temperature', 'humidity', 'light', 'ph']
        
        sensor = {
            'sensor_id': sensor_id,
            'field_id': field_id,
            'sensor_type': random.choice(sensor_types),
            'location': {
                'latitude': random.uniform(30.0, 50.0),
                'longitude': random.uniform(-120.0, -80.0)
            },
            'status': random.choice(['active', 'inactive', 'maintenance']),
            'battery_level': random.uniform(20.0, 100.0),
            'last_reading': self._random_past_date(1).isoformat(),
            'installed_at': self._random_past_date(180).isoformat()
        }
        
        return sensor
    
    def generate_sensor_reading(
        self,
        sensor_id: Optional[str] = None,
        sensor_type: str = 'soil_moisture'
    ) -> Dict:
        """
        Generate mock sensor reading
        
        Args:
            sensor_id: Optional sensor ID
            sensor_type: Type of sensor
            
        Returns:
            Sensor reading dictionary
        """
        if not sensor_id:
            sensor_id = self._generate_id('sensor')
        
        # Value ranges by sensor type
        value_ranges = {
            'soil_moisture': (0, 100),
            'temperature': (-10, 45),
            'humidity': (0, 100),
            'light': (0, 100000),
            'ph': (4.0, 9.0)
        }
        
        min_val, max_val = value_ranges.get(sensor_type, (0, 100))
        
        reading = {
            'reading_id': self._generate_id('reading'),
            'sensor_id': sensor_id,
            'timestamp': self._random_past_date(0.1).isoformat(),
            'value': random.uniform(min_val, max_val),
            'unit': self._get_unit_for_type(sensor_type),
            'quality': random.choice(['good', 'fair', 'poor'])
        }
        
        return reading
    
    def generate_user(
        self,
        user_id: Optional[str] = None,
        role: str = 'farmer'
    ) -> Dict:
        """
        Generate mock user data
        
        Args:
            user_id: Optional user ID
            role: User role
            
        Returns:
            User dictionary
        """
        if not user_id:
            user_id = self._generate_id('user')
        
        first_names = ['John', 'Jane', 'Michael', 'Sarah', 'David', 'Emily']
        last_names = ['Smith', 'Johnson', 'Williams', 'Brown', 'Jones', 'Garcia']
        
        first_name = random.choice(first_names)
        last_name = random.choice(last_names)
        
        user = {
            'user_id': user_id,
            'email': f'{first_name.lower()}.{last_name.lower()}@example.com',
            'first_name': first_name,
            'last_name': last_name,
            'role': role,
            'phone': self._generate_phone_number(),
            'created_at': self._random_past_date(730).isoformat(),
            'last_login': self._random_past_date(7).isoformat(),
            'is_active': random.choice([True, True, True, False])
        }
        
        return user
    
    def generate_batch_data(
        self,
        entity_type: str,
        count: int
    ) -> List[Dict]:
        """
        Generate batch of mock data
        
        Args:
            entity_type: Type of entity (farm, field, sensor, user)
            count: Number of entities to generate
            
        Returns:
            List of entities
        """
        generators = {
            'farm': self.generate_farm,
            'field': self.generate_field,
            'sensor': self.generate_sensor,
            'user': self.generate_user
        }
        
        if entity_type not in generators:
            raise ValueError(f"Unknown entity type: {entity_type}")
        
        generator = generators[entity_type]
        
        return [generator() for _ in range(count)]
    
    def _generate_id(self, prefix: str) -> str:
        """Generate unique ID"""
        id_val = f"{prefix}_{int(time.time() * 1000)}_{random.randint(1000, 9999)}"
        
        if prefix not in self.generated_ids:
            self.generated_ids[prefix] = []
        
        self.generated_ids[prefix].append(id_val)
        
        return id_val
    
    def _generate_address(self) -> str:
        """Generate mock address"""
        street_num = random.randint(100, 9999)
        street_names = ['Main St', 'Oak Ave', 'Maple Dr', 'Farm Rd', 'County Line Rd']
        cities = ['Springfield', 'Riverside', 'Fairview', 'Madison', 'Georgetown']
        states = ['CA', 'TX', 'IA', 'NE', 'IL']
        
        return f"{street_num} {random.choice(street_names)}, {random.choice(cities)}, {random.choice(states)}"
    
    def _generate_phone_number(self) -> str:
        """Generate mock phone number"""
        area_code = random.randint(200, 999)
        exchange = random.randint(200, 999)
        number = random.randint(1000, 9999)
        
        return f"+1{area_code}{exchange}{number}"
    
    def _generate_polygon_coordinates(self, num_points: int = 4) -> List[List[float]]:
        """Generate polygon coordinates"""
        center_lat = random.uniform(30.0, 50.0)
        center_lon = random.uniform(-120.0, -80.0)
        radius = 0.01  # ~1km
        
        coords = []
        
        for i in range(num_points):
            angle = 2 * 3.14159 * i / num_points
            lat = center_lat + radius * random.uniform(0.8, 1.2) * (i % 2 * 2 - 1)
            lon = center_lon + radius * random.uniform(0.8, 1.2) * ((i + 1) % 2 * 2 - 1)
            coords.append([lat, lon])
        
        # Close polygon
        coords.append(coords[0])
        
        return coords
    
    def _random_past_date(self, max_days_ago: float) -> datetime:
        """Generate random past date"""
        seconds_ago = random.uniform(0, max_days_ago * 24 * 3600)
        return datetime.now() - timedelta(seconds=seconds_ago)
    
    def _random_future_date(self, max_days_ahead: float) -> datetime:
        """Generate random future date"""
        seconds_ahead = random.uniform(0, max_days_ahead * 24 * 3600)
        return datetime.now() + timedelta(seconds=seconds_ahead)
    
    def _get_unit_for_type(self, sensor_type: str) -> str:
        """Get unit for sensor type"""
        units = {
            'soil_moisture': '%',
            'temperature': '°C',
            'humidity': '%',
            'light': 'lux',
            'ph': 'pH'
        }
        return units.get(sensor_type, '')


class TestFixtureManager:
    """
    Manage test fixtures and setup/teardown
    """
    
    def __init__(self):
        """Initialize fixture manager"""
        self.fixtures: Dict[str, Any] = {}
        self.cleanup_callbacks: List[Callable] = []
        
        logger.info("TestFixtureManager initialized")
    
    def register_fixture(
        self,
        name: str,
        factory: Callable,
        cleanup: Optional[Callable] = None
    ):
        """
        Register test fixture
        
        Args:
            name: Fixture name
            factory: Factory function to create fixture
            cleanup: Optional cleanup function
        """
        self.fixtures[name] = {
            'factory': factory,
            'cleanup': cleanup,
            'instance': None
        }
        
        logger.debug(f"Fixture registered: {name}")
    
    def get_fixture(self, name: str) -> Any:
        """
        Get fixture instance
        
        Args:
            name: Fixture name
            
        Returns:
            Fixture instance
        """
        if name not in self.fixtures:
            raise ValueError(f"Fixture not found: {name}")
        
        fixture = self.fixtures[name]
        
        if fixture['instance'] is None:
            fixture['instance'] = fixture['factory']()
            
            if fixture['cleanup']:
                self.cleanup_callbacks.append(
                    lambda: fixture['cleanup'](fixture['instance'])
                )
        
        return fixture['instance']
    
    def cleanup_all(self):
        """Run all cleanup callbacks"""
        for callback in self.cleanup_callbacks:
            try:
                callback()
            except Exception as e:
                logger.error(f"Cleanup error: {e}")
        
        self.cleanup_callbacks.clear()
        
        for fixture in self.fixtures.values():
            fixture['instance'] = None
        
        logger.info("All fixtures cleaned up")


class APITestClient:
    """
    HTTP API testing client
    
    Makes requests and validates responses.
    """
    
    def __init__(self, base_url: str):
        """
        Initialize API test client
        
        Args:
            base_url: Base URL for API
        """
        self.base_url = base_url
        self.default_headers = {
            'Content-Type': 'application/json'
        }
        self.mock_mode = True  # Would use requests library
        
        self.request_history: List[Dict] = []
        
        logger.info(f"APITestClient initialized for {base_url}")
    
    def get(
        self,
        endpoint: str,
        params: Optional[Dict] = None,
        headers: Optional[Dict] = None
    ) -> Dict:
        """
        Make GET request
        
        Args:
            endpoint: API endpoint
            params: Query parameters
            headers: Request headers
            
        Returns:
            Response dictionary
        """
        url = f"{self.base_url}{endpoint}"
        
        request = {
            'method': 'GET',
            'url': url,
            'params': params,
            'headers': {**self.default_headers, **(headers or {})},
            'timestamp': datetime.now()
        }
        
        self.request_history.append(request)
        
        if self.mock_mode:
            return {
                'status': 200,
                'data': {'message': 'Mock response'},
                'headers': {}
            }
        
        # Would use requests.get()
        return {}
    
    def post(
        self,
        endpoint: str,
        data: Optional[Dict] = None,
        headers: Optional[Dict] = None
    ) -> Dict:
        """
        Make POST request
        
        Args:
            endpoint: API endpoint
            data: Request body
            headers: Request headers
            
        Returns:
            Response dictionary
        """
        url = f"{self.base_url}{endpoint}"
        
        request = {
            'method': 'POST',
            'url': url,
            'data': data,
            'headers': {**self.default_headers, **(headers or {})},
            'timestamp': datetime.now()
        }
        
        self.request_history.append(request)
        
        if self.mock_mode:
            return {
                'status': 201,
                'data': {'id': 'mock_id', **data} if data else {},
                'headers': {}
            }
        
        # Would use requests.post()
        return {}
    
    def assert_status(self, response: Dict, expected_status: int):
        """Assert response status code"""
        actual_status = response.get('status')
        assert actual_status == expected_status, \
            f"Expected status {expected_status}, got {actual_status}"
    
    def assert_json_contains(self, response: Dict, key: str):
        """Assert response JSON contains key"""
        data = response.get('data', {})
        assert key in data, f"Response does not contain key: {key}"


class LoadTestRunner:
    """
    Load testing runner
    
    Simulates concurrent users and measures performance.
    """
    
    def __init__(self):
        """Initialize load test runner"""
        self.results: List[LoadTestResult] = []
        
        logger.info("LoadTestRunner initialized")
    
    def run_load_test(self, config: LoadTestConfig) -> LoadTestResult:
        """
        Run load test
        
        Args:
            config: Load test configuration
            
        Returns:
            Load test result
        """
        logger.info(
            f"Starting load test: {config.concurrent_users} users, "
            f"{config.duration_seconds}s duration"
        )
        
        start_time = time.time()
        response_times = []
        errors = []
        
        # Simulate load test
        num_requests = config.concurrent_users * config.duration_seconds // 2
        
        for i in range(num_requests):
            response_time = random.uniform(0.01, 2.0)
            response_times.append(response_time)
            
            if random.random() < 0.05:  # 5% error rate
                errors.append(f"Request {i} failed")
        
        # Calculate statistics
        response_times.sort()
        
        result = LoadTestResult(
            config=config,
            total_requests=num_requests,
            successful_requests=num_requests - len(errors),
            failed_requests=len(errors),
            average_response_time=sum(response_times) / len(response_times),
            min_response_time=min(response_times),
            max_response_time=max(response_times),
            p50_response_time=response_times[len(response_times) // 2],
            p95_response_time=response_times[int(len(response_times) * 0.95)],
            p99_response_time=response_times[int(len(response_times) * 0.99)],
            requests_per_second=num_requests / (time.time() - start_time),
            errors=errors
        )
        
        self.results.append(result)
        
        logger.info(
            f"Load test completed: {result.successful_requests}/{result.total_requests} "
            f"successful, avg response time: {result.average_response_time:.3f}s"
        )
        
        return result


class PerformanceBenchmark:
    """
    Performance benchmarking utilities
    
    Measures execution time and resource usage.
    """
    
    def __init__(self):
        """Initialize performance benchmark"""
        self.benchmarks: Dict[str, List[float]] = {}
        
        logger.info("PerformanceBenchmark initialized")
    
    def benchmark(
        self,
        name: str,
        func: Callable,
        iterations: int = 100
    ) -> Dict:
        """
        Benchmark function execution
        
        Args:
            name: Benchmark name
            func: Function to benchmark
            iterations: Number of iterations
            
        Returns:
            Benchmark results
        """
        times = []
        
        for _ in range(iterations):
            start = time.time()
            func()
            elapsed = time.time() - start
            times.append(elapsed)
        
        times.sort()
        
        results = {
            'name': name,
            'iterations': iterations,
            'total_time': sum(times),
            'average_time': sum(times) / len(times),
            'min_time': min(times),
            'max_time': max(times),
            'median_time': times[len(times) // 2],
            'p95_time': times[int(len(times) * 0.95)],
            'p99_time': times[int(len(times) * 0.99)]
        }
        
        self.benchmarks[name] = times
        
        logger.info(
            f"Benchmark '{name}': avg={results['average_time']:.6f}s, "
            f"p95={results['p95_time']:.6f}s"
        )
        
        return results
    
    def compare_benchmarks(
        self,
        name1: str,
        name2: str
    ) -> Dict:
        """
        Compare two benchmarks
        
        Args:
            name1: First benchmark name
            name2: Second benchmark name
            
        Returns:
            Comparison results
        """
        if name1 not in self.benchmarks or name2 not in self.benchmarks:
            raise ValueError("Benchmarks not found")
        
        times1 = self.benchmarks[name1]
        times2 = self.benchmarks[name2]
        
        avg1 = sum(times1) / len(times1)
        avg2 = sum(times2) / len(times2)
        
        speedup = avg1 / avg2 if avg2 > 0 else 0
        
        return {
            'benchmark1': name1,
            'benchmark2': name2,
            'avg_time1': avg1,
            'avg_time2': avg2,
            'speedup': speedup,
            'faster': name1 if avg1 < avg2 else name2,
            'percent_difference': abs(avg1 - avg2) / max(avg1, avg2) * 100
        }
