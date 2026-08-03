"""
Exercises app.services.canopy_overlay_rendering against synthetic RGB arrays
- no DB, no real imagery. Uses the same colour fixtures as
test_canopy_vigor_assessment.py so the two stay in step.
"""

import numpy as np

from app.services.canopy_overlay_rendering import render_vigor_overlay
from app.services.canopy_vigor_assessment import CanopyVigorAssessment, assess_canopy_vigor

_BROWN_SOIL = (30, 70, 110)  # BGR - reddish-brown, G is not dominant
_GREEN_CANOPY = (40, 160, 60)  # BGR - strong green dominance


def _solid_frame(color, size=(240, 240)) -> np.ndarray:
    frame = np.zeros((size[0], size[1], 3), dtype=np.uint8)
    frame[:, :] = color
    return frame


def _frame_with_green_square(square_frac=0.5, size=(240, 240)) -> np.ndarray:
    frame = _solid_frame(_BROWN_SOIL, size=size)
    side = int(size[0] * square_frac)
    frame[0:side, 0:side] = _GREEN_CANOPY
    return frame


def test_overlay_preserves_shape_and_does_not_mutate_the_input():
    frame = _frame_with_green_square()
    original = frame.copy()
    assessment = assess_canopy_vigor(frame)

    overlay = render_vigor_overlay(frame, assessment)

    assert overlay.shape == frame.shape
    assert np.array_equal(frame, original), "render_vigor_overlay must not mutate its input"


def test_overlay_actually_draws_something_on_a_vegetated_frame():
    frame = _frame_with_green_square()
    assessment = assess_canopy_vigor(frame)

    overlay = render_vigor_overlay(frame, assessment)

    assert not np.array_equal(overlay, frame), "expected boundary/labels to be drawn"


def test_bare_frame_still_returns_a_valid_image():
    frame = _solid_frame(_BROWN_SOIL)
    assessment = assess_canopy_vigor(frame)

    overlay = render_vigor_overlay(frame, assessment)

    # No canopy boundary to trace, but the summary label block is still drawn.
    assert overlay.shape == frame.shape
    assert overlay.dtype == frame.dtype


def test_fully_vegetated_frame_does_not_raise():
    frame = _solid_frame(_GREEN_CANOPY)
    assessment = assess_canopy_vigor(frame)

    overlay = render_vigor_overlay(frame, assessment)

    assert overlay.shape == frame.shape


def test_malformed_low_vigor_region_is_skipped_not_fatal():
    frame = _frame_with_green_square()
    assessment = CanopyVigorAssessment(
        coverage_pct=25.0,
        vigor_level="moderate",
        vigor_indicators=[],
        low_vigor_regions=[{"bbox": {"min_row": 0}}, {"not_a_bbox": True}],
    )

    overlay = render_vigor_overlay(frame, assessment)

    assert overlay.shape == frame.shape


def test_ground_sampling_distance_switches_labels_to_metres():
    frame = _frame_with_green_square()
    with_gsd = assess_canopy_vigor(frame, ground_sampling_distance_cm=10.0)
    without_gsd = assess_canopy_vigor(frame)

    metric_overlay = render_vigor_overlay(frame, with_gsd, ground_sampling_distance_cm=10.0)
    pixel_overlay = render_vigor_overlay(frame, without_gsd)

    # Different label text (m/acre vs px/"pixels only") means different pixels.
    assert not np.array_equal(metric_overlay, pixel_overlay)
    assert with_gsd.total_canopy_area_m2 is not None
    assert without_gsd.total_canopy_area_m2 is None


print("success")