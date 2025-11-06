# c:\Users\Codeternal\Desktop\AgroPulse\app\iot\fleet_management\main.py

"""
Main CLI and Orchestrator for Fleet Management
==============================================

This script serves as the main entry point and orchestrator for the entire
fleet management system. It provides a command-line interface (CLI) to run the
system, and it brings all the individual components (registry, communication,
scheduling, maintenance) together to form a cohesive application.

The script simulates a real-world backend service that would run continuously
to manage the fleet.

Core Functionality:
-------------------
1.  **Initialization**:
    -   It initializes all the singleton services: `FleetRegistry`,
      `FleetCommunicationService`, `FleetScheduler`, `MaintenanceScheduler`, etc.
    -   It loads any existing fleet data from a persisted file (`fleet_data.json`),
      allowing the system to maintain state between restarts.
    -   It populates the registry with some sample vehicles if the registry is empty,
      which is useful for demonstrations.

2.  **Simulation of Real-time Operations**:
    -   It starts the `FleetCommunicationService`'s telemetry simulation, which
      runs in a background thread to mimic a constant stream of data coming from
      the vehicles. This continuously updates vehicle locations, statuses, and

      operating hours.

3.  **Periodic Task Execution**:
    -   The main part of the script is a `while True` loop that simulates a
      master control program or a cron-based job scheduler.
    -   **Scheduling Cycle**: Every 15 seconds, it runs the `FleetScheduler`, which
      checks the `TaskQueue` for pending operational tasks (like plowing or
      spraying) and assigns them to available vehicles.
    -   **Maintenance Cycle**: Every 60 seconds, it runs the `MaintenancePredictor`
      to check for vehicles that are due for service. If any are found, it uses
      the `MaintenanceScheduler` to create high-priority maintenance tasks.
    -   **Reporting Cycle**: Every 2 minutes, it calls the `FleetAnalyticsService`
      to generate and print a comprehensive daily report, providing a snapshot of
      the fleet's health and performance.

4.  **Graceful Shutdown**:
    -   It catches `KeyboardInterrupt` (Ctrl+C) to allow for a graceful shutdown.
    -   On exit, it stops the telemetry simulation and, crucially, saves the
      current state of the `FleetRegistry` back to disk. This ensures that all
      changes made during the session (new telemetry, updated operating hours,
      maintenance logs) are preserved.

How to Run:
-----------
```bash
python -m app.iot.fleet_management.main
```
This command starts the main loop, and you can observe the system's operations
through the console logs. You will see telemetry updates, scheduling decisions,
maintenance checks, and periodic reports.
"""

import time
import logging
import os
import sys

# Ensure the parent directory is in the path to allow for absolute imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..')))

from app.iot.fleet_management import (
    get_fleet_registry,
    get_communication_service,
    Vehicle,
    VehicleType,
    VehicleStatus,
    TaskDefinition,
    TaskPriority
)
from app.iot.fleet_management.scheduling import scheduler, task_queue
from app.iot.fleet_management.maintenance import maintenance_predictor, maintenance_scheduler
from app.iot.fleet_management.analytics import analytics_service

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Constants ---
FLEET_DATA_FILE = "fleet_data.json"
SCHEDULING_INTERVAL_SEC = 15
MAINTENANCE_CHECK_INTERVAL_SEC = 60
ANALYTICS_REPORT_INTERVAL_SEC = 120
TELEMETRY_SIM_INTERVAL_SEC = 10

def setup_initial_state():
    """
    Loads data from disk or sets up a default initial state for the fleet.
    """
    registry = get_fleet_registry()
    
    # Try to load existing data
    if os.path.exists(FLEET_DATA_FILE):
        if registry.load_from_disk(FLEET_DATA_FILE):
            logging.info(f"Successfully loaded {len(registry.get_all_vehicles())} vehicles from {FLEET_DATA_FILE}.")
            return

    # If loading fails or file doesn't exist, create a default fleet
    logging.info("No existing data found or load failed. Creating a default fleet for demonstration.")
    
    default_vehicles = [
        Vehicle(vehicle_id="TRACTOR_01", vin="DEMOVIN0000000001", make="John Deere", model="8R 370", year=2022, vehicle_type=VehicleType.TRACTOR, status=VehicleStatus.IDLE),
        Vehicle(vehicle_id="DRONE_01", vin="DEMOVIN0000000002", make="DJI", model="Agras T30", year=2023, vehicle_type=VehicleType.DRONE, status=VehicleStatus.IDLE),
        Vehicle(vehicle_id="HARVESTER_01", vin="DEMOVIN0000000003", make="CLAAS", model="Lexion 8900", year=2021, vehicle_type=VehicleType.COMBINE_HARVESTER, status=VehicleStatus.MAINTENANCE),
        Vehicle(vehicle_id="SPRAYER_01", vin="DEMOVIN0000000004", make="Case IH", model="Patriot 4440", year=2023, vehicle_type=VehicleType.SPRAYER, status=VehicleStatus.IDLE),
    ]
    for v in default_vehicles:
        registry.add_vehicle(v)

    # Add some demo tasks to the queue
    task_queue.add_task(TaskDefinition(
        task_type="field_scouting",
        required_vehicle_type=VehicleType.DRONE,
        priority=TaskPriority.HIGH,
        target_area={"type": "Polygon", "coordinates": [[[-100, 40], [-100, 41], [-101, 41], [-100, 40]]]},
        estimated_duration_hours=1.5
    ))
    task_queue.add_task(TaskDefinition(
        task_type="plowing_field_B7",
        required_vehicle_type=VehicleType.TRACTOR,
        priority=TaskPriority.MEDIUM,
        target_area={"type": "Polygon", "coordinates": [[[-102, 42], [-102, 43], [-103, 43], [-102, 42]]]},
        estimated_duration_hours=8.0
    ))


def main_loop():
    """
    The main continuous loop that orchestrates all fleet management services.
    """
    comm_service = get_communication_service()
    
    # Start the background simulation of incoming telemetry data
    comm_service.connect()
    comm_service.start_simulation(interval_seconds=TELEMETRY_SIM_INTERVAL_SEC)

    last_scheduling_run = 0
    last_maintenance_run = 0
    last_analytics_run = 0

    logging.info("Starting main fleet management orchestration loop. Press Ctrl+C to exit.")
    try:
        while True:
            current_time = time.time()

            # --- Run Operational Task Scheduler ---
            if current_time - last_scheduling_run > SCHEDULING_INTERVAL_SEC:
                logging.info("--- [CYCLE] Running Operational Scheduler ---")
                scheduler.schedule_pending_tasks()
                last_scheduling_run = current_time

            # --- Run Preventive Maintenance Scheduler ---
            if current_time - last_maintenance_run > MAINTENANCE_CHECK_INTERVAL_SEC:
                logging.info("--- [CYCLE] Running Maintenance Predictor & Scheduler ---")
                due_vehicles = maintenance_predictor.check_for_due_maintenance()
                maintenance_scheduler.schedule_maintenance_tasks(due_vehicles)
                last_maintenance_run = current_time

            # --- Run Analytics and Reporting ---
            if current_time - last_analytics_run > ANALYTICS_REPORT_INTERVAL_SEC:
                logging.info("--- [CYCLE] Generating Fleet Analytics Report ---")
                report = analytics_service.generate_daily_report()
                print("\n" + "="*80)
                print("FLEET ANALYTICS SNAPSHOT")
                print(f"Generated at: {report['report_generated_at']}")
                print(f"Total Vehicles: {report['total_vehicles']}")
                print(f"Status Distribution: {report['fleet_status_distribution']}")
                print(f"Vehicles Due for Service: {report['vehicles_due_for_maintenance']}")
                print(f"Costs (last 24h): ${report['costs_last_24_hours']['total_fleet_cost_usd']:.2f}")
                print("="*80 + "\n")
                last_analytics_run = current_time

            time.sleep(1) # Main loop sleeps briefly to prevent busy-waiting

    except KeyboardInterrupt:
        logging.info("Shutdown signal received.")
    finally:
        # --- Graceful Shutdown ---
        logging.info("Stopping services and saving state...")
        comm_service.stop_simulation()
        
        registry = get_fleet_registry()
        if registry.save_to_disk(FLEET_DATA_FILE):
            logging.info(f"Fleet state successfully saved to {FLEET_DATA_FILE}.")
        else:
            logging.error("Failed to save fleet state on exit.")
        
        logging.info("Fleet Management System has shut down.")


if __name__ == "__main__":
    setup_initial_state()
    main_loop()
```