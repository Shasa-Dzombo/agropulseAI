# c:\Users\Codeternal\Desktop\AgroPulse\app\iot\fleet_management\registry.py

"""
Fleet Registry and Management Service
=====================================

This module provides the `FleetRegistry`, a central service for managing the
collection of `Vehicle` objects. It acts as an in-memory database and provides
a high-level API for performing CRUD (Create, Read, Update, Delete) operations
on the fleet.

The registry is designed to be the single source of truth for the state of all
vehicles. It uses a dictionary for efficient lookups by `vehicle_id`.

Key Features:
-------------
1.  **Singleton Pattern**:
    -   The `get_fleet_registry` function ensures that only one instance of the
      `FleetRegistry` exists throughout the application's lifecycle. This prevents
      data inconsistencies and ensures all parts of the system interact with the
      same fleet data.

2.  **CRUD Operations**:
    -   `add_vehicle()`: Adds a new vehicle to the registry, ensuring no ID
      collisions.
    -   `get_vehicle()`: Retrieves a vehicle by its ID.
    -   `update_vehicle()`: Updates the data for an existing vehicle.
    -   `remove_vehicle()`: Deletes a vehicle from the registry.

3.  **Advanced Queries**:
    -   The registry provides methods to query the fleet based on various
      criteria, making it easy to get insights into the fleet's status.
    -   `get_vehicles_by_status()`: Finds all vehicles in a specific state (e.g.,
      all vehicles currently under `MAINTENANCE`).
    -   `get_vehicles_by_type()`: Retrieves all vehicles of a certain type (e.g.,
      all `DRONE`s).
    -   `find_vehicles_needing_service()`: A more complex query that identifies
      vehicles due for maintenance based on their operating hours since the last
      service.
    -   `get_offline_vehicles()`: Finds vehicles that haven't reported telemetry
      recently.

4.  **Telemetry and State Management**:
    -   `update_telemetry()`: A dedicated method to update a vehicle's real-time
      telemetry data. This is a frequent operation and having a specific endpoint
      for it is efficient. It also automatically updates the vehicle's status
      to `ACTIVE`.

5.  **Persistence (Conceptual)**:
    -   Includes placeholder methods (`save_to_disk`, `load_from_disk`) to
      demonstrate how the in-memory data could be persisted to a file (like JSON
      or a pickle file). In a production system, this would be replaced with a
      proper database connection (e.g., to MongoDB, PostgreSQL, or a Redis cache).

This registry is the backbone of the fleet management system, providing the
necessary abstractions to interact with the fleet without needing to manage the
underlying data store directly.
"""

import json
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import threading
import logging

