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
  XFile? _image;
  bool _submitting = false;

  @override
  void dispose() {
    _symptomsController.dispose();
    super.dispose();
  }

  Future<void> _pickImage(ImageSource source) async {
    final picked = await _picker.pickImage(source: source, maxWidth: 1600, imageQuality: 85);
    if (picked != null) setState(() => _image = picked);
  }

  Future<void> _submit() async {
    final image = _image;
    if (image == null) return;

    setState(() => _submitting = true);
    try {
      final bytes = await image.readAsBytes();
      final imageUrl = await DiagnosisRepository.instance.uploadImage(bytes, image.name);
      final diagnosis = await DiagnosisRepository.instance.createDiagnosis(
        imageUrls: [imageUrl],
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
              AspectRatio(
                aspectRatio: 1,
                child: Container(
                  decoration: BoxDecoration(
                    color: Theme.of(context).colorScheme.surfaceContainerHighest,
                    borderRadius: BorderRadius.circular(12),
                  ),
                  clipBehavior: Clip.antiAlias,
                  child: _image == null
                      ? const Center(child: Icon(Icons.eco_outlined, size: 64))
                      : Image.file(File(_image!.path), fit: BoxFit.cover),
                ),
              ),
              const SizedBox(height: 16),
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
                onPressed: (_image == null || _submitting) ? null : _submit,
                child: _submitting
                    ? const SizedBox(height: 20, width: 20, child: CircularProgressIndicator(strokeWidth: 2))
                    : const Text('Diagnose'),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
