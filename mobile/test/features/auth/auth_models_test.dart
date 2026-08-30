// Guards against drift from app/api/auth.py's TokenResponse/UserInfoResponse
// shapes - a silent field-name mismatch here would break login for every
// user, so it's worth a real test rather than just eyeballing it.

import 'package:flutter_test/flutter_test.dart';
import 'package:agropulse_mobile/features/auth/auth_models.dart';

void main() {
  test('AuthTokens.fromJson parses the backend TokenResponse shape', () {
    final tokens = AuthTokens.fromJson({
      'access_token': 'abc',
      'refresh_token': 'def',
      'token_type': 'bearer',
      'expires_in': 1800,
    });

    expect(tokens.accessToken, 'abc');
    expect(tokens.refreshToken, 'def');
    expect(tokens.expiresIn, 1800);
  });

  test('UserInfo.fromJson parses the backend UserInfoResponse shape, including null county', () {
    final user = UserInfo.fromJson({
      'id': 1,
      'uuid': 'uuid-1',
      'username': 'jane',
      'email': 'jane@example.com',
      'phone_number': '+254712345678',
      'full_name': 'Jane Farmer',
      'role': 'farmer',
      'county': null,
      'is_active': true,
      'email_verified': false,
      'phone_verified': false,
      'two_factor_enabled': false,
      'subscription_tier': 'free',
      'created_at': '2026-01-01T00:00:00Z',
    });

    expect(user.username, 'jane');
    expect(user.county, isNull);
    expect(user.subscriptionTier, 'free');
  });
}
