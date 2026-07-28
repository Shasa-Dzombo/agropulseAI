"""
Watches a local folder (e.g. where `adb pull` lands photos copied off a
DJI remote controller mid-flight) for new, fully-written DJI multispectral
captures, and POSTs each complete one to
POST /drones/flights/{flight_id}/images as soon as it's ready - the "active
side pushes to a passive backend" half of the manual DJI ground-ingestion
pipeline (see app/services/drone_ai_service.py's ingest_captured_image()).

Grouping is filename-stem based: DJI's companion consumer RGB JPG has no
band suffix (e.g. DJI_0001.JPG); band TIFFs are named
DJI_0001_MS_<BAND>.TIF, where BAND is one of G/R/RE/NIR (P4M) - this is
DJI's publicly documented P4M convention, NOT independently verified against
a real file in this repo, and Mavic 3M's naming may differ. Run
scripts/inspect_dji_metadata.py against a real file first and adjust
_BAND_SUFFIX_PATTERN/_NIR_BAND_NAMES/_RED_EDGE_BAND_NAMES below if your real
filenames don't match. Blue/Green/Red band files are intentionally ignored -
v1 uploads the companion RGB JPG directly instead of stacking calibrated
bands (see Addendum 6's "v1 image handling" note).

Usage:
    python scripts/watch_and_upload_dji_images.py \\
        --flight-id 42 \\
        --folder "C:\\Users\\you\\dji_pulls" \\
        --token "<bearer token from POST /auth/login>" \\
        [--api-base-url http://localhost:8030/api/v1] \\
        [--poll-interval 2.0]

Ctrl-C to stop. Safe to re-run: uploaded captures are recorded in
<folder>/.uploaded_stems.txt so they aren't re-uploaded on restart.
"""

import argparse
import os
import re
import sys
import time
from contextlib import ExitStack

import requests

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

_BAND_SUFFIX_PATTERN = re.compile(r"^(?P<stem>.+?)(?:_MS_(?P<band>[A-Za-z]+))?\.(?P<ext>[A-Za-z]+)$")
_NIR_BAND_NAMES = {"NIR"}
_RED_EDGE_BAND_NAMES = {"RE", "REDEDGE"}
_STABILITY_CHECKS = 2  # unchanged-size polls in a row before a file is considered fully written


def classify(filename: str):
    """Returns (stem, band) where band is 'rgb'/'nir'/'red_edge', or
    (stem, None) for a recognized-but-unused band (G/R/B), or (None, None)
    for anything unrecognized."""
    m = _BAND_SUFFIX_PATTERN.match(filename)
    if not m:
        return None, None
    stem = m.group("stem")
    band = m.group("band")
    ext = m.group("ext").lower()

    if band is None:
        if ext in ("jpg", "jpeg"):
            return stem, "rgb"
        return None, None

    band_upper = band.upper()
    if band_upper in _NIR_BAND_NAMES:
        return stem, "nir"
    if band_upper in _RED_EDGE_BAND_NAMES:
        return stem, "red_edge"
    return stem, None


def is_stable(path: str, checks: int, interval: float) -> bool:
    last_size = -1
    stable_count = 0
    while stable_count < checks:
        try:
            size = os.path.getsize(path)
        except OSError:
            return False
        stable_count = stable_count + 1 if size == last_size else 0
        last_size = size
        time.sleep(interval)
    return True


def load_uploaded_stems(marker_path: str) -> set:
    if not os.path.exists(marker_path):
        return set()
    with open(marker_path) as f:
        return {line.strip() for line in f if line.strip()}


def mark_uploaded(marker_path: str, stem: str) -> None:
    with open(marker_path, "a") as f:
        f.write(stem + "\n")


def upload_capture(api_base_url: str, token: str, flight_id: int, files: dict) -> None:
    url = f"{api_base_url}/drones/flights/{flight_id}/images"
    headers = {"Authorization": f"Bearer {token}"}

    with ExitStack() as stack:
        multipart = {}
        for field, key in (("rgb", "rgb"), ("nir", "nir"), ("red_edge", "red_edge")):
            if key in files:
                fh = stack.enter_context(open(files[key], "rb"))
                multipart[field] = (os.path.basename(files[key]), fh)
        response = requests.post(url, headers=headers, files=multipart, timeout=60)

    if response.status_code >= 400:
        print(f"  FAILED ({response.status_code}): {response.text}")
    else:
        print(f"  uploaded -> DroneImage id={response.json().get('id')}")


def scan_groups(folder: str) -> dict:
    groups = {}
    for name in os.listdir(folder):
        path = os.path.join(folder, name)
        if not os.path.isfile(path):
            continue
        stem, band = classify(name)
        if stem is None or band is None:
            continue
        groups.setdefault(stem, {})[band] = path
    return groups


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--flight-id", type=int, required=True)
    parser.add_argument("--folder", required=True)
    parser.add_argument("--token", required=True, help="Bearer token from POST /auth/login")
    parser.add_argument("--api-base-url", default="http://localhost:8030/api/v1")
    parser.add_argument("--poll-interval", type=float, default=2.0)
    args = parser.parse_args()

    marker_path = os.path.join(args.folder, ".uploaded_stems.txt")
    uploaded = load_uploaded_stems(marker_path)

    print(f"Watching {args.folder} for new DJI captures (flight_id={args.flight_id}) - Ctrl-C to stop.")
    try:
        while True:
            for stem, files in scan_groups(args.folder).items():
                if stem in uploaded or "rgb" not in files:
                    continue

                if not all(is_stable(p, _STABILITY_CHECKS, args.poll_interval) for p in files.values()):
                    continue  # still being written - retry next poll

                print(f"New capture: {stem} ({', '.join(sorted(files))})")
                try:
                    upload_capture(args.api_base_url, args.token, args.flight_id, files)
                except Exception as e:
                    print(f"  FAILED (exception): {e}")
                    continue

                mark_uploaded(marker_path, stem)
                uploaded.add(stem)

            time.sleep(args.poll_interval)
    except KeyboardInterrupt:
        print("Stopped.")


if __name__ == "__main__":
    main()
