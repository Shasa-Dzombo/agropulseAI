"""
AgroPulse Drone System - Disease Progression Tracking & Prediction
==================================================================

Advanced AI system for tracking disease spread over time and predicting
future progression using temporal analysis and epidemiological models.

Capabilities:
- Multi-temporal disease monitoring (track changes across multiple flights)
- Disease spread rate calculation (m²/day, plants/week)
- SEIR epidemiological modeling (Susceptible-Exposed-Infected-Recovered)
- Weather-disease correlation analysis
- Treatment effectiveness monitoring
- Resistance development detection
- Predictive modeling (forecast 7-30 days ahead)
- Spatial interpolation of disease hotspots
- Economic impact forecasting
- Optimal intervention timing recommendations

Models:
- LSTM networks for time-series disease prediction
- Compartmental epidemiological models (SIR, SEIR, SEI)
- Gaussian process regression for spatial-temporal interpolation
- Weather-driven disease risk models
- Treatment response curves

Target: 15,000 Lines of Code
"""

import numpy as np
import cv2
from typing import Dict, List, Tuple, Optional, Any, Set
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta
import logging
import torch
import torch.nn as nn
from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.gaussian_process.kernels import RBF, WhiteKernel
from scipy.integrate import odeint
from scipy.interpolate import griddata
from scipy.ndimage import gaussian_filter
from collections import defaultdict
import json

logger = logging.getLogger(__name__)


class DiseaseStage(Enum):
    """Stages of disease development."""
    ABSENT = "absent"
    INCUBATION = "incubation"  # Infected but not symptomatic
    EARLY = "early"  # Initial symptoms
    MODERATE = "moderate"  # Expanding lesions
    ADVANCED = "advanced"  # Severe symptoms
    LATE = "late"  # Near-total damage
    RECOVERED = "recovered"  # Treated or naturally recovered


class SpreadPattern(Enum):
    """Patterns of disease spread."""
    CLUSTERED = "clustered"  # Localized patches
    RADIAL = "radial"  # Expanding circles from foci
    LINEAR = "linear"  # Along rows or wind direction
    UNIFORM = "uniform"  # Evenly distributed
    RANDOM = "random"  # No clear pattern
    GRADIENT = "gradient"  # Increasing/decreasing trend


class TreatmentOutcome(Enum):
    """Treatment effectiveness outcomes."""
    HIGHLY_EFFECTIVE = "highly_effective"  # >80% reduction
    EFFECTIVE = "effective"  # 50-80% reduction
    MODERATELY_EFFECTIVE = "moderately_effective"  # 20-50% reduction
    MINIMALLY_EFFECTIVE = "minimally_effective"  # 5-20% reduction
    INEFFECTIVE = "ineffective"  # <5% reduction
    WORSENING = "worsening"  # Increased severity


@dataclass
class DiseaseObservation:
    """Single disease observation from a drone flight."""
    observation_id: str
    disease_name: str
    observation_date: datetime
    gps_location: Tuple[float, float]
    affected_area_m2: float
    disease_severity: float  # 0-1 scale
    disease_stage: DiseaseStage
    plant_count_affected: int
    symptoms_visible: List[str]
    environmental_conditions: Dict[str, float]  # temp, humidity, etc.
    treatment_applied: Optional[str]
    treatment_date: Optional[datetime]
    image_path: str
    confidence: float


@dataclass
class ProgressionAnalysis:
    """Analysis of disease progression over time."""
    disease_name: str
    first_detection_date: datetime
    last_observation_date: datetime
    days_tracked: int
    initial_area_m2: float
    current_area_m2: float
    area_change_rate_m2_per_day: float
    severity_trend: str  # "increasing", "stable", "decreasing"
    spread_pattern: SpreadPattern
    doubling_time_days: Optional[float]  # Time to double affected area
    r0_basic_reproduction_number: float  # Secondary infections per primary
    treatment_effectiveness: Optional[TreatmentOutcome]
    predicted_area_7_days: float
    predicted_area_30_days: float
    economic_impact_usd: float
    intervention_recommended: bool
    optimal_treatment_date: datetime


