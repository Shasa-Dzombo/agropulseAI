# c:\Users\Codeternal\Desktop\AgroPulse\app\iot\fleet_management\vehicle.py

"""
Vehicle and Fleet Data Models
=============================

This module defines the core data structures for representing vehicles and their
associated data within the fleet management system. It uses Pydantic for robust
data validation and to create clear, self-documenting models.

The models are designed to be extensible and can be easily serialized to/from
JSON for API communication or storage in a document database like MongoDB.

Core Models:
------------
1.  **`VehicleStatus(Enum)`**:
    -   Defines the possible states a vehicle can be in (e.g., IDLE, ACTIVE,
      MAINTENANCE, OFFLINE). This provides a controlled vocabulary for vehicle status.

2.  **`VehicleType(Enum)`**:
    -   Categorizes the types of vehicles in the fleet (e.g., TRACTOR, DRONE,
      HARVESTER, SPRAYER).

3.  **`Location`**:
    -   A simple model to represent a geographic location with latitude, longitude,
      and altitude.

4.  **`TelemetryData`**:
    -   Represents a single snapshot of telemetry from a vehicle. It includes
      location, speed, fuel/battery level, engine temperature, and a timestamp.
      This model is central to real-time tracking.

5.  **`MaintenanceLog`**:
    -   Records a maintenance event, including the type of service performed,
      date, cost, and detailed notes. This is crucial for tracking vehicle
      health and operational costs.

6.  **`OperatingHours`**:
    -   Tracks the total and recent operating hours of a vehicle, which is a key
      metric for scheduling preventive maintenance.

7.  **`Vehicle`**:
    -   The main model representing a single vehicle in the fleet.
    -   **Attributes**:
        -   `vehicle_id`: A unique identifier for the vehicle.
        -   `vin`: The official Vehicle Identification Number.
        -   `make`, `model`, `year`: Basic vehicle information.
        -   `vehicle_type`: The category of the vehicle (from `VehicleType`).
        -   `status`: The current operational status (from `VehicleStatus`).
        -   `current_telemetry`: The latest telemetry data snapshot.
        -   `operating_hours`: Engine/motor usage statistics.
        -   `maintenance_logs`: A list of all historical maintenance events.
        -   `assigned_operator_id`: The ID of the person currently assigned to
          operate the vehicle.
        -   `custom_attributes`: A flexible dictionary for storing any additional,
          non-standard information about the vehicle.

These models provide a solid foundation for building the fleet management
features, including real-time tracking, maintenance scheduling, and operational
analytics.
"""

from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum
import uuid

# --- Enumerations for controlled vocabularies ---

class VehicleStatus(str, Enum):
    """Defines the operational status of a vehicle."""
    IDLE = "idle"
    ACTIVE = "active"
    IN_TRANSIT = "in_transit"
    MAINTENANCE = "maintenance"
    OFFLINE = "offline"
    ERROR = "error"

class VehicleType(str, Enum):
    """Defines the type of vehicle."""
    TRACTOR = "tractor"
    COMBINE_HARVESTER = "combine_harvester"
    SPRAYER = "sprayer"
    PLANTER = "planter"
    UTV = "utility_task_vehicle"
    DRONE = "drone"
    TRUCK = "truck"
    IRRIGATION_RIG = "irrigation_rig"

class MaintenanceType(str, Enum):
    """Defines the type of maintenance performed."""
    PREVENTIVE = "preventive"
    CORRECTIVE = "corrective"
    EMERGENCY = "emergency"
    INSPECTION = "inspection"
    UPGRADE = "upgrade"

# --- Core Data Models ---

class Location(BaseModel):
    """Represents a geographic location."""
    latitude: float = Field(..., description="Latitude in decimal degrees.", ge=-90, le=90)
    longitude: float = Field(..., description="Longitude in decimal degrees.", ge=-180, le=180)
    altitude: Optional[float] = Field(None, description="Altitude in meters above sea level.")

class TelemetryData(BaseModel):
    """Represents a snapshot of vehicle telemetry data."""
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Timestamp of the telemetry reading.")
    location: Location
    speed_kph: float = Field(..., description="Speed in kilometers per hour.", ge=0)
    fuel_level_percent: Optional[float] = Field(None, description="Fuel level as a percentage (for combustion engines).", ge=0, le=100)
    battery_level_percent: Optional[float] = Field(None, description="Battery level as a percentage (for electric vehicles).", ge=0, le=100)
    engine_temp_celsius: Optional[float] = Field(None, description="Engine temperature in Celsius.")
    engine_rpm: Optional[int] = Field(None, description="Engine revolutions per minute.", ge=0)
    tire_pressure_psi: Optional[Dict[str, float]] = Field(None, description="Tire pressure for each tire in PSI.")

