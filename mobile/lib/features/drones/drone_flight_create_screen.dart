import 'dart:async';

import 'package:flutter/material.dart';
import 'package:geolocator/geolocator.dart';
import 'package:latlong2/latlong.dart';

import '../../core/api_exception.dart';
import 'drone_boundary_map_screen.dart';
import 'drone_repository.dart';

class DroneFlightCreateScreen extends StatefulWidget {
  final int farmId;
  final double farmLatitude;
  final double farmLongitude;

  const DroneFlightCreateScreen({
    super.key,
    required this.farmId,
    required this.farmLatitude,
    required this.farmLongitude,
  });

  @override
  State<DroneFlightCreateScreen> createState() => _DroneFlightCreateScreenState();
}

class _DroneFlightCreateScreenState extends State<DroneFlightCreateScreen> {
  final _formKey = GlobalKey<FormState>();
  final _droneIdController = TextEditingController();
  final _notesController = TextEditingController();
  late final TextEditingController _latController;
  late final TextEditingController _lngController;
  bool _locating = false;
  bool _saving = false;
  List<LatLng>? _boundary;
  bool _goalHealth = true;
  bool _goalCount = false;

  @override
  void initState() {
    super.initState();
    // Defaults to the farm's own coordinates - the drone launches from the
    // field it's surveying, so this is almost always right without the
    // farmer needing to fetch a fresh GPS fix at all.
    _latController = TextEditingController(text: widget.farmLatitude.toStringAsFixed(6));
    _lngController = TextEditingController(text: widget.farmLongitude.toStringAsFixed(6));
  }

  @override
  void dispose() {
    _droneIdController.dispose();
    _notesController.dispose();
    _latController.dispose();
    _lngController.dispose();
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
      // geolocator's own timeLimit isn't reliably honored on Android (see
      // mobile/CHANGELOG.md) - .timeout() is the guaranteed backstop.
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

  Future<void> _traceBoundary() async {
    final center = LatLng(
      double.tryParse(_latController.text) ?? widget.farmLatitude,
      double.tryParse(_lngController.text) ?? widget.farmLongitude,
    );
    final result = await Navigator.of(context).push<List<LatLng>>(
      MaterialPageRoute(
        builder: (_) => DroneBoundaryMapScreen(initialCenter: center, initialPoints: _boundary),
      ),
    );
    if (result != null) setState(() => _boundary = result);
  }

  Future<void> _submit() async {
    if (!_formKey.currentState!.validate()) return;
    setState(() => _saving = true);
    try {
      final flight = await DroneRepository.instance.createFlight(
        farmId: widget.farmId,
        droneId: _droneIdController.text.trim(),
        homeLatitude: double.parse(_latController.text),
        homeLongitude: double.parse(_lngController.text),
        boundaryPolygon: _boundary,
        surveyGoals: [
          if (_goalHealth) 'health',
          if (_goalCount) 'count',
        ],
        surveyNotes: _notesController.text.trim(),
      );
      if (!mounted) return;
      Navigator.of(context).pop(flight);
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
      appBar: AppBar(title: const Text('Start a drone flight')),
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(24),
          child: Form(
            key: _formKey,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                const Text(
                  "This app doesn't fly the drone - it's flown manually (e.g. the DJI app on the "
                  'remote), and photos are uploaded here as they\'re captured.',
                  style: TextStyle(color: Colors.black54),
                ),
                const SizedBox(height: 16),
                TextFormField(
                  controller: _droneIdController,
                  decoration: const InputDecoration(labelText: 'Drone ID / name', border: OutlineInputBorder()),
                  validator: (v) => (v == null || v.trim().isEmpty) ? 'Required' : null,
                ),
                const SizedBox(height: 16),
                Row(
                  children: [
                    Expanded(
                      child: TextFormField(
                        controller: _latController,
                        keyboardType: const TextInputType.numberWithOptions(decimal: true, signed: true),
                        decoration: const InputDecoration(labelText: 'Home latitude', border: OutlineInputBorder()),
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
                        decoration: const InputDecoration(labelText: 'Home longitude', border: OutlineInputBorder()),
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
                  label: const Text('Use my location instead'),
                ),
                const SizedBox(height: 24),
                Text('What do you want from this survey?', style: Theme.of(context).textTheme.titleSmall),
                const SizedBox(height: 4),
                CheckboxListTile(
                  value: _goalHealth,
                  onChanged: (v) => setState(() => _goalHealth = v ?? false),
                  title: const Text('Health analysis'),
                  subtitle: const Text('Disease, pest, or stress read on each photo'),
                  controlAffinity: ListTileControlAffinity.leading,
                  contentPadding: EdgeInsets.zero,
                ),
                CheckboxListTile(
                  value: _goalCount,
                  onChanged: (v) => setState(() => _goalCount = v ?? false),
                  title: const Text('Count plants/trees'),
                  subtitle: const Text('Rough visible count per photo'),
                  controlAffinity: ListTileControlAffinity.leading,
                  contentPadding: EdgeInsets.zero,
                ),
                const SizedBox(height: 8),
                TextFormField(
                  controller: _notesController,
                  maxLines: 2,
                  decoration: const InputDecoration(
                    labelText: 'Anything else? (optional)',
                    hintText: 'e.g. sprayed fungicide 5 days ago, focus on the north corner',
                    border: OutlineInputBorder(),
                  ),
                ),
                const SizedBox(height: 24),
                OutlinedButton.icon(
                  onPressed: _traceBoundary,
                  icon: const Icon(Icons.crop_free),
                  label: Text(_boundary == null ? 'Trace flight boundary (optional)' : 'Edit flight boundary'),
                ),
                if (_boundary != null)
                  Padding(
                    padding: const EdgeInsets.only(top: 8),
                    child: Row(
                      children: [
                        Expanded(child: Text('Boundary set · ${_boundary!.length} points', style: const TextStyle(color: Colors.black54))),
                        TextButton(onPressed: () => setState(() => _boundary = null), child: const Text('Clear')),
                      ],
                    ),
                  ),
                const SizedBox(height: 24),
                FilledButton(
                  onPressed: _saving ? null : _submit,
                  child: _saving
                      ? const SizedBox(height: 20, width: 20, child: CircularProgressIndicator(strokeWidth: 2))
                      : const Text('Start flight'),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
