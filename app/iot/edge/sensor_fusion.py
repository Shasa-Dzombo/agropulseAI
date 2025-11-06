"""
Sensor Fusion Engine

Advanced sensor fusion using Kalman filters, particle filters,
and complementary filters for multi-sensor data integration.

Features:
- Extended Kalman Filter (EKF)
- Unscented Kalman Filter (UKF)
- Particle Filter
- Complementary Filter
- Sensor calibration
- Outlier detection
- State estimation
- Uncertainty quantification
"""

import numpy as np
import logging
from typing import Dict, List, Optional, Tuple, Union
from dataclasses import dataclass, field
from datetime import datetime
from scipy.linalg import sqrtm
from collections import deque
import json


logger = logging.getLogger(__name__)


@dataclass
class SensorReading:
    """Individual sensor reading"""
    sensor_id: str
    sensor_type: str  # 'temperature', 'humidity', 'soil_moisture', 'accelerometer', etc.
    value: Union[float, np.ndarray]
    timestamp: datetime
    uncertainty: Optional[float] = None
    quality: float = 1.0  # 0-1, where 1 is perfect quality
    metadata: Dict = field(default_factory=dict)


@dataclass
class FusedState:
    """Fused state estimate"""
    state: np.ndarray
    covariance: np.ndarray
    timestamp: datetime
    sensor_contributions: Dict[str, float]
    confidence: float
    metadata: Dict = field(default_factory=dict)


class KalmanFilter:
    """
    Extended Kalman Filter for sensor fusion
    
    Implements EKF for nonlinear state estimation with multiple sensors.
    """
    
    def __init__(
        self,
        state_dim: int,
        measurement_dim: int,
        process_noise: float = 0.01,
        measurement_noise: float = 0.1
    ):
        self.state_dim = state_dim
        self.measurement_dim = measurement_dim
        
        # State vector and covariance
        self.state = np.zeros(state_dim)
        self.covariance = np.eye(state_dim)
        
        # Process noise covariance (Q)
        self.Q = np.eye(state_dim) * process_noise
        
        # Measurement noise covariance (R)
        self.R = np.eye(measurement_dim) * measurement_noise
        
        # State transition matrix (F) - identity by default
        self.F = np.eye(state_dim)
        
        # Measurement matrix (H)
        self.H = np.eye(measurement_dim, state_dim)
        
        # History
        self.state_history: List[Tuple[datetime, np.ndarray]] = []
        self.measurement_history: List[Tuple[datetime, np.ndarray]] = []
        
        logger.info(f"KalmanFilter initialized (state_dim={state_dim}, meas_dim={measurement_dim})")
    
    def predict(self, dt: float, control_input: Optional[np.ndarray] = None):
        """
        Prediction step
        
        Args:
            dt: Time step
            control_input: Optional control input
        """
        # Update state transition matrix for time step
        # For constant velocity model: F = [[1, dt], [0, 1]]
        if self.state_dim == 2:  # Position and velocity
            self.F = np.array([[1, dt], [0, 1]])
        
        # Predict state
        self.state = self.F @ self.state
        if control_input is not None:
            self.state += control_input
        
        # Predict covariance
        self.covariance = self.F @ self.covariance @ self.F.T + self.Q
    
    def update(self, measurement: np.ndarray, measurement_noise: Optional[np.ndarray] = None):
        """
        Update step with measurement
        
        Args:
            measurement: Measurement vector
            measurement_noise: Optional measurement noise covariance
        """
        if measurement_noise is not None:
            R = measurement_noise
        else:
            R = self.R
        
        # Innovation (measurement residual)
        y = measurement - self.H @ self.state
        
        # Innovation covariance
        S = self.H @ self.covariance @ self.H.T + R
        
        # Kalman gain
        K = self.covariance @ self.H.T @ np.linalg.inv(S)
        
        # Update state
        self.state = self.state + K @ y
        
        # Update covariance
        I = np.eye(self.state_dim)
        self.covariance = (I - K @ self.H) @ self.covariance
        
        # Record history
        self.measurement_history.append((datetime.now(), measurement))
        self.state_history.append((datetime.now(), self.state.copy()))
    
    def get_state(self) -> Tuple[np.ndarray, np.ndarray]:
        """Get current state estimate and covariance"""
        return self.state.copy(), self.covariance.copy()
    
    def reset(self, initial_state: Optional[np.ndarray] = None):
        """Reset filter to initial conditions"""
        if initial_state is not None:
            self.state = initial_state
        else:
            self.state = np.zeros(self.state_dim)
        self.covariance = np.eye(self.state_dim)
        self.state_history.clear()
        self.measurement_history.clear()


