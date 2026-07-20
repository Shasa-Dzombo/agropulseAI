"""
Exercises app.services.plant_stress_assessment's index-threshold logic
directly against hand-built VegetationIndices - no DB, no external API,
pure function behavior.
"""

from app.services.plant_stress_assessment import (
    assess_plant_stress, STRESS_HEALTHY, STRESS_SEVERE,
)
from drone_orchard_system.multispectral_imaging import VegetationIndices


def test_healthy_indices_produce_no_stress_indicators():
    indices = VegetationIndices(ndvi=0.75, gndvi=0.6, ndre=0.35, savi=0.7, evi=0.5)

    result = assess_plant_stress(indices)

    assert result.stress_level == STRESS_HEALTHY
    assert result.stress_indicators == []


def test_low_ndvi_and_ndre_produce_severe_stress_with_reasons():
    indices = VegetationIndices(ndvi=0.15, gndvi=0.2, ndre=0.10, savi=0.18, evi=0.1)

    result = assess_plant_stress(indices)

    assert result.stress_level == STRESS_SEVERE
    assert any("NDVI" in reason for reason in result.stress_indicators)
    assert any("nitrogen" in reason.lower() for reason in result.stress_indicators)


def test_sparse_canopy_vs_water_stress_distinction():
    """Low NDVI but SAVI (soil-corrected) notably higher suggests sparse
    canopy/soil background rather than genuine water stress - real,
    established remote-sensing interpretation, not an invented heuristic."""
    indices = VegetationIndices(ndvi=0.25, gndvi=0.3, ndre=0.28, savi=0.45, evi=0.3)

    result = assess_plant_stress(indices)

    assert any("sparse canopy" in reason.lower() or "soil background" in reason.lower() for reason in result.stress_indicators)


def test_never_raises_on_nan_index_values():
    indices = VegetationIndices(ndvi=float("nan"), gndvi=float("nan"), ndre=float("nan"), savi=float("nan"), evi=float("nan"))

    result = assess_plant_stress(indices)

    assert result.stress_level == STRESS_HEALTHY
    assert result.stress_indicators == []
