"""
Disease Forecasting Models
Epidemic prediction using weather data and infection models

FORECASTING SYSTEMS:

LATE BLIGHT FORECASTING:
- BlightCast (USA): Accumulated severity values (temperature + RH)
- Smith Period: 90%+ RH for 12+ hours at 10-25°C = infection
- Hyre Model: Degree-day accumulation with RH weighting
- Negative prognosis: Cool dry weather stops epidemic
- Positive prognosis: Warm humid weather = explosive growth

APPLE SCAB FORECASTING:
- Mills Table: Temperature + leaf wetness hours = infection severity
- Degree-day models: Ascospore maturation timing
- RIMpro: Comprehensive European model (maturation + infection)
- Hourly infection periods: Track each rain event

DOWNY MILDEW FORECASTING:
- DMCast (Cucurbits): Temperature + leaf wetness + disease pressure
- 10-rule: 5 consecutive nights >10°C, RH >90%, 10mm rain
- Sporangial production: Cool nights + high humidity
- Oospore survival: Overwinter in soil/debris

POWDERY MILDEW FORECASTING:
- DMI sensitivity: Temperature + VPD optimal conditions
- Degree-day accumulation: Predict peak infection periods
- VPD thresholds: 0.4-1.2 kPa optimal for conidial germination
- Rain inhibitory: Heavy rain washes spores (temporary suppression)

FIRE BLIGHT FORECASTING:
- Maryblyt (USA): Blossom blight prediction, canker blight
- CougarBlight (USA): Refined temperature-wetness model
- BIS95 (Europe): Integrated infection risk
- Critical: Bloom period + temperature >18°C + wetness

FUSARIUM HEAD BLIGHT (Wheat):
- DON accumulation models: Mycotoxin risk prediction
- Flowering + rain = infection event
- Temperature 25-30°C optimal for toxin production

COFFEE LEAF RUST:
- Temperature: 21-25°C optimal (inhibited <15°C, >28°C)
- Altitude: 1200-1800m highest risk zone
- Rainfall: 1500-2500mm annual optimal
- Shade level: 30-50% reduces epidemic
- Climate change: Moving to higher elevations

Author: AgroPulse AI Team
Version: 1.0.0
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Tuple, Optional
from datetime import datetime, timedelta
import math


class EpidemicRisk(Enum):
    """Epidemic risk levels"""
    NONE = "none"
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    CRITICAL = "critical"


class InfectionEvent(Enum):
    """Infection event status"""
    NO_INFECTION = "no_infection"
    LIGHT_INFECTION = "light_infection"
    MODERATE_INFECTION = "moderate_infection"
    SEVERE_INFECTION = "severe_infection"


@dataclass
class WeatherData:
    """Hourly or daily weather data"""
    timestamp: datetime
    temperature_c: float
    relative_humidity: float
    leaf_wetness_hours: float
    rainfall_mm: float
    wind_speed_ms: Optional[float] = None
    solar_radiation: Optional[float] = None


@dataclass
class SmithPeriod:
    """Smith period for late blight (Phytophthora infestans)"""
    start_time: datetime
    end_time: datetime
    duration_hours: float
    avg_temperature: float
    avg_humidity: float
    
    is_favorable: bool  # True if conditions favor infection
    severity_value: float  # Accumulated severity
    
    notes: str = ""


@dataclass
class MillsInfection:
    """Mills table infection period (apple scab)"""
    timestamp: datetime
    temperature_c: float
    wetness_hours: float
    
    infection_occurred: bool
    severity: str  # light, moderate, severe
    hours_required: float
    
    confidence: float


@dataclass
class EpidemicForecast:
    """Epidemic development forecast"""
    disease: str
    forecast_date: datetime
    forecast_days: int
    
    # Current status
    current_disease_pressure: str  # none, low, moderate, high
    inoculum_present: bool
    
    # Forecast
    infection_events: List[Tuple[datetime, InfectionEvent]]
    epidemic_risk: EpidemicRisk
    
    # Accumulated values
    severity_value_total: float
    infection_periods: int
    favorable_days: int
    
    # Recommendations
    spray_recommended: bool
    spray_timing: Optional[datetime] = None
    urgency: str = "low"  # low, moderate, high, critical
    
    notes: str = ""


@dataclass
class DiseaseSpreadModel:
    """Disease spread rate modeling"""
    disease: str
    initial_incidence: float  # % of plants infected
    
    # Spread parameters
    days_elapsed: int
    current_incidence: float  # Current % infected
    doubling_time_days: float  # Epidemic doubling time
    
    # Projection
    projected_7day: float
    projected_14day: float
    projected_21day: float
    
    # Control impact
    with_treatment_7day: float
    with_treatment_14day: float
    
    epidemic_status: str  # stable, increasing, explosive
    
    notes: str = ""


class DiseaseForecastingModel:
    """
    Disease forecasting models
    
    FEATURES:
    - Late blight forecasting (Smith periods, BlightCast)
    - Apple scab (Mills table)
    - Epidemic spread modeling
    - Weather-based predictions
    """
    
    def __init__(self):
        pass
    
    def calculate_smith_period(
        self, 
        weather_data: List[WeatherData]
    ) -> List[SmithPeriod]:
        """
        Calculate Smith periods for late blight
        
        Smith Period: 90%+ RH for 12+ consecutive hours at 10-25°C
        """
        smith_periods = []
        
        # Find consecutive periods with favorable conditions
        period_start = None
        period_temps = []
        period_hums = []
        
        for i, data in enumerate(weather_data):
            favorable = (
                data.relative_humidity >= 90.0 and
                10.0 <= data.temperature_c <= 25.0
            )
            
            if favorable:
                if period_start is None:
                    period_start = data.timestamp
                    period_temps = [data.temperature_c]
                    period_hums = [data.relative_humidity]
                else:
                    period_temps.append(data.temperature_c)
                    period_hums.append(data.relative_humidity)
            else:
                # End of period
                if period_start is not None:
                    hours = len(period_temps)
                    
                    if hours >= 12:  # Minimum 12 hours
                        avg_temp = sum(period_temps) / len(period_temps)
                        avg_hum = sum(period_hums) / len(period_hums)
                        
                        # Calculate severity value
                        severity = self._calculate_late_blight_severity(
                            hours, avg_temp, avg_hum
                        )
                        
                        smith_periods.append(SmithPeriod(
                            start_time=period_start,
                            end_time=data.timestamp,
                            duration_hours=hours,
                            avg_temperature=avg_temp,
                            avg_humidity=avg_hum,
                            is_favorable=True,
                            severity_value=severity,
                            notes=f"Smith period: {hours}h at {avg_temp:.1f}°C"
                        ))
                    
                    # Reset
                    period_start = None
                    period_temps = []
                    period_hums = []
        
        return smith_periods
    
    def _calculate_late_blight_severity(
        self, 
        hours: float, 
        temperature: float, 
        humidity: float
    ) -> float:
        """
        Calculate late blight severity value
        
        Higher temperature + longer duration = higher severity
        """
        # Base severity (hours of favorable conditions)
        base_severity = hours / 12.0  # Normalize to 12-hour periods
        
        # Temperature adjustment (15-20°C optimal)
        if 15.0 <= temperature <= 20.0:
            temp_factor = 1.0
        elif temperature < 15.0:
            temp_factor = 0.5 + (temperature - 10.0) / 10.0
        else:
            temp_factor = 1.0 - (temperature - 20.0) / 10.0
        
        # Humidity adjustment (higher = worse)
        humidity_factor = (humidity - 90.0) / 10.0 + 1.0
        
        severity = base_severity * temp_factor * humidity_factor
        
        return max(0.0, severity)
    
    def mills_table_forecast(
        self,
        weather_forecast: List[WeatherData]
    ) -> List[MillsInfection]:
        """
        Apply Mills table to weather forecast
        
        Predicts apple scab infection periods
        """
        infections = []
        
        # Mills table (simplified)
        mills_table = {
            (6, 7): 28,    # 6-7°C: 28 hours
            (7, 10): 26,   # 7-10°C: 26 hours
            (10, 13): 15,  # 10-13°C: 15 hours
            (13, 18): 14,  # 13-18°C: 14 hours
            (18, 21): 12,  # 18-21°C: 12 hours
            (21, 25): 9    # 21-25°C: 9 hours
        }
        
        for data in weather_forecast:
            if data.leaf_wetness_hours > 0:
                # Find matching temperature range
                hours_required = 999
                for (temp_min, temp_max), hours in mills_table.items():
                    if temp_min <= data.temperature_c < temp_max:
                        hours_required = hours
                        break
                
                infection_occurred = data.leaf_wetness_hours >= hours_required
                
                if infection_occurred:
                    # Determine severity
                    if data.leaf_wetness_hours >= hours_required * 1.5:
                        severity = "severe"
                    elif data.leaf_wetness_hours >= hours_required * 1.2:
                        severity = "moderate"
                    else:
                        severity = "light"
                    
                    infections.append(MillsInfection(
                        timestamp=data.timestamp,
                        temperature_c=data.temperature_c,
                        wetness_hours=data.leaf_wetness_hours,
                        infection_occurred=True,
                        severity=severity,
                        hours_required=hours_required,
                        confidence=0.85
                    ))
        
        return infections
    
    def forecast_epidemic(
        self,
        disease: str,
        weather_forecast: List[WeatherData],
        current_disease_pressure: str = "low",
        inoculum_present: bool = True
    ) -> EpidemicForecast:
        """
        Forecast epidemic development
        """
        forecast_date = weather_forecast[0].timestamp if weather_forecast else datetime.now()
        forecast_days = len(weather_forecast)
        
        # Disease-specific forecasting
        if disease.lower() in ['late blight', 'phytophthora']:
            return self._forecast_late_blight(
                weather_forecast, current_disease_pressure, inoculum_present
            )
        elif disease.lower() in ['apple scab', 'scab']:
            return self._forecast_apple_scab(
                weather_forecast, current_disease_pressure, inoculum_present
            )
        else:
            # Generic forecast
            return self._forecast_generic(
                disease, weather_forecast, current_disease_pressure, inoculum_present
            )
    
    def _forecast_late_blight(
        self,
        weather_forecast: List[WeatherData],
        current_pressure: str,
        inoculum_present: bool
    ) -> EpidemicForecast:
        """Late blight specific forecast"""
        
        # Calculate Smith periods
        smith_periods = self.calculate_smith_period(weather_forecast)
        
        # Accumulate severity
        total_severity = sum(p.severity_value for p in smith_periods)
        
        # Count favorable days
        favorable_days = 0
        infection_events = []
        
        for data in weather_forecast:
            favorable = (
                data.relative_humidity >= 85.0 and
                10.0 <= data.temperature_c <= 25.0 and
                data.leaf_wetness_hours >= 12.0
            )
            
            if favorable:
                favorable_days += 1
                
                # Determine infection severity
                if data.leaf_wetness_hours >= 24:
                    event = InfectionEvent.SEVERE_INFECTION
                elif data.leaf_wetness_hours >= 18:
                    event = InfectionEvent.MODERATE_INFECTION
                else:
                    event = InfectionEvent.LIGHT_INFECTION
                
                infection_events.append((data.timestamp, event))
        
        # Determine epidemic risk
        if not inoculum_present:
            risk = EpidemicRisk.NONE
        elif total_severity >= 20:
            risk = EpidemicRisk.CRITICAL
        elif total_severity >= 10:
            risk = EpidemicRisk.HIGH
        elif total_severity >= 5:
            risk = EpidemicRisk.MODERATE
        elif favorable_days >= 3:
            risk = EpidemicRisk.MODERATE
        elif favorable_days >= 1:
            risk = EpidemicRisk.LOW
        else:
            risk = EpidemicRisk.NONE
        
        # Spray recommendations
        spray_recommended = risk in [EpidemicRisk.HIGH, EpidemicRisk.CRITICAL]
        spray_timing = None
        
        if spray_recommended and infection_events:
            # Spray before first infection event
            spray_timing = infection_events[0][0] - timedelta(days=1)
        
        urgency = "critical" if risk == EpidemicRisk.CRITICAL else \
                 "high" if risk == EpidemicRisk.HIGH else \
                 "moderate" if risk == EpidemicRisk.MODERATE else "low"
        
        return EpidemicForecast(
            disease='Late Blight',
            forecast_date=weather_forecast[0].timestamp,
            forecast_days=len(weather_forecast),
            current_disease_pressure=current_pressure,
            inoculum_present=inoculum_present,
            infection_events=infection_events,
            epidemic_risk=risk,
            severity_value_total=total_severity,
            infection_periods=len(smith_periods),
            favorable_days=favorable_days,
            spray_recommended=spray_recommended,
            spray_timing=spray_timing,
            urgency=urgency,
            notes=f"Smith periods: {len(smith_periods)}, Severity: {total_severity:.1f}"
        )
    
    def _forecast_apple_scab(
        self,
        weather_forecast: List[WeatherData],
        current_pressure: str,
        inoculum_present: bool
    ) -> EpidemicForecast:
        """Apple scab specific forecast"""
        
        # Mills table infections
        infections = self.mills_table_forecast(weather_forecast)
        
        # Count infection events by severity
        severe_count = sum(1 for i in infections if i.severity == "severe")
        moderate_count = sum(1 for i in infections if i.severity == "moderate")
        light_count = sum(1 for i in infections if i.severity == "light")
        
        # Calculate risk
        if not inoculum_present:
            risk = EpidemicRisk.NONE
        elif severe_count >= 2:
            risk = EpidemicRisk.CRITICAL
        elif severe_count >= 1 or moderate_count >= 3:
            risk = EpidemicRisk.HIGH
        elif moderate_count >= 1 or light_count >= 2:
            risk = EpidemicRisk.MODERATE
        elif light_count >= 1:
            risk = EpidemicRisk.LOW
        else:
            risk = EpidemicRisk.NONE
        
        # Convert to infection events
        infection_events = []
        for inf in infections:
            if inf.severity == "severe":
                event = InfectionEvent.SEVERE_INFECTION
            elif inf.severity == "moderate":
                event = InfectionEvent.MODERATE_INFECTION
            else:
                event = InfectionEvent.LIGHT_INFECTION
            infection_events.append((inf.timestamp, event))
        
        spray_recommended = len(infections) > 0
        spray_timing = infections[0].timestamp - timedelta(hours=12) if infections else None
        
        return EpidemicForecast(
            disease='Apple Scab',
            forecast_date=weather_forecast[0].timestamp,
            forecast_days=len(weather_forecast),
            current_disease_pressure=current_pressure,
            inoculum_present=inoculum_present,
            infection_events=infection_events,
            epidemic_risk=risk,
            severity_value_total=float(severe_count * 3 + moderate_count * 2 + light_count),
            infection_periods=len(infections),
            favorable_days=len(infections),
            spray_recommended=spray_recommended,
            spray_timing=spray_timing,
            urgency="high" if severe_count > 0 else "moderate",
            notes=f"Mills infections: {len(infections)} ({severe_count} severe, {moderate_count} moderate)"
        )
    
    def _forecast_generic(
        self,
        disease: str,
        weather_forecast: List[WeatherData],
        current_pressure: str,
        inoculum_present: bool
    ) -> EpidemicForecast:
        """Generic disease forecast"""
        
        # Simple favorable conditions count
        favorable_days = 0
        infection_events = []
        
        for data in weather_forecast:
            # Generic favorable: 15-30°C, 80%+ RH, some wetness
            favorable = (
                15.0 <= data.temperature_c <= 30.0 and
                data.relative_humidity >= 80.0 and
                data.leaf_wetness_hours >= 6.0
            )
            
            if favorable:
                favorable_days += 1
                infection_events.append((
                    data.timestamp,
                    InfectionEvent.MODERATE_INFECTION
                ))
        
        # Risk assessment
        if not inoculum_present:
            risk = EpidemicRisk.NONE
        elif favorable_days >= 5:
            risk = EpidemicRisk.HIGH
        elif favorable_days >= 3:
            risk = EpidemicRisk.MODERATE
        elif favorable_days >= 1:
            risk = EpidemicRisk.LOW
        else:
            risk = EpidemicRisk.NONE
        
        return EpidemicForecast(
            disease=disease,
            forecast_date=weather_forecast[0].timestamp,
            forecast_days=len(weather_forecast),
            current_disease_pressure=current_pressure,
            inoculum_present=inoculum_present,
            infection_events=infection_events,
            epidemic_risk=risk,
            severity_value_total=float(favorable_days),
            infection_periods=favorable_days,
            favorable_days=favorable_days,
            spray_recommended=favorable_days >= 3,
            urgency="moderate" if favorable_days >= 3 else "low"
        )
    
    def model_disease_spread(
        self,
        disease: str,
        initial_incidence: float,
        days_elapsed: int,
        weather_favorable: bool = True,
        treatment_applied: bool = False
    ) -> DiseaseSpreadModel:
        """
        Model disease spread over time
        
        Exponential growth for epidemic diseases
        """
        # Disease-specific doubling times
        doubling_times = {
            'late_blight': 7,  # 7-10 days (extremely fast)
            'downy_mildew': 10,
            'powdery_mildew': 12,
            'early_blight': 14,
            'bacterial_spot': 10,
            'rust': 10,
            'scab': 14
        }
        
        doubling_time = doubling_times.get(disease.lower().replace(' ', '_'), 14)
        
        if not weather_favorable:
            doubling_time *= 2  # Slow spread
        
        # Calculate current incidence (exponential growth)
        growth_rate = math.log(2) / doubling_time
        current_incidence = initial_incidence * math.exp(growth_rate * days_elapsed)
        current_incidence = min(current_incidence, 100.0)  # Cap at 100%
        
        # Project future incidence
        projected_7day = min(current_incidence * math.exp(growth_rate * 7), 100.0)
        projected_14day = min(current_incidence * math.exp(growth_rate * 14), 100.0)
        projected_21day = min(current_incidence * math.exp(growth_rate * 21), 100.0)
        
        # With treatment (70-90% control)
        if treatment_applied:
            control_efficacy = 0.80
            with_treatment_7day = current_incidence + (projected_7day - current_incidence) * (1 - control_efficacy)
            with_treatment_14day = current_incidence + (projected_14day - current_incidence) * (1 - control_efficacy)
        else:
            with_treatment_7day = projected_7day
            with_treatment_14day = projected_14day
        
        # Epidemic status
        if current_incidence >= 50:
            status = "explosive"
        elif current_incidence >= 20:
            status = "increasing"
        else:
            status = "stable"
        
        return DiseaseSpreadModel(
            disease=disease,
            initial_incidence=initial_incidence,
            days_elapsed=days_elapsed,
            current_incidence=current_incidence,
            doubling_time_days=doubling_time,
            projected_7day=projected_7day,
            projected_14day=projected_14day,
            projected_21day=projected_21day,
            with_treatment_7day=with_treatment_7day,
            with_treatment_14day=with_treatment_14day,
            epidemic_status=status,
            notes=f"Doubling time: {doubling_time} days. Growth rate: {growth_rate:.3f}/day"
        )


def main():
    """Example usage"""
    model = DiseaseForecastingModel()
    
    print("=== AgroPulse Disease Forecasting Models ===")
    
    print("\n🌡️ FORECASTING SYSTEMS:")
    print("\n1. LATE BLIGHT:")
    print("   - Smith periods (90%+ RH, 12+ hours, 10-25°C)")
    print("   - BlightCast severity accumulation")
    print("   - Doubling time: 7-10 days (EXPLOSIVE)")
    
    print("\n2. APPLE SCAB:")
    print("   - Mills table (temp + wetness = infection)")
    print("   - Ascospore maturation models")
    print("   - Hourly infection period tracking")
    
    print("\n3. EPIDEMIC SPREAD:")
    print("   - Exponential growth modeling")
    print("   - Treatment impact simulation")
    print("   - Doubling time calculations")
    
    # Simulate late blight forecast
    print("\n📊 LATE BLIGHT EPIDEMIC FORECAST:")
    
    # Create favorable weather conditions
    forecast_weather = []
    base_time = datetime.now()
    
    for day in range(7):
        # Simulated favorable conditions (days 2-4)
        if 2 <= day <= 4:
            temp = 18.0
            rh = 95.0
            wetness = 15.0
            rain = 12.0
        else:
            temp = 22.0
            rh = 70.0
            wetness = 2.0
            rain = 0.0
        
        forecast_weather.append(WeatherData(
            timestamp=base_time + timedelta(days=day),
            temperature_c=temp,
            relative_humidity=rh,
            leaf_wetness_hours=wetness,
            rainfall_mm=rain
        ))
    
    forecast = model.forecast_epidemic('Late Blight', forecast_weather, 'low', True)
    
    print(f"\nForecast period: {forecast.forecast_days} days")
    print(f"Epidemic risk: {forecast.epidemic_risk.value.upper()}")
    print(f"Favorable days: {forecast.favorable_days}")
    print(f"Infection periods: {forecast.infection_periods}")
    print(f"Severity total: {forecast.severity_value_total:.1f}")
    print(f"Spray recommended: {'YES' if forecast.spray_recommended else 'NO'}")
    print(f"Urgency: {forecast.urgency}")
    
    # Epidemic spread modeling
    print("\n📈 EPIDEMIC SPREAD MODEL:")
    spread = model.model_disease_spread('Late Blight', 5.0, 7, True, False)
    
    print(f"\nDisease: {spread.disease}")
    print(f"Initial incidence: {spread.initial_incidence}%")
    print(f"Days elapsed: {spread.days_elapsed}")
    print(f"Current incidence: {spread.current_incidence:.1f}%")
    print(f"Doubling time: {spread.doubling_time_days} days")
    print(f"\nProjections (untreated):")
    print(f"   7 days: {spread.projected_7day:.1f}%")
    print(f"   14 days: {spread.projected_14day:.1f}%")
    print(f"   21 days: {spread.projected_21day:.1f}%")
    print(f"\nWith treatment:")
    print(f"   7 days: {spread.with_treatment_7day:.1f}%")
    print(f"   14 days: {spread.with_treatment_14day:.1f}%")
    print(f"\n⚠️ Status: {spread.epidemic_status.upper()}")
    
    print("\n✅ SYSTEM STATUS: Forecasting models operational")


if __name__ == "__main__":
    main()
