# c:\Users\Codeternal\Desktop\AgroPulse\app\iot\fleet_management\maintenance.py

"""
Fleet Maintenance Management System
===================================

This module provides a comprehensive system for managing the maintenance
lifecycle of all vehicles in the fleet. It automates the process of identifying
vehicles that need service, creating maintenance tasks, and tracking the history
and costs associated with maintenance.

Core Components:
-------------
1.  **`MaintenancePredictor`**:
    -   **Purpose**: Proactively identifies vehicles that are due for preventive
      maintenance.
    -   **`check_for_due_maintenance()`**: This is the core method. It iterates
      through all vehicles in the `FleetRegistry` and checks their `OperatingHours`.
      If a vehicle's hours since the last service exceed a predefined threshold
      (e.g., 200 hours for a tractor), it flags the vehicle as needing maintenance.
    -   **Integration**: It's designed to be run periodically (e.g., daily) by a
      background job or scheduler.

2.  **`MaintenanceScheduler`**:
    -   **Purpose**: Takes the list of vehicles flagged by the `MaintenancePredictor`
      and creates formal maintenance tasks in the `TaskQueue`.
    -   **`schedule_maintenance_tasks()`**:
        -   For each vehicle needing service, it creates a `TaskDefinition` with
          a specific `task_type` (e.g., 'preventive_maintenance').
        -   It assigns a high priority to these tasks to ensure they are handled
          promptly.
        -   It adds these tasks to the main `TaskQueue`, where they will be picked
          up by the `FleetScheduler` and assigned to a virtual "maintenance bay"
          or a real-world service provider.

3.  **`MaintenanceLogger`**:
    -   **Purpose**: Provides a high-level API for recording completed maintenance
      work and updating the vehicle's state accordingly.
    -   **`log_maintenance_completed()`**:
        -   Takes a `vehicle_id` and a `MaintenanceLog` object as input.
        -   It retrieves the vehicle from the `FleetRegistry`.
        -   Appends the new log to the vehicle's `maintenance_logs` list.
        -   Crucially, it updates the `last_serviced_at_hours` in the vehicle's
          `OperatingHours` to the current total hours. This "resets the clock"
          for the next maintenance interval.
        -   It ensures the vehicle's status is set back to `IDLE` so it can be
          re-assigned to operational tasks.

This module works in concert with the other fleet management components to create
a closed-loop system: the `MaintenancePredictor` identifies the need, the
`MaintenanceScheduler` creates the work order, the `FleetScheduler` assigns it,
and the `MaintenanceLogger` records the completion, making the vehicle ready for
service again.
"""

import logging
from datetime import datetime
from typing import List, Dict

from .registry import get_fleet_registry
from .scheduling import task_queue, TaskDefinition, TaskPriority
from .vehicle import Vehicle, VehicleType, MaintenanceLog, MaintenanceType

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Default maintenance intervals in operating hours for different vehicle types
DEFAULT_MAINTENANCE_INTERVALS: Dict[VehicleType, float] = {
    VehicleType.TRACTOR: 200.0,
    VehicleType.COMBINE_HARVESTER: 150.0,
    VehicleType.SPRAYER: 100.0,
    VehicleType.PLANTER: 120.0,
    VehicleType.UTV: 80.0,
    VehicleType.DRONE: 50.0,  # Drones often have shorter service intervals
    VehicleType.TRUCK: 300.0,
    VehicleType.IRRIGATION_RIG: 500.0,
}

class MaintenancePredictor:
    """
    Analyzes the fleet to identify vehicles due for preventive maintenance.
    """
    def __init__(self):
        self._registry = get_fleet_registry()
        logging.info("MaintenancePredictor initialized.")

    def check_for_due_maintenance(self) -> List[Vehicle]:
        """
        Scans the fleet and returns a list of vehicles that have exceeded their
        maintenance interval.
        """
        due_vehicles: List[Vehicle] = []
        all_vehicles = self._registry.get_all_vehicles()
        
        for vehicle in all_vehicles:
            interval = DEFAULT_MAINTENANCE_INTERVALS.get(vehicle.vehicle_type)
            if not interval:
                continue # Skip vehicle types without a defined interval

            if vehicle.operating_hours.hours_since_last_service >= interval:
                due_vehicles.append(vehicle)
                logging.info(
                    f"Vehicle {vehicle.vehicle_id} ({vehicle.make} {vehicle.model}) is due for maintenance. "
                    f"Hours since last service: {vehicle.operating_hours.hours_since_last_service:.2f} "
                    f"(Interval: {interval} hours)"
                )
        return due_vehicles

