import 'dart:io';

import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';

import '../../core/api_exception.dart';
import 'drone_analysis_tracker.dart';
import 'drone_diagnosis_view.dart';
import 'drone_image_view.dart';
import 'drone_models.dart';
import 'drone_ndvi_view.dart';
import 'drone_repository.dart';

class DroneImageCaptureScreen extends StatefulWidget {
  final int flightId;

  const DroneImageCaptureScreen({super.key, required this.flightId});

  @override
  State<DroneImageCaptureScreen> createState() => _DroneImageCaptureScreenState();
}

class _DroneImageCaptureScreenState extends State<DroneImageCaptureScreen> {
  final _picker = ImagePicker();
  final _treeIdController = TextEditingController();
  XFile? _image;
  bool _submitting = false;
  bool _analyzing = false;
  DroneImage? _result;
  bool _bulkUploading = false;
  int _bulkDone = 0;
  int _bulkTotal = 0;

  @override
  void dispose() {
    _treeIdController.dispose();
    super.dispose();
  }

  Future<void> _pickImage(ImageSource source) async {
    final picked = await _picker.pickImage(source: source, maxWidth: 1600, imageQuality: 85);
    if (picked != null) setState(() { _image = picked; _result = null; });
  }

  /// Bulk path for photos already taken elsewhere (e.g. offloaded from the
  /// drone's own SD card into the phone's gallery) - each selected photo
  /// becomes its own DroneImage (uploaded one at a time; the backend has no
  /// batch-upload endpoint), unlike the greenhouse diagnosis flow's
  /// multi-select, which bundles several photos into one diagnosis. No AI
  /// analysis is triggered automatically - that stays a separate, on-demand
  /// step per photo from the flight's photo list once this returns.
  Future<void> _pickMultipleFromGallery() async {
    final picked = await _picker.pickMultiImage(maxWidth: 1600, imageQuality: 85);
    if (picked.isEmpty) return;

    setState(() { _bulkUploading = true; _bulkDone = 0; _bulkTotal = picked.length; });
    var failures = 0;
    for (final image in picked) {
      try {
        final bytes = await image.readAsBytes();
        await DroneRepository.instance.uploadImage(widget.flightId, bytes, image.name);
      } on ApiException {
        failures++;
      }
      if (mounted) setState(() => _bulkDone++);
    }
    if (!mounted) return;
    setState(() => _bulkUploading = false);
    ScaffoldMessenger.of(context).showSnackBar(SnackBar(
      content: Text(failures == 0
          ? 'Uploaded ${picked.length} photos'
          : 'Uploaded ${picked.length - failures} of ${picked.length} photos ($failures failed)'),
    ));
    Navigator.of(context).pop();
  }

