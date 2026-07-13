"""
Full DroneAIService.execute_mission() integration test: plan -> fly (simulated
backend) -> capture -> NDVI analysis -> persist, against an in-memory DB.
The S3 uploader is replaced with a stub callable (avoids needing real AWS
credentials or a moto dependency) - everything else is the real code path.
"""

import math

from sqlalchemy import select

from app.models.drone import DroneFlight, DroneFlightStatus, DroneImage, DroneImageAnalysis, DroneTelemetryLog
from app.services.drone_ai_service import DroneAIService
from tests_drones.conftest import sample_waypoints


async def fake_uploader(content: bytes, file_name: str, folder: str) -> str:
    return f"https://fake-bucket.test/{folder}/{file_name}"


async def test_execute_mission_completes_and_persists_everything(db_session, test_farm, test_user):
    service = DroneAIService(db_session, image_uploader=fake_uploader)
    waypoints = sample_waypoints()

    flight = await service.plan_mission(
        farm_id=test_farm.id,
        user_id=test_user.id,
        drone_id="AGRO-DRONE-001",
        home_latitude=37.77,
        home_longitude=-122.4,
        home_altitude=100.0,
        target_altitude_m=30.0,
        backend_type="simulated",
        waypoints=waypoints,
    )
    assert flight.status == DroneFlightStatus.PLANNED

    completed = await service.execute_mission(flight.id, test_user.id)

    assert completed.status == DroneFlightStatus.COMPLETED
    assert completed.error_message is None
    assert completed.battery_start_pct is not None
    assert completed.battery_end_pct is not None
    assert completed.battery_end_pct <= completed.battery_start_pct

    telemetry_result = await db_session.execute(
        select(DroneTelemetryLog).where(DroneTelemetryLog.flight_id == flight.id)
    )
    telemetry_rows = telemetry_result.scalars().all()
    assert len(telemetry_rows) == len(waypoints)

    photo_waypoints = [wp for wp in waypoints if wp["action"] == "take_photo"]
    images_result = await db_session.execute(select(DroneImage).where(DroneImage.flight_id == flight.id))
    images = images_result.scalars().all()
    assert len(images) == len(photo_waypoints)
    for image in images:
        assert image.rgb_url.startswith("https://fake-bucket.test/drone-imagery/")
        assert image.nir_url.startswith("https://fake-bucket.test/drone-imagery/")

    analyses_result = await db_session.execute(
        select(DroneImageAnalysis).join(DroneImage, DroneImage.id == DroneImageAnalysis.image_id)
        .where(DroneImage.flight_id == flight.id)
    )
    analyses = analyses_result.scalars().all()
    assert len(analyses) == len(photo_waypoints)
    for analysis in analyses:
        assert analysis.ndvi is not None
        assert not math.isnan(analysis.ndvi)
        assert -1.0 <= analysis.ndvi <= 1.0
        assert analysis.health_status is not None


async def test_execute_mission_rejects_flight_that_is_not_planned(db_session, test_farm, test_user):
    service = DroneAIService(db_session, image_uploader=fake_uploader)
    flight = await service.plan_mission(
        farm_id=test_farm.id,
        user_id=test_user.id,
        drone_id="AGRO-DRONE-001",
        home_latitude=37.77,
        home_longitude=-122.4,
        home_altitude=100.0,
        target_altitude_m=30.0,
        backend_type="simulated",
        waypoints=sample_waypoints(),
    )
    await service.execute_mission(flight.id, test_user.id)

    from fastapi import HTTPException
    import pytest

    with pytest.raises(HTTPException) as exc_info:
        await service.execute_mission(flight.id, test_user.id)
    assert exc_info.value.status_code == 409
