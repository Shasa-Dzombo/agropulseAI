"""
Exercises app.services.kml_mission_parser directly (no DB) and the
POST /drones/flights/parse-kml endpoint (via the shared client/auth_headers
fixtures in tests_drones/conftest.py).
"""

import pytest

from app.services.kml_mission_parser import parse_kml_waypoints

_VALID_KML = b"""<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
  <Document>
    <Placemark>
      <name>WP1</name>
      <Point><coordinates>36.821946,-1.292066,0</coordinates></Point>
    </Placemark>
    <Placemark>
      <name>WP2</name>
      <Point><coordinates>36.822946,-1.291066,30</coordinates></Point>
    </Placemark>
  </Document>
</kml>
"""

_MIXED_KML = b"""<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
  <Document>
    <Placemark>
      <name>Good</name>
      <Point><coordinates>36.821946,-1.292066,0</coordinates></Point>
    </Placemark>
    <Placemark>
      <name>NoCoords</name>
    </Placemark>
    <Placemark>
      <name>Malformed</name>
      <Point><coordinates>not-a-number</coordinates></Point>
    </Placemark>
  </Document>
</kml>
"""

_EMPTY_KML = b"""<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
  <Document></Document>
</kml>
"""


def test_parses_all_placemarks_in_document_order():
    waypoints, warnings = parse_kml_waypoints(_VALID_KML)

    assert warnings == []
    assert len(waypoints) == 2
    assert waypoints[0]["latitude"] == pytest.approx(-1.292066)
    assert waypoints[0]["longitude"] == pytest.approx(36.821946)
    assert waypoints[0]["altitude"] == 0.0
    assert waypoints[1]["altitude"] == 30.0


def test_placemark_name_becomes_tree_id():
    waypoints, _ = parse_kml_waypoints(_VALID_KML)

    assert waypoints[0]["tree_id"] == "WP1"
    assert waypoints[1]["tree_id"] == "WP2"


def test_unnamed_placemark_has_no_tree_id():
    kml = _VALID_KML.replace(b"<name>WP1</name>", b"")
    waypoints, _ = parse_kml_waypoints(kml)

    assert waypoints[0]["tree_id"] is None


def test_applies_requested_action_and_flight_params_to_every_waypoint():
    waypoints, _ = parse_kml_waypoints(_VALID_KML, action="fly_through", speed=5.0, gimbal_pitch=-45.0)

    assert all(wp["action"] == "fly_through" for wp in waypoints)
    assert all(wp["speed"] == 5.0 for wp in waypoints)
    assert all(wp["gimbal_pitch"] == -45.0 for wp in waypoints)


def test_missing_altitude_falls_back_to_default_altitude():
    kml = _VALID_KML.replace(b",0</coordinates>", b"</coordinates>")
    waypoints, _ = parse_kml_waypoints(kml, default_altitude=42.0)

    assert waypoints[0]["altitude"] == 42.0


def test_skips_bad_placemarks_and_keeps_good_ones_with_warnings():
    waypoints, warnings = parse_kml_waypoints(_MIXED_KML)

    assert len(waypoints) == 1
    assert len(warnings) == 2
    assert any("NoCoords" in w for w in warnings)
    assert any("Malformed" in w for w in warnings)


def test_no_placemarks_raises_value_error():
    with pytest.raises(ValueError, match="No <Placemark>"):
        parse_kml_waypoints(_EMPTY_KML)


def test_all_placemarks_bad_raises_value_error():
    kml = _MIXED_KML.replace(
        b"<Point><coordinates>36.821946,-1.292066,0</coordinates></Point>", b""
    )
    with pytest.raises(ValueError, match="No usable waypoints"):
        parse_kml_waypoints(kml)


def test_invalid_action_raises_value_error():
    with pytest.raises(ValueError, match="action must be one of"):
        parse_kml_waypoints(_VALID_KML, action="not-a-real-action")


async def test_parse_kml_endpoint_returns_waypoints_ready_for_create_flight(client, auth_headers):
    response = await client.post(
        "/api/v1/drones/flights/parse-kml",
        files={"file": ("mission.kml", _VALID_KML, "application/vnd.google-earth.kml+xml")},
        headers=auth_headers,
    )

    assert response.status_code == 200
    body = response.json()
    assert len(body["waypoints"]) == 2
    assert body["warnings"] == []


async def test_parse_kml_endpoint_rejects_placemark_less_file(client, auth_headers):
    response = await client.post(
        "/api/v1/drones/flights/parse-kml",
        files={"file": ("empty.kml", _EMPTY_KML, "application/vnd.google-earth.kml+xml")},
        headers=auth_headers,
    )

    assert response.status_code == 400


async def test_parse_kml_endpoint_requires_auth(client):
    response = await client.post(
        "/api/v1/drones/flights/parse-kml",
        files={"file": ("mission.kml", _VALID_KML, "application/vnd.google-earth.kml+xml")},
    )

    assert response.status_code in (401, 403)
