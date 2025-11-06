"""
Market Intelligence and Price Prediction Module

This module provides agricultural market intelligence:
- Crop price prediction
- Market demand forecasting
- Supply chain optimization
- Best selling time recommendations
- Price trend analysis
- Market sentiment analysis
- Buyer-seller matching
- Profitability analysis
"""

import numpy as np
import pandas as pd
from typing import Dict, Any, List, Optional, Tuple, Union
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
import logging

from app.ml.base import BaseMLModel, ModelType, ModelMetrics, PredictionResult

logger = logging.getLogger(__name__)


class MarketTrend(Enum):
    """Market price trends."""
    BULLISH = "bullish"  # Rising prices
    BEARISH = "bearish"  # Falling prices
    STABLE = "stable"    # Stable prices
    VOLATILE = "volatile"  # High volatility


class MarketSeason(Enum):
    """Market seasons."""
    PEAK_SUPPLY = "peak_supply"  # High supply, lower prices
    LOW_SUPPLY = "low_supply"    # Low supply, higher prices
    NORMAL = "normal"            # Normal supply/demand balance


@dataclass
class PricePrediction:
    """
    Price prediction result.
    
    Attributes:
        crop: Crop name
        predicted_price: Predicted price per kg
        confidence_interval: (lower, upper) price bounds
        prediction_date: Date of prediction
        trend: Market trend
        factors: Price influencing factors
        recommendation: Selling recommendation
        alternative_markets: Alternative market options
    """
    crop: str
    predicted_price: float
    confidence_interval: Tuple[float, float]
    prediction_date: datetime
    trend: MarketTrend
    factors: Dict[str, float]
    recommendation: str
    alternative_markets: List[Dict[str, Any]]


@dataclass
class MarketAnalysis:
    """
    Comprehensive market analysis.
    
    Attributes:
        crop: Crop name
        current_price: Current market price
        historical_average: Historical average price
        price_volatility: Price volatility measure
        demand_level: Current demand level
        supply_level: Current supply level
        season: Market season
        opportunities: Market opportunities
        risks: Market risks
    """
    crop: str
    current_price: float
    historical_average: float
    price_volatility: float
    demand_level: str
    supply_level: str
    season: MarketSeason
    opportunities: List[str]
    risks: List[str]


