from sqlalchemy import Column, Integer, String, Float, DateTime, Text, ForeignKey, Enum as SQLEnum, JSON
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

    analyzed_at = Column(DateTime(timezone=True), server_default=func.now())
