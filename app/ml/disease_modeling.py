"""
Greenhouse Disease Progression and Climate-Linked Epidemic Modeling

This module provides disease management intelligence for controlled environments:
- Disease spread simulation in greenhouse zones
- Infection risk prediction with climate sensor integration
- Epidemic modeling for closed growing environments
- Treatment timing optimization (IPM protocols)
- Fungicide resistance management
- Zone-based quarantine recommendations
- Climate-triggered disease forecasts and alerts
- Biological control effectiveness modeling

Specialized for Greenhouse Environments:
- High humidity disease dynamics (Botrytis, powdery mildew)
- Climate control integration (temp, humidity, air circulation)
- Zone-to-zone spread modeling (multi-zone greenhouses)
- Hydroponic system pathogen transmission (pythium, fusarium)
- LED/HPS lighting effects on disease development
- Biocontrol timing (beneficial insects, antagonistic microbes)

Optimized for: Tomatoes, cucumbers, peppers, lettuce, herbs, strawberries

Author: AgroPulse Horticulture Disease Modeling Team  
Date: November 3, 2025
"""

import numpy as np
import pandas as pd
from typing import Dict, Any, List, Optional, Tuple, Union
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
import logging
from scipy.integrate import odeint

logger = logging.getLogger(__name__)


class GreenhouseDiseaseType(Enum):
    """Greenhouse disease types."""
    FUNGAL = "fungal"  # Botrytis, powdery mildew, fusarium
    BACTERIAL = "bacterial"  # Bacterial canker, soft rot
    VIRAL = "viral"  # TMV, TSWV (spread by thrips)
    OOMYCETE = "oomycete"  # Pythium, downy mildew
    PHYSIOLOGICAL = "physiological"  # Blossom end rot, tipburn


class GreenhouseInfectionRisk(Enum):
    """Greenhouse infection risk levels (climate-linked)."""
    VERY_LOW = "very_low"  # Optimal climate control
    LOW = "low"  # Good air circulation
    MODERATE = "moderate"  # Some humidity spikes
    HIGH = "high"  # Poor air flow, high humidity
    VERY_HIGH = "very_high"  # Critical humidity, leaf wetness
    EPIDEMIC = "epidemic"  # Multi-zone outbreak


class ClimateRiskFactor(Enum):
    """Climate factors affecting disease risk in greenhouses."""
    HIGH_HUMIDITY = "high_humidity"  # >85% RH
    POOR_AIR_CIRCULATION = "poor_air_circulation"
    LEAF_WETNESS = "leaf_wetness"  # Overhead irrigation, condensation
    TEMPERATURE_FLUCTUATION = "temperature_fluctuation"
    LOW_LIGHT = "low_light"  # Weak plant immunity
    OVERCROWDING = "overcrowding"  # Dense canopy


class DiseaseStage(Enum):
    """Disease progression stages."""
    ABSENT = "absent"
    EARLY = "early"
    ESTABLISHED = "established"
    SEVERE = "severe"
    EPIDEMIC = "epidemic"


class TreatmentUrgency(Enum):
    """Treatment urgency levels."""
    NONE = "none"
    PREVENTIVE = "preventive"
    ROUTINE = "routine"
    URGENT = "urgent"
    EMERGENCY = "emergency"


@dataclass
class DiseaseProfile:
    """
    Disease profile information.
    
    Attributes:
        disease_name: Disease name
        pathogen: Pathogen name
        disease_type: Type of disease
        hosts: Susceptible crops
        optimal_temp_range: Optimal temperature range
        optimal_humidity: Optimal humidity
        incubation_period_days: Incubation period
        transmission_rate: Base transmission rate
        survival_days: Pathogen survival time
        severity_factors: Factors affecting severity
    """
    disease_name: str
    pathogen: str
    disease_type: DiseaseType
    hosts: List[str]
    optimal_temp_range: Tuple[float, float]
    optimal_humidity: float
    incubation_period_days: int
    transmission_rate: float
    survival_days: int
    severity_factors: Dict[str, float]


