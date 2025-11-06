# c:\Users\Codeternal\Desktop\AgroPulse\app\iot\fleet_management\scheduling.py

"""
Fleet Task Scheduling and Dispatch System
=========================================

This module provides a sophisticated system for scheduling, assigning, and
tracking tasks for the vehicle fleet. It includes models for defining tasks,
a scheduler for optimal resource allocation, and a dispatcher for managing the
lifecycle of assigned tasks.

Core Components:
-------------
1.  **Task Models**:
    -   `TaskStatus(Enum)`: Defines the states a task can be in (e.g., PENDING,
      ASSIGNED, IN_PROGRESS, COMPLETED, FAILED).
    -   `TaskPriority(IntEnum)`: Allows for prioritizing tasks (e.g., LOW, MEDIUM,
      HIGH, URGENT).
    -   `TaskDefinition`: A Pydantic model that defines a task, including its
      type (e.g., 'plowing', 'spraying'), the area it applies to (as a GeoJSON
      Polygon), its priority, and any specific parameters.
    -   `AssignedTask`: A model that links a `TaskDefinition` to a specific
      `vehicle_id` and tracks its real-time status and progress.

2.  **`TaskQueue`**:
    -   **Purpose**: A thread-safe, priority-based queue for managing all pending
      tasks.
    -   **Functionality**: It uses Python's `heapq` module to ensure that when a
      task is requested, the one with the highest priority (and oldest submission
      time, as a tie-breaker) is always returned first.

3.  **`FleetScheduler`**:
    -   **Purpose**: The brain of the scheduling system. It's responsible for
      intelligently assigning tasks from the queue to the most suitable available
      vehicles.
    -   **`_find_best_vehicle_for_task()`**: The core logic for assignment. It
      considers multiple factors:
        -   **Vehicle Status**: Only assigns tasks to `IDLE` vehicles.
        -   **Vehicle Type**: Matches the task's required vehicle type (e.g., a
          'spraying' task needs a `SPRAYER`).
        -   **Proximity**: (Conceptual) In a real system, it would calculate the
          distance between the vehicle's current location and the task area to
          minimize travel time.
    -   **`schedule_pending_tasks()`**: The main method that runs periodically. It
      fetches pending tasks from the queue and attempts to assign each one to an
      optimal vehicle using the matching logic.

4.  **`FleetDispatcher`**:
    -   **Purpose**: Manages the lifecycle of tasks that have been assigned to
      vehicles.
    -   **`dispatch_task()`**: "Sends" the task to the vehicle by publishing a
      command via the `FleetCommunicationService`.
    -   **`update_task_status()`**: Provides a method to update the status of an
      assigned task (e.g., from `ASSIGNED` to `IN_PROGRESS` when the vehicle
      confirms it has started).
    -   **`get_task_by_vehicle()`**: Retrieves the currently active task for a
      specific vehicle.

This module provides a complete, albeit simulated, workflow for automated fleet
operations: tasks are created and queued, the scheduler assigns them to optimal
vehicles, and the dispatcher manages their execution.
"""

import heapq
import threading
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from enum import Enum, IntEnum
import uuid
import logging

from pydantic import BaseModel, Field

from .registry import get_fleet_registry
from .communication import get_communication_service
from .vehicle import Vehicle, VehicleStatus, VehicleType, Location

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Task Models ---

class TaskStatus(str, Enum):
    PENDING = "pending"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class TaskPriority(IntEnum):
    LOW = 4
    MEDIUM = 3
    HIGH = 2
    URGENT = 1

class TaskDefinition(BaseModel):
    """Defines a task to be performed by the fleet."""
    task_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    task_type: str = Field(..., description="Type of task, e.g., 'plowing', 'spraying', 'scouting'.")
    required_vehicle_type: VehicleType
    priority: TaskPriority = TaskPriority.MEDIUM
    creation_time: datetime = Field(default_factory=datetime.utcnow)
    
    # GeoJSON-like field for the target area
    target_area: Dict[str, Any] = Field(..., description="A GeoJSON Polygon defining the work area.")
    
    estimated_duration_hours: float = Field(..., description="Estimated time to complete the task.", gt=0)
    task_parameters: Dict[str, Any] = Field(default_factory=dict, description="Specific parameters for the task, e.g., {'spray_rate': 5.5}")

class AssignedTask(BaseModel):
    """Represents a task that has been assigned to a vehicle."""
    task_definition: TaskDefinition
    vehicle_id: str
    status: TaskStatus = TaskStatus.ASSIGNED
    assign_time: datetime = Field(default_factory=datetime.utcnow)
    start_time: Optional[datetime] = None
    completion_time: Optional[datetime] = None
    progress_percent: float = Field(0.0, ge=0, le=100)
    notes: str = ""