from .vehicle import Vehicle, VehicleStatus, VehicleType, TelemetryData

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class FleetRegistry:
    """
    A thread-safe, in-memory database for managing the vehicle fleet.
    Provides CRUD operations and advanced querying capabilities.
    """
    _instance = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        # Singleton implementation
        if not cls._instance:
            with cls._lock:
                if not cls._instance:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        # The __init__ will be called every time FleetRegistry() is invoked,
        # but the instance will be the same. We use a flag to initialize only once.
        if not hasattr(self, '_initialized'):
            self._vehicles: Dict[str, Vehicle] = {}
            self._initialized = True
            logging.info("FleetRegistry initialized.")

    # --- Basic CRUD Operations ---

    def add_vehicle(self, vehicle: Vehicle) -> bool:
        """
        Adds a new vehicle to the registry.
        Returns True if successful, False if a vehicle with the same ID already exists.
        """
        with self._lock:
            if vehicle.vehicle_id in self._vehicles:
                logging.warning(f"Vehicle with ID {vehicle.vehicle_id} already exists. Cannot add.")
                return False
            self._vehicles[vehicle.vehicle_id] = vehicle
            logging.info(f"Added vehicle {vehicle.make} {vehicle.model} (ID: {vehicle.vehicle_id}) to the registry.")
            return True

    def get_vehicle(self, vehicle_id: str) -> Optional[Vehicle]:
        """Retrieves a vehicle by its unique ID."""
        with self._lock:
            return self._vehicles.get(vehicle_id)

    def update_vehicle(self, vehicle_id: str, vehicle_data: Dict) -> Optional[Vehicle]:
        """
        Updates an existing vehicle's data.
        Uses Pydantic's update mechanism for safe partial updates.
        """
        with self._lock:
            vehicle = self._vehicles.get(vehicle_id)
            if not vehicle:
                logging.error(f"Vehicle with ID {vehicle_id} not found. Cannot update.")
                return None
            
            updated_vehicle = vehicle.copy(update=vehicle_data)
            self._vehicles[vehicle_id] = updated_vehicle
            logging.info(f"Updated vehicle {vehicle_id}.")
            return updated_vehicle

    def remove_vehicle(self, vehicle_id: str) -> bool:
        """
        Removes a vehicle from the registry.
        Returns True if successful, False if the vehicle was not found.
        """
        with self._lock:
            if vehicle_id in self._vehicles:
                del self._vehicles[vehicle_id]
                logging.info(f"Removed vehicle {vehicle_id} from the registry.")
                return True
            logging.warning(f"Vehicle with ID {vehicle_id} not found. Cannot remove.")
            return False

    def get_all_vehicles(self) -> List[Vehicle]:
        """Returns a list of all vehicles in the registry."""
        with self._lock:
            return list(self._vehicles.values())

    # --- Advanced Querying ---

    def get_vehicles_by_status(self, status: VehicleStatus) -> List[Vehicle]:
        """Returns all vehicles with a specific operational status."""
        with self._lock:
            return [v for v in self._vehicles.values() if v.status == status]

    def get_vehicles_by_type(self, vehicle_type: VehicleType) -> List[Vehicle]:
        """Returns all vehicles of a specific type."""
        with self._lock:
            return [v for v in self._vehicles.values() if v.vehicle_type == vehicle_type]

    def find_vehicles_needing_service(self, hours_threshold: float = 200.0) -> List[Vehicle]:
        """
        Finds vehicles that have operated longer than a threshold since their last service.
        """
        with self._lock:
            return [
                v for v in self._vehicles.values()
                if v.operating_hours.hours_since_last_service >= hours_threshold
            ]

    def get_offline_vehicles(self, offline_threshold_minutes: int = 60) -> List[Vehicle]:
        """
        Finds vehicles that have not sent telemetry data within the specified time threshold.
        """
        now = datetime.utcnow()
        offline_threshold = timedelta(minutes=offline_threshold_minutes)
        offline_vehicles = []
        with self._lock:
            for vehicle in self._vehicles.values():
                if vehicle.current_telemetry is None:
                    # If it never sent telemetry, it's considered offline
                    offline_vehicles.append(vehicle)
                elif now - vehicle.current_telemetry.timestamp > offline_threshold:
                    # If the last telemetry is too old
                    offline_vehicles.append(vehicle)
        return offline_vehicles

    # --- State and Telemetry Management ---

    def update_telemetry(self, vehicle_id: str, telemetry_data: TelemetryData) -> bool:
        """
        Updates the telemetry for a specific vehicle and sets its status to ACTIVE.
        """
        with self._lock:
            vehicle = self.get_vehicle(vehicle_id)
            if not vehicle:
                logging.error(f"Cannot update telemetry. Vehicle with ID {vehicle_id} not found.")
                return False
            
            vehicle.current_telemetry = telemetry_data
            vehicle.status = VehicleStatus.ACTIVE
            # Update operating hours based on telemetry (a real system might do this differently)
            # This is a simplified assumption that if telemetry is coming, it's operating.
            # A more robust system would get operating hours from the vehicle's CAN bus data.
            # Let's assume 1 minute of telemetry = 1 minute of operation for this simulation.
            # This is not perfect, but demonstrates the concept.
            # In a real scenario, you'd have a separate process to calculate this.
            # vehicle.operating_hours.total_hours += 1/60 
            
            self._vehicles[vehicle_id] = vehicle
            logging.debug(f"Updated telemetry for vehicle {vehicle_id}.")
            return True

    # --- Persistence (Example Implementation) ---

    def save_to_disk(self, filepath: str) -> bool:
        """
        Serializes the current fleet registry to a JSON file.
        In a real application, this would be a database operation.
        """
        with self._lock:
            try:
                with open(filepath, 'w') as f:
                    # Pydantic's `json()` method is not directly available on the dict values.
                    # We need to serialize each vehicle object.
                    json.dump([v.dict() for v in self._vehicles.values()], f, indent=4, default=str)
                logging.info(f"Fleet registry successfully saved to {filepath}")
                return True
            except (IOError, TypeError) as e:
                logging.error(f"Failed to save fleet registry to {filepath}: {e}")
                return False

    def load_from_disk(self, filepath: str) -> bool:
        """

        Loads the fleet registry from a JSON file.
        """
        with self._lock:
            try:
                with open(filepath, 'r') as f:
                    data = json.load(f)
                    self._vehicles = {item['vehicle_id']: Vehicle(**item) for item in data}
                logging.info(f"Fleet registry successfully loaded from {filepath}")
                return True
            except (IOError, json.JSONDecodeError, KeyError) as e:
                logging.error(f"Failed to load fleet registry from {filepath}: {e}")
                # In case of failure, start with an empty registry
                self._vehicles = {}
                return False

