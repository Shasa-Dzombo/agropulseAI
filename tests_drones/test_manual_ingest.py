"""
Exercises DroneAIService's manual DJI ground-ingestion path: start_manual_flight
-> ingest_captured_image (with and without a real NIR file, with and without
GPS EXIF) -> complete_manual_flight, against an in-memory DB. No FlightBackend,
no waypoint plan - mirrors the real ground-testing workflow (manual DJI
flight, images pushed in from scripts/watch_and_upload_dji_images.py).
"""

import io
import math

import pytest
from PIL import Image
from fastapi import HTTPException
from sqlalchemy import select

from app.models.drone import DroneBackendType, DroneFlightStatus, DroneImageAnalysis
from app.services.drone_ai_service import DroneAIService

_GPS_INFO_TAG = 34853


async def fake_uploader(content: bytes, file_name: str, folder: str) -> str:
    return f"https://fake-bucket.test/{folder}/{file_name}"


def _jpeg_bytes(color=(20, 90, 60), size=(32, 32), gps_ifd=None) -> bytes:
    img = Image.new("RGB", size, color=color)
    save_kwargs = {}
    if gps_ifd is not None:
        exif = img.getexif()
        exif[_GPS_INFO_TAG] = gps_ifd
        save_kwargs["exif"] = exif
    buf = io.BytesIO()
    img.save(buf, format="JPEG", **save_kwargs)
    return buf.getvalue()


def _grayscale_tiff_bytes(value=220, size=(32, 32)) -> bytes:
    img = Image.new("L", size, color=value)
    buf = io.BytesIO()
    img.save(buf, format="TIFF")
    return buf.getvalue()


async def _start_flight(service, test_farm, test_user):
    return await service.start_manual_flight(
        farm_id=test_farm.id, user_id=test_user.id, drone_id="P4M-001",
        home_latitude=37.77, home_longitude=-122.4, home_altitude=50.0,
    )


async def test_start_manual_flight_creates_in_progress_flight_with_no_waypoints(db_session, test_farm, test_user):
    service = DroneAIService(db_session, image_uploader=fake_uploader)

    flight = await _start_flight(service, test_farm, test_user)

    assert flight.status == DroneFlightStatus.IN_PROGRESS
    assert flight.backend_type == DroneBackendType.MANUAL_INGEST
    assert flight.mission_plan is None
    assert flight.target_altitude_m is None


async def test_ingest_image_without_nir_falls_back_to_home_coords_and_placeholder(db_session, test_farm, test_user):
    service = DroneAIService(db_session, image_uploader=fake_uploader)
    flight = await _start_flight(service, test_farm, test_user)

    image = await service.ingest_captured_image(flight.id, test_user.id, _jpeg_bytes(), None, None)

    assert image.latitude == flight.home_latitude
    assert image.longitude == flight.home_longitude
    assert image.nir_url is None
    assert image.rgb_url.startswith("https://fake-bucket.test/drone-imagery/")

    result = await db_session.execute(select(DroneImageAnalysis).where(DroneImageAnalysis.image_id == image.id))
    analysis = result.scalar_one()
    assert analysis.ndvi is None or not math.isnan(analysis.ndvi)
    assert analysis.stress_level is not None
    assert analysis.canopy_coverage_pct is not None
    assert analysis.vigor_level is not None


async def test_ingest_image_with_gps_exif_and_real_nir_overrides_home_coords(db_session, test_farm, test_user):
    service = DroneAIService(db_session, image_uploader=fake_uploader)
    flight = await _start_flight(service, test_farm, test_user)

    gps_ifd = {1: "N", 2: (12.0, 30.0, 0.0), 3: "E", 4: (34.0, 15.0, 0.0)}
    rgb_bytes = _jpeg_bytes(gps_ifd=gps_ifd)
    nir_bytes = _grayscale_tiff_bytes(value=220)

    image = await service.ingest_captured_image(flight.id, test_user.id, rgb_bytes, nir_bytes, None)

    assert image.latitude == pytest.approx(12 + 30 / 60)
    assert image.longitude == pytest.approx(34 + 15 / 60)
    assert image.nir_url is not None
    assert image.nir_url != image.rgb_url


async def test_ingest_image_rejects_flight_not_in_progress(db_session, test_farm, test_user):
    service = DroneAIService(db_session, image_uploader=fake_uploader)
    flight = await _start_flight(service, test_farm, test_user)
    await service.complete_manual_flight(flight.id, test_user.id, "completed")

    with pytest.raises(HTTPException) as exc_info:
        await service.ingest_captured_image(flight.id, test_user.id, _jpeg_bytes(), None, None)
    assert exc_info.value.status_code == 409


