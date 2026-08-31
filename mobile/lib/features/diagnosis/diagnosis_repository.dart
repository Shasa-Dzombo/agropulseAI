import 'dart:typed_data';

import '../../core/api_client.dart';
import 'diagnosis_models.dart';

class DiagnosisRepository {
  DiagnosisRepository._();
  static final instance = DiagnosisRepository._();

  final _api = ApiClient.instance;

  /// Uploads image bytes and returns the server-side image_url to pass to
  /// [createDiagnosis]. Backend saves to local disk (see app/api/diagnoses.py) -
  /// there's no AWS S3 configured in this environment.
  Future<String> uploadImage(Uint8List bytes, String filename) async {
    final json = await _api.uploadFile(
      '/diagnoses/upload-image',
      fieldName: 'file',
      bytes: bytes,
      filename: filename,
    );
    return json['image_url'] as String;
  }

  Future<Diagnosis> createDiagnosis({required List<String> imageUrls, String? userSymptoms, int? farmId}) async {
    final json = await _api.post('/diagnoses', auth: true, body: {
      'image_urls': imageUrls,
      if (userSymptoms != null && userSymptoms.isNotEmpty) 'user_symptoms': userSymptoms,
      'farm_id': ?farmId,
    });
    return Diagnosis.fromJson(json as Map<String, dynamic>);
  }

  Future<Diagnosis> getDiagnosis(int id) async {
    final json = await _api.get('/diagnoses/$id', auth: true);
    return Diagnosis.fromJson(json as Map<String, dynamic>);
  }

  Future<List<Diagnosis>> listDiagnoses() async {
    final json = await _api.get('/diagnoses', auth: true);
    return (json as List).map((e) => Diagnosis.fromJson(e as Map<String, dynamic>)).toList();
  }
}
