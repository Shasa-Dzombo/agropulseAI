import 'package:flutter/material.dart';

import '../../core/api_exception.dart';
import 'chama_repository.dart';

const _chamaTypes = ['savings', 'investment', 'welfare', 'multipurpose'];

class ChamaCreateScreen extends StatefulWidget {
  const ChamaCreateScreen({super.key});

  @override
  State<ChamaCreateScreen> createState() => _ChamaCreateScreenState();
}

class _ChamaCreateScreenState extends State<ChamaCreateScreen> {
  final _formKey = GlobalKey<FormState>();
  final _nameController = TextEditingController();
  final _descriptionController = TextEditingController();
  final _monthlyContributionController = TextEditingController();
  final _paybillController = TextEditingController();
  String _chamaType = 'savings';
  bool _isPublic = true;
  bool _saving = false;

  @override
  void dispose() {
    _nameController.dispose();
    _descriptionController.dispose();
    _monthlyContributionController.dispose();
    _paybillController.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    if (!_formKey.currentState!.validate()) return;
    setState(() => _saving = true);
    try {
      final monthly = _monthlyContributionController.text.trim();
      final chama = await ChamaRepository.instance.createChama(
        name: _nameController.text.trim(),
        description: _descriptionController.text.trim().isEmpty ? null : _descriptionController.text.trim(),
        chamaType: _chamaType,
        monthlyContributionKsh: monthly.isEmpty ? null : double.parse(monthly),
        isPublic: _isPublic,
        mpesaPaybillNumber: _paybillController.text.trim().isEmpty ? null : _paybillController.text.trim(),
      );
      if (!mounted) return;
      Navigator.of(context).pop(chama);
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
      appBar: AppBar(title: const Text('Start a chama')),
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(24),
          child: Form(
            key: _formKey,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                TextFormField(
                  controller: _nameController,
                  decoration: const InputDecoration(labelText: 'Chama name', border: OutlineInputBorder()),
                  validator: (v) => (v == null || v.trim().length < 2) ? 'Enter a name' : null,
                ),
                const SizedBox(height: 16),
                TextFormField(
                  controller: _descriptionController,
                  decoration: const InputDecoration(labelText: 'Description (optional)', border: OutlineInputBorder()),
                  maxLines: 2,
                ),
                const SizedBox(height: 16),
                DropdownButtonFormField<String>(
                  initialValue: _chamaType,
                  decoration: const InputDecoration(labelText: 'Type', border: OutlineInputBorder()),
                  items: _chamaTypes.map((t) => DropdownMenuItem(value: t, child: Text(t))).toList(),
                  onChanged: (v) => setState(() => _chamaType = v ?? 'savings'),
                ),
                const SizedBox(height: 16),
                TextFormField(
                  controller: _monthlyContributionController,
                  keyboardType: const TextInputType.numberWithOptions(decimal: true),
                  decoration: const InputDecoration(
                    labelText: 'Monthly contribution, KSh (optional)',
                    border: OutlineInputBorder(),
                  ),
                  validator: (v) {
                    if (v == null || v.trim().isEmpty) return null;
                    final n = double.tryParse(v.trim());
                    if (n == null || n <= 0) return 'Enter a valid amount';
                    return null;
                  },
                ),
                const SizedBox(height: 16),
                TextFormField(
                  controller: _paybillController,
                  keyboardType: TextInputType.number,
                  decoration: const InputDecoration(
                    labelText: 'M-Pesa paybill (optional)',
                    helperText: 'Where members send contributions - only shown to members, not verified automatically',
                    border: OutlineInputBorder(),
                  ),
                ),
                const SizedBox(height: 16),
                SwitchListTile(
                  contentPadding: EdgeInsets.zero,
                  title: const Text('Open to new members'),
                  subtitle: const Text('Others can find and join this chama'),
                  value: _isPublic,
                  onChanged: (v) => setState(() => _isPublic = v),
                ),
                const SizedBox(height: 24),
                FilledButton(
                  onPressed: _saving ? null : _submit,
                  child: _saving
                      ? const SizedBox(height: 20, width: 20, child: CircularProgressIndicator(strokeWidth: 2))
                      : const Text('Create chama'),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
