"""
Irrigation Optimization and Water Management Module

This module provides intelligent irrigation management:
- Irrigation scheduling optimization
- Water requirement calculation
- Soil moisture prediction
- Evapotranspiration estimation
- Irrigation system efficiency analysis
- Drought stress prediction
- Water conservation recommendations
- Smart irrigation control
"""

import numpy as np
import pandas as pd
from typing import Dict, Any, List, Optional, Tuple, Union
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class IrrigationMethod(Enum):
    """Irrigation methods."""
    FURROW = "furrow"
    SPRINKLER = "sprinkler"
    DRIP = "drip"
    FLOOD = "flood"
    PIVOT = "center_pivot"
    SUBSURFACE_DRIP = "subsurface_drip"


class WaterStressLevel(Enum):
    """Water stress levels."""
    NONE = "none"
    MILD = "mild"
    MODERATE = "moderate"
    SEVERE = "severe"
    CRITICAL = "critical"


class IrrigationEfficiency(Enum):
    """Irrigation system efficiency classes."""
    POOR = "poor"          # <60%
    FAIR = "fair"          # 60-75%
    GOOD = "good"          # 75-85%
    EXCELLENT = "excellent"  # >85%


@dataclass
class IrrigationSchedule:
    """
    Irrigation schedule.
    
    Attributes:
        crop: Crop name
        growth_stage: Current growth stage
        next_irrigation_date: Next irrigation date
        water_amount_mm: Water amount to apply
        frequency_days: Irrigation frequency
        method: Irrigation method
        duration_hours: Irrigation duration
        priority: Priority level
        reason: Reason for irrigation
    """
    crop: str
    growth_stage: str
    next_irrigation_date: datetime
    water_amount_mm: float
    frequency_days: int
    method: IrrigationMethod
    duration_hours: float
    priority: str
    reason: str


@dataclass
class WaterBudget:
    """
    Water budget analysis.
    
    Attributes:
        crop: Crop name
        period_days: Analysis period
        water_input_mm: Total water input (rain + irrigation)
        rainfall_mm: Rainfall amount
        irrigation_mm: Irrigation amount
        et_crop_mm: Crop evapotranspiration
        deep_percolation_mm: Deep percolation loss
        runoff_mm: Surface runoff
        balance_mm: Water balance
        efficiency_pct: Water use efficiency
    """
    crop: str
    period_days: int
    water_input_mm: float
    rainfall_mm: float
    irrigation_mm: float
    et_crop_mm: float
    deep_percolation_mm: float
    runoff_mm: float
    balance_mm: float
    efficiency_pct: float


@dataclass
class WaterStressAssessment:
    """
    Water stress assessment.
    
    Attributes:
        stress_level: Current stress level
        soil_moisture_pct: Current soil moisture
        optimal_moisture_pct: Optimal soil moisture
        deficit_mm: Water deficit
        symptoms: Stress symptoms
        impacts: Expected impacts
        urgent_action_needed: Whether urgent action needed
        recommendations: Remedial recommendations
    """
    stress_level: WaterStressLevel
    soil_moisture_pct: float
    optimal_moisture_pct: float
    deficit_mm: float
    symptoms: List[str]
    impacts: List[str]
    urgent_action_needed: bool
    recommendations: List[str]


