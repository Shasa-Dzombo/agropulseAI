import 'dart:convert';
import 'package:http/http.dart' as http;

import 'api_config.dart';
import 'api_exception.dart';
import 'token_storage.dart';

/// Thin JSON REST client for the AgroPulse FastAPI backend.
///
/// Handles: base URL resolution, bearer-token attachment, FastAPI's error
/// shape (`{"detail": "..."}`), and a single automatic refresh-and-retry on
/// a 401 so callers don't each have to implement that dance.
class ApiClient {
  ApiClient._();
  static final instance = ApiClient._();

  /// Set once by AuthRepository at app startup. Kept as an injectable
  /// callback (rather than importing AuthRepository directly) to avoid a
  /// circular dependency between the two.
  Future<bool> Function()? refreshAccessToken;

  Uri _uri(String path, [Map<String, dynamic>? query]) => Uri.parse('$apiBaseUrl$path')
      .replace(queryParameters: query?.map((k, v) => MapEntry(k, '$v')));

  Future<Map<String, String>> _headers({bool auth = false}) async {
    final headers = {'Content-Type': 'application/json'};
    if (auth) {
      final token = await TokenStorage.instance.accessToken;
      if (token != null) headers['Authorization'] = 'Bearer $token';
    }
    return headers;
  }

  Future<dynamic> get(String path, {bool auth = false, Map<String, dynamic>? query}) =>
      _send('GET', path, auth: auth, query: query);

  Future<dynamic> post(String path, {Map<String, dynamic>? body, bool auth = false, Map<String, dynamic>? query}) =>
      _send('POST', path, body: body, auth: auth, query: query);

  Future<dynamic> _send(
    String method,
    String path, {
    Map<String, dynamic>? body,
    bool auth = false,
    Map<String, dynamic>? query,
    bool isRetry = false,
  }) async {
    late http.Response response;
    try {
      final uri = _uri(path, query);
      final headers = await _headers(auth: auth);
      final encodedBody = body != null ? jsonEncode(body) : null;
      response = switch (method) {
        'GET' => await http.get(uri, headers: headers),
        'POST' => await http.post(uri, headers: headers, body: encodedBody),
        _ => throw UnsupportedError('Unsupported method $method'),
      };
    } catch (e) {
      throw ApiException.network(e);
    }

    if (response.statusCode == 401 && auth && !isRetry && refreshAccessToken != null) {
      final refreshed = await refreshAccessToken!();
      if (refreshed) {
        return _send(method, path, body: body, auth: auth, query: query, isRetry: true);
      }
    }

    if (response.statusCode >= 200 && response.statusCode < 300) {
      if (response.body.isEmpty) return null;
      return jsonDecode(response.body);
    }

    throw ApiException(_extractDetail(response), statusCode: response.statusCode);
  }

  String _extractDetail(http.Response response) {
    try {
      final decoded = jsonDecode(response.body);
      final detail = decoded is Map ? decoded['detail'] : null;
      if (detail is String) return detail;
      if (detail != null) return detail.toString();
    } catch (_) {
      // Response wasn't JSON (e.g. a raw 500 HTML page) - fall through.
    }
    return 'Request failed (${response.statusCode})';
  }
}