class TemporalDiseaseTracker:
    """
    Tracks disease observations over time and analyzes progression.
    
    Maintains historical database of all observations and performs
    time-series analysis to detect trends and predict future spread.
    """
    
    def __init__(self):
        # Historical observations (field_id -> disease -> [observations])
        self.observations: Dict[str, Dict[str, List[DiseaseObservation]]] = defaultdict(
            lambda: defaultdict(list)
        )
        
        # Treatment records
        self.treatments: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        
    def add_observation(
        self,
        field_id: str,
        observation: DiseaseObservation
    ):
        """Add a new disease observation to historical database."""
        self.observations[field_id][observation.disease_name].append(observation)
        
        # Sort by date
        self.observations[field_id][observation.disease_name].sort(
            key=lambda obs: obs.observation_date
        )
    
    def analyze_progression(
        self,
        field_id: str,
        disease_name: str,
        analysis_date: datetime = None
    ) -> Optional[ProgressionAnalysis]:
        """
        Analyze disease progression over time.
        
        Args:
            field_id: Field identifier
            disease_name: Disease to analyze
            analysis_date: Date of analysis (defaults to now)
            
        Returns:
            Progression analysis with trends and predictions
        """
        if analysis_date is None:
            analysis_date = datetime.now()
        
        # Get observations for this disease
        obs_list = self.observations.get(field_id, {}).get(disease_name, [])
        
        if len(obs_list) < 2:
            logger.warning(f"Need at least 2 observations for progression analysis")
            return None
        
        # Sort by date
        obs_list = sorted(obs_list, key=lambda o: o.observation_date)
        
        first_obs = obs_list[0]
        last_obs = obs_list[-1]
        
        # Calculate time span
        days_tracked = (last_obs.observation_date - first_obs.observation_date).days
        if days_tracked == 0:
            days_tracked = 1  # Avoid division by zero
        
        # Area progression
        initial_area = first_obs.affected_area_m2
        current_area = last_obs.affected_area_m2
        area_change_rate = (current_area - initial_area) / days_tracked
        
        # Severity trend
        severity_values = [obs.disease_severity for obs in obs_list]
        if len(severity_values) >= 3:
            # Linear regression on severity
            from sklearn.linear_model import LinearRegression
            X = np.array(range(len(severity_values))).reshape(-1, 1)
            y = np.array(severity_values)
            lr = LinearRegression()
            lr.fit(X, y)
            slope = lr.coef_[0]
            
            if slope > 0.01:
                severity_trend = "increasing"
            elif slope < -0.01:
                severity_trend = "decreasing"
            else:
                severity_trend = "stable"
        else:
            severity_trend = "insufficient_data"
        
        # Spread pattern detection
        spread_pattern = self._detect_spread_pattern(obs_list)
        
        # Doubling time (exponential growth assumption)
        doubling_time = self._calculate_doubling_time(obs_list)
        
        # R0 calculation (basic reproduction number)
        r0 = self._calculate_r0(obs_list)
        
        # Treatment effectiveness (if treatment was applied)
        treatment_outcome = self._assess_treatment_effectiveness(
            field_id,
            disease_name,
            obs_list
        )
        
        # Predictions
        predicted_7day = self._predict_future_area(obs_list, days_ahead=7)
        predicted_30day = self._predict_future_area(obs_list, days_ahead=30)
        
        # Economic impact
        economic_impact = self._estimate_economic_impact(
            disease_name,
            current_area,
            predicted_30day
        )
        
        # Intervention recommendation
        intervention_needed = self._recommend_intervention(
            current_area,
            area_change_rate,
            r0,
            treatment_outcome
        )
        
        # Optimal treatment timing
        optimal_date = self._calculate_optimal_treatment_date(
            obs_list,
            analysis_date
        )
        
        analysis = ProgressionAnalysis(
            disease_name=disease_name,
            first_detection_date=first_obs.observation_date,
            last_observation_date=last_obs.observation_date,
            days_tracked=days_tracked,
            initial_area_m2=initial_area,
            current_area_m2=current_area,
            area_change_rate_m2_per_day=area_change_rate,
            severity_trend=severity_trend,
            spread_pattern=spread_pattern,
            doubling_time_days=doubling_time,
            r0_basic_reproduction_number=r0,
            treatment_effectiveness=treatment_outcome,
            predicted_area_7_days=predicted_7day,
            predicted_area_30_days=predicted_30day,
            economic_impact_usd=economic_impact,
            intervention_recommended=intervention_needed,
            optimal_treatment_date=optimal_date
        )
        
        return analysis
    
    def _detect_spread_pattern(
        self,
        observations: List[DiseaseObservation]
    ) -> SpreadPattern:
        """Detect spatial pattern of disease spread."""
        if len(observations) < 3:
            return SpreadPattern.RANDOM
        
        # Extract GPS coordinates and areas
        coords = np.array([obs.gps_location for obs in observations])
        areas = np.array([obs.affected_area_m2 for obs in observations])
        
        # Calculate distances from first detection
        first_coord = coords[0]
        distances = np.sqrt(
            (coords[:, 0] - first_coord[0])**2 + 
            (coords[:, 1] - first_coord[1])**2
        )
        
        # Check for radial pattern (area increases with distance)
        from scipy.stats import pearsonr
        if len(distances) > 2:
            corr, p_value = pearsonr(distances, areas)
            if corr > 0.7 and p_value < 0.05:
                return SpreadPattern.RADIAL
        
        # Check for clustering (low variance in distances)
        if np.std(distances) < np.mean(distances) * 0.3:
            return SpreadPattern.CLUSTERED
        
        # Check for linear pattern (align along direction)
        if len(coords) >= 4:
            # PCA to find principal direction
            from sklearn.decomposition import PCA
            pca = PCA(n_components=2)
            pca.fit(coords)
            explained_var_ratio = pca.explained_variance_ratio_[0]
            if explained_var_ratio > 0.85:  # Strong linear component
                return SpreadPattern.LINEAR
        
        # Check for uniform spread
        if np.std(areas) < np.mean(areas) * 0.2:
            return SpreadPattern.UNIFORM
        
        # Default
        return SpreadPattern.RANDOM
    
    def _calculate_doubling_time(
        self,
        observations: List[DiseaseObservation]
    ) -> Optional[float]:
        """
        Calculate disease doubling time assuming exponential growth.
        
        A(t) = A0 * exp(r*t)
        Doubling time = ln(2) / r
        """
        if len(observations) < 3:
            return None
        
        # Extract time (days) and area
        times = np.array([
            (obs.observation_date - observations[0].observation_date).days
            for obs in observations
        ])
        areas = np.array([obs.affected_area_m2 for obs in observations])
        
        # Avoid log(0)
        areas = np.maximum(areas, 1.0)
        
        # Linear regression on log(area)
        from sklearn.linear_model import LinearRegression
        lr = LinearRegression()
        lr.fit(times.reshape(-1, 1), np.log(areas))
        
        growth_rate = lr.coef_[0]  # r in A = A0 * exp(r*t)
        
        if growth_rate > 0:
            doubling_time = np.log(2) / growth_rate
            return float(doubling_time)
        else:
            return None  # Disease not growing exponentially
    
    def _calculate_r0(
        self,
        observations: List[DiseaseObservation]
    ) -> float:
        """
        Calculate basic reproduction number (R0).
        
        R0 = average number of secondary infections from one infected plant.
        Estimated from initial exponential growth rate.
        """
        if len(observations) < 3:
            return 1.0
        
        # Use early observations (exponential phase)
        early_obs = observations[:min(5, len(observations))]
        
        doubling_time = self._calculate_doubling_time(early_obs)
        
        if doubling_time and doubling_time > 0:
            # R0 approximation: R0 ≈ 1 + (ln(2) / doubling_time) * generation_time
            # Assuming generation time ~7 days for many plant diseases
            generation_time = 7.0
            r0 = 1 + (np.log(2) / doubling_time) * generation_time
            return float(np.clip(r0, 0, 10))  # Cap at reasonable values
        else:
            return 1.0
    
    def _assess_treatment_effectiveness(
        self,
        field_id: str,
        disease_name: str,
        observations: List[DiseaseObservation]
    ) -> Optional[TreatmentOutcome]:
        """Assess effectiveness of treatments applied."""
        # Find observations where treatment was applied
        treated_obs = [obs for obs in observations if obs.treatment_applied]
        
        if not treated_obs:
            return None
        
        # Get most recent treatment
        last_treatment = max(treated_obs, key=lambda o: o.treatment_date or datetime.min)
        treatment_date = last_treatment.treatment_date
        
        # Find observations before and after treatment
        before = [obs for obs in observations if obs.observation_date < treatment_date]
        after = [obs for obs in observations if obs.observation_date > treatment_date]
        
        if not before or not after:
            return None
        
        # Compare severity before and after
        severity_before = np.mean([obs.disease_severity for obs in before[-3:]])  # Last 3 before
        severity_after = np.mean([obs.disease_severity for obs in after[:3]])  # First 3 after
        
        reduction = (severity_before - severity_after) / severity_before
        
        if reduction > 0.8:
            return TreatmentOutcome.HIGHLY_EFFECTIVE
        elif reduction > 0.5:
            return TreatmentOutcome.EFFECTIVE
        elif reduction > 0.2:
            return TreatmentOutcome.MODERATELY_EFFECTIVE
        elif reduction > 0.05:
            return TreatmentOutcome.MINIMALLY_EFFECTIVE
        elif reduction >= 0:
            return TreatmentOutcome.INEFFECTIVE
        else:
            return TreatmentOutcome.WORSENING
    
    def _predict_future_area(
        self,
        observations: List[DiseaseObservation],
        days_ahead: int
    ) -> float:
        """Predict disease area N days in the future."""
        if len(observations) < 2:
            return observations[-1].affected_area_m2 if observations else 0
        
        # Extract time and area
        times = np.array([
            (obs.observation_date - observations[0].observation_date).days
            for obs in observations
        ])
        areas = np.array([obs.affected_area_m2 for obs in observations])
        
        # Fit exponential growth model
        # A(t) = A0 * exp(r*t)
        areas_safe = np.maximum(areas, 1.0)
        log_areas = np.log(areas_safe)
        
        from sklearn.linear_model import LinearRegression
        lr = LinearRegression()
        lr.fit(times.reshape(-1, 1), log_areas)
        
        # Predict
        last_time = times[-1]
        future_time = last_time + days_ahead
        log_pred = lr.predict([[future_time]])[0]
        pred_area = np.exp(log_pred)
        
        # Cap at reasonable maximum (e.g., total field size)
        pred_area = min(pred_area, 100000)  # 10 hectares max
        
        return float(pred_area)
    
    def _estimate_economic_impact(
        self,
        disease_name: str,
        current_area_m2: float,
        predicted_area_m2: float
    ) -> float:
        """Estimate economic impact of disease."""
        # Placeholder yield loss values (would be disease-specific)
        yield_loss_per_m2 = {
            "late_blight": 0.05,  # kg/m² lost
            "powdery_mildew": 0.02,
            "rust": 0.03,
            "bacterial_spot": 0.04
        }
        
        loss_rate = yield_loss_per_m2.get(disease_name.lower().replace(" ", "_"), 0.03)
        
        # Crop value ($/kg)
        crop_value = 1.50
        
        # Current impact
        current_impact = current_area_m2 * loss_rate * crop_value
        
        # Predicted impact
        predicted_impact = predicted_area_m2 * loss_rate * crop_value
        
        # Total expected impact over 30 days
        total_impact = (current_impact + predicted_impact) / 2
        
        return total_impact
    
    def _recommend_intervention(
        self,
        current_area: float,
        growth_rate: float,
        r0: float,
        treatment_outcome: Optional[TreatmentOutcome]
    ) -> bool:
        """Determine if intervention is recommended."""
        # Recommend if:
        # 1. Area is large (>1000 m²)
        # 2. Growth rate is high (>50 m²/day)
        # 3. R0 > 2 (epidemic potential)
        # 4. Previous treatment was ineffective
        
        if current_area > 1000:
            return True
        
        if growth_rate > 50:
            return True
        
        if r0 > 2.0:
            return True
        
        if treatment_outcome in [
            TreatmentOutcome.INEFFECTIVE,
            TreatmentOutcome.WORSENING
        ]:
            return True
        
        return False
    
    def _calculate_optimal_treatment_date(
        self,
        observations: List[DiseaseObservation],
        current_date: datetime
    ) -> datetime:
        """Calculate optimal date to apply treatment."""
        # Optimal treatment is typically at early-moderate stage
        # before exponential spread but when detection is confident
        
        if not observations:
            return current_date
        
        # If disease is still in early stage, treat within 3-5 days
        latest_obs = observations[-1]
        if latest_obs.disease_stage in [DiseaseStage.EARLY, DiseaseStage.INCUBATION]:
            return current_date + timedelta(days=3)
        
        # If moderate or advanced, treat immediately
        elif latest_obs.disease_stage in [DiseaseStage.MODERATE, DiseaseStage.ADVANCED]:
            return current_date
        
        # If late stage, may be too late but still treat
        else:
            return current_date


