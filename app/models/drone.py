from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Text, ForeignKey, Enum as SQLEnum, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base
# Real (Universe B) targets for farm_id/requested_by_id/diagnosis_id below -
# a different declarative Base/registry than this module's own Base, in a
# different MetaData. A bare ForeignKey("farms.id") string only resolves
# within the referencing column's own Base.metadata, so it can't find these
# by name; passing the actual mapped Column (Farm.id etc.) sidesteps that
# name lookup entirely and works fine across registries.
from app.models.database import Diagnosis as _UniverseBDiagnosis, Farm as _UniverseBFarm, User as _UniverseBUser
import enum


class DroneBackendType(str, enum.Enum):
    # SIMULATED/MAVLINK backed an autonomous mission-execution pathway
    # (plan_mission/execute_mission + a FlightBackend implementation) that
    # was removed - this project's actual hardware is flown manually and
    # never spoke MAVLink. Kept only so any pre-existing rows/enum values
    # still deserialize; no code path creates new rows with these values.
    SIMULATED = "simulated"
    MAVLINK = "mavlink"
    # The only backend type new flights use - images are pushed in after
    # the fact (or live, via scripts/watch_and_upload_dji_images.py) from a
    # manually-flown real drone. See DroneAIService.start_manual_flight().
    MANUAL_INGEST = "manual_ingest"


class DroneFlightStatus(str, enum.Enum):
    # No code path sets PLANNED anymore (it belonged to the removed
    # plan_mission/execute_mission pathway) - kept for the same reason as
    # DroneBackendType.SIMULATED/MAVLINK above. Manual-ingest flights go
    # straight to IN_PROGRESS.
    PLANNED = "planned"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    ABORTED = "aborted"
    FAILED = "failed"


class DroneFlight(Base):
    __tablename__ = "drone_flights"

    id = Column(Integer, primary_key=True, index=True)
    farm_id = Column(Integer, ForeignKey(_UniverseBFarm.id), nullable=False, index=True)
    requested_by_id = Column(Integer, ForeignKey(_UniverseBUser.id), nullable=False, index=True)
    drone_id = Column(String(100), nullable=False)

    backend_type = Column(SQLEnum(DroneBackendType), nullable=False, default=DroneBackendType.MANUAL_INGEST)
    status = Column(SQLEnum(DroneFlightStatus), nullable=False, default=DroneFlightStatus.IN_PROGRESS, index=True)

    home_latitude = Column(Float, nullable=False)
    home_longitude = Column(Float, nullable=False)
    home_altitude = Column(Float, nullable=False)
    # Nullable: always None now - belonged to the removed autonomous
    # mission-execution pathway, never applicable to MANUAL_INGEST flights.
    target_altitude_m = Column(Float, nullable=True)

    # Optional reference/briefing waypoint list (e.g. KML-derived via
    # app.services.kml_mission_parser), attached at start_manual_flight()
    # time - nothing in this system flies it. Used only to auto-tag incoming
    # photos with the nearest waypoint's tree_id; see
    # DroneAIService.ingest_captured_image().
    mission_plan = Column(JSON, nullable=True)

    disease_detection_enabled = Column(Boolean, nullable=False, default=False, server_default="false")

    # Yield projection placeholders - intentionally unpopulated. Real values
    # need a model calibrated against actual harvest-yield ground truth this
    # project doesn't have; no computation logic exists for these anywhere.
    # TODO: populate once real calibration data is available.
    projected_yield_kg_per_hectare = Column(Float, nullable=True)
    yield_projection_model_version = Column(String(50), nullable=True)

    # Real OpenWeatherMap conditions at the home coordinates, fetched once at
    # start_manual_flight() time (app.services.weather_service). Advisory
    # only - all nullable, stays None when OPENWEATHER_API_KEY is unset or
    # the lookup fails; never blocks a mission either way.
    weather_temperature_c = Column(Float, nullable=True)
    weather_humidity_pct = Column(Integer, nullable=True)
    weather_wind_speed_ms = Column(Float, nullable=True)
    weather_conditions = Column(String(100), nullable=True)
    weather_flight_suitable = Column(Boolean, nullable=True)
    weather_warnings = Column(JSON, nullable=True)
    weather_disease_pressure = Column(String(20), nullable=True)
    weather_checked_at = Column(DateTime(timezone=True), nullable=True)

    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    battery_start_pct = Column(Float, nullable=True)
    battery_end_pct = Column(Float, nullable=True)
    error_message = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class DroneTelemetryLog(Base):
    """Per-waypoint telemetry samples, written only by the removed
    execute_mission() pathway - no current code path inserts rows here.
    Table/model kept as-is rather than dropped; not written to by
    manual-ingest flights."""
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
    #
    # Always None today: the code path that would set this raises
    # NotImplementedError (see DroneAIService._process_and_persist_image) -
    # the per-image disease-detection integration still targets the old
    # Universe A Diagnosis model, which nothing else in the app reads any
    # more. No ORM relationship() here on purpose: this FK points at the
    # real (Universe B) diagnoses table, but Universe A's Diagnosis class
    # (the only "Diagnosis" in this model's own declarative registry) maps
    # to a different table with no FK to this one - a relationship() to it
    # fails mapper configuration outright ("no foreign keys linking these
    # tables"), not just silently wrong. Query app.models.database.Diagnosis
    # directly by this id once that integration is redone.
    diagnosis_id = Column(Integer, ForeignKey(_UniverseBDiagnosis.id, ondelete="SET NULL"), nullable=True, index=True)
    # Read-only link to the real-math NDVI/stress/vigor analysis row for this
    # photo (app.services.plant_stress_assessment /
    # app.services.canopy_vigor_assessment). selectin batches the load
    # across a whole image list, same as diagnosis above - do not rely on
    # this immediately after creating a DroneImage in the same request (see
    # app/api/drones.py's upload_manual_flight_image, which re-queries
    # DroneImageAnalysis directly instead for that reason).
    analysis = relationship("DroneImageAnalysis", lazy="selectin", viewonly=True, uselist=False)

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

    # Excess-Green-Index canopy coverage/vigor screening
    # (app.services.canopy_vigor_assessment) - real math over the plain RGB
    # frame, not a trained model. Always computed like stress_level above;
    # this is the free/local counterpart to the opt-in, paid Kindwise
    # diagnosis on diagnosis_id - a scouting cue, not a diagnosis.
    canopy_coverage_pct = Column(Float, nullable=True)
    vigor_level = Column(String(20), nullable=True)
    vigor_indicators = Column(JSON, nullable=True)
    low_vigor_regions = Column(JSON, nullable=True)
    # Real m^2, only populated when the caller supplied a ground-sample-
    # distance at upload time (DroneImage.ground_sampling_distance_cm) -
    # None otherwise, never a fabricated estimate. See
    # app.services.canopy_vigor_assessment._pixel_area_m2.
    total_canopy_area_m2 = Column(Float, nullable=True)
    # Uploaded annotated copy of the photo - canopy boundary traced, low-vigor
    # areas boxed in red, coverage/vigor/area labelled
    # (app.services.canopy_overlay_rendering). Nullable: stays None if the
    # render or its upload failed, which never blocks image ingestion.
    overlay_url = Column(String(500), nullable=True)

    analyzed_at = Column(DateTime(timezone=True), server_default=func.now())
