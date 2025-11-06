"""
AgroPulse Sensors Module

Ground sensors, edge computing, and IoT systems for smart agriculture.

This module provides:
- DIY low-cost sensor hardware
- Edge computing and data compression
- Local calibration systems
- Real-time environmental monitoring
"""

__version__ = "1.0.0"

from .diy_hardware import (
    MoistureSensor,
    ECSensor,
    TemperatureSensor,
    AcousticSensor,
    CalibrationSystem
)

__all__ = [
    'MoistureSensor',
    'ECSensor',
    'TemperatureSensor',
    'AcousticSensor',
    'CalibrationSystem'
]
