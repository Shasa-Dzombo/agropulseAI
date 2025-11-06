"""
Predictive Harvest System
========================

Comprehensive harvest prediction integrating:
- Drone intelligence (plant count, NDVI, biomass)
- Ground sensors (soil moisture, EC, weather)
- Historical yield database
- Market demand forecasting
- Quality grading prediction
- Digital harvest certificates

Author: AgroPulse Team
Version: 1.0.0
"""

from .predictions import (
    YieldForecastEngine,
    QualityGradingPredictor,
    OnFieldGradingIntegration,
    MarketDemandForecaster,
    HarvestCertificateGenerator,
    HistoricalYieldDatabase,
    WeatherCorrelationEngine,
    OptimalHarvestPlanner
)

__all__ = [
    'YieldForecastEngine',
    'QualityGradingPredictor',
    'OnFieldGradingIntegration',
    'MarketDemandForecaster',
    'HarvestCertificateGenerator',
    'HistoricalYieldDatabase',
    'WeatherCorrelationEngine',
    'OptimalHarvestPlanner'
]

__version__ = '1.0.0'
