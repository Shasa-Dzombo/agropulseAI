"""
Exercises the manual-ingest HTTP endpoints end to end (POST /flights/manual
-> POST /flights/{id}/images -> GET /flights/{id}/images), via the shared
client/auth_headers fixtures in tests_drones/conftest.py - confirms per-photo
NDVI/stress/vigor analysis is actually visible in the API response, not just
persisted to the DB (see app.services.drone_ai_service.ingest_captured_image).
"""

import io

from PIL import Image


def _jpeg_bytes(color=(20, 90, 60), size=(64, 64)) -> bytes:
    img = Image.new("RGB", size, color=color)
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


async def _start_manual_flight(client, auth_headers, test_farm):
    response = await client.post(
        "/api/v1/drones/flights/manual",
        json={
            "farm_id": test_farm.id, "drone_id": "P4M-001",
            "home_latitude": 37.77, "home_longitude": -122.4, "home_altitude": 50.0,
        },
        headers=auth_headers,
    )
    assert response.status_code == 201
    return response.json()["id"]


async def test_uploaded_image_response_includes_vigor_analysis(client, auth_headers, test_farm):
    flight_id = await _start_manual_flight(client, auth_headers, test_farm)

    response = await client.post(
        f"/api/v1/drones/flights/{flight_id}/images",
        files={"rgb": ("photo.jpg", _jpeg_bytes(), "image/jpeg")},
        headers=auth_headers,
    )

    assert response.status_code == 201
    body = response.json()
    assert body["analysis"] is not None
    assert body["analysis"]["canopy_coverage_pct"] is not None
    assert body["analysis"]["vigor_level"] in ("good", "moderate", "low")
    assert body["analysis"]["total_canopy_area_m2"] is None  # no GSD supplied
    # Annotated overlay image was rendered and uploaded alongside the raw bands.
    assert body["analysis"]["overlay_url"] is not None
    assert body["analysis"]["overlay_url"].endswith("_overlay.jpg")


async def test_ground_sampling_distance_produces_real_area_m2(client, auth_headers, test_farm):
    flight_id = await _start_manual_flight(client, auth_headers, test_farm)

    response = await client.post(
        f"/api/v1/drones/flights/{flight_id}/images",
        files={"rgb": ("photo.jpg", _jpeg_bytes(color=(20, 200, 20)), "image/jpeg")},
        data={"ground_sampling_distance_cm": "5.0"},
        headers=auth_headers,
    )

    assert response.status_code == 201
    analysis = response.json()["analysis"]
    assert analysis["total_canopy_area_m2"] is not None
    assert analysis["total_canopy_area_m2"] > 0


async def test_list_flight_images_includes_analysis_per_photo(client, auth_headers, test_farm):
    flight_id = await _start_manual_flight(client, auth_headers, test_farm)
    await client.post(
        f"/api/v1/drones/flights/{flight_id}/images",
        files={"rgb": ("photo.jpg", _jpeg_bytes(), "image/jpeg")},
        headers=auth_headers,
    )

    response = await client.get(f"/api/v1/drones/flights/{flight_id}/images", headers=auth_headers)

    assert response.status_code == 200
    images = response.json()
    assert len(images) == 1
    assert images[0]["analysis"] is not None
    assert images[0]["analysis"]["vigor_level"] in ("good", "moderate", "low")
