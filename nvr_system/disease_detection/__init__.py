"""
Disease Detection Module for Greenhouse Horticulture

Comprehensive computer vision-based disease detection system for controlled
environment agriculture. Supports major fungal, bacterial, and viral diseases
affecting greenhouse crops.

Modules:
- powdery_mildew_detector: Powdery mildew (multiple pathogens) ✅
- botrytis_detector: Gray mold (Botrytis cinerea) ✅
- downy_mildew_detector: Downy mildew (Peronospora spp.) ✅
- bacterial_spot_detector: Bacterial spot/speck (Xanthomonas, Pseudomonas) [Coming Soon]
- fusarium_wilt_detector: Vascular wilt diseases [Coming Soon]
- viral_symptom_detector: TMV, TYLCV, CMV, PepMV [Coming Soon]
- root_rot_detector: Pythium, Phytophthora (hydroponic systems) [Coming Soon]
- anthracnose_detector: Colletotrichum spp. [Coming Soon]

Author: AgroPulse Greenhouse Vision Team
Date: November 3, 2025
"""

from .powdery_mildew_detector import (
    PowderyMildewDetector,
    MildewStage,
    GreenhouseCrop,
    TreatmentAction,
    MildewColony,
    MildewInfectionZone,
    MildewTreatmentPlan,
    PowderyMildewDetectionResult
)

from .botrytis_detector import (
    BotrytisDetector,
    BotrytisStage,
    InfectionSite,
    TreatmentUrgency,
    BotrytisLesion,
    BotrytisCluster,
    EnvironmentalRisk,
    BotytisTreatmentPlan,
    BotrytisDetectionResult
)

from .downy_mildew_detector import (
    DownyMildewDetector,
    DownyMildewStage,
    SporulationColor,
    DownyMildewPathogen,
    LeafSurface,
    AngularLesion,
    SporulationZone,
    SystemicInfection,
    DownyMildewCluster,
    EnvironmentalRiskFactors,
    DownyMildewTreatmentPlan,
    DownyMildewDetectionResult
)

__all__ = [
    # Powdery Mildew
    "PowderyMildewDetector",
    "MildewStage",
    "GreenhouseCrop",
    "TreatmentAction",
    "MildewColony",
    "MildewInfectionZone",
    "MildewTreatmentPlan",
    "PowderyMildewDetectionResult",
    # Botrytis Gray Mold
    "BotrytisDetector",
    "BotrytisStage",
    "InfectionSite",
    "TreatmentUrgency",
    "BotrytisLesion",
    "BotrytisCluster",
    "EnvironmentalRisk",
    "BotytisTreatmentPlan",
    "BotrytisDetectionResult",
    # Downy Mildew
    "DownyMildewDetector",
    "DownyMildewStage",
    "SporulationColor",
    "DownyMildewPathogen",
    "LeafSurface",
    "AngularLesion",
    "SporulationZone",
    "SystemicInfection",
    "DownyMildewCluster",
    "EnvironmentalRiskFactors",
    "DownyMildewTreatmentPlan",
    "DownyMildewDetectionResult",
]

__version__ = "2.1.0"
__author__ = "AgroPulse Greenhouse Vision Team"
