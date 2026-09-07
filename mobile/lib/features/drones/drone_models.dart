import 'package:latlong2/latlong.dart';

/// Plain-language wording for DroneImageAnalysis.healthStatus/vigorLevel,
/// shared by the capture-result card and the flight's captured-images list
/// so a farmer sees the same wording everywhere instead of raw enum values
/// like "dead" or "moderate_stress". See DroneImage.hasRealNir: this app's
/// NDVI is currently always an estimate, not a real infrared reading.
String plainHealthLabel(String? healthStatus) {
  switch (healthStatus) {
    case 'healthy':
      return 'Looks healthy';
    case 'mild_stress':
      return 'Slight stress signs';
    case 'moderate_stress':
      return 'Moderate stress signs';
    case 'severe_stress':
      return 'Significant stress signs';
    case 'dead':
      return 'No live vegetation detected';
    default:
      return 'Not enough signal to assess';
  }
}

String? plainVigorLabel(String? vigorLevel) {
  switch (vigorLevel) {
    case 'good':
      return 'good canopy vigor';
    case 'moderate':
      return 'moderate canopy vigor';
    case 'low':
      return 'low canopy vigor';
    default:
      return null;
  }
}

/// Mirrors app/schemas/drone.py's DroneFlightResponse.
class DroneFlight {
  final int id;
  final int farmId;
  final String droneId;
  final String backendType;
  final String status;
  final double homeLatitude;
  final double homeLongitude;
  // Traced survey-area boundary - a shape, not a flight path. Null until the
  // farmer draws or imports one (see DroneBoundaryMapScreen).
  final List<LatLng>? boundaryPolygon;
  // What the farmer wants out of this survey - any of "count"/"health" - and
  // any free-text context, set once at flight creation. Steers the on-demand
  // AI analysis per photo (see DroneDiagnosis).
  final List<String>? surveyGoals;
  final String? surveyNotes;
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
    required this.boundaryPolygon,
    required this.surveyGoals,
    required this.surveyNotes,
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
        boundaryPolygon: (json['boundary_polygon'] as List?)
            ?.map((p) => LatLng((p['lat'] as num).toDouble(), (p['lng'] as num).toDouble()))
            .toList(),
        surveyGoals: (json['survey_goals'] as List?)?.cast<String>(),
        surveyNotes: json['survey_notes'] as String?,
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
  final List<String> stressIndicators;
  final List<String> vigorIndicators;
  // Whether app/services/canopy_overlay_rendering produced an annotated
  // copy of the photo - never guaranteed (render/upload failures never
  // block ingestion), so check this before trying to load one.
  final bool hasOverlay;

  DroneImageAnalysis({
    required this.ndvi,
    required this.healthStatus,
    required this.stressLevel,
    required this.canopyCoveragePct,
    required this.vigorLevel,
    required this.stressIndicators,
    required this.vigorIndicators,
    required this.hasOverlay,
  });

  factory DroneImageAnalysis.fromJson(Map<String, dynamic> json) => DroneImageAnalysis(
        ndvi: (json['ndvi'] as num?)?.toDouble(),
        healthStatus: json['health_status'] as String?,
        stressLevel: json['stress_level'] as String?,
        canopyCoveragePct: (json['canopy_coverage_pct'] as num?)?.toDouble(),
        vigorLevel: json['vigor_level'] as String?,
        hasOverlay: json['overlay_url'] != null,
        stressIndicators: (json['stress_indicators'] as List?)?.cast<String>() ?? const [],
        vigorIndicators: (json['vigor_indicators'] as List?)?.cast<String>() ?? const [],
      );
}

/// Mirrors app/schemas/drone.py's DroneImageResponse. rgb_url/nir_url
/// themselves are backend-local file:// paths (see
/// app/services/local_image_storage.py) and stay unmodeled here - but the
/// actual photo/overlay bytes ARE viewable, via the ownership-checked
/// GET /drones/flights/{flightId}/images/{id}/rgb|overlay endpoints (see
/// DroneImageView) rather than the raw file:// URL. nir_url's presence IS
/// modeled (as hasRealNir, not the url itself): the backend only sets it
/// when a real infrared file was uploaded alongside the RGB photo. The
/// mobile capture flow never sends one, so hasRealNir is currently always
/// false here - NDVI on every photo taken through this app is approximated
/// from the RGB green channel (see app/drones/flight/camera.py's
/// green_channel_as_nir_placeholder), not a real infrared reading. The
/// result screen uses this to show an honest caveat instead of stating
/// "dead"/a precise NDVI number with false confidence.
/// Mirrors app/schemas/drone.py's DiseaseAnswer - the on-demand deep AI read
/// from POST .../images/{id}/analyze (see DroneAIService.analyze_image),
/// distinct from DroneImageAnalysis above (the always-on, free, local NDVI/
/// vigor read every photo already gets). Null until the farmer taps to
/// request it.
class DroneDiagnosis {
  final String? diseaseName;
  final double? confidence;
  final String? severity;
  final bool isHealthy;
  final List<String> topTreatmentActions;
  // Only non-null when the flight's survey_goals included "count".
  final int? estimatedCount;
  final String? countNotes;

  DroneDiagnosis({
    required this.diseaseName,
    required this.confidence,
    required this.severity,
    required this.isHealthy,
    required this.topTreatmentActions,
    required this.estimatedCount,
    required this.countNotes,
  });

  factory DroneDiagnosis.fromJson(Map<String, dynamic> json) => DroneDiagnosis(
        diseaseName: json['disease_name'] as String?,
        confidence: (json['confidence'] as num?)?.toDouble(),
        severity: json['severity'] as String?,
        isHealthy: json['is_healthy'] as bool? ?? false,
        topTreatmentActions: (json['top_treatment_actions'] as List?)?.cast<String>() ?? const [],
        estimatedCount: json['estimated_count'] as int?,
        countNotes: json['count_notes'] as String?,
      );
}

class DroneImage {
  final int id;
  final int flightId;
  final int waypointIndex;
  final String? treeId;
  final DroneImageAnalysis? analysis;
  final DroneDiagnosis? diagnosis;
  final DateTime? capturedAt;
  final bool hasRealNir;

  DroneImage({
    required this.id,
    required this.flightId,
    required this.waypointIndex,
    required this.treeId,
    required this.analysis,
    required this.diagnosis,
    required this.capturedAt,
    required this.hasRealNir,
  });

  factory DroneImage.fromJson(Map<String, dynamic> json) => DroneImage(
        id: json['id'] as int,
        flightId: json['flight_id'] as int,
        waypointIndex: json['waypoint_index'] as int,
        treeId: json['tree_id'] as String?,
        analysis: json['analysis'] == null ? null : DroneImageAnalysis.fromJson(json['analysis'] as Map<String, dynamic>),
        diagnosis: json['diagnosis'] == null ? null : DroneDiagnosis.fromJson(json['diagnosis'] as Map<String, dynamic>),
        capturedAt: json['captured_at'] == null ? null : DateTime.parse(json['captured_at'] as String),
        hasRealNir: json['nir_url'] != null,
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