class CropPricePredictor(BaseMLModel):
    """
    ML model for crop price prediction.
    """
    
    def __init__(self, crop: str, version: str = "1.0.0"):
        """
        Initialize price predictor.
        
        Args:
            crop: Crop name
            version: Model version
        """
        super().__init__(
            model_name=f"price_predictor_{crop}",
            model_type=ModelType.REGRESSION,
            version=version
        )
        self.crop = crop
        
        # Historical price data (would be loaded from database)
        self.historical_prices = self._load_historical_prices()
        
        logger.info(f"Crop Price Predictor initialized for {crop}")
    
    def _load_historical_prices(self) -> pd.DataFrame:
        """Load historical price data."""
        # Simulate historical data
        dates = pd.date_range(end=datetime.now(), periods=365, freq='D')
        base_price = np.random.uniform(20, 100)
        
        # Generate synthetic prices with seasonality and trend
        prices = []
        for i, date in enumerate(dates):
            # Seasonal component
            seasonal = 10 * np.sin(2 * np.pi * i / 365)
            # Trend component
            trend = 0.05 * i
            # Random noise
            noise = np.random.randn() * 5
            
            price = base_price + seasonal + trend + noise
            prices.append(max(10, price))
        
        return pd.DataFrame({
            'date': dates,
            'price': prices
        })
    
    def train(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
        **kwargs
    ) -> ModelMetrics:
        """
        Train price prediction model.
        
        Args:
            X_train: Training features (date, supply, demand, etc.)
            y_train: Historical prices
            
        Returns:
            Training metrics
        """
        logger.info(f"Training price predictor for {self.crop}")
        
        # Simulate training
        # In production, would use ARIMA, LSTM, or similar time series models
        
        self.is_trained = True
        
        return ModelMetrics(
            mae=5.2,
            rmse=7.8,
            r2_score=0.82,
            training_time=12.5
        )
    
    def predict(
        self,
        X: Union[np.ndarray, Dict[str, Any]],
        days_ahead: int = 7
    ) -> PredictionResult:
        """
        Predict future prices.
        
        Args:
            X: Input features or dict with market data
            days_ahead: Days ahead to predict
            
        Returns:
            Price prediction
        """
        if not self.is_trained:
            raise ValueError("Model must be trained before prediction")
        
        # Extract features
        if isinstance(X, dict):
            current_supply = X.get("supply_level", 1.0)
            current_demand = X.get("demand_level", 1.0)
            season = X.get("season", "normal")
        else:
            current_supply = 1.0
            current_demand = 1.0
            season = "normal"
        
        # Get current price
        current_price = self.historical_prices['price'].iloc[-1]
        
        # Predict future price
        predicted_price = self._predict_price(
            current_price,
            current_supply,
            current_demand,
            season,
            days_ahead
        )
        
        # Calculate confidence interval
        std = self.historical_prices['price'].std()
        confidence_interval = (
            predicted_price - 1.96 * std / np.sqrt(days_ahead),
            predicted_price + 1.96 * std / np.sqrt(days_ahead)
        )
        
        # Determine trend
        recent_prices = self.historical_prices['price'].tail(30).values
        trend = self._determine_trend(recent_prices)
        
        # Analyze factors
        factors = self._analyze_price_factors(
            current_supply,
            current_demand,
            season
        )
        
        # Generate recommendation
        recommendation = self._generate_selling_recommendation(
            predicted_price,
            current_price,
            trend
        )
        
        # Find alternative markets
        alternatives = self._find_alternative_markets(self.crop, predicted_price)
        
        price_pred = PricePrediction(
            crop=self.crop,
            predicted_price=predicted_price,
            confidence_interval=confidence_interval,
            prediction_date=datetime.now() + timedelta(days=days_ahead),
            trend=trend,
            factors=factors,
            recommendation=recommendation,
            alternative_markets=alternatives
        )
        
        return PredictionResult(
            prediction=predicted_price,
            confidence=0.82,
            explanation=f"Predicted price: KES {predicted_price:.2f}/kg in {days_ahead} days - {recommendation}",
            metadata={
                "current_price": current_price,
                "price_change_pct": ((predicted_price - current_price) / current_price) * 100,
                "trend": trend.value,
                "confidence_interval": confidence_interval,
                "factors": factors,
                "alternative_markets": alternatives
            },
            model_version=self.version
        )
    
    def _predict_price(
        self,
        current_price: float,
        supply: float,
        demand: float,
        season: str,
        days_ahead: int
    ) -> float:
        """Predict future price."""
        # Base prediction on current price
        predicted = current_price
        
        # Supply-demand adjustment
        supply_demand_ratio = supply / demand if demand > 0 else 1.0
        if supply_demand_ratio > 1.2:
            predicted *= 0.9  # Oversupply, lower prices
        elif supply_demand_ratio < 0.8:
            predicted *= 1.15  # Under supply, higher prices
        
        # Seasonal adjustment
        if season == "peak_supply":
            predicted *= 0.85
        elif season == "low_supply":
            predicted *= 1.25
        
        # Time decay (uncertainty increases with horizon)
        uncertainty_factor = 1 + (days_ahead / 365) * 0.1
        predicted *= np.random.uniform(0.95, 1.05) * uncertainty_factor
        
        return max(10, predicted)
    
    def _determine_trend(self, recent_prices: np.ndarray) -> MarketTrend:
        """Determine market trend."""
        if len(recent_prices) < 10:
            return MarketTrend.STABLE
        
        # Calculate price changes
        changes = np.diff(recent_prices)
        avg_change = np.mean(changes)
        volatility = np.std(changes)
        
        # High volatility
        if volatility > np.mean(recent_prices) * 0.1:
            return MarketTrend.VOLATILE
        
        # Trending up
        if avg_change > np.mean(recent_prices) * 0.01:
            return MarketTrend.BULLISH
        
        # Trending down
        if avg_change < -np.mean(recent_prices) * 0.01:
            return MarketTrend.BEARISH
        
        return MarketTrend.STABLE
    
    def _analyze_price_factors(
        self,
        supply: float,
        demand: float,
        season: str
    ) -> Dict[str, float]:
        """Analyze factors affecting price."""
        factors = {}
        
        # Supply impact (0-100 scale)
        if supply > 1.2:
            factors["oversupply"] = -30
        elif supply < 0.8:
            factors["shortage"] = 25
        else:
            factors["supply_normal"] = 0
        
        # Demand impact
        if demand > 1.2:
            factors["high_demand"] = 25
        elif demand < 0.8:
            factors["low_demand"] = -20
        else:
            factors["demand_normal"] = 0
        
        # Seasonal impact
        if season == "peak_supply":
            factors["seasonal_surplus"] = -25
        elif season == "low_supply":
            factors["seasonal_shortage"] = 30
        
        # Weather impact (simplified)
        factors["weather_conditions"] = np.random.uniform(-10, 10)
        
        return factors
    
    def _generate_selling_recommendation(
        self,
        predicted_price: float,
        current_price: float,
        trend: MarketTrend
    ) -> str:
        """Generate selling recommendation."""
        price_change_pct = ((predicted_price - current_price) / current_price) * 100
        
        if trend == MarketTrend.BULLISH:
            if price_change_pct > 10:
                return "HOLD - Prices expected to rise significantly. Wait for better prices."
            else:
                return "CONSIDER HOLDING - Moderate price increase expected."
        
        elif trend == MarketTrend.BEARISH:
            if price_change_pct < -10:
                return "SELL NOW - Prices likely to fall. Sell immediately to avoid losses."
            else:
                return "SELL SOON - Slight price decline expected. Consider selling within a week."
        
        elif trend == MarketTrend.VOLATILE:
            return "SELL GRADUALLY - High volatility. Consider selling in batches to average prices."
        
        else:  # STABLE
            return "FLEXIBLE - Prices stable. Sell based on cash flow needs."
    
    def _find_alternative_markets(
        self,
        crop: str,
        predicted_price: float
    ) -> List[Dict[str, Any]]:
        """Find alternative markets."""
        # Simulate alternative markets
        markets = [
            {
                "market_name": "Nairobi Wholesale Market",
                "expected_price": predicted_price * 1.1,
                "distance_km": 50,
                "transport_cost_per_kg": 2.5,
                "market_fee_pct": 5
            },
            {
                "market_name": "Local Retail Market",
                "expected_price": predicted_price * 1.25,
                "distance_km": 5,
                "transport_cost_per_kg": 0.5,
                "market_fee_pct": 2
            },
            {
                "market_name": "Export Market",
                "expected_price": predicted_price * 1.5,
                "distance_km": 200,
                "transport_cost_per_kg": 8.0,
                "market_fee_pct": 10
            }
        ]
        
        # Calculate net price for each market
        for market in markets:
            transport = market["transport_cost_per_kg"]
            fee = market["expected_price"] * (market["market_fee_pct"] / 100)
            market["net_price"] = market["expected_price"] - transport - fee
            market["premium_vs_base"] = market["net_price"] - predicted_price
        
        # Sort by net price
        markets.sort(key=lambda x: x["net_price"], reverse=True)
        
        return markets[:3]
    
    def evaluate(
        self,
        X_test: np.ndarray,
        y_test: np.ndarray
    ) -> ModelMetrics:
        """
        Evaluate price prediction model.
        
        Args:
            X_test: Test features
            y_test: Actual prices
            
        Returns:
            Evaluation metrics
        """
        # Simulate evaluation
        predictions = []
        for x in X_test:
            pred = self.predict({"supply_level": 1.0, "demand_level": 1.0})
            predictions.append(pred.prediction)
        
        predictions = np.array(predictions)
        
        mae = np.mean(np.abs(predictions - y_test))
        rmse = np.sqrt(np.mean((predictions - y_test) ** 2))
        r2 = 1 - np.sum((y_test - predictions) ** 2) / np.sum((y_test - np.mean(y_test)) ** 2)
        
        return ModelMetrics(
            mae=mae,
            rmse=rmse,
            r2_score=r2,
            inference_time=0.03
        )