class UnscentedKalmanFilter:
    """
    Unscented Kalman Filter for highly nonlinear systems
    
    Uses sigma points to capture nonlinear transformations more accurately than EKF.
    """
    
    def __init__(
        self,
        state_dim: int,
        measurement_dim: int,
        process_noise: float = 0.01,
        measurement_noise: float = 0.1,
        alpha: float = 1e-3,
        beta: float = 2.0,
        kappa: float = 0.0
    ):
        self.state_dim = state_dim
        self.measurement_dim = measurement_dim
        
        # State and covariance
        self.state = np.zeros(state_dim)
        self.covariance = np.eye(state_dim)
        
        # Noise covariances
        self.Q = np.eye(state_dim) * process_noise
        self.R = np.eye(measurement_dim) * measurement_noise
        
        # UKF parameters
        self.alpha = alpha
        self.beta = beta
        self.kappa = kappa
        
        # Calculate lambda
        self.lambda_ = alpha**2 * (state_dim + kappa) - state_dim
        
        # Calculate weights
        self.n_sigma = 2 * state_dim + 1
        self.weights_mean = np.zeros(self.n_sigma)
        self.weights_cov = np.zeros(self.n_sigma)
        
        self.weights_mean[0] = self.lambda_ / (state_dim + self.lambda_)
        self.weights_cov[0] = self.weights_mean[0] + (1 - alpha**2 + beta)
        
        for i in range(1, self.n_sigma):
            self.weights_mean[i] = 1 / (2 * (state_dim + self.lambda_))
            self.weights_cov[i] = self.weights_mean[i]
        
        logger.info(f"UKF initialized (state_dim={state_dim})")
    
    def _generate_sigma_points(self) -> np.ndarray:
        """Generate sigma points"""
        sigma_points = np.zeros((self.n_sigma, self.state_dim))
        
        # Calculate square root of covariance
        sqrt_cov = sqrtm((self.state_dim + self.lambda_) * self.covariance)
        
        # First sigma point is the mean
        sigma_points[0] = self.state
        
        # Generate remaining sigma points
        for i in range(self.state_dim):
            sigma_points[i + 1] = self.state + sqrt_cov[i]
            sigma_points[i + 1 + self.state_dim] = self.state - sqrt_cov[i]
        
        return sigma_points
    
    def predict(self, dt: float, state_transition_fn: callable):
        """
        Prediction step with custom state transition function
        
        Args:
            dt: Time step
            state_transition_fn: Function that propagates state
        """
        # Generate sigma points
        sigma_points = self._generate_sigma_points()
        
        # Propagate sigma points through state transition
        propagated_points = np.array([
            state_transition_fn(point, dt) for point in sigma_points
        ])
        
        # Calculate predicted mean
        self.state = np.sum(
            self.weights_mean[:, np.newaxis] * propagated_points, axis=0
        )
        
        # Calculate predicted covariance
        diff = propagated_points - self.state
        self.covariance = np.sum(
            self.weights_cov[:, np.newaxis, np.newaxis] *
            (diff[:, :, np.newaxis] @ diff[:, np.newaxis, :]),
            axis=0
        ) + self.Q
    
    def update(self, measurement: np.ndarray, measurement_fn: callable):
        """
        Update step with measurement
        
        Args:
            measurement: Measurement vector
            measurement_fn: Function that maps state to measurement
        """
        # Generate sigma points
        sigma_points = self._generate_sigma_points()
        
        # Transform sigma points through measurement function
        meas_points = np.array([measurement_fn(point) for point in sigma_points])
        
        # Calculate predicted measurement
        pred_meas = np.sum(
            self.weights_mean[:, np.newaxis] * meas_points, axis=0
        )
        
        # Calculate innovation covariance
        meas_diff = meas_points - pred_meas
        Pzz = np.sum(
            self.weights_cov[:, np.newaxis, np.newaxis] *
            (meas_diff[:, :, np.newaxis] @ meas_diff[:, np.newaxis, :]),
            axis=0
        ) + self.R
        
        # Calculate cross-covariance
        state_diff = sigma_points - self.state
        Pxz = np.sum(
            self.weights_cov[:, np.newaxis, np.newaxis] *
            (state_diff[:, :, np.newaxis] @ meas_diff[:, np.newaxis, :]),
            axis=0
        )
        
        # Calculate Kalman gain
        K = Pxz @ np.linalg.inv(Pzz)
        
        # Update state
        innovation = measurement - pred_meas
        self.state = self.state + K @ innovation
        
        # Update covariance
        self.covariance = self.covariance - K @ Pzz @ K.T


