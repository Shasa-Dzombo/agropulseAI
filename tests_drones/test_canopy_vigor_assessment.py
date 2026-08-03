"""
Exercises app.services.canopy_vigor_assessment's ExG threshold/region logic
directly against synthetic RGB arrays - no DB, no real imagery.
"""

import numpy as np
import pytest

from app.services.canopy_vigor_assessment import (
    VIGOR_GOOD,
    VIGOR_LOW,
    VIGOR_MODERATE,
    assess_canopy_vigor,
    compute_exg_mask,
    find_canopy_regions,
)

_BROWN_SOIL = (30, 70, 110)  # BGR - reddish-brown, G is not dominant
_GREEN_CANOPY = (40, 160, 60)  # BGR - strong green dominance


def _solid_frame(color, size=(120, 120)) -> np.ndarray:
    frame = np.zeros((size[0], size[1], 3), dtype=np.uint8)
    frame[:, :] = color
    return frame


def _frame_with_green_square(square_frac=0.5, size=(120, 120)) -> np.ndarray:
    frame = _solid_frame(_BROWN_SOIL, size=size)
    side = int(size[0] * square_frac)
    frame[0:side, 0:side] = _GREEN_CANOPY
    return frame


def test_all_soil_frame_has_near_zero_coverage_and_low_vigor():
    frame = _solid_frame(_BROWN_SOIL)

    result = assess_canopy_vigor(frame)

    assert result.coverage_pct < 5.0
    assert result.vigor_level == VIGOR_LOW
    assert any("coverage" in i.lower() for i in result.vigor_indicators)


def test_all_canopy_frame_has_near_full_coverage_and_good_vigor():
    frame = _solid_frame(_GREEN_CANOPY)

    result = assess_canopy_vigor(frame)

    assert result.coverage_pct > 90.0
    assert result.vigor_level == VIGOR_GOOD
    assert result.vigor_indicators == []


def test_partial_canopy_frame_falls_between_the_extremes():
    frame = _frame_with_green_square(square_frac=0.5)

    result = assess_canopy_vigor(frame)

    assert 15.0 < result.coverage_pct < 35.0
    assert result.vigor_level == VIGOR_MODERATE


def test_compute_exg_mask_flags_green_pixels_not_brown_ones():
    frame = _frame_with_green_square(square_frac=0.5)

    mask = compute_exg_mask(frame)

    assert mask[10, 10] > 0  # inside the green square
    assert mask[100, 100] == 0  # outside it, in the brown soil


def test_find_canopy_regions_reports_bbox_and_area_for_a_single_cluster():
    frame = _frame_with_green_square(square_frac=0.5, size=(200, 200))
    mask = compute_exg_mask(frame)

    regions = find_canopy_regions(mask, min_area=100)

    assert len(regions) == 1
    region = regions[0]
    assert region.area_px > 0
    assert region.coverage_pct > 50.0
    assert region.bbox["min_row"] == 0
    assert region.bbox["min_col"] == 0


def test_find_canopy_regions_filters_out_small_noise_specks():
    frame = _solid_frame(_BROWN_SOIL, size=(50, 50))
    frame[5:7, 5:7] = _GREEN_CANOPY  # tiny 2x2 speck

    mask = compute_exg_mask(frame)
    regions = find_canopy_regions(mask, min_area=2000)

    assert regions == []


def test_area_m2_is_none_without_a_ground_sampling_distance():
    frame = _frame_with_green_square(square_frac=0.5, size=(200, 200))

    result = assess_canopy_vigor(frame)

    assert result.total_canopy_area_m2 is None
    mask = compute_exg_mask(frame)
    assert find_canopy_regions(mask, min_area=100)[0].area_m2 is None


def test_area_m2_is_computed_from_a_supplied_ground_sampling_distance():
    frame = _frame_with_green_square(square_frac=0.5, size=(200, 200))
    mask = compute_exg_mask(frame)
    veg_pixels = int(np.count_nonzero(mask))

    # 10 cm/px -> 0.1 m/px -> 0.01 m^2 per pixel.
    result = assess_canopy_vigor(frame, ground_sampling_distance_cm=10.0)

    assert result.total_canopy_area_m2 == pytest.approx(veg_pixels * 0.01, rel=1e-6)
    regions = find_canopy_regions(mask, min_area=100, pixel_area_m2=0.01)
    assert regions[0].area_m2 == pytest.approx(regions[0].area_px * 0.01, rel=1e-6)
