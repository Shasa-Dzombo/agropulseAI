"""
Prophet-based Time-Series Forecasting Models
============================================

Facebook Prophet models optimized for agricultural forecasting with
strong seasonal patterns and holiday effects.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta
import logging
from prophet import Prophet
from prophet.diagnostics import cross_validation, performance_metrics
import joblib
from pathlib import Path

logger = logging.getLogger(__name__)


class ProphetYieldPredictor:
    """
    Crop yield forecasting using Prophet with weather and sensor data as regressors.
    
    Features:
    - Seasonal decomposition (planting/harvest cycles)
    - Weather regressor (temperature, rainfall, humidity)
    - Soil condition regressors (moisture, nutrients)
    - Holiday effects (regional farming holidays)
    - Uncertainty intervals (80% and 95%)
    """
    
    def __init__(
        self,
        seasonality_mode: str = 'multiplicative',
        changepoint_prior_scale: float = 0.05,
        seasonality_prior_scale: float = 10.0,
        holidays_prior_scale: float = 10.0,
        interval_width: float = 0.95,
    ):
        """
        Initialize Prophet yield predictor.
        
        Args:
            seasonality_mode: 'additive' or 'multiplicative'
            changepoint_prior_scale: Flexibility of trend (default: 0.05)
            seasonality_prior_scale: Strength of seasonality (default: 10.0)
            holidays_prior_scale: Strength of holiday effects (default: 10.0)
            interval_width: Uncertainty interval width (default: 0.95)
        """
        self.model = Prophet(
            seasonality_mode=seasonality_mode,
            changepoint_prior_scale=changepoint_prior_scale,
            seasonality_prior_scale=seasonality_prior_scale,
            holidays_prior_scale=holidays_prior_scale,
            interval_width=interval_width,
            daily_seasonality=False,
            weekly_seasonality=False,
            yearly_seasonality=True,
        )
        
        # Add custom seasonalities for agricultural cycles
        self.model.add_seasonality(
            name='planting_season',
            period=365.25,
            fourier_order=10,
        )
        self.model.add_seasonality(
            name='growth_season',
            period=90,
            fourier_order=5,
        )
        
        self.is_fitted = False
        self.feature_names = []
        self.metrics = {}
        
    def add_regressors(self, regressor_names: List[str]):
        """
        Add external regressors (weather, soil, etc.)
        
        Args:
            regressor_names: List of regressor column names
        """
        for name in regressor_names:
            self.model.add_regressor(name)
            self.feature_names.append(name)
        logger.info(f"Added {len(regressor_names)} regressors: {regressor_names}")
        
    def prepare_data(
        self,
        dates: pd.Series,
        yields: pd.Series,
        weather_data: Optional[pd.DataFrame] = None,
        soil_data: Optional[pd.DataFrame] = None,
    ) -> pd.DataFrame:
        """
        Prepare data in Prophet format (ds, y, regressors).
        
        Args:
            dates: Datetime series
            yields: Yield values (kg/ha)
            weather_data: Weather features (temp, rainfall, humidity)
            soil_data: Soil features (moisture, pH, NPK)
            
        Returns:
            Prophet-formatted DataFrame
        """
        df = pd.DataFrame({
            'ds': pd.to_datetime(dates),
            'y': yields,
        })
        
        # Add weather regressors
        if weather_data is not None:
            for col in weather_data.columns:
                df[col] = weather_data[col].values
                
        # Add soil regressors
        if soil_data is not None:
            for col in soil_data.columns:
                df[col] = soil_data[col].values
                
        # Remove any NaN values
        df = df.dropna()
        
        logger.info(f"Prepared {len(df)} samples with {len(df.columns)-2} regressors")
        return df
        
    def fit(
        self,
        train_data: pd.DataFrame,
        holidays: Optional[pd.DataFrame] = None,
    ) -> Dict[str, float]:
        """
        Train Prophet model on historical data.
        
        Args:
            train_data: Prophet-formatted training data
            holidays: Optional holiday DataFrame (ds, holiday, country)
            
        Returns:
            Training metrics
        """
        if holidays is not None:
            self.model.holidays = holidays
            
        logger.info("Training Prophet yield predictor...")
        self.model.fit(train_data)
        self.is_fitted = True
        
        # Calculate in-sample metrics
        forecast = self.model.predict(train_data)
        mae = np.mean(np.abs(forecast['yhat'] - train_data['y']))
        rmse = np.sqrt(np.mean((forecast['yhat'] - train_data['y'])**2))
        mape = np.mean(np.abs((train_data['y'] - forecast['yhat']) / train_data['y'])) * 100
        
        self.metrics = {
            'mae': mae,
            'rmse': rmse,
            'mape': mape,
            'samples': len(train_data),
        }
        
        logger.info(f"Training complete: MAE={mae:.2f}, RMSE={rmse:.2f}, MAPE={mape:.2f}%")
        return self.metrics
        
    def predict(
        self,
        periods: int,
        freq: str = 'D',
        future_regressors: Optional[pd.DataFrame] = None,
    ) -> pd.DataFrame:
        """
        Make future predictions.
        
        Args:
            periods: Number of periods to forecast
            freq: Frequency ('D' for daily, 'W' for weekly, 'M' for monthly)
            future_regressors: Future values for regressors
            
        Returns:
            Forecast DataFrame with predictions and uncertainty intervals
        """
        if not self.is_fitted:
            raise ValueError("Model must be fitted before prediction")
            
        # Create future dataframe
        future = self.model.make_future_dataframe(periods=periods, freq=freq)
        
        # Add future regressor values if provided
        if future_regressors is not None:
            for col in future_regressors.columns:
                if col in self.feature_names:
                    # Match dates and fill
                    future = future.merge(
                        future_regressors[[col]],
                        left_on='ds',
                        right_index=True,
                        how='left'
                    )
                    # Forward fill missing values
                    future[col] = future[col].fillna(method='ffill')
                    
        # Generate forecast
        forecast = self.model.predict(future)
        
        # Select relevant columns
        result = forecast[[
            'ds', 'yhat', 'yhat_lower', 'yhat_upper',
            'trend', 'trend_lower', 'trend_upper',
        ]].copy()
        
        # Add seasonal components
        if 'planting_season' in forecast.columns:
            result['planting_season'] = forecast['planting_season']
        if 'growth_season' in forecast.columns:
            result['growth_season'] = forecast['growth_season']
            
        logger.info(f"Generated {periods} period forecast")
        return result
        
    def cross_validate(
        self,
        initial: str = '730 days',
        period: str = '180 days',
        horizon: str = '365 days',
    ) -> pd.DataFrame:
        """
        Perform cross-validation to assess forecast accuracy.
        
        Args:
            initial: Initial training period
            period: Spacing between cutoff dates
            horizon: Forecast horizon
            
        Returns:
            Cross-validation metrics
        """
        if not self.is_fitted:
            raise ValueError("Model must be fitted before cross-validation")
            
        logger.info("Performing cross-validation...")
        df_cv = cross_validation(
            self.model,
            initial=initial,
            period=period,
            horizon=horizon,
        )
        
        df_metrics = performance_metrics(df_cv)
        
        logger.info(f"Cross-validation complete: {len(df_cv)} forecasts evaluated")
        return df_metrics
        
    def get_feature_importance(self) -> Dict[str, float]:
        """
        Get regressor importance from model coefficients.
        
        Returns:
            Dictionary of feature importances
        """
        if not self.is_fitted:
            raise ValueError("Model must be fitted first")
            
        importance = {}
        
        # Get regressor coefficients
        for regressor in self.feature_names:
            if regressor in self.model.train_component_cols:
                coef = self.model.params['beta'][
                    self.model.train_component_cols[regressor]
                ]
                importance[regressor] = abs(coef.mean())
                
        # Normalize
        total = sum(importance.values())
        if total > 0:
            importance = {k: v/total for k, v in importance.items()}
            
        return importance
        
    def save(self, filepath: str):
        """Save trained model to disk."""
        if not self.is_fitted:
            raise ValueError("Cannot save unfitted model")
            
        model_data = {
            'model': self.model,
            'feature_names': self.feature_names,
            'metrics': self.metrics,
        }
        joblib.dump(model_data, filepath)
        logger.info(f"Model saved to {filepath}")
        
    @classmethod
    def load(cls, filepath: str) -> 'ProphetYieldPredictor':
        """Load trained model from disk."""
        model_data = joblib.load(filepath)
        
        predictor = cls()
        predictor.model = model_data['model']
        predictor.feature_names = model_data['feature_names']
        predictor.metrics = model_data['metrics']
        predictor.is_fitted = True
        
        logger.info(f"Model loaded from {filepath}")
        return predictor


class ProphetPriceForecaster:
    """
    Market price forecasting using Prophet with external indicators.
    
    Features:
    - Seasonal price patterns
    - Holiday effects (festivals, holidays)
    - Supply/demand indicators
    - Weather impact on prices
    - Multi-commodity forecasting
    """
    
    def __init__(
        self,
        commodity: str,
        seasonality_mode: str = 'multiplicative',
        changepoint_prior_scale: float = 0.1,
        mcmc_samples: int = 0,
    ):
        """
        Initialize Prophet price forecaster.
        
        Args:
            commodity: Commodity name (e.g., 'maize', 'wheat', 'coffee')
            seasonality_mode: 'additive' or 'multiplicative'
            changepoint_prior_scale: Trend flexibility (default: 0.1)
            mcmc_samples: MCMC samples for uncertainty (0 = MAP estimation)
        """
        self.commodity = commodity
        self.model = Prophet(
            seasonality_mode=seasonality_mode,
            changepoint_prior_scale=changepoint_prior_scale,
            mcmc_samples=mcmc_samples,
            interval_width=0.95,
        )
        
        # Add market-specific seasonalities
        self.model.add_seasonality(
            name='harvest_impact',
            period=365.25,
            fourier_order=8,
        )
        self.model.add_seasonality(
            name='monthly_cycle',
            period=30.5,
            fourier_order=5,
        )
        
        self.is_fitted = False
        self.regressors = []
        
    def add_market_regressors(
        self,
        supply_indicator: bool = True,
        demand_indicator: bool = True,
        weather_impact: bool = True,
        fuel_prices: bool = True,
    ):
        """
        Add market-related regressors.
        
        Args:
            supply_indicator: Add supply levels
            demand_indicator: Add demand levels
            weather_impact: Add weather anomaly index
            fuel_prices: Add fuel price impact
        """
        if supply_indicator:
            self.model.add_regressor('supply_index')
            self.regressors.append('supply_index')
            
        if demand_indicator:
            self.model.add_regressor('demand_index')
            self.regressors.append('demand_index')
            
        if weather_impact:
            self.model.add_regressor('weather_anomaly')
            self.regressors.append('weather_anomaly')
            
        if fuel_prices:
            self.model.add_regressor('fuel_price_index')
            self.regressors.append('fuel_price_index')
            
        logger.info(f"Added {len(self.regressors)} market regressors")
        
    def prepare_price_data(
        self,
        dates: pd.Series,
        prices: pd.Series,
        market_data: Optional[pd.DataFrame] = None,
    ) -> pd.DataFrame:
        """
        Prepare price data in Prophet format.
        
        Args:
            dates: Datetime series
            prices: Price values (local currency per kg)
            market_data: Market indicators (supply, demand, etc.)
            
        Returns:
            Prophet-formatted DataFrame
        """
        df = pd.DataFrame({
            'ds': pd.to_datetime(dates),
            'y': prices,
        })
        
        # Add market regressors
        if market_data is not None:
            for col in market_data.columns:
                if col in self.regressors:
                    df[col] = market_data[col].values
                    
        df = df.dropna()
        
        logger.info(f"Prepared {len(df)} price samples for {self.commodity}")
        return df
        
    def fit(
        self,
        train_data: pd.DataFrame,
        holidays: Optional[pd.DataFrame] = None,
    ) -> Dict[str, float]:
        """Train Prophet price forecaster."""
        if holidays is not None:
            self.model.holidays = holidays
            
        logger.info(f"Training price forecaster for {self.commodity}...")
        self.model.fit(train_data)
        self.is_fitted = True
        
        # Calculate metrics
        forecast = self.model.predict(train_data)
        mae = np.mean(np.abs(forecast['yhat'] - train_data['y']))
        rmse = np.sqrt(np.mean((forecast['yhat'] - train_data['y'])**2))
        mape = np.mean(np.abs((train_data['y'] - forecast['yhat']) / train_data['y'])) * 100
        
        metrics = {
            'commodity': self.commodity,
            'mae': mae,
            'rmse': rmse,
            'mape': mape,
            'samples': len(train_data),
        }
        
        logger.info(f"Training complete: MAE={mae:.2f}, RMSE={rmse:.2f}, MAPE={mape:.2f}%")
        return metrics
        
    def predict(
        self,
        periods: int,
        freq: str = 'D',
        future_regressors: Optional[pd.DataFrame] = None,
    ) -> pd.DataFrame:
        """Generate price forecast."""
        if not self.is_fitted:
            raise ValueError("Model must be fitted before prediction")
            
        future = self.model.make_future_dataframe(periods=periods, freq=freq)
        
        # Add future regressor values
        if future_regressors is not None:
            for col in future_regressors.columns:
                if col in self.regressors:
                    future = future.merge(
                        future_regressors[[col]],
                        left_on='ds',
                        right_index=True,
                        how='left'
                    )
                    future[col] = future[col].fillna(method='ffill')
                    
        forecast = self.model.predict(future)
        
        result = forecast[[
            'ds', 'yhat', 'yhat_lower', 'yhat_upper',
            'trend', 'harvest_impact', 'monthly_cycle',
        ]].copy()
        
        result['commodity'] = self.commodity
        
        logger.info(f"Generated {periods} period price forecast for {self.commodity}")
        return result
        
    def save(self, filepath: str):
        """Save trained model."""
        model_data = {
            'commodity': self.commodity,
            'model': self.model,
            'regressors': self.regressors,
            'is_fitted': self.is_fitted,
        }
        joblib.dump(model_data, filepath)
        logger.info(f"Price forecaster saved to {filepath}")
        
    @classmethod
    def load(cls, filepath: str) -> 'ProphetPriceForecaster':
        """Load trained model."""
        model_data = joblib.load(filepath)
        
        forecaster = cls(commodity=model_data['commodity'])
        forecaster.model = model_data['model']
        forecaster.regressors = model_data['regressors']
        forecaster.is_fitted = model_data['is_fitted']
        
        logger.info(f"Price forecaster loaded from {filepath}")
        return forecaster


class ProphetWeatherForecaster:
    """
    Weather pattern forecasting for agricultural planning.
    
    Features:
    - Temperature predictions
    - Rainfall forecasting
    - Humidity patterns
    - Seasonal weather analysis
    """
    
    def __init__(
        self,
        weather_variable: str,
        location: str,
    ):
        """
        Initialize weather forecaster.
        
        Args:
            weather_variable: 'temperature', 'rainfall', or 'humidity'
            location: Location identifier
        """
        self.weather_variable = weather_variable
        self.location = location
        
        # Configure model based on variable
        if weather_variable == 'temperature':
            seasonality_mode = 'additive'
            changepoint_scale = 0.01
        elif weather_variable == 'rainfall':
            seasonality_mode = 'multiplicative'
            changepoint_scale = 0.05
        else:  # humidity
            seasonality_mode = 'additive'
            changepoint_scale = 0.02
            
        self.model = Prophet(
            seasonality_mode=seasonality_mode,
            changepoint_prior_scale=changepoint_scale,
            yearly_seasonality=True,
            weekly_seasonality=False,
            daily_seasonality=False,
        )
        
        self.is_fitted = False
        
    def fit(self, train_data: pd.DataFrame) -> Dict[str, float]:
        """Train weather forecaster."""
        logger.info(f"Training weather forecaster for {self.weather_variable} at {self.location}...")
        self.model.fit(train_data)
        self.is_fitted = True
        
        forecast = self.model.predict(train_data)
        mae = np.mean(np.abs(forecast['yhat'] - train_data['y']))
        rmse = np.sqrt(np.mean((forecast['yhat'] - train_data['y'])**2))
        
        metrics = {
            'variable': self.weather_variable,
            'location': self.location,
            'mae': mae,
            'rmse': rmse,
        }
        
        logger.info(f"Training complete: MAE={mae:.2f}, RMSE={rmse:.2f}")
        return metrics
        
    def predict(self, periods: int, freq: str = 'D') -> pd.DataFrame:
        """Generate weather forecast."""
        if not self.is_fitted:
            raise ValueError("Model must be fitted before prediction")
            
        future = self.model.make_future_dataframe(periods=periods, freq=freq)
        forecast = self.model.predict(future)
        
        result = forecast[['ds', 'yhat', 'yhat_lower', 'yhat_upper']].copy()
        result['variable'] = self.weather_variable
        result['location'] = self.location
        
        return result
