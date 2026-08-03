"""
Renders a canopy-vigor assessment back onto the photo it came from: the
detected canopy boundary traced as a polygon, low-vigor areas boxed in red,
and a summary label block.

This is the visual counterpart to app.services.canopy_vigor_assessment's
numbers - same honesty contract (never raises, never fabricates), just drawn
instead of returned as JSON. Nothing here re-analyzes the image; it only
draws what the assessment already found.

Real-world distances/areas are only drawn when a ground-sample-distance is
supplied. Without one, edge lengths and area are labeled in pixels and the
label block says so explicitly - a pixel count is not a land measurement, and
silently omitting the distinction would let "1.2M" read as square meters.
"""

import logging
from typing import List, Optional, Tuple

import cv2
import numpy as np

from app.services.canopy_vigor_assessment import (
    DEFAULT_EXG_THRESHOLD,
    CanopyVigorAssessment,
    compute_exg_mask,
)

logger = logging.getLogger(__name__)

# BGR - cv2's channel order, matching how rgb arrays are handled throughout
# this pipeline (see canopy_vigor_assessment.compute_exg_mask).
_BOUNDARY_COLOR = (0, 255, 0)  # green - detected canopy boundary
_LOW_VIGOR_COLOR = (0, 0, 255)  # red - "inspect this" regions, per spec F2
_TEXT_COLOR = (255, 255, 255)
_TEXT_BACKGROUND = (0, 0, 0)

_FONT = cv2.FONT_HERSHEY_SIMPLEX
_SQUARE_METRES_PER_ACRE = 4046.856

# Above this many vertices the polygon is too complex for per-edge labels to
# be readable - the boundary still gets drawn, just without length labels.
_MAX_LABELLED_EDGES = 12

# Fraction of the image a contour must cover to be treated as real canopy
# boundary rather than an isolated speck worth outlining.
_MIN_BOUNDARY_AREA_FRACTION = 0.005

# Morphological-close kernel as a fraction of the frame's shorter side, used
# to merge separate crop rows into one planted region before tracing the
# field outline. Wide enough to span a typical inter-row gap at survey
# altitude without swallowing genuine field-edge concavity.
_ROW_GAP_BRIDGE_FRACTION = 0.06


def _scaled(image_width: int, base: float, minimum: float) -> float:
    """Font/line sizes that stay readable on both a 64px test fixture and a
    4000px real photo."""
    return max(minimum, base * image_width / 1600.0)


def _draw_label_block(canvas: np.ndarray, lines: List[str], font_scale: float, thickness: int) -> None:
    """Top-left stacked text with a filled backing box, so labels stay legible
    over both bright soil and dark canopy."""
    if not lines:
        return

    pad = max(4, int(6 * font_scale))
    line_height = int(28 * font_scale) + pad
    box_width = 0
    for line in lines:
        (text_width, _), _ = cv2.getTextSize(line, _FONT, font_scale, thickness)
        box_width = max(box_width, text_width)

    cv2.rectangle(
        canvas,
        (0, 0),
        (box_width + 2 * pad, line_height * len(lines) + pad),
        _TEXT_BACKGROUND,
        thickness=cv2.FILLED,
    )

    for i, line in enumerate(lines):
        baseline_y = line_height * (i + 1)
        cv2.putText(canvas, line, (pad, baseline_y), _FONT, font_scale, _TEXT_COLOR, thickness, cv2.LINE_AA)


def _field_boundary_polygons(mask: np.ndarray) -> List[np.ndarray]:
    """Outlines of every significant planted block, largest first, each
    simplified into a clean polygon. Empty when the frame has no meaningful
    vegetation at all.

    The mask is aggressively closed first: a row crop reads as dozens of
    disconnected strips, so tracing raw contours would outline individual
    rows rather than the block they form. Closing with a kernel wider than
    the inter-row gap merges rows back into a region, keeping the block's
    concave shape - which a convex hull would flatten away.

    Every qualifying block is returned, not just the biggest: the label
    block reports canopy area across the whole frame, so outlining one block
    while quoting a total covering several would make the picture and the
    number disagree.
    """
    # Proportional to the frame so it bridges row gaps at any resolution.
    gap_bridge = max(3, int(min(mask.shape[:2]) * _ROW_GAP_BRIDGE_FRACTION))
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (gap_bridge, gap_bridge))
    merged = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)

    contours, _ = cv2.findContours(merged, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return []

    minimum_area = mask.shape[0] * mask.shape[1] * _MIN_BOUNDARY_AREA_FRACTION
    significant = [c for c in contours if cv2.contourArea(c) >= minimum_area]
    significant.sort(key=cv2.contourArea, reverse=True)

    polygons = []
    for contour in significant:
        # 1% of perimeter - loose enough to collapse ragged leaf edges into
        # straight runs, tight enough to keep the block's actual shape.
        epsilon = 0.01 * cv2.arcLength(contour, closed=True)
        polygons.append(cv2.approxPolyDP(contour, epsilon, closed=True))
    return polygons


def _edge_length_label(
    start: Tuple[int, int], end: Tuple[int, int], ground_sampling_distance_cm: Optional[float]
) -> str:
    length_px = float(np.hypot(end[0] - start[0], end[1] - start[1]))
    if ground_sampling_distance_cm is None or ground_sampling_distance_cm <= 0:
        return f"{length_px:.0f}px"
    return f"{length_px * ground_sampling_distance_cm / 100.0:.1f}m"


def _draw_polygon_with_edge_labels(
    canvas: np.ndarray,
    polygon: np.ndarray,
    ground_sampling_distance_cm: Optional[float],
    font_scale: float,
    line_thickness: int,
    text_thickness: int,
    label_edges: bool = True,
) -> None:
    cv2.polylines(canvas, [polygon], isClosed=True, color=_BOUNDARY_COLOR, thickness=line_thickness)

    points = [tuple(point[0]) for point in polygon]
    if not label_edges or len(points) > _MAX_LABELLED_EDGES:
        return

    for i, start in enumerate(points):
        end = points[(i + 1) % len(points)]
        midpoint = ((start[0] + end[0]) // 2, (start[1] + end[1]) // 2)
        cv2.putText(
            canvas,
            _edge_length_label(start, end, ground_sampling_distance_cm),
            midpoint,
            _FONT,
            font_scale,
            _BOUNDARY_COLOR,
            text_thickness,
            cv2.LINE_AA,
        )


def _area_lines(assessment: CanopyVigorAssessment) -> List[str]:
    if assessment.total_canopy_area_m2 is None:
        return ["Area: pixels only (no ground-sample-distance supplied)"]
    acres = assessment.total_canopy_area_m2 / _SQUARE_METRES_PER_ACRE
    return [f"Canopy area: {assessment.total_canopy_area_m2:,.0f} m2 ({acres:.2f} acre)"]


def render_vigor_overlay(
    rgb: np.ndarray,
    assessment: CanopyVigorAssessment,
    exg_threshold: int = DEFAULT_EXG_THRESHOLD,
    ground_sampling_distance_cm: Optional[float] = None,
) -> np.ndarray:
    """Returns a new annotated copy of `rgb` - the input is never mutated.

    Never raises: a frame with no detectable vegetation still returns a valid
    image (the original, with just the summary labels), because a failed
    drawing step must not take down the ingest pipeline that calls this.
    """
    canvas = rgb.copy()
    try:
        image_width = canvas.shape[1]
        font_scale = _scaled(image_width, base=0.8, minimum=0.35)
        line_thickness = int(_scaled(image_width, base=3.0, minimum=1))
        text_thickness = int(_scaled(image_width, base=2.0, minimum=1))

        mask = compute_exg_mask(rgb, threshold=exg_threshold)
        polygons = _field_boundary_polygons(mask)
        for index, polygon in enumerate(polygons):
            # Edge lengths are labelled on the largest block only - repeating
            # them on every block turns a readable map into a wall of text.
            _draw_polygon_with_edge_labels(
                canvas, polygon, ground_sampling_distance_cm, font_scale,
                line_thickness, text_thickness, label_edges=(index == 0),
            )

        for region in assessment.low_vigor_regions:
            bbox = region.get("bbox") or {}
            try:
                top_left = (int(bbox["min_col"]), int(bbox["min_row"]))
                bottom_right = (int(bbox["max_col"]), int(bbox["max_row"]))
            except (KeyError, TypeError, ValueError):
                continue  # a malformed region shouldn't lose the whole overlay
            cv2.rectangle(canvas, top_left, bottom_right, _LOW_VIGOR_COLOR, line_thickness)

        lines = [
            f"Canopy coverage: {assessment.coverage_pct:.1f}%",
            f"Vigor: {assessment.vigor_level}",
        ]
        lines.extend(_area_lines(assessment))
        if assessment.low_vigor_regions:
            lines.append(f"Low-vigor areas flagged: {len(assessment.low_vigor_regions)} (red)")
        _draw_label_block(canvas, lines, font_scale, text_thickness)
    except Exception:
        logger.exception("Failed to render canopy vigor overlay - returning the unannotated frame")
        return rgb.copy()

    return canvas
