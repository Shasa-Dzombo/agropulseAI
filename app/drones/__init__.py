"""
AgroPulse Drones Module

Drone intelligence, flight control, and aerial analytics for smart agriculture.

This module provides:
- Autonomous drone flight planning
- Plant counting and spacing analysis
- Multispectral imaging (NDVI, NDRE)
- Biomass estimation
- Harvest readiness mapping
- Digital twin generation
"""

__version__ = "1.0.0"

from .intelligence import (
    DroneController,
    PlantCounter,
    BiomassEstimator,
    MultispectralAnalyzer,
    HarvestMapper,
    DigitalTwin
)

__all__ = [
    'DroneController',
    'PlantCounter',
    'BiomassEstimator',
    'MultispectralAnalyzer',
    'HarvestMapper',
    'DigitalTwin'
]