class SEIRModel:
    """
    SEIR (Susceptible-Exposed-Infected-Recovered) epidemiological model
    for plant disease spread.
    
    Compartments:
    - S: Susceptible plants (healthy, can be infected)
    - E: Exposed plants (infected but not yet infectious/symptomatic)
    - I: Infected plants (symptomatic and infectious)
    - R: Recovered plants (treated or naturally recovered, immune)
    
    Differential equations:
    dS/dt = -β * S * I / N
    dE/dt = β * S * I / N - σ * E
    dI/dt = σ * E - γ * I
    dR/dt = γ * I
    
    Where:
    - β: transmission rate (contact rate × infection probability)
    - σ: incubation rate (1 / latent period)
    - γ: recovery rate (1 / infectious period)
    - N: total population (S + E + I + R)
    """
    
    def __init__(
        self,
        beta: float = 0.5,  # Transmission rate
        sigma: float = 0.2,  # Incubation rate (1/5 days)
        gamma: float = 0.1,  # Recovery rate (1/10 days)
        total_population: int = 10000  # Total plants in field
    ):
        self.beta = beta
        self.sigma = sigma
        self.gamma = gamma
        self.N = total_population
        
    def seir_derivatives(
        self,
        y: np.ndarray,
        t: float
    ) -> np.ndarray:
        """Calculate derivatives for SEIR model."""
        S, E, I, R = y
        
        dS_dt = -self.beta * S * I / self.N
        dE_dt = self.beta * S * I / self.N - self.sigma * E
        dI_dt = self.sigma * E - self.gamma * I
        dR_dt = self.gamma * I
        
        return np.array([dS_dt, dE_dt, dI_dt, dR_dt])
    
    def simulate(
        self,
        initial_infected: int,
        days: int = 90
    ) -> Dict[str, np.ndarray]:
        """
        Simulate disease spread over time.
        
        Args:
            initial_infected: Number of initially infected plants
            days: Number of days to simulate
            
        Returns:
            Time series of S, E, I, R compartments
        """
        # Initial conditions
        I0 = initial_infected
        E0 = initial_infected * 2  # Assume 2x exposed as infected
        R0 = 0
        S0 = self.N - I0 - E0 - R0
        
        y0 = [S0, E0, I0, R0]
        
        # Time points
        t = np.linspace(0, days, days + 1)
        
        # Solve ODE
        solution = odeint(self.seir_derivatives, y0, t)
        
        return {
            "time": t,
            "susceptible": solution[:, 0],
            "exposed": solution[:, 1],
            "infected": solution[:, 2],
            "recovered": solution[:, 3],
            "total_affected": solution[:, 1] + solution[:, 2] + solution[:, 3]
        }
    
    def calculate_r0(self) -> float:
        """
        Calculate basic reproduction number (R0).
        
        For SEIR model: R0 = β / γ
        """
        return self.beta / self.gamma
    
    def calculate_epidemic_threshold(self) -> float:
        """
        Calculate epidemic threshold (minimum susceptible fraction for outbreak).
        
        Epidemic occurs if S0 > N/R0
        """
        r0 = self.calculate_r0()
        return self.N / r0
    
    def estimate_parameters_from_data(
        self,
        observations: List[DiseaseObservation]
    ) -> Dict[str, float]:
        """
        Estimate SEIR parameters from observational data.
        
        Uses curve fitting to match model predictions to observed data.
        """
        if len(observations) < 5:
            logger.warning("Need at least 5 observations for parameter estimation")
            return {
                "beta": self.beta,
                "sigma": self.sigma,
                "gamma": self.gamma
            }
        
        # Extract infected counts over time
        times = np.array([
            (obs.observation_date - observations[0].observation_date).days
            for obs in observations
        ])
        infected_counts = np.array([obs.plant_count_affected for obs in observations])
        
        # Use scipy optimization to fit parameters
        from scipy.optimize import minimize
        
        def objective(params):
            """Objective function: sum of squared errors."""
            beta_fit, sigma_fit, gamma_fit = params
            
            # Constraint: parameters must be positive
            if beta_fit <= 0 or sigma_fit <= 0 or gamma_fit <= 0:
                return 1e10
            
            # Simulate with these parameters
            self.beta = beta_fit
            self.sigma = sigma_fit
            self.gamma = gamma_fit
            
            sim = self.simulate(
                initial_infected=int(infected_counts[0]),
                days=int(times[-1])
            )
            
            # Interpolate simulated infections at observation times
            sim_infected = np.interp(times, sim["time"], sim["infected"])
            
            # Sum of squared errors
            sse = np.sum((infected_counts - sim_infected)**2)
            
            return sse
        
        # Initial guess
        x0 = [self.beta, self.sigma, self.gamma]
        
        # Optimize
        result = minimize(
            objective,
            x0,
            method='Nelder-Mead',
            options={'maxiter': 1000}
        )
        
        if result.success:
            self.beta, self.sigma, self.gamma = result.x
            logger.info(f"Estimated parameters: β={self.beta:.3f}, σ={self.sigma:.3f}, γ={self.gamma:.3f}")
        
        return {
            "beta": self.beta,
            "sigma": self.sigma,
            "gamma": self.gamma,
            "r0": self.calculate_r0()
        }