@dataclass
class InfectionRiskAssessment:
    """
    Infection risk assessment.
    
    Attributes:
        disease: Disease name
        crop: Crop name
        risk_level: Overall risk level
        risk_score: Numeric risk score
        environmental_risk: Environmental contribution
        host_susceptibility: Host susceptibility
        inoculum_pressure: Inoculum pressure
        contributing_factors: Risk factors
        infection_probability: Infection probability
        expected_onset_date: Expected infection date
        recommendations: Preventive recommendations
    """
    disease: str
    crop: str
    risk_level: InfectionRisk
    risk_score: float
    environmental_risk: float
    host_susceptibility: float
    inoculum_pressure: float
    contributing_factors: List[str]
    infection_probability: float
    expected_onset_date: Optional[datetime]
    recommendations: List[str]


@dataclass
class DiseaseProgression:
    """
    Disease progression forecast.
    
    Attributes:
        disease: Disease name
        current_stage: Current disease stage
        current_incidence: Current disease incidence (%)
        forecasted_incidence: Forecasted incidence
        doubling_time_days: Time to double incidence
        peak_incidence_date: Expected peak date
        peak_incidence_pct: Expected peak incidence
        spread_rate: Daily spread rate
        area_affected_pct: Area affected
        yield_loss_pct: Expected yield loss
        economic_impact: Economic impact estimate
    """
    disease: str
    current_stage: DiseaseStage
    current_incidence: float
    forecasted_incidence: List[Tuple[datetime, float]]
    doubling_time_days: float
    peak_incidence_date: datetime
    peak_incidence_pct: float
    spread_rate: float
    area_affected_pct: float
    yield_loss_pct: float
    economic_impact: float


@dataclass
class TreatmentRecommendation:
    """
    Treatment recommendation.
    
    Attributes:
        disease: Disease name
        urgency: Treatment urgency
        treatment_type: Type of treatment
        products: Recommended products
        application_timing: When to apply
        application_method: How to apply
        dosage: Dosage information
        frequency: Application frequency
        resistance_risk: Resistance development risk
        efficacy_pct: Expected efficacy
        cost_estimate: Cost estimate
        alternative_treatments: Alternative options
    """
    disease: str
    urgency: TreatmentUrgency
    treatment_type: str
    products: List[str]
    application_timing: str
    application_method: str
    dosage: str
    frequency: str
    resistance_risk: str
    efficacy_pct: float
    cost_estimate: float
    alternative_treatments: List[str]


