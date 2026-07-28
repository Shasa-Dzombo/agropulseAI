"""
Canopy vigor/coverage screening from plain RGB drone imagery.

Real, deterministic math (Excess Green Index thresholding + connected-component
region stats) - no ML, no model download, no external API. This is the free,
always-on counterpart to the opt-in, paid Kindwise diagnosis
(app.services.kindwise_disease_service): every manual-ingest or mission photo
gets a coverage/vigor read regardless of whether disease detection ran.

Deliberately stays in the same honest lane as
app.services.plant_stress_assessment: at typical drone survey altitude this
can flag *where canopy looks thin or absent* (a scouting cue) but cannot
diagnose disease, pests, or nutrient deficiency - do not read vigor_level or
vigor_indicators as a diagnosis.

"Regions" here are connected vegetation clusters detected within a single
photo, not pre-surveyed rectangular trial plots - real capture images are
oblique single-stand shots, not nadir grids of plots separated by tractor
tracks, so there is no plot grid to key off.
"""

from dataclasses import dataclass, field
from typing import Dict, List

import cv2
import numpy as np
from skimage.measure import label, regionprops

VIGOR_GOOD = "good"
VIGOR_MODERATE = "moderate"
VIGOR_LOW = "low"

_VIGOR_ORDER = [VIGOR_GOOD, VIGOR_MODERATE, VIGOR_LOW]

DEFAULT_EXG_THRESHOLD = 20
DEFAULT_MIN_REGION_AREA = 2000


@dataclass
class CanopyRegion:
    """One connected vegetation cluster detected within a photo."""
    bbox: Dict[str, int]  # {min_row, min_col, max_row, max_col}
    area_px: int
    coverage_pct: float  # % of this region's own bounding box that is vegetation
    centroid: Dict[str, float]  # {row, col}


@dataclass
class CanopyVigorAssessment:
    coverage_pct: float
    vigor_level: str
    vigor_indicators: List[str] = field(default_factory=list)
    low_vigor_regions: List[dict] = field(default_factory=list)


def _worse(a: str, b: str) -> str:
    return a if _VIGOR_ORDER.index(a) >= _VIGOR_ORDER.index(b) else b


def compute_exg_mask(rgb: np.ndarray, threshold: int = DEFAULT_EXG_THRESHOLD) -> np.ndarray:
    """Excess Green Index (2G-R-B) thresholded into a binary vegetation mask,
    cleaned with a morphological open+close. rgb is expected BGR or RGB
    uint8 (channel order doesn't matter for ExG - only relative green
    dominance does, and B/R only ever appear together, never distinguished)."""
    b = rgb[:, :, 0].astype(np.int16)
    g = rgb[:, :, 1].astype(np.int16)
    r = rgb[:, :, 2].astype(np.int16)

    exg = 2 * g - r - b
    mask = (exg > threshold).astype(np.uint8) * 255

    kernel = np.ones((5, 5), np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
    return mask


def find_canopy_regions(mask: np.ndarray, min_area: int = DEFAULT_MIN_REGION_AREA) -> List[CanopyRegion]:
    """Labels connected components in a vegetation mask and returns per-region
    stats for everything at or above min_area (filters out noise specks)."""
    labeled = label(mask > 0)
    regions: List[CanopyRegion] = []

    for props in regionprops(labeled):
        if props.area < min_area:
            continue

        min_row, min_col, max_row, max_col = props.bbox
        bbox_area = (max_row - min_row) * (max_col - min_col)
        coverage_pct = (props.area / bbox_area * 100.0) if bbox_area > 0 else 0.0

        regions.append(CanopyRegion(
            bbox={"min_row": min_row, "min_col": min_col, "max_row": max_row, "max_col": max_col},
            area_px=int(props.area),
            coverage_pct=coverage_pct,
            centroid={"row": props.centroid[0], "col": props.centroid[1]},
        ))

    return regions


def assess_canopy_vigor(
    rgb: np.ndarray,
    exg_threshold: int = DEFAULT_EXG_THRESHOLD,
    min_region_area: int = DEFAULT_MIN_REGION_AREA,
) -> CanopyVigorAssessment:
    """Never raises - a completely bare or completely green frame both produce
    a valid (if unremarkable) assessment rather than an error."""
    mask = compute_exg_mask(rgb, threshold=exg_threshold)
    total_pixels = mask.shape[0] * mask.shape[1]
    coverage_pct = float(np.count_nonzero(mask)) / total_pixels * 100.0 if total_pixels > 0 else 0.0

    level = VIGOR_GOOD
    indicators: List[str] = []

    if coverage_pct < 15.0:
        level = _worse(level, VIGOR_LOW)
        indicators.append(f"Low overall canopy coverage ({coverage_pct:.1f}%) - inspect for gaps or bare ground")
    elif coverage_pct < 35.0:
        level = _worse(level, VIGOR_MODERATE)
        indicators.append(f"Below-average canopy coverage ({coverage_pct:.1f}%)")

    regions = find_canopy_regions(mask, min_area=min_region_area)
    low_vigor_regions: List[dict] = []

    if len(regions) >= 4:
        # Bottom quartile by in-bbox coverage, flagged as "inspect" cues -
        # only meaningful once there are enough distinct clusters to rank.
        sorted_regions = sorted(regions, key=lambda r: r.coverage_pct)
        quartile_count = max(1, len(sorted_regions) // 4)
        for r in sorted_regions[:quartile_count]:
            low_vigor_regions.append({
                "bbox": r.bbox,
                "area_px": r.area_px,
                "coverage_pct": r.coverage_pct,
                "centroid": r.centroid,
            })
        indicators.append(
            f"{quartile_count} of {len(regions)} detected canopy region(s) fall in the bottom coverage "
            "quartile - inspect these areas"
        )

    return CanopyVigorAssessment(
        coverage_pct=coverage_pct,
        vigor_level=level,
        vigor_indicators=indicators,
        low_vigor_regions=low_vigor_regions,
    )