class IrrigationScheduler:
    """
    Intelligent irrigation scheduling system.
    """
    
    def __init__(self):
        """Initialize irrigation scheduler."""
        self.crop_water_requirements = self._initialize_crop_requirements()
        logger.info("Irrigation Scheduler initialized")
    
    def _initialize_crop_requirements(self) -> Dict[str, Dict[str, float]]:
        """Initialize crop water requirements."""
        return {
            "maize": {
                "kc_initial": 0.3,      # Crop coefficient - initial stage
                "kc_mid": 1.2,          # Mid-season
                "kc_end": 0.6,          # End season
                "rooting_depth_m": 1.5,
                "mad": 0.55,            # Management Allowed Depletion
                "critical_stages": ["flowering", "grain_filling"]
            },
            "tomatoes": {
                "kc_initial": 0.6,
                "kc_mid": 1.15,
                "kc_end": 0.8,
                "rooting_depth_m": 0.7,
                "mad": 0.4,
                "critical_stages": ["flowering", "fruiting"]
            },
            "beans": {
                "kc_initial": 0.4,
                "kc_mid": 1.05,
                "kc_end": 0.9,
                "rooting_depth_m": 0.6,
                "mad": 0.45,
                "critical_stages": ["flowering", "pod_formation"]
            },
            "potatoes": {
                "kc_initial": 0.5,
                "kc_mid": 1.15,
                "kc_end": 0.75,
                "rooting_depth_m": 0.6,
                "mad": 0.35,
                "critical_stages": ["tuber_initiation", "bulking"]
            },
            "kale": {
                "kc_initial": 0.7,
                "kc_mid": 1.0,
                "kc_end": 0.95,
                "rooting_depth_m": 0.4,
                "mad": 0.45,
                "critical_stages": ["vegetative"]
            }
        }
    
    def calculate_irrigation_schedule(
        self,
        crop: str,
        growth_stage: str,
        soil_data: Dict[str, float],
        weather_data: Dict[str, float],
        irrigation_method: IrrigationMethod = IrrigationMethod.DRIP
    ) -> IrrigationSchedule:
        """
        Calculate optimal irrigation schedule.
        
        Args:
            crop: Crop name
            growth_stage: Current growth stage
            soil_data: Soil properties
            weather_data: Weather conditions
            irrigation_method: Irrigation method
            
        Returns:
            Irrigation schedule
        """
        logger.info(f"Calculating irrigation schedule for {crop}")
        
        # Get crop requirements
        crop_req = self.crop_water_requirements.get(crop, {
            "kc_initial": 0.5,
            "kc_mid": 1.0,
            "kc_end": 0.7,
            "rooting_depth_m": 0.5,
            "mad": 0.5,
            "critical_stages": []
        })
        
        # Get crop coefficient for current stage
        kc = self._get_crop_coefficient(growth_stage, crop_req)
        
        # Calculate reference ET (ET0)
        et0 = self._calculate_et0(weather_data)
        
        # Calculate crop ET (ETc)
        etc = et0 * kc
        
        # Get soil properties
        soil_moisture = soil_data.get("moisture", 50)
        field_capacity = soil_data.get("field_capacity", 35)
        wilting_point = soil_data.get("wilting_point", 15)
        
        # Calculate total available water
        taw = (field_capacity - wilting_point) * crop_req["rooting_depth_m"] * 10  # mm
        
        # Calculate readily available water
        raw = taw * crop_req["mad"]
        
        # Calculate water deficit
        current_water = (soil_moisture - wilting_point) * crop_req["rooting_depth_m"] * 10
        deficit = max(0, raw - current_water)
        
        # Adjust for rainfall
        forecast_rainfall = weather_data.get("forecast_rainfall_7d", 0)
        effective_rainfall = forecast_rainfall * 0.8  # 80% effective
        
        net_deficit = max(0, deficit - effective_rainfall)
        
        # Determine irrigation amount
        irrigation_amount = net_deficit
        
        # Adjust for irrigation efficiency
        efficiency = self._get_irrigation_efficiency(irrigation_method)
        gross_irrigation = irrigation_amount / efficiency
        
        # Calculate frequency
        if etc > 0:
            frequency = int(raw / etc)
        else:
            frequency = 7
        frequency = max(1, min(14, frequency))
        
        # Determine priority
        priority = self._determine_priority(
            growth_stage,
            crop_req["critical_stages"],
            soil_moisture,
            field_capacity
        )
        
        # Calculate duration
        application_rate = self._get_application_rate(irrigation_method)  # mm/hour
        duration = gross_irrigation / application_rate if application_rate > 0 else 2.0
        
        # Determine next irrigation date
        if soil_moisture < field_capacity * 0.7:
            next_date = datetime.now()
            reason = "Soil moisture below optimal level"
        else:
            next_date = datetime.now() + timedelta(days=frequency)
            reason = f"Scheduled irrigation based on {frequency}-day cycle"
        
        return IrrigationSchedule(
            crop=crop,
            growth_stage=growth_stage,
            next_irrigation_date=next_date,
            water_amount_mm=gross_irrigation,
            frequency_days=frequency,
            method=irrigation_method,
            duration_hours=duration,
            priority=priority,
            reason=reason
        )
    
    def _get_crop_coefficient(self, growth_stage: str, crop_req: Dict) -> float:
        """Get crop coefficient for growth stage."""
        stage_mapping = {
            "germination": "kc_initial",
            "vegetative": "kc_mid",
            "flowering": "kc_mid",
            "fruiting": "kc_mid",
            "maturity": "kc_end"
        }
        
        kc_key = stage_mapping.get(growth_stage, "kc_mid")
        return crop_req.get(kc_key, 1.0)
    
    def _calculate_et0(self, weather: Dict[str, float]) -> float:
        """Calculate reference evapotranspiration."""
        # Simplified Hargreaves equation
        temp_max = weather.get("temperature_max", 30)
        temp_min = weather.get("temperature_min", 20)
        temp_avg = (temp_max + temp_min) / 2
        
        # Simplified ET0 calculation
        et0 = 0.0023 * (temp_avg + 17.8) * (temp_max - temp_min) ** 0.5
        
        return max(0, et0)
    
    def _get_irrigation_efficiency(self, method: IrrigationMethod) -> float:
        """Get irrigation efficiency by method."""
        efficiencies = {
            IrrigationMethod.DRIP: 0.90,
            IrrigationMethod.SPRINKLER: 0.75,
            IrrigationMethod.FURROW: 0.60,
            IrrigationMethod.FLOOD: 0.50,
            IrrigationMethod.PIVOT: 0.80,
            IrrigationMethod.SUBSURFACE_DRIP: 0.95
        }
        return efficiencies.get(method, 0.70)
    
    def _get_application_rate(self, method: IrrigationMethod) -> float:
        """Get application rate by method (mm/hour)."""
        rates = {
            IrrigationMethod.DRIP: 4.0,
            IrrigationMethod.SPRINKLER: 8.0,
            IrrigationMethod.FURROW: 10.0,
            IrrigationMethod.FLOOD: 15.0,
            IrrigationMethod.PIVOT: 12.0,
            IrrigationMethod.SUBSURFACE_DRIP: 3.0
        }
        return rates.get(method, 5.0)
    
    def _determine_priority(
        self,
        growth_stage: str,
        critical_stages: List[str],
        soil_moisture: float,
        field_capacity: float
    ) -> str:
        """Determine irrigation priority."""
        # Critical growth stage
        if growth_stage in critical_stages:
            if soil_moisture < field_capacity * 0.6:
                return "urgent"
            else:
                return "high"
        
        # Based on soil moisture
        if soil_moisture < field_capacity * 0.5:
            return "high"
        elif soil_moisture < field_capacity * 0.7:
            return "medium"
        else:
            return "low"


