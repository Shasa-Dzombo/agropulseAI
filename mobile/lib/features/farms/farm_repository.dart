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
}