async def test_ingest_image_rejects_other_users_flight(db_session, test_farm, test_user, other_user):
    service = DroneAIService(db_session, image_uploader=fake_uploader)
    flight = await _start_flight(service, test_farm, test_user)

    with pytest.raises(HTTPException) as exc_info:
        await service.ingest_captured_image(flight.id, other_user.id, _jpeg_bytes(), None, None)
    assert exc_info.value.status_code == 404


async def test_complete_manual_flight_marks_completed(db_session, test_farm, test_user):
    service = DroneAIService(db_session, image_uploader=fake_uploader)
    flight = await _start_flight(service, test_farm, test_user)

    completed = await service.complete_manual_flight(flight.id, test_user.id, "completed", battery_end_pct=64.0)

    assert completed.status == DroneFlightStatus.COMPLETED
    assert completed.completed_at is not None
    assert completed.battery_end_pct == 64.0


async def test_ingest_image_with_mission_plan_auto_tags_nearest_waypoint_tree_id(db_session, test_farm, test_user):
    service = DroneAIService(db_session, image_uploader=fake_uploader)
    mission_plan = [
        {"latitude": 12.5, "longitude": 34.25, "altitude": 30.0, "action": "take_photo",
         "hover_time": 0.0, "speed": 10.0, "gimbal_pitch": -90.0, "photo_interval": 0.0,
         "tree_id": "mango_row1_tree0"},
        {"latitude": 12.6, "longitude": 34.30, "altitude": 30.0, "action": "take_photo",
         "hover_time": 0.0, "speed": 10.0, "gimbal_pitch": -90.0, "photo_interval": 0.0,
         "tree_id": "mango_row1_tree1"},
    ]
    flight = await service.start_manual_flight(
        farm_id=test_farm.id, user_id=test_user.id, drone_id="P4M-001",
        home_latitude=37.77, home_longitude=-122.4, home_altitude=50.0,
        mission_plan=mission_plan,
    )
    assert flight.mission_plan == mission_plan

    gps_ifd = {1: "N", 2: (12.0, 30.0, 0.0), 3: "E", 4: (34.0, 15.0, 0.0)}  # -> lat 12.5, lon 34.25
    rgb_bytes = _jpeg_bytes(gps_ifd=gps_ifd)

    image = await service.ingest_captured_image(flight.id, test_user.id, rgb_bytes, None, None)

    assert image.tree_id == "mango_row1_tree0"


async def test_ingest_image_explicit_tree_id_overrides_nearest_waypoint_match(db_session, test_farm, test_user):
    service = DroneAIService(db_session, image_uploader=fake_uploader)
    mission_plan = [{"latitude": 12.5, "longitude": 34.25, "altitude": 30.0, "tree_id": "mango_row1_tree0"}]
    flight = await service.start_manual_flight(
        farm_id=test_farm.id, user_id=test_user.id, drone_id="P4M-001",
        home_latitude=37.77, home_longitude=-122.4, home_altitude=50.0,
        mission_plan=mission_plan,
    )

    gps_ifd = {1: "N", 2: (12.0, 30.0, 0.0), 3: "E", 4: (34.0, 15.0, 0.0)}
    rgb_bytes = _jpeg_bytes(gps_ifd=gps_ifd)

    image = await service.ingest_captured_image(
        flight.id, test_user.id, rgb_bytes, None, None, tree_id="manually_specified",
    )

    assert image.tree_id == "manually_specified"


async def test_ingest_image_without_real_gps_does_not_auto_tag_from_mission_plan(db_session, test_farm, test_user):
    service = DroneAIService(db_session, image_uploader=fake_uploader)
    mission_plan = [{"latitude": 12.5, "longitude": 34.25, "altitude": 30.0, "tree_id": "should_not_apply"}]
    flight = await service.start_manual_flight(
        farm_id=test_farm.id, user_id=test_user.id, drone_id="P4M-001",
        home_latitude=37.77, home_longitude=-122.4, home_altitude=50.0,
        mission_plan=mission_plan,
    )

    # No GPS EXIF on this photo - falls back to the flight's home coordinates,
    # which must never be treated as a real per-photo GPS match.
    image = await service.ingest_captured_image(flight.id, test_user.id, _jpeg_bytes(), None, None)

    assert image.tree_id is None


async def test_complete_manual_flight_aborted_status(db_session, test_farm, test_user):
    service = DroneAIService(db_session, image_uploader=fake_uploader)
    flight = await _start_flight(service, test_farm, test_user)

    aborted = await service.complete_manual_flight(flight.id, test_user.id, "aborted", error_message="lost signal")

    assert aborted.status == DroneFlightStatus.ABORTED
    assert aborted.error_message == "lost signal"
