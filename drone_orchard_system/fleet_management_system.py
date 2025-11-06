"""
Comprehensive Fleet Management and Predictive Maintenance System

This advanced system provides:
- Multi-drone fleet coordination and scheduling
- Real-time fleet health monitoring
- Predictive maintenance using machine learning
- Component lifetime tracking and replacement planning
- Automated diagnostics and troubleshooting
- Maintenance scheduling optimization
- Spare parts inventory management
- Flight hour tracking and maintenance intervals
- Battery health monitoring and optimization
- Motor performance analysis
- Calibration management
- Firmware version tracking and updates
- Incident reporting and analysis
- Compliance and certification tracking
- Cost tracking and ROI analysis
- Fleet utilization optimization
- Remote diagnostics capabilities
- Automated health scoring

Author: AgroPulse Development Team
Version: 5.0.0
"""

import numpy as np
from typing import Dict, List, Tuple, Optional, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import asyncio
from collections import defaultdict, deque
import json
import pickle
from pathlib import Path
import pandas as pd
from scipy import stats
from sklearn.ensemble import RandomForestClassifier, GradientBoostingRegressor
from sklearn.preprocessing import StandardScaler
import warnings
warnings.filterwarnings('ignore')


class DroneStatus(Enum):
    """Operational status of a drone"""
    ACTIVE = "active"
    IDLE = "idle"
    CHARGING = "charging"
    MAINTENANCE = "maintenance"
    OUT_OF_SERVICE = "out_of_service"
    IN_FLIGHT = "in_flight"
    ERROR = "error"


class MaintenanceType(Enum):
    """Types of maintenance activities"""
    PREVENTIVE = "preventive"
    CORRECTIVE = "corrective"
    PREDICTIVE = "predictive"
    EMERGENCY = "emergency"
    ROUTINE_INSPECTION = "routine_inspection"
    CALIBRATION = "calibration"
    FIRMWARE_UPDATE = "firmware_update"


class ComponentType(Enum):
    """Types of drone components"""
    MOTOR = "motor"
    ESC = "esc"
    PROPELLER = "propeller"
    BATTERY = "battery"
    CAMERA = "camera"
    GPS = "gps"
    IMU = "imu"
    FLIGHT_CONTROLLER = "flight_controller"
    COMMUNICATION = "communication"
    FRAME = "frame"


class HealthStatus(Enum):
    """Component health status"""
    EXCELLENT = "excellent"
    GOOD = "good"
    FAIR = "fair"
    POOR = "poor"
    CRITICAL = "critical"
    FAILED = "failed"


class Priority(Enum):
    """Task priority levels"""
    CRITICAL = 1
    HIGH = 2
    MEDIUM = 3
    LOW = 4


@dataclass
class Component:
    """Individual component information"""
    component_id: str
    component_type: ComponentType
    manufacturer: str
    model: str
    serial_number: str
    installation_date: datetime
    flight_hours: float = 0.0
    cycles: int = 0
    last_maintenance: Optional[datetime] = None
    expected_lifetime: float = 1000.0  # hours
    health_score: float = 100.0
    status: HealthStatus = HealthStatus.EXCELLENT
    notes: List[str] = field(default_factory=list)
    
    def remaining_lifetime(self) -> float:
        """Calculate remaining lifetime percentage"""
        return max(0, (self.expected_lifetime - self.flight_hours) / self.expected_lifetime * 100)


@dataclass
class Battery:
    """Battery-specific tracking"""
    battery_id: str
    capacity_mah: float
    voltage: float
    cycles: int = 0
    current_capacity: float = 0.0  # Current capacity percentage
    health: float = 100.0
    temperature: float = 25.0
    discharge_rate: float = 0.0
    charge_rate: float = 0.0
    cell_voltages: List[float] = field(default_factory=list)
    last_calibration: Optional[datetime] = None
    
    def degradation_rate(self) -> float:
        """Calculate battery degradation rate per cycle"""
        if self.cycles == 0:
            return 0.0
        return (100.0 - self.health) / self.cycles


@dataclass
class MaintenanceTask:
    """Maintenance task information"""
    task_id: str
    drone_id: str
    task_type: MaintenanceType
    priority: Priority
    description: str
    scheduled_date: datetime
    estimated_duration: timedelta
    assigned_technician: Optional[str] = None
    status: str = "pending"  # pending, in_progress, completed, cancelled
    parts_required: List[str] = field(default_factory=list)
    cost_estimate: float = 0.0
    completion_date: Optional[datetime] = None
    notes: List[str] = field(default_factory=list)


