"""
Exercises app.services.exif_gps.extract_gps_from_image_bytes against real
Pillow-written JPEG EXIF - standard GPS EXIF tags, not a DJI-specific format.
"""

import io

import pytest
from PIL import Image

from app.services.exif_gps import extract_gps_from_image_bytes

_GPS_INFO_TAG = 34853


def _jpeg_bytes_with_gps(gps_ifd=None) -> bytes:
    img = Image.new("RGB", (4, 4), color=(10, 20, 30))
    save_kwargs = {}
    if gps_ifd is not None:
        exif = img.getexif()
        exif[_GPS_INFO_TAG] = gps_ifd
        save_kwargs["exif"] = exif
    buf = io.BytesIO()
    img.save(buf, format="JPEG", **save_kwargs)
    return buf.getvalue()


def test_extracts_northern_eastern_hemisphere_gps():
    data = _jpeg_bytes_with_gps({1: "N", 2: (37.0, 46.0, 12.0), 3: "E", 4: (122.0, 25.0, 12.0)})

    reading = extract_gps_from_image_bytes(data)

    assert reading is not None
    assert reading.latitude == pytest.approx(37 + 46 / 60 + 12 / 3600)
    assert reading.longitude == pytest.approx(122 + 25 / 60 + 12 / 3600)


def test_southern_western_hemisphere_produces_negative_coordinates():
    data = _jpeg_bytes_with_gps({1: "S", 2: (1.0, 0.0, 0.0), 3: "W", 4: (36.0, 0.0, 0.0)})

    reading = extract_gps_from_image_bytes(data)

    assert reading.latitude == pytest.approx(-1.0)
    assert reading.longitude == pytest.approx(-36.0)


def test_extracts_altitude_when_present():
    data = _jpeg_bytes_with_gps({1: "N", 2: (0.0, 0.0, 0.0), 3: "E", 4: (0.0, 0.0, 0.0), 5: 0, 6: 1583.4})

    reading = extract_gps_from_image_bytes(data)

    assert reading.altitude == pytest.approx(1583.4)


def test_below_sea_level_altitude_is_negative():
    data = _jpeg_bytes_with_gps({1: "N", 2: (0.0, 0.0, 0.0), 3: "E", 4: (0.0, 0.0, 0.0), 5: 1, 6: 10.0})

    reading = extract_gps_from_image_bytes(data)

    assert reading.altitude == pytest.approx(-10.0)


def test_no_gps_block_returns_none():
    data = _jpeg_bytes_with_gps(gps_ifd=None)

    assert extract_gps_from_image_bytes(data) is None


def test_not_an_image_returns_none_not_raise():
    assert extract_gps_from_image_bytes(b"not a real image") is None