# --- Task Queue ---

class TaskQueue:
    """A thread-safe, priority-based queue for pending tasks."""
    def __init__(self):
        self._queue: List[Tuple[int, datetime, TaskDefinition]] = []
        self._lock = threading.Lock()

    def add_task(self, task: TaskDefinition):
        """Adds a task to the priority queue."""
        with self._lock:
            # heapq uses a min-heap, so priority is the first element.
            # creation_time is the tie-breaker.
            heapq.heappush(self._queue, (task.priority, task.creation_time, task))
            logging.info(f"Task {task.task_id} (Priority: {task.priority.name}) added to the queue.")

    def get_next_task(self) -> Optional[TaskDefinition]:
        """Retrieves and removes the highest-priority task from the queue."""
        with self._lock:
            if not self._queue:
                return None
            _, _, task = heapq.heappop(self._queue)
            logging.info(f"Retrieved task {task.task_id} from the queue.")
            return task

    def is_empty(self) -> bool:
        with self._lock:
            return len(self._queue) == 0

# --- Scheduler and Dispatcher ---

class FleetScheduler:
    """Assigns pending tasks to available and suitable vehicles."""
    def __init__(self, task_queue: TaskQueue, dispatcher: 'FleetDispatcher'):
        self._registry = get_fleet_registry()
        self._task_queue = task_queue
        self._dispatcher = dispatcher
        logging.info("FleetScheduler initialized.")

    def _find_best_vehicle_for_task(self, task: TaskDefinition) -> Optional[Vehicle]:
        """Finds the most suitable available vehicle for a given task."""
        idle_vehicles = self._registry.get_vehicles_by_status(VehicleStatus.IDLE)
        
        suitable_vehicles = [
            v for v in idle_vehicles 
            if v.vehicle_type == task.required_vehicle_type
        ]

        if not suitable_vehicles:
            logging.debug(f"No idle vehicles of type {task.required_vehicle_type.value} available for task {task.task_id}.")
            return None

        # Simple strategy: return the first suitable vehicle.
        # A more advanced strategy would consider proximity to the task location,
        # operating hours, fuel/battery level, etc.
        # For now, we'll just pick the first one.
        best_vehicle = suitable_vehicles[0]
        logging.info(f"Found best vehicle {best_vehicle.vehicle_id} for task {task.task_id}.")
        return best_vehicle

    def schedule_pending_tasks(self):
        """Iterates through the task queue and tries to assign tasks."""
        logging.info("Running scheduling cycle...")
        if self._task_queue.is_empty():
            logging.info("Task queue is empty. Nothing to schedule.")
            return

        task_to_schedule = self._task_queue.get_next_task()
        if not task_to_schedule:
            return

        vehicle = self._find_best_vehicle_for_task(task_to_schedule)

        if vehicle:
            assigned_task = AssignedTask(
                task_definition=task_to_schedule,
                vehicle_id=vehicle.vehicle_id
            )
            self._dispatcher.dispatch_task(assigned_task)
            # Set vehicle status to assigned/in-transit
            self._registry.update_vehicle(vehicle.vehicle_id, {"status": VehicleStatus.IN_TRANSIT})
        else:
            # If no vehicle is found, put the task back in the queue
            logging.warning(f"No suitable vehicle found for task {task_to_schedule.task_id}. Re-queuing.")
            self._task_queue.add_task(task_to_schedule)

class FleetDispatcher:
    """Manages the lifecycle of assigned tasks and communicates with vehicles."""
    def __init__(self):
        self._comm_service = get_communication_service()
        self._active_tasks: Dict[str, AssignedTask] = {} # vehicle_id -> AssignedTask
        self._lock = threading.Lock()
        logging.info("FleetDispatcher initialized.")

    def dispatch_task(self, task: AssignedTask):
        """Sends the task command to the assigned vehicle."""
        with self._lock:
            self._active_tasks[task.vehicle_id] = task
        
        command = {
            "command": "start_task",
            "task_details": task.task_definition.dict()
        }
        self._comm_service.publish_command(task.vehicle_id, command)
        logging.info(f"Dispatched task {task.task_definition.task_id} to vehicle {task.vehicle_id}.")

    def update_task_status(self, vehicle_id: str, status: TaskStatus, progress: Optional[float] = None):
        """Updates the status of an active task."""
        with self._lock:
            task = self._active_tasks.get(vehicle_id)
            if not task:
                logging.warning(f"No active task found for vehicle {vehicle_id} to update status.")
                return

            task.status = status
            if status == TaskStatus.IN_PROGRESS and task.start_time is None:
                task.start_time = datetime.utcnow()
            
            if progress is not None:
                task.progress_percent = progress

            if status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]:
                task.completion_time = datetime.utcnow()
                # Make the vehicle available again
                get_fleet_registry().update_vehicle(vehicle_id, {"status": VehicleStatus.IDLE})
                # Remove from active tasks
                del self._active_tasks[vehicle_id]
                logging.info(f"Task {task.task_definition.task_id} for vehicle {vehicle_id} is now {status.value}. Vehicle is now IDLE.")
            else:
                logging.info(f"Updated task {task.task_definition.task_id} for vehicle {vehicle_id} to status {status.value}.")

    def get_task_by_vehicle(self, vehicle_id: str) -> Optional[AssignedTask]:
        """Gets the current task for a specific vehicle."""
        with self._lock:
            return self._active_tasks.get(vehicle_id)

