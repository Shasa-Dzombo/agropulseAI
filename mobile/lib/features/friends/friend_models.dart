/// Mirrors app/schemas/friend.py's ChamaSummary.
class ChamaSummary {
  final int id;
  final String name;

  ChamaSummary({required this.id, required this.name});

  factory ChamaSummary.fromJson(Map<String, dynamic> json) =>
      ChamaSummary(id: json['id'] as int, name: json['name'] as String);
}

/// Mirrors app/schemas/friend.py's NearbyFarmerResponse. "Nearby" means same
/// county (User.county), not GPS distance - see app/api/friends.py's
/// docstring for why.
class NearbyFarmer {
  final int id;
  final String name;
  final String? county;
  final bool isFriend;
  final bool requestPending;
  final List<ChamaSummary> publicChamas;

  NearbyFarmer({
    required this.id,
    required this.name,
    required this.county,
    required this.isFriend,
    required this.requestPending,
    required this.publicChamas,
  });

  factory NearbyFarmer.fromJson(Map<String, dynamic> json) => NearbyFarmer(
        id: json['id'] as int,
        name: json['name'] as String,
        county: json['county'] as String?,
        isFriend: json['is_friend'] as bool,
        requestPending: json['request_pending'] as bool,
        publicChamas: (json['public_chamas'] as List).map((e) => ChamaSummary.fromJson(e as Map<String, dynamic>)).toList(),
      );
}

/// Mirrors app/schemas/friend.py's FriendRequestResponse - an incoming,
/// still-pending request from someone else.
class IncomingFriendRequest {
  final int id;
  final int requesterId;
  final String requesterName;
  final String? requesterCounty;
  final DateTime createdAt;

  IncomingFriendRequest({
    required this.id,
    required this.requesterId,
    required this.requesterName,
    required this.requesterCounty,
    required this.createdAt,
  });

  factory IncomingFriendRequest.fromJson(Map<String, dynamic> json) => IncomingFriendRequest(
        id: json['id'] as int,
        requesterId: json['requester_id'] as int,
        requesterName: json['requester_name'] as String,
        requesterCounty: json['requester_county'] as String?,
        createdAt: DateTime.parse(json['created_at'] as String),
      );
}

/// Mirrors app/schemas/friend.py's FriendResponse.
class Friend {
  final int id;
  final String name;
  final String? county;
  final DateTime? friendsSince;

  Friend({required this.id, required this.name, required this.county, required this.friendsSince});

  factory Friend.fromJson(Map<String, dynamic> json) => Friend(
        id: json['id'] as int,
        name: json['name'] as String,
        county: json['county'] as String?,
        friendsSince: json['friends_since'] == null ? null : DateTime.parse(json['friends_since'] as String),
      );
}
