import 'package:flutter/material.dart';

import '../../core/api_exception.dart';
import 'farm_input_repository.dart';

class FarmYieldCreateScreen extends StatefulWidget {
  final int farmId;

  const FarmYieldCreateScreen({super.key, required this.farmId});

  @override
  State<FarmYieldCreateScreen> createState() => _FarmYieldCreateScreenState();
}

class _FarmYieldCreateScreenState extends State<FarmYieldCreateScreen> {
  final _formKey = GlobalKey<FormState>();
  final _cropController = TextEditingController();
  final _seasonController = TextEditingController();
  final _expectedYieldController = TextEditingController();
  DateTime? _plantedDate;
  bool _saving = false;

  @override
  void dispose() {
    _cropController.dispose();
    _seasonController.dispose();
    _expectedYieldController.dispose();
    super.dispose();
  }

  Future<void> _pickDate() async {
    final picked = await showDatePicker(
      context: context,
      initialDate: _plantedDate ?? DateTime.now(),
      firstDate: DateTime(2020),
      lastDate: DateTime.now().add(const Duration(days: 1)),
    );
    if (picked != null) setState(() => _plantedDate = picked);
  }

  Future<void> _submit() async {
    if (!_formKey.currentState!.validate()) return;
    setState(() => _saving = true);
    try {
      final expected = _expectedYieldController.text.trim();
      final record = await FarmInputRepository.instance.createYieldRecord(
        widget.farmId,
        crop: _cropController.text.trim(),
        seasonLabel: _seasonController.text.trim(),
        plantedDate: _plantedDate,
        expectedYieldKg: expected.isEmpty ? null : double.parse(expected),
      );
      if (!mounted) return;
      Navigator.of(context).pop(record);
    } on ApiException catch (e) {
      _showError(e.message);
    } finally {
      if (mounted) setState(() => _saving = false);
    }
  }

  void _showError(String message) {
    ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(message)));
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Start a yield record')),
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(24),
          child: Form(
            key: _formKey,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                TextFormField(
                  controller: _cropController,
                  decoration: const InputDecoration(labelText: 'Crop', hintText: 'e.g. Maize', border: OutlineInputBorder()),
                  validator: (v) => (v == null || v.trim().isEmpty) ? 'Required' : null,
                ),
                const SizedBox(height: 16),
                TextFormField(
                  controller: _seasonController,
                  decoration: const InputDecoration(
                    labelText: 'Season',
                    hintText: 'e.g. 2026 long rains',
                    border: OutlineInputBorder(),
                  ),
                  validator: (v) => (v == null || v.trim().isEmpty) ? 'Required' : null,
                ),
                const SizedBox(height: 16),
                ListTile(
                  contentPadding: EdgeInsets.zero,
                  title: const Text('Planted date (optional)'),
                  subtitle: Text(_plantedDate == null
                      ? 'Not set'
                      : '${_plantedDate!.year}-${_plantedDate!.month.toString().padLeft(2, '0')}-${_plantedDate!.day.toString().padLeft(2, '0')}'),
                  trailing: const Icon(Icons.calendar_today),
                  onTap: _pickDate,
                ),
                const SizedBox(height: 16),
                TextFormField(
                  controller: _expectedYieldController,
                  keyboardType: const TextInputType.numberWithOptions(decimal: true),
                  decoration: const InputDecoration(labelText: 'Expected yield, kg (optional)', border: OutlineInputBorder()),
                  validator: (v) {
                    if (v == null || v.trim().isEmpty) return null;
                    final n = double.tryParse(v.trim());
                    if (n == null || n <= 0) return 'Invalid';
                    return null;
                  },
                ),
                const SizedBox(height: 24),
                FilledButton(
                  onPressed: _saving ? null : _submit,
                  child: _saving
                      ? const SizedBox(height: 20, width: 20, child: CircularProgressIndicator(strokeWidth: 2))
                      : const Text('Save'),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
