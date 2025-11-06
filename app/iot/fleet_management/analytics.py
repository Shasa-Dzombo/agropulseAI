# c:\Users\Codeternal\Desktop\AgroPulse\app\iot\fleet_management\analytics.py

"""
Fleet Analytics and Reporting Service
=====================================

This module provides a service for generating insightful analytics and reports
from the fleet's operational data. It leverages the data stored in the
`FleetRegistry` to compute key performance indicators (KPIs) and historical trends.

The analytics are designed to help farm managers make data-driven decisions to
improve efficiency, reduce costs, and optimize fleet utilization.

Core Components:
-------------
1.  **`FleetAnalyticsService`**:
    -   **Purpose**: The main class that encapsulates all analytics-related logic.
    -   **`get_fleet_utilization()`**:
        -   Calculates the percentage of time vehicles spend in different states
          (e.g., ACTIVE, IDLE, MAINTENANCE).
        -   High utilization (a large percentage of time in the ACTIVE state) is
          generally desirable. High IDLE time might indicate over-capacity, while
          high MAINTENANCE time could signal reliability issues.
    -   **`calculate_operating_costs()`**:
        -   Aggregates maintenance costs across the entire fleet or on a per-vehicle
          basis over a specified time period.
        -   This is crucial for understanding the total cost of ownership (TCO) for
          each asset.
    -   **`get_fuel_efficiency_report()`**:
        -   (Conceptual) Demonstrates how one would calculate fuel efficiency. It
          requires historical telemetry data that includes both distance traveled
          (derived from location changes) and fuel consumed.
        -   This highlights the need for a more robust historical data store than
          the simple in-memory registry for certain types of analytics.
    -   **`get_task_completion_analytics()`**:
        -   (Conceptual) Analyzes historical task data to report on metrics like
          the number of tasks completed, average completion time, and failure rates.
        -   This helps in assessing operational efficiency and identifying bottlenecks
          in the task management workflow.
    -   **`generate_daily_report()`**:
        -   A comprehensive method that combines several key analytics into a
          single, easy-to-digest report.
        -   It provides a snapshot of the fleet's performance over the last 24 hours,
          including utilization, costs, and maintenance activities.

This module serves as the business intelligence (BI) layer of the fleet management
system, transforming raw operational data into actionable insights.
"""

import logging
from datetime import datetime, timedelta
from collections import defaultdict
from typing import Dict, List, Any

from .registry import get_fleet_registry
from .vehicle import Vehicle, VehicleStatus, MaintenanceLog

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class FleetAnalyticsService:
    """
    Provides methods for analyzing fleet data and generating reports.
    """
    def __init__(self):
        self._registry = get_fleet_registry()
        logging.info("FleetAnalyticsService initialized.")

    def get_fleet_utilization(self, time_period_days: int = 30) -> Dict[str, Dict[str, float]]:
        """
        Calculates the utilization rate for each vehicle and the fleet overall.
        
        NOTE: This is a simplified simulation. A real implementation would require
        historical status data. Here, we use the current status as a proxy for
        the entire period, which is not accurate but demonstrates the concept.
        
        Args:
            time_period_days (int): The period over which to calculate utilization.

        Returns:
            A dictionary containing utilization percentages by status for the overall fleet.
        """
        status_counts = defaultdict(int)
        all_vehicles = self._registry.get_all_vehicles()
        total_vehicles = len(all_vehicles)

        if total_vehicles == 0:
            return {}

        for vehicle in all_vehicles:
            status_counts[vehicle.status.value] += 1
            
        fleet_utilization = {status: (count / total_vehicles) * 100 for status, count in status_counts.items()}
        
        logging.info(f"Calculated fleet utilization based on current status: {fleet_utilization}")
        return {"overall_fleet": fleet_utilization}

    def calculate_operating_costs(self, time_period_days: int = 30) -> Dict[str, float]:
        """
        Calculates total maintenance costs over a given period for the entire fleet
        and on a per-vehicle basis.

        Args:
            time_period_days (int): The historical period to consider for costs.

        Returns:
            A dictionary with total fleet cost and a breakdown of costs per vehicle.
        """
        since_date = datetime.utcnow() - timedelta(days=time_period_days)
        all_vehicles = self._registry.get_all_vehicles()
        
        total_fleet_cost = 0.0
        per_vehicle_costs = defaultdict(float)

        for vehicle in all_vehicles:
            vehicle_cost = 0.0
            for log in vehicle.maintenance_logs:
                if log.maintenance_date >= since_date:
                    vehicle_cost += log.cost_usd
            
            if vehicle_cost > 0:
                per_vehicle_costs[vehicle.vehicle_id] = vehicle_cost
                total_fleet_cost += vehicle_cost
        
        logging.info(f"Total operating cost over last {time_period_days} days: ${total_fleet_cost:.2f}")
        
        return {
            "total_fleet_cost_usd": total_fleet_cost,
            "per_vehicle_costs_usd": dict(per_vehicle_costs)
        }

    def get_downtime_report(self, time_period_days: int = 30) -> Dict[str, float]:
        """
        Generates a report on vehicle downtime.
        
        NOTE: This is also a simplified simulation. It assumes any vehicle in
        'maintenance' or 'error' status has been in that state for a fixed
        amount of time. A real system would need historical status transition data.
        """
        downtime_by_vehicle: Dict[str, float] = defaultdict(float)
        
        # Vehicles under maintenance
        maintenance_vehicles = self._registry.get_vehicles_by_status("maintenance")
        for vehicle in maintenance_vehicles:
            # Assume it's been down for an average of 8 hours for this report
            downtime_by_vehicle[vehicle.vehicle_id] += 8.0 

        # Vehicles in an error state
        error_vehicles = self._registry.get_vehicles_by_status("error")
        for vehicle in error_vehicles:
            # Assume it's been down for an average of 4 hours
            downtime_by_vehicle[vehicle.vehicle_id] += 4.0
            
        logging.info(f"Generated downtime report: {downtime_by_vehicle}")
        return dict(downtime_by_vehicle)

    def generate_daily_report(self) -> Dict[str, Any]:
        """
        Generates a comprehensive daily snapshot of the fleet's performance.
        """
        logging.info("Generating daily fleet report...")
        
        report = {
            "report_generated_at": datetime.utcnow().isoformat(),
            "total_vehicles": len(self._registry.get_all_vehicles()),
            "fleet_status_distribution": {status.value: len(self._registry.get_vehicles_by_status(status)) for status in VehicleStatus},
            "costs_last_24_hours": self.calculate_operating_costs(time_period_days=1),
            "vehicles_due_for_maintenance": [v.vehicle_id for v in self.get_vehicles_due_for_maintenance()],
            "simulated_utilization": self.get_fleet_utilization(time_period_days=1),
        }
        
        return report

    def get_vehicles_due_for_maintenance(self) -> List[Vehicle]:
        """Helper to get vehicles needing service, for reporting."""
        # This duplicates logic from the maintenance module for reporting purposes.
        # In a larger system, this might be a shared utility or a direct call.
        from .maintenance import maintenance_predictor
        return maintenance_predictor.check_for_due_maintenance()


