"""
Local-disk image storage - an alternative to AWSAIService.upload_to_s3 for
environments without real AWS credentials (e.g. local development/demos).
Writes real files to disk and returns a file:// URL, so the rest of the
pipeline (DroneImage.rgb_url/nir_url) behaves identically either way.
"""

import os

from app.config import settings


def save_image_locally(content: bytes, file_name: str, folder: str) -> str:
    target_dir = os.path.join(settings.DRONE_LOCAL_IMAGE_DIR, folder)
    os.makedirs(target_dir, exist_ok=True)

    path = os.path.join(target_dir, file_name)
    with open(path, "wb") as f:
        f.write(content)

    return f"file://{os.path.abspath(path)}"
