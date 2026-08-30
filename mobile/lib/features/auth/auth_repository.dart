import '../../core/api_client.dart';
import '../../core/token_storage.dart';
import 'auth_models.dart';

class AuthRepository {
  AuthRepository._() {
    // Let ApiClient call back into us for the refresh-on-401 dance without
    // ApiClient importing this file (would be circular).
    ApiClient.instance.refreshAccessToken = _tryRefresh;
  }
  static final instance = AuthRepository._();

  final _api = ApiClient.instance;
  final _storage = TokenStorage.instance;

  Future<UserInfo> register({
    required String username,
    required String email,
    required String phoneNumber,
    required String password,
    required String fullName,
    String? county,
  }) async {
    final json = await _api.post('/auth/register', body: {
      'username': username,
      'email': email,
      'phone_number': phoneNumber,
      'password': password,
      'full_name': fullName,
      if (county != null && county.isNotEmpty) 'county': county,
    });
    final tokens = AuthTokens.fromJson(json as Map<String, dynamic>);
    await _storage.save(accessToken: tokens.accessToken, refreshToken: tokens.refreshToken);
    return me();
  }

  Future<UserInfo> login({
    required String usernameOrEmail,
    required String password,
    bool rememberMe = false,
  }) async {
    final json = await _api.post('/auth/login', body: {
      'username_or_email': usernameOrEmail,
      'password': password,
      'remember_me': rememberMe,
    });
    final tokens = AuthTokens.fromJson(json as Map<String, dynamic>);
    await _storage.save(accessToken: tokens.accessToken, refreshToken: tokens.refreshToken);
    return me();
  }

  Future<UserInfo> me() async {
    final json = await _api.get('/auth/me', auth: true);
    return UserInfo.fromJson(json as Map<String, dynamic>);
  }

  Future<bool> get isLoggedIn async => (await _storage.accessToken) != null;

  Future<void> logout() async {
    try {
      await _api.post('/auth/logout', auth: true);
    } catch (_) {
      // Best-effort - the token gets discarded client-side regardless.
    }
    await _storage.clear();
  }

  /// Backend's /auth/refresh takes the refresh token as a query param, not
  /// a JSON body (see app/api/auth.py - it's a plain function arg with no
  /// Body() annotation, so FastAPI defaults it to a query param).
  Future<bool> _tryRefresh() async {
    final refreshToken = await _storage.refreshToken;
    if (refreshToken == null) return false;
    try {
      final json = await _api.post('/auth/refresh', query: {'refresh_token': refreshToken});
      final tokens = AuthTokens.fromJson(json as Map<String, dynamic>);
      await _storage.save(accessToken: tokens.accessToken, refreshToken: tokens.refreshToken);
      return true;
    } catch (_) {
      await _storage.clear();
      return false;
    }
  }
}
