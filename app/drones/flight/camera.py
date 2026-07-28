"""
Camera capture strategy for the drone survey pipeline. Produces
drone_orchard_system.multispectral_imaging.MultispectralImage objects, which
feed directly into MultispectralProcessor - no adapter/conversion layer needed.
"""

import logging
import os
import time
from abc import ABC, abstractmethod
from typing import List, Optional

import cv2
import numpy as np

from app.drones.flight import _console  # noqa: F401 - must run before any drone_orchard_system import

from drone_orchard_system.multispectral_imaging import MultispectralImage

from app.drones.flight.backend import Waypoint

logger = logging.getLogger(__name__)

__all__ = [
    "MultispectralImage", "CameraBackend", "SimulatedCameraBackend",
    "LocalFileCameraBackend", "RealCameraBackend",
    "green_channel_as_nir_placeholder",
]

_IMAGE_EXTENSIONS = (".png", ".jpg", ".jpeg")


def green_channel_as_nir_placeholder(rgb: np.ndarray) -> np.ndarray:
    """Clearly-approximate placeholder for a missing real NIR band - NOT a
    real near-infrared reading, NDVI computed from it is not trustworthy.
    Used by LocalFileCameraBackend below and by the manual DJI-ingestion
    upload endpoint (app/api/drones.py) when a caller doesn't supply a real
    NIR file, so the pipeline stays runnable either way."""
    return rgb[:, :, 1]  # green channel, BGR-indexed


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


class LocalFileCameraBackend(CameraBackend):
    """
    Reads real, pre-existing photos from a local directory instead of
    generating synthetic imagery - for demos using actual aerial photos.

    RGB source: any .png/.jpg/.jpeg file directly in `source_dir` (files
    ending in "_nir" are treated as NIR pairs, not RGB sources, and skipped).
    Files are cycled through round-robin, one per capture() call, since
    there's no fixed mapping between waypoints and specific photos.

    NIR pairing convention: for an RGB file "name.ext", a matching NIR band
    is looked up at "name_nir.ext" in the same directory. Add NIR imagery by
    dropping files named this way alongside their RGB counterparts - no code
    change needed, they'll be picked up automatically. Until a real NIR file
    exists for a given photo, this falls back to the RGB's green channel as
    a clearly-approximate placeholder (logged once per file), NOT a
    real near-infrared reading - NDVI computed from it is not trustworthy,
    it only keeps the pipeline runnable until real NIR imagery is added.
    """

    def __init__(self, source_dir: str):
        self.source_dir = source_dir
        self._rgb_files = self._list_rgb_files(source_dir)
        if not self._rgb_files:
            raise ValueError(f"No RGB image files found in {source_dir}")
        self._index = 0
        self._warned_missing_nir = set()

    @staticmethod
    def _list_rgb_files(source_dir: str) -> List[str]:
        files = []
        for name in sorted(os.listdir(source_dir)):
            stem, ext = os.path.splitext(name)
            if ext.lower() not in _IMAGE_EXTENSIONS:
                continue
            if stem.lower().endswith("_nir"):
                continue
            files.append(name)
        return files

    def _load_nir(self, rgb_filename: str, rgb: np.ndarray) -> np.ndarray:
        stem, ext = os.path.splitext(rgb_filename)
        nir_path = os.path.join(self.source_dir, f"{stem}_nir{ext}")

        if os.path.exists(nir_path):
            nir = cv2.imread(nir_path, cv2.IMREAD_GRAYSCALE)
            if nir is not None:
                return nir

        if rgb_filename not in self._warned_missing_nir:
            logger.warning(
                f"No NIR file found for '{rgb_filename}' (expected '{stem}_nir{ext}'). "
                "Falling back to the green channel as a placeholder - NDVI computed "
                "from this is not real near-infrared data."
            )
            self._warned_missing_nir.add(rgb_filename)

        return green_channel_as_nir_placeholder(rgb)

    async def capture(self, waypoint: Waypoint, altitude_m: float) -> MultispectralImage:
        filename = self._rgb_files[self._index % len(self._rgb_files)]
        self._index += 1

        rgb_path = os.path.join(self.source_dir, filename)
        rgb = cv2.imread(rgb_path)
        if rgb is None:
            raise ValueError(f"Failed to read image: {rgb_path}")

        nir = self._load_nir(filename, rgb)

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
