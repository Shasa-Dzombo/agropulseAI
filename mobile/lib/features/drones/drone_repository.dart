import 'dart:typed_data';

import 'package:latlong2/latlong.dart';

import '../../core/api_client.dart';
import 'drone_models.dart';

List<Map<String, double>> _encodeBoundary(List<LatLng> points) =>
    points.map((p) => {'lat': p.latitude, 'lng': p.longitude}).toList();

class KmlBoundaryResult {
  final List<LatLng> points;
  final List<String> warnings;
  KmlBoundaryResult({required this.points, required this.warnings});
}

/// Mirrors app/schemas/drone.py's SavedBoundaryResponse - a named, reusable
/// survey-area shape for a farm (app.models.database.SavedFlightBoundary),
/// distinct from DroneFlight.boundaryPolygon (the shape on one specific
/// flight - saving/loading a template never touches a flight by itself).
class SavedBoundary {
  final int id;
  final int farmId;
  final String name;
  final List<LatLng> polygon;
  final DateTime createdAt;

  SavedBoundary({required this.id, required this.farmId, required this.name, required this.polygon, required this.createdAt});

  factory SavedBoundary.fromJson(Map<String, dynamic> json) => SavedBoundary(
        id: json['id'] as int,
        farmId: json['farm_id'] as int,
        name: json['name'] as String,
        polygon: (json['polygon'] as List).map((p) => LatLng((p['lat'] as num).toDouble(), (p['lng'] as num).toDouble())).toList(),
        createdAt: DateTime.parse(json['created_at'] as String),
      );
}

class DroneRepository {
  DroneRepository._();
  static final instance = DroneRepository._();

  final _api = ApiClient.instance;

  Future<List<DroneFlight>> listFlights(int farmId) async {
    final json = await _api.get('/drones/flights', auth: true, query: {'farm_id': farmId});
    return (json as List).map((e) => DroneFlight.fromJson(e as Map<String, dynamic>)).toList();
  }

  Future<DroneFlight> createFlight({
    required int farmId,
    required String droneId,
    required double homeLatitude,
    required double homeLongitude,
    List<LatLng>? boundaryPolygon,
    List<String>? surveyGoals,
    String? surveyNotes,
  }) async {
    final json = await _api.post('/drones/flights/manual', auth: true, body: {
      'farm_id': farmId,
      'drone_id': droneId,
      'home_latitude': homeLatitude,
      'home_longitude': homeLongitude,
      if (boundaryPolygon != null) 'boundary_polygon': _encodeBoundary(boundaryPolygon),
      if (surveyGoals != null && surveyGoals.isNotEmpty) 'survey_goals': surveyGoals,
      if (surveyNotes != null && surveyNotes.isNotEmpty) 'survey_notes': surveyNotes,
    });
    return DroneFlight.fromJson(json as Map<String, dynamic>);
  }

  Future<DroneFlight> getFlight(int flightId) async {
    final json = await _api.get('/drones/flights/$flightId', auth: true);
    return DroneFlight.fromJson(json as Map<String, dynamic>);
  }

  Future<DroneFlight> completeFlight(int flightId, {required bool completed}) async {
    final json = await _api.post('/drones/flights/$flightId/complete', auth: true, body: {
      'status': completed ? 'completed' : 'aborted',
    });
    return DroneFlight.fromJson(json as Map<String, dynamic>);
  }

  /// Only operational metadata is editable - see UpdateFlightRequest on
  /// the backend for why (home coordinates/status aren't touched here).
  Future<DroneFlight> updateFlight(int flightId, {String? droneId, double? targetAltitudeM, List<LatLng>? boundaryPolygon}) async {
    final json = await _api.patch('/drones/flights/$flightId', auth: true, body: {
      'drone_id': ?droneId,
      'target_altitude_m': ?targetAltitudeM,
      if (boundaryPolygon != null) 'boundary_polygon': _encodeBoundary(boundaryPolygon),
    });
    return DroneFlight.fromJson(json as Map<String, dynamic>);
  }

  Future<void> deleteFlight(int flightId) async {
    await _api.delete('/drones/flights/$flightId', auth: true);
  }

  Future<void> deleteImage(int flightId, int imageId) async {
    await _api.delete('/drones/flights/$flightId/images/$imageId', auth: true);
  }

  Future<DroneImage> uploadImage(int flightId, Uint8List rgbBytes, String filename, {String? treeId}) async {
    final json = await _api.uploadFile(
      '/drones/flights/$flightId/images',
      fieldName: 'rgb',
      bytes: rgbBytes,
      filename: filename,
      fields: treeId == null || treeId.isEmpty ? null : {'tree_id': treeId},
    );
    return DroneImage.fromJson(json as Map<String, dynamic>);
  }

  Future<List<DroneImage>> listImages(int flightId) async {
    final json = await _api.get('/drones/flights/$flightId/images', auth: true);
    return (json as List).map((e) => DroneImage.fromJson(e as Map<String, dynamic>)).toList();
  }

  /// On-demand deep AI read of one photo (~15-20s, a real network call to
  /// the configured LLM_PROVIDER) - not run automatically per photo. See
  /// DroneAIService.analyze_image.
  Future<DroneImage> analyzeImage(int flightId, int imageId) async {
    final json = await _api.post('/drones/flights/$flightId/images/$imageId/analyze', auth: true);
    return DroneImage.fromJson(json as Map<String, dynamic>);
  }

  /// Parses an uploaded .kml file's Polygon/LineString into boundary points -
  /// review/adjust on the map (DroneBoundaryMapScreen) before saving, same
  /// as a hand-traced boundary. Doesn't touch any flight - see
  /// app.services.kml_mission_parser.parse_kml_boundary.
  Future<KmlBoundaryResult> parseKmlBoundary(Uint8List bytes, String filename) async {
    final json = await _api.uploadFile(
      '/drones/flights/parse-kml-boundary',
      fieldName: 'file',
      bytes: bytes,
      filename: filename,
    );
    final map = json as Map<String, dynamic>;
    return KmlBoundaryResult(
      points: (map['points'] as List).map((p) => LatLng((p['lat'] as num).toDouble(), (p['lng'] as num).toDouble())).toList(),
      warnings: (map['warnings'] as List?)?.cast<String>() ?? const [],
    );
  }

  Future<SavedBoundary> createSavedBoundary(int farmId, {required String name, required List<LatLng> polygon}) async {
    final json = await _api.post('/drones/farms/$farmId/boundaries', auth: true, body: {
      'name': name,
      'polygon': _encodeBoundary(polygon),
    });
    return SavedBoundary.fromJson(json as Map<String, dynamic>);
  }

  Future<List<SavedBoundary>> listSavedBoundaries(int farmId) async {
    final json = await _api.get('/drones/farms/$farmId/boundaries', auth: true);
    return (json as List).map((e) => SavedBoundary.fromJson(e as Map<String, dynamic>)).toList();
  }

  Future<SavedBoundary> renameSavedBoundary(int boundaryId, String name) async {
    final json = await _api.patch('/drones/boundaries/$boundaryId', auth: true, body: {'name': name});
    return SavedBoundary.fromJson(json as Map<String, dynamic>);
  }

  Future<void> deleteSavedBoundary(int boundaryId) async {
    await _api.delete('/drones/boundaries/$boundaryId', auth: true);
  }

  Future<FlightAnalysisSummary> getAnalysisSummary(int flightId) async {
    final json = await _api.get('/drones/flights/$flightId/analysis', auth: true);
    return FlightAnalysisSummary.fromJson(json as Map<String, dynamic>);
  }
}
