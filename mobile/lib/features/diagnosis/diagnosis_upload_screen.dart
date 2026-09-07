import 'dart:io';

import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';

import '../../core/api_exception.dart';
import 'diagnosis_repository.dart';
import 'diagnosis_result_screen.dart';

class DiagnosisUploadScreen extends StatefulWidget {
  const DiagnosisUploadScreen({super.key});

  @override
  State<DiagnosisUploadScreen> createState() => _DiagnosisUploadScreenState();
}

class _DiagnosisUploadScreenState extends State<DiagnosisUploadScreen> {
  final _picker = ImagePicker();
  final _symptomsController = TextEditingController();
  final List<XFile> _images = [];
  bool _submitting = false;

  @override
  void dispose() {
    _symptomsController.dispose();
    super.dispose();
  }

  Future<void> _pickFromCamera() async {
    final picked = await _picker.pickImage(source: ImageSource.camera, maxWidth: 1600, imageQuality: 85);
    if (picked != null) setState(() => _images.add(picked));
  }

  Future<void> _pickFromGallery() async {
    // pickMultiImage lets the farmer select several photos of the same
    // plant (different angles/leaves) in one go - they all go into a
    // single diagnosis (backend already accepts image_urls: List[str]).
    final picked = await _picker.pickMultiImage(maxWidth: 1600, imageQuality: 85);
    if (picked.isNotEmpty) setState(() => _images.addAll(picked));
  }

  void _removeImage(int index) => setState(() => _images.removeAt(index));

  Future<void> _submit() async {
    if (_images.isEmpty) return;

    setState(() => _submitting = true);
    try {
      final imageUrls = <String>[];
      for (final image in _images) {
        final bytes = await image.readAsBytes();
        imageUrls.add(await DiagnosisRepository.instance.uploadImage(bytes, image.name));
      }
      final diagnosis = await DiagnosisRepository.instance.createDiagnosis(
        imageUrls: imageUrls,
        userSymptoms: _symptomsController.text.trim().isEmpty ? null : _symptomsController.text.trim(),
      );
      if (!mounted) return;
      Navigator.of(context).push(MaterialPageRoute(builder: (_) => DiagnosisResultScreen(diagnosis: diagnosis)));
    } on ApiException catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(e.message)));
    } finally {
      if (mounted) setState(() => _submitting = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Diagnose a plant')),
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(24),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              if (_images.isEmpty)
                AspectRatio(
                  aspectRatio: 1,
                  child: Container(
                    decoration: BoxDecoration(
                      color: Theme.of(context).colorScheme.surfaceContainerHighest,
                      borderRadius: BorderRadius.circular(12),
                    ),
                    child: const Center(child: Icon(Icons.eco_outlined, size: 64)),
                  ),
                )
              else
                SizedBox(
                  height: 120,
                  child: ListView.separated(
                    scrollDirection: Axis.horizontal,
                    itemCount: _images.length,
                    separatorBuilder: (_, _) => const SizedBox(width: 8),
                    itemBuilder: (context, index) => Stack(
                      children: [
                        ClipRRect(
                          borderRadius: BorderRadius.circular(12),
                          child: Image.file(File(_images[index].path), width: 120, height: 120, fit: BoxFit.cover),
                        ),
                        Positioned(
                          top: 4,
                          right: 4,
                          child: GestureDetector(
                            onTap: _submitting ? null : () => _removeImage(index),
                            child: const CircleAvatar(
                              radius: 12,
                              backgroundColor: Colors.black54,
                              child: Icon(Icons.close, size: 16, color: Colors.white),
                            ),
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
              if (_images.isNotEmpty)
                Padding(
                  padding: const EdgeInsets.only(top: 8),
                  child: Text('${_images.length} photo${_images.length == 1 ? '' : 's'} selected', style: const TextStyle(color: Colors.black54)),
                ),
              const SizedBox(height: 16),
              Row(
                children: [
                  Expanded(
                    child: OutlinedButton.icon(
                      onPressed: _submitting ? null : _pickFromCamera,
                      icon: const Icon(Icons.camera_alt),
                      label: const Text('Camera'),
                    ),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: OutlinedButton.icon(
                      onPressed: _submitting ? null : _pickFromGallery,
                      icon: const Icon(Icons.photo_library),
                      label: const Text('Gallery'),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 16),
              TextField(
                controller: _symptomsController,
                maxLines: 3,
                decoration: const InputDecoration(
                  labelText: 'Symptoms (optional)',
                  hintText: 'e.g. yellow spots on the leaves',
                  border: OutlineInputBorder(),
                ),
              ),
              const SizedBox(height: 16),
              FilledButton(
                onPressed: (_images.isEmpty || _submitting) ? null : _submit,
                child: _submitting
                    ? const SizedBox(height: 20, width: 20, child: CircularProgressIndicator(strokeWidth: 2))
                    : Text(_images.length > 1 ? 'Diagnose ${_images.length} photos' : 'Diagnose'),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