# --- Global Instances ---
task_queue = TaskQueue()
dispatcher = FleetDispatcher()
scheduler = FleetScheduler(task_queue, dispatcher)

# Example Usage
if __name__ == "__main__":
    # 1. Ensure registry has vehicles
    registry = get_fleet_registry()
    if not registry.get_all_vehicles():
        tractor = Vehicle(vin="SCHEDULINGTRACTOR1", make="Fendt", model="900 Vario", year=2023, vehicle_type=VehicleType.TRACTOR, status=VehicleStatus.IDLE)
        sprayer = Vehicle(vin="SCHEDULINGSPRAYER1", make="John Deere", model="R4045", year=2022, vehicle_type=VehicleType.SPRAYER, status=VehicleStatus.IDLE)
        registry.add_vehicle(tractor)
        registry.add_vehicle(sprayer)

    # 2. Create some tasks
    plowing_task = TaskDefinition(
        task_type="plowing",
        required_vehicle_type=VehicleType.TRACTOR,
        priority=TaskPriority.MEDIUM,
        target_area={"type": "Polygon", "coordinates": [[[-118.0, 34.0], [-118.0, 34.1], [-118.1, 34.1], [-118.1, 34.0], [-118.0, 34.0]]]},
        estimated_duration_hours=4.0
    )
    
    spraying_task_urgent = TaskDefinition(
        task_type="spraying",
        required_vehicle_type=VehicleType.SPRAYER,
        priority=TaskPriority.URGENT,
        target_area={"type": "Polygon", "coordinates": [[[-118.2, 34.2], [-118.2, 34.3], [-118.3, 34.3], [-118.3, 34.2], [-118.2, 34.2]]]},
        estimated_duration_hours=2.5,
        task_parameters={"spray_rate": 7.0, "chemical": "Herbicide-A"}
    )

    # 3. Add tasks to the queue
    task_queue.add_task(plowing_task)
    task_queue.add_task(spraying_task_urgent)

    # 4. Run the scheduler
    # The urgent spraying task should be scheduled first
    print("\n--- Running first scheduling cycle ---")
    scheduler.schedule_pending_tasks()
    
    sprayer_vehicle = registry.get_vehicle("SCHEDULINGSPRAYER1")
    print(f"Sprayer status after scheduling: {sprayer_vehicle.status}")
    active_sprayer_task = dispatcher.get_task_by_vehicle(sprayer_vehicle.vehicle_id)
    print(f"Active task for sprayer: {active_sprayer_task.task_definition.task_type if active_sprayer_task else 'None'}")

    # 5. Simulate task progress
    dispatcher.update_task_status(sprayer_vehicle.vehicle_id, TaskStatus.IN_PROGRESS, progress=50.0)
    
    # 6. Run scheduler again. Now the plowing task should be assigned.
    print("\n--- Running second scheduling cycle ---")
    scheduler.schedule_pending_tasks()
    
    tractor_vehicle = registry.get_vehicle("SCHEDULINGTRACTOR1")
    print(f"Tractor status after scheduling: {tractor_vehicle.status}")
    active_tractor_task = dispatcher.get_task_by_vehicle(tractor_vehicle.vehicle_id)
    print(f"Active task for tractor: {active_tractor_task.task_definition.task_type if active_tractor_task else 'None'}")

    # 7. Simulate task completion
    dispatcher.update_task_status(sprayer_vehicle.vehicle_id, TaskStatus.COMPLETED)
    print(f"\nSprayer status after task completion: {sprayer_vehicle.status}")
    print(f"Is there an active task for the sprayer? {'Yes' if dispatcher.get_task_by_vehicle(sprayer_vehicle.vehicle_id) else 'No'}")
```