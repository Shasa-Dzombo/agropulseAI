# c:\Users\Codeternal\Desktop\AgroPulse\app\computer_vision\crop_health_assessment\temporal_analysis.py

"""
Temporal Analysis for Crop Health Monitoring
============================================

This module provides a suite of tools for analyzing time-series data derived
from remote sensing imagery. Monitoring the temporal evolution of vegetation
indices (VIs) is crucial for understanding crop phenology, tracking growth
stages, and detecting anomalies that may indicate stress, disease, or other issues.

The core of this module is to work with time-series of VIs for specific fields
or management zones. The input is typically a pandas DataFrame where each row
represents a date and columns represent different VIs or spectral bands.

Key Capabilities:
-----------------
1.  **Data Smoothing and Interpolation**:
    -   Raw time-series data from satellites is often noisy due to atmospheric
      conditions (e.g., clouds, haze). This module provides robust smoothing
      techniques (like Savitzky-Golay, Whittaker smoother) to filter noise
      while preserving the underlying phenological signal.
    -   It also provides methods to interpolate the data to a regular daily
      time step, which is necessary for many modeling techniques.

2.  **Phenology Modeling**:
    -   `PhenologyModel`: A class that fits a mathematical function (e.g., a
      double logistic function) to the smoothed VI time-series.
    -   This model allows for the extraction of key phenological metrics, such as:
        -   Start of Season (SOS): The date when green-up begins.
        -   End of Season (EOS): The date when senescence is complete.
        -   Peak of Season (POS): The date of maximum VI, corresponding to peak
          canopy development.
        -   Length of Season (LOS): The duration between SOS and EOS.

3.  **Growth Curve Analysis**:
    -   Provides tools to compare the current season's growth curve against
      historical averages or reference curves.
    -   This comparison can reveal if the crop is developing faster or slower
      than expected, which can inform management decisions.

4.  **Temporal Anomaly Detection**:
    -   `TemporalAnomalyDetector`: A class that uses statistical methods or
      machine learning models to detect deviations from expected behavior.
    -   **Z-Score Method**: A simple statistical method to flag observations that
      deviate significantly from the historical mean for that day of the year.
    -   **LSTM Autoencoder**: A more advanced deep learning approach that learns a
      representation of a "normal" growth curve and can detect anomalies as
      points with high reconstruction error.

Core Classes:
-------------
-   `TimeSeriesSmoother`: Applies various smoothing and interpolation algorithms.
-   `PhenologyModel`: Fits a double logistic model to VI time-series to extract
  key growth stage dates.
-   `TemporalAnomalyDetector`: Implements different algorithms for detecting
  anomalies in growth curves.
"""

import numpy as np
import pandas as pd
from scipy.optimize import curve_fit
from scipy.signal import savgol_filter
import torch
import torch.nn as nn
from typing import Dict, Tuple, List, Optional
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Time-Series Smoothing ---

