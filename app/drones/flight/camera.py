"""
Camera capture strategy for the drone survey pipeline. Produces
drone_orchard_system.multispectral_imaging.MultispectralImage objects, which
feed directly into MultispectralProcessor - no adapter/conversion layer needed.
"""

import time
from abc import ABC, abstractmethod
from typing import Optional

import numpy as np

from app.drones.flight import _console  # noqa: F401 - must run before any drone_orchard_system import

from drone_orchard_system.multispectral_imaging import MultispectralImage

from app.drones.flight.backend import Waypoint

__all__ = ["MultispectralImage", "CameraBackend", "SimulatedCameraBackend", "RealCameraBackend"]


class CameraBackend(ABC):
    @abstractmethod
    async def capture(self, waypoint: Waypoint, altitude_m: float) -> MultispectralImage:
        ...


class SimulatedCameraBackend(CameraBackend):
    """
    Generates small synthetic RGB+NIR patches biased toward healthy vegetation
    (high NIR, low red) so process_multispectral_image() yields a well-defined,
    positive mean NDVI rather than the NaN it returns when no pixel is positive
    (process_multispectral_image excludes non-positive-NDVI pixels from the mean).
    """

    def __init__(self, size: int = 64, seed: Optional[int] = None):
        self.size = size
        self._rng = np.random.default_rng(seed)

    async def capture(self, waypoint: Waypoint, altitude_m: float) -> MultispectralImage:
        # rgb is indexed BGR-style by MultispectralProcessor (rgb[:,:,2] is
        # treated as red), matching drone_orchard_system's own convention.
        blue = self._rng.integers(40, 120, (self.size, self.size), dtype=np.uint8)
        green = self._rng.integers(60, 140, (self.size, self.size), dtype=np.uint8)
        red = self._rng.integers(20, 90, (self.size, self.size), dtype=np.uint8)
        rgb = np.stack([blue, green, red], axis=-1)
        nir = self._rng.integers(150, 255, (self.size, self.size), dtype=np.uint8)

        return MultispectralImage(
            rgb=rgb,
            nir=nir,
            timestamp=time.time(),
            gps_latitude=waypoint.gps.latitude,
            gps_longitude=waypoint.gps.longitude,
            altitude=altitude_m,
            gimbal_pitch=waypoint.gimbal_pitch,
            ground_sampling_distance=3.0,
        )


class RealCameraBackend(CameraBackend):
    """
    Real multispectral camera capture. Not implemented - no physical camera or
    gimbal hardware has been chosen yet. Fill this in once hardware is picked.
    """

    async def capture(self, waypoint: Waypoint, altitude_m: float) -> MultispectralImage:
        raise NotImplementedError(
            "No physical camera/gimbal hardware is configured yet. "
            "RealCameraBackend.capture() must be implemented once hardware is chosen."
        )
    
print("success")