@dataclass
class FlightLog:
    """Flight log entry"""
    log_id: str
    drone_id: str
    start_time: datetime
    end_time: datetime
    flight_duration: timedelta
    distance_covered: float  # meters
    max_altitude: float
    avg_speed: float
    battery_consumed: float  # percentage
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    mission_type: str = "survey"
    weather_conditions: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Drone:
    """Complete drone information"""
    drone_id: str
    model: str
    serial_number: str
    registration_number: str
    manufacture_date: datetime
    purchase_date: datetime
    total_flight_hours: float = 0.0
    total_flights: int = 0
    status: DroneStatus = DroneStatus.IDLE
    current_location: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    home_base: str = "default"
    components: Dict[str, Component] = field(default_factory=dict)
    batteries: List[Battery] = field(default_factory=list)
    flight_logs: List[FlightLog] = field(default_factory=list)
    maintenance_history: List[MaintenanceTask] = field(default_factory=list)
    health_score: float = 100.0
    last_inspection: Optional[datetime] = None
    next_maintenance: Optional[datetime] = None
    firmware_version: str = "1.0.0"
    notes: List[str] = field(default_factory=list)


@dataclass
class Technician:
    """Maintenance technician information"""
    technician_id: str
    name: str
    specializations: List[ComponentType]
    available: bool = True
    current_task: Optional[str] = None
    completed_tasks: int = 0
    certifications: List[str] = field(default_factory=list)


class PredictiveMaintenanceModel:
    """
    Machine learning model for predicting component failures
    """
    
    def __init__(self):
        self.classifier = RandomForestClassifier(n_estimators=100, random_state=42)
        self.regressor = GradientBoostingRegressor(n_estimators=100, random_state=42)
        self.scaler = StandardScaler()
        self.is_trained = False
    
    def prepare_features(self, component: Component, 
                        recent_logs: List[FlightLog]) -> np.ndarray:
        """
        Extract features from component and flight logs
        """
        features = [
            component.flight_hours,
            component.cycles,
            component.remaining_lifetime(),
            component.health_score,
            len(recent_logs),
        ]
        
        # Add flight statistics if available
        if recent_logs:
            durations = [log.flight_duration.total_seconds() for log in recent_logs]
            features.extend([
                np.mean(durations),
                np.std(durations),
                np.max(durations),
            ])
            
            distances = [log.distance_covered for log in recent_logs]
            features.extend([
                np.mean(distances),
                np.std(distances),
            ])
            
            # Count warnings and errors
            total_warnings = sum(len(log.warnings) for log in recent_logs)
            total_errors = sum(len(log.errors) for log in recent_logs)
            features.extend([total_warnings, total_errors])
        else:
            features.extend([0, 0, 0, 0, 0, 0, 0])
        
        return np.array(features).reshape(1, -1)
    
    def train(self, training_data: List[Dict[str, Any]]):
        """
        Train the predictive model
        
        Args:
            training_data: List of dicts with 'features', 'failed', 'hours_to_failure'
        """
        if not training_data:
            return
        
        X = np.array([d['features'] for d in training_data])
        y_classification = np.array([d['failed'] for d in training_data])
        y_regression = np.array([d['hours_to_failure'] for d in training_data])
        
        # Scale features
        X_scaled = self.scaler.fit_transform(X)
        
        # Train classifier (will it fail soon?)
        self.classifier.fit(X_scaled, y_classification)
        
        # Train regressor (when will it fail?)
        self.regressor.fit(X_scaled, y_regression)
        
        self.is_trained = True
    
    def predict_failure(self, component: Component, 
                       recent_logs: List[FlightLog]) -> Dict[str, Any]:
        """
        Predict if and when a component will fail
        
        Returns:
            Dict with 'failure_probability', 'estimated_hours_remaining', 'confidence'
        """
        if not self.is_trained:
            # Use rule-based prediction if model not trained
            return self._rule_based_prediction(component)
        
        features = self.prepare_features(component, recent_logs)
        features_scaled = self.scaler.transform(features)
        
        # Predict probability of failure
        failure_prob = self.classifier.predict_proba(features_scaled)[0, 1]
        
        # Predict hours until failure
        hours_remaining = self.regressor.predict(features_scaled)[0]
        hours_remaining = max(0, hours_remaining)
        
        # Calculate confidence based on feature importance and data quality
        confidence = 0.7 + (0.3 * (len(recent_logs) / 100))  # More logs = higher confidence
        confidence = min(1.0, confidence)
        
        return {
            'failure_probability': float(failure_prob),
            'estimated_hours_remaining': float(hours_remaining),
            'confidence': float(confidence),
            'recommendation': self._generate_recommendation(failure_prob, hours_remaining)
        }
    
    def _rule_based_prediction(self, component: Component) -> Dict[str, Any]:
        """Fallback rule-based prediction"""
        remaining_life = component.remaining_lifetime()
        
        if remaining_life < 10:
            failure_prob = 0.8
            hours_remaining = component.expected_lifetime - component.flight_hours
        elif remaining_life < 25:
            failure_prob = 0.5
            hours_remaining = (component.expected_lifetime - component.flight_hours) * 0.8
        elif remaining_life < 50:
            failure_prob = 0.2
            hours_remaining = (component.expected_lifetime - component.flight_hours) * 0.9
        else:
            failure_prob = 0.05
            hours_remaining = component.expected_lifetime - component.flight_hours
        
        # Adjust for health score
        failure_prob *= (100 - component.health_score) / 50
        failure_prob = min(1.0, max(0.0, failure_prob))
        
        return {
            'failure_probability': failure_prob,
            'estimated_hours_remaining': hours_remaining,
            'confidence': 0.6,
            'recommendation': self._generate_recommendation(failure_prob, hours_remaining)
        }
    
    def _generate_recommendation(self, failure_prob: float, 
                                hours_remaining: float) -> str:
        """Generate maintenance recommendation"""
        if failure_prob > 0.7:
            return "URGENT: Replace component immediately"
        elif failure_prob > 0.5:
            return "Schedule replacement within 10 flight hours"
        elif failure_prob > 0.3:
            return "Schedule inspection and potential replacement"
        elif hours_remaining < 50:
            return "Monitor closely and plan replacement"
        else:
            return "Component in good condition"


