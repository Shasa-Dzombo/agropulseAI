/// Mirrors app/schemas/drone.py's DroneFlightResponse.
class DroneFlight {
  final int id;
  final int farmId;
  final String droneId;
  final String backendType;
  final String status;
  final double homeLatitude;
  final double homeLongitude;
  final double? weatherTemperatureC;
  final String? weatherConditions;
  final bool? weatherFlightSuitable;
  final List<String>? weatherWarnings;
  final String? weatherDiseasePressure;
  final DateTime? startedAt;
  final DateTime? completedAt;

  DroneFlight({
    required this.id,
    required this.farmId,
    required this.droneId,
    required this.backendType,
    required this.status,
    required this.homeLatitude,
    required this.homeLongitude,
    required this.weatherTemperatureC,
    required this.weatherConditions,
    required this.weatherFlightSuitable,
    required this.weatherWarnings,
    required this.weatherDiseasePressure,
    required this.startedAt,
    required this.completedAt,
  });

  factory DroneFlight.fromJson(Map<String, dynamic> json) => DroneFlight(
        id: json['id'] as int,
        farmId: json['farm_id'] as int,
        droneId: json['drone_id'] as String,
        backendType: json['backend_type'] as String,
        status: json['status'] as String,
        homeLatitude: (json['home_latitude'] as num).toDouble(),
        homeLongitude: (json['home_longitude'] as num).toDouble(),
        weatherTemperatureC: (json['weather_temperature_c'] as num?)?.toDouble(),
        weatherConditions: json['weather_conditions'] as String?,
        weatherFlightSuitable: json['weather_flight_suitable'] as bool?,
        weatherWarnings: (json['weather_warnings'] as List?)?.map((e) => e as String).toList(),
        weatherDiseasePressure: json['weather_disease_pressure'] as String?,
        startedAt: json['started_at'] == null ? null : DateTime.parse(json['started_at'] as String),
        completedAt: json['completed_at'] == null ? null : DateTime.parse(json['completed_at'] as String),
      );
}

/// Mirrors app/schemas/drone.py's DroneImageAnalysisResponse.
class DroneImageAnalysis {
  final double? ndvi;
  final String? healthStatus;
  final String? stressLevel;
  final double? canopyCoveragePct;
  final String? vigorLevel;

  DroneImageAnalysis({
    required this.ndvi,
    required this.healthStatus,
    required this.stressLevel,
    required this.canopyCoveragePct,
    required this.vigorLevel,
  });

  factory DroneImageAnalysis.fromJson(Map<String, dynamic> json) => DroneImageAnalysis(
        ndvi: (json['ndvi'] as num?)?.toDouble(),
        healthStatus: json['health_status'] as String?,
        stressLevel: json['stress_level'] as String?,
        canopyCoveragePct: (json['canopy_coverage_pct'] as num?)?.toDouble(),
        vigorLevel: json['vigor_level'] as String?,
      );
}

/// Mirrors app/schemas/drone.py's DroneImageResponse. rgb_url/nir_url are
/// backend-local file:// paths (see app/services/local_image_storage.py) -
/// there's no static file mount serving local_uploads/ over HTTP, so they
/// can't be loaded as network images here. Deliberately not modeled/shown -
/// same constraint as diagnosis images, whose result screen also only shows
/// the AI's text findings, not the photo.
class DroneImage {
  final int id;
  final int waypointIndex;
  final String? treeId;
  final DroneImageAnalysis? analysis;
  final DateTime? capturedAt;

  DroneImage({
    required this.id,
    required this.waypointIndex,
    required this.treeId,
    required this.analysis,
    required this.capturedAt,
  });

  factory DroneImage.fromJson(Map<String, dynamic> json) => DroneImage(
        id: json['id'] as int,
        waypointIndex: json['waypoint_index'] as int,
        treeId: json['tree_id'] as String?,
        analysis: json['analysis'] == null ? null : DroneImageAnalysis.fromJson(json['analysis'] as Map<String, dynamic>),
        capturedAt: json['captured_at'] == null ? null : DateTime.parse(json['captured_at'] as String),
      );
}

/// Mirrors app/schemas/drone.py's FlightAnalysisSummary.
class FlightAnalysisSummary {
  final int imageCount;
  final double? meanNdvi;
  final Map<String, int> healthStatusHistogram;
  final double? meanCanopyCoveragePct;
  final Map<String, int> vigorLevelHistogram;

  FlightAnalysisSummary({
    required this.imageCount,
    required this.meanNdvi,
    required this.healthStatusHistogram,
    required this.meanCanopyCoveragePct,
    required this.vigorLevelHistogram,
  });

  factory FlightAnalysisSummary.fromJson(Map<String, dynamic> json) => FlightAnalysisSummary(
        imageCount: json['image_count'] as int,
        meanNdvi: (json['mean_ndvi'] as num?)?.toDouble(),
        healthStatusHistogram: (json['health_status_histogram'] as Map).map((k, v) => MapEntry(k as String, v as int)),
        meanCanopyCoveragePct: (json['mean_canopy_coverage_pct'] as num?)?.toDouble(),
        vigorLevelHistogram: (json['vigor_level_histogram'] as Map).map((k, v) => MapEntry(k as String, v as int)),
      );
}
