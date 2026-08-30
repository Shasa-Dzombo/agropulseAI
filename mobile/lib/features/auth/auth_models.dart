/// Mirrors app/api/auth.py's TokenResponse exactly - keep in sync with the backend.
class AuthTokens {
  final String accessToken;
  final String refreshToken;
  final int expiresIn;

  AuthTokens({required this.accessToken, required this.refreshToken, required this.expiresIn});

  factory AuthTokens.fromJson(Map<String, dynamic> json) => AuthTokens(
        accessToken: json['access_token'] as String,
        refreshToken: json['refresh_token'] as String,
        expiresIn: json['expires_in'] as int,
      );
}

/// Mirrors app/api/auth.py's UserInfoResponse.
class UserInfo {
  final int id;
  final String username;
  final String email;
  final String phoneNumber;
  final String fullName;
  final String role;
  final String? county;
  final bool emailVerified;
  final bool phoneVerified;
  final String subscriptionTier;

  UserInfo({
    required this.id,
    required this.username,
    required this.email,
    required this.phoneNumber,
    required this.fullName,
    required this.role,
    required this.county,
    required this.emailVerified,
    required this.phoneVerified,
    required this.subscriptionTier,
  });

  factory UserInfo.fromJson(Map<String, dynamic> json) => UserInfo(
        id: json['id'] as int,
        username: json['username'] as String,
        email: json['email'] as String,
        phoneNumber: json['phone_number'] as String,
        fullName: json['full_name'] as String,
        role: json['role'] as String,
        county: json['county'] as String?,
        emailVerified: json['email_verified'] as bool,
        phoneVerified: json['phone_verified'] as bool,
        subscriptionTier: json['subscription_tier'] as String,
      );
}
