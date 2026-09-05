import '../../core/api_client.dart';
import 'friend_models.dart';

class FriendRepository {
  FriendRepository._();
  static final instance = FriendRepository._();

  final _api = ApiClient.instance;

  Future<List<NearbyFarmer>> listNearbyFarmers() async {
    final json = await _api.get('/users/nearby', auth: true);
    return (json as List).map((e) => NearbyFarmer.fromJson(e as Map<String, dynamic>)).toList();
  }

  Future<void> sendFriendRequest(int recipientId) async {
    await _api.post('/friends/requests', auth: true, body: {'recipient_id': recipientId});
  }

  Future<List<IncomingFriendRequest>> listIncomingRequests() async {
    final json = await _api.get('/friends/requests', auth: true);
    return (json as List).map((e) => IncomingFriendRequest.fromJson(e as Map<String, dynamic>)).toList();
  }

  Future<void> acceptFriendRequest(int requestId) async {
    await _api.post('/friends/requests/$requestId/accept', auth: true);
  }

  Future<void> rejectFriendRequest(int requestId) async {
    await _api.post('/friends/requests/$requestId/reject', auth: true);
  }

  Future<List<Friend>> listFriends() async {
    final json = await _api.get('/friends', auth: true);
    return (json as List).map((e) => Friend.fromJson(e as Map<String, dynamic>)).toList();
  }
}
