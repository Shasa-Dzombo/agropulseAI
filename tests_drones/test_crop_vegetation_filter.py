"""
Exercises app.services.crop_vegetation_filter against synthetic frames - no
DB, no real imagery. The scenarios mirror the real failure modes documented
in that module: a dark treeline beside sunlit crop (should separate), and a
uniformly-lit crop (must be left alone).
"""

import numpy as np

from app.services.canopy_vigor_assessment import assess_canopy_vigor, compute_exg_mask
from app.services.crop_vegetation_filter import separate_crop_from_shaded_canopy

_SUNLIT_CROP = (60, 190, 80)  # BGR - bright green
_SHADED_CANOPY = (25, 70, 30)  # BGR - dark, saturated green (tree/hedge)
_SOIL = (30, 70, 110)


def _frame(size=(400, 400)) -> np.ndarray:
    frame = np.zeros((size[0], size[1], 3), dtype=np.uint8)
    frame[:, :] = _SOIL
    return frame


def test_dark_canopy_band_is_separated_from_sunlit_crop():
    frame = _frame()
    frame[0:120, :] = _SHADED_CANOPY  # treeline across the top
    frame[160:400, :] = _SUNLIT_CROP  # crop below it

    result = separate_crop_from_shaded_canopy(frame, compute_exg_mask(frame))

    assert result.applied is True
    assert result.excluded_fraction > 0.1
    # The excluded pixels should sit in the treeline band, not the crop.
    assert result.excluded_mask[0:120, :].sum() > result.excluded_mask[160:400, :].sum()


def test_uniformly_lit_crop_is_left_untouched():
    frame = _frame()
    frame[50:350, :] = _SUNLIT_CROP  # one brightness population, no canopy

    mask = compute_exg_mask(frame)
    result = separate_crop_from_shaded_canopy(frame, mask)

    assert result.applied is False
    assert np.array_equal(result.crop_mask, mask)
    assert result.excluded_mask.sum() == 0
    assert any("uniform" in n.lower() or "single-peaked" in n.lower() for n in result.notes)


def test_frame_with_no_vegetation_is_handled():
    frame = _frame()

    result = separate_crop_from_shaded_canopy(frame, compute_exg_mask(frame))

    assert result.applied is False
    assert result.excluded_fraction == 0.0


def test_mostly_shaded_frame_refuses_to_filter():
    """Woodland, not a crop field with a treeline - excluding most of the
    vegetation would be wrong, so it must decline and say why."""
    frame = _frame()
    frame[:, :] = _SHADED_CANOPY
    frame[380:400, :] = _SUNLIT_CROP  # a sliver of brightness

    result = separate_crop_from_shaded_canopy(frame, compute_exg_mask(frame))

    assert result.applied is False
    assert np.count_nonzero(result.excluded_mask) == 0


def test_assess_canopy_vigor_flag_lowers_coverage_when_canopy_present():
    frame = _frame()
    frame[0:120, :] = _SHADED_CANOPY
    frame[160:400, :] = _SUNLIT_CROP

    unfiltered = assess_canopy_vigor(frame)
    filtered = assess_canopy_vigor(frame, exclude_shaded_canopy=True)

    assert filtered.coverage_pct < unfiltered.coverage_pct
    assert any("shaded canopy" in i.lower() for i in filtered.vigor_indicators)


def test_assess_canopy_vigor_flag_defaults_off():
    frame = _frame()
    frame[0:120, :] = _SHADED_CANOPY
    frame[160:400, :] = _SUNLIT_CROP

    assert assess_canopy_vigor(frame).coverage_pct == assess_canopy_vigor(
        frame, exclude_shaded_canopy=False
    ).coverage_pct
