import 'package:flutter/material.dart';

import '../../core/api_exception.dart';
import 'farm_input_repository.dart';

const _categories = ['seed', 'fertilizer', 'pesticide', 'labor', 'other'];

class FarmInputCreateScreen extends StatefulWidget {
  final int farmId;

  const FarmInputCreateScreen({super.key, required this.farmId});

  @override
  State<FarmInputCreateScreen> createState() => _FarmInputCreateScreenState();
}

class _FarmInputCreateScreenState extends State<FarmInputCreateScreen> {
  final _formKey = GlobalKey<FormState>();
  final _itemNameController = TextEditingController();
  final _quantityController = TextEditingController();
  final _unitController = TextEditingController();
  final _costController = TextEditingController();
  final _notesController = TextEditingController();
  String _entryType = 'purchase';
  String _category = 'fertilizer';
  DateTime _entryDate = DateTime.now();
  bool _saving = false;

  @override
  void dispose() {
    _itemNameController.dispose();
    _quantityController.dispose();
    _unitController.dispose();
    _costController.dispose();
    _notesController.dispose();
    super.dispose();
  }

  Future<void> _pickDate() async {
    final picked = await showDatePicker(
      context: context,
      initialDate: _entryDate,
      firstDate: DateTime(2020),
      lastDate: DateTime.now().add(const Duration(days: 1)),
    );
    if (picked != null) setState(() => _entryDate = picked);
  }

  Future<void> _submit() async {
    if (!_formKey.currentState!.validate()) return;
    setState(() => _saving = true);
    try {
      final quantity = _quantityController.text.trim();
      final cost = _costController.text.trim();
      final record = await FarmInputRepository.instance.createInputRecord(
        widget.farmId,
        entryType: _entryType,
        category: _category,
        itemName: _itemNameController.text.trim(),
        quantity: quantity.isEmpty ? null : double.parse(quantity),
        unit: _unitController.text.trim().isEmpty ? null : _unitController.text.trim(),
        costKsh: (_entryType == 'purchase' && cost.isNotEmpty) ? double.parse(cost) : null,
        notes: _notesController.text.trim().isEmpty ? null : _notesController.text.trim(),
        entryDate: _entryDate,
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
      appBar: AppBar(title: const Text('Log an input')),
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(24),
          child: Form(
            key: _formKey,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                SegmentedButton<String>(
                  segments: const [
                    ButtonSegment(value: 'purchase', label: Text('Bought'), icon: Icon(Icons.shopping_cart)),
                    ButtonSegment(value: 'application', label: Text('Applied'), icon: Icon(Icons.grass)),
                  ],
                  selected: {_entryType},
                  onSelectionChanged: (s) => setState(() => _entryType = s.first),
                ),
                const SizedBox(height: 16),
                DropdownButtonFormField<String>(
                  initialValue: _category,
                  decoration: const InputDecoration(labelText: 'Category', border: OutlineInputBorder()),
                  items: _categories.map((c) => DropdownMenuItem(value: c, child: Text(c))).toList(),
                  onChanged: (v) => setState(() => _category = v ?? 'fertilizer'),
                ),
                const SizedBox(height: 16),
                TextFormField(
                  controller: _itemNameController,
                  decoration: const InputDecoration(labelText: 'Item', hintText: 'e.g. DAP fertilizer', border: OutlineInputBorder()),
                  validator: (v) => (v == null || v.trim().isEmpty) ? 'Required' : null,
                ),
                const SizedBox(height: 16),
                Row(
                  children: [
                    Expanded(
                      child: TextFormField(
                        controller: _quantityController,
                        keyboardType: const TextInputType.numberWithOptions(decimal: true),
                        decoration: const InputDecoration(labelText: 'Quantity (optional)', border: OutlineInputBorder()),
                        validator: (v) {
                          if (v == null || v.trim().isEmpty) return null;
                          return double.tryParse(v.trim()) == null ? 'Invalid' : null;
                        },
                      ),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: TextFormField(
                        controller: _unitController,
                        decoration: const InputDecoration(labelText: 'Unit', hintText: 'kg, bags...', border: OutlineInputBorder()),
                      ),
                    ),
                  ],
                ),
                if (_entryType == 'purchase') ...[
                  const SizedBox(height: 16),
                  TextFormField(
                    controller: _costController,
                    keyboardType: const TextInputType.numberWithOptions(decimal: true),
                    decoration: const InputDecoration(labelText: 'Cost, KSh (optional)', border: OutlineInputBorder()),
                    validator: (v) {
                      if (v == null || v.trim().isEmpty) return null;
                      final n = double.tryParse(v.trim());
                      if (n == null || n < 0) return 'Invalid';
                      return null;
                    },
                  ),
                ],
                const SizedBox(height: 16),
                ListTile(
                  contentPadding: EdgeInsets.zero,
                  title: const Text('Date'),
                  subtitle: Text('${_entryDate.year}-${_entryDate.month.toString().padLeft(2, '0')}-${_entryDate.day.toString().padLeft(2, '0')}'),
                  trailing: const Icon(Icons.calendar_today),
                  onTap: _pickDate,
                ),
                const SizedBox(height: 16),
                TextFormField(
                  controller: _notesController,
                  decoration: const InputDecoration(labelText: 'Notes (optional)', border: OutlineInputBorder()),
                  maxLines: 2,
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
