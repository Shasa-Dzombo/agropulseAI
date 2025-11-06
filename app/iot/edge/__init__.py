"""
Edge Computing Module for AgroPulse IoT Platform

Provides edge AI inference, sensor fusion, predictive maintenance,
and local data processing capabilities for IoT devices.
"""

from .inference_engine import EdgeInferenceEngine, ModelRegistry
from .sensor_fusion import SensorFusionEngine, KalmanFilter
from .predictive_maintenance import PredictiveMaintenanceEngine
from .fleet_manager import FleetManager, DeviceOrchestrator
from .ota_updater import OTAUpdateManager, FirmwareValidator
from .edge_analytics import EdgeAnalyticsEngine, LocalAggregator
from .mesh_network import MeshNetworkManager, RoutingProtocol

__all__ = [
    'EdgeInferenceEngine',
    'ModelRegistry',
    'SensorFusionEngine',
    'KalmanFilter',
    'PredictiveMaintenanceEngine',
    'FleetManager',
    'DeviceOrchestrator',
    'OTAUpdateManager',
    'FirmwareValidator',
    'EdgeAnalyticsEngine',
    'LocalAggregator',
    'MeshNetworkManager',
    'RoutingProtocol',
]

__version__ = '1.0.0'