class WaterBudgetAnalyzer:
    """
    Analyze water budget and efficiency.
    """
    
    def __init__(self):
        """Initialize water budget analyzer."""
        logger.info("Water Budget Analyzer initialized")
    
    def calculate_water_budget(
        self,
        crop: str,
        period_days: int,
        rainfall_mm: float,
        irrigation_mm: float,
        et_crop_mm: float,
        soil_type: str = "loam"
    ) -> WaterBudget:
        """
        Calculate water budget.
        
        Args:
            crop: Crop name
            period_days: Analysis period
            rainfall_mm: Rainfall amount
            irrigation_mm: Irrigation amount
            et_crop_mm: Crop evapotranspiration
            soil_type: Soil type
            
        Returns:
            Water budget analysis
        """
        logger.info(f"Calculating water budget for {crop}")
        
        # Total water input
        total_input = rainfall_mm + irrigation_mm
        
        # Estimate losses
        deep_percolation = self._estimate_deep_percolation(
            total_input,
            et_crop_mm,
            soil_type
        )
        
        runoff = self._estimate_runoff(rainfall_mm, soil_type)
        
        # Water balance
        balance = total_input - et_crop_mm - deep_percolation - runoff
        
        # Water use efficiency
        if total_input > 0:
            efficiency = (et_crop_mm / total_input) * 100
        else:
            efficiency = 0
        
        return WaterBudget(
            crop=crop,
            period_days=period_days,
            water_input_mm=total_input,
            rainfall_mm=rainfall_mm,
            irrigation_mm=irrigation_mm,
            et_crop_mm=et_crop_mm,
            deep_percolation_mm=deep_percolation,
            runoff_mm=runoff,
            balance_mm=balance,
            efficiency_pct=efficiency
        )
    
    def _estimate_deep_percolation(
        self,
        water_input: float,
        et_crop: float,
        soil_type: str
    ) -> float:
        """Estimate deep percolation loss."""
        # Simplified percolation estimation
        excess_water = max(0, water_input - et_crop)
        
        # Percolation factor by soil type
        percolation_factors = {
            "sand": 0.4,
            "loamy_sand": 0.3,
            "sandy_loam": 0.25,
            "loam": 0.2,
            "silt_loam": 0.15,
            "clay_loam": 0.1,
            "clay": 0.05
        }
        
        factor = percolation_factors.get(soil_type, 0.2)
        return excess_water * factor
    
    def _estimate_runoff(self, rainfall: float, soil_type: str) -> float:
        """Estimate surface runoff."""
        # Simplified runoff estimation
        runoff_factors = {
            "sand": 0.05,
            "loamy_sand": 0.08,
            "sandy_loam": 0.10,
            "loam": 0.12,
            "silt_loam": 0.15,
            "clay_loam": 0.20,
            "clay": 0.25
        }
        
        factor = runoff_factors.get(soil_type, 0.12)
        
        # Runoff only from heavy rainfall events
        if rainfall > 30:
            return (rainfall - 30) * factor
        return 0


