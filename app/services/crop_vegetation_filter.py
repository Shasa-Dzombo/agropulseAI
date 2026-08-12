"""
Separates sunlit crop canopy from deeply-shaded vegetation (tree canopy,
hedgerows, bush) inside an Excess-Green vegetation mask.

Why: ExG (app.services.canopy_vigor_assessment.compute_exg_mask) flags
anything green. On a frame that includes a treeline or hedge, "62% canopy
coverage" silently counts woodland as crop, and the vigor grade reads
better than the field actually is.

What this ACTUALLY does - read before trusting the numbers it produces:
it removes vegetation that is dark and strongly saturated relative to the
rest of the vegetation in the same frame. In a sunlit scene, dense tree and
hedge canopy self-shadows heavily and reads far darker than open crop, which
is what makes the split work. Measured on real survey frames from this
project, tree/hedge sat around V=66 (median) against V=114-120 for maize and
cabbage.

It is emphatically NOT a species or crop classifier. It cannot tell maize
from a weed mat, and it will misjudge:
  - crop lying in the shadow of a tree or building (wrongly excluded),
  - trees under flat overcast light, where nothing is strongly lit
    (wrongly kept),
  - imagery where the crop itself is the darkest vegetation present.

Texture was evaluated as a discriminator first and rejected: on the same
frames, local standard deviation came out at 31.3 (tree/hedge), 35.5
(maize) and 31.3 (cabbage) - no usable separation.

Because the effect is illumination-dependent, the threshold is derived per
frame (Otsu over the vegetation's own brightness) rather than hardcoded, and
is only applied when the frame really does contain two distinct brightness
populations. On a uniformly-lit frame it deliberately does nothing rather
than split a single population down the middle.
"""

import logging
from dataclasses import dataclass, field
from typing import List

import cv2
import numpy as np

logger = logging.getLogger(__name__)

# Minimum gap between the mean brightness of the dark and bright vegetation
# classes before the split is believed. Otsu always returns a threshold, even
# for a single population - without this guard a uniformly-lit crop would
# have its shadier half discarded as "trees".
_MIN_CLASS_SEPARATION_V = 35.0

# Shaded canopy is not just dark, it stays strongly coloured; dark *soil*
# and shadow on bare ground are far less saturated. Requiring both avoids
# eating shadowed soil that ExG already excluded anyway.
_MIN_SHADED_SATURATION = 100

# If the "shaded" class would swallow most of the vegetation, the assumption
# that it represents a background treeline is wrong - most likely the whole
# frame is shaded or is woodland. Leave the mask alone and say so.
_MAX_EXCLUDED_FRACTION = 0.60

# The decision is made per neighbourhood, not per pixel. Every crop canopy
# contains dark inter-leaf shadow, so excluding individual dark pixels
# strips shaded leaves out of perfectly healthy crop - measured at a 21
# percentage-point coverage loss on a real frame, most of it inside the
# maize rather than the hedge. Tree/hedge canopy differs by being *densely*
# shaded over a whole area, so shading is averaged over a window and only
# consistently-dark neighbourhoods are dropped.
_SHADE_WINDOW_FRACTION = 0.05  # of the frame's shorter side
# Measured on a real survey frame containing both a hedgerow and a maize
# block, varying this threshold (hedge removed / crop wrongly lost):
#   0.30 -> 78% / 53%      0.45 -> 54% / 16%
#   0.40 -> 62% / 29%      0.55 -> 43% /  2%
# There is no clean split - brightness cannot distinguish *sunlit* hedge
# foliage from crop, so removing more hedge always costs real crop. 0.55 is
# chosen as the precision end of that curve: it clears deep canopy shade
# while leaving the crop essentially intact, and accepts that roughly half
# the treeline survives. Lower it only if under-counting trees matters more
# than under-counting crop.
_MIN_LOCAL_SHADE_DENSITY = 0.55  # fraction of the window that must be shaded