# --- Global Instance ---
analytics_service = FleetAnalyticsService()

# --- Example Usage ---
if __name__ == "__main__":
    from .maintenance import maintenance_logger

    registry = get_fleet_registry()

    # 1. Ensure there's data to analyze
    if not registry.get_vehicle("ANALYTICS_TRACTOR_01"):
        tractor = Vehicle(
            vehicle_id="ANALYTICS_TRACTOR_01",
            vin="ANALYTICSTRACVIN01",
            make="Fendt",
            model="1000 Vario",
            year=2021,
            vehicle_type="tractor",
            status="idle"
        )
        registry.add_vehicle(tractor)
    
    vehicle = registry.get_vehicle("ANALYTICS_TRACTOR_01")

    # 2. Add a recent maintenance log to have some cost data
    log = MaintenanceLog(
        maintenance_date=datetime.utcnow() - timedelta(days=5),
        maintenance_type="corrective",
        description="Replaced hydraulic pump.",
        service_provider="External Service",
        cost_usd=2500.50,
        odometer_reading_km=5000
    )
    # Use the logger to add it correctly
    # Temporarily modify state to log, then revert
    vehicle.operating_hours.total_hours = 300
    registry.update_vehicle(vehicle.vehicle_id, {"operating_hours": vehicle.operating_hours.dict()})
    maintenance_logger.log_maintenance_completed(vehicle.vehicle_id, log)
    
    # Set another vehicle to maintenance status for utilization report
    if not registry.get_vehicle("ANALYTICS_SPRAYER_01"):
        sprayer = Vehicle(
            vehicle_id="ANALYTICS_SPRAYER_01",
            vin="ANALYTICSSPRAYVIN01",
            make="John Deere",
            model="R4045",
            year=2022,
            vehicle_type="sprayer",
            status="maintenance" # Set status for report
        )
        registry.add_vehicle(sprayer)

    # 3. Generate and print reports
    print("\n--- Operating Costs Report (Last 30 Days) ---")
    costs = analytics_service.calculate_operating_costs(time_period_days=30)
    print(json.dumps(costs, indent=2))
    assert costs["total_fleet_cost_usd"] == 2500.50

    print("\n--- Fleet Utilization Report ---")
    utilization = analytics_service.get_fleet_utilization()
    print(json.dumps(utilization, indent=2))
    assert "idle" in utilization["overall_fleet"]
    assert "maintenance" in utilization["overall_fleet"]

    print("\n--- Comprehensive Daily Report ---")
    daily_report = analytics_service.generate_daily_report()
    print(json.dumps(daily_report, indent=2, default=str))
    assert daily_report["total_vehicles"] >= 2
    assert daily_report["fleet_status_distribution"]["maintenance"] == 1
```