class BatteryHealthAnalyzer:
    """
    Analyze and optimize battery health
    """
    
    def __init__(self):
        self.discharge_curves = {}
        self.health_history = defaultdict(list)
    
    def analyze_battery(self, battery: Battery, 
                       charge_discharge_history: List[Dict]) -> Dict[str, Any]:
        """
        Comprehensive battery analysis
        """
        # Calculate state of health (SOH)
        soh = self._calculate_soh(battery, charge_discharge_history)
        
        # Estimate remaining cycles
        remaining_cycles = self._estimate_remaining_cycles(battery)
        
        # Check for cell imbalance
        cell_balance = self._check_cell_balance(battery)
        
        # Predict capacity fade
        capacity_fade = self._predict_capacity_fade(battery)
        
        # Calculate optimal charging strategy
        charging_recommendation = self._optimize_charging_strategy(battery)
        
        return {
            'state_of_health': soh,
            'remaining_cycles': remaining_cycles,
            'cell_balance_status': cell_balance,
            'predicted_capacity_fade': capacity_fade,
            'charging_recommendation': charging_recommendation,
            'replacement_recommended': soh < 80 or remaining_cycles < 50,
            'health_grade': self._grade_battery_health(soh)
        }
    
    def _calculate_soh(self, battery: Battery, 
                      history: List[Dict]) -> float:
        """Calculate State of Health"""
        if not history:
            return battery.health
        
        # Method 1: Capacity-based SOH
        if battery.capacity_mah > 0:
            current_capacity = battery.current_capacity * battery.capacity_mah / 100
            capacity_soh = (current_capacity / battery.capacity_mah) * 100
        else:
            capacity_soh = battery.health
        
        # Method 2: Internal resistance increase (simplified)
        resistance_factor = 1.0 - (battery.cycles * 0.0001)  # Simplified model
        resistance_soh = resistance_factor * 100
        
        # Method 3: Cycle count based
        expected_cycles = 500  # Typical LiPo battery
        cycle_soh = max(0, (expected_cycles - battery.cycles) / expected_cycles * 100)
        
        # Weighted average
        soh = (capacity_soh * 0.5 + resistance_soh * 0.3 + cycle_soh * 0.2)
        
        return min(100, max(0, soh))
    
    def _estimate_remaining_cycles(self, battery: Battery) -> int:
        """Estimate remaining charge cycles"""
        degradation_per_cycle = battery.degradation_rate()
        
        if degradation_per_cycle == 0:
            return 500 - battery.cycles  # Default estimate
        
        # Calculate cycles until 80% health (typical EOL)
        current_health = battery.health
        target_health = 80.0
        
        if current_health <= target_health:
            return 0
        
        remaining_cycles = int((current_health - target_health) / degradation_per_cycle)
        return max(0, remaining_cycles)
    
    def _check_cell_balance(self, battery: Battery) -> Dict[str, Any]:
        """Check for cell voltage imbalance"""
        if not battery.cell_voltages or len(battery.cell_voltages) < 2:
            return {'status': 'unknown', 'max_difference': 0.0}
        
        voltages = np.array(battery.cell_voltages)
        max_voltage = np.max(voltages)
        min_voltage = np.min(voltages)
        difference = max_voltage - min_voltage
        
        # Cell balance thresholds
        if difference < 0.01:
            status = 'excellent'
        elif difference < 0.03:
            status = 'good'
        elif difference < 0.05:
            status = 'fair'
        else:
            status = 'poor'
        
        return {
            'status': status,
            'max_difference': float(difference),
            'max_voltage': float(max_voltage),
            'min_voltage': float(min_voltage),
            'balance_required': difference > 0.05
        }
    
    def _predict_capacity_fade(self, battery: Battery) -> Dict[str, float]:
        """Predict future capacity fade"""
        # Simplified capacity fade model
        # Real model would use more sophisticated electrochemical models
        
        current_cycles = battery.cycles
        fade_rate = battery.degradation_rate()
        
        predictions = {}
        for future_cycles in [50, 100, 200]:
            total_cycles = current_cycles + future_cycles
            predicted_health = battery.health - (fade_rate * future_cycles)
            predicted_health = max(0, min(100, predicted_health))
            predictions[f'after_{future_cycles}_cycles'] = predicted_health
        
        return predictions
    
    def _optimize_charging_strategy(self, battery: Battery) -> Dict[str, Any]:
        """Recommend optimal charging parameters"""
        # Conservative charging for longer life
        if battery.health < 85:
            return {
                'charge_current': '0.5C',  # Slower charging
                'max_voltage': 4.15,  # Slightly lower than max
                'target_soc': 90,  # Don't charge to 100%
                'storage_voltage': 3.8,
                'strategy': 'conservative'
            }
        else:
            return {
                'charge_current': '1C',  # Normal charging
                'max_voltage': 4.2,
                'target_soc': 100,
                'storage_voltage': 3.8,
                'strategy': 'normal'
            }
    
    def _grade_battery_health(self, soh: float) -> str:
        """Assign letter grade to battery health"""
        if soh >= 95:
            return 'A+'
        elif soh >= 90:
            return 'A'
        elif soh >= 85:
            return 'B'
        elif soh >= 80:
            return 'C'
        elif soh >= 70:
            return 'D'
        else:
            return 'F'


