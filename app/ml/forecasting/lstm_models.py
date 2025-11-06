"""
LSTM Neural Network Time-Series Forecasting Models
==================================================

Deep learning models for complex agricultural time-series predictions
with multi-variate inputs and long-term dependencies.
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple, Any
import tensorflow as tf
from tensorflow import keras
from tensorflow.keras import layers, models, callbacks
from sklearn.preprocessing import MinMaxScaler, StandardScaler
import joblib
import logging

logger = logging.getLogger(__name__)


class LSTMYieldPredictor:
    """
    LSTM-based crop yield predictor with multi-variate sensor inputs.
    
    Architecture:
    - Input: Sequence of historical sensor readings (temperature, moisture, etc.)
    - LSTM layers: 128 -> 64 -> 32 units with dropout
    - Output: Predicted yield value with confidence interval
    
    Features:
    - Handles variable-length sequences
    - Attention mechanism for important timestamps
    - Dropout for regularization
    - Early stopping to prevent overfitting
    """
    
    def __init__(
        self,
        sequence_length: int = 30,
        n_features: int = 10,
        lstm_units: List[int] = [128, 64, 32],
        dropout_rate: float = 0.2,
        learning_rate: float = 0.001,
    ):
        """
        Initialize LSTM yield predictor.
        
        Args:
            sequence_length: Number of time steps to look back
            n_features: Number of input features
            lstm_units: List of LSTM layer sizes
            dropout_rate: Dropout rate for regularization
            learning_rate: Adam optimizer learning rate
        """
        self.sequence_length = sequence_length
        self.n_features = n_features
        self.lstm_units = lstm_units
        self.dropout_rate = dropout_rate
        self.learning_rate = learning_rate
        
        self.model = None
        self.scaler_X = MinMaxScaler()
        self.scaler_y = MinMaxScaler()
        self.is_fitted = False
        self.history = None
        
    def build_model(self):
        """Build LSTM model architecture."""
        inputs = keras.Input(shape=(self.sequence_length, self.n_features))
        
        # First LSTM layer
        x = layers.LSTM(
            self.lstm_units[0],
            return_sequences=True,
            kernel_regularizer=keras.regularizers.l2(0.01)
        )(inputs)
        x = layers.Dropout(self.dropout_rate)(x)
        x = layers.BatchNormalization()(x)
        
        # Second LSTM layer
        x = layers.LSTM(
            self.lstm_units[1],
            return_sequences=True,
            kernel_regularizer=keras.regularizers.l2(0.01)
        )(x)
        x = layers.Dropout(self.dropout_rate)(x)
        x = layers.BatchNormalization()(x)
        
        # Third LSTM layer
        x = layers.LSTM(
            self.lstm_units[2],
            return_sequences=False,
            kernel_regularizer=keras.regularizers.l2(0.01)
        )(x)
        x = layers.Dropout(self.dropout_rate)(x)
        x = layers.BatchNormalization()(x)
        
        # Attention mechanism
        attention = layers.Dense(self.lstm_units[2], activation='tanh')(x)
        attention = layers.Dense(1, activation='softmax')(attention)
        x = layers.Multiply()([x, attention])
        
        # Dense layers for prediction
        x = layers.Dense(64, activation='relu')(x)
        x = layers.Dropout(self.dropout_rate)(x)
        x = layers.Dense(32, activation='relu')(x)
        
        # Output layers: mean and std for confidence intervals
        mean_output = layers.Dense(1, name='mean')(x)
        std_output = layers.Dense(1, activation='softplus', name='std')(x)
        
        outputs = [mean_output, std_output]
        
        model = keras.Model(inputs=inputs, outputs=outputs)
        
        # Custom loss for uncertainty
        def uncertainty_loss(y_true, y_pred):
            mean, std = y_pred[0], y_pred[1]
            loss = tf.reduce_mean(
                0.5 * tf.math.log(std**2) + 
                0.5 * ((y_true - mean)**2) / (std**2)
            )
            return loss
        
        model.compile(
            optimizer=keras.optimizers.Adam(learning_rate=self.learning_rate),
            loss={
                'mean': 'mse',
                'std': 'mse'
            },
            metrics={
                'mean': ['mae', 'mse'],
                'std': ['mae']
            }
        )
        
        self.model = model
        logger.info(f"Built LSTM model with {model.count_params()} parameters")
        return model
        
    def prepare_sequences(
        self,
        data: np.ndarray,
        targets: np.ndarray,
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Create sequences for LSTM training.
        
        Args:
            data: Feature array (samples, features)
            targets: Target values (samples,)
            
        Returns:
            X: Sequences (samples, sequence_length, features)
            y: Targets (samples,)
        """
        X, y = [], []
        
        for i in range(len(data) - self.sequence_length):
            X.append(data[i:i + self.sequence_length])
            y.append(targets[i + self.sequence_length])
            
        X = np.array(X)
        y = np.array(y)
        
        logger.info(f"Created {len(X)} sequences of length {self.sequence_length}")
        return X, y
        
    def fit(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
        X_val: Optional[np.ndarray] = None,
        y_val: Optional[np.ndarray] = None,
        epochs: int = 100,
        batch_size: int = 32,
        verbose: int = 1,
    ) -> Dict[str, Any]:
        """
        Train LSTM model.
        
        Args:
            X_train: Training features (samples, time_steps, features)
            y_train: Training targets (samples,)
            X_val: Validation features
            y_val: Validation targets
            epochs: Number of training epochs
            batch_size: Batch size
            verbose: Verbosity level
            
        Returns:
            Training history and metrics
        """
        # Scale data
        n_samples = X_train.shape[0]
        X_train_scaled = self.scaler_X.fit_transform(
            X_train.reshape(-1, self.n_features)
        ).reshape(n_samples, self.sequence_length, self.n_features)
        
        y_train_scaled = self.scaler_y.fit_transform(y_train.reshape(-1, 1))
        
        if X_val is not None and y_val is not None:
            n_val_samples = X_val.shape[0]
            X_val_scaled = self.scaler_X.transform(
                X_val.reshape(-1, self.n_features)
            ).reshape(n_val_samples, self.sequence_length, self.n_features)
            y_val_scaled = self.scaler_y.transform(y_val.reshape(-1, 1))
            validation_data = (X_val_scaled, {'mean': y_val_scaled, 'std': y_val_scaled})
        else:
            validation_data = None
            
        # Build model if not already built
        if self.model is None:
            self.build_model()
            
        # Callbacks
        callback_list = [
            callbacks.EarlyStopping(
                monitor='val_loss' if validation_data else 'loss',
                patience=15,
                restore_best_weights=True,
                verbose=1
            ),
            callbacks.ReduceLROnPlateau(
                monitor='val_loss' if validation_data else 'loss',
                factor=0.5,
                patience=5,
                min_lr=1e-7,
                verbose=1
            ),
            callbacks.ModelCheckpoint(
                'best_lstm_yield_model.h5',
                monitor='val_loss' if validation_data else 'loss',
                save_best_only=True,
                verbose=0
            )
        ]
        
        logger.info("Training LSTM yield predictor...")
        self.history = self.model.fit(
            X_train_scaled,
            {'mean': y_train_scaled, 'std': y_train_scaled},
            validation_data=validation_data,
            epochs=epochs,
            batch_size=batch_size,
            callbacks=callback_list,
            verbose=verbose
        )
        
        self.is_fitted = True
        
        # Calculate final metrics
        train_pred = self.predict(X_train)
        mae = np.mean(np.abs(train_pred['mean'] - y_train))
        rmse = np.sqrt(np.mean((train_pred['mean'] - y_train)**2))
        
        metrics = {
            'train_mae': mae,
            'train_rmse': rmse,
            'epochs_trained': len(self.history.history['loss']),
            'final_loss': self.history.history['loss'][-1],
        }
        
        if validation_data:
            val_pred = self.predict(X_val)
            val_mae = np.mean(np.abs(val_pred['mean'] - y_val))
            val_rmse = np.sqrt(np.mean((val_pred['mean'] - y_val)**2))
            metrics.update({
                'val_mae': val_mae,
                'val_rmse': val_rmse,
                'final_val_loss': self.history.history['val_loss'][-1],
            })
            
        logger.info(f"Training complete: Train MAE={mae:.2f}, RMSE={rmse:.2f}")
        return metrics
        
    def predict(
        self,
        X: np.ndarray,
        return_std: bool = True,
    ) -> Dict[str, np.ndarray]:
        """
        Make predictions with uncertainty estimates.
        
        Args:
            X: Input sequences (samples, time_steps, features)
            return_std: Whether to return standard deviation
            
        Returns:
            Dictionary with 'mean' and optionally 'std' predictions
        """
        if not self.is_fitted:
            raise ValueError("Model must be fitted before prediction")
            
        # Scale input
        n_samples = X.shape[0]
        X_scaled = self.scaler_X.transform(
            X.reshape(-1, self.n_features)
        ).reshape(n_samples, self.sequence_length, self.n_features)
        
        # Predict
        predictions = self.model.predict(X_scaled, verbose=0)
        
        # Inverse transform
        mean_pred = self.scaler_y.inverse_transform(predictions[0])
        
        result = {'mean': mean_pred.flatten()}
        
        if return_std:
            std_pred = self.scaler_y.inverse_transform(predictions[1])
            result['std'] = std_pred.flatten()
            result['lower_bound'] = result['mean'] - 1.96 * result['std']
            result['upper_bound'] = result['mean'] + 1.96 * result['std']
            
        return result
        
    def save(self, filepath: str):
        """Save trained model."""
        if not self.is_fitted:
            raise ValueError("Cannot save unfitted model")
            
        self.model.save(f"{filepath}_model.h5")
        
        model_data = {
            'sequence_length': self.sequence_length,
            'n_features': self.n_features,
            'lstm_units': self.lstm_units,
            'dropout_rate': self.dropout_rate,
            'scaler_X': self.scaler_X,
            'scaler_y': self.scaler_y,
        }
        joblib.dump(model_data, f"{filepath}_metadata.pkl")
        logger.info(f"LSTM model saved to {filepath}")
        
    @classmethod
    def load(cls, filepath: str) -> 'LSTMYieldPredictor':
        """Load trained model."""
        model_data = joblib.load(f"{filepath}_metadata.pkl")
        
        predictor = cls(
            sequence_length=model_data['sequence_length'],
            n_features=model_data['n_features'],
            lstm_units=model_data['lstm_units'],
            dropout_rate=model_data['dropout_rate'],
        )
        
        predictor.model = keras.models.load_model(f"{filepath}_model.h5")
        predictor.scaler_X = model_data['scaler_X']
        predictor.scaler_y = model_data['scaler_y']
        predictor.is_fitted = True
        
        logger.info(f"LSTM model loaded from {filepath}")
        return predictor