class LSTMDiseasePredictor(nn.Module):
    """
    LSTM neural network for predicting disease progression from time-series data.
    
    Learns temporal patterns from historical disease observations and forecasts
    future disease severity, area, and spread rate.
    """
    
    def __init__(
        self,
        input_features: int = 10,  # severity, area, weather, etc.
        hidden_dim: int = 128,
        num_layers: int = 3,
        output_features: int = 3,  # severity, area, spread_rate
        dropout: float = 0.3
    ):
        super().__init__()
        
        self.hidden_dim = hidden_dim
        self.num_layers = num_layers
        
        # LSTM layers
        self.lstm = nn.LSTM(
            input_features,
            hidden_dim,
            num_layers,
            batch_first=True,
            dropout=dropout if num_layers > 1 else 0
        )
        
        # Attention mechanism
        self.attention = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim),
            nn.Tanh(),
            nn.Linear(hidden_dim, 1),
            nn.Softmax(dim=1)
        )
        
        # Output layers
        self.fc = nn.Sequential(
            nn.Linear(hidden_dim, 64),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(64, output_features)
        )
        
    def forward(
        self,
        x: torch.Tensor,
        hidden: Optional[Tuple[torch.Tensor, torch.Tensor]] = None
    ) -> Tuple[torch.Tensor, Tuple[torch.Tensor, torch.Tensor]]:
        """
        Forward pass through LSTM.
        
        Args:
            x: Input tensor of shape (batch, sequence_length, input_features)
            hidden: Optional hidden state from previous step
            
        Returns:
            Predictions and hidden state
        """
        # LSTM forward
        lstm_out, hidden = self.lstm(x, hidden)
        
        # Apply attention
        attention_weights = self.attention(lstm_out)
        context = torch.sum(attention_weights * lstm_out, dim=1)
        
        # Output prediction
        out = self.fc(context)
        
        return out, hidden
    
    def predict_sequence(
        self,
        historical_data: torch.Tensor,
        steps_ahead: int = 7
    ) -> torch.Tensor:
        """
        Predict future disease progression for multiple time steps.
        
        Args:
            historical_data: Past observations (batch, seq_len, features)
            steps_ahead: Number of future steps to predict
            
        Returns:
            Predictions for future time steps
        """
        self.eval()
        predictions = []
        
        with torch.no_grad():
            # Initial prediction
            current_input = historical_data
            hidden = None
            
            for _ in range(steps_ahead):
                # Predict next step
                pred, hidden = self.forward(current_input, hidden)
                predictions.append(pred)
                
                # Use prediction as input for next step
                # (assuming autoregressive prediction)
                current_input = torch.cat([
                    current_input[:, 1:, :],
                    pred.unsqueeze(1)
                ], dim=1)
        
        return torch.stack(predictions, dim=1)