class MarketAnalyzer:
    """
    Comprehensive market analysis system.
    """
    
    def __init__(self):
        """Initialize market analyzer."""
        self.crop_prices = self._initialize_price_database()
        logger.info("Market Analyzer initialized")
    
    def _initialize_price_database(self) -> Dict[str, float]:
        """Initialize crop price database."""
        return {
            "maize": 45.0,
            "beans": 120.0,
            "potatoes": 35.0,
            "tomatoes": 60.0,
            "kale": 25.0,
            "cabbage": 30.0,
            "wheat": 50.0,
            "rice": 80.0,
            "bananas": 40.0,
            "sugarcane": 15.0
        }
    
    def analyze_market(
        self,
        crop: str,
        current_supply: float,
        current_demand: float,
        historical_data: Optional[pd.DataFrame] = None
    ) -> MarketAnalysis:
        """
        Perform comprehensive market analysis.
        
        Args:
            crop: Crop name
            current_supply: Current supply level
            current_demand: Current demand level
            historical_data: Historical price data
            
        Returns:
            Market analysis
        """
        logger.info(f"Analyzing market for {crop}")
        
        # Get current price
        current_price = self.crop_prices.get(crop, 50.0)
        
        # Calculate historical average
        if historical_data is not None and 'price' in historical_data.columns:
            historical_avg = historical_data['price'].mean()
            volatility = historical_data['price'].std() / historical_avg
        else:
            historical_avg = current_price * 0.9
            volatility = 0.15
        
        # Determine supply/demand levels
        demand_level = self._classify_level(current_demand, "demand")
        supply_level = self._classify_level(current_supply, "supply")
        
        # Determine season
        season = self._determine_season(current_supply, current_demand)
        
        # Identify opportunities
        opportunities = self._identify_opportunities(
            crop,
            current_price,
            historical_avg,
            demand_level,
            supply_level,
            season
        )
        
        # Identify risks
        risks = self._identify_risks(
            crop,
            volatility,
            demand_level,
            supply_level,
            season
        )
        
        return MarketAnalysis(
            crop=crop,
            current_price=current_price,
            historical_average=historical_avg,
            price_volatility=volatility,
            demand_level=demand_level,
            supply_level=supply_level,
            season=season,
            opportunities=opportunities,
            risks=risks
        )
    
    def _classify_level(self, value: float, metric: str) -> str:
        """Classify supply or demand level."""
        if value > 1.3:
            return "very_high"
        elif value > 1.1:
            return "high"
        elif value > 0.9:
            return "normal"
        elif value > 0.7:
            return "low"
        else:
            return "very_low"
    
    def _determine_season(self, supply: float, demand: float) -> MarketSeason:
        """Determine market season."""
        ratio = supply / demand if demand > 0 else 1.0
        
        if ratio > 1.3:
            return MarketSeason.PEAK_SUPPLY
        elif ratio < 0.7:
            return MarketSeason.LOW_SUPPLY
        else:
            return MarketSeason.NORMAL
    
    def _identify_opportunities(
        self,
        crop: str,
        current_price: float,
        historical_avg: float,
        demand: str,
        supply: str,
        season: MarketSeason
    ) -> List[str]:
        """Identify market opportunities."""
        opportunities = []
        
        # Price opportunities
        if current_price > historical_avg * 1.2:
            opportunities.append(f"Premium prices - {((current_price/historical_avg - 1) * 100):.1f}% above average")
        
        # Demand opportunities
        if demand in ["high", "very_high"]:
            opportunities.append("Strong market demand - good time to sell")
        
        # Supply opportunities
        if supply in ["low", "very_low"] and season == MarketSeason.LOW_SUPPLY:
            opportunities.append("Low supply conditions - prices likely to increase")
        
        # Seasonal opportunities
        if season == MarketSeason.LOW_SUPPLY:
            opportunities.append("Off-season production - premium prices available")
        
        # Value addition
        opportunities.append(f"Consider value addition (processing, packaging) to increase {crop} value")
        
        # Direct market access
        opportunities.append("Explore direct-to-consumer channels for better margins")
        
        return opportunities
    
    def _identify_risks(
        self,
        crop: str,
        volatility: float,
        demand: str,
        supply: str,
        season: MarketSeason
    ) -> List[str]:
        """Identify market risks."""
        risks = []
        
        # Volatility risk
        if volatility > 0.25:
            risks.append(f"High price volatility ({volatility*100:.1f}%) - unpredictable prices")
        
        # Supply risk
        if supply in ["high", "very_high"]:
            risks.append("Oversupply conditions - downward pressure on prices")
        
        # Demand risk
        if demand in ["low", "very_low"]:
            risks.append("Weak demand - difficult to sell at good prices")
        
        # Seasonal risk
        if season == MarketSeason.PEAK_SUPPLY:
            risks.append("Peak supply season - prices typically lower")
        
        # Storage risk
        risks.append("Post-harvest losses if not sold quickly - consider storage options")
        
        # Quality risk
        risks.append("Quality degradation affects price - maintain proper handling")
        
        return risks