class LSTMPriceForecaster:
    """
    LSTM-based market price forecaster with external indicators.
    
    Features:
    - Bidirectional LSTM for past and future context
    - Multi-head attention for feature importance
    - Encoder-decoder architecture for multi-step forecasting
    """
    
    def __init__(
        self,
        sequence_length: int = 60,
        forecast_horizon: int = 30,
        n_features: int = 8,
        encoder_units: List[int] = [128, 64],
        decoder_units: List[int] = [64, 32],
        attention_heads: int = 4,
    ):
        """Initialize LSTM price forecaster."""
        self.sequence_length = sequence_length
        self.forecast_horizon = forecast_horizon
        self.n_features = n_features
        self.encoder_units = encoder_units
        self.decoder_units = decoder_units
        self.attention_heads = attention_heads
        
        self.model = None
        self.scaler = StandardScaler()
        self.is_fitted = False
        
    def build_model(self):
        """Build encoder-decoder LSTM with attention."""
        # Encoder
        encoder_inputs = keras.Input(shape=(self.sequence_length, self.n_features))
        
        # Bidirectional LSTM encoder
        x = layers.Bidirectional(
            layers.LSTM(self.encoder_units[0], return_sequences=True)
        )(encoder_inputs)
        x = layers.Dropout(0.2)(x)
        
        encoder_outputs = layers.Bidirectional(
            layers.LSTM(self.encoder_units[1], return_sequences=True)
        )(x)
        
        # Multi-head attention
        attention_output = layers.MultiHeadAttention(
            num_heads=self.attention_heads,
            key_dim=self.encoder_units[1] * 2
        )(encoder_outputs, encoder_outputs)
        
        attention_output = layers.Dropout(0.2)(attention_output)
        attention_output = layers.LayerNormalization()(attention_output + encoder_outputs)
        
        # Decoder
        decoder_lstm = layers.LSTM(self.decoder_units[0], return_sequences=True)(attention_output)
        decoder_lstm = layers.Dropout(0.2)(decoder_lstm)
        decoder_lstm = layers.LSTM(self.decoder_units[1])(decoder_lstm)
        
        # Output dense layers
        x = layers.Dense(64, activation='relu')(decoder_lstm)
        x = layers.Dropout(0.2)(x)
        outputs = layers.Dense(self.forecast_horizon)(x)
        
        model = keras.Model(inputs=encoder_inputs, outputs=outputs)
        
        model.compile(
            optimizer=keras.optimizers.Adam(learning_rate=0.001),
            loss='mse',
            metrics=['mae', 'mape']
        )
        
        self.model = model
        logger.info(f"Built encoder-decoder LSTM with {model.count_params()} parameters")
        return model
        
    def prepare_data(
        self,
        data: np.ndarray,
    ) -> Tuple[np.ndarray, np.ndarray]:
        """Prepare encoder-decoder training data."""
        X, y = [], []
        
        for i in range(len(data) - self.sequence_length - self.forecast_horizon):
            X.append(data[i:i + self.sequence_length])
            y.append(data[i + self.sequence_length:i + self.sequence_length + self.forecast_horizon, 0])
            
        return np.array(X), np.array(y)
        
    def fit(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
        X_val: Optional[np.ndarray] = None,
        y_val: Optional[np.ndarray] = None,
        epochs: int = 50,
        batch_size: int = 32,
    ) -> Dict[str, float]:
        """Train price forecaster."""
        # Scale data
        n_samples = X_train.shape[0]
        X_train_scaled = self.scaler.fit_transform(
            X_train.reshape(-1, self.n_features)
        ).reshape(n_samples, self.sequence_length, self.n_features)
        
        if X_val is not None:
            n_val = X_val.shape[0]
            X_val_scaled = self.scaler.transform(
                X_val.reshape(-1, self.n_features)
            ).reshape(n_val, self.sequence_length, self.n_features)
            validation_data = (X_val_scaled, y_val)
        else:
            validation_data = None
            
        if self.model is None:
            self.build_model()
            
        logger.info("Training LSTM price forecaster...")
        history = self.model.fit(
            X_train_scaled,
            y_train,
            validation_data=validation_data,
            epochs=epochs,
            batch_size=batch_size,
            callbacks=[
                callbacks.EarlyStopping(patience=10, restore_best_weights=True),
                callbacks.ReduceLROnPlateau(factor=0.5, patience=5)
            ],
            verbose=1
        )
        
        self.is_fitted = True
        
        return {
            'final_loss': history.history['loss'][-1],
            'final_mae': history.history['mae'][-1],
            'epochs': len(history.history['loss'])
        }
        
    def predict(self, X: np.ndarray) -> np.ndarray:
        """Forecast future prices."""
        if not self.is_fitted:
            raise ValueError("Model must be fitted first")
            
        n_samples = X.shape[0]
        X_scaled = self.scaler.transform(
            X.reshape(-1, self.n_features)
        ).reshape(n_samples, self.sequence_length, self.n_features)
        
        return self.model.predict(X_scaled, verbose=0)