  Future<void> _submit() async {
    final image = _image;
    if (image == null) return;

    setState(() => _submitting = true);
    try {
      final bytes = await image.readAsBytes();
      final result = await DroneRepository.instance.uploadImage(
        widget.flightId, bytes, image.name,
        treeId: _treeIdController.text.trim().isEmpty ? null : _treeIdController.text.trim(),
      );
      if (!mounted) return;
      setState(() => _result = result);
    } on ApiException catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(e.message)));
    } finally {
      if (mounted) setState(() => _submitting = false);
    }
  }

  Future<void> _analyzeWithAI() async {
    final result = _result;
    if (result == null) return;
    final analyzingImageId = result.id;
    setState(() => _analyzing = true);
    try {
      // Goes through the tracker rather than calling the repository
      // directly - the request keeps running even if this screen is left
      // (capture another photo, go back) before it finishes; whoever's
      // still around when it resolves picks up the result, and the flight's
      // photo list also shows it as "Analyzing..." in the meantime.
      final updated = await DroneAnalysisTracker.instance.start(result.flightId, result.id);
      // Guards against "capture another" having moved this same screen on
      // to a different photo while this one's analysis was still running -
      // without this, the old photo's result could overwrite the new one.
      if (!mounted || _result?.id != analyzingImageId) return;
      setState(() => _result = updated);
    } on ApiException catch (e) {
      if (mounted && _result?.id == analyzingImageId) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(e.message)));
      }
    } finally {
      if (mounted && _result?.id == analyzingImageId) setState(() => _analyzing = false);
    }
  }

  void _captureAnother() {
    // If the previous photo's AI analysis is still running, it keeps going
    // in the tracker regardless (see DroneAnalysisTracker) - just detach
    // this screen's spinner from it so the new photo doesn't inherit a
    // stale "analyzing" state it never actually started.
    setState(() { _image = null; _result = null; _analyzing = false; _treeIdController.clear(); });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Capture a photo')),
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(24),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              AspectRatio(
                aspectRatio: 1,
                child: Container(
                  decoration: BoxDecoration(
                    color: Theme.of(context).colorScheme.surfaceContainerHighest,
                    borderRadius: BorderRadius.circular(12),
                  ),
                  clipBehavior: Clip.antiAlias,
                  child: _result != null && _result!.analysis?.hasOverlay == true
                      ? InteractiveViewer(
                          minScale: 1,
                          maxScale: 5,
                          child: DroneImageView(flightId: _result!.flightId, imageId: _result!.id, overlay: true),
                        )
                      : _image == null
                          ? const Center(child: Icon(Icons.flight_takeoff, size: 64))
                          : InteractiveViewer(
                              minScale: 1,
                              maxScale: 5,
                              child: Image.file(File(_image!.path), fit: BoxFit.cover),
                            ),
                ),
              ),
              if ((_result != null && _result!.analysis?.hasOverlay == true) || _image != null)
                const Padding(
                  padding: EdgeInsets.only(top: 4),
                  child: Text('Pinch to zoom in on the photo', style: TextStyle(color: Colors.black45, fontSize: 11)),
                ),
              const SizedBox(height: 16),
              if (_result == null) ...[
                Row(
                  children: [
                    Expanded(
                      child: OutlinedButton.icon(
                        onPressed: _submitting ? null : () => _pickImage(ImageSource.camera),
                        icon: const Icon(Icons.camera_alt),
                        label: const Text('Camera'),
                      ),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: OutlinedButton.icon(
                        onPressed: _submitting ? null : () => _pickImage(ImageSource.gallery),
                        icon: const Icon(Icons.photo_library),
                        label: const Text('Gallery'),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 16),
                TextField(
                  controller: _treeIdController,
                  decoration: const InputDecoration(
                    labelText: 'Tree/plot ID (optional)',
                    hintText: 'e.g. Row 4, Tree 12',
                    border: OutlineInputBorder(),
                  ),
                ),
                const SizedBox(height: 16),
                FilledButton(
                  onPressed: (_image == null || _submitting) ? null : _submit,
                  child: _submitting
                      ? const SizedBox(height: 20, width: 20, child: CircularProgressIndicator(strokeWidth: 2))
                      : const Text('Upload and analyze'),
                ),
                const SizedBox(height: 16),
                const Row(children: [Expanded(child: Divider()), Padding(padding: EdgeInsets.symmetric(horizontal: 8), child: Text('or', style: TextStyle(color: Colors.black45))), Expanded(child: Divider())]),
                const SizedBox(height: 16),
                OutlinedButton.icon(
                  onPressed: _bulkUploading ? null : _pickMultipleFromGallery,
                  icon: _bulkUploading
                      ? const SizedBox(height: 16, width: 16, child: CircularProgressIndicator(strokeWidth: 2))
                      : const Icon(Icons.photo_library_outlined),
                  label: Text(_bulkUploading ? 'Uploading $_bulkDone of $_bulkTotal...' : 'Add multiple photos from gallery'),
                ),
                const Padding(
                  padding: EdgeInsets.only(top: 4),
                  child: Text(
                    'Already have several photos ready (e.g. offloaded from the drone)? Select them all at once - each becomes its own photo in this flight.',
                    style: TextStyle(color: Colors.black45, fontSize: 11),
                  ),
                ),
              ] else ...[
                _buildResultCard(_result!),
                const SizedBox(height: 16),
                OutlinedButton(onPressed: _captureAnother, child: const Text('Capture another')),
              ],
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildResultCard(DroneImage image) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            DroneNdviView(
              analysis: image.analysis,
              hasRealNir: image.hasRealNir,
              hasOverlay: image.analysis?.hasOverlay == true,
            ),
            const Divider(height: 32),
            DroneDiagnosisView(diagnosis: image.diagnosis, analyzing: _analyzing, onAnalyze: _analyzeWithAI),
          ],
        ),
      ),
    );
  }
}