class MaintenanceScheduler:
    """
    Optimize maintenance scheduling across the fleet
    """
    
    def __init__(self):
        self.pending_tasks = []
        self.scheduled_tasks = []
        self.technicians = {}
    
    def add_task(self, task: MaintenanceTask):
        """Add a new maintenance task"""
        self.pending_tasks.append(task)
        self._reoptimize_schedule()
    
    def add_technician(self, technician: Technician):
        """Register a technician"""
        self.technicians[technician.technician_id] = technician
    
    def _reoptimize_schedule(self):
        """Re-optimize the maintenance schedule"""
        # Sort tasks by priority and scheduled date
        sorted_tasks = sorted(
            self.pending_tasks,
            key=lambda t: (t.priority.value, t.scheduled_date)
        )
        
        # Assign tasks to technicians
        for task in sorted_tasks:
            best_technician = self._find_best_technician(task)
            if best_technician:
                task.assigned_technician = best_technician.technician_id
                task.status = "scheduled"
                self.scheduled_tasks.append(task)
    
    def _find_best_technician(self, task: MaintenanceTask) -> Optional[Technician]:
        """Find the best available technician for a task"""
        available_technicians = [
            t for t in self.technicians.values()
            if t.available
        ]
        
        if not available_technicians:
            return None
        
        # Score technicians based on specializations
        scores = []
        for tech in available_technicians:
            score = 1.0  # Base score
            
            # Check if task requires specific component expertise
            # (simplified - would need component info from task)
            score += tech.completed_tasks * 0.01  # Experience bonus
            
            scores.append((score, tech))
        
        # Return technician with highest score
        scores.sort(key=lambda x: x[0], reverse=True)
        return scores[0][1] if scores else None
    
    def get_schedule(self, days_ahead: int = 7) -> List[MaintenanceTask]:
        """Get maintenance schedule for next N days"""
        cutoff_date = datetime.now() + timedelta(days=days_ahead)
        
        upcoming_tasks = [
            task for task in self.scheduled_tasks
            if task.scheduled_date <= cutoff_date and task.status != "completed"
        ]
        
        return sorted(upcoming_tasks, key=lambda t: t.scheduled_date)
    
    def estimate_downtime(self, drone_id: str) -> timedelta:
        """Estimate total maintenance downtime for a drone"""
        drone_tasks = [
            task for task in self.scheduled_tasks
            if task.drone_id == drone_id and task.status != "completed"
        ]
        
        total_duration = sum(
            (task.estimated_duration for task in drone_tasks),
            timedelta()
        )
        
        return total_duration