class DiseaseDatabase:
    """
    Disease information database.
    """
    
    def __init__(self):
        """Initialize disease database."""
        self.diseases = self._initialize_disease_database()
        logger.info("Disease Database initialized")
    
    def _initialize_disease_database(self) -> Dict[str, DiseaseProfile]:
        """Initialize disease profiles."""
        return {
            "late_blight": DiseaseProfile(
                disease_name="Late Blight",
                pathogen="Phytophthora infestans",
                disease_type=DiseaseType.FUNGAL,
                hosts=["potatoes", "tomatoes"],
                optimal_temp_range=(10, 25),
                optimal_humidity=90,
                incubation_period_days=5,
                transmission_rate=0.3,
                survival_days=7,
                severity_factors={
                    "humidity": 2.5,
                    "leaf_wetness": 2.0,
                    "temperature": 1.5,
                    "susceptible_variety": 2.0
                }
            ),
            "early_blight": DiseaseProfile(
                disease_name="Early Blight",
                pathogen="Alternaria solani",
                disease_type=DiseaseType.FUNGAL,
                hosts=["tomatoes", "potatoes"],
                optimal_temp_range=(24, 29),
                optimal_humidity=80,
                incubation_period_days=7,
                transmission_rate=0.2,
                survival_days=30,
                severity_factors={
                    "temperature": 1.8,
                    "humidity": 1.5,
                    "plant_stress": 2.0,
                    "nitrogen_excess": 1.3
                }
            ),
            "bacterial_wilt": DiseaseProfile(
                disease_name="Bacterial Wilt",
                pathogen="Ralstonia solanacearum",
                disease_type=DiseaseType.BACTERIAL,
                hosts=["tomatoes", "potatoes", "peppers"],
                optimal_temp_range=(27, 32),
                optimal_humidity=85,
                incubation_period_days=10,
                transmission_rate=0.15,
                survival_days=365,
                severity_factors={
                    "soil_moisture": 2.2,
                    "temperature": 2.0,
                    "soil_ph": 1.5,
                    "wounds": 2.5
                }
            ),
            "maize_streak_virus": DiseaseProfile(
                disease_name="Maize Streak Virus",
                pathogen="Maize streak virus",
                disease_type=DiseaseType.VIRAL,
                hosts=["maize"],
                optimal_temp_range=(25, 30),
                optimal_humidity=70,
                incubation_period_days=14,
                transmission_rate=0.25,
                survival_days=180,
                severity_factors={
                    "leafhopper_population": 3.0,
                    "young_plants": 2.5,
                    "temperature": 1.5
                }
            ),
            "powdery_mildew": DiseaseProfile(
                disease_name="Powdery Mildew",
                pathogen="Erysiphe sp.",
                disease_type=DiseaseType.FUNGAL,
                hosts=["beans", "peas", "cucurbits"],
                optimal_temp_range=(20, 27),
                optimal_humidity=50,
                incubation_period_days=5,
                transmission_rate=0.35,
                survival_days=14,
                severity_factors={
                    "low_light": 2.0,
                    "dense_planting": 1.8,
                    "nitrogen_excess": 1.6,
                    "dry_foliage": 1.5
                }
            ),
            "fusarium_wilt": DiseaseProfile(
                disease_name="Fusarium Wilt",
                pathogen="Fusarium oxysporum",
                disease_type=DiseaseType.FUNGAL,
                hosts=["tomatoes", "beans", "bananas"],
                optimal_temp_range=(27, 32),
                optimal_humidity=75,
                incubation_period_days=21,
                transmission_rate=0.1,
                survival_days=1825,
                severity_factors={
                    "soil_temperature": 2.5,
                    "soil_ph": 1.8,
                    "root_wounds": 2.3,
                    "continuous_cropping": 2.0
                }
            )
        }
    
    def get_disease_profile(self, disease_name: str) -> Optional[DiseaseProfile]:
        """Get disease profile by name."""
        return self.diseases.get(disease_name)
    
    def get_diseases_for_crop(self, crop: str) -> List[DiseaseProfile]:
        """Get all diseases affecting a crop."""
        return [
            profile for profile in self.diseases.values()
            if crop in profile.hosts
        ]


