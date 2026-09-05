// Guards against drift from app/schemas/friend.py's response shapes -
// matches actual live responses captured while wiring app/api/friends.py
// (see mobile/CHANGELOG.md).

import 'package:flutter_test/flutter_test.dart';
import 'package:agropulse_mobile/features/friends/friend_models.dart';

void main() {
  test('NearbyFarmer.fromJson parses a real nearby-farmer row with public chamas', () {
    final farmer = NearbyFarmer.fromJson({
      'id': 518, 'name': 'Nakuru Neighbor', 'county': 'Nakuru',
      'is_friend': false, 'request_pending': false,
      'public_chamas': [
        {'id': 3, 'name': 'Nakuru Farmers Savings Group'},
      ],
    });

    expect(farmer.isFriend, isFalse);
    expect(farmer.publicChamas, hasLength(1));
    expect(farmer.publicChamas.first.name, 'Nakuru Farmers Savings Group');
  });

  test('IncomingFriendRequest.fromJson parses a real pending request', () {
    final request = IncomingFriendRequest.fromJson({
      'id': 1, 'requester_id': 514, 'requester_name': 'Farm Tester',
      'requester_county': 'Nakuru', 'created_at': '2026-09-05T07:37:35.765356Z',
    });

    expect(request.requesterName, 'Farm Tester');
    expect(request.createdAt, DateTime.parse('2026-09-05T07:37:35.765356Z'));
  });

  test('Friend.fromJson parses a real accepted friend', () {
    final friend = Friend.fromJson({
      'id': 518, 'name': 'Nakuru Neighbor', 'county': 'Nakuru',
      'friends_since': '2026-09-05T07:38:14.694762Z',
    });

    expect(friend.friendsSince, isNotNull);
  });
}
