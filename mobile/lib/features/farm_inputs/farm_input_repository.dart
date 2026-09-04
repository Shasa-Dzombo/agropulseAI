import '../../core/api_client.dart';
import 'farm_input_models.dart';

class FarmInputRepository {
  FarmInputRepository._();
  static final instance = FarmInputRepository._();

  final _api = ApiClient.instance;

  Future<FarmInputRecord> createInputRecord(
    int farmId, {
    required String entryType,
    required String category,
    required String itemName,
    double? quantity,
    String? unit,
    double? costKsh,
    String? notes,
    required DateTime entryDate,
  }) async {
    final json = await _api.post('/farms/$farmId/inputs', auth: true, body: {
      'entry_type': entryType,
      'category': category,
      'item_name': itemName,
      'quantity': ?quantity,
      'unit': ?unit,
      'cost_ksh': ?costKsh,
      'notes': ?notes,
      'entry_date': entryDate.toIso8601String().split('T').first,
    });
    return FarmInputRecord.fromJson(json as Map<String, dynamic>);
  }

  Future<FarmInputList> listInputRecords(int farmId, {String? entryType}) async {
    final json = await _api.get('/farms/$farmId/inputs', auth: true, query: {'entry_type': ?entryType});
    return FarmInputList.fromJson(json as Map<String, dynamic>);
  }

  Future<void> deleteInputRecord(int farmId, int recordId) async {
    await _api.delete('/farms/$farmId/inputs/$recordId', auth: true);
  }

  Future<FarmYieldRecord> createYieldRecord(
    int farmId, {
    required String crop,
    required String seasonLabel,
    DateTime? plantedDate,
    double? expectedYieldKg,
  }) async {
    final json = await _api.post('/farms/$farmId/yields', auth: true, body: {
      'crop': crop,
      'season_label': seasonLabel,
      'planted_date': ?plantedDate?.toIso8601String().split('T').first,
      'expected_yield_kg': ?expectedYieldKg,
    });
    return FarmYieldRecord.fromJson(json as Map<String, dynamic>);
  }

  Future<List<FarmYieldRecord>> listYieldRecords(int farmId) async {
    // Backend returns {"items": [...]} (FarmYieldListResponse), not a bare
    // array - matches FarmInputList's shape above.
    final json = await _api.get('/farms/$farmId/yields', auth: true) as Map<String, dynamic>;
    return (json['items'] as List).map((e) => FarmYieldRecord.fromJson(e as Map<String, dynamic>)).toList();
  }

  Future<FarmYieldRecord> recordHarvest(
    int farmId,
    int recordId, {
    required double actualYieldKg,
    DateTime? harvestDate,
    String? notes,
  }) async {
    final json = await _api.patch('/farms/$farmId/yields/$recordId', auth: true, body: {
      'actual_yield_kg': actualYieldKg,
      'harvest_date': ?harvestDate?.toIso8601String().split('T').first,
      'notes': ?notes,
    });
    return FarmYieldRecord.fromJson(json as Map<String, dynamic>);
  }
}
