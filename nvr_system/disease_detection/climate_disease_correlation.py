"""
Climate-Disease Correlation Engine
Predicts disease risk based on environmental conditions

CRITICAL ENVIRONMENTAL TRIGGERS:

TEMPERATURE THRESHOLDS:
- Phytophthora infestans (late blight): 10-25°C OPTIMAL (epidemic zone)
- Powdery mildew: 15-27°C OPTIMAL, inhibited >35°C
- Downy mildew: 10-22°C OPTIMAL, dies >30°C
- Bacterial blight: 24-32°C OPTIMAL (hot humid)
- Coffee leaf rust: 21-25°C OPTIMAL, inhibited <15°C and >28°C
- Tea blister blight: 20-25°C OPTIMAL (monsoon season)

HUMIDITY REQUIREMENTS:
- Late blight: 90%+ RH required for infection
- Downy mildew: 95%+ RH required (high humidity obligate)
- Powdery mildew: 40-70% RH optimal (INHIBITED by free water!)
- Bacterial diseases: 85%+ RH (water film required)
- Botrytis: 85-95% RH (wet conditions)

LEAF WETNESS DURATION:
- Late blight: 12 hours minimum for infection
- Apple scab: Mills table (temperature + wetness hours = infection)
- Anthracnose: 6-12 hours wetness
- Bacterial spot: 4-8 hours wetness minimum

RAINFALL TRIGGERS:
- Citrus canker: 25mm+ rain = SPLASH DISPERSAL epidemic
- Coffee berry disease: 100mm+ monthly = HIGH RISK
- Downy mildew: 10mm rain = infection event
- Black Sigatoka: >2000mm annual = severe pressure

ALTITUDE EFFECTS:
- Coffee leaf rust: 1200-1800m OPTIMAL (disappears >2000m, severe <1000m)
- Tea blister blight: 1400-2100m HIGH RISK (monsoon elevation)
- Powdery mildew: Sea level to 1500m
- Climate warming: Diseases moving to higher elevations

VAPOR PRESSURE DEFICIT (VPD):
- VPD <0.4 kPa: High disease risk (wet conditions)
- VPD 0.4-1.2 kPa: Moderate disease risk
- VPD >1.2 kPa: Low disease risk (dry conditions)
- VPD = (1 - RH/100) × Saturated Vapor Pressure

Author: AgroPulse AI Team
Version: 1.0.0
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Tuple, Optional
import math
from datetime import datetime, timedelta


class DiseaseRiskLevel(Enum):
    """Disease risk levels"""
    EXTREME = "extreme"  # Epidemic conditions
    HIGH = "high"  # Favorable conditions
    MODERATE = "moderate"  # Marginal conditions
    LOW = "low"  # Unfavorable conditions
    NONE = "none"  # Inhibitory conditions


class ClimateZone(Enum):
    """Climate classification"""
    TROPICAL = "tropical"
    SUBTROPICAL = "subtropical"
    TEMPERATE = "temperate"
    COOL_TEMPERATE = "cool_temperate"
    MEDITERRANEAN = "mediterranean"
    ARID = "arid"
    MONSOON = "monsoon"


@dataclass
class EnvironmentalConditions:
    """Current environmental parameters"""
    temperature_c: float
    relative_humidity: float  # 0-100
    leaf_wetness_hours: float
    rainfall_mm: float  # Daily
    wind_speed_ms: Optional[float] = None
    
    # Extended period data
    rainfall_7day: Optional[float] = None
    rainfall_monthly: Optional[float] = None
    avg_temp_7day: Optional[float] = None
    
    # Location
    altitude_m: Optional[float] = None
    latitude: Optional[float] = None


@dataclass
class DiseaseClimateProfile:
    """Climate requirements for disease development"""
    disease_name: str
    pathogen: str
    
    # Temperature
    temp_min: float
    temp_optimal_min: float
    temp_optimal_max: float
    temp_max: float
    
    # Humidity
    rh_min: float  # Minimum RH for infection
    rh_optimal: float  # Optimal RH
    
    # Leaf wetness
    wetness_hours_min: float  # Minimum hours for infection
    wetness_optimal_hours: float  # Optimal wetness period
    
    # Rainfall
    rainfall_trigger_mm: Optional[float] = None  # Rainfall amount that triggers epidemic
    
    # VPD
    vpd_max_kpa: Optional[float] = None  # Maximum VPD for infection
    
    # Altitude
    altitude_min_m: Optional[float] = None
    altitude_max_m: Optional[float] = None
    
    # Special conditions
    inhibited_by_free_water: bool = False  # Powdery mildew
    requires_cool_nights: bool = False
    
    notes: str = ""


@dataclass
class InfectionPeriod:
    """Mills table or similar infection period model"""
    disease: str
    temperature_c: float
    wetness_hours: float
    infection_occurred: bool
    severity: str  # light, moderate, severe
    
    hours_to_infection: float
    confidence: float


@dataclass
class DiseaseRiskForecast:
    """Disease risk prediction"""
    disease: str
    risk_level: DiseaseRiskLevel
    confidence: float
    
    # Contributing factors
    temperature_favorable: bool
    humidity_favorable: bool
    wetness_sufficient: bool
    rainfall_trigger: bool
    
    # Risk score components
    temperature_score: float  # 0-1
    humidity_score: float  # 0-1
    wetness_score: float  # 0-1
    overall_score: float  # 0-1
    
    # Recommendations
    action_required: bool
    spray_recommended: bool
    days_to_infection: Optional[int] = None
    
    notes: str = ""


class ClimateDiseaseCorrelation:
    """
    Climate-disease correlation engine
    
    FEATURES:
    - Disease risk prediction
    - Infection period models
    - VPD calculations
    - Epidemic forecasting
    """
    
    def __init__(self):
        self.disease_profiles = self._initialize_disease_profiles()
    
    def _initialize_disease_profiles(self) -> Dict[str, DiseaseClimateProfile]:
        """Comprehensive disease climate requirements"""
        return {
            'late_blight': DiseaseClimateProfile(
                disease_name='Late Blight',
                pathogen='Phytophthora infestans',
                temp_min=3.0,
                temp_optimal_min=10.0,
                temp_optimal_max=25.0,
                temp_max=30.0,
                rh_min=90.0,
                rh_optimal=95.0,
                wetness_hours_min=12.0,
                wetness_optimal_hours=24.0,
                rainfall_trigger_mm=10.0,
                vpd_max_kpa=0.4,
                notes='EPIDEMIC PATHOGEN: 10-25°C + 90%+ RH + 12h wetness = DISASTER'
            ),
            
            'powdery_mildew': DiseaseClimateProfile(
                disease_name='Powdery Mildew',
                pathogen='Various Erysiphales',
                temp_min=10.0,
                temp_optimal_min=15.0,
                temp_optimal_max=27.0,
                temp_max=35.0,
                rh_min=40.0,
                rh_optimal=70.0,
                wetness_hours_min=0.0,  # Does NOT require leaf wetness!
                wetness_optimal_hours=0.0,
                inhibited_by_free_water=True,
                notes='UNIQUE: Inhibited by free water (rain washes spores), favors dry conditions with moderate RH'
            ),
            
            'downy_mildew': DiseaseClimateProfile(
                disease_name='Downy Mildew',
                pathogen='Peronosporales',
                temp_min=5.0,
                temp_optimal_min=10.0,
                temp_optimal_max=22.0,
                temp_max=30.0,
                rh_min=95.0,
                rh_optimal=100.0,
                wetness_hours_min=6.0,
                wetness_optimal_hours=12.0,
                rainfall_trigger_mm=10.0,
                vpd_max_kpa=0.3,
                requires_cool_nights=True,
                notes='HIGH HUMIDITY OBLIGATE: 95%+ RH required, cool mornings with dew'
            ),
            
            'bacterial_spot': DiseaseClimateProfile(
                disease_name='Bacterial Spot',
                pathogen='Xanthomonas spp.',
                temp_min=15.0,
                temp_optimal_min=24.0,
                temp_optimal_max=32.0,
                temp_max=38.0,
                rh_min=85.0,
                rh_optimal=95.0,
                wetness_hours_min=4.0,
                wetness_optimal_hours=8.0,
                rainfall_trigger_mm=25.0,
                notes='HOT + HUMID: 24-32°C + high RH + rain splash = severe'
            ),
            
            'coffee_leaf_rust': DiseaseClimateProfile(
                disease_name='Coffee Leaf Rust',
                pathogen='Hemileia vastatrix',
                temp_min=15.0,
                temp_optimal_min=21.0,
                temp_optimal_max=25.0,
                temp_max=28.0,
                rh_min=85.0,
                rh_optimal=95.0,
                wetness_hours_min=6.0,
                wetness_optimal_hours=12.0,
                altitude_min_m=600.0,
                altitude_max_m=1800.0,
                notes='ALTITUDE CRITICAL: 1200-1800m optimal, disappears >2000m, severe <1000m'
            ),
            
            'tea_blister_blight': DiseaseClimateProfile(
                disease_name='Tea Blister Blight',
                pathogen='Exobasidium venkatesii',
                temp_min=15.0,
                temp_optimal_min=20.0,
                temp_optimal_max=25.0,
                temp_max=30.0,
                rh_min=90.0,
                rh_optimal=98.0,
                wetness_hours_min=8.0,
                wetness_optimal_hours=24.0,
                rainfall_trigger_mm=200.0,  # Monthly
                altitude_min_m=1400.0,
                altitude_max_m=2100.0,
                notes='MONSOON DISEASE: Heavy rain + high elevation + cool temps = epidemic'
            ),
            
            'citrus_canker': DiseaseClimateProfile(
                disease_name='Citrus Canker',
                pathogen='Xanthomonas citri',
                temp_min=20.0,
                temp_optimal_min=25.0,
                temp_optimal_max=35.0,
                temp_max=40.0,
                rh_min=80.0,
                rh_optimal=95.0,
                wetness_hours_min=2.0,
                wetness_optimal_hours=4.0,
                rainfall_trigger_mm=25.0,
                notes='RAIN SPLASH: 25mm+ rain = massive splash dispersal epidemic'
            ),
            
            'apple_scab': DiseaseClimateProfile(
                disease_name='Apple Scab',
                pathogen='Venturia inaequalis',
                temp_min=0.0,
                temp_optimal_min=12.0,
                temp_optimal_max=24.0,
                temp_max=32.0,
                rh_min=95.0,
                rh_optimal=100.0,
                wetness_hours_min=6.0,  # Mills table minimum
                wetness_optimal_hours=18.0,
                notes='MILLS TABLE: Infection hours = f(temperature, wetness duration)'
            ),
            
            'botrytis': DiseaseClimateProfile(
                disease_name='Botrytis Gray Mold',
                pathogen='Botrytis cinerea',
                temp_min=0.0,
                temp_optimal_min=15.0,
                temp_optimal_max=23.0,
                temp_max=30.0,
                rh_min=85.0,
                rh_optimal=93.0,
                wetness_hours_min=4.0,
                wetness_optimal_hours=12.0,
                notes='COOL + WET: Favors cool humid conditions, post-harvest threat'
            )
        }
    
    def calculate_vpd(self, temperature_c: float, relative_humidity: float) -> float:
        """
        Calculate Vapor Pressure Deficit (VPD)
        
        VPD indicates atmospheric moisture stress
        Low VPD = humid (disease favorable)
        High VPD = dry (disease unfavorable)
        """
        # Saturated vapor pressure (SVP) using Magnus formula
        svp = 0.6108 * math.exp((17.27 * temperature_c) / (temperature_c + 237.3))
        
        # Actual vapor pressure
        avp = svp * (relative_humidity / 100.0)
        
        # VPD in kPa
        vpd = svp - avp
        
        return vpd
    
    def mills_table_infection(self, temperature_c: float, wetness_hours: float) -> InfectionPeriod:
        """
        Mills table for apple scab infection periods
        
        MILLS TABLE:
        Temperature (°C) | Hours wetness for infection | Severity
        0-5              | No infection                | -
        6                | 28 hours                    | Light
        7-9              | 26-28 hours                 | Light
        10-12            | 15-17 hours                 | Moderate
        13-17            | 14-15 hours                 | Moderate
        18-20            | 12-14 hours                 | Severe
        21-24            | 9-12 hours                  | Severe
        25+              | No infection                | -
        """
        # Mills table lookup
        mills_table = {
            (0, 6): (999, "none"),
            (6, 7): (28, "light"),
            (7, 10): (26, "light"),
            (10, 13): (15, "moderate"),
            (13, 18): (14, "moderate"),
            (18, 21): (12, "severe"),
            (21, 25): (9, "severe"),
            (25, 50): (999, "none")
        }
        
        # Find matching range
        hours_required = 999
        severity = "none"
        
        for (temp_min, temp_max), (hours, sev) in mills_table.items():
            if temp_min <= temperature_c < temp_max:
                hours_required = hours
                severity = sev
                break
        
        infection_occurred = wetness_hours >= hours_required
        
        return InfectionPeriod(
            disease='Apple Scab',
            temperature_c=temperature_c,
            wetness_hours=wetness_hours,
            infection_occurred=infection_occurred,
            severity=severity if infection_occurred else "none",
            hours_to_infection=hours_required,
            confidence=0.9 if infection_occurred else 0.3
        )
    
    def assess_disease_risk(
        self, 
        disease: str, 
        conditions: EnvironmentalConditions
    ) -> DiseaseRiskForecast:
        """
        Assess disease risk based on current conditions
        """
        if disease not in self.disease_profiles:
            return DiseaseRiskForecast(
                disease=disease,
                risk_level=DiseaseRiskLevel.NONE,
                confidence=0.0,
                temperature_favorable=False,
                humidity_favorable=False,
                wetness_sufficient=False,
                rainfall_trigger=False,
                temperature_score=0.0,
                humidity_score=0.0,
                wetness_score=0.0,
                overall_score=0.0,
                action_required=False,
                spray_recommended=False,
                notes="Disease profile not found"
            )
        
        profile = self.disease_profiles[disease]
        
        # Temperature score
        temp_score = self._calculate_temperature_score(
            conditions.temperature_c,
            profile.temp_min,
            profile.temp_optimal_min,
            profile.temp_optimal_max,
            profile.temp_max
        )
        
        # Humidity score
        humidity_score = self._calculate_humidity_score(
            conditions.relative_humidity,
            profile.rh_min,
            profile.rh_optimal
        )
        
        # Wetness score
        wetness_score = self._calculate_wetness_score(
            conditions.leaf_wetness_hours,
            profile.wetness_hours_min,
            profile.wetness_optimal_hours
        )
        
        # Special conditions
        if profile.inhibited_by_free_water and conditions.leaf_wetness_hours > 2:
            # Powdery mildew inhibited by free water
            wetness_score = 0.0
            humidity_score *= 0.5
        
        # VPD check
        vpd = self.calculate_vpd(conditions.temperature_c, conditions.relative_humidity)
        if profile.vpd_max_kpa and vpd > profile.vpd_max_kpa:
            humidity_score *= 0.5
        
        # Altitude check
        if conditions.altitude_m and profile.altitude_min_m and profile.altitude_max_m:
            if not (profile.altitude_min_m <= conditions.altitude_m <= profile.altitude_max_m):
                temp_score *= 0.3
        
        # Rainfall trigger
        rainfall_trigger = False
        if profile.rainfall_trigger_mm and conditions.rainfall_mm:
            rainfall_trigger = conditions.rainfall_mm >= profile.rainfall_trigger_mm
        
        # Overall risk score
        overall_score = (temp_score + humidity_score + wetness_score) / 3.0
        
        # Determine risk level
        if overall_score >= 0.8:
            risk_level = DiseaseRiskLevel.EXTREME
        elif overall_score >= 0.6:
            risk_level = DiseaseRiskLevel.HIGH
        elif overall_score >= 0.4:
            risk_level = DiseaseRiskLevel.MODERATE
        elif overall_score >= 0.2:
            risk_level = DiseaseRiskLevel.LOW
        else:
            risk_level = DiseaseRiskLevel.NONE
        
        # Action recommendations
        action_required = risk_level in [DiseaseRiskLevel.EXTREME, DiseaseRiskLevel.HIGH]
        spray_recommended = risk_level == DiseaseRiskLevel.EXTREME or (
            risk_level == DiseaseRiskLevel.HIGH and rainfall_trigger
        )
        
        # Days to infection estimate
        days_to_infection = None
        if wetness_score > 0.5 and temp_score > 0.5:
            # Infection likely within 1-3 days
            days_to_infection = 1 if overall_score > 0.8 else 2
        
        return DiseaseRiskForecast(
            disease=disease,
            risk_level=risk_level,
            confidence=overall_score,
            temperature_favorable=temp_score > 0.5,
            humidity_favorable=humidity_score > 0.5,
            wetness_sufficient=wetness_score > 0.5,
            rainfall_trigger=rainfall_trigger,
            temperature_score=temp_score,
            humidity_score=humidity_score,
            wetness_score=wetness_score,
            overall_score=overall_score,
            action_required=action_required,
            spray_recommended=spray_recommended,
            days_to_infection=days_to_infection,
            notes=f"VPD: {vpd:.2f} kPa | {profile.notes}"
        )
    
    def _calculate_temperature_score(
        self, 
        temp: float, 
        temp_min: float, 
        opt_min: float, 
        opt_max: float, 
        temp_max: float
    ) -> float:
        """Calculate temperature favorability score (0-1)"""
        if temp < temp_min or temp > temp_max:
            return 0.0
        
        if opt_min <= temp <= opt_max:
            return 1.0
        
        if temp < opt_min:
            # Between min and optimal min
            return (temp - temp_min) / (opt_min - temp_min)
        else:
            # Between optimal max and max
            return (temp_max - temp) / (temp_max - opt_max)
    
    def _calculate_humidity_score(self, rh: float, rh_min: float, rh_optimal: float) -> float:
        """Calculate humidity favorability score (0-1)"""
        if rh < rh_min:
            return 0.0
        
        if rh >= rh_optimal:
            return 1.0
        
        # Linear between min and optimal
        return (rh - rh_min) / (rh_optimal - rh_min)
    
    def _calculate_wetness_score(
        self, 
        wetness: float, 
        min_hours: float, 
        optimal_hours: float
    ) -> float:
        """Calculate leaf wetness favorability score (0-1)"""
        if wetness < min_hours:
            return 0.0
        
        if wetness >= optimal_hours:
            return 1.0
        
        # Linear between min and optimal
        if optimal_hours > min_hours:
            return (wetness - min_hours) / (optimal_hours - min_hours)
        else:
            return 1.0
    
    def predict_epidemic_conditions(
        self, 
        disease: str, 
        forecast_conditions: List[EnvironmentalConditions],
        days: int = 7
    ) -> Dict:
        """Predict epidemic development over forecast period"""
        daily_risks = []
        
        for conditions in forecast_conditions[:days]:
            risk = self.assess_disease_risk(disease, conditions)
            daily_risks.append(risk)
        
        # Analyze risk pattern
        high_risk_days = sum(1 for r in daily_risks if r.risk_level in [
            DiseaseRiskLevel.EXTREME, DiseaseRiskLevel.HIGH
        ])
        
        extreme_risk_days = sum(1 for r in daily_risks if r.risk_level == DiseaseRiskLevel.EXTREME)
        
        # Epidemic threshold
        epidemic_likely = extreme_risk_days >= 2 or high_risk_days >= 4
        
        return {
            'disease': disease,
            'forecast_days': days,
            'daily_risks': daily_risks,
            'high_risk_days': high_risk_days,
            'extreme_risk_days': extreme_risk_days,
            'epidemic_likely': epidemic_likely,
            'spray_urgency': 'critical' if extreme_risk_days > 0 else 'moderate' if high_risk_days > 2 else 'low'
        }


def main():
    """Example usage"""
    engine = ClimateDiseaseCorrelation()
    
    print("=== AgroPulse Climate-Disease Correlation Engine ===")
    print(f"\nDisease profiles loaded: {len(engine.disease_profiles)}")
    
    print("\n🌡️ DISEASE CLIMATE REQUIREMENTS:")
    
    print("\n1. LATE BLIGHT (Phytophthora infestans)")
    print("   Temperature: 10-25°C optimal (EPIDEMIC ZONE)")
    print("   Humidity: 90%+ RH required")
    print("   Leaf wetness: 12+ hours minimum")
    print("   VPD: <0.4 kPa (wet conditions)")
    print("   ⚠️ MOST DESTRUCTIVE DISEASE IN HISTORY")
    
    print("\n2. POWDERY MILDEW")
    print("   Temperature: 15-27°C optimal")
    print("   Humidity: 40-70% RH (moderate, NOT high!)")
    print("   Leaf wetness: 0 hours (INHIBITED by free water!)")
    print("   🌧️ UNIQUE: Rain washes away spores")
    
    print("\n3. COFFEE LEAF RUST")
    print("   Temperature: 21-25°C optimal")
    print("   Altitude: 1200-1800m OPTIMAL")
    print("   🏔️ Disappears >2000m elevation")
    print("   🌡️ Climate warming = moving higher")
    
    # Test late blight risk
    print("\n📊 LATE BLIGHT RISK ASSESSMENT:")
    
    # Favorable conditions
    conditions_favorable = EnvironmentalConditions(
        temperature_c=18.0,
        relative_humidity=95.0,
        leaf_wetness_hours=15.0,
        rainfall_mm=12.0
    )
    
    risk = engine.assess_disease_risk('late_blight', conditions_favorable)
    print(f"\n🚨 Favorable conditions (18°C, 95% RH, 15h wetness):")
    print(f"   Risk Level: {risk.risk_level.value.upper()}")
    print(f"   Overall Score: {risk.overall_score:.2f}")
    print(f"   Temperature: {'✅' if risk.temperature_favorable else '❌'} ({risk.temperature_score:.2f})")
    print(f"   Humidity: {'✅' if risk.humidity_favorable else '❌'} ({risk.humidity_score:.2f})")
    print(f"   Wetness: {'✅' if risk.wetness_sufficient else '❌'} ({risk.wetness_score:.2f})")
    print(f"   🎯 Spray recommended: {'YES' if risk.spray_recommended else 'NO'}")
    
    # Unfavorable conditions
    conditions_unfavorable = EnvironmentalConditions(
        temperature_c=32.0,
        relative_humidity=65.0,
        leaf_wetness_hours=2.0,
        rainfall_mm=0.0
    )
    
    risk2 = engine.assess_disease_risk('late_blight', conditions_unfavorable)
    print(f"\n✅ Unfavorable conditions (32°C, 65% RH, 2h wetness):")
    print(f"   Risk Level: {risk2.risk_level.value.upper()}")
    print(f"   Overall Score: {risk2.overall_score:.2f}")
    
    # Mills table test
    print("\n📈 MILLS TABLE (Apple Scab):")
    print("\nTemperature | Wetness Hours | Infection | Severity")
    print("-" * 55)
    
    test_cases = [
        (10, 18, "Yes", "Moderate"),
        (18, 15, "Yes", "Severe"),
        (24, 10, "Yes", "Severe"),
        (10, 10, "No", "None"),
        (30, 20, "No", "None")
    ]
    
    for temp, wetness, expected, severity in test_cases:
        infection = engine.mills_table_infection(temp, wetness)
        status = "✅" if infection.infection_occurred else "❌"
        print(f"{temp:5}°C    | {wetness:6.0f} hours  | {status} {expected:3} | {infection.severity.capitalize()}")
    
    print("\n✅ SYSTEM STATUS: Climate correlation operational")


if __name__ == "__main__":
    main()