class ProfitabilityAnalyzer:
    """
    Analyze crop profitability.
    """
    
    def __init__(self):
        """Initialize profitability analyzer."""
        self.cost_database = self._initialize_cost_database()
        logger.info("Profitability Analyzer initialized")
    
    def _initialize_cost_database(self) -> Dict[str, Dict[str, float]]:
        """Initialize production cost database."""
        return {
            "maize": {
                "seed": 5000,
                "fertilizer": 15000,
                "pesticides": 5000,
                "labor": 20000,
                "land_prep": 8000,
                "harvesting": 10000,
                "transport": 5000
            },
            "tomatoes": {
                "seed": 8000,
                "fertilizer": 25000,
                "pesticides": 15000,
                "labor": 40000,
                "land_prep": 10000,
                "harvesting": 20000,
                "transport": 8000
            }
        }
    
    def analyze_profitability(
        self,
        crop: str,
        area_ha: float,
        expected_yield_tons: float,
        selling_price_per_kg: float,
        custom_costs: Optional[Dict[str, float]] = None
    ) -> Dict[str, Any]:
        """
        Analyze crop profitability.
        
        Args:
            crop: Crop name
            area_ha: Farm area in hectares
            expected_yield_tons: Expected yield
            selling_price_per_kg: Selling price per kg
            custom_costs: Custom production costs
            
        Returns:
            Profitability analysis
        """
        logger.info(f"Analyzing profitability for {crop}")
        
        # Get production costs
        if custom_costs:
            costs = custom_costs
        else:
            base_costs = self.cost_database.get(crop, {
                "seed": 5000,
                "fertilizer": 15000,
                "pesticides": 5000,
                "labor": 20000,
                "land_prep": 8000,
                "harvesting": 10000,
                "transport": 5000
            })
            # Scale costs by area
            costs = {k: v * area_ha for k, v in base_costs.items()}
        
        total_costs = sum(costs.values())
        
        # Calculate revenue
        total_yield_kg = expected_yield_tons * 1000
        gross_revenue = total_yield_kg * selling_price_per_kg
        
        # Calculate profit
        net_profit = gross_revenue - total_costs
        profit_margin = (net_profit / gross_revenue * 100) if gross_revenue > 0 else 0
        roi = (net_profit / total_costs * 100) if total_costs > 0 else 0
        
        # Break-even analysis
        breakeven_price = (total_costs / total_yield_kg) if total_yield_kg > 0 else 0
        breakeven_yield = (total_costs / selling_price_per_kg) if selling_price_per_kg > 0 else 0
        
        # Cost per kg
        cost_per_kg = (total_costs / total_yield_kg) if total_yield_kg > 0 else 0
        
        # Risk assessment
        risk_level = self._assess_profit_risk(profit_margin, roi)
        
        return {
            "crop": crop,
            "area_ha": area_ha,
            "expected_yield_tons": expected_yield_tons,
            "selling_price_per_kg": selling_price_per_kg,
            "costs": costs,
            "total_costs": total_costs,
            "cost_per_kg": cost_per_kg,
            "gross_revenue": gross_revenue,
            "net_profit": net_profit,
            "profit_margin_pct": profit_margin,
            "roi_pct": roi,
            "breakeven_price_per_kg": breakeven_price,
            "breakeven_yield_tons": breakeven_yield / 1000,
            "risk_level": risk_level,
            "recommendations": self._generate_profit_recommendations(
                profit_margin, roi, cost_per_kg, breakeven_price, selling_price_per_kg
            )
        }
    
    def _assess_profit_risk(self, profit_margin: float, roi: float) -> str:
        """Assess profitability risk level."""
        if profit_margin > 40 and roi > 50:
            return "low"
        elif profit_margin > 25 and roi > 30:
            return "moderate"
        elif profit_margin > 10 and roi > 15:
            return "high"
        else:
            return "very_high"
    
    def _generate_profit_recommendations(
        self,
        profit_margin: float,
        roi: float,
        cost_per_kg: float,
        breakeven_price: float,
        selling_price: float
    ) -> List[str]:
        """Generate profitability recommendations."""
        recommendations = []
        
        if profit_margin < 20:
            recommendations.append("Low profit margin - consider reducing production costs")
            recommendations.append("Explore value addition to increase selling price")
        
        if roi < 30:
            recommendations.append("Low ROI - review input efficiency and yields")
        
        price_premium = ((selling_price - breakeven_price) / breakeven_price * 100) if breakeven_price > 0 else 0
        if price_premium < 20:
            recommendations.append(f"Narrow safety margin ({price_premium:.1f}%) - minimize price risks")
        
        recommendations.append("Consider crop insurance to protect against losses")
        recommendations.append("Join farmer cooperatives for better input prices")
        recommendations.append("Implement precision farming to optimize input use")
        
        return recommendations
