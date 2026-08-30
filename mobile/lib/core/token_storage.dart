import 'package:flutter_secure_storage/flutter_secure_storage.dart';

/// Persists auth tokens outside plain SharedPreferences - these unlock paid
/// diagnosis permits and farm data, so they get the platform keystore
/// (Android Keystore / iOS Keychain) rather than plaintext storage.
class TokenStorage {
  TokenStorage._();
  static final instance = TokenStorage._();

  final _storage = const FlutterSecureStorage();

  static const _accessKey = 'access_token';
  static const _refreshKey = 'refresh_token';

  Future<void> save({required String accessToken, required String refreshToken}) async {
    await _storage.write(key: _accessKey, value: accessToken);
    await _storage.write(key: _refreshKey, value: refreshToken);
  }

  Future<String?> get accessToken => _storage.read(key: _accessKey);
  Future<String?> get refreshToken => _storage.read(key: _refreshKey);

  Future<void> clear() async {
    await _storage.delete(key: _accessKey);
    await _storage.delete(key: _refreshKey);
  }
}
