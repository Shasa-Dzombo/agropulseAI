import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:http_parser/http_parser.dart';
import 'package:mime/mime.dart';

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

  /// Multipart file upload (e.g. POST /diagnoses/upload-image). Kept separate
  /// from [_send] - multipart requests don't share its JSON-body shape - but
  /// mirrors its auth-header and refresh-on-401 handling.
  Future<dynamic> uploadFile(
    String path, {
    required String fieldName,
    required List<int> bytes,
    required String filename,
    Map<String, String>? fields,
    bool isRetry = false,
  }) async {
    late http.StreamedResponse streamed;
    try {
      final request = http.MultipartRequest('POST', _uri(path));
      final token = await TokenStorage.instance.accessToken;
      if (token != null) request.headers['Authorization'] = 'Bearer $token';
      if (fields != null) request.fields.addAll(fields);
      // http.MultipartFile.fromBytes sends no Content-Type by default, which
      // makes the backend's `file.content_type.startswith("image/")` check
      // reject the upload outright ("File must be an image") even for a
      // real image - look it up from the filename instead of leaving it unset.
      final mimeType = lookupMimeType(filename) ?? 'application/octet-stream';
      request.files.add(http.MultipartFile.fromBytes(
        fieldName,
        bytes,
        filename: filename,
        contentType: MediaType.parse(mimeType),
      ));
      streamed = await request.send();
    } catch (e) {
      throw ApiException.network(e);
    }

    final response = await http.Response.fromStream(streamed);

    if (response.statusCode == 401 && !isRetry && refreshAccessToken != null) {
      final refreshed = await refreshAccessToken!();
      if (refreshed) {
        return uploadFile(path, fieldName: fieldName, bytes: bytes, filename: filename, fields: fields, isRetry: true);
      }
    }

    if (response.statusCode >= 200 && response.statusCode < 300) {
      return jsonDecode(response.body);
    }
    throw ApiException(_extractDetail(response), statusCode: response.statusCode);
  }

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
