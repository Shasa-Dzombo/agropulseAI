import 'dart:async';

import 'package:camera/camera.dart';
import 'package:flutter/material.dart';

import '../../core/api_exception.dart';
import 'drone_analysis_tracker.dart';
import 'drone_image_view.dart';
import 'drone_repository.dart';

/// "Forget NDVI, just stream frames to the AI" mode - a fixed-interval
/// auto-capture loop (not a real video stream; genuinely live per-frame NDVI
/// plus a real video pipeline is a much bigger lift than this, see
/// mobile/CHANGELOG.md's 2026-09-07 video-stream-feasibility entry). Every
/// photo captured here uploads and is immediately queued into
/// DroneAnalysisTracker - no per-photo "Analyze with AI" tap, matching the
/// user's own framing: skip the NDVI gate, send frames straight to the AI.
class DroneScanScreen extends StatefulWidget {
  final int flightId;

  const DroneScanScreen({super.key, required this.flightId});

  @override
  State<DroneScanScreen> createState() => _DroneScanScreenState();
}

class _ScannedPhoto {
  final int imageId;
  _ScannedPhoto({required this.imageId});
}

class _DroneScanScreenState extends State<DroneScanScreen> with WidgetsBindingObserver {
  CameraController? _controller;
  Future<void>? _initFuture;
  String? _cameraError;

  bool _scanning = false;
  int _intervalSeconds = 10;
  Timer? _timer;
  bool _capturing = false;

  final List<_ScannedPhoto> _captured = [];
  int _failedCount = 0;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    _initCamera();
  }

  Future<void> _initCamera() async {
    try {
      final cameras = await availableCameras();
      final back = cameras.firstWhere((c) => c.lensDirection == CameraLensDirection.back, orElse: () => cameras.first);
      final controller = CameraController(back, ResolutionPreset.high, enableAudio: false);
      _controller = controller;
      setState(() => _initFuture = controller.initialize());
      await _initFuture;
    } catch (e) {
      setState(() => _cameraError = 'Could not start the camera: $e');
    }
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    final controller = _controller;
    if (controller == null || !controller.value.isInitialized) return;
    if (state == AppLifecycleState.inactive || state == AppLifecycleState.paused) {
      _stopScanning();
      controller.dispose();
    } else if (state == AppLifecycleState.resumed) {
      _initCamera();
    }
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    _timer?.cancel();
    _controller?.dispose();
    super.dispose();
  }

  void _startScanning() {
    setState(() => _scanning = true);
    _captureOne();
    _timer = Timer.periodic(Duration(seconds: _intervalSeconds), (_) => _captureOne());
  }

  void _stopScanning() {
    _timer?.cancel();
    _timer = null;
    if (mounted) setState(() => _scanning = false);
  }

  Future<void> _captureOne() async {
    final controller = _controller;
    if (controller == null || !controller.value.isInitialized || _capturing) return;
    _capturing = true;
    try {
      final file = await controller.takePicture();
      final bytes = await file.readAsBytes();
      final image = await DroneRepository.instance.uploadImage(widget.flightId, bytes, file.name);
      if (!mounted) return;
      setState(() => _captured.insert(0, _ScannedPhoto(imageId: image.id)));
      // Fire-and-forget: queued in the tracker, keeps running even if the
      // farmer stops scanning or leaves this screen before it resolves -
      // see DroneAnalysisTracker.
      DroneAnalysisTracker.instance.start(widget.flightId, image.id).catchError((_) => image);
      if (mounted) setState(() {});
    } on ApiException {
      if (mounted) setState(() => _failedCount++);
    } catch (_) {
      if (mounted) setState(() => _failedCount++);
    } finally {
      _capturing = false;
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Scan mode'),
        actions: [
          if (!_scanning)
            PopupMenuButton<int>(
              tooltip: 'Capture interval',
              initialValue: _intervalSeconds,
              onSelected: (v) => setState(() => _intervalSeconds = v),
              itemBuilder: (context) => const [
                PopupMenuItem(value: 5, child: Text('Every 5 seconds')),
                PopupMenuItem(value: 10, child: Text('Every 10 seconds')),
                PopupMenuItem(value: 15, child: Text('Every 15 seconds')),
                PopupMenuItem(value: 30, child: Text('Every 30 seconds')),
              ],
              child: Padding(
                padding: const EdgeInsets.symmetric(horizontal: 16),
                child: Center(child: Text('Every ${_intervalSeconds}s')),
              ),
            ),
        ],
      ),
      body: SafeArea(
        child: Column(
          children: [
            Container(
              color: Colors.black,
              height: 320,
              width: double.infinity,
              child: _buildPreview(),
            ),
            Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  Text(
                    'Every photo is uploaded and sent straight to the AI - no NDVI review step. '
                    'Each analysis is a real ~15-20s call, so results trickle in below over the next few minutes.',
                    style: TextStyle(color: Colors.black54, fontSize: 12),
                  ),
                  const SizedBox(height: 12),
                  FilledButton.icon(
                    onPressed: _cameraError != null ? null : (_scanning ? _stopScanning : _startScanning),
                    icon: Icon(_scanning ? Icons.stop_circle_outlined : Icons.play_circle_outline),
                    label: Text(_scanning ? 'Stop scanning' : 'Start scanning'),
                    style: _scanning ? FilledButton.styleFrom(backgroundColor: Colors.red) : null,
                  ),
                  if (_captured.isNotEmpty || _failedCount > 0)
                    Padding(
                      padding: const EdgeInsets.only(top: 8),
                      child: Text(
                        '${_captured.length} captured${_failedCount > 0 ? ' · $_failedCount failed to upload' : ''}',
                        style: const TextStyle(color: Colors.black54, fontSize: 12),
                      ),
                    ),
                ],
              ),
            ),
            const Divider(height: 1),
            Expanded(
              child: _captured.isEmpty
                  ? const Center(child: Text('Captured photos will appear here', style: TextStyle(color: Colors.black45)))
                  : ListView.builder(
                      itemCount: _captured.length,
                      itemBuilder: (context, index) {
                        final photo = _captured[index];
                        final analyzing = DroneAnalysisTracker.instance.isPending(photo.imageId);
                        return ListTile(
                          leading: ClipRRect(
                            borderRadius: BorderRadius.circular(6),
                            child: SizedBox(
                              width: 44,
                              height: 44,
                              child: DroneImageView(flightId: widget.flightId, imageId: photo.imageId),
                            ),
                          ),
                          title: Text('Photo ${_captured.length - index}'),
                          trailing: analyzing
                              ? const SizedBox(
                                  height: 16,
                                  width: 16,
                                  child: CircularProgressIndicator(strokeWidth: 2),
                                )
                              : const Icon(Icons.check_circle, color: Colors.green, size: 20),
                          subtitle: Text(analyzing ? 'Analyzing...' : 'Queued/done - view in the flight\'s photo list'),
                        );
                      },
                    ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildPreview() {
    if (_cameraError != null) {
      return Center(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Text(_cameraError!, style: const TextStyle(color: Colors.white), textAlign: TextAlign.center),
        ),
      );
    }
    final controller = _controller;
    final initFuture = _initFuture;
    if (controller == null || initFuture == null) {
      return const Center(child: CircularProgressIndicator());
    }
    return FutureBuilder<void>(
      future: initFuture,
      builder: (context, snapshot) {
        if (snapshot.connectionState != ConnectionState.done) {
          return const Center(child: CircularProgressIndicator());
        }
        return ClipRect(child: CameraPreview(controller));
      },
    );
  }
}