class LSTMMultivariatePredictor:
    """
    Multi-output LSTM for predicting multiple agricultural variables simultaneously.
    
    Outputs:
    - Crop yield
    - Market price
    - Soil moisture
    - Pest risk
    """
    
    def __init__(
        self,
        sequence_length: int = 30,
        n_features: int = 15,
        n_outputs: int = 4,
        lstm_units: List[int] = [256, 128, 64],
    ):
        """Initialize multivariate predictor."""
        self.sequence_length = sequence_length
        self.n_features = n_features
        self.n_outputs = n_outputs
        self.lstm_units = lstm_units
        
        self.model = None
        self.scaler_X = StandardScaler()
        self.scaler_y = StandardScaler()
        self.is_fitted = False
        
    def build_model(self):
        """Build multi-output LSTM model."""
        inputs = keras.Input(shape=(self.sequence_length, self.n_features))
        
        # Shared LSTM layers
        x = layers.LSTM(self.lstm_units[0], return_sequences=True)(inputs)
        x = layers.Dropout(0.3)(x)
        x = layers.LSTM(self.lstm_units[1], return_sequences=True)(x)
        x = layers.Dropout(0.3)(x)
        shared = layers.LSTM(self.lstm_units[2])(x)
        
        # Task-specific heads
        yield_head = layers.Dense(32, activation='relu', name='yield_dense')(shared)
        yield_output = layers.Dense(1, name='yield_output')(yield_head)
        
        price_head = layers.Dense(32, activation='relu', name='price_dense')(shared)
        price_output = layers.Dense(1, name='price_output')(price_head)
        
        moisture_head = layers.Dense(32, activation='relu', name='moisture_dense')(shared)
        moisture_output = layers.Dense(1, name='moisture_output')(moisture_head)
        
        risk_head = layers.Dense(32, activation='relu', name='risk_dense')(shared)
        risk_output = layers.Dense(1, activation='sigmoid', name='risk_output')(risk_head)
        
        model = keras.Model(
            inputs=inputs,
            outputs=[yield_output, price_output, moisture_output, risk_output]
        )
        
        model.compile(
            optimizer=keras.optimizers.Adam(learning_rate=0.001),
            loss={
                'yield_output': 'mse',
                'price_output': 'mse',
                'moisture_output': 'mse',
                'risk_output': 'binary_crossentropy'
            },
            loss_weights={
                'yield_output': 1.0,
                'price_output': 1.0,
                'moisture_output': 0.5,
                'risk_output': 2.0
            },
            metrics={
                'yield_output': ['mae'],
                'price_output': ['mae'],
                'moisture_output': ['mae'],
                'risk_output': ['accuracy']
            }
        )
        
        self.model = model
        logger.info(f"Built multivariate LSTM with {model.count_params()} parameters")
        return model
