import 'drone_models.dart';
import 'drone_repository.dart';

/// Tracks in-flight "Analyze with AI" calls independently of any screen's
/// widget lifecycle, so navigating away (capture another photo, go back to
/// the flight, close the app to the background) doesn't lose or duplicate
/// the request - the underlying HTTP call keeps running either way (it's a
/// real ~15-20s round trip to the server), this just lets any screen that
/// cares check on it later instead of the result being silently dropped by
/// a disposed widget's `if (!mounted)` guard.
class DroneAnalysisTracker {
  DroneAnalysisTracker._();
  static final instance = DroneAnalysisTracker._();

  final Map<int, Future<DroneImage>> _pending = {};

  bool isPending(int imageId) => _pending.containsKey(imageId);

  /// Starts analysis for [imageId] if not already running, and returns the
  /// (possibly already in-flight) future either way - callers can attach a
  /// listener without caring whether they started it or another screen did.
  Future<DroneImage> start(int flightId, int imageId) {
    final existing = _pending[imageId];
    if (existing != null) return existing;

    final future = DroneRepository.instance.analyzeImage(flightId, imageId);
    _pending[imageId] = future;
    // Always clears on completion (success or failure) - a failed analysis
    // shouldn't permanently block retrying the same photo.
    future.whenComplete(() => _pending.remove(imageId));
    return future;
  }
}