class MaintenanceLog(BaseModel):
    """Records a maintenance event for a vehicle."""
    log_id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique identifier for the maintenance log.")
    maintenance_date: datetime = Field(..., description="Date the maintenance was performed.")
    maintenance_type: MaintenanceType
    description: str = Field(..., description="Detailed description of the work performed.")
    service_provider: str = Field(..., description="Who performed the service (e.g., 'Internal Team', 'John Deere Service Center').")
    cost_usd: float = Field(..., description="Total cost of the maintenance in USD.", ge=0)
    parts_replaced: List[str] = Field(default_factory=list, description="List of parts that were replaced.")
    odometer_reading_km: float = Field(..., description="Odometer reading at the time of maintenance.", ge=0)

class OperatingHours(BaseModel):
    """Tracks the operating hours of a vehicle's engine or motor."""
    total_hours: float = Field(0.0, description="Total accumulated operating hours.", ge=0)
    last_serviced_at_hours: float = Field(0.0, description="Operating hours at the last service.", ge=0)
    
    @property
    def hours_since_last_service(self) -> float:
        """Calculates hours elapsed since the last maintenance."""
        return self.total_hours - self.last_serviced_at_hours

class Vehicle(BaseModel):
    """The main model representing a single vehicle in the fleet."""
    vehicle_id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique identifier for the vehicle.")
    vin: str = Field(..., description="Vehicle Identification Number, must be unique.")
    make: str = Field(..., description="Manufacturer of the vehicle (e.g., 'John Deere').")
    model: str = Field(..., description="Model of the vehicle (e.g., '8R 370').")
    year: int = Field(..., description="Manufacturing year.", gt=1980)
    vehicle_type: VehicleType
    
    status: VehicleStatus = Field(VehicleStatus.OFFLINE, description="Current operational status of the vehicle.")
    
    # Real-time and historical data
    current_telemetry: Optional[TelemetryData] = Field(None, description="The most recent telemetry data received from the vehicle.")
    operating_hours: OperatingHours = Field(default_factory=OperatingHours)
    maintenance_logs: List[MaintenanceLog] = Field(default_factory=list, description="A complete history of maintenance events.")
    
    # Assignment and metadata
    assigned_operator_id: Optional[str] = Field(None, description="ID of the operator currently assigned to the vehicle.")
    purchase_date: Optional[datetime] = Field(None, description="Date the vehicle was acquired.")
    purchase_price_usd: Optional[float] = Field(None, description="Purchase price in USD.")
    custom_attributes: Dict[str, Any] = Field(default_factory=dict, description="Flexible key-value store for additional vehicle attributes.")

    @validator('vin')
    def vin_must_be_alphanumeric_and_specific_length(cls, v):
        """Validate that the VIN is 17 characters long and alphanumeric."""
        if not v.isalnum() or len(v) != 17:
            raise ValueError('VIN must be 17 alphanumeric characters.')
        return v.upper()

    class Config:
        """Pydantic model configuration."""
        use_enum_values = True # Serialize enums to their string values
        anystr_strip_whitespace = True
        validate_assignment = True

# Example Usage (for testing and demonstration)
if __name__ == "__main__":
    # 1. Create a new tractor object
    tractor = Vehicle(
        vin="1AB2C3D4E5F6G7H8I",
        make="John Deere",
        model="8R 370",
        year=2022,
        vehicle_type=VehicleType.TRACTOR,
        purchase_date=datetime(2022, 5, 20),
        purchase_price_usd=350000.00,
        custom_attributes={"color": "Green", "dealership": "AgroTractors Inc."}
    )
    print("--- Initial Vehicle ---")
    print(tractor.json(indent=2))

    # 2. Update its status and telemetry
    tractor.status = VehicleStatus.ACTIVE
    tractor.current_telemetry = TelemetryData(
        location=Location(latitude=34.0522, longitude=-118.2437),
        speed_kph=15.5,
        fuel_level_percent=85.2,
        engine_temp_celsius=90.5,
        engine_rpm=1800,
        tire_pressure_psi={"front_left": 15.1, "front_right": 15.0, "rear_left": 20.2, "rear_right": 20.1}
    )
    tractor.operating_hours.total_hours += 8.5
    
    print("\n--- Updated Vehicle (Active) ---")
    print(tractor.json(indent=2))

    # 3. Add a maintenance log
    maintenance_event = MaintenanceLog(
        maintenance_date=datetime.utcnow(),
        maintenance_type=MaintenanceType.PREVENTIVE,
        description="500-hour service: Oil change, filter replacement, and fluid check.",
        service_provider="Internal Team",
        cost_usd=450.75,
        parts_replaced=["Oil Filter #A45-23", "Air Filter #B99-01"],
        odometer_reading_km=12540.5
    )
    tractor.maintenance_logs.append(maintenance_event)
    tractor.operating_hours.last_serviced_at_hours = tractor.operating_hours.total_hours
    tractor.status = VehicleStatus.IDLE

    print("\n--- After Maintenance ---")
    print(f"Hours since last service: {tractor.operating_hours.hours_since_last_service}")
    print(tractor.json(indent=2))
```