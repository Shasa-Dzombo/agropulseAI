/// Thrown for any non-2xx API response or network failure. Carries the
/// backend's `detail` message (FastAPI's standard error shape) when present,
/// so screens can show it directly instead of a generic "something broke".
class ApiException implements Exception {
  final int? statusCode;
  final String message;

  ApiException(this.message, {this.statusCode});

  factory ApiException.network(Object error) =>
      ApiException('Could not reach the server. Check your connection and try again.');

  @override
  String toString() => message;
}