class WaterStressMonitor:
    """
    Monitor and predict water stress.
    """
    
    def __init__(self):
        """Initialize water stress monitor."""
        logger.info("Water Stress Monitor initialized")
    
    def assess_water_stress(
        self,
        crop: str,
        soil_moisture: float,
        growth_stage: str,
        temperature: float,
        days_since_irrigation: int
    ) -> WaterStressAssessment:
        """
        Assess water stress level.
        
        Args:
            crop: Crop name
            soil_moisture: Current soil moisture (%)
            growth_stage: Current growth stage
            temperature: Current temperature
            days_since_irrigation: Days since last irrigation
            
        Returns:
            Water stress assessment
        """
        logger.info(f"Assessing water stress for {crop}")
        
        # Get optimal moisture range
        optimal_moisture = self._get_optimal_moisture(crop, growth_stage)
        
        # Calculate stress level
        stress_level = self._calculate_stress_level(
            soil_moisture,
            optimal_moisture,
            temperature,
            days_since_irrigation
        )
        
        # Calculate water deficit
        deficit = max(0, optimal_moisture - soil_moisture) * 10  # Convert to mm approximation
        
        # Identify symptoms
        symptoms = self._identify_stress_symptoms(stress_level, crop)
        
        # Predict impacts
        impacts = self._predict_stress_impacts(stress_level, growth_stage)
        
        # Determine urgency
        urgent = stress_level in [WaterStressLevel.SEVERE, WaterStressLevel.CRITICAL]
        
        # Generate recommendations
        recommendations = self._generate_stress_recommendations(
            stress_level,
            soil_moisture,
            optimal_moisture,
            growth_stage
        )
        
        return WaterStressAssessment(
            stress_level=stress_level,
            soil_moisture_pct=soil_moisture,
            optimal_moisture_pct=optimal_moisture,
            deficit_mm=deficit,
            symptoms=symptoms,
            impacts=impacts,
            urgent_action_needed=urgent,
            recommendations=recommendations
        )
    
    def _get_optimal_moisture(self, crop: str, growth_stage: str) -> float:
        """Get optimal soil moisture for crop and stage."""
        # Simplified optimal moisture levels
        base_optimal = {
            "maize": 70,
            "tomatoes": 75,
            "beans": 65,
            "potatoes": 70,
            "kale": 68
        }
        
        optimal = base_optimal.get(crop, 70)
        
        # Critical stages need higher moisture
        if growth_stage in ["flowering", "fruiting", "grain_filling"]:
            optimal += 5
        
        return optimal
    
    def _calculate_stress_level(
        self,
        moisture: float,
        optimal: float,
        temperature: float,
        days_since_irrigation: int
    ) -> WaterStressLevel:
        """Calculate water stress level."""
        # Moisture-based stress
        moisture_deficit_pct = ((optimal - moisture) / optimal) * 100
        
        # Temperature stress multiplier
        temp_stress = 1.0
        if temperature > 35:
            temp_stress = 1.5
        elif temperature > 30:
            temp_stress = 1.2
        
        # Time since irrigation factor
        time_factor = min(1.5, 1.0 + (days_since_irrigation / 10))
        
        # Combined stress score
        stress_score = moisture_deficit_pct * temp_stress * time_factor
        
        if stress_score < 10:
            return WaterStressLevel.NONE
        elif stress_score < 25:
            return WaterStressLevel.MILD
        elif stress_score < 40:
            return WaterStressLevel.MODERATE
        elif stress_score < 60:
            return WaterStressLevel.SEVERE
        else:
            return WaterStressLevel.CRITICAL
    
    def _identify_stress_symptoms(self, level: WaterStressLevel, crop: str) -> List[str]:
        """Identify water stress symptoms."""
        symptoms = []
        
        if level == WaterStressLevel.MILD:
            symptoms.extend([
                "Slight leaf wilting during hottest part of day",
                "Leaves may appear slightly darker green"
            ])
        elif level == WaterStressLevel.MODERATE:
            symptoms.extend([
                "Persistent leaf wilting",
                "Leaf rolling or cupping",
                "Stunted growth",
                "Delayed flowering"
            ])
        elif level == WaterStressLevel.SEVERE:
            symptoms.extend([
                "Severe wilting throughout day",
                "Leaf yellowing and drying",
                "Flower and fruit drop",
                "Significant growth reduction"
            ])
        elif level == WaterStressLevel.CRITICAL:
            symptoms.extend([
                "Complete wilting",
                "Extensive leaf death",
                "Plant death imminent",
                "Irreversible damage occurring"
            ])
        
        return symptoms
    
    def _predict_stress_impacts(self, level: WaterStressLevel, stage: str) -> List[str]:
        """Predict impacts of water stress."""
        impacts = []
        
        if level == WaterStressLevel.NONE:
            impacts.append("No significant impacts expected")
        elif level == WaterStressLevel.MILD:
            impacts.extend([
                "5-10% yield reduction possible",
                "Minimal quality impacts"
            ])
        elif level == WaterStressLevel.MODERATE:
            impacts.extend([
                "15-30% yield reduction likely",
                "Reduced fruit/grain size",
                "Lower crop quality"
            ])
        elif level == WaterStressLevel.SEVERE:
            impacts.extend([
                "40-60% yield loss expected",
                "Severe quality degradation",
                "Increased pest and disease susceptibility"
            ])
        elif level == WaterStressLevel.CRITICAL:
            impacts.extend([
                "70-100% crop loss possible",
                "Plant death likely",
                "Complete economic loss"
            ])
        
        # Critical stage impacts
        if stage in ["flowering", "fruiting", "grain_filling"]:
            impacts.append(f"Critical growth stage - stress impacts magnified")
        
        return impacts
    
    def _generate_stress_recommendations(
        self,
        level: WaterStressLevel,
        moisture: float,
        optimal: float,
        stage: str
    ) -> List[str]:
        """Generate stress remediation recommendations."""
        recommendations = []
        
        if level == WaterStressLevel.NONE:
            recommendations.append("Continue current irrigation schedule")
        
        elif level == WaterStressLevel.MILD:
            recommendations.extend([
                "Increase irrigation frequency slightly",
                "Apply mulch to conserve soil moisture",
                "Monitor plants daily"
            ])
        
        elif level in [WaterStressLevel.MODERATE, WaterStressLevel.SEVERE]:
            deficit = optimal - moisture
            recommendations.extend([
                f"URGENT: Irrigate immediately with {deficit * 10:.0f}mm water",
                "Apply water slowly to ensure deep penetration",
                "Consider light irrigation daily until moisture restored",
                "Avoid fertilizer application until stress relieved"
            ])
        
        elif level == WaterStressLevel.CRITICAL:
            recommendations.extend([
                "EMERGENCY IRRIGATION REQUIRED IMMEDIATELY",
                "Apply water gradually to avoid further stress",
                "Provide temporary shade if possible",
                "Accept that some plants may not recover",
                "Focus on saving viable plants first"
            ])
        
        # General recommendations
        recommendations.extend([
            "Check irrigation system for malfunctions",
            "Ensure even water distribution across field"
        ])
        
        return recommendations