class InfectionRiskPredictor:
    """
    Predict disease infection risk.
    """
    
    def __init__(self):
        """Initialize infection risk predictor."""
        self.disease_db = DiseaseDatabase()
        logger.info("Infection Risk Predictor initialized")
    
    def assess_infection_risk(
        self,
        disease_name: str,
        crop: str,
        weather_data: Dict[str, float],
        field_conditions: Dict[str, Any],
        history: Optional[Dict[str, Any]] = None
    ) -> InfectionRiskAssessment:
        """
        Assess infection risk for a disease.
        
        Args:
            disease_name: Disease name
            crop: Crop name
            weather_data: Weather conditions
            field_conditions: Field conditions
            history: Disease history
            
        Returns:
            Infection risk assessment
        """
        logger.info(f"Assessing infection risk for {disease_name} on {crop}")
        
        # Get disease profile
        profile = self.disease_db.get_disease_profile(disease_name)
        if not profile:
            logger.warning(f"Disease profile not found: {disease_name}")
            # Return default assessment
            return self._create_default_assessment(disease_name, crop)
        
        # Calculate environmental risk
        env_risk = self._calculate_environmental_risk(weather_data, profile)
        
        # Calculate host susceptibility
        host_susc = self._calculate_host_susceptibility(crop, field_conditions, profile)
        
        # Calculate inoculum pressure
        inoculum = self._calculate_inoculum_pressure(history, profile)
        
        # Overall risk score
        risk_score = (env_risk * 0.4 + host_susc * 0.35 + inoculum * 0.25) * 100
        
        # Classify risk level
        risk_level = self._classify_risk_level(risk_score)
        
        # Identify contributing factors
        factors = self._identify_risk_factors(
            weather_data,
            field_conditions,
            profile
        )
        
        # Calculate infection probability
        infection_prob = min(100, risk_score * 1.2) / 100
        
        # Estimate onset date
        onset_date = self._estimate_onset_date(
            infection_prob,
            profile.incubation_period_days
        )
        
        # Generate recommendations
        recommendations = self._generate_risk_recommendations(
            risk_level,
            factors,
            profile
        )
        
        return InfectionRiskAssessment(
            disease=disease_name,
            crop=crop,
            risk_level=risk_level,
            risk_score=risk_score,
            environmental_risk=env_risk * 100,
            host_susceptibility=host_susc * 100,
            inoculum_pressure=inoculum * 100,
            contributing_factors=factors,
            infection_probability=infection_prob,
            expected_onset_date=onset_date,
            recommendations=recommendations
        )
    
    def _calculate_environmental_risk(
        self,
        weather: Dict[str, float],
        profile: DiseaseProfile
    ) -> float:
        """Calculate environmental risk component."""
        temp = weather.get("temperature", 25)
        humidity = weather.get("humidity", 70)
        rainfall = weather.get("rainfall_24h", 0)
        leaf_wetness = weather.get("leaf_wetness_hours", 0)
        
        # Temperature suitability
        temp_min, temp_max = profile.optimal_temp_range
        if temp_min <= temp <= temp_max:
            temp_factor = 1.0
        elif temp < temp_min:
            temp_factor = max(0, 1 - (temp_min - temp) / 10)
        else:
            temp_factor = max(0, 1 - (temp - temp_max) / 10)
        
        # Humidity suitability
        humidity_diff = abs(humidity - profile.optimal_humidity)
        humidity_factor = max(0, 1 - humidity_diff / 50)
        
        # Rainfall/wetness factor
        if profile.disease_type == DiseaseType.FUNGAL:
            if rainfall > 5 or leaf_wetness > 6:
                wetness_factor = 1.0
            elif rainfall > 0 or leaf_wetness > 0:
                wetness_factor = 0.5
            else:
                wetness_factor = 0.1
        else:
            wetness_factor = 0.5
        
        # Combined environmental risk
        env_risk = (temp_factor * 0.4 + humidity_factor * 0.35 + wetness_factor * 0.25)
        
        return env_risk
    
    def _calculate_host_susceptibility(
        self,
        crop: str,
        conditions: Dict[str, Any],
        profile: DiseaseProfile
    ) -> float:
        """Calculate host susceptibility."""
        # Base susceptibility
        if crop in profile.hosts:
            base_susc = 0.7
        else:
            base_susc = 0.1
        
        # Growth stage factor
        growth_stage = conditions.get("growth_stage", "vegetative")
        if growth_stage in ["seedling", "early_vegetative"]:
            stage_factor = 1.2
        elif growth_stage in ["flowering", "fruiting"]:
            stage_factor = 1.1
        else:
            stage_factor = 1.0
        
        # Plant stress factor
        water_stress = conditions.get("water_stress", False)
        nutrient_stress = conditions.get("nutrient_stress", False)
        
        stress_factor = 1.0
        if water_stress:
            stress_factor += 0.2
        if nutrient_stress:
            stress_factor += 0.15
        
        # Variety resistance
        variety_resistance = conditions.get("variety_resistance", "moderate")
        resistance_factors = {
            "resistant": 0.3,
            "moderate": 0.7,
            "susceptible": 1.2
        }
        resistance_factor = resistance_factors.get(variety_resistance, 0.7)
        
        # Combined susceptibility
        susceptibility = base_susc * stage_factor * stress_factor * resistance_factor
        
        return min(1.0, susceptibility)
    
    def _calculate_inoculum_pressure(
        self,
        history: Optional[Dict[str, Any]],
        profile: DiseaseProfile
    ) -> float:
        """Calculate inoculum pressure."""
        if not history:
            return 0.3  # Default moderate pressure
        
        # Previous occurrence
        prev_occurrence = history.get("previous_occurrence", False)
        days_since_occurrence = history.get("days_since_occurrence", 365)
        
        if not prev_occurrence:
            return 0.2
        
        # Pathogen survival factor
        if days_since_occurrence > profile.survival_days:
            survival_factor = 0.2
        else:
            survival_factor = 1 - (days_since_occurrence / profile.survival_days) * 0.7
        
        # Nearby infections
        nearby_infections = history.get("nearby_infected_fields", 0)
        proximity_factor = min(1.0, 0.3 + (nearby_infections * 0.2))
        
        # Combined inoculum pressure
        inoculum = (survival_factor * 0.6 + proximity_factor * 0.4)
        
        return min(1.0, inoculum)
    
    def _classify_risk_level(self, score: float) -> InfectionRisk:
        """Classify risk level from score."""
        if score < 15:
            return InfectionRisk.VERY_LOW
        elif score < 30:
            return InfectionRisk.LOW
        elif score < 50:
            return InfectionRisk.MODERATE
        elif score < 70:
            return InfectionRisk.HIGH
        elif score < 85:
            return InfectionRisk.VERY_HIGH
        else:
            return InfectionRisk.CRITICAL
    
    def _identify_risk_factors(
        self,
        weather: Dict[str, float],
        conditions: Dict[str, Any],
        profile: DiseaseProfile
    ) -> List[str]:
        """Identify specific risk factors."""
        factors = []
        
        # Temperature
        temp = weather.get("temperature", 25)
        temp_min, temp_max = profile.optimal_temp_range
        if temp_min <= temp <= temp_max:
            factors.append(f"Optimal temperature ({temp}°C) for disease development")
        
        # Humidity
        humidity = weather.get("humidity", 70)
        if humidity > profile.optimal_humidity * 0.9:
            factors.append(f"High humidity ({humidity}%) favorable for infection")
        
        # Rainfall
        if weather.get("rainfall_24h", 0) > 5:
            factors.append("Recent rainfall creating favorable conditions")
        
        # Leaf wetness
        if weather.get("leaf_wetness_hours", 0) > 6:
            factors.append("Extended leaf wetness period")
        
        # Host factors
        if conditions.get("water_stress", False):
            factors.append("Water stress increasing susceptibility")
        
        if conditions.get("nutrient_stress", False):
            factors.append("Nutrient deficiency weakening plants")
        
        if conditions.get("variety_resistance") == "susceptible":
            factors.append("Susceptible variety planted")
        
        if conditions.get("dense_planting", False):
            factors.append("Dense planting reducing air circulation")
        
        return factors
    
    def _estimate_onset_date(
        self,
        infection_prob: float,
        incubation_days: int
    ) -> Optional[datetime]:
        """Estimate disease onset date."""
        if infection_prob < 0.3:
            return None
        
        # Higher probability = earlier onset
        days_adjustment = int((1 - infection_prob) * 7)
        expected_days = incubation_days + days_adjustment
        
        return datetime.now() + timedelta(days=expected_days)
    
    def _generate_risk_recommendations(
        self,
        risk_level: InfectionRisk,
        factors: List[str],
        profile: DiseaseProfile
    ) -> List[str]:
        """Generate risk management recommendations."""
        recommendations = []
        
        if risk_level == InfectionRisk.VERY_LOW:
            recommendations.append("Continue routine monitoring")
        
        elif risk_level == InfectionRisk.LOW:
            recommendations.extend([
                "Maintain regular scouting schedule",
                "Ensure good air circulation",
                "Avoid overhead irrigation if possible"
            ])
        
        elif risk_level == InfectionRisk.MODERATE:
            recommendations.extend([
                "Increase monitoring frequency to weekly",
                "Consider preventive fungicide application",
                "Improve drainage to reduce moisture",
                "Remove infected plant debris"
            ])
        
        elif risk_level in [InfectionRisk.HIGH, InfectionRisk.VERY_HIGH]:
            recommendations.extend([
                "URGENT: Apply protective fungicide immediately",
                "Scout fields daily for early symptoms",
                "Improve air circulation by pruning/spacing",
                "Reduce irrigation frequency",
                "Remove and destroy any infected plants"
            ])
        
        elif risk_level == InfectionRisk.CRITICAL:
            recommendations.extend([
                "EMERGENCY: Immediate protective treatment required",
                "Apply systemic fungicide for better protection",
                "Consider crop insurance claim if available",
                "Implement strict quarantine measures",
                "Prepare for potential crop loss"
            ])
        
        # Disease-specific recommendations
        if profile.disease_type == DiseaseType.FUNGAL:
            recommendations.append("Rotate fungicide modes of action to prevent resistance")
        elif profile.disease_type == DiseaseType.BACTERIAL:
            recommendations.append("Use copper-based bactericides")
        elif profile.disease_type == DiseaseType.VIRAL:
            recommendations.append("Control vector populations (insects)")
        
        return recommendations
    
    def _create_default_assessment(
        self,
        disease: str,
        crop: str
    ) -> InfectionRiskAssessment:
        """Create default assessment when disease profile not found."""
        return InfectionRiskAssessment(
            disease=disease,
            crop=crop,
            risk_level=InfectionRisk.LOW,
            risk_score=25.0,
            environmental_risk=30.0,
            host_susceptibility=40.0,
            inoculum_pressure=20.0,
            contributing_factors=["Limited disease information available"],
            infection_probability=0.25,
            expected_onset_date=None,
            recommendations=["Consult local agricultural extension for specific guidance"]
        )


