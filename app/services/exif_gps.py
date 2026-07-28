"""
Real, standard EXIF GPS extraction (GPSLatitude/GPSLongitude/GPSAltitude and
their Ref tags - universal JPEG/TIFF EXIF, not a DJI-specific format) for the
manual drone-image-ingestion pipeline (app/services/drone_ai_service.py).
Unlike DJI's per-band calibration metadata, this tag set is well-documented
and safe to parse without first inspecting a real DJI file.
"""

import io
import logging
from dataclasses import dataclass
from typing import Optional

from PIL import ExifTags, Image

logger = logging.getLogger(__name__)


@dataclass
class GpsReading:
    latitude: float
    longitude: float
    altitude: Optional[float] = None


def _dms_to_decimal(dms, ref: str) -> float:
    degrees, minutes, seconds = (float(v) for v in dms)
    decimal = degrees + minutes / 60.0 + seconds / 3600.0
    if ref in ("S", "W"):
        decimal = -decimal
    return decimal


def extract_gps_from_image_bytes(image_bytes: bytes) -> Optional[GpsReading]:
    """Never raises - returns None when the file has no GPS EXIF block or
    can't be parsed as an image at all."""
    try:
        with Image.open(io.BytesIO(image_bytes)) as img:
            exif = img.getexif()
            if not exif:
                return None
            gps_ifd = exif.get_ifd(ExifTags.IFD.GPSInfo)
            if not gps_ifd:
                return None

            lat_dms = gps_ifd.get(2)  # GPSLatitude
            lat_ref = gps_ifd.get(1)  # GPSLatitudeRef
            lon_dms = gps_ifd.get(4)  # GPSLongitude
            lon_ref = gps_ifd.get(3)  # GPSLongitudeRef
            if not (lat_dms and lat_ref and lon_dms and lon_ref):
                return None

            latitude = _dms_to_decimal(lat_dms, lat_ref)
            longitude = _dms_to_decimal(lon_dms, lon_ref)

            altitude = None
            alt_value = gps_ifd.get(6)  # GPSAltitude
            if alt_value is not None:
                altitude = float(alt_value)
                # GPSAltitudeRef is an EXIF BYTE field - Pillow round-trips it
                # as bytes (b'\x01'), not int 1, so both forms need handling.
                alt_ref = gps_ifd.get(5)
                below_sea_level = alt_ref == 1 or alt_ref == b"\x01"
                if below_sea_level:
                    altitude = -altitude

            return GpsReading(latitude=latitude, longitude=longitude, altitude=altitude)
    except Exception:
        logger.exception("Failed to extract GPS EXIF from uploaded image - falling back to flight home coordinates")
        return None