class MaintenanceScheduler:
    """
    Creates and schedules maintenance tasks for vehicles identified by the predictor.
    """
    def __init__(self):
        self._task_queue = task_queue
        logging.info("MaintenanceScheduler initialized.")

    def schedule_maintenance_tasks(self, vehicles_due: List[Vehicle]):
        """
        Creates high-priority maintenance tasks and adds them to the global task queue.
        """
        if not vehicles_due:
            logging.info("No vehicles due for maintenance. Nothing to schedule.")
            return

        for vehicle in vehicles_due:
            # In a real system, the "required_vehicle_type" for a maintenance task
            # might be a "maintenance_bay" or a "service_technician" resource.
            # For simplicity, we'll create a task that conceptually targets the vehicle itself.
            # The task itself won't be assigned back to the vehicle, but to a maintenance resource.
            # Here, we'll just create the task definition.
            
            maintenance_task = TaskDefinition(
                task_type=f"preventive_maintenance_{vehicle.vehicle_type.value}",
                # This is a conceptual placeholder. A real system would have a resource type for maintenance crews/bays.
                required_vehicle_type=vehicle.vehicle_type, 
                priority=TaskPriority.HIGH,
                target_area={"type": "Point", "coordinates": []}, # No specific area for maintenance
                estimated_duration_hours=4.0, # Default estimate
                task_parameters={
                    "target_vehicle_id": vehicle.vehicle_id,
                    "reason": f"{vehicle.operating_hours.hours_since_last_service:.2f} hours since last service."
                }
            )
            self._task_queue.add_task(maintenance_task)
            logging.info(f"Scheduled maintenance task {maintenance_task.task_id} for vehicle {vehicle.vehicle_id}.")

class MaintenanceLogger:
    """
    Provides an API to log completed maintenance work and update vehicle state.
    """
    def __init__(self):
        self._registry = get_fleet_registry()
        logging.info("MaintenanceLogger initialized.")

    def log_maintenance_completed(self, vehicle_id: str, maintenance_log: MaintenanceLog) -> bool:
        """
        Logs a maintenance event for a vehicle and resets its service clock.

        Args:
            vehicle_id (str): The ID of the vehicle that was serviced.
            maintenance_log (MaintenanceLog): The record of the maintenance performed.

        Returns:
            bool: True if the log was successfully added, False otherwise.
        """
        vehicle = self._registry.get_vehicle(vehicle_id)
        if not vehicle:
            logging.error(f"Cannot log maintenance. Vehicle with ID {vehicle_id} not found.")
            return False

        # 1. Add the new log to the vehicle's history
        vehicle.maintenance_logs.append(maintenance_log)

        # 2. Update the operating hours at last service to the current total
        vehicle.operating_hours.last_serviced_at_hours = vehicle.operating_hours.total_hours

        # 3. Set the vehicle's status back to IDLE, ready for work
        vehicle.status = "idle"

        # 4. Persist the changes to the registry
        self._registry.update_vehicle(vehicle_id, vehicle.dict())
        
        logging.info(
            f"Successfully logged maintenance for vehicle {vehicle_id}. "
            f"Hours since last service reset to 0. Status set to IDLE."
        )
        return True

# --- Global Instances ---
maintenance_predictor = MaintenancePredictor()
maintenance_scheduler = MaintenanceScheduler()
maintenance_logger = MaintenanceLogger()

# --- Example Usage ---
if __name__ == "__main__":
    registry = get_fleet_registry()

    # 1. Add a vehicle if none exist
    if not registry.get_vehicle("MAINT_TRACTOR_01"):
        tractor = Vehicle(
            vehicle_id="MAINT_TRACTOR_01",
            vin="MAINTTRACTORVIN001",
            make="New Holland",
            model="T8",
            year=2022,
            vehicle_type=VehicleType.TRACTOR,
            status="idle"
        )
        registry.add_vehicle(tractor)
    
    vehicle = registry.get_vehicle("MAINT_TRACTOR_01")

    # 2. Simulate vehicle usage to make it due for service
    vehicle.operating_hours.total_hours = 250.5
    vehicle.operating_hours.last_serviced_at_hours = 45.0 # Last serviced 205.5 hours ago
    registry.update_vehicle(vehicle.vehicle_id, {"operating_hours": vehicle.operating_hours.dict()})
    
    print(f"Vehicle has {vehicle.operating_hours.hours_since_last_service:.2f} hours since last service.")

    # 3. Run the predictor to find due vehicles
    print("\n--- Running Maintenance Predictor ---")
    due_vehicles = maintenance_predictor.check_for_due_maintenance()
    assert len(due_vehicles) > 0
    assert due_vehicles[0].vehicle_id == "MAINT_TRACTOR_01"
    print(f"Found {len(due_vehicles)} vehicle(s) due for maintenance.")

    # 4. Run the scheduler to create maintenance tasks
    print("\n--- Running Maintenance Scheduler ---")
    maintenance_scheduler.schedule_maintenance_tasks(due_vehicles)
    assert not task_queue.is_empty()
    print("Maintenance tasks have been added to the main task queue.")

    # 5. Simulate completing the maintenance
    print("\n--- Logging Maintenance Completion ---")
    new_log = MaintenanceLog(
        maintenance_date=datetime.utcnow(),
        maintenance_type=MaintenanceType.PREVENTIVE,
        description="200-hour service package.",
        service_provider="Internal Maintenance Team",
        cost_usd=650.00,
        odometer_reading_km=vehicle.operating_hours.total_hours * 15, # Assuming avg 15 km/hr
        parts_replaced=["Engine Oil", "Hydraulic Filter"]
    )
    
    success = maintenance_logger.log_maintenance_completed(vehicle.vehicle_id, new_log)
    assert success

    # 6. Verify the vehicle's state
    updated_vehicle = registry.get_vehicle(vehicle.vehicle_id)
    print(f"Vehicle status after maintenance: {updated_vehicle.status}")
    print(f"Hours since last service after maintenance: {updated_vehicle.operating_hours.hours_since_last_service:.2f}")
    assert updated_vehicle.operating_hours.hours_since_last_service == 0.0
    assert len(updated_vehicle.maintenance_logs) == 1
```