class DiseaseProgressionModeler:
    """
    Model disease progression and spread.
    """
    
    def __init__(self):
        """Initialize disease progression modeler."""
        self.disease_db = DiseaseDatabase()
        logger.info("Disease Progression Modeler initialized")
    
    def simulate_disease_spread(
        self,
        disease_name: str,
        current_incidence: float,
        field_size_ha: float,
        weather_forecast: List[Dict[str, float]],
        control_measures: Optional[List[str]] = None
    ) -> DiseaseProgression:
        """
        Simulate disease progression.
        
        Args:
            disease_name: Disease name
            current_incidence: Current disease incidence (%)
            field_size_ha: Field size in hectares
            weather_forecast: Weather forecast data
            control_measures: Applied control measures
            
        Returns:
            Disease progression forecast
        """
        logger.info(f"Simulating disease spread for {disease_name}")
        
        # Get disease profile
        profile = self.disease_db.get_disease_profile(disease_name)
        if not profile:
            logger.warning(f"Disease profile not found: {disease_name}")
            profile = self._get_default_profile(disease_name)
        
        # Calculate effective transmission rate
        transmission_rate = self._calculate_transmission_rate(
            profile,
            weather_forecast,
            control_measures
        )
        
        # Simulate spread using epidemic model
        forecast = self._run_epidemic_model(
            current_incidence,
            transmission_rate,
            len(weather_forecast)
        )
        
        # Calculate doubling time
        doubling_time = self._calculate_doubling_time(
            current_incidence,
            transmission_rate
        )
        
        # Find peak
        peak_date, peak_incidence = self._find_epidemic_peak(forecast)
        
        # Calculate spread rate
        if len(forecast) > 1:
            spread_rate = (forecast[1][1] - forecast[0][1])
        else:
            spread_rate = 0
        
        # Estimate area affected
        area_affected = (forecast[-1][1] / 100) * field_size_ha
        
        # Estimate yield loss
        yield_loss = self._estimate_yield_loss(
            forecast[-1][1],
            profile
        )
        
        # Estimate economic impact
        economic_impact = self._estimate_economic_impact(
            field_size_ha,
            yield_loss
        )
        
        # Determine current stage
        stage = self._determine_disease_stage(current_incidence)
        
        return DiseaseProgression(
            disease=disease_name,
            current_stage=stage,
            current_incidence=current_incidence,
            forecasted_incidence=forecast,
            doubling_time_days=doubling_time,
            peak_incidence_date=peak_date,
            peak_incidence_pct=peak_incidence,
            spread_rate=spread_rate,
            area_affected_pct=(area_affected / field_size_ha) * 100,
            yield_loss_pct=yield_loss,
            economic_impact=economic_impact
        )
    
    def _calculate_transmission_rate(
        self,
        profile: DiseaseProfile,
        weather: List[Dict[str, float]],
        controls: Optional[List[str]]
    ) -> float:
        """Calculate effective transmission rate."""
        base_rate = profile.transmission_rate
        
        # Weather adjustment
        avg_temp = np.mean([w.get("temperature", 25) for w in weather])
        temp_min, temp_max = profile.optimal_temp_range
        
        if temp_min <= avg_temp <= temp_max:
            weather_factor = 1.2
        else:
            weather_factor = 0.8
        
        # Control measures adjustment
        control_factor = 1.0
        if controls:
            if "fungicide" in controls:
                control_factor *= 0.4
            if "resistant_variety" in controls:
                control_factor *= 0.6
            if "crop_rotation" in controls:
                control_factor *= 0.7
            if "sanitation" in controls:
                control_factor *= 0.8
        
        effective_rate = base_rate * weather_factor * control_factor
        
        return effective_rate
    
    def _run_epidemic_model(
        self,
        initial_incidence: float,
        transmission_rate: float,
        days: int
    ) -> List[Tuple[datetime, float]]:
        """Run epidemic model simulation."""
        # Logistic growth model for disease spread
        def logistic_growth(y, t, r, K):
            return r * y * (1 - y / K)
        
        # Initial condition (as proportion)
        y0 = initial_incidence / 100
        
        # Carrying capacity (maximum incidence)
        K = 0.95  # 95% maximum
        
        # Time points
        t = np.linspace(0, days, days + 1)
        
        # Solve ODE
        solution = odeint(logistic_growth, y0, t, args=(transmission_rate, K))
        
        # Convert to forecast format
        forecast = []
        for i, incidence in enumerate(solution):
            date = datetime.now() + timedelta(days=i)
            forecast.append((date, min(95, incidence[0] * 100)))
        
        return forecast
    
    def _calculate_doubling_time(
        self,
        current_incidence: float,
        transmission_rate: float
    ) -> float:
        """Calculate disease doubling time."""
        if transmission_rate <= 0:
            return float('inf')
        
        # Exponential growth doubling time
        doubling_time = np.log(2) / transmission_rate
        
        return doubling_time
    
    def _find_epidemic_peak(
        self,
        forecast: List[Tuple[datetime, float]]
    ) -> Tuple[datetime, float]:
        """Find epidemic peak."""
        peak_incidence = 0
        peak_date = datetime.now()
        
        for date, incidence in forecast:
            if incidence > peak_incidence:
                peak_incidence = incidence
                peak_date = date
        
        return peak_date, peak_incidence
    
    def _estimate_yield_loss(
        self,
        final_incidence: float,
        profile: DiseaseProfile
    ) -> float:
        """Estimate yield loss from disease."""
        # Disease-specific yield loss relationships
        if profile.disease_type == DiseaseType.FUNGAL:
            # Non-linear relationship
            yield_loss = final_incidence * 0.8
        elif profile.disease_type == DiseaseType.BACTERIAL:
            yield_loss = final_incidence * 0.9
        elif profile.disease_type == DiseaseType.VIRAL:
            yield_loss = final_incidence * 1.1
        else:
            yield_loss = final_incidence * 0.7
        
        return min(100, yield_loss)
    
    def _estimate_economic_impact(
        self,
        field_size_ha: float,
        yield_loss_pct: float
    ) -> float:
        """Estimate economic impact."""
        # Assumed crop value (KES per hectare)
        crop_value_per_ha = 150000
        
        total_value = crop_value_per_ha * field_size_ha
        loss = total_value * (yield_loss_pct / 100)
        
        return loss
    
    def _determine_disease_stage(self, incidence: float) -> DiseaseStage:
        """Determine disease stage from incidence."""
        if incidence < 1:
            return DiseaseStage.ABSENT
        elif incidence < 10:
            return DiseaseStage.EARLY
        elif incidence < 30:
            return DiseaseStage.ESTABLISHED
        elif incidence < 60:
            return DiseaseStage.SEVERE
        else:
            return DiseaseStage.EPIDEMIC
    
    def _get_default_profile(self, disease_name: str) -> DiseaseProfile:
        """Create default disease profile."""
        return DiseaseProfile(
            disease_name=disease_name,
            pathogen="Unknown",
            disease_type=DiseaseType.FUNGAL,
            hosts=["unknown"],
            optimal_temp_range=(20, 30),
            optimal_humidity=80,
            incubation_period_days=7,
            transmission_rate=0.2,
            survival_days=30,
            severity_factors={}
        )
