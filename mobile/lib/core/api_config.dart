/// Central place for the backend base URL.
///
/// The Android emulator can't reach the host machine via `localhost` - it
/// needs the special alias `10.0.2.2`, which routes to the host's loopback.
/// A physical device needs the host's real LAN IP instead (override via
/// `--dart-define=API_BASE_URL=http://<lan-ip>:8030/api/v1` when running).
library;

import 'dart:io' show Platform;
import 'package:flutter/foundation.dart' show kIsWeb;

String get apiBaseUrl {
  const override = String.fromEnvironment('API_BASE_URL');
  if (override.isNotEmpty) return override;

  if (kIsWeb) return 'http://localhost:8030/api/v1';
  if (Platform.isAndroid) return 'http://10.0.2.2:8030/api/v1';
  return 'http://localhost:8030/api/v1'; // iOS simulator, desktop
}
