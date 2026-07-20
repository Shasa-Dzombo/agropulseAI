"""
Plant stress assessment from multispectral vegetation indices.

This is index-threshold reasoning over real, already-computed NDVI/GNDVI/
NDRE/SAVI/EVI values (from drone_orchard_system.multispectral_imaging) - NOT
a trained model. It combines several indices instead of NDVI alone, using
standard, well-established remote-sensing interpretations:

- NDVI: overall vegetation vigor/canopy density.
- NDRE: more sensitive to chlorophyll/nitrogen content than NDVI (uses the
  red-edge band) - a common indicator of nitrogen deficiency.
- SAVI: corrects for soil background reflectance, useful for distinguishing
  genuine canopy stress from naturally sparse canopy (soil showing through).

Deliberately excludes anything resembling drone_orchard_system's disease/
weed/yield modules (random.choice stubs, untrained neural nets) - this stays
honest about being a coarse heuristic, not a diagnosis.
"""

from dataclasses import dataclass, field
from typing import List

from app.drones.flight import _console  # noqa: F401 - must run before any drone_orchard_system import
from drone_orchard_system.multispectral_imaging import VegetationIndices

STRESS_HEALTHY = "healthy"
STRESS_MILD = "mild_stress"
STRESS_MODERATE = "moderate_stress"
STRESS_SEVERE = "severe_stress"

_STRESS_ORDER = [STRESS_HEALTHY, STRESS_MILD, STRESS_MODERATE, STRESS_SEVERE]


@dataclass
class StressAssessment:
    stress_level: str
    stress_indicators: List[str] = field(default_factory=list)


def _worse(a: str, b: str) -> str:
    return a if _STRESS_ORDER.index(a) >= _STRESS_ORDER.index(b) else b


def assess_plant_stress(indices: VegetationIndices) -> StressAssessment:
    """Combines NDVI/NDRE/SAVI thresholds into a coarse stress classification.
    Never raises - out-of-range/NaN index values are treated as "no signal"
    for that index rather than an error."""
    level = STRESS_HEALTHY
    reasons: List[str] = []

    ndvi = indices.ndvi
    ndre = indices.ndre
    savi = indices.savi

    if ndvi == ndvi:  # not NaN
        if ndvi < 0.2:
            level = _worse(level, STRESS_SEVERE)
            reasons.append(f"Low NDVI ({ndvi:.2f}) - general vigor loss or bare canopy")
        elif ndvi < 0.4:
            level = _worse(level, STRESS_MODERATE)
            reasons.append(f"Below-average NDVI ({ndvi:.2f}) - reduced vegetation vigor")
        elif ndvi < 0.55:
            level = _worse(level, STRESS_MILD)
            reasons.append(f"Slightly low NDVI ({ndvi:.2f})")

    if ndre == ndre:  # not NaN
        if ndre < 0.15:
            level = _worse(level, STRESS_MODERATE)
            reasons.append(f"Low NDRE ({ndre:.2f}) - possible nitrogen/chlorophyll deficiency")
        elif ndre < 0.25:
            level = _worse(level, STRESS_MILD)
            reasons.append(f"Below-average NDRE ({ndre:.2f}) - watch for early nitrogen deficiency")

    # If NDVI reads low but SAVI (soil-corrected) is comparatively higher,
    # the signal is more likely sparse/young canopy than genuine stress -
    # note it but don't escalate further on NDVI alone.
    if ndvi == ndvi and savi == savi and ndvi < 0.4 and savi - ndvi > 0.1:
        reasons.append(
            f"NDVI ({ndvi:.2f}) low relative to SAVI ({savi:.2f}) - "
            "may indicate sparse canopy/soil background rather than water stress"
        )

    return StressAssessment(stress_level=level, stress_indicators=reasons)
