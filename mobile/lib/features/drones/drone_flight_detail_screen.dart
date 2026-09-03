import 'package:flutter/material.dart';

import '../../core/api_exception.dart';
import 'drone_image_capture_screen.dart';
import 'drone_models.dart';
import 'drone_repository.dart';

class DroneFlightDetailScreen extends StatefulWidget {
  final DroneFlight flight;

  const DroneFlightDetailScreen({super.key, required this.flight});

  @override
  State<DroneFlightDetailScreen> createState() => _DroneFlightDetailScreenState();
}

class _DroneFlightDetailScreenState extends State<DroneFlightDetailScreen> {
  late DroneFlight _flight;
  late Future<List<DroneImage>> _imagesFuture;
  late Future<FlightAnalysisSummary> _summaryFuture;
  bool _completing = false;

  @override
  void initState() {
    super.initState();
    _flight = widget.flight;
    _loadLists();
  }

  void _loadLists() {
    _imagesFuture = DroneRepository.instance.listImages(_flight.id);
    _summaryFuture = DroneRepository.instance.getAnalysisSummary(_flight.id);
  }

  Future<void> _refresh() async {
    final updated = await DroneRepository.instance.getFlight(_flight.id);
    if (!mounted) return;
    setState(() {
      _flight = updated;
      _loadLists();
    });
    await Future.wait([_imagesFuture, _summaryFuture]);
  }

  Future<void> _capturePhoto() async {
    await Navigator.of(context).push(
      MaterialPageRoute(builder: (_) => DroneImageCaptureScreen(flightId: _flight.id)),
    );
    _refresh();
  }

