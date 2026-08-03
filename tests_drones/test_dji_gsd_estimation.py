"""
Exercises app.services.dji_gsd_estimation against synthetic JPEGs carrying
known EXIF + XMP values - no real DJI files needed. Mirrors
tests_drones/test_exif_gps.py's approach of building the metadata by hand so
the expected result is arithmetic, not a fixture nobody can verify.
"""

import io

import pytest
from PIL import Image

from app.services.dji_gsd_estimation import estimate_ground_sampling_distance_cm

_FOCAL_LENGTH = 37386
_FOCAL_PLANE_X_RESOLUTION = 41486
_FOCAL_PLANE_RESOLUTION_UNIT = 41488

_XMP_TEMPLATE = (
    '<?xpacket begin="" id="W5M0MpCehiHzreSzNTczkc9d"?>'
    '<x:xmpmeta xmlns:x="adobe:ns:meta/">'
    '<rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">'
    '<rdf:Description rdf:about="" xmlns:drone-dji="http://www.dji.com/drone-dji/1.0/" '
    'drone-dji:RelativeAltitude="{altitude}"/>'
    "</rdf:RDF></x:xmpmeta><?xpacket end='w'?>"
)


def _jpeg_with_metadata(
    width=4000,
    height=3000,
    focal_length_mm=8.8,
    focal_plane_x_resolution=None,
    resolution_unit=2,  # 2 = inch
    altitude="+50.00",
) -> bytes:
    """A 1:1-scaled-down image would change width, so the image is generated
    at the real pixel width the EXIF claims - width is part of the formula."""
    img = Image.new("RGB", (width, height), color=(20, 90, 60))

    exif = img.getexif()
    if focal_length_mm is not None:
        exif[_FOCAL_LENGTH] = focal_length_mm
    if focal_plane_x_resolution is not None:
        exif[_FOCAL_PLANE_X_RESOLUTION] = focal_plane_x_resolution
    if resolution_unit is not None:
        exif[_FOCAL_PLANE_RESOLUTION_UNIT] = resolution_unit

    kwargs = {"exif": exif}
    if altitude is not None:
        kwargs["xmp"] = _XMP_TEMPLATE.format(altitude=altitude).encode("utf-8")

    buf = io.BytesIO()
    img.save(buf, format="JPEG", **kwargs)
    return buf.getvalue()


def test_computes_gsd_from_focal_length_sensor_width_and_altitude():
    # 4000 px wide, 10160 px/inch -> sensor width = 4000/10160*25.4 = 10.0 mm.
    # GSD = (10.0mm * 50m * 100) / (8.8mm * 4000px) = 1.4204... cm/px
    image_bytes = _jpeg_with_metadata(
        width=4000, focal_length_mm=8.8, focal_plane_x_resolution=10160,
        resolution_unit=2, altitude="+50.00",
    )

    gsd = estimate_ground_sampling_distance_cm(image_bytes)

    assert gsd == pytest.approx(10.0 * 50.0 * 100.0 / (8.8 * 4000), rel=1e-3)


def test_higher_altitude_gives_proportionally_larger_gsd():
    low = estimate_ground_sampling_distance_cm(
        _jpeg_with_metadata(focal_plane_x_resolution=10160, altitude="+50.00")
    )
    high = estimate_ground_sampling_distance_cm(
        _jpeg_with_metadata(focal_plane_x_resolution=10160, altitude="+100.00")
    )

    assert low is not None and high is not None
    assert high == pytest.approx(low * 2.0, rel=1e-6)


def test_missing_altitude_returns_none():
    image_bytes = _jpeg_with_metadata(focal_plane_x_resolution=10160, altitude=None)

    assert estimate_ground_sampling_distance_cm(image_bytes) is None


def test_missing_focal_length_returns_none():
    image_bytes = _jpeg_with_metadata(focal_length_mm=None, focal_plane_x_resolution=10160)

    assert estimate_ground_sampling_distance_cm(image_bytes) is None


def test_missing_focal_plane_resolution_returns_none():
    image_bytes = _jpeg_with_metadata(focal_plane_x_resolution=None)

    assert estimate_ground_sampling_distance_cm(image_bytes) is None


def test_zero_focal_length_returns_none_rather_than_dividing_by_zero():
    image_bytes = _jpeg_with_metadata(focal_length_mm=0, focal_plane_x_resolution=10160)

    assert estimate_ground_sampling_distance_cm(image_bytes) is None


def test_unmapped_resolution_unit_returns_none():
    # 1 = "none", i.e. the density has no physical scale attached.
    image_bytes = _jpeg_with_metadata(focal_plane_x_resolution=10160, resolution_unit=1)

    assert estimate_ground_sampling_distance_cm(image_bytes) is None


def test_negative_altitude_returns_none():
    image_bytes = _jpeg_with_metadata(focal_plane_x_resolution=10160, altitude="-10.00")

    assert estimate_ground_sampling_distance_cm(image_bytes) is None


def test_plain_photo_with_no_metadata_returns_none():
    img = Image.new("RGB", (640, 480), color=(20, 90, 60))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")

    assert estimate_ground_sampling_distance_cm(buf.getvalue()) is None


def test_not_an_image_returns_none_not_raise():
    assert estimate_ground_sampling_distance_cm(b"this is not an image") is None
