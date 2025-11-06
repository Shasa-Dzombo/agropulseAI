"""
Advanced Swarm Coordination and Multi-Drone Management System

This module provides sophisticated multi-drone coordination capabilities:
- Distributed task allocation and scheduling
- Collision avoidance with dynamic path planning
- Swarm formation control and maintenance
- Cooperative sensing and data fusion
- Load balancing across drone fleet
- Communication protocol management
- Fault tolerance and redundancy
- Energy-aware mission planning
- Consensus algorithms for distributed decision making
- Leader-follower and virtual structure formations
- Market-based task assignment
- Real-time swarm optimization
- Emergency response coordination

Author: AgroPulse Development Team
Version: 3.0.0
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
from typing import Dict, List, Tuple, Optional, Any, Set
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import json
from pathlib import Path
from scipy import optimize, spatial
from scipy.spatial import Voronoi, Delaunay, ConvexHull
from sklearn.cluster import KMeans, DBSCAN
import networkx as nx
from collections import deque, defaultdict
import heapq
import threading
import queue
import warnings
warnings.filterwarnings('ignore')


class DroneRole(Enum):
    """Roles drones can assume in swarm"""
    LEADER = "Leader"
    FOLLOWER = "Follower"
    SCOUT = "Scout"
    WORKER = "Worker"
    RELAY = "Communication Relay"
    BACKUP = "Backup"
    SPECIALIST = "Specialist"


class SwarmFormation(Enum):
    """Swarm formation types"""
    LINE = "Line"
    COLUMN = "Column"
    WEDGE = "Wedge"
    DIAMOND = "Diamond"
    CIRCLE = "Circle"
    GRID = "Grid"
    RANDOM = "Random"
    ADAPTIVE = "Adaptive"


class TaskType(Enum):
    """Types of tasks drones can perform"""
    MONITORING = "Monitoring"
    SPRAYING = "Spraying"
    POLLINATION = "Pollination"
    MAPPING = "Mapping"
    INSPECTION = "Inspection"
    TRANSPORT = "Transport"
    RELAY = "Communication Relay"
    CHARGING = "Charging"


class TaskStatus(Enum):
    """Task execution status"""
    PENDING = "Pending"
    ASSIGNED = "Assigned"
    IN_PROGRESS = "In Progress"
    COMPLETED = "Completed"
    FAILED = "Failed"
    CANCELLED = "Cancelled"


class CommunicationProtocol(Enum):
    """Communication protocols"""
    WIFI = "WiFi"
    LORA = "LoRa"
    CELLULAR = "Cellular 4G/5G"
    ZIGBEE = "ZigBee"
    MESH = "Mesh Network"


@dataclass
class DroneState:
    """Complete state information for a drone"""
    drone_id: str
    position: Tuple[float, float, float]  # x, y, z (meters)
    velocity: Tuple[float, float, float]  # vx, vy, vz (m/s)
    orientation: Tuple[float, float, float]  # roll, pitch, yaw (radians)
    battery_percent: float
    payload_capacity_kg: float
    current_load_kg: float
    role: DroneRole
    assigned_tasks: List[str]
    status: str
    communication_range_m: float
    sensor_range_m: float
    max_speed_mps: float
    timestamp: datetime
    neighbors: List[str] = field(default_factory=list)
    health_status: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Task:
    """Task definition"""
    task_id: str
    task_type: TaskType
    priority: int  # 1-10, higher is more urgent
    location: Tuple[float, float, float]
    area_coverage_m2: float
    estimated_duration_min: float
    required_capabilities: List[str]
    deadline: Optional[datetime]
    status: TaskStatus
    assigned_drone: Optional[str]
    dependencies: List[str] = field(default_factory=list)
    payload_required_kg: float = 0.0
    energy_required_wh: float = 0.0


@dataclass
class SwarmMetrics:
    """Performance metrics for swarm"""
    total_drones: int
    active_drones: int
    tasks_completed: int
    tasks_pending: int
    average_battery: float
    communication_efficiency: float
    coverage_area_m2: float
    collision_avoidance_events: int
    average_task_completion_time: float
    swarm_cohesion: float
    load_balance_variance: float


class DistributedTaskAllocator:
    """
    Market-based task allocation using auction mechanism
    Implements Contract Net Protocol (CNP) for distributed task assignment
    """
    
    def __init__(self, communication_delay_ms: float = 100):
        self.task_queue = []
        self.bids = defaultdict(list)
        self.allocations = {}
        self.communication_delay = communication_delay_ms / 1000.0
    
    def allocate_tasks(self,
                      tasks: List[Task],
                      drones: List[DroneState]) -> Dict[str, List[str]]:
        """
        Allocate tasks to drones using market-based mechanism
        
        Args:
            tasks: List of tasks to allocate
            drones: List of available drones
        
        Returns:
            Dictionary mapping drone_id to list of task_ids
        """
        allocations = defaultdict(list)
        
        # Sort tasks by priority and deadline
        sorted_tasks = sorted(
            tasks,
            key=lambda t: (-t.priority, t.deadline or datetime.max)
        )
        
        for task in sorted_tasks:
            if task.status != TaskStatus.PENDING:
                continue
            
            # Request bids from all drones
            bids = self._request_bids(task, drones)
            
            if not bids:
                continue
            
            # Select winner (lowest cost bid)
            winner_drone, winning_bid = min(bids, key=lambda x: x[1])
            
            # Allocate task
            allocations[winner_drone].append(task.task_id)
            task.status = TaskStatus.ASSIGNED
            task.assigned_drone = winner_drone
        
        return dict(allocations)
    
    def _request_bids(self,
                     task: Task,
                     drones: List[DroneState]) -> List[Tuple[str, float]]:
        """
        Request bids from drones for a task
        
        Args:
            task: Task to bid on
            drones: Available drones
        
        Returns:
            List of (drone_id, bid_cost) tuples
        """
        bids = []
        
        for drone in drones:
            # Check if drone can perform task
            if not self._can_perform_task(drone, task):
                continue
            
            # Calculate bid cost
            cost = self._calculate_bid_cost(drone, task)
            
            bids.append((drone.drone_id, cost))
        
        return bids
    
    def _can_perform_task(self, drone: DroneState, task: Task) -> bool:
        """Check if drone can perform task"""
        # Check battery
        if drone.battery_percent < 20:
            return False
        
        # Check payload capacity
        if task.payload_required_kg > (drone.payload_capacity_kg - drone.current_load_kg):
            return False
        
        # Check if already overloaded
        if len(drone.assigned_tasks) >= 5:
            return False
        
        return True
    
    def _calculate_bid_cost(self, drone: DroneState, task: Task) -> float:
        """
        Calculate bid cost for drone to perform task
        Lower cost = better suited
        
        Considers:
        - Distance to task
        - Current workload
        - Battery level
        - Payload availability
        """
        # Distance cost
        distance = np.linalg.norm(
            np.array(drone.position[:2]) - np.array(task.location[:2])
        )
        distance_cost = distance * 1.0
        
        # Workload cost
        workload_cost = len(drone.assigned_tasks) * 100
        
        # Battery cost (higher cost if low battery)
        battery_cost = (100 - drone.battery_percent) * 2.0
        
        # Payload cost
        payload_utilization = drone.current_load_kg / drone.payload_capacity_kg
        payload_cost = payload_utilization * 50
        
        # Priority adjustment (reduce cost for high priority tasks)
        priority_factor = 1.0 / task.priority
        
        total_cost = (distance_cost + workload_cost + battery_cost + payload_cost) * priority_factor
        
        return total_cost


class CollisionAvoidanceSystem:
    """
    Advanced collision avoidance using velocity obstacles and artificial potential fields
    """
    
    def __init__(self, safety_distance_m: float = 5.0):
        self.safety_distance = safety_distance_m
        self.collision_events = 0
    
    def compute_safe_velocities(self,
                               drones: List[DroneState],
                               time_horizon: float = 5.0) -> Dict[str, Tuple[float, float, float]]:
        """
        Compute collision-free velocities for all drones
        
        Args:
            drones: List of drone states
            time_horizon: Time horizon for collision prediction (seconds)
        
        Returns:
            Dictionary mapping drone_id to safe velocity vector
        """
        safe_velocities = {}
        
        for drone in drones:
            # Get nearby drones
            neighbors = self._get_neighbors(drone, drones)
            
            # Compute velocity obstacles
            vo_constraints = self._compute_velocity_obstacles(
                drone, neighbors, time_horizon
            )
            
            # Compute artificial potential field
            attractive_force = self._compute_attractive_force(drone)
            repulsive_force = self._compute_repulsive_force(drone, neighbors)
            
            # Combine forces
            total_force = attractive_force + repulsive_force
            
            # Convert to velocity (with max speed constraint)
            desired_velocity = total_force * 0.5
            speed = np.linalg.norm(desired_velocity)
            
            if speed > drone.max_speed_mps:
                desired_velocity = desired_velocity / speed * drone.max_speed_mps
            
            # Check against velocity obstacles
            if self._is_velocity_safe(desired_velocity, vo_constraints):
                safe_velocities[drone.drone_id] = tuple(desired_velocity)
            else:
                # Find alternative safe velocity
                safe_vel = self._find_safe_velocity(
                    desired_velocity, vo_constraints, drone.max_speed_mps
                )
                safe_velocities[drone.drone_id] = safe_vel
        
        return safe_velocities
    
    def _get_neighbors(self,
                      drone: DroneState,
                      all_drones: List[DroneState],
                      radius: float = 50.0) -> List[DroneState]:
        """Get neighboring drones within radius"""
        neighbors = []
        
        for other in all_drones:
            if other.drone_id == drone.drone_id:
                continue
            
            distance = np.linalg.norm(
                np.array(drone.position) - np.array(other.position)
            )
            
            if distance < radius:
                neighbors.append(other)
        
        return neighbors
    
    def _compute_velocity_obstacles(self,
                                   drone: DroneState,
                                   neighbors: List[DroneState],
                                   time_horizon: float) -> List[np.ndarray]:
        """Compute velocity obstacle cones for neighbors"""
        vo_constraints = []
        
        for neighbor in neighbors:
            # Relative position
            rel_pos = np.array(neighbor.position) - np.array(drone.position)
            distance = np.linalg.norm(rel_pos)
            
            if distance < 0.1:
                continue
            
            # Relative velocity
            rel_vel = np.array(neighbor.velocity) - np.array(drone.velocity)
            
            # Compute velocity obstacle cone
            # VO = {v : (p_i + v*tau) collides with (p_j + v_j*tau) for tau in [0, T]}
            
            # Simplified: velocities that lead to collision within time_horizon
            collision_cone_angle = np.arcsin(self.safety_distance / distance)
            cone_direction = rel_pos / distance
            
            vo_constraints.append({
                'center': rel_vel,
                'direction': cone_direction,
                'angle': collision_cone_angle,
                'distance': distance
            })
        
        return vo_constraints
    
    def _compute_attractive_force(self, drone: DroneState) -> np.ndarray:
        """Compute attractive force toward goal"""
        # Simplified: assume goal is maintaining altitude and moving forward
        goal_force = np.array([1.0, 0.0, 0.0])  # Move forward
        
        # Scale by distance to goal
        force_magnitude = 2.0
        
        return goal_force * force_magnitude
    
    def _compute_repulsive_force(self,
                                drone: DroneState,
                                neighbors: List[DroneState]) -> np.ndarray:
        """Compute repulsive force from obstacles/neighbors"""
        total_repulsion = np.zeros(3)
        
        for neighbor in neighbors:
            rel_pos = np.array(drone.position) - np.array(neighbor.position)
            distance = np.linalg.norm(rel_pos)
            
            if distance < 0.1:
                distance = 0.1
            
            # Repulsive potential: U_rep = k * (1/d - 1/d0)^2
            if distance < self.safety_distance * 3:
                repulsion_magnitude = 5.0 * (1.0 / distance - 1.0 / (self.safety_distance * 3)) ** 2
                repulsion_direction = rel_pos / distance
                total_repulsion += repulsion_direction * repulsion_magnitude
        
        return total_repulsion
    
    def _is_velocity_safe(self,
                         velocity: np.ndarray,
                         vo_constraints: List[Dict]) -> bool:
        """Check if velocity is collision-free"""
        for vo in vo_constraints:
            # Check if velocity is inside velocity obstacle cone
            rel_vel = velocity - vo['center']
            
            if np.linalg.norm(rel_vel) < 0.1:
                continue
            
            # Check angle
            cos_angle = np.dot(rel_vel, vo['direction']) / (np.linalg.norm(rel_vel) + 1e-6)
            
            if cos_angle > np.cos(vo['angle']):
                return False
        
        return True
    
    def _find_safe_velocity(self,
                           desired_velocity: np.ndarray,
                           vo_constraints: List[Dict],
                           max_speed: float,
                           num_samples: int = 100) -> Tuple[float, float, float]:
        """Find safe velocity closest to desired velocity"""
        best_velocity = np.array([0.0, 0.0, 0.0])
        best_score = float('inf')
        
        # Sample velocity space
        for _ in range(num_samples):
            # Random velocity
            sample_vel = np.random.uniform(-max_speed, max_speed, 3)
            
            if np.linalg.norm(sample_vel) > max_speed:
                sample_vel = sample_vel / np.linalg.norm(sample_vel) * max_speed
            
            # Check if safe
            if self._is_velocity_safe(sample_vel, vo_constraints):
                # Score by similarity to desired velocity
                score = np.linalg.norm(sample_vel - desired_velocity)
                
                if score < best_score:
                    best_score = score
                    best_velocity = sample_vel
        
        return tuple(best_velocity)


class FormationController:
    """
    Maintain swarm formations using virtual structure approach
    """
    
    def __init__(self, formation_type: SwarmFormation = SwarmFormation.GRID):
        self.formation_type = formation_type
        self.spacing = 10.0  # meters between drones
    
    def compute_formation_positions(self,
                                   num_drones: int,
                                   center: Tuple[float, float, float],
                                   heading: float = 0.0) -> List[Tuple[float, float, float]]:
        """
        Compute desired positions for formation
        
        Args:
            num_drones: Number of drones in formation
            center: Formation center position
            heading: Formation heading in radians
        
        Returns:
            List of target positions
        """
        if self.formation_type == SwarmFormation.LINE:
            positions = self._line_formation(num_drones, center, heading)
        elif self.formation_type == SwarmFormation.GRID:
            positions = self._grid_formation(num_drones, center, heading)
        elif self.formation_type == SwarmFormation.WEDGE:
            positions = self._wedge_formation(num_drones, center, heading)
        elif self.formation_type == SwarmFormation.CIRCLE:
            positions = self._circle_formation(num_drones, center)
        else:
            positions = self._grid_formation(num_drones, center, heading)
        
        return positions
    
    def _line_formation(self,
                       num_drones: int,
                       center: Tuple[float, float, float],
                       heading: float) -> List[Tuple[float, float, float]]:
        """Line formation"""
        positions = []
        cx, cy, cz = center
        
        # Drones arranged in a line perpendicular to heading
        for i in range(num_drones):
            offset = (i - num_drones / 2) * self.spacing
            
            # Rotate offset by heading
            x = cx + offset * np.cos(heading + np.pi/2)
            y = cy + offset * np.sin(heading + np.pi/2)
            z = cz
            
            positions.append((x, y, z))
        
        return positions
    
    def _grid_formation(self,
                       num_drones: int,
                       center: Tuple[float, float, float],
                       heading: float) -> List[Tuple[float, float, float]]:
        """Grid formation"""
        positions = []
        cx, cy, cz = center
        
        # Calculate grid dimensions
        cols = int(np.ceil(np.sqrt(num_drones)))
        rows = int(np.ceil(num_drones / cols))
        
        for i in range(num_drones):
            row = i // cols
            col = i % cols
            
            # Position in local grid
            local_x = (col - cols / 2) * self.spacing
            local_y = (row - rows / 2) * self.spacing
            
            # Rotate by heading
            x = cx + local_x * np.cos(heading) - local_y * np.sin(heading)
            y = cy + local_x * np.sin(heading) + local_y * np.cos(heading)
            z = cz
            
            positions.append((x, y, z))
        
        return positions
    
    def _wedge_formation(self,
                        num_drones: int,
                        center: Tuple[float, float, float],
                        heading: float) -> List[Tuple[float, float, float]]:
        """V-shaped wedge formation"""
        positions = []
        cx, cy, cz = center
        
        # Leader at front
        positions.append((cx, cy, cz))
        
        # Others in V-shape
        for i in range(1, num_drones):
            side = 1 if i % 2 == 1 else -1
            rank = (i + 1) // 2
            
            # Offset from leader
            forward_offset = -rank * self.spacing * 0.8
            lateral_offset = side * rank * self.spacing * 0.6
            
            # Rotate by heading
            x = cx + (forward_offset * np.cos(heading) - lateral_offset * np.sin(heading))
            y = cy + (forward_offset * np.sin(heading) + lateral_offset * np.cos(heading))
            z = cz
            
            positions.append((x, y, z))
        
        return positions
    
    def _circle_formation(self,
                         num_drones: int,
                         center: Tuple[float, float, float]) -> List[Tuple[float, float, float]]:
        """Circular formation"""
        positions = []
        cx, cy, cz = center
        
        radius = self.spacing * num_drones / (2 * np.pi)
        
        for i in range(num_drones):
            angle = 2 * np.pi * i / num_drones
            
            x = cx + radius * np.cos(angle)
            y = cy + radius * np.sin(angle)
            z = cz
            
            positions.append((x, y, z))
        
        return positions
    
    def compute_control_inputs(self,
                              drones: List[DroneState],
                              target_positions: List[Tuple[float, float, float]],
                              formation_velocity: Tuple[float, float, float] = (0, 0, 0)) -> Dict[str, Tuple[float, float, float]]:
        """
        Compute control inputs to maintain formation
        
        Args:
            drones: Current drone states
            target_positions: Desired formation positions
            formation_velocity: Velocity of formation as a whole
        
        Returns:
            Dictionary mapping drone_id to velocity command
        """
        control_inputs = {}
        
        # Sort drones by ID for consistent assignment
        sorted_drones = sorted(drones, key=lambda d: d.drone_id)
        
        for i, drone in enumerate(sorted_drones):
            if i >= len(target_positions):
                break
            
            target_pos = target_positions[i]
            current_pos = np.array(drone.position)
            target_pos_array = np.array(target_pos)
            
            # PD controller for position tracking
            position_error = target_pos_array - current_pos
            velocity_error = np.array(formation_velocity) - np.array(drone.velocity)
            
            # Control gains
            kp = 0.8  # Proportional gain
            kd = 0.3  # Derivative gain
            
            # Compute desired velocity
            desired_velocity = kp * position_error + kd * velocity_error
            
            # Limit to max speed
            speed = np.linalg.norm(desired_velocity)
            if speed > drone.max_speed_mps:
                desired_velocity = desired_velocity / speed * drone.max_speed_mps
            
            control_inputs[drone.drone_id] = tuple(desired_velocity)
        
        return control_inputs


class ConsensusAlgorithm:
    """
    Distributed consensus for swarm coordination
    Implements average consensus and leader election
    """
    
    def __init__(self, convergence_threshold: float = 0.01):
        self.convergence_threshold = convergence_threshold
    
    def average_consensus(self,
                         drones: List[DroneState],
                         values: Dict[str, float],
                         max_iterations: int = 100) -> Dict[str, float]:
        """
        Achieve consensus on average value across swarm
        
        Args:
            drones: List of drones
            values: Initial values for each drone
            max_iterations: Maximum consensus iterations
        
        Returns:
            Converged consensus values
        """
        # Build communication graph
        adjacency = self._build_adjacency_matrix(drones)
        
        # Initialize
        current_values = values.copy()
        
        # Consensus iterations
        for iteration in range(max_iterations):
            new_values = {}
            
            for drone in drones:
                # Average with neighbors
                neighbors = [d for d in drones if adjacency[drone.drone_id].get(d.drone_id, False)]
                
                if not neighbors:
                    new_values[drone.drone_id] = current_values[drone.drone_id]
                    continue
                
                neighbor_sum = sum(current_values[n.drone_id] for n in neighbors)
                neighbor_sum += current_values[drone.drone_id]
                count = len(neighbors) + 1
                
                new_values[drone.drone_id] = neighbor_sum / count
            
            # Check convergence
            max_change = max(
                abs(new_values[d.drone_id] - current_values[d.drone_id])
                for d in drones
            )
            
            current_values = new_values
            
            if max_change < self.convergence_threshold:
                break
        
        return current_values
    
    def elect_leader(self,
                    drones: List[DroneState],
                    criteria: str = 'battery') -> str:
        """
        Elect a leader drone based on criteria
        
        Args:
            drones: List of drones
            criteria: Selection criteria (battery, position, id)
        
        Returns:
            Drone ID of elected leader
        """
        if criteria == 'battery':
            # Highest battery
            leader = max(drones, key=lambda d: d.battery_percent)
        elif criteria == 'central':
            # Most central position
            positions = np.array([d.position for d in drones])
            centroid = positions.mean(axis=0)
            distances = [np.linalg.norm(np.array(d.position) - centroid) for d in drones]
            leader = drones[np.argmin(distances)]
        elif criteria == 'id':
            # Lowest ID (deterministic)
            leader = min(drones, key=lambda d: d.drone_id)
        else:
            leader = drones[0]
        
        return leader.drone_id
    
    def _build_adjacency_matrix(self,
                               drones: List[DroneState]) -> Dict[str, Dict[str, bool]]:
        """Build communication adjacency matrix"""
        adjacency = defaultdict(dict)
        
        for i, drone1 in enumerate(drones):
            for j, drone2 in enumerate(drones):
                if i == j:
                    continue
                
                distance = np.linalg.norm(
                    np.array(drone1.position) - np.array(drone2.position)
                )
                
                # Within communication range
                connected = distance < drone1.communication_range_m
                adjacency[drone1.drone_id][drone2.drone_id] = connected
        
        return adjacency


class LoadBalancer:
    """
    Balance workload across drone fleet
    """
    
    def __init__(self):
        self.load_history = defaultdict(list)
    
    def balance_load(self,
                    drones: List[DroneState],
                    tasks: List[Task]) -> Dict[str, List[str]]:
        """
        Redistribute tasks to balance load
        
        Args:
            drones: List of drones
            tasks: List of assigned tasks
        
        Returns:
            Rebalanced task allocation
        """
        # Calculate current load for each drone
        current_loads = self._calculate_loads(drones, tasks)
        
        # Find overloaded and underloaded drones
        avg_load = sum(current_loads.values()) / len(drones)
        overloaded = {d: l for d, l in current_loads.items() if l > avg_load * 1.2}
        underloaded = {d: l for d, l in current_loads.items() if l < avg_load * 0.8}
        
        if not overloaded or not underloaded:
            return {d.drone_id: d.assigned_tasks for d in drones}
        
        # Reassign tasks
        new_allocation = defaultdict(list)
        for drone in drones:
            new_allocation[drone.drone_id] = drone.assigned_tasks.copy()
        
        # Move tasks from overloaded to underloaded
        for overloaded_id in overloaded:
            if not underloaded:
                break
            
            overloaded_drone = next(d for d in drones if d.drone_id == overloaded_id)
            
            # Find tasks that can be reassigned
            for task_id in overloaded_drone.assigned_tasks:
                task = next((t for t in tasks if t.task_id == task_id), None)
                
                if not task or task.status == TaskStatus.IN_PROGRESS:
                    continue
                
                # Find best underloaded drone
                best_drone = None
                best_cost = float('inf')
                
                for underloaded_id in underloaded:
                    underloaded_drone = next(d for d in drones if d.drone_id == underloaded_id)
                    cost = self._reassignment_cost(underloaded_drone, task)
                    
                    if cost < best_cost:
                        best_cost = cost
                        best_drone = underloaded_id
                
                if best_drone:
                    # Reassign
                    new_allocation[overloaded_id].remove(task_id)
                    new_allocation[best_drone].append(task_id)
                    
                    # Update loads
                    current_loads[overloaded_id] -= 1
                    current_loads[best_drone] += 1
                    
                    # Check if balanced
                    if current_loads[best_drone] >= avg_load * 0.9:
                        del underloaded[best_drone]
                    
                    if current_loads[overloaded_id] <= avg_load * 1.1:
                        break
        
        return dict(new_allocation)
    
    def _calculate_loads(self,
                        drones: List[DroneState],
                        tasks: List[Task]) -> Dict[str, float]:
        """Calculate load for each drone"""
        loads = {}
        
        for drone in drones:
            # Load based on number of tasks and their complexity
            task_count = len(drone.assigned_tasks)
            loads[drone.drone_id] = task_count
        
        return loads
    
    def _reassignment_cost(self, drone: DroneState, task: Task) -> float:
        """Calculate cost of reassigning task to drone"""
        # Distance to task
        distance = np.linalg.norm(
            np.array(drone.position[:2]) - np.array(task.location[:2])
        )
        
        # Battery cost
        battery_cost = (100 - drone.battery_percent) * 0.5
        
        return distance + battery_cost


class EnergyOptimizer:
    """
    Optimize energy consumption across swarm
    """
    
    def __init__(self):
        self.energy_model = {
            'hover': 150,  # Watts
            'cruise': 100,  # Watts
            'climb': 200,  # Watts
            'descend': 80   # Watts
        }
    
    def estimate_mission_energy(self,
                               drone: DroneState,
                               tasks: List[Task],
                               flight_plan: List[Tuple[float, float, float]]) -> float:
        """
        Estimate total energy consumption for mission
        
        Args:
            drone: Drone state
            tasks: Tasks to perform
            flight_plan: Planned flight path
        
        Returns:
            Estimated energy in Watt-hours
        """
        total_energy = 0
        
        # Energy for flight
        for i in range(len(flight_plan) - 1):
            p1 = np.array(flight_plan[i])
            p2 = np.array(flight_plan[i + 1])
            
            distance = np.linalg.norm(p2 - p1)
            altitude_change = p2[2] - p1[2]
            
            # Flight time
            flight_time_h = distance / drone.max_speed_mps / 3600
            
            # Energy based on flight mode
            if altitude_change > 1:
                energy = self.energy_model['climb'] * flight_time_h
            elif altitude_change < -1:
                energy = self.energy_model['descend'] * flight_time_h
            else:
                energy = self.energy_model['cruise'] * flight_time_h
            
            total_energy += energy
        
        # Energy for tasks
        for task in tasks:
            # Hovering energy
            hover_time_h = task.estimated_duration_min / 60
            total_energy += self.energy_model['hover'] * hover_time_h
        
        return total_energy
    
    def optimize_flight_path(self,
                            start: Tuple[float, float, float],
                            waypoints: List[Tuple[float, float, float]],
                            end: Tuple[float, float, float]) -> List[Tuple[float, float, float]]:
        """
        Optimize flight path for minimum energy
        
        Args:
            start: Start position
            waypoints: Intermediate waypoints
            end: End position
        
        Returns:
            Optimized path
        """
        # Use traveling salesman problem solver
        points = [start] + waypoints + [end]
        n = len(points)
        
        # Build distance matrix
        dist_matrix = np.zeros((n, n))
        for i in range(n):
            for j in range(n):
                dist_matrix[i, j] = np.linalg.norm(
                    np.array(points[i]) - np.array(points[j])
                )
        
        # Simple greedy solution (can be replaced with better algorithm)
        visited = [0]
        current = 0
        
        while len(visited) < n - 1:
            # Find nearest unvisited
            unvisited = [i for i in range(1, n-1) if i not in visited]
            if not unvisited:
                break
            
            nearest = min(unvisited, key=lambda i: dist_matrix[current, i])
            visited.append(nearest)
            current = nearest
        
        visited.append(n - 1)  # Add end point
        
        # Build optimized path
        optimized_path = [points[i] for i in visited]
        
        return optimized_path


class SwarmCoordinationSystem:
    """
    Main swarm coordination system integrating all components
    """
    
    def __init__(self):
        self.drones: Dict[str, DroneState] = {}
        self.tasks: Dict[str, Task] = {}
        
        self.task_allocator = DistributedTaskAllocator()
        self.collision_avoidance = CollisionAvoidanceSystem()
        self.formation_controller = FormationController()
        self.consensus = ConsensusAlgorithm()
        self.load_balancer = LoadBalancer()
        self.energy_optimizer = EnergyOptimizer()
        
        self.metrics = SwarmMetrics(
            total_drones=0,
            active_drones=0,
            tasks_completed=0,
            tasks_pending=0,
            average_battery=0,
            communication_efficiency=0,
            coverage_area_m2=0,
            collision_avoidance_events=0,
            average_task_completion_time=0,
            swarm_cohesion=0,
            load_balance_variance=0
        )
    
    def register_drone(self, drone: DroneState):
        """Register a drone with the swarm"""
        self.drones[drone.drone_id] = drone
        self.metrics.total_drones = len(self.drones)
    
    def add_task(self, task: Task):
        """Add a task to the task queue"""
        self.tasks[task.task_id] = task
        self.metrics.tasks_pending += 1
    
    def coordinate_swarm(self) -> Dict[str, Any]:
        """
        Main coordination loop
        
        Returns:
            Coordination results and commands
        """
        results = {
            'timestamp': datetime.now(),
            'allocations': {},
            'velocities': {},
            'formation_positions': [],
            'metrics': None
        }
        
        drone_list = list(self.drones.values())
        task_list = [t for t in self.tasks.values() if t.status == TaskStatus.PENDING]
        
        if not drone_list:
            return results
        
        # 1. Task allocation
        allocations = self.task_allocator.allocate_tasks(task_list, drone_list)
        results['allocations'] = allocations
        
        # Update drone assignments
        for drone_id, task_ids in allocations.items():
            if drone_id in self.drones:
                self.drones[drone_id].assigned_tasks.extend(task_ids)
        
        # 2. Load balancing
        balanced_allocation = self.load_balancer.balance_load(drone_list, task_list)
        
        # 3. Formation control
        formation_positions = self.formation_controller.compute_formation_positions(
            num_drones=len(drone_list),
            center=(0, 0, 50),
            heading=0
        )
        results['formation_positions'] = formation_positions
        
        formation_velocities = self.formation_controller.compute_control_inputs(
            drones=drone_list,
            target_positions=formation_positions
        )
        
        # 4. Collision avoidance
        safe_velocities = self.collision_avoidance.compute_safe_velocities(drone_list)
        results['velocities'] = safe_velocities
        
        # 5. Consensus (e.g., agree on formation center)
        if len(drone_list) > 1:
            battery_values = {d.drone_id: d.battery_percent for d in drone_list}
            consensus_battery = self.consensus.average_consensus(drone_list, battery_values)
        
        # 6. Update metrics
        self._update_metrics()
        results['metrics'] = self.metrics
        
        return results
    
    def _update_metrics(self):
        """Update swarm performance metrics"""
        drone_list = list(self.drones.values())
        
        if not drone_list:
            return
        
        # Active drones (battery > 10%)
        self.metrics.active_drones = sum(1 for d in drone_list if d.battery_percent > 10)
        
        # Average battery
        self.metrics.average_battery = np.mean([d.battery_percent for d in drone_list])
        
        # Task statistics
        completed_tasks = [t for t in self.tasks.values() if t.status == TaskStatus.COMPLETED]
        self.metrics.tasks_completed = len(completed_tasks)
        self.metrics.tasks_pending = sum(
            1 for t in self.tasks.values() if t.status == TaskStatus.PENDING
        )
        
        # Swarm cohesion (average distance from centroid)
        positions = np.array([d.position for d in drone_list])
        centroid = positions.mean(axis=0)
        distances = [np.linalg.norm(pos - centroid) for pos in positions]
        self.metrics.swarm_cohesion = 1.0 / (1.0 + np.mean(distances))
        
        # Load balance variance
        task_counts = [len(d.assigned_tasks) for d in drone_list]
        self.metrics.load_balance_variance = np.var(task_counts)
    
    def get_swarm_status(self) -> Dict[str, Any]:
        """Get comprehensive swarm status"""
        return {
            'total_drones': self.metrics.total_drones,
            'active_drones': self.metrics.active_drones,
            'average_battery': f"{self.metrics.average_battery:.1f}%",
            'tasks_completed': self.metrics.tasks_completed,
            'tasks_pending': self.metrics.tasks_pending,
            'swarm_cohesion': f"{self.metrics.swarm_cohesion:.2f}",
            'load_balance_variance': f"{self.metrics.load_balance_variance:.2f}",
            'collision_events': self.metrics.collision_avoidance_events
        }


def main():
    """Demonstration of swarm coordination system"""
    print("=" * 80)
    print("AgroPulse Advanced Swarm Coordination System")
    print("=" * 80)
    
    # Initialize swarm
    swarm = SwarmCoordinationSystem()
    
    # Create drones
    print("\nInitializing drone fleet...")
    for i in range(10):
        drone = DroneState(
            drone_id=f"DRONE_{i:03d}",
            position=(i * 15.0, 0.0, 50.0),
            velocity=(0.0, 0.0, 0.0),
            orientation=(0.0, 0.0, 0.0),
            battery_percent=80.0 + np.random.uniform(-10, 10),
            payload_capacity_kg=5.0,
            current_load_kg=0.0,
            role=DroneRole.WORKER,
            assigned_tasks=[],
            status="Ready",
            communication_range_m=100.0,
            sensor_range_m=50.0,
            max_speed_mps=15.0,
            timestamp=datetime.now()
        )
        swarm.register_drone(drone)
    
    # Create tasks
    print("Creating mission tasks...")
    for i in range(25):
        task = Task(
            task_id=f"TASK_{i:03d}",
            task_type=TaskType.MONITORING,
            priority=np.random.randint(1, 11),
            location=(np.random.uniform(0, 200), np.random.uniform(0, 200), 50.0),
            area_coverage_m2=100.0,
            estimated_duration_min=5.0,
            required_capabilities=["camera", "gps"],
            deadline=datetime.now() + timedelta(hours=2),
            status=TaskStatus.PENDING,
            assigned_drone=None
        )
        swarm.add_task(task)
    
    # Run coordination
    print("\nExecuting swarm coordination...")
    results = swarm.coordinate_swarm()
    
    # Display results
    print("\n" + "=" * 80)
    print("SWARM COORDINATION RESULTS")
    print("=" * 80)
    
    print(f"\nTimestamp: {results['timestamp']}")
    
    print(f"\nTask Allocations:")
    for drone_id, task_ids in results['allocations'].items():
        print(f"  {drone_id}: {len(task_ids)} tasks")
    
    print(f"\nVelocity Commands:")
    for drone_id, velocity in list(results['velocities'].items())[:5]:
        print(f"  {drone_id}: ({velocity[0]:.2f}, {velocity[1]:.2f}, {velocity[2]:.2f}) m/s")
    
    print(f"\nSwarm Status:")
    status = swarm.get_swarm_status()
    for key, value in status.items():
        print(f"  {key}: {value}")
    
    print("\n" + "=" * 80)
    print("Swarm coordination complete!")
    print("=" * 80)


if __name__ == "__main__":
    main()