class ParticleFilter:
    """
    Particle Filter for non-Gaussian nonlinear state estimation
    
    Uses Monte Carlo sampling to represent state distribution.
    """
    
    def __init__(
        self,
        state_dim: int,
        num_particles: int = 1000,
        process_noise: float = 0.01,
        measurement_noise: float = 0.1
    ):
        self.state_dim = state_dim
        self.num_particles = num_particles
        self.process_noise = process_noise
        self.measurement_noise = measurement_noise
        
        # Initialize particles uniformly
        self.particles = np.random.randn(num_particles, state_dim)
        self.weights = np.ones(num_particles) / num_particles
        
        # Effective sample size threshold for resampling
        self.ess_threshold = num_particles / 2
        
        logger.info(f"ParticleFilter initialized (n_particles={num_particles})")
    
    def predict(self, dt: float, state_transition_fn: callable):
        """
        Prediction step - propagate particles
        
        Args:
            dt: Time step
            state_transition_fn: Function that propagates state
        """
        # Add process noise
        noise = np.random.randn(self.num_particles, self.state_dim) * self.process_noise
        
        # Propagate each particle
        for i in range(self.num_particles):
            self.particles[i] = state_transition_fn(self.particles[i], dt) + noise[i]
    
    def update(self, measurement: np.ndarray, likelihood_fn: callable):
        """
        Update step - reweight particles based on measurement
        
        Args:
            measurement: Measurement vector
            likelihood_fn: Function that computes measurement likelihood
        """
        # Compute likelihood for each particle
        for i in range(self.num_particles):
            self.weights[i] *= likelihood_fn(self.particles[i], measurement)
        
        # Normalize weights
        self.weights += 1e-300  # Avoid division by zero
        self.weights /= np.sum(self.weights)
        
        # Resample if effective sample size is too low
        ess = 1.0 / np.sum(self.weights**2)
        if ess < self.ess_threshold:
            self._resample()
    
    def _resample(self):
        """Systematic resampling"""
        cumsum = np.cumsum(self.weights)
        cumsum[-1] = 1.0  # Avoid numerical errors
        
        # Generate systematic samples
        positions = (np.arange(self.num_particles) + np.random.rand()) / self.num_particles
        
        # Resample particles
        indices = np.searchsorted(cumsum, positions)
        self.particles = self.particles[indices]
        self.weights = np.ones(self.num_particles) / self.num_particles
    
    def get_state(self) -> Tuple[np.ndarray, np.ndarray]:
        """
        Get state estimate (weighted mean) and covariance
        
        Returns:
            (state, covariance)
        """
        # Weighted mean
        state = np.sum(self.weights[:, np.newaxis] * self.particles, axis=0)
        
        # Weighted covariance
        diff = self.particles - state
        covariance = np.sum(
            self.weights[:, np.newaxis, np.newaxis] *
            (diff[:, :, np.newaxis] @ diff[:, np.newaxis, :]),
            axis=0
        )
        
        return state, covariance


