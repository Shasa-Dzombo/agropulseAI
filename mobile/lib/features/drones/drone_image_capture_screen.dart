import 'dart:io';

import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';

import '../../core/api_exception.dart';
import 'drone_models.dart';
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
  DroneImage? _result;

  @override
  void dispose() {
    _treeIdController.dispose();
    super.dispose();
  }

  Future<void> _pickImage(ImageSource source) async {
    final picked = await _picker.pickImage(source: source, maxWidth: 1600, imageQuality: 85);
    if (picked != null) setState(() { _image = picked; _result = null; });
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

  void _captureAnother() {
    setState(() { _image = null; _result = null; _treeIdController.clear(); });
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
                  child: _image == null
                      ? const Center(child: Icon(Icons.flight_takeoff, size: 64))
                      : Image.file(File(_image!.path), fit: BoxFit.cover),
                ),
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
    final analysis = image.analysis;
    final indicators = analysis == null
        ? const <String>[]
        : [...analysis.stressIndicators, ...analysis.vigorIndicators];

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                const Icon(Icons.check_circle, color: Colors.green),
                const SizedBox(width: 8),
                Text('Analyzed', style: Theme.of(context).textTheme.titleMedium),
              ],
            ),
            if (!image.hasRealNir) ...[
              const SizedBox(height: 12),
              Container(
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: Colors.orange.withValues(alpha: 0.12),
                  borderRadius: BorderRadius.circular(8),
                  border: Border.all(color: Colors.orange.shade300),
                ),
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Icon(Icons.info_outline, size: 18, color: Colors.orange.shade800),
                    const SizedBox(width: 8),
                    Expanded(
                      child: Text(
                        'Estimated from an ordinary photo, not a real infrared sensor. '
                        'Treat this as a rough scouting cue, not a precise reading.',
                        style: TextStyle(color: Colors.orange.shade900, fontSize: 13),
                      ),
                    ),
                  ],
                ),
              ),
            ],
            if (analysis != null) ...[
              const SizedBox(height: 12),
              Text(_plainSummary(analysis), style: Theme.of(context).textTheme.bodyLarge),
              if (analysis.canopyCoveragePct != null) ...[
                const SizedBox(height: 4),
                Text('Canopy coverage: ${analysis.canopyCoveragePct!.toStringAsFixed(0)}%'),
              ],
              if (analysis.ndvi != null) ...[
                const SizedBox(height: 4),
                Text(
                  'Vegetation index (NDVI): ${analysis.ndvi!.toStringAsFixed(2)}',
                  style: const TextStyle(color: Colors.black54, fontSize: 12),
                ),
              ],
              if (indicators.isNotEmpty) ...[
                const SizedBox(height: 12),
                Text('What this suggests', style: Theme.of(context).textTheme.titleSmall),
                const SizedBox(height: 4),
                for (final indicator in indicators)
                  Padding(
                    padding: const EdgeInsets.only(top: 4),
                    child: Text('• $indicator'),
                  ),
              ],
            ],
          ],
        ),
      ),
    );
  }

  String _plainSummary(DroneImageAnalysis analysis) {
    final health = plainHealthLabel(analysis.healthStatus);
    final vigor = plainVigorLabel(analysis.vigorLevel);
    return vigor == null ? health : '$health, $vigor';
  }
}
