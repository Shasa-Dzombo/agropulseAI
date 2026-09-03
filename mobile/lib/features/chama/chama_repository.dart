import '../../core/api_client.dart';
import 'chama_models.dart';

class ChamaRepository {
  ChamaRepository._();
  static final instance = ChamaRepository._();

  final _api = ApiClient.instance;

  Future<List<Chama>> listChamas({bool mineOnly = false}) async {
    final json = await _api.get('/chamas', auth: true, query: {'mine_only': mineOnly});
    return (json as List).map((e) => Chama.fromJson(e as Map<String, dynamic>)).toList();
  }

  Future<Chama> createChama({
    required String name,
    String? description,
    String chamaType = 'savings',
    double? monthlyContributionKsh,
    bool isPublic = true,
    String? mpesaPaybillNumber,
  }) async {
    final json = await _api.post('/chamas', auth: true, body: {
      'name': name,
      'description': ?description,
      'chama_type': chamaType,
      'monthly_contribution_ksh': ?monthlyContributionKsh,
      'is_public': isPublic,
      'mpesa_paybill_number': ?mpesaPaybillNumber,
    });
    return Chama.fromJson(json as Map<String, dynamic>);
  }

  Future<Chama> getChama(int chamaId) async {
    final json = await _api.get('/chamas/$chamaId', auth: true);
    return Chama.fromJson(json as Map<String, dynamic>);
  }

  Future<Chama> joinChama(int chamaId) async {
    final json = await _api.post('/chamas/$chamaId/join', auth: true);
    return Chama.fromJson(json as Map<String, dynamic>);
  }

  Future<List<ChamaMember>> listMembers(int chamaId) async {
    final json = await _api.get('/chamas/$chamaId/members', auth: true);
    return (json as List).map((e) => ChamaMember.fromJson(e as Map<String, dynamic>)).toList();
  }

  Future<List<ChamaMember>> listJoinRequests(int chamaId) async {
    final json = await _api.get('/chamas/$chamaId/join-requests', auth: true);
    return (json as List).map((e) => ChamaMember.fromJson(e as Map<String, dynamic>)).toList();
  }

  Future<void> approveJoinRequest(int chamaId, int userId) async {
    await _api.post('/chamas/$chamaId/join-requests/$userId/approve', auth: true);
  }

  Future<void> rejectJoinRequest(int chamaId, int userId) async {
    await _api.post('/chamas/$chamaId/join-requests/$userId/reject', auth: true);
  }

  Future<Contribution> recordContribution(
    int chamaId, {
    required double amountKsh,
    String? paymentMethod,
    String? notes,
  }) async {
    final json = await _api.post('/chamas/$chamaId/contributions', auth: true, body: {
      'amount_ksh': amountKsh,
      'payment_method': ?paymentMethod,
      'notes': ?notes,
    });
    return Contribution.fromJson(json as Map<String, dynamic>);
  }

  Future<List<Contribution>> listContributions(int chamaId) async {
    final json = await _api.get('/chamas/$chamaId/contributions', auth: true);
    return (json as List).map((e) => Contribution.fromJson(e as Map<String, dynamic>)).toList();
  }
}