class SensorFusionEngine:
    """
    Multi-sensor fusion engine
    
    Combines data from multiple sensors using various fusion algorithms.
    Handles sensor calibration, outlier detection, and uncertainty quantification.
    """
    
    def __init__(
        self,
        fusion_method: str = 'kalman',  # 'kalman', 'ukf', 'particle', 'complementary'
        state_dim: int = 6,  # Position (3) + Velocity (3)
        enable_outlier_detection: bool = True,
        outlier_threshold: float = 3.0
    ):
        self.fusion_method = fusion_method
        self.state_dim = state_dim
        self.enable_outlier_detection = enable_outlier_detection
        self.outlier_threshold = outlier_threshold
        
        # Initialize fusion filter
        if fusion_method == 'kalman':
            self.filter = KalmanFilter(state_dim=state_dim, measurement_dim=state_dim)
        elif fusion_method == 'ukf':
            self.filter = UnscentedKalmanFilter(state_dim=state_dim, measurement_dim=state_dim)
        elif fusion_method == 'particle':
            self.filter = ParticleFilter(state_dim=state_dim, num_particles=1000)
        else:
            raise ValueError(f"Unknown fusion method: {fusion_method}")
        
        # Sensor calibration parameters
        self.sensor_biases: Dict[str, float] = {}
        self.sensor_scales: Dict[str, float] = {}
        
        # Sensor reliability tracking
        self.sensor_reliabilities: Dict[str, float] = {}
        self.sensor_failure_counts: Dict[str, int] = {}
        
        # Reading history for outlier detection
        self.reading_history: Dict[str, deque] = {}
        self.history_length = 100
        
        # Fusion statistics
        self.fusion_count = 0
        self.outlier_count = 0
        
        logger.info(f"SensorFusionEngine initialized (method={fusion_method})")
    
    def calibrate_sensor(
        self,
        sensor_id: str,
        bias: float = 0.0,
        scale: float = 1.0
    ):
        """
        Set calibration parameters for a sensor
        
        Args:
            sensor_id: Sensor ID
            bias: Bias to subtract from readings
            scale: Scale factor to multiply readings
        """
        self.sensor_biases[sensor_id] = bias
        self.sensor_scales[sensor_id] = scale
        logger.info(f"Calibrated sensor {sensor_id}: bias={bias}, scale={scale}")
    
    def _apply_calibration(self, sensor_id: str, value: float) -> float:
        """Apply calibration to sensor reading"""
        bias = self.sensor_biases.get(sensor_id, 0.0)
        scale = self.sensor_scales.get(sensor_id, 1.0)
        return (value - bias) * scale
    
    def _is_outlier(self, sensor_id: str, value: float) -> bool:
        """Detect if reading is an outlier using statistical methods"""
        if not self.enable_outlier_detection:
            return False
        
        if sensor_id not in self.reading_history:
            return False
        
        history = list(self.reading_history[sensor_id])
        if len(history) < 10:
            return False
        
        # Calculate z-score
        mean = np.mean(history)
        std = np.std(history)
        
        if std < 1e-6:
            return False
        
        z_score = abs((value - mean) / std)
        
        return z_score > self.outlier_threshold
    
    def _update_reading_history(self, sensor_id: str, value: float):
        """Update reading history for sensor"""
        if sensor_id not in self.reading_history:
            self.reading_history[sensor_id] = deque(maxlen=self.history_length)
        
        self.reading_history[sensor_id].append(value)
    
    def _update_reliability(self, sensor_id: str, is_outlier: bool):
        """Update sensor reliability score"""
        if sensor_id not in self.sensor_reliabilities:
            self.sensor_reliabilities[sensor_id] = 1.0
            self.sensor_failure_counts[sensor_id] = 0
        
        if is_outlier:
            self.sensor_failure_counts[sensor_id] += 1
            # Exponential decay of reliability
            self.sensor_reliabilities[sensor_id] *= 0.95
        else:
            # Gradual recovery of reliability
            self.sensor_reliabilities[sensor_id] = min(
                1.0,
                self.sensor_reliabilities[sensor_id] + 0.01
            )
    
    def fuse_readings(
        self,
        readings: List[SensorReading],
        dt: float = 0.1
    ) -> FusedState:
        """
        Fuse multiple sensor readings into unified state estimate
        
        Args:
            readings: List of sensor readings
            dt: Time step since last fusion
            
        Returns:
            Fused state estimate
        """
        # Prediction step
        if self.fusion_method in ['kalman', 'ukf']:
            self.filter.predict(dt)
        
        # Process each reading
        valid_readings = []
        sensor_contributions = {}
        
        for reading in readings:
            # Apply calibration
            if isinstance(reading.value, (int, float)):
                calibrated_value = self._apply_calibration(reading.sensor_id, reading.value)
            else:
                calibrated_value = reading.value
            
            # Outlier detection
            if isinstance(calibrated_value, (int, float)):
                is_outlier = self._is_outlier(reading.sensor_id, calibrated_value)
                
                if is_outlier:
                    logger.warning(
                        f"Outlier detected from {reading.sensor_id}: {calibrated_value}"
                    )
                    self.outlier_count += 1
                    self._update_reliability(reading.sensor_id, True)
                    continue
                
                # Update history
                self._update_reading_history(reading.sensor_id, calibrated_value)
                self._update_reliability(reading.sensor_id, False)
            
            valid_readings.append((reading, calibrated_value))
        
        # Update step with valid readings
        if valid_readings:
            # Create measurement vector from valid readings
            # This is simplified - in practice, you'd map readings to state vector
            measurement = np.zeros(self.state_dim)
            total_weight = 0.0
            
            for reading, value in valid_readings:
                reliability = self.sensor_reliabilities.get(reading.sensor_id, 1.0)
                quality = reading.quality * reliability
                
                # Map reading to state vector (simplified)
                if isinstance(value, (int, float)):
                    # For scalar readings, update first dimension
                    measurement[0] += value * quality
                    total_weight += quality
                
                sensor_contributions[reading.sensor_id] = quality
            
            if total_weight > 0:
                measurement /= total_weight
                
                # Update filter
                if self.fusion_method == 'kalman':
                    self.filter.update(measurement)
                elif self.fusion_method == 'ukf':
                    # Define measurement function (identity for simplicity)
                    self.filter.update(
                        measurement,
                        measurement_fn=lambda x: x
                    )
        
        # Get fused state
        state, covariance = self.filter.get_state()
        
        # Calculate confidence from covariance
        confidence = 1.0 / (1.0 + np.trace(covariance))
        
        self.fusion_count += 1
        
        return FusedState(
            state=state,
            covariance=covariance,
            timestamp=datetime.now(),
            sensor_contributions=sensor_contributions,
            confidence=confidence,
            metadata={
                'fusion_count': self.fusion_count,
                'outlier_count': self.outlier_count,
                'num_sensors': len(valid_readings),
            }
        )
    
    def get_sensor_stats(self) -> Dict[str, Dict]:
        """Get statistics for all sensors"""
        stats = {}
        for sensor_id in self.sensor_reliabilities.keys():
            stats[sensor_id] = {
                'reliability': self.sensor_reliabilities[sensor_id],
                'failure_count': self.sensor_failure_counts[sensor_id],
                'bias': self.sensor_biases.get(sensor_id, 0.0),
                'scale': self.sensor_scales.get(sensor_id, 1.0),
            }
        return stats
    
    def reset(self):
        """Reset fusion engine"""
        if hasattr(self.filter, 'reset'):
            self.filter.reset()
        self.reading_history.clear()
        self.fusion_count = 0
        self.outlier_count = 0
        logger.info("SensorFusionEngine reset")