@dataclass
class CropSeparation:
    """crop_mask is what should feed coverage/vigor; excluded_mask is what
    was treated as non-crop, kept so it can be drawn or audited rather than
    silently vanishing."""
    crop_mask: np.ndarray
    excluded_mask: np.ndarray
    applied: bool
    notes: List[str] = field(default_factory=list)

    @property
    def excluded_fraction(self) -> float:
        total = int(np.count_nonzero(self.crop_mask)) + int(np.count_nonzero(self.excluded_mask))
        if total == 0:
            return 0.0
        return float(np.count_nonzero(self.excluded_mask)) / total


def _empty_separation(mask: np.ndarray, note: str) -> CropSeparation:
    return CropSeparation(
        crop_mask=mask.copy(),
        excluded_mask=np.zeros_like(mask),
        applied=False,
        notes=[note],
    )


def separate_crop_from_shaded_canopy(rgb: np.ndarray, vegetation_mask: np.ndarray) -> CropSeparation:
    """Splits an existing vegetation mask into crop vs shaded-canopy.

    Never raises: on any failure the original mask is returned untouched with
    applied=False, so a filtering problem degrades the result to "unfiltered"
    rather than losing the analysis.
    """
    try:
        mask_bool = vegetation_mask > 0
        vegetation_pixels = int(np.count_nonzero(mask_bool))
        if vegetation_pixels == 0:
            return _empty_separation(vegetation_mask, "No vegetation to separate")

        hsv = cv2.cvtColor(rgb, cv2.COLOR_BGR2HSV)
        value = hsv[:, :, 2]
        saturation = hsv[:, :, 1]

        # Otsu over only the vegetation pixels - including soil would bias
        # the threshold toward separating plant-from-ground instead of
        # sunlit-from-shaded plant.
        vegetation_values = value[mask_bool].astype(np.uint8)
        threshold, _ = cv2.threshold(vegetation_values, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

        dark = mask_bool & (value <= threshold)
        bright = mask_bool & (value > threshold)
        if not dark.any() or not bright.any():
            return _empty_separation(vegetation_mask, "Vegetation brightness is single-peaked - no canopy layer to exclude")

        separation = float(value[bright].mean()) - float(value[dark].mean())
        if separation < _MIN_CLASS_SEPARATION_V:
            return _empty_separation(
                vegetation_mask,
                f"Vegetation is uniformly lit (brightness gap {separation:.0f} < {_MIN_CLASS_SEPARATION_V:.0f}) - "
                "nothing confidently identifiable as shaded canopy",
            )

        shaded_pixels = dark & (saturation >= _MIN_SHADED_SATURATION)

        # Promote the per-pixel judgement to a per-area one: a pixel is only
        # excluded when its neighbourhood is predominantly shaded, which is
        # true of tree/hedge canopy but not of shadow scattered between the
        # leaves of an otherwise sunlit crop.
        window = max(3, int(min(rgb.shape[:2]) * _SHADE_WINDOW_FRACTION) | 1)
        shade_density = cv2.blur(shaded_pixels.astype(np.float32), (window, window))
        excluded = mask_bool & (shade_density >= _MIN_LOCAL_SHADE_DENSITY)

        excluded_fraction = float(np.count_nonzero(excluded)) / vegetation_pixels
        if excluded_fraction > _MAX_EXCLUDED_FRACTION:
            return _empty_separation(
                vegetation_mask,
                f"Shaded vegetation is {excluded_fraction * 100:.0f}% of all vegetation - too much to be a "
                "background treeline, so the frame was left unfiltered",
            )

        crop = mask_bool & ~excluded
        notes = [
            f"Excluded {excluded_fraction * 100:.0f}% of vegetation as shaded canopy "
            f"(tree/hedge-like: brightness <= {int(threshold)}, gap {separation:.0f})"
        ]
        return CropSeparation(
            crop_mask=(crop.astype(np.uint8) * 255),
            excluded_mask=(excluded.astype(np.uint8) * 255),
            applied=True,
            notes=notes,
        )
    except Exception:
        logger.exception("Crop/shaded-canopy separation failed - falling back to the unfiltered vegetation mask")
        return _empty_separation(vegetation_mask, "Separation failed - using unfiltered vegetation")
