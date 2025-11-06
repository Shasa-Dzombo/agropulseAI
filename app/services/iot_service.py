"""
IoT Service Module

This service handles all business logic for IoT devices and sensor data, including:
- Device provisioning and registration
- Sensor data processing and validation
- Threshold monitoring and alerts
- Weather data integration
- Irrigation control logic
- Device analytics and reporting
- Data aggregation and statistics
- Device health monitoring

Supports various sensor types: soil moisture, temperature, humidity, pH,
NPK levels, light intensity, and weather sensors.
"""

from sqlalchemy.orm import Session
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime, timedelta
from decimal import Decimal
from statistics import mean, median, stdev

from app.services.base import (
    BaseService,
    ValidationException,
    BusinessRuleException,
    ResourceNotFoundException,
    InsufficientPermissionsException
)
from app.repositories.farm import FarmRepository
from app.repositories.user import UserRepository
from app.repositories.base import BaseRepository
from app.models.database import IoTDevice, SensorData, WeatherRecord, Farm


class IoTService(BaseService):
    """
    Service class for IoT device and sensor data business logic.
    
    This service provides comprehensive IoT operations for smart farming,
    implementing sensor management and data processing rules.
    """
    
    # Sensor thresholds (optimal ranges)
    THRESHOLDS = {
        "soil_moisture": {"min": 20, "max": 80, "unit": "%"},
        "temperature": {"min": 15, "max": 35, "unit": "°C"},
        "humidity": {"min": 40, "max": 70, "unit": "%"},
        "ph": {"min": 6.0, "max": 7.5, "unit": "pH"},
        "nitrogen": {"min": 40, "max": 60, "unit": "ppm"},
        "phosphorus": {"min": 30, "max": 50, "unit": "ppm"},
        "potassium": {"min": 40, "max": 60, "unit": "ppm"},
        "light_intensity": {"min": 200, "max": 400, "unit": "µmol/m²/s"}
    }
    
    def __init__(self, db: Session):
        """
        Initialize the IoT service.
        
        Args:
            db: SQLAlchemy database session
        """
        super().__init__(db)
        self.device_repo = BaseRepository(IoTDevice, db)
        self.sensor_repo = BaseRepository(SensorData, db)
        self.weather_repo = BaseRepository(WeatherRecord, db)
        self.farm_repo = FarmRepository(db)
        self.user_repo = UserRepository(db)
    
    # ========================================================================
    # Device Provisioning and Management
    # ========================================================================
    
    def register_device(
        self,
        farm_id: int,
        user_id: int,
        device_name: str,
        device_type: str,
        serial_number: str,
        location_description: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Register a new IoT device.
        
        Business Rules:
        - User must own the farm
        - Serial number must be unique
        - Device type must be valid
        - Farm must exist and be active
        
        Args:
            farm_id: ID of farm where device is installed
            user_id: ID of user registering device
            device_name: Name/identifier for the device
            device_type: Type of device (soil_sensor, weather_station, irrigation_controller)
            serial_number: Device serial number
            location_description: Description of device location (optional)
            
        Returns:
            Dictionary with device information
            
        Raises:
            ValidationException: If validation fails
            ResourceNotFoundException: If farm not found
            InsufficientPermissionsException: If user doesn't own farm
        """
        with self.transaction():
            # Validate farm and ownership
            farm = self.check_resource_exists(
                self.farm_repo.get_by_id(farm_id),
                "Farm",
                farm_id
            )
            
            self.check_ownership(farm.owner_id, user_id, "farm")
            
            # Validate device type
            valid_types = [
                "soil_sensor",
                "weather_station",
                "irrigation_controller",
                "multi_sensor",
                "camera"
            ]
            
            if device_type not in valid_types:
                raise ValidationException(
                    f"Invalid device type. Must be one of: {', '.join(valid_types)}",
                    field="device_type"
                )
            
            # Check serial number uniqueness
            existing_device = self.db.query(IoTDevice).filter(
                IoTDevice.serial_number == serial_number
            ).first()
            
            if existing_device:
                raise ValidationException(
                    "Device with this serial number already registered",
                    field="serial_number"
                )
            
            # Validate name
            self.validate_string_length(device_name, 2, 100, "device_name")
            
            # Create device
            device = IoTDevice(
                farm_id=farm_id,
                device_name=device_name,
                device_type=device_type,
                serial_number=serial_number,
                location_description=location_description,
                is_active=True,
                last_seen=datetime.utcnow()
            )
            self.db.add(device)
            self.db.flush()
            
            self.log_activity("device_registered", user_id, {
                "device_id": device.id,
                "farm_id": farm_id,
                "device_type": device_type
            })
            
            return self._format_device_response(device)
    
    def update_device(
        self,
        device_id: int,
        user_id: int,
        device_name: Optional[str] = None,
        location_description: Optional[str] = None,
        is_active: Optional[bool] = None
    ) -> Dict[str, Any]:
        """
        Update device information.
        
        Args:
            device_id: ID of device
            user_id: ID of user performing update
            device_name: New device name (optional)
            location_description: New location description (optional)
            is_active: Active status (optional)
            
        Returns:
            Updated device information
            
        Raises:
            ResourceNotFoundException: If device not found
            InsufficientPermissionsException: If user doesn't own farm
        """
        device = self.check_resource_exists(
            self.device_repo.get_by_id(device_id),
            "IoTDevice",
            device_id
        )
        
        farm = self.farm_repo.get_by_id(device.farm_id)
        self.check_ownership(farm.owner_id, user_id, "farm")
        
        if device_name is not None:
            self.validate_string_length(device_name, 2, 100, "device_name")
            device.device_name = device_name
        
        if location_description is not None:
            device.location_description = location_description
        
        if is_active is not None:
            device.is_active = is_active
        
        self.db.flush()
        
        self.log_activity("device_updated", user_id, {"device_id": device_id})
        
        return self._format_device_response(device)
    
    def deactivate_device(self, device_id: int, user_id: int) -> Dict[str, str]:
        """
        Deactivate a device.
        
        Args:
            device_id: ID of device
            user_id: ID of user deactivating device
            
        Returns:
            Success message
            
        Raises:
            ResourceNotFoundException: If device not found
            InsufficientPermissionsException: If user doesn't own farm
        """
        device = self.check_resource_exists(
            self.device_repo.get_by_id(device_id),
            "IoTDevice",
            device_id
        )
        
        farm = self.farm_repo.get_by_id(device.farm_id)
        self.check_ownership(farm.owner_id, user_id, "farm")
        
        device.is_active = False
        self.db.flush()
        
        self.log_activity("device_deactivated", user_id, {"device_id": device_id})
        
        return {"message": "Device deactivated successfully"}
    
    # ========================================================================
    # Sensor Data Processing
    # ========================================================================
    
    def record_sensor_data(
        self,
        device_id: int,
        sensor_type: str,
        value: float,
        unit: str,
        timestamp: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Record sensor data reading.
        
        Business Rules:
        - Device must exist and be active
        - Sensor type must be valid
        - Value must be within reasonable range
        - Automatic threshold checking
        - Alert generation if out of range
        
        Args:
            device_id: ID of device
            sensor_type: Type of sensor
            value: Sensor reading value
            unit: Unit of measurement
            timestamp: Reading timestamp (default: now)
            
        Returns:
            Dictionary with sensor data and any alerts
            
        Raises:
            ValidationException: If validation fails
            ResourceNotFoundException: If device not found
        """
        with self.transaction():
            device = self.check_resource_exists(
                self.device_repo.get_by_id(device_id),
                "IoTDevice",
                device_id
            )
            
            if not device.is_active:
                raise BusinessRuleException(
                    "Cannot record data for inactive device",
                    rule="active_device_required"
                )
            
            # Validate sensor type
            valid_sensors = list(self.THRESHOLDS.keys())
            if sensor_type not in valid_sensors:
                raise ValidationException(
                    f"Invalid sensor type. Must be one of: {', '.join(valid_sensors)}",
                    field="sensor_type"
                )
            
            # Validate value is reasonable
            self._validate_sensor_value(sensor_type, value)
            
            # Use provided timestamp or current time
            if timestamp is None:
                timestamp = datetime.utcnow()
            
            # Create sensor data record
            sensor_data = SensorData(
                device_id=device_id,
                sensor_type=sensor_type,
                value=value,
                unit=unit,
                timestamp=timestamp
            )
            self.db.add(sensor_data)
            
            # Update device last seen
            device.last_seen = datetime.utcnow()
            
            # Check thresholds and generate alerts
            alerts = self._check_threshold_alerts(sensor_type, value, device)
            
            self.db.flush()
            
            return {
                "id": sensor_data.id,
                "device_id": sensor_data.device_id,
                "sensor_type": sensor_data.sensor_type,
                "value": sensor_data.value,
                "unit": sensor_data.unit,
                "timestamp": sensor_data.timestamp.isoformat(),
                "alerts": alerts
            }
    
    def _validate_sensor_value(self, sensor_type: str, value: float):
        """
        Validate sensor value is within reasonable range.
        
        Args:
            sensor_type: Type of sensor
            value: Sensor value
            
        Raises:
            ValidationException: If value is unreasonable
        """
        # Define absolute limits (beyond which data is likely erroneous)
        absolute_limits = {
            "soil_moisture": (0, 100),
            "temperature": (-50, 70),
            "humidity": (0, 100),
            "ph": (0, 14),
            "nitrogen": (0, 200),
            "phosphorus": (0, 200),
            "potassium": (0, 200),
            "light_intensity": (0, 2000)
        }
        
        if sensor_type in absolute_limits:
            min_val, max_val = absolute_limits[sensor_type]
            if not (min_val <= value <= max_val):
                raise ValidationException(
                    f"{sensor_type} value must be between {min_val} and {max_val}",
                    field="value",
                    details={"value": value, "range": absolute_limits[sensor_type]}
                )
    
    def _check_threshold_alerts(
        self,
        sensor_type: str,
        value: float,
        device: IoTDevice
    ) -> List[Dict[str, Any]]:
        """
        Check if sensor value is outside optimal thresholds.
        
        Args:
            sensor_type: Type of sensor
            value: Sensor value
            device: IoT device
            
        Returns:
            List of alert dictionaries
        """
        alerts = []
        
        if sensor_type in self.THRESHOLDS:
            threshold = self.THRESHOLDS[sensor_type]
            
            if value < threshold["min"]:
                alerts.append({
                    "type": "low",
                    "severity": "warning",
                    "message": f"{sensor_type.replace('_', ' ').title()} is low ({value} {threshold['unit']}). Optimal range: {threshold['min']}-{threshold['max']} {threshold['unit']}",
                    "sensor_type": sensor_type,
                    "value": value,
                    "threshold_min": threshold["min"],
                    "threshold_max": threshold["max"]
                })
            
            elif value > threshold["max"]:
                alerts.append({
                    "type": "high",
                    "severity": "warning",
                    "message": f"{sensor_type.replace('_', ' ').title()} is high ({value} {threshold['unit']}). Optimal range: {threshold['min']}-{threshold['max']} {threshold['unit']}",
                    "sensor_type": sensor_type,
                    "value": value,
                    "threshold_min": threshold["min"],
                    "threshold_max": threshold["max"]
                })
        
        return alerts
    
    def get_latest_readings(
        self,
        device_id: int,
        user_id: int
    ) -> Dict[str, Any]:
        """
        Get latest readings from all sensors on a device.
        
        Args:
            device_id: ID of device
            user_id: ID of requesting user
            
        Returns:
            Dictionary with latest readings by sensor type
            
        Raises:
            ResourceNotFoundException: If device not found
            InsufficientPermissionsException: If user doesn't own farm
        """
        device = self.check_resource_exists(
            self.device_repo.get_by_id(device_id),
            "IoTDevice",
            device_id
        )
        
        farm = self.farm_repo.get_by_id(device.farm_id)
        self.check_ownership(farm.owner_id, user_id, "farm")
        
        # Get latest reading for each sensor type
        latest_readings = {}
        
        for sensor_type in self.THRESHOLDS.keys():
            reading = self.db.query(SensorData).filter(
                SensorData.device_id == device_id,
                SensorData.sensor_type == sensor_type
            ).order_by(SensorData.timestamp.desc()).first()
            
            if reading:
                # Check thresholds
                threshold = self.THRESHOLDS[sensor_type]
                status = "optimal"
                if reading.value < threshold["min"]:
                    status = "low"
                elif reading.value > threshold["max"]:
                    status = "high"
                
                latest_readings[sensor_type] = {
                    "value": reading.value,
                    "unit": reading.unit,
                    "timestamp": reading.timestamp.isoformat(),
                    "status": status,
                    "optimal_range": f"{threshold['min']}-{threshold['max']} {threshold['unit']}"
                }
        
        return {
            "device_id": device_id,
            "device_name": device.device_name,
            "readings": latest_readings,
            "last_updated": device.last_seen.isoformat() if device.last_seen else None
        }
    
    def get_sensor_history(
        self,
        device_id: int,
        user_id: int,
        sensor_type: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100
    ) -> Dict[str, Any]:
        """
        Get historical sensor data.
        
        Args:
            device_id: ID of device
            user_id: ID of requesting user
            sensor_type: Type of sensor
            start_date: Start date for data (optional)
            end_date: End date for data (optional)
            limit: Maximum number of records (default: 100)
            
        Returns:
            Dictionary with historical sensor data
            
        Raises:
            ResourceNotFoundException: If device not found
            InsufficientPermissionsException: If user doesn't own farm
        """
        device = self.check_resource_exists(
            self.device_repo.get_by_id(device_id),
            "IoTDevice",
            device_id
        )
        
        farm = self.farm_repo.get_by_id(device.farm_id)
        self.check_ownership(farm.owner_id, user_id, "farm")
        
        # Build query
        query = self.db.query(SensorData).filter(
            SensorData.device_id == device_id,
            SensorData.sensor_type == sensor_type
        )
        
        if start_date:
            query = query.filter(SensorData.timestamp >= start_date)
        
        if end_date:
            query = query.filter(SensorData.timestamp <= end_date)
        
        # Get data ordered by timestamp
        readings = query.order_by(SensorData.timestamp.desc()).limit(limit).all()
        
        return {
            "device_id": device_id,
            "sensor_type": sensor_type,
            "total_readings": len(readings),
            "start_date": start_date.isoformat() if start_date else None,
            "end_date": end_date.isoformat() if end_date else None,
            "readings": [
                {
                    "value": r.value,
                    "unit": r.unit,
                    "timestamp": r.timestamp.isoformat()
                }
                for r in readings
            ]
        }
    
    # ========================================================================
    # Sensor Data Analytics
    # ========================================================================
    
    def calculate_sensor_statistics(
        self,
        device_id: int,
        user_id: int,
        sensor_type: str,
        period_hours: int = 24
    ) -> Dict[str, Any]:
        """
        Calculate statistics for sensor data over a time period.
        
        Args:
            device_id: ID of device
            user_id: ID of requesting user
            sensor_type: Type of sensor
            period_hours: Time period in hours (default: 24)
            
        Returns:
            Dictionary with statistical analysis
            
        Raises:
            ResourceNotFoundException: If device not found
            InsufficientPermissionsException: If user doesn't own farm
        """
        device = self.check_resource_exists(
            self.device_repo.get_by_id(device_id),
            "IoTDevice",
            device_id
        )
        
        farm = self.farm_repo.get_by_id(device.farm_id)
        self.check_ownership(farm.owner_id, user_id, "farm")
        
        # Get data for period
        start_time = datetime.utcnow() - timedelta(hours=period_hours)
        
        readings = self.db.query(SensorData).filter(
            SensorData.device_id == device_id,
            SensorData.sensor_type == sensor_type,
            SensorData.timestamp >= start_time
        ).all()
        
        if not readings:
            return {
                "device_id": device_id,
                "sensor_type": sensor_type,
                "period_hours": period_hours,
                "message": "No data available for this period"
            }
        
        # Calculate statistics
        values = [r.value for r in readings]
        
        average = mean(values)
        median_val = median(values)
        min_val = min(values)
        max_val = max(values)
        std_dev = stdev(values) if len(values) > 1 else 0
        
        # Get threshold info
        threshold = self.THRESHOLDS.get(sensor_type, {})
        
        # Calculate time in optimal range
        if threshold:
            optimal_count = sum(
                1 for v in values
                if threshold["min"] <= v <= threshold["max"]
            )
            optimal_percentage = self.calculate_percentage(optimal_count, len(values))
        else:
            optimal_percentage = None
        
        return {
            "device_id": device_id,
            "sensor_type": sensor_type,
            "period_hours": period_hours,
            "total_readings": len(readings),
            "statistics": {
                "average": round(average, 2),
                "median": round(median_val, 2),
                "minimum": round(min_val, 2),
                "maximum": round(max_val, 2),
                "standard_deviation": round(std_dev, 2),
                "range": round(max_val - min_val, 2)
            },
            "optimal_range": threshold,
            "time_in_optimal_range_percentage": optimal_percentage,
            "trend": self._calculate_trend(values)
        }
    
    def _calculate_trend(self, values: List[float]) -> str:
        """
        Calculate trend direction from values.
        
        Args:
            values: List of sensor values (newest first)
            
        Returns:
            Trend direction: "increasing", "decreasing", or "stable"
        """
        if len(values) < 2:
            return "stable"
        
        # Compare recent half vs older half
        mid_point = len(values) // 2
        recent_avg = mean(values[:mid_point])
        older_avg = mean(values[mid_point:])
        
        diff_percentage = abs((recent_avg - older_avg) / older_avg * 100) if older_avg != 0 else 0
        
        # Consider significant if more than 5% change
        if diff_percentage < 5:
            return "stable"
        elif recent_avg > older_avg:
            return "increasing"
        else:
            return "decreasing"
    
    def get_device_health_status(self, device_id: int, user_id: int) -> Dict[str, Any]:
        """
        Get comprehensive health status of a device.
        
        Args:
            device_id: ID of device
            user_id: ID of requesting user
            
        Returns:
            Dictionary with device health information
            
        Raises:
            ResourceNotFoundException: If device not found
            InsufficientPermissionsException: If user doesn't own farm
        """
        device = self.check_resource_exists(
            self.device_repo.get_by_id(device_id),
            "IoTDevice",
            device_id
        )
        
        farm = self.farm_repo.get_by_id(device.farm_id)
        self.check_ownership(farm.owner_id, user_id, "farm")
        
        # Calculate time since last seen
        if device.last_seen:
            minutes_since_last_seen = self.calculate_days_between(
                device.last_seen,
                datetime.utcnow()
            ) * 24 * 60
        else:
            minutes_since_last_seen = None
        
        # Determine connection status
        if not device.is_active:
            connection_status = "inactive"
            health_status = "offline"
        elif minutes_since_last_seen is None or minutes_since_last_seen > 60:
            connection_status = "disconnected"
            health_status = "critical"
        elif minutes_since_last_seen > 30:
            connection_status = "intermittent"
            health_status = "warning"
        else:
            connection_status = "connected"
            health_status = "healthy"
        
        # Get recent data count
        recent_data_count = self.db.query(SensorData).filter(
            SensorData.device_id == device_id,
            SensorData.timestamp >= datetime.utcnow() - timedelta(hours=24)
        ).count()
        
        # Get alerts in last 24 hours
        recent_readings = self.db.query(SensorData).filter(
            SensorData.device_id == device_id,
            SensorData.timestamp >= datetime.utcnow() - timedelta(hours=24)
        ).all()
        
        alert_count = 0
        for reading in recent_readings:
            alerts = self._check_threshold_alerts(
                reading.sensor_type,
                reading.value,
                device
            )
            alert_count += len(alerts)
        
        return {
            "device_id": device_id,
            "device_name": device.device_name,
            "health_status": health_status,
            "connection_status": connection_status,
            "is_active": device.is_active,
            "last_seen": device.last_seen.isoformat() if device.last_seen else None,
            "minutes_since_last_seen": minutes_since_last_seen,
            "recent_data_points_24h": recent_data_count,
            "alerts_24h": alert_count,
            "battery_level": None,  # Placeholder for future battery monitoring
            "signal_strength": None  # Placeholder for future signal monitoring
        }
    
    # ========================================================================
    # Weather Data Integration
    # ========================================================================
    
    def record_weather_data(
        self,
        farm_id: int,
        temperature: float,
        humidity: float,
        rainfall: float,
        wind_speed: float,
        pressure: Optional[float] = None,
        timestamp: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Record weather data for a farm.
        
        Args:
            farm_id: ID of farm
            temperature: Temperature in Celsius
            humidity: Humidity percentage
            rainfall: Rainfall in mm
            wind_speed: Wind speed in km/h
            pressure: Atmospheric pressure in hPa (optional)
            timestamp: Data timestamp (default: now)
            
        Returns:
            Dictionary with weather data
            
        Raises:
            ResourceNotFoundException: If farm not found
        """
        farm = self.check_resource_exists(
            self.farm_repo.get_by_id(farm_id),
            "Farm",
            farm_id
        )
        
        # Validate values
        if not (-50 <= temperature <= 70):
            raise ValidationException("Temperature must be between -50 and 70°C")
        
        if not (0 <= humidity <= 100):
            raise ValidationException("Humidity must be between 0 and 100%")
        
        if rainfall < 0:
            raise ValidationException("Rainfall cannot be negative")
        
        if wind_speed < 0:
            raise ValidationException("Wind speed cannot be negative")
        
        if timestamp is None:
            timestamp = datetime.utcnow()
        
        # Create weather record
        weather = WeatherRecord(
            farm_id=farm_id,
            temperature=temperature,
            humidity=humidity,
            rainfall=rainfall,
            wind_speed=wind_speed,
            pressure=pressure,
            timestamp=timestamp
        )
        self.db.add(weather)
        self.db.flush()
        
        return {
            "id": weather.id,
            "farm_id": weather.farm_id,
            "temperature": weather.temperature,
            "humidity": weather.humidity,
            "rainfall": weather.rainfall,
            "wind_speed": weather.wind_speed,
            "pressure": weather.pressure,
            "timestamp": weather.timestamp.isoformat()
        }
    
    def get_weather_forecast(
        self,
        farm_id: int,
        user_id: int,
        days: int = 7
    ) -> Dict[str, Any]:
        """
        Get weather forecast for a farm (placeholder for external API integration).
        
        Args:
            farm_id: ID of farm
            user_id: ID of requesting user
            days: Number of days to forecast (default: 7)
            
        Returns:
            Dictionary with forecast data
            
        Raises:
            ResourceNotFoundException: If farm not found
            InsufficientPermissionsException: If user doesn't own farm
        """
        farm = self.check_resource_exists(
            self.farm_repo.get_by_id(farm_id),
            "Farm",
            farm_id
        )
        
        self.check_ownership(farm.owner_id, user_id, "farm")
        
        # This is a placeholder - in production, integrate with weather API
        # (e.g., OpenWeatherMap, Weather.com, etc.)
        
        return {
            "farm_id": farm_id,
            "location": {
                "latitude": farm.latitude,
                "longitude": farm.longitude
            },
            "forecast_days": days,
            "message": "Weather forecast API integration pending",
            "forecast": []
        }
    
    # ========================================================================
    # Irrigation Control
    # ========================================================================
    
    def control_irrigation(
        self,
        device_id: int,
        user_id: int,
        action: str,
        duration_minutes: Optional[int] = None,
        zone: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Control irrigation system.
        
        Business Rules:
        - Device must be irrigation controller
        - User must own the farm
        - Duration must be reasonable (1-480 minutes)
        
        Args:
            device_id: ID of irrigation controller device
            user_id: ID of user issuing command
            action: Action to perform (start, stop, schedule)
            duration_minutes: Duration in minutes (required for start)
            zone: Irrigation zone identifier (optional)
            
        Returns:
            Dictionary with command status
            
        Raises:
            ValidationException: If validation fails
            ResourceNotFoundException: If device not found
            BusinessRuleException: If business rules violated
        """
        device = self.check_resource_exists(
            self.device_repo.get_by_id(device_id),
            "IoTDevice",
            device_id
        )
        
        farm = self.farm_repo.get_by_id(device.farm_id)
        self.check_ownership(farm.owner_id, user_id, "farm")
        
        # Validate device type
        if device.device_type != "irrigation_controller":
            raise BusinessRuleException(
                "Device is not an irrigation controller",
                rule="irrigation_controller_required"
            )
        
        if not device.is_active:
            raise BusinessRuleException(
                "Cannot control inactive device",
                rule="active_device_required"
            )
        
        # Validate action
        valid_actions = ["start", "stop", "schedule"]
        if action not in valid_actions:
            raise ValidationException(
                f"Invalid action. Must be one of: {', '.join(valid_actions)}",
                field="action"
            )
        
        # Validate duration for start action
        if action == "start":
            if duration_minutes is None:
                raise ValidationException(
                    "Duration is required for start action",
                    field="duration_minutes"
                )
            
            if not (1 <= duration_minutes <= 480):
                raise ValidationException(
                    "Duration must be between 1 and 480 minutes (8 hours)",
                    field="duration_minutes"
                )
        
        # In production, this would send actual command to device via MQTT/HTTP
        # For now, we log the command
        
        self.log_activity("irrigation_control", user_id, {
            "device_id": device_id,
            "action": action,
            "duration_minutes": duration_minutes,
            "zone": zone
        })
        
        return {
            "device_id": device_id,
            "action": action,
            "duration_minutes": duration_minutes,
            "zone": zone,
            "status": "command_sent",
            "timestamp": datetime.utcnow().isoformat(),
            "message": f"Irrigation {action} command sent successfully"
        }
    
    def get_irrigation_status(
        self,
        device_id: int,
        user_id: int
    ) -> Dict[str, Any]:
        """
        Get current irrigation system status.
        
        Args:
            device_id: ID of irrigation controller device
            user_id: ID of requesting user
            
        Returns:
            Dictionary with irrigation status
            
        Raises:
            ResourceNotFoundException: If device not found
            InsufficientPermissionsException: If user doesn't own farm
        """
        device = self.check_resource_exists(
            self.device_repo.get_by_id(device_id),
            "IoTDevice",
            device_id
        )
        
        farm = self.farm_repo.get_by_id(device.farm_id)
        self.check_ownership(farm.owner_id, user_id, "farm")
        
        # In production, query actual device status
        # For now, return placeholder
        
        return {
            "device_id": device_id,
            "device_name": device.device_name,
            "status": "idle",
            "current_zone": None,
            "remaining_time_minutes": 0,
            "water_flow_rate": None,
            "total_water_used_today": None,
            "last_updated": datetime.utcnow().isoformat()
        }
    
    # ========================================================================
    # Helper Methods
    # ========================================================================
    
    def _format_device_response(self, device: IoTDevice) -> Dict[str, Any]:
        """Format device object as API response dictionary."""
        return {
            "id": device.id,
            "farm_id": device.farm_id,
            "device_name": device.device_name,
            "device_type": device.device_type,
            "serial_number": device.serial_number,
            "location_description": device.location_description,
            "is_active": device.is_active,
            "last_seen": device.last_seen.isoformat() if device.last_seen else None,
            "created_at": device.created_at.isoformat()
        }