class SmartIrrigationController:
    """
    Smart irrigation control system.
    """
    
    def __init__(self):
        """Initialize smart irrigation controller."""
        self.scheduler = IrrigationScheduler()
        self.stress_monitor = WaterStressMonitor()
        logger.info("Smart Irrigation Controller initialized")
    
    def make_irrigation_decision(
        self,
        crop: str,
        growth_stage: str,
        soil_data: Dict[str, float],
        weather_data: Dict[str, float],
        irrigation_method: IrrigationMethod
    ) -> Dict[str, Any]:
        """
        Make intelligent irrigation decision.
        
        Args:
            crop: Crop name
            growth_stage: Current growth stage
            soil_data: Soil conditions
            weather_data: Weather conditions
            irrigation_method: Irrigation method
            
        Returns:
            Irrigation decision with rationale
        """
        logger.info(f"Making irrigation decision for {crop}")
        
        # Get irrigation schedule
        schedule = self.scheduler.calculate_irrigation_schedule(
            crop, growth_stage, soil_data, weather_data, irrigation_method
        )
        
        # Assess water stress
        stress = self.stress_monitor.assess_water_stress(
            crop,
            soil_data.get("moisture", 50),
            growth_stage,
            weather_data.get("temperature", 25),
            soil_data.get("days_since_irrigation", 3)
        )
        
        # Make decision
        should_irrigate = False
        reason = ""
        
        if stress.urgent_action_needed:
            should_irrigate = True
            reason = f"Critical water stress detected - immediate irrigation required"
        elif schedule.priority == "urgent":
            should_irrigate = True
            reason = f"Soil moisture critically low - urgent irrigation needed"
        elif schedule.next_irrigation_date <= datetime.now():
            should_irrigate = True
            reason = schedule.reason
        else:
            days_until_next = (schedule.next_irrigation_date - datetime.now()).days
            if weather_data.get("forecast_rainfall_3d", 0) < 10:
                reason = f"Next irrigation in {days_until_next} days - no immediate action needed"
            else:
                reason = f"Rainfall expected - postpone irrigation"
        
        return {
            "should_irrigate": should_irrigate,
            "reason": reason,
            "schedule": schedule,
            "stress_assessment": stress,
            "water_amount_mm": schedule.water_amount_mm,
            "duration_hours": schedule.duration_hours,
            "priority": schedule.priority,
            "estimated_cost": self._estimate_irrigation_cost(
                schedule.water_amount_mm,
                irrigation_method
            )
        }
    
    def _estimate_irrigation_cost(
        self,
        water_mm: float,
        method: IrrigationMethod
    ) -> float:
        """Estimate irrigation cost."""
        # Cost factors (KES per mm per hectare)
        method_costs = {
            IrrigationMethod.DRIP: 150,
            IrrigationMethod.SPRINKLER: 120,
            IrrigationMethod.FURROW: 80,
            IrrigationMethod.FLOOD: 60,
            IrrigationMethod.PIVOT: 140,
            IrrigationMethod.SUBSURFACE_DRIP: 160
        }
        
        cost_per_mm = method_costs.get(method, 100)
        return water_mm * cost_per_mm
