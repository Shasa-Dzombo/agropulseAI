import 'dart:async';

import 'package:flutter/material.dart';
import 'package:geolocator/geolocator.dart';

import '../../core/api_exception.dart';
import '../../core/kenya_counties.dart';
import 'farm_repository.dart';

const _farmTypes = ['Smallholder', 'Commercial', 'Mixed', 'Organic', 'Cooperative'];

class FarmCreateScreen extends StatefulWidget {
  const FarmCreateScreen({super.key});

  @override
  State<FarmCreateScreen> createState() => _FarmCreateScreenState();
}

class _FarmCreateScreenState extends State<FarmCreateScreen> {
  final _formKey = GlobalKey<FormState>();
  final _nameController = TextEditingController();
  final _sizeController = TextEditingController();
  final _latController = TextEditingController();
  final _lngController = TextEditingController();
  final _cropController = TextEditingController();
  String? _selectedCounty;
  String? _selectedFarmType;
  bool _hasIrrigation = false;
  bool _locating = false;
  bool _saving = false;

  @override
  void dispose() {
    _nameController.dispose();
    _sizeController.dispose();
    _latController.dispose();
    _lngController.dispose();
    _cropController.dispose();
    super.dispose();
  }

  Future<void> _useMyLocation() async {
    setState(() => _locating = true);
    try {
      var permission = await Geolocator.checkPermission();
      if (permission == LocationPermission.denied) {
        permission = await Geolocator.requestPermission();
      }
      if (permission == LocationPermission.denied || permission == LocationPermission.deniedForever) {
        _showError('Location permission denied. Enter coordinates manually.');
        return;
      }
      if (!await Geolocator.isLocationServiceEnabled()) {
        _showError('Location services are off. Enter coordinates manually.');
        return;
      }
      // geolocator's own `timeLimit` isn't reliably honored on Android (seen
      // hanging well past it on-device) - wrap in our own timeout as a
      // guaranteed backstop so this button can never spin forever.
      final position = await Geolocator.getCurrentPosition(
        locationSettings: const LocationSettings(accuracy: LocationAccuracy.high, timeLimit: Duration(seconds: 15)),
      ).timeout(const Duration(seconds: 15));
      _latController.text = position.latitude.toStringAsFixed(6);
      _lngController.text = position.longitude.toStringAsFixed(6);
    } on TimeoutException {
      _showError('Timed out getting location. Enter coordinates manually.');
    } catch (e) {
      _showError('Could not get location. Enter coordinates manually.');
    } finally {
      if (mounted) setState(() => _locating = false);
    }
  }

  Future<void> _submit() async {
    if (!_formKey.currentState!.validate()) return;
    setState(() => _saving = true);
    try {
      final farm = await FarmRepository.instance.createFarm(
        name: _nameController.text.trim(),
        latitude: double.parse(_latController.text),
        longitude: double.parse(_lngController.text),
        sizeAcres: double.parse(_sizeController.text),
        county: _selectedCounty!,
        farmType: _selectedFarmType,
        primaryCrop: _cropController.text.trim().isEmpty ? null : _cropController.text.trim(),
        hasIrrigation: _hasIrrigation,
      );
      if (!mounted) return;
      Navigator.of(context).pop(farm);
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
      appBar: AppBar(title: const Text('Add farm')),
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
                  decoration: const InputDecoration(labelText: 'Farm name', border: OutlineInputBorder()),
                  validator: (v) => (v == null || v.trim().isEmpty) ? 'Required' : null,
                ),
                const SizedBox(height: 16),
                TextFormField(
                  controller: _sizeController,
                  keyboardType: const TextInputType.numberWithOptions(decimal: true),
                  decoration: const InputDecoration(labelText: 'Size (acres)', border: OutlineInputBorder()),
                  validator: (v) {
                    final n = double.tryParse(v ?? '');
                    if (n == null || n <= 0) return 'Enter a valid size';
                    return null;
                  },
                ),
                const SizedBox(height: 16),
                DropdownButtonFormField<String>(
                  initialValue: _selectedCounty,
                  decoration: const InputDecoration(labelText: 'County', border: OutlineInputBorder()),
                  isExpanded: true,
                  items: kenyaCounties.map((c) => DropdownMenuItem(value: c, child: Text(c))).toList(),
                  onChanged: (v) => setState(() => _selectedCounty = v),
                  validator: (v) => v == null ? 'Required' : null,
                ),
                const SizedBox(height: 16),
                DropdownButtonFormField<String>(
                  initialValue: _selectedFarmType,
                  decoration: const InputDecoration(labelText: 'Farm type (optional)', border: OutlineInputBorder()),
                  isExpanded: true,
                  items: _farmTypes.map((t) => DropdownMenuItem(value: t, child: Text(t))).toList(),
                  onChanged: (v) => setState(() => _selectedFarmType = v),
                ),
                const SizedBox(height: 16),
                TextFormField(
                  controller: _cropController,
                  decoration: const InputDecoration(labelText: 'Primary crop (optional)', border: OutlineInputBorder()),
                ),
                const SizedBox(height: 16),
                SwitchListTile(
                  contentPadding: EdgeInsets.zero,
                  title: const Text('Has irrigation'),
                  value: _hasIrrigation,
                  onChanged: (v) => setState(() => _hasIrrigation = v),
                ),
                const SizedBox(height: 16),
                Row(
                  children: [
                    Expanded(
                      child: TextFormField(
                        controller: _latController,
                        keyboardType: const TextInputType.numberWithOptions(decimal: true, signed: true),
                        decoration: const InputDecoration(labelText: 'Latitude', border: OutlineInputBorder()),
                        validator: (v) {
                          final n = double.tryParse(v ?? '');
                          if (n == null || n < -90 || n > 90) return 'Invalid';
                          return null;
                        },
                      ),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: TextFormField(
                        controller: _lngController,
                        keyboardType: const TextInputType.numberWithOptions(decimal: true, signed: true),
                        decoration: const InputDecoration(labelText: 'Longitude', border: OutlineInputBorder()),
                        validator: (v) {
                          final n = double.tryParse(v ?? '');
                          if (n == null || n < -180 || n > 180) return 'Invalid';
                          return null;
                        },
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 8),
                OutlinedButton.icon(
                  onPressed: _locating ? null : _useMyLocation,
                  icon: _locating
                      ? const SizedBox(height: 16, width: 16, child: CircularProgressIndicator(strokeWidth: 2))
                      : const Icon(Icons.my_location),
                  label: const Text('Use my location'),
                ),
                const SizedBox(height: 24),
                FilledButton(
                  onPressed: _saving ? null : _submit,
                  child: _saving
                      ? const SizedBox(height: 20, width: 20, child: CircularProgressIndicator(strokeWidth: 2))
                      : const Text('Save farm'),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