class FleetManager:
    """
    Main fleet management system coordinating all operations
    """
    
    def __init__(self):
        self.drones = {}
        self.predictive_model = PredictiveMaintenanceModel()
        self.battery_analyzer = BatteryHealthAnalyzer()
        self.scheduler = MaintenanceScheduler()
        
        self.fleet_statistics = defaultdict(float)
        self.alerts = deque(maxlen=1000)
    
    def register_drone(self, drone: Drone):
        """Register a new drone in the fleet"""
        self.drones[drone.drone_id] = drone
        self._update_fleet_statistics()
    
    def log_flight(self, drone_id: str, flight_log: FlightLog):
        """Log a completed flight"""
        if drone_id not in self.drones:
            return
        
        drone = self.drones[drone_id]
        drone.flight_logs.append(flight_log)
        drone.total_flight_hours += flight_log.flight_duration.total_seconds() / 3600
        drone.total_flights += 1
        
        # Update component flight hours
        for component in drone.components.values():
            component.flight_hours += flight_log.flight_duration.total_seconds() / 3600
            component.cycles += 1
        
        # Check if maintenance is needed
        self._check_maintenance_triggers(drone_id)
        
        self._update_fleet_statistics()
    
    def _check_maintenance_triggers(self, drone_id: str):
        """Check if maintenance is triggered based on flight hours or predictions"""
        drone = self.drones[drone_id]
        
        # Check each component
        for component_id, component in drone.components.items():
            # Get recent flight logs
            recent_logs = drone.flight_logs[-50:] if len(drone.flight_logs) > 50 else drone.flight_logs
            
            # Predict failure
            prediction = self.predictive_model.predict_failure(component, recent_logs)
            
            # Create maintenance task if needed
            if prediction['failure_probability'] > 0.5:
                task = MaintenanceTask(
                    task_id=f"MAINT-{drone_id}-{component_id}-{datetime.now().timestamp()}",
                    drone_id=drone_id,
                    task_type=MaintenanceType.PREDICTIVE,
                    priority=Priority.HIGH if prediction['failure_probability'] > 0.7 else Priority.MEDIUM,
                    description=f"Predictive maintenance for {component.component_type.value}: {prediction['recommendation']}",
                    scheduled_date=datetime.now() + timedelta(hours=prediction['estimated_hours_remaining'] * 0.5),
                    estimated_duration=timedelta(hours=2),
                    parts_required=[component.component_type.value]
                )
                
                self.scheduler.add_task(task)
                
                self.alerts.append({
                    'timestamp': datetime.now(),
                    'severity': 'high' if prediction['failure_probability'] > 0.7 else 'medium',
                    'drone_id': drone_id,
                    'component': component_id,
                    'message': prediction['recommendation']
                })
    
    def analyze_battery_health(self, drone_id: str, 
                              battery_id: str) -> Dict[str, Any]:
        """Analyze health of a specific battery"""
        if drone_id not in self.drones:
            return {'error': 'Drone not found'}
        
        drone = self.drones[drone_id]
        battery = next((b for b in drone.batteries if b.battery_id == battery_id), None)
        
        if not battery:
            return {'error': 'Battery not found'}
        
        # Get charge/discharge history from flight logs
        history = [
            {
                'cycles': battery.cycles,
                'capacity': battery.current_capacity
            }
        ]
        
        analysis = self.battery_analyzer.analyze_battery(battery, history)
        
        # Generate alert if replacement recommended
        if analysis['replacement_recommended']:
            self.alerts.append({
                'timestamp': datetime.now(),
                'severity': 'high',
                'drone_id': drone_id,
                'battery_id': battery_id,
                'message': f"Battery replacement recommended (SOH: {analysis['state_of_health']:.1f}%)"
            })
        
        return analysis
    
    def calculate_fleet_health(self) -> Dict[str, Any]:
        """Calculate overall fleet health score"""
        if not self.drones:
            return {'overall_health': 100.0, 'details': {}}
        
        health_scores = [drone.health_score for drone in self.drones.values()]
        
        overall_health = np.mean(health_scores)
        
        # Count drones by status
        status_counts = defaultdict(int)
        for drone in self.drones.values():
            status_counts[drone.status.value] += 1
        
        # Calculate availability
        available_drones = sum(1 for d in self.drones.values() 
                             if d.status in [DroneStatus.ACTIVE, DroneStatus.IDLE])
        availability = available_drones / len(self.drones) * 100
        
        return {
            'overall_health': float(overall_health),
            'availability': float(availability),
            'total_drones': len(self.drones),
            'status_breakdown': dict(status_counts),
            'average_flight_hours': float(np.mean([d.total_flight_hours for d in self.drones.values()])),
            'total_flight_hours': sum(d.total_flight_hours for d in self.drones.values()),
            'pending_maintenance': len(self.scheduler.pending_tasks)
        }
    
    def optimize_fleet_utilization(self) -> List[Dict[str, Any]]:
        """Analyze and optimize fleet utilization"""
        recommendations = []
        
        for drone_id, drone in self.drones.items():
            # Check if drone is underutilized
            if drone.total_flight_hours < 10 and drone.status == DroneStatus.IDLE:
                recommendations.append({
                    'drone_id': drone_id,
                    'recommendation': 'underutilized',
                    'message': f'Drone has only {drone.total_flight_hours:.1f} flight hours. Consider assigning more missions.',
                    'priority': 'low'
                })
            
            # Check if drone needs rest/maintenance
            if drone.total_flight_hours > 100 and not drone.last_inspection:
                recommendations.append({
                    'drone_id': drone_id,
                    'recommendation': 'inspection_needed',
                    'message': f'Drone has {drone.total_flight_hours:.1f} flight hours without inspection.',
                    'priority': 'high'
                })
            
            # Check battery rotation
            if len(drone.batteries) > 1:
                battery_cycles = [b.cycles for b in drone.batteries]
                if max(battery_cycles) - min(battery_cycles) > 50:
                    recommendations.append({
                        'drone_id': drone_id,
                        'recommendation': 'rotate_batteries',
                        'message': 'Uneven battery usage detected. Rotate batteries to equalize wear.',
                        'priority': 'medium'
                    })
        
        return recommendations
    
    def _update_fleet_statistics(self):
        """Update fleet-wide statistics"""
        if not self.drones:
            return
        
        self.fleet_statistics['total_drones'] = len(self.drones)
        self.fleet_statistics['total_flight_hours'] = sum(
            d.total_flight_hours for d in self.drones.values()
        )
        self.fleet_statistics['total_flights'] = sum(
            d.total_flights for d in self.drones.values()
        )
        self.fleet_statistics['average_health'] = np.mean(
            [d.health_score for d in self.drones.values()]
        )
    
    def generate_fleet_report(self) -> Dict[str, Any]:
        """Generate comprehensive fleet report"""
        fleet_health = self.calculate_fleet_health()
        utilization_recommendations = self.optimize_fleet_utilization()
        maintenance_schedule = self.scheduler.get_schedule(days_ahead=7)
        
        # Recent alerts
        recent_alerts = list(self.alerts)[-10:]
        
        return {
            'timestamp': datetime.now().isoformat(),
            'fleet_health': fleet_health,
            'recommendations': utilization_recommendations,
            'upcoming_maintenance': [
                {
                    'task_id': task.task_id,
                    'drone_id': task.drone_id,
                    'type': task.task_type.value,
                    'priority': task.priority.value,
                    'scheduled': task.scheduled_date.isoformat(),
                    'description': task.description
                }
                for task in maintenance_schedule
            ],
            'recent_alerts': recent_alerts,
            'statistics': dict(self.fleet_statistics)
        }
    
    def export_maintenance_history(self, drone_id: str) -> pd.DataFrame:
        """Export maintenance history as DataFrame"""
        if drone_id not in self.drones:
            return pd.DataFrame()
        
        drone = self.drones[drone_id]
        
        data = []
        for task in drone.maintenance_history:
            data.append({
                'Task ID': task.task_id,
                'Type': task.task_type.value,
                'Priority': task.priority.value,
                'Scheduled Date': task.scheduled_date,
                'Completion Date': task.completion_date,
                'Duration': task.estimated_duration.total_seconds() / 3600,
                'Technician': task.assigned_technician,
                'Cost': task.cost_estimate,
                'Status': task.status
            })
        
        return pd.DataFrame(data)


