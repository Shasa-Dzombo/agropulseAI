"""
AgroPulse Vision Module

Advanced 3D vision, multispectral sensing, and computational photography
for agricultural diagnostics and monitoring.

Modules:
- multispectral: Virtual multispectral sensing and NDVI calculation
- photogrammetry: 3D reconstruction from multiple views
- super_resolution: AI-powered image enhancement and stacking
- multimodal_fusion: Multi-modal AI diagnostic fusion
- sentry: IoT CCTV-based monitoring system
- scout: Mobile NPU-powered capture system
- rendering: 3D visualization and rendering
- hardware: Hardware integration layer
"""

__version__ = "1.0.0"

from app.vision.multispectral import (
    MultispectralSensor,
    NDVICalculator,
    ChlorophyllAnalyzer,
    StressDetector
)

from app.vision.photogrammetry import (
    PhotogrammetryEngine,
    NeRFReconstructor,
    PointCloudGenerator,
    MeshReconstructor
)

__all__ = [
    "MultispectralSensor",
    "NDVICalculator",
    "ChlorophyllAnalyzer",
    "StressDetector",
    "PhotogrammetryEngine",
    "NeRFReconstructor",
    "PointCloudGenerator",
    "MeshReconstructor",
]