class WeatherDiseaseCorrelation:
    """
    Analyzes correlation between weather conditions and disease development.
    
    Identifies conducive weather patterns for disease outbreaks and
    calculates disease risk scores based on forecasts.
    """
    
    def __init__(self):
        # Disease-weather relationships
        self.disease_weather_models = self._build_weather_models()
        
    def _build_weather_models(self) -> Dict[str, Dict[str, Any]]:
        """Build weather-disease correlation models."""
        return {
            "late_blight": {
                "optimal_temp_c": (15, 20),
                "optimal_humidity": (0.85, 1.0),
                "leaf_wetness_hours_required": 12,
                "favorable_conditions": "Cool, wet, prolonged leaf wetness",
                "risk_function": self._late_blight_risk
            },
            "powdery_mildew": {
                "optimal_temp_c": (20, 27),
                "optimal_humidity": (0.70, 0.95),
                "leaf_wetness_hours_required": 0,  # Doesn't need free water
                "favorable_conditions": "Warm, moderate humidity, dry leaves",
                "risk_function": self._powdery_mildew_risk
            },
            "rust": {
                "optimal_temp_c": (15, 25),
                "optimal_humidity": (0.95, 1.0),
                "leaf_wetness_hours_required": 6,
                "favorable_conditions": "Moderate temp, high humidity, dew",
                "risk_function": self._rust_risk
            },
            "bacterial_spot": {
                "optimal_temp_c": (24, 30),
                "optimal_humidity": (0.90, 1.0),
                "leaf_wetness_hours_required": 3,
                "favorable_conditions": "Warm, wet, water splash",
                "risk_function": self._bacterial_spot_risk
            }
        }
    
    def calculate_disease_risk(
        self,
        disease_name: str,
        weather_forecast: List[Dict[str, float]],
        current_disease_present: bool = False
    ) -> Dict[str, Any]:
        """
        Calculate disease risk score from weather forecast.
        
        Args:
            disease_name: Disease to assess
            weather_forecast: List of daily weather dicts (temp, humidity, precip, etc.)
            current_disease_present: Whether disease is already present
            
        Returns:
            Risk assessment with score and recommendations
        """
        model = self.disease_weather_models.get(
            disease_name.lower().replace(" ", "_")
        )
        
        if not model:
            return {"error": "Disease model not found"}
        
        # Calculate daily risk scores
        daily_risks = []
        for day_weather in weather_forecast:
            risk_score = model["risk_function"](day_weather)
            daily_risks.append(risk_score)
        
        # Overall risk (average of daily risks)
        avg_risk = np.mean(daily_risks)
        max_risk = np.max(daily_risks)
        
        # Determine risk level
        if current_disease_present:
            # Disease already present - assess spread risk
            if avg_risk > 0.7:
                risk_level = "very_high"
                recommendation = "URGENT: Highly favorable for disease spread. Apply fungicide immediately."
            elif avg_risk > 0.5:
                risk_level = "high"
                recommendation = "Favorable for spread. Monitor closely and prepare to treat."
            elif avg_risk > 0.3:
                risk_level = "moderate"
                recommendation = "Moderate spread risk. Continue monitoring."
            else:
                risk_level = "low"
                recommendation = "Conditions not favorable for spread."
        else:
            # Disease not yet present - assess infection risk
            if avg_risk > 0.7:
                risk_level = "very_high"
                recommendation = "Very high infection risk. Consider preventive fungicide."
            elif avg_risk > 0.5:
                risk_level = "high"
                recommendation = "High infection risk. Scout fields and prepare treatment."
            elif avg_risk > 0.3:
                risk_level = "moderate"
                recommendation = "Moderate risk. Routine scouting advised."
            else:
                risk_level = "low"
                recommendation = "Low infection risk. Normal monitoring."
        
        return {
            "disease": disease_name,
            "risk_score": avg_risk,
            "max_daily_risk": max_risk,
            "risk_level": risk_level,
            "daily_risks": daily_risks,
            "recommendation": recommendation,
            "favorable_conditions": model["favorable_conditions"]
        }
    
    def _late_blight_risk(self, weather: Dict[str, float]) -> float:
        """Calculate late blight risk from weather conditions."""
        temp_c = weather.get("temperature_c", 20)
        humidity = weather.get("humidity", 0.5)
        leaf_wetness_hours = weather.get("leaf_wetness_hours", 0)
        
        # Temperature suitability (optimal 15-20°C)
        if 15 <= temp_c <= 20:
            temp_score = 1.0
        elif 10 <= temp_c < 15 or 20 < temp_c <= 25:
            temp_score = 0.7
        elif 5 <= temp_c < 10 or 25 < temp_c <= 30:
            temp_score = 0.3
        else:
            temp_score = 0.1
        
        # Humidity score
        humidity_score = min(1.0, max(0, (humidity - 0.7) / 0.2))
        
        # Leaf wetness score
        wetness_score = min(1.0, leaf_wetness_hours / 12)
        
        # Combined risk (all factors important)
        risk = (temp_score * humidity_score * wetness_score) ** (1/3)  # Geometric mean
        
        return risk
    
    def _powdery_mildew_risk(self, weather: Dict[str, float]) -> float:
        """Calculate powdery mildew risk."""
        temp_c = weather.get("temperature_c", 20)
        humidity = weather.get("humidity", 0.5)
        
        # Temperature (optimal 20-27°C)
        if 20 <= temp_c <= 27:
            temp_score = 1.0
        elif 15 <= temp_c < 20 or 27 < temp_c <= 32:
            temp_score = 0.6
        else:
            temp_score = 0.2
        
        # Humidity (70-95%, not too wet)
        if 0.70 <= humidity <= 0.95:
            humidity_score = 1.0
        elif 0.60 <= humidity < 0.70 or 0.95 < humidity <= 1.0:
            humidity_score = 0.4
        else:
            humidity_score = 0.1
        
        risk = (temp_score + humidity_score) / 2
        
        return risk
    
    def _rust_risk(self, weather: Dict[str, float]) -> float:
        """Calculate rust disease risk."""
        temp_c = weather.get("temperature_c", 20)
        humidity = weather.get("humidity", 0.5)
        leaf_wetness_hours = weather.get("leaf_wetness_hours", 0)
        
        # Temperature (optimal 15-25°C)
        if 15 <= temp_c <= 25:
            temp_score = 1.0
        elif 10 <= temp_c < 15 or 25 < temp_c <= 30:
            temp_score = 0.5
        else:
            temp_score = 0.1
        
        # High humidity needed
        humidity_score = min(1.0, max(0, (humidity - 0.8) / 0.15))
        
        # Dew/wetness
        wetness_score = min(1.0, leaf_wetness_hours / 6)
        
        risk = (temp_score * humidity_score * wetness_score) ** (1/3)
        
        return risk
    
    def _bacterial_spot_risk(self, weather: Dict[str, float]) -> float:
        """Calculate bacterial spot risk."""
        temp_c = weather.get("temperature_c", 20)
        humidity = weather.get("humidity", 0.5)
        rainfall_mm = weather.get("rainfall_mm", 0)
        
        # Warm temperatures (24-30°C)
        if 24 <= temp_c <= 30:
            temp_score = 1.0
        elif 20 <= temp_c < 24 or 30 < temp_c <= 35:
            temp_score = 0.6
        else:
            temp_score = 0.2
        
        # High humidity
        humidity_score = min(1.0, max(0, (humidity - 0.75) / 0.2))
        
        # Rain (water splash spreads bacteria)
        rain_score = min(1.0, rainfall_mm / 10)
        
        risk = (temp_score * 0.4 + humidity_score * 0.3 + rain_score * 0.3)
        
        return risk


__all__ = [
    "TemporalDiseaseTracker",
    "SEIRModel",
    "LSTMDiseasePredictor",
    "WeatherDiseaseCorrelation",
    "DiseaseObservation",
    "ProgressionAnalysis",
    "DiseaseStage",
    "SpreadPattern",
    "TreatmentOutcome",
]
