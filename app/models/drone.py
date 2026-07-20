from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Text, ForeignKey, Enum as SQLEnum, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base
import enum


class DroneBackendType(str, enum.Enum):
    SIMULATED = "simulated"
    MAVLINK = "mavlink"


class DroneFlightStatus(str, enum.Enum):
    PLANNED = "planned"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    ABORTED = "aborted"
    FAILED = "failed"


class DroneFlight(Base):
    __tablename__ = "drone_flights"

    id = Column(Integer, primary_key=True, index=True)
    farm_id = Column(Integer, ForeignKey("app_farms.id"), nullable=False, index=True)
    requested_by_id = Column(Integer, ForeignKey("app_users.id"), nullable=False, index=True)
    drone_id = Column(String(100), nullable=False)

    backend_type = Column(SQLEnum(DroneBackendType), nullable=False, default=DroneBackendType.SIMULATED)
    status = Column(SQLEnum(DroneFlightStatus), nullable=False, default=DroneFlightStatus.PLANNED, index=True)

    home_latitude = Column(Float, nullable=False)
    home_longitude = Column(Float, nullable=False)
    home_altitude = Column(Float, nullable=False)
    target_altitude_m = Column(Float, nullable=False)

    mission_plan = Column(JSON, nullable=False)  # serialized waypoint list at request time

    disease_detection_enabled = Column(Boolean, nullable=False, default=False, server_default="false")

    # Yield projection placeholders - intentionally unpopulated. Real values
    # need a model calibrated against actual harvest-yield ground truth this
    # project doesn't have; no computation logic exists for these anywhere.
    # TODO: populate once real calibration data is available.
    projected_yield_kg_per_hectare = Column(Float, nullable=True)
    yield_projection_model_version = Column(String(50), nullable=True)

    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    battery_start_pct = Column(Float, nullable=True)
    battery_end_pct = Column(Float, nullable=True)
    error_message = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class DroneTelemetryLog(Base):
    __tablename__ = "drone_telemetry_logs"

    id = Column(Integer, primary_key=True, index=True)
    flight_id = Column(Integer, ForeignKey("drone_flights.id", ondelete="CASCADE"), nullable=False, index=True)
    waypoint_index = Column(Integer, nullable=False)

    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    altitude = Column(Float, nullable=False)
    heading = Column(Float, nullable=True)
    ground_speed = Column(Float, nullable=True)
    battery_pct = Column(Float, nullable=True)
    battery_voltage = Column(Float, nullable=True)
    flight_mode = Column(String(50), nullable=True)

    recorded_at = Column(DateTime(timezone=True), server_default=func.now())


class DroneImage(Base):
    __tablename__ = "drone_images"

    id = Column(Integer, primary_key=True, index=True)
    flight_id = Column(Integer, ForeignKey("drone_flights.id", ondelete="CASCADE"), nullable=False, index=True)
    waypoint_index = Column(Integer, nullable=False)
    tree_id = Column(String(100), nullable=True)

    rgb_url = Column(String(500), nullable=True)
    nir_url = Column(String(500), nullable=True)

    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    altitude = Column(Float, nullable=False)
    ground_sampling_distance_cm = Column(Float, nullable=True)

    # Populated only when the parent flight's disease_detection_enabled is
    # True AND a Kindwise API call actually produced a result for this
    # photo. DroneImageAnalysis (NDVI/stress) stays fully decoupled from
    # Diagnosis - they're orthogonal analyses of the same photo.
    diagnosis_id = Column(Integer, ForeignKey("app_diagnoses.id", ondelete="SET NULL"), nullable=True, index=True)
    # Read-only link for embedding disease answers in API responses
    # (app/api/drones.py). selectin batches the load across a whole image
    # list instead of one query per image.
    diagnosis = relationship("Diagnosis", lazy="selectin", viewonly=True)

    captured_at = Column(DateTime(timezone=True), server_default=func.now())


class DroneImageAnalysis(Base):
    __tablename__ = "drone_image_analyses"

    id = Column(Integer, primary_key=True, index=True)
    image_id = Column(Integer, ForeignKey("drone_images.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)

    ndvi = Column(Float, nullable=True)
    gndvi = Column(Float, nullable=True)
    ndre = Column(Float, nullable=True)
    savi = Column(Float, nullable=True)
    evi = Column(Float, nullable=True)
    health_status = Column(String(50), nullable=True)

    # Index-threshold stress assessment (app.services.plant_stress_assessment)
    # - real math over the indices above, not a trained model. Always
    # computed (no external API, no opt-in needed), unlike disease_id above.
    stress_level = Column(String(20), nullable=True)
    stress_indicators = Column(JSON, nullable=True)

    analyzed_at = Column(DateTime(timezone=True), server_default=func.now())