  Future<void> _completeFlight() async {
    setState(() => _completing = true);
    try {
      final updated = await DroneRepository.instance.completeFlight(_flight.id, completed: true);
      if (!mounted) return;
      setState(() => _flight = updated);
    } on ApiException catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(e.message)));
    } finally {
      if (mounted) setState(() => _completing = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final inProgress = _flight.status == 'in_progress';
    return Scaffold(
      appBar: AppBar(title: Text('Flight · ${_flight.droneId}')),
      floatingActionButton: inProgress
          ? FloatingActionButton.extended(
              onPressed: _capturePhoto,
              icon: const Icon(Icons.add_a_photo),
              label: const Text('Add photo'),
            )
          : null,
      body: SafeArea(
        child: RefreshIndicator(
          onRefresh: _refresh,
          child: ListView(
            padding: const EdgeInsets.all(16),
            children: [
              _buildInfoCard(),
              const SizedBox(height: 16),
              if (inProgress) ...[
                FilledButton(
                  onPressed: _completing ? null : _completeFlight,
                  child: _completing
                      ? const SizedBox(height: 20, width: 20, child: CircularProgressIndicator(strokeWidth: 2))
                      : const Text('Complete flight'),
                ),
                const SizedBox(height: 16),
              ],
              Text('Analysis summary', style: Theme.of(context).textTheme.titleMedium),
              const SizedBox(height: 8),
              _buildSummary(),
              const SizedBox(height: 24),
              Text('Captured images', style: Theme.of(context).textTheme.titleMedium),
              const SizedBox(height: 8),
              _buildImagesList(),
              const SizedBox(height: 80),
            ],
          ),
        ),
      ),
    );
  }

  Color _statusColor(String status) {
    switch (status) {
      case 'in_progress':
        return Colors.blue;
      case 'completed':
        return Colors.green;
      case 'aborted':
      case 'failed':
        return Colors.red;
      default:
        return Colors.grey;
    }
  }

  Widget _buildInfoCard() {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Expanded(child: Text(_flight.droneId, style: Theme.of(context).textTheme.titleLarge)),
                Chip(
                  label: Text(_flight.status.replaceAll('_', ' ')),
                  backgroundColor: _statusColor(_flight.status).withValues(alpha: 0.15),
                  labelStyle: TextStyle(color: _statusColor(_flight.status)),
                ),
              ],
            ),
            const SizedBox(height: 4),
            Text('Home: ${_flight.homeLatitude.toStringAsFixed(5)}, ${_flight.homeLongitude.toStringAsFixed(5)}'),
            if (_flight.weatherTemperatureC != null) ...[
              const SizedBox(height: 12),
              Wrap(
                spacing: 16,
                runSpacing: 8,
                children: [
                  _stat(Icons.thermostat, '${_flight.weatherTemperatureC!.round()}°C'),
                  if (_flight.weatherConditions != null) _stat(Icons.cloud, _flight.weatherConditions!),
                  if (_flight.weatherFlightSuitable != null)
                    _stat(
                      _flight.weatherFlightSuitable! ? Icons.check_circle : Icons.warning,
                      _flight.weatherFlightSuitable! ? 'Suitable for flight' : 'Not ideal for flight',
                    ),
                ],
              ),
              if (_flight.weatherWarnings != null && _flight.weatherWarnings!.isNotEmpty)
                Padding(
                  padding: const EdgeInsets.only(top: 8),
                  child: Text(
                    _flight.weatherWarnings!.join(' · '),
                    style: const TextStyle(color: Colors.orange),
                  ),
                ),
            ],
          ],
        ),
      ),
    );
  }

  Widget _stat(IconData icon, String label) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Icon(icon, size: 18),
        const SizedBox(width: 4),
        Text(label),
      ],
    );
  }

  Widget _buildSummary() {
    return FutureBuilder<FlightAnalysisSummary>(
      future: _summaryFuture,
      builder: (context, snapshot) {
        if (snapshot.connectionState == ConnectionState.waiting) {
          return const Padding(padding: EdgeInsets.all(16), child: Center(child: CircularProgressIndicator()));
        }
        if (snapshot.hasError) {
          return Text(snapshot.error is ApiException ? (snapshot.error as ApiException).message : 'Could not load summary');
        }
        final summary = snapshot.data!;
        if (summary.imageCount == 0) return const Text('No photos analyzed yet');
        return Card(
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text('${summary.imageCount} photo${summary.imageCount == 1 ? '' : 's'} analyzed'),
                if (summary.meanNdvi != null) Text('Mean NDVI: ${summary.meanNdvi!.toStringAsFixed(2)}'),
                if (summary.meanCanopyCoveragePct != null)
                  Text('Mean canopy coverage: ${summary.meanCanopyCoveragePct!.toStringAsFixed(0)}%'),
                if (summary.healthStatusHistogram.isNotEmpty)
                  Text('Health: ${summary.healthStatusHistogram.entries.map((e) => '${e.key} (${e.value})').join(', ')}'),
                if (summary.vigorLevelHistogram.isNotEmpty)
                  Text('Vigor: ${summary.vigorLevelHistogram.entries.map((e) => '${e.key} (${e.value})').join(', ')}'),
              ],
            ),
          ),
        );
      },
    );
  }

  Widget _buildImagesList() {
    return FutureBuilder<List<DroneImage>>(
      future: _imagesFuture,
      builder: (context, snapshot) {
        if (snapshot.connectionState == ConnectionState.waiting) {
          return const Padding(padding: EdgeInsets.all(16), child: Center(child: CircularProgressIndicator()));
        }
        if (snapshot.hasError) {
          return Text(snapshot.error is ApiException ? (snapshot.error as ApiException).message : 'Could not load images');
        }
        final images = snapshot.data!;
        if (images.isEmpty) return const Text('No photos captured yet');
        return Card(
          child: Column(
            children: images
                .map((img) => ListTile(
                      leading: const Icon(Icons.image),
                      title: Text(img.treeId ?? 'Waypoint ${img.waypointIndex}'),
                      subtitle: img.analysis == null
                          ? null
                          : Text([
                              if (img.analysis!.ndvi != null) 'NDVI ${img.analysis!.ndvi!.toStringAsFixed(2)}',
                              if (img.analysis!.healthStatus != null) img.analysis!.healthStatus!,
                            ].join(' · ')),
                    ))
                .toList(),
          ),
        );
      },
    );
  }
}