# --- Singleton Accessor ---

def get_fleet_registry() -> FleetRegistry:
    """
    Global accessor for the FleetRegistry singleton instance.
    """
    return FleetRegistry()

# Example Usage
if __name__ == "__main__":
    from .vehicle import Location

    # Get the singleton instance
    registry = get_fleet_registry()

    # Create and add some vehicles
    tractor1 = Vehicle(vin="TRACTORVIN00000001", make="Case IH", model="Magnum 380", year=2021, vehicle_type=VehicleType.TRACTOR)
    drone1 = Vehicle(vin="DRONEVIN0000000001", make="DJI", model="Agras T30", year=2023, vehicle_type=VehicleType.DRONE)
    
    registry.add_vehicle(tractor1)
    registry.add_vehicle(drone1)

    print(f"Total vehicles in registry: {len(registry.get_all_vehicles())}")

    # Update telemetry for the tractor
    telemetry = TelemetryData(
        location=Location(latitude=40.7128, longitude=-74.0060),
        speed_kph=10,
        fuel_level_percent=75
    )
    registry.update_telemetry(tractor1.vehicle_id, telemetry)
    
    retrieved_tractor = registry.get_vehicle(tractor1.vehicle_id)
    print(f"Tractor status: {retrieved_tractor.status}")
    print(f"Tractor location: {retrieved_tractor.current_telemetry.location}")

    # Find vehicles needing service (initially none)
    print(f"Vehicles needing service: {len(registry.find_vehicles_needing_service())}")

    # Simulate operating hours
    retrieved_tractor.operating_hours.total_hours = 250
    registry.update_vehicle(retrieved_tractor.vehicle_id, {"operating_hours": retrieved_tractor.operating_hours.dict()})
    
    print(f"Vehicles needing service after usage: {len(registry.find_vehicles_needing_service(hours_threshold=200))}")

    # Save and load from disk
    FILEPATH = "fleet_data.json"
    registry.save_to_disk(FILEPATH)

    # Create a new registry instance (it will be the same singleton) and load data
    new_registry = get_fleet_registry()
    print(f"Is registry the same instance? {registry is new_registry}")
    new_registry.load_from_disk(FILEPATH)
    print(f"Total vehicles after loading from disk: {len(new_registry.get_all_vehicles())}")
    loaded_tractor = new_registry.get_vehicle(tractor1.vehicle_id)
    print(f"Loaded tractor model: {loaded_tractor.model}")
```