import '../../core/api_client.dart';
import 'farm_models.dart';

class FarmRepository {
  FarmRepository._();
  static final instance = FarmRepository._();

  final _api = ApiClient.instance;

  Future<PaginatedFarms> listFarms({int page = 1, int pageSize = 20}) async {
    final json = await _api.get('/farms', auth: true, query: {'page': page, 'page_size': pageSize});
    return PaginatedFarms.fromJson(json as Map<String, dynamic>);
  }

  Future<void> createFarm({
    required String name,
    required double latitude,
    required double longitude,
    required double sizeAcres,
    required String county,
    String? farmType,
    String? primaryCrop,
    bool hasIrrigation = false,
  }) async {
    await _api.post('/farms', auth: true, body: {
      'name': name,
      'latitude': latitude,
      'longitude': longitude,
      'size_acres': sizeAcres,
      'county': county,
      'farm_type': ?farmType,
      'primary_crop': ?primaryCrop,
      'has_irrigation': hasIrrigation,
    });
  }
}
