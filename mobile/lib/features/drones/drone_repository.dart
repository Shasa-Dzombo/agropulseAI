import 'dart:typed_data';

import '../../core/api_client.dart';
import 'drone_models.dart';

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
  }) async {
    final json = await _api.post('/drones/flights/manual', auth: true, body: {
      'farm_id': farmId,
      'drone_id': droneId,
      'home_latitude': homeLatitude,
      'home_longitude': homeLongitude,
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

  Future<FlightAnalysisSummary> getAnalysisSummary(int flightId) async {
    final json = await _api.get('/drones/flights/$flightId/analysis', auth: true);
    return FlightAnalysisSummary.fromJson(json as Map<String, dynamic>);
  }
}