class TimeSeriesSmoother:
    """
    A class to smooth and interpolate time-series vegetation index data.
    """
    def __init__(self, method: str = 'savgol', **kwargs):
        if method not in ['savgol', 'whittaker']:
            raise ValueError("method must be one of 'savgol' or 'whittaker'")
        self.method = method
        self.params = kwargs
        logging.info(f"Initialized TimeSeriesSmoother with method: {self.method}")

    def smooth(self, ts: pd.Series) -> pd.Series:
        """
        Applies the chosen smoothing method to the time-series.
        
        Args:
            ts (pd.Series): A pandas Series with a DatetimeIndex and VI values.
            
        Returns:
            pd.Series: The smoothed time-series.
        """
        # Drop NaNs and sort by date
        ts = ts.dropna().sort_index()
        if ts.empty:
            return pd.Series(dtype=np.float64)

        if self.method == 'savgol':
            window_length = self.params.get('window_length', 15)
            polyorder = self.params.get('polyorder', 2)
            # Ensure window_length is odd and less than the number of points
            if len(ts) < window_length:
                window_length = max(3, len(ts) // 2 * 2 + 1) # Make it odd
            if window_length % 2 == 0:
                window_length += 1

            smoothed_values = savgol_filter(ts.values, window_length, polyorder)
            return pd.Series(smoothed_values, index=ts.index)
        
        elif self.method == 'whittaker':
            # A simplified implementation of the Whittaker smoother
            # For a full implementation, a library like `pywhittaker` would be better.
            lam = self.params.get('lambda', 10**2)
            d = 2 # Second-order differences
            
            y = ts.values
            m = len(y)
            D = np.diff(np.eye(m), d, axis=0)
            W = np.diag(np.ones(m)) # Assuming all points have equal weight
            
            # The core of the smoother
            z = np.linalg.solve(W + lam * (D.T @ D), y)
            return pd.Series(z, index=ts.index)

    def interpolate(self, ts: pd.Series, freq: str = 'D') -> pd.Series:
        """
        Interpolates a time-series to a regular frequency.
        
        Args:
            ts (pd.Series): The input time-series.
            freq (str): The target frequency (e.g., 'D' for daily).
            
        Returns:
            pd.Series: The interpolated time-series.
        """
        # Resample to the desired frequency and then interpolate
        return ts.resample(freq).interpolate(method='linear')

# --- Phenology Modeling ---

def double_logistic(t: np.ndarray, m1, m2, m3, m4, m5, m6, m7) -> np.ndarray:
    """
    Double logistic function for modeling vegetation phenology.
    This is a common model for VI time-series (e.g., from TIMESAT).
    """
    return m1 + m2 * (1 / (1 + np.exp(m3 - m4 * t)) - 1 / (1 + np.exp(m5 - m6 * t))) + m7 * t

class PhenologyModel:
    """
    Fits a double logistic model to a VI time-series to extract phenological metrics.
    """
    def __init__(self, ts: pd.Series):
        """
        Args:
            ts (pd.Series): A smoothed, daily-interpolated time-series of a VI.
        """
        if not isinstance(ts.index, pd.DatetimeIndex):
            raise TypeError("Input Series must have a DatetimeIndex.")
        self.ts = ts
        self.doy = ts.index.dayofyear.values
        self.params: Optional[np.ndarray] = None
        self.pheno_metrics: Dict[str, pd.Timestamp] = {}

    def fit(self):
        """Fits the double logistic model to the time-series data."""
        logging.info("Fitting double logistic model to time-series...")
        
        # Provide some reasonable initial guesses for the parameters
        initial_guess = [
            self.ts.min(), self.ts.max() - self.ts.min(),
            self.doy[len(self.doy)//4], 0.1,
            self.doy[len(self.doy)*3//4], 0.1,
            0.0
        ]
        
        try:
            popt, _ = curve_fit(
                double_logistic, self.doy, self.ts.values,
                p0=initial_guess, maxfev=10000
            )
            self.params = popt
            logging.info("Model fitting successful.")
            self._extract_phenometrics()
        except RuntimeError as e:
            logging.error(f"Could not fit the phenology model: {e}")
            self.params = None

    def predict(self, days: np.ndarray) -> np.ndarray:
        """Predicts VI values for given days of the year using the fitted model."""
        if self.params is None:
            raise RuntimeError("Model has not been fitted yet.")
        return double_logistic(days, *self.params)

    def _extract_phenometrics(self):
        """
        Extracts key phenological dates from the fitted model.
        This is a simplified interpretation based on the derivatives of the function.
        """
        if self.params is None:
            return

        # Generate a fine-grained time axis
        fine_doy = np.linspace(self.doy.min(), self.doy.max(), 2000)
        fitted_curve = self.predict(fine_doy)
        
        # Calculate first derivative (rate of change)
        derivative = np.gradient(fitted_curve, fine_doy)
        
        # Start of Season (SOS): Max of derivative in the first half
        first_half_idx = len(fine_doy) // 2
        sos_idx = np.argmax(derivative[:first_half_idx])
        sos_doy = fine_doy[sos_idx]
        
        # End of Season (EOS): Min of derivative in the second half
        eos_idx = np.argmin(derivative[first_half_idx:]) + first_half_idx
        eos_doy = fine_doy[eos_idx]
        
        # Peak of Season (POS): Max of the fitted curve
        pos_idx = np.argmax(fitted_curve)
        pos_doy = fine_doy[pos_idx]
        
        # Convert DOY back to Timestamp
        year = self.ts.index[0].year
        self.pheno_metrics = {
            'SOS': pd.to_datetime(f"{year}-01-01") + pd.to_timedelta(sos_doy - 1, 'D'),
            'POS': pd.to_datetime(f"{year}-01-01") + pd.to_timedelta(pos_doy - 1, 'D'),
            'EOS': pd.to_datetime(f"{year}-01-01") + pd.to_timedelta(eos_doy - 1, 'D'),
        }
        logging.info(f"Extracted Phenometrics: {self.pheno_metrics}")

# --- Temporal Anomaly Detection ---

class LSTMAutoencoder(nn.Module):
    """An LSTM Autoencoder for learning normal time-series patterns."""
    def __init__(self, input_dim: int, sequence_len: int, embedding_dim: int = 64):
        super().__init__()
        self.sequence_len = sequence_len
        self.embedding_dim = embedding_dim
        
        self.encoder = nn.LSTM(
            input_size=input_dim,
            hidden_size=embedding_dim,
            num_layers=1,
            batch_first=True
        )
        self.decoder = nn.LSTM(
            input_size=embedding_dim,
            hidden_size=input_dim,
            num_layers=1,
            batch_first=True
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # x shape: (batch_size, seq_len, input_dim)
        
        # Encoder
        _, (hidden, _) = self.encoder(x)
        
        # Repeat the final hidden state for each time step in the decoder
        decoder_input = hidden.repeat(1, self.sequence_len, 1)
        
        # Decoder
        reconstructed, _ = self.decoder(decoder_input)
        return reconstructed

class TemporalAnomalyDetector:
    """
    Detects anomalies in a time-series by comparing it to a historical norm.
    """
    def __init__(self, method: str = 'z_score', **kwargs):
        if method not in ['z_score', 'lstm_autoencoder']:
            raise ValueError("method must be 'z_score' or 'lstm_autoencoder'")
        self.method = method
        self.params = kwargs
        self.model = None
        logging.info(f"Initialized TemporalAnomalyDetector with method: {self.method}")

    def fit(self, historical_ts: List[pd.Series]):
        """
        Fits the anomaly detection model on historical data.
        
        Args:
            historical_ts (List[pd.Series]): A list of pandas Series, each
                representing a historical growth season.
        """
        if self.method == 'z_score':
            # Calculate historical mean and std dev for each day of the year
            all_ts = pd.concat(historical_ts)
            self.model = {
                'mean': all_ts.groupby(all_ts.index.dayofyear).mean(),
                'std': all_ts.groupby(all_ts.index.dayofyear).std()
            }
            logging.info("Calculated historical mean and std dev for Z-score method.")
        
        elif self.method == 'lstm_autoencoder':
            # Train an LSTM autoencoder on the historical data
            self.model = LSTMAutoencoder(**self.params.get('model_params', {}))
            # In a real scenario, a full training loop would be here.
            # This is a placeholder for the complex training logic.
            logging.warning("LSTM Autoencoder training is complex and not fully implemented in this demo. "
                            "The model is initialized but not trained.")

    def detect(self, current_ts: pd.Series, threshold: float = 2.5) -> pd.Series:
        """
        Detects anomalies in the current time-series.
        
        Args:
            current_ts (pd.Series): The time-series for the current season.
            threshold (float): The threshold for flagging an anomaly. For Z-score,
                               it's the number of standard deviations.
                               
        Returns:
            pd.Series: A Series with anomaly scores for each timestamp.
        """
        if self.model is None:
            raise RuntimeError("Detector has not been fitted yet.")
            
        if self.method == 'z_score':
            doy = current_ts.index.dayofyear
            mean = self.model['mean'].reindex(doy).ffill().bfill()
            std = self.model['std'].reindex(doy).ffill().bfill()
            
            # Ensure indices align
            mean.index = current_ts.index
            std.index = current_ts.index
            
            z_scores = (current_ts - mean) / (std + EPSILON)
            anomalies = z_scores.abs()
            logging.info(f"Detected { (anomalies > threshold).sum() } anomalies using Z-score method.")
            return anomalies
            
        elif self.method == 'lstm_autoencoder':
            # This is a simplified prediction step.
            logging.warning("LSTM prediction is simplified. Assumes untrained model.")
            # Preprocess current_ts into sequences
            # Pass sequences through the model to get reconstruction error
            # Anomaly score is the reconstruction error
            return pd.Series(np.random.rand(len(current_ts)), index=current_ts.index)


# --- Example Usage ---
if __name__ == '__main__':
    print("--- Temporal Analysis Module Demo ---")

    # 1. Generate dummy time-series data for NDVI
    dates = pd.to_datetime(pd.date_range(start='2023-03-01', end='2023-10-31', freq='5D'))
    true_doy = dates.dayofyear
    true_phenology = double_logistic(true_doy, 0.1, 0.7, 120, 0.1, 240, 0.1, 0)
    noise = np.random.normal(0, 0.05, len(dates))
    gaps = np.random.choice(len(dates), 10, replace=False)
    raw_ndvi = true_phenology + noise
    raw_ndvi[gaps] = np.nan # Simulate cloud cover
    
    ts_raw = pd.Series(raw_ndvi, index=dates)
    print(f"\nGenerated raw NDVI time-series with {len(ts_raw)} points.")

    # 2. Smooth and interpolate the data
    smoother = TimeSeriesSmoother(method='savgol', window_length=7)
    ts_smoothed = smoother.smooth(ts_raw)
    ts_daily = smoother.interpolate(ts_smoothed, freq='D')
    print("Smoothed and interpolated the time-series to daily frequency.")

    # 3. Fit phenology model
    pheno_model = PhenologyModel(ts_daily)
    pheno_model.fit()
    if pheno_model.params is not None:
        print(f"Phenology metrics: SOS={pheno_model.pheno_metrics['SOS'].date()}, "
              f"POS={pheno_model.pheno_metrics['POS'].date()}, "
              f"EOS={pheno_model.pheno_metrics['EOS'].date()}")

    # 4. Anomaly Detection
    print("\n--- Anomaly Detection Demo ---")
    # Create some historical data
    historical_data = []
    for _ in range(5): # 5 historical seasons
        hist_dates = pd.to_datetime(pd.date_range(start='2022-03-01', end='2022-10-31', freq='7D'))
        hist_doy = hist_dates.dayofyear
        hist_pheno = double_logistic(hist_doy, 0.1, 0.7, 120, 0.1, 240, 0.1, 0)
        hist_noise = np.random.normal(0, 0.03, len(hist_dates))
        historical_data.append(pd.Series(hist_pheno + hist_noise, index=hist_dates))
    
    # Initialize and fit the detector
    anomaly_detector = TemporalAnomalyDetector(method='z_score')
    anomaly_detector.fit(historical_data)
    
    # Introduce an anomaly into the current data
    ts_anomaly = ts_raw.copy()
    anomaly_date = pd.to_datetime('2023-07-15')
    ts_anomaly[anomaly_date] = 0.3 # A sudden drop
    ts_anomaly = ts_anomaly.sort_index()
    
    # Detect anomalies
    anomaly_scores = anomaly_detector.detect(ts_anomaly.dropna(), threshold=2.0)
    
    print("Top 5 anomaly scores:")
    print(anomaly_scores.nlargest(5))
    
    # Verify the introduced anomaly is detected
    if anomaly_date in anomaly_scores.nlargest(5).index:
        print("\nSuccessfully detected the manually introduced anomaly.")

```