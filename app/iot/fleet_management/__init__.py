# c:\Users\Codeternal\Desktop\AgroPulse\app\iot\fleet_management\__init__.py

"""
IoT Fleet Management Package
============================

This package provides a comprehensive, end-to-end system for managing a fleet
of IoT-enabled agricultural vehicles, such as tractors, drones, and harvesters.
It is designed as a modular, microservice-style architecture, where each
component has a distinct responsibility.

The system is built around a central, in-memory `FleetRegistry` that acts as the
single source of truth for the state of all vehicles.

Core Modules:
-------------
-   **`vehicle`**:
    -   Defines the core Pydantic data models for the system, including `Vehicle`,
      `TelemetryData`, and `MaintenanceLog`. This ensures data consistency and
      validation throughout the application.

-   **`registry`**:
    -   Contains the `FleetRegistry`, a singleton service that provides CRUD
      operations and advanced querying for the entire fleet. It's the heart of
      the system, managing all vehicle data in memory.

-   **`communication`**:
    -   Simulates the communication layer, handling incoming data from vehicles
      (typically via MQTT) and providing a mechanism to send commands back to them.
      It includes a simulation engine to generate realistic telemetry data for
      demonstration purposes.

-   **`scheduling`**:
    -   Implements a sophisticated task scheduling and dispatching system. It
      includes a `TaskQueue` for pending tasks, a `FleetScheduler` for intelligent
      task assignment based on vehicle suitability, and a `FleetDispatcher` to
      manage the lifecycle of assigned tasks.

-   **`maintenance`**:
    -   Provides a proactive maintenance management system. The `MaintenancePredictor`
      identifies vehicles due for service based on operating hours, the
      `MaintenanceScheduler` creates high-priority maintenance tasks, and the
      `MaintenanceLogger` records completed work and resets the vehicle's service
      clock.

-   **`analytics`**:
    -   The business intelligence layer of the package. The `FleetAnalyticsService`
      generates reports on key performance indicators (KPIs) like fleet utilization,
      operating costs, and vehicle downtime, turning raw data into actionable
      insights.

This `__init__.py` file makes the `fleet_management` directory a Python package
and exposes the key services and models for easy access by other parts of the
AgroPulse application, such as a web API or a master control program.
"""

# Expose the primary singleton accessors and core models for easy use
from .vehicle import (
    Vehicle,
    VehicleStatus,
    VehicleType,
    TelemetryData,
    MaintenanceLog,
    Location
)
from .registry import get_fleet_registry, FleetRegistry
from .communication import get_communication_service, FleetCommunicationService
from .scheduling import (
    TaskQueue,
    FleetScheduler,
    FleetDispatcher,
    TaskDefinition,
    AssignedTask,
    TaskStatus,
    TaskPriority
)
from .maintenance import (
    MaintenancePredictor,
    MaintenanceScheduler,
    MaintenanceLogger
)
from .analytics import FleetAnalyticsService

__all__ = [
    # vehicle.py
    "Vehicle",
    "VehicleStatus",
    "VehicleType",
    "TelemetryData",
    "MaintenanceLog",
    "Location",
    
    # registry.py
    "get_fleet_registry",
    "FleetRegistry",

    # communication.py
    "get_communication_service",
    "FleetCommunicationService",

    # scheduling.py
    "TaskQueue",
    "FleetScheduler",
    "FleetDispatcher",
    "TaskDefinition",
    "AssignedTask",
    "TaskStatus",
    "TaskPriority",

    # maintenance.py
    "MaintenancePredictor",
    "MaintenanceScheduler",
    "MaintenanceLogger",

    # analytics.py
    "FleetAnalyticsService",
]

__version__ = "0.1.0"
```