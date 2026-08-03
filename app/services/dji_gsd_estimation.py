"""
Derives ground-sample-distance (cm of real ground covered by one pixel) from
a drone photo's own EXIF/XMP metadata, so canopy areas can be reported in
real m2 without the operator having to work it out and type it in.

Same contract as app.services.exif_gps.extract_gps_from_image_bytes: never
raises, and returns None rather than a guess whenever any required field is
missing, zero, or unparseable. A wrong GSD silently scales every area figure
in the system, so "unknown" is always the safer answer than "estimated".

    GSD_cm/px = (sensor_width_mm * altitude_m * 100) / (focal_length_mm * image_width_px)

Sensor width comes from EXIF FocalPlaneXResolution (pixels per
FocalPlaneResolutionUnit on the sensor), altitude from DJI's XMP
`drone-dji:RelativeAltitude` (height above the takeoff point - deliberately
NOT GPS absolute altitude, which is height above sea level and would produce
wildly wrong ground distances).

IMPORTANT - verify before relying on this in the field: which of these tags
DJI actually writes varies by model and firmware. Run
scripts/inspect_dji_metadata.py against one real photo from your aircraft to
confirm FocalLength / FocalPlane* / RelativeAltitude are present. If they
aren't, this returns None and area simply stays unavailable (see
app.services.canopy_vigor_assessment._pixel_area_m2) - nothing breaks, but
nothing is invented either.
"""

import io
import logging
import re
from typing import Optional

from PIL import Image

logger = logging.getLogger(__name__)

_FOCAL_LENGTH = 37386
_FOCAL_PLANE_X_RESOLUTION = 41486
_FOCAL_PLANE_RESOLUTION_UNIT = 41488

# XMP is an embedded plain-text segment, so RelativeAltitude is pulled
# straight out of the raw bytes instead of via Pillow's getxmp(): getxmp()
# silently returns nothing unless the optional `defusedxml` package is
# installed, which would make this whole feature quietly no-op on a machine
# that happens to lack it. Only one scalar attribute is needed, so a full
# XML parse (and the dependency it requires) buys nothing here - same
# stdlib-first reasoning as app.services.kml_mission_parser.
# DJI writes it as an attribute; some tools write it as an element instead.
_RELATIVE_ALTITUDE_PATTERNS = (
    re.compile(rb'RelativeAltitude\s*=\s*"([+-]?[0-9.]+)"'),
    re.compile(rb'<[^>]*RelativeAltitude>\s*([+-]?[0-9.]+)\s*<'),
)

# EXIF FocalPlaneResolutionUnit is an enum, not a free unit: how many
# millimetres one unit represents. 2=inch is what virtually every camera
# writes; 3=cm and 4=mm appear occasionally. 1 ("none") gives no scale at
# all, so it's deliberately absent - an unmapped value means "give up".
_RESOLUTION_UNIT_TO_MM = {2: 25.4, 3: 10.0, 4: 1.0}


def _relative_altitude_m(image_bytes: bytes) -> Optional[float]:
    """Height above the takeoff point, from the XMP block DJI embeds in the
    file. Returns None when absent or non-positive (a zero/negative height
    can't produce a meaningful ground distance)."""
    for pattern in _RELATIVE_ALTITUDE_PATTERNS:
        match = pattern.search(image_bytes)
        if match is None:
            continue
        # DJI writes it signed, e.g. "+37.60".
        altitude = float(match.group(1).decode("ascii").lstrip("+"))
        return altitude if altitude > 0 else None
    return None


def _sensor_width_mm(exif, image_width_px: int) -> Optional[float]:
    resolution = exif.get(_FOCAL_PLANE_X_RESOLUTION)
    unit = exif.get(_FOCAL_PLANE_RESOLUTION_UNIT)
    if resolution is None or unit is None:
        return None

    mm_per_unit = _RESOLUTION_UNIT_TO_MM.get(int(unit))
    if mm_per_unit is None:
        return None

    pixels_per_unit = float(resolution)
    if pixels_per_unit <= 0:
        return None

    # resolution is pixels-per-unit along the sensor's X axis, so the
    # sensor's physical width is the pixel count divided by that density.
    return image_width_px / pixels_per_unit * mm_per_unit


def estimate_ground_sampling_distance_cm(image_bytes: bytes) -> Optional[float]:
    """Returns cm-per-pixel, or None when the photo doesn't carry enough
    metadata to work it out. Never raises."""
    try:
        with Image.open(io.BytesIO(image_bytes)) as img:
            image_width_px = img.width
            if image_width_px <= 0:
                return None

            exif = img.getexif()
            if not exif:
                return None

            focal_length_mm = exif.get(_FOCAL_LENGTH)
            if focal_length_mm is None or float(focal_length_mm) <= 0:
                return None
            focal_length_mm = float(focal_length_mm)

            sensor_width_mm = _sensor_width_mm(exif, image_width_px)
            if sensor_width_mm is None or sensor_width_mm <= 0:
                return None

            altitude_m = _relative_altitude_m(image_bytes)
            if altitude_m is None:
                return None

            return (sensor_width_mm * altitude_m * 100.0) / (focal_length_mm * image_width_px)
    except Exception:
        logger.exception("Could not estimate ground-sample-distance from image metadata - area will stay unavailable")
        return None
