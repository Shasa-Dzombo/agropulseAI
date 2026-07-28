"""
Converts a KML file's Placemarks into drone mission waypoints
(app.schemas.drone.WaypointIn shape) - a reference/briefing plan for a
manually-flown flight (there is no autonomous mission execution in this
system; both the simulated and real MAVLink flight backends were removed
since this project's actual hardware is flown manually via DJI's own app).

Uses only the stdlib xml.etree.ElementTree - no KML parsing library exists
anywhere else in this repo, and this only ever needs to read
Placemark/Point/coordinates, not write or round-trip full KML.

Each Placemark's <name>, when present, becomes that waypoint's tree_id -
app.services.drone_ai_service.ingest_captured_image() uses these to
auto-tag manually-flown photos by matching each photo's real GPS reading to
the nearest waypoint in the flight's mission_plan.

This is a one-way, reviewable conversion: it never creates a DroneFlight or
touches the DB itself. The caller (POST /drones/flights/parse-kml) hands the
parsed waypoints back to the user/frontend to review and edit before
attaching them as mission_plan on POST /drones/flights/manual.
"""

import xml.etree.ElementTree as ET
from typing import List, Tuple

_KML_NS = {"kml": "http://www.opengis.net/kml/2.2"}

_VALID_ACTIONS = {"fly_through", "hover", "take_photo", "rtl"}


def _find_all(root: ET.Element, tag: str) -> List[ET.Element]:
    """Namespace-tolerant find: tries the standard KML 2.2 namespace first,
    falls back to a bare tag search for KML files that omit/vary the
    namespace declaration."""
    found = root.findall(f".//kml:{tag}", _KML_NS)
    if found:
        return found
    return root.findall(f".//{tag}")


def _parse_coordinates_text(text: str) -> Tuple[float, float, float]:
    """KML coordinates are 'lon,lat[,alt]', optionally whitespace-padded.
    Raises ValueError on malformed input - caller decides whether to skip."""
    parts = text.strip().split(",")
    if len(parts) < 2:
        raise ValueError(f"Expected 'lon,lat[,alt]', got {text!r}")
    longitude = float(parts[0])
    latitude = float(parts[1])
    altitude = float(parts[2]) if len(parts) > 2 and parts[2].strip() else None
    return latitude, longitude, altitude


def parse_kml_waypoints(
    kml_bytes: bytes,
    action: str = "take_photo",
    default_altitude: float = 30.0,
    speed: float = 10.0,
    gimbal_pitch: float = -90.0,
) -> Tuple[List[dict], List[str]]:
    """Extracts one waypoint per Placemark>Point>coordinates, in document
    order. Placemarks without a parseable Point are skipped (not raised) and
    recorded as a warning - only an empty result for the whole file is an
    error, since a single bad placemark shouldn't block the rest of a real
    survey plan.

    Returns (waypoints, warnings) where each waypoint dict matches
    app.schemas.drone.WaypointIn's fields exactly.
    """
    if action not in _VALID_ACTIONS:
        raise ValueError(f"action must be one of {sorted(_VALID_ACTIONS)}, got {action!r}")

    try:
        root = ET.fromstring(kml_bytes)
    except ET.ParseError as e:
        raise ValueError(f"Could not parse KML: {e}") from e

    placemarks = _find_all(root, "Placemark")
    if not placemarks:
        raise ValueError("No <Placemark> elements found in KML file")

    waypoints: List[dict] = []
    warnings: List[str] = []

    for index, placemark in enumerate(placemarks):
        name_el = placemark.find("kml:name", _KML_NS)
        if name_el is None:
            name_el = placemark.find("name")
        real_name = name_el.text.strip() if name_el is not None and name_el.text and name_el.text.strip() else None
        label = real_name or f"placemark #{index}"

        coords_el = _find_all(placemark, "coordinates")
        if not coords_el or not coords_el[0].text:
            warnings.append(f"Skipped {label}: no <coordinates> found")
            continue

        # A Point has exactly one coordinate tuple; a LineString/Polygon may
        # have several - only the first vertex is used per placemark, since
        # one placemark maps to one waypoint here.
        first_tuple = coords_el[0].text.strip().split()[0]
        try:
            latitude, longitude, altitude = _parse_coordinates_text(first_tuple)
        except ValueError as e:
            warnings.append(f"Skipped {label}: {e}")
            continue

        waypoints.append({
            "latitude": latitude,
            "longitude": longitude,
            "altitude": altitude if altitude is not None else default_altitude,
            "action": action,
            "hover_time": 0.0,
            "speed": speed,
            "gimbal_pitch": gimbal_pitch,
            "photo_interval": 0.0,
            "tree_id": real_name,
        })

    if not waypoints:
        raise ValueError("No usable waypoints could be extracted from this KML file")

    return waypoints, warnings
