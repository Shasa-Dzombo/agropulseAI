// Guards against drift from app/schemas/drone.py's response shapes - matches
// actual live responses captured while wiring app/api/drones.py to real
// farms/logins (see mobile/CHANGELOG.md 2026-09-03).

import 'package:flutter_test/flutter_test.dart';
import 'package:agropulse_mobile/features/drones/drone_models.dart';

void main() {
  test('DroneFlight.fromJson parses a real flight with auto-attached weather', () {
    final flight = DroneFlight.fromJson({
      'id': 5, 'farm_id': 804, 'requested_by_id': 514, 'drone_id': 'DJI-Mavic-3M-01',
      'backend_type': 'manual_ingest', 'status': 'in_progress',
      'home_latitude': -1.2921, 'home_longitude': 36.821898, 'home_altitude': 1795.0,
      'target_altitude_m': null, 'mission_plan': null, 'disease_detection_enabled': false,
      'projected_yield_kg_per_hectare': null, 'yield_projection_model_version': null,
      'weather_temperature_c': 16.02, 'weather_humidity_pct': 77, 'weather_wind_speed_ms': 0.0,
      'weather_conditions': 'scattered clouds', 'weather_flight_suitable': true,
      'weather_warnings': [], 'weather_disease_pressure': 'moderate',
      'weather_checked_at': '2026-09-03T05:47:26.975609',
      'started_at': '2026-09-03T05:47:25.348035Z', 'completed_at': null,
      'battery_start_pct': null, 'battery_end_pct': null, 'error_message': null,
      'created_at': '2026-09-03T05:47:25.177701Z',
    });

    expect(flight.status, 'in_progress');
    expect(flight.weatherTemperatureC, closeTo(16.02, 0.01));
    expect(flight.weatherFlightSuitable, isTrue);
    expect(flight.completedAt, isNull);
  });

  test('DroneImage.fromJson parses a real analyzed photo, including nested analysis', () {
    final image = DroneImage.fromJson({
      'id': 2, 'flight_id': 5, 'waypoint_index': 0, 'tree_id': 'T-001',
      'rgb_url': 'file://C:/local_uploads/drone-imagery/5/0_rgb.jpg', 'nir_url': null,
      'latitude': -1.2921, 'longitude': 36.821898, 'altitude': 1795.0,
      'ground_sampling_distance_cm': null, 'diagnosis_id': null, 'diagnosis': null,
      'analysis': {
        'image_id': 2, 'ndvi': 0.55517276039474, 'gndvi': null, 'ndre': 0.0,
        'savi': 0.823427125185523, 'evi': -0.9245823261695497, 'health_status': 'mild_stress',
        'stress_level': 'moderate_stress', 'stress_indicators': ['Low NDRE (0.00) - possible nitrogen/chlorophyll deficiency'],
        'canopy_coverage_pct': 100.0, 'vigor_level': 'good', 'vigor_indicators': [],
        'low_vigor_regions': [], 'total_canopy_area_m2': null,
        'overlay_url': 'file://C:/local_uploads/drone-imagery/5/0_overlay.jpg',
      },
      'captured_at': '2026-09-03T05:50:19.956404Z',
    });

    expect(image.treeId, 'T-001');
    expect(image.analysis, isNotNull);
    expect(image.analysis!.ndvi, closeTo(0.555, 0.001));
    expect(image.analysis!.healthStatus, 'mild_stress');
    expect(image.analysis!.vigorLevel, 'good');
  });

  test('FlightAnalysisSummary.fromJson parses a real aggregate summary', () {
    final summary = FlightAnalysisSummary.fromJson({
      'flight_id': 5, 'image_count': 1, 'mean_ndvi': 0.55517276039474,
      'min_ndvi': 0.55517276039474, 'max_ndvi': 0.55517276039474,
      'health_status_histogram': {'mild_stress': 1},
      'mean_canopy_coverage_pct': 100.0, 'min_canopy_coverage_pct': 100.0, 'max_canopy_coverage_pct': 100.0,
      'vigor_level_histogram': {'good': 1},
    });

    expect(summary.imageCount, 1);
    expect(summary.healthStatusHistogram['mild_stress'], 1);
    expect(summary.vigorLevelHistogram['good'], 1);
  });
}