class ComplementaryFilter:
    """
    Complementary filter for IMU sensor fusion
    
    Combines accelerometer and gyroscope data for attitude estimation.
    Lightweight alternative to Kalman filtering.
    """
    
    def __init__(self, alpha: float = 0.98):
        """
        Initialize complementary filter
        
        Args:
            alpha: Filter coefficient (0-1), higher values trust gyroscope more
        """
        self.alpha = alpha
        self.pitch = 0.0
        self.roll = 0.0
        self.yaw = 0.0
        
        logger.info(f"ComplementaryFilter initialized (alpha={alpha})")
    
    def update(
        self,
        accel: np.ndarray,
        gyro: np.ndarray,
        dt: float
    ) -> Tuple[float, float, float]:
        """
        Update attitude estimate
        
        Args:
            accel: Accelerometer reading [ax, ay, az] (m/s^2)
            gyro: Gyroscope reading [gx, gy, gz] (rad/s)
            dt: Time step (seconds)
            
        Returns:
            (pitch, roll, yaw) in radians
        """
        # Calculate angles from accelerometer
        accel_pitch = np.arctan2(accel[1], np.sqrt(accel[0]**2 + accel[2]**2))
        accel_roll = np.arctan2(-accel[0], accel[2])
        
        # Integrate gyroscope
        gyro_pitch = self.pitch + gyro[0] * dt
        gyro_roll = self.roll + gyro[1] * dt
        gyro_yaw = self.yaw + gyro[2] * dt
        
        # Complementary filter
        self.pitch = self.alpha * gyro_pitch + (1 - self.alpha) * accel_pitch
        self.roll = self.alpha * gyro_roll + (1 - self.alpha) * accel_roll
        self.yaw = gyro_yaw  # Yaw can only come from gyroscope
        
        return self.pitch, self.roll, self.yaw
    
    def reset(self):
        """Reset filter"""
        self.pitch = 0.0
        self.roll = 0.0
        self.yaw = 0.0
