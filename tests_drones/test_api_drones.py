"""
Exercises the real /api/v1/drones/* endpoints through the FastAPI app
(auth, ownership checks, and all), not just the service layer directly.
"""

import pytest

import app.services.drone_ai_service as drone_ai_service
from tests_drones.conftest import sample_waypoints


@pytest.fixture(autouse=True)
def stub_image_uploads(monkeypatch):
    """The router builds DroneAIService with no custom uploader, so it falls
    back to the real S3 uploader - which would otherwise try to hit AWS with
    this repo's placeholder credentials. Patch the module-level default
    instead of adding a moto dependency."""
    async def fake_uploader(content: bytes, file_name: str, folder: str) -> str:
        return f"https://fake-bucket.test/{folder}/{file_name}"

    monkeypatch.setattr(drone_ai_service, "_default_image_uploader", fake_uploader)


def _create_payload(farm_id: int) -> dict:
    return {
        "farm_id": farm_id,
        "drone_id": "AGRO-DRONE-001",
        "home_latitude": 37.77,
        "home_longitude": -122.4,
        "home_altitude": 100.0,
        "target_altitude_m": 30.0,
        "backend_type": "simulated",
        "waypoints": sample_waypoints(),
    }


async def test_create_execute_and_get_analysis_happy_path(client, auth_headers, test_farm):
    create_resp = await client.post("/api/v1/drones/flights", json=_create_payload(test_farm.id), headers=auth_headers)
    assert create_resp.status_code == 201
    flight = create_resp.json()
    assert flight["status"] == "planned"
    flight_id = flight["id"]

    execute_resp = await client.post(f"/api/v1/drones/flights/{flight_id}/execute", json={}, headers=auth_headers)
    assert execute_resp.status_code == 200
    executed = execute_resp.json()
    assert executed["status"] == "completed"

    analysis_resp = await client.get(f"/api/v1/drones/flights/{flight_id}/analysis", headers=auth_headers)
    assert analysis_resp.status_code == 200
    summary = analysis_resp.json()
    assert summary["flight_id"] == flight_id
    assert summary["image_count"] == len([wp for wp in sample_waypoints() if wp["action"] == "take_photo"])
    assert summary["mean_ndvi"] is not None

    images_resp = await client.get(f"/api/v1/drones/flights/{flight_id}/images", headers=auth_headers)
    assert images_resp.status_code == 200
    assert len(images_resp.json()) == summary["image_count"]

    list_resp = await client.get(f"/api/v1/drones/flights?farm_id={test_farm.id}", headers=auth_headers)
    assert list_resp.status_code == 200
    assert any(f["id"] == flight_id for f in list_resp.json())


async def test_create_flight_without_auth_is_rejected(client, test_farm):
    resp = await client.post("/api/v1/drones/flights", json=_create_payload(test_farm.id))
    assert resp.status_code == 401


async def test_cannot_access_another_users_farm_flight(client, auth_headers, other_auth_headers, test_farm):
    create_resp = await client.post("/api/v1/drones/flights", json=_create_payload(test_farm.id), headers=auth_headers)
    assert create_resp.status_code == 201
    flight_id = create_resp.json()["id"]

    resp = await client.get(f"/api/v1/drones/flights/{flight_id}", headers=other_auth_headers)
    assert resp.status_code == 404


async def test_mavlink_backend_without_connection_string_is_rejected(client, auth_headers, test_farm):
    payload = _create_payload(test_farm.id)
    payload["backend_type"] = "mavlink"
    resp = await client.post("/api/v1/drones/flights", json=payload, headers=auth_headers)
    assert resp.status_code == 400
