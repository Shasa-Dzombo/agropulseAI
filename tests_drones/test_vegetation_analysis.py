"""
Exercises drone_orchard_system.multispectral_imaging's real NDVI/GNDVI/SAVI/EVI
math against synthetic inputs - not a mock, actual formula evaluation.

Note: MultispectralProcessor.process_multispectral_image() computes
mean_ndvi = np.mean(ndvi[ndvi > 0]) - it excludes non-positive pixels from
the mean by design ("exclude non-vegetation"). That means a uniformly
low-NIR/high-red ("stressed") image yields NaN through that path, not a
real negative number - so the negative-NDVI case below is tested against
calculate_ndvi() directly (the raw per-pixel formula), and the full
process_multispectral_image() pipeline is exercised with a healthy image,
matching what SimulatedCameraBackend actually produces.
"""

import math

import numpy as np

from app.drones.flight.camera import SimulatedCameraBackend
from app.drones.flight.backend import GPSCoordinate, Waypoint
from app.services.drone_ai_service import _safe_float
from drone_orchard_system.multispectral_imaging import MultispectralImage, MultispectralProcessor, TreeHealthStatus


def test_calculate_ndvi_healthy_patch_is_strongly_positive():
    processor = MultispectralProcessor()
    nir = np.full((16, 16), 200, dtype=np.uint8)
    red = np.full((16, 16), 20, dtype=np.uint8)

    ndvi = processor.calculate_ndvi(nir, red)

    assert float(np.mean(ndvi)) > 0.5


def test_calculate_ndvi_stressed_patch_is_negative():
    processor = MultispectralProcessor()
    nir = np.full((16, 16), 20, dtype=np.uint8)
    red = np.full((16, 16), 200, dtype=np.uint8)

    ndvi = processor.calculate_ndvi(nir, red)

    assert float(np.mean(ndvi)) < 0


async def test_process_multispectral_image_on_healthy_synthetic_capture():
    processor = MultispectralProcessor()
    camera = SimulatedCameraBackend(size=32, seed=42)
    waypoint = Waypoint(gps=GPSCoordinate(37.77, -122.4, 30.0), action="take_photo", waypoint_id=0)

    image = await camera.capture(waypoint, altitude_m=30.0)
    indices = processor.process_multispectral_image(image)

    assert not math.isnan(indices.ndvi)
    assert indices.ndvi > 0.3
    assert indices.get_health_status() in (TreeHealthStatus.HEALTHY, TreeHealthStatus.MILD_STRESS)


def test_process_multispectral_image_returns_nan_when_no_vegetation_detected():
    """Documents the reused function's real edge-case behavior: an image with
    no positive-NDVI pixels produces NaN, not a negative number - this is why
    the service layer's _safe_float() guard exists."""
    processor = MultispectralProcessor()
    size = 8
    rgb = np.zeros((size, size, 3), dtype=np.uint8)
    rgb[:, :, 2] = 200  # red channel high
    nir = np.full((size, size), 10, dtype=np.uint8)  # NIR low everywhere

    image = MultispectralImage(rgb=rgb, nir=nir, gps_latitude=0, gps_longitude=0, altitude=30.0)
    indices = processor.process_multispectral_image(image)

    assert math.isnan(indices.ndvi)
    assert _safe_float(indices.ndvi) is None


def test_safe_float_passes_through_real_values():
    assert _safe_float(0.42) == 0.42
    assert _safe_float(-0.1) == -0.1