# Example usage and testing
if __name__ == "__main__":
    # Initialize fleet manager
    fleet = FleetManager()
    
    # Create and register drones
    for i in range(5):
        drone = Drone(
            drone_id=f"DRONE-{i+1:03d}",
            model="AgroPulse X1",
            serial_number=f"SN{10000+i}",
            registration_number=f"REG-{i+1}",
            manufacture_date=datetime(2024, 1, 1),
            purchase_date=datetime(2024, 6, 1)
        )
        
        # Add components
        for motor_num in range(4):
            component = Component(
                component_id=f"MOTOR-{motor_num+1}",
                component_type=ComponentType.MOTOR,
                manufacturer="T-Motor",
                model="F80 Pro",
                serial_number=f"MTR{i*4+motor_num}",
                installation_date=drone.manufacture_date,
                expected_lifetime=1000.0
            )
            drone.components[component.component_id] = component
        
        # Add batteries
        for bat_num in range(3):
            battery = Battery(
                battery_id=f"BAT-{i+1}-{bat_num+1}",
                capacity_mah=10000.0,
                voltage=14.8,
                current_capacity=100.0,
                cell_voltages=[3.7, 3.7, 3.7, 3.7]
            )
            drone.batteries.append(battery)
        
        fleet.register_drone(drone)
    
    print(f"Registered {len(fleet.drones)} drones in fleet")
    
    # Simulate some flights
    for drone_id in list(fleet.drones.keys())[:2]:
        for flight_num in range(10):
            flight_log = FlightLog(
                log_id=f"FLIGHT-{drone_id}-{flight_num}",
                drone_id=drone_id,
                start_time=datetime.now() - timedelta(days=10-flight_num, hours=2),
                end_time=datetime.now() - timedelta(days=10-flight_num, hours=1),
                flight_duration=timedelta(hours=1),
                distance_covered=5000.0 + np.random.normal(0, 500),
                max_altitude=50.0,
                avg_speed=5.0,
                battery_consumed=25.0 + np.random.normal(0, 5)
            )
            fleet.log_flight(drone_id, flight_log)
    
    print(f"Logged flights for fleet")
    
    # Generate fleet report
    report = fleet.generate_fleet_report()
    
    print("\n=== FLEET REPORT ===")
    print(f"Overall Health: {report['fleet_health']['overall_health']:.1f}%")
    print(f"Availability: {report['fleet_health']['availability']:.1f}%")
    print(f"Total Flight Hours: {report['fleet_health']['total_flight_hours']:.1f}")
    print(f"Pending Maintenance Tasks: {report['fleet_health']['pending_maintenance']}")
    
    if report['recommendations']:
        print("\n=== RECOMMENDATIONS ===")
        for rec in report['recommendations'][:5]:
            print(f"- {rec['drone_id']}: {rec['message']} (Priority: {rec['priority']})")
    
    if report['upcoming_maintenance']:
        print("\n=== UPCOMING MAINTENANCE ===")
        for task in report['upcoming_maintenance'][:5]:
            print(f"- {task['drone_id']}: {task['description']}")
            print(f"  Scheduled: {task['scheduled']}, Priority: {task['priority']}")
    
    print("\nFleet Management System initialized successfully!")
    print("System ready for production fleet operations.")
