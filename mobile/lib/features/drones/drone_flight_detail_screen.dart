import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';
import 'package:latlong2/latlong.dart';

import '../../core/api_exception.dart';
import 'drone_analysis_tracker.dart';
import 'drone_boundary_map_screen.dart';
import 'drone_image_capture_screen.dart';
import 'drone_image_detail_screen.dart';
import 'drone_saved_boundary_picker.dart';
import 'drone_scan_screen.dart';
import 'drone_image_view.dart';
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

  Future<void> _editDroneId() async {
    final controller = TextEditingController(text: _flight.droneId);
    final newName = await showDialog<String>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Edit drone name'),
        content: TextField(controller: controller, decoration: const InputDecoration(labelText: 'Drone ID / name')),
        actions: [
          TextButton(onPressed: () => Navigator.of(context).pop(), child: const Text('Cancel')),
          FilledButton(onPressed: () => Navigator.of(context).pop(controller.text.trim()), child: const Text('Save')),
        ],
      ),
    );
    if (newName == null || newName.isEmpty || newName == _flight.droneId) return;
    try {
      final updated = await DroneRepository.instance.updateFlight(_flight.id, droneId: newName);
      if (mounted) setState(() => _flight = updated);
    } on ApiException catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(e.message)));
    }
  }

  Future<void> _editBoundary() async {
    final result = await Navigator.of(context).push<List<LatLng>>(
      MaterialPageRoute(
        builder: (_) => DroneBoundaryMapScreen(
          farmId: _flight.farmId,
          initialCenter: LatLng(_flight.homeLatitude, _flight.homeLongitude),
          initialPoints: _flight.boundaryPolygon,
        ),
      ),
    );
    if (result == null) return;
    await _saveBoundary(result);
  }

  Future<void> _importKmlBoundary() async {
    final picked = await FilePicker.platform.pickFiles(type: FileType.custom, allowedExtensions: ['kml'], withData: true);
    final file = picked?.files.single;
    if (file?.bytes == null) return;
    try {
      final parsed = await DroneRepository.instance.parseKmlBoundary(file!.bytes!, file.name);
      if (!mounted) return;
      for (final warning in parsed.warnings) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(warning)));
      }
      final result = await Navigator.of(context).push<List<LatLng>>(
        MaterialPageRoute(
          builder: (_) => DroneBoundaryMapScreen(
            farmId: _flight.farmId,
            initialCenter: LatLng(_flight.homeLatitude, _flight.homeLongitude),
            initialPoints: parsed.points,
          ),
        ),
      );
      if (result == null) return;
      await _saveBoundary(result);
    } on ApiException catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(e.message)));
    }
  }

  Future<void> _loadSavedBoundary() async {
    final points = await pickSavedBoundary(context, _flight.farmId);
    if (points == null || !mounted) return;
    final result = await Navigator.of(context).push<List<LatLng>>(
      MaterialPageRoute(
        builder: (_) => DroneBoundaryMapScreen(
          farmId: _flight.farmId,
          initialCenter: LatLng(_flight.homeLatitude, _flight.homeLongitude),
          initialPoints: points,
        ),
      ),
    );
    if (result == null) return;
    await _saveBoundary(result);
  }

  Future<void> _saveBoundary(List<LatLng> result) async {
    try {
      final updated = await DroneRepository.instance.updateFlight(_flight.id, boundaryPolygon: result);
      if (mounted) setState(() => _flight = updated);
    } on ApiException catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(e.message)));
    }
  }

  Future<void> _deleteImage(DroneImage image) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Delete photo?'),
        content: const Text('This removes the photo and its analysis. This can\'t be undone.'),
        actions: [
          TextButton(onPressed: () => Navigator.of(context).pop(false), child: const Text('Cancel')),
          TextButton(
            onPressed: () => Navigator.of(context).pop(true),
            child: const Text('Delete', style: TextStyle(color: Colors.red)),
          ),
        ],
      ),
    );
    if (confirmed != true) return;
    try {
      await DroneRepository.instance.deleteImage(_flight.id, image.id);
      _refresh();
    } on ApiException catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(e.message)));
    }
  }

  /// Fire-and-forget through the tracker (see DroneAnalysisTracker) - stays
  /// running even if this screen is closed before it finishes; refreshes
  /// the list on completion only if still mounted and on this screen.
  void _analyzeImage(DroneImage image) {
    setState(() {});
    DroneAnalysisTracker.instance.start(_flight.id, image.id).then((_) {
      if (mounted) _refresh();
    }).catchError((e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(e is ApiException ? e.message : 'AI analysis failed')),
        );
        setState(() {});
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    final inProgress = _flight.status == 'in_progress';
    return Scaffold(
      appBar: AppBar(
        title: Text('Flight · ${_flight.droneId}'),
        actions: [
          if (inProgress)
            IconButton(
              icon: const Icon(Icons.camera_enhance_outlined),
              tooltip: 'Scan mode',
              onPressed: () async {
                await Navigator.of(context).push(
                  MaterialPageRoute(builder: (_) => DroneScanScreen(flightId: _flight.id)),
                );
                _refresh();
              },
            ),
          IconButton(icon: const Icon(Icons.edit_outlined), onPressed: _editDroneId),
        ],
      ),
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
              Row(
                children: [
                  Text('Analysis summary', style: Theme.of(context).textTheme.titleMedium),
                  IconButton(
                    icon: const Icon(Icons.info_outline, size: 20),
                    visualDensity: VisualDensity.compact,
                    onPressed: _showMetricsExplainer,
                  ),
                ],
              ),
              const SizedBox(height: 4),
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

  Future<void> _showMetricsExplainer() async {
    await showModalBottomSheet(
      context: context,
      showDragHandle: true,
      isScrollControlled: true,
      builder: (context) => ConstrainedBox(
        constraints: BoxConstraints(maxHeight: MediaQuery.of(context).size.height * 0.8),
        child: SingleChildScrollView(
          padding: const EdgeInsets.fromLTRB(20, 0, 20, 24),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text('What these numbers mean', style: Theme.of(context).textTheme.titleMedium),
              const SizedBox(height: 16),
              _metricExplainer('NDVI (vegetation index)',
                  'A score from the photo\'s colors that estimates how green and leafy the crop looks. '
                  'Higher generally means more healthy live leaf cover; low or negative usually means bare soil, dead plants, or stress.'),
              _metricExplainer('NDRE',
                  'Similar idea to NDVI, but more sensitive to chlorophyll/nitrogen levels in the leaves - it can catch early nutrient '
                  'stress that NDVI sometimes misses, before the plant visibly yellows.'),
              _metricExplainer('Canopy coverage',
                  'What share of the photo is covered by living plant leaves, as a percentage - the rest is bare soil, shadow, or other.'),
              _metricExplainer('Canopy vigor',
                  'A simple good/moderate/low read on how vigorous the visible canopy looks, based on how much of it shows strong, healthy green.'),
              const SizedBox(height: 4),
              Container(
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(color: Colors.orange.withValues(alpha: 0.12), borderRadius: BorderRadius.circular(8)),
                child: Text(
                  'Right now these are estimated from an ordinary photo, not a real infrared sensor - treat them as a rough scouting cue, not a precise measurement.',
                  style: TextStyle(color: Colors.orange.shade900, fontSize: 13),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _metricExplainer(String title, String body) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 14),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(title, style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 14)),
          const SizedBox(height: 2),
          Text(body, style: const TextStyle(fontSize: 13, color: Colors.black87, height: 1.4)),
        ],
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
            const SizedBox(height: 8),
            Row(
              children: [
                Expanded(
                  child: Text(_flight.boundaryPolygon == null
                      ? 'No survey boundary traced yet'
                      : 'Boundary: ${_flight.boundaryPolygon!.length} points'),
                ),
                TextButton(onPressed: _editBoundary, child: Text(_flight.boundaryPolygon == null ? 'Trace' : 'Edit')),
                IconButton(
                  icon: const Icon(Icons.file_upload_outlined, size: 20),
                  tooltip: 'Import from KML',
                  onPressed: _importKmlBoundary,
                ),
                IconButton(
                  icon: const Icon(Icons.bookmark_outline, size: 20),
                  tooltip: 'Load saved template',
                  onPressed: _loadSavedBoundary,
                ),
              ],
            ),
            if (_flight.surveyGoals != null && _flight.surveyGoals!.isNotEmpty) ...[
              const SizedBox(height: 8),
              Wrap(
                spacing: 6,
                children: [
                  for (final goal in _flight.surveyGoals!)
                    Chip(
                      label: Text(goal == 'count' ? 'Count plants/trees' : 'Health analysis'),
                      visualDensity: VisualDensity.compact,
                    ),
                ],
              ),
            ],
            if (_flight.surveyNotes != null && _flight.surveyNotes!.isNotEmpty) ...[
              const SizedBox(height: 8),
              Text(_flight.surveyNotes!, style: const TextStyle(color: Colors.black54, fontSize: 13)),
            ],
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
                Text(
                  'Estimated from ordinary photos, not real infrared readings - a rough scouting cue.',
                  style: TextStyle(color: Colors.orange.shade800, fontSize: 12),
                ),
                if (summary.meanCanopyCoveragePct != null) ...[
                  const SizedBox(height: 8),
                  Text('Average canopy coverage: ${summary.meanCanopyCoveragePct!.toStringAsFixed(0)}%'),
                ],
                if (summary.healthStatusHistogram.isNotEmpty)
                  Text('Health: ${summary.healthStatusHistogram.entries.map((e) => '${plainHealthLabel(e.key)} (${e.value})').join(', ')}'),
                if (summary.vigorLevelHistogram.isNotEmpty)
                  Text('Vigor: ${summary.vigorLevelHistogram.entries.map((e) => '${plainVigorLabel(e.key) ?? e.key} (${e.value})').join(', ')}'),
                if (summary.meanNdvi != null) ...[
                  const SizedBox(height: 8),
                  Text(
                    'Mean vegetation index (NDVI): ${summary.meanNdvi!.toStringAsFixed(2)}',
                    style: const TextStyle(color: Colors.black54, fontSize: 12),
                  ),
                ],
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
            children: images.map((img) {
              final analyzing = DroneAnalysisTracker.instance.isPending(img.id);
              final subtitleLines = [
                if (img.analysis != null)
                  [
                    plainHealthLabel(img.analysis!.healthStatus),
                    if (img.analysis!.canopyCoveragePct != null)
                      '${img.analysis!.canopyCoveragePct!.toStringAsFixed(0)}% coverage',
                  ].join(' · '),
                if (img.diagnosis != null)
                  'AI: ${img.diagnosis!.severity ?? (img.diagnosis!.isHealthy ? 'healthy' : 'needs review')}'
                  '${img.diagnosis!.estimatedCount != null ? ' · ~${img.diagnosis!.estimatedCount} plants' : ''}',
                if (analyzing) 'AI analysis running...',
              ];
              return ListTile(
                leading: ClipRRect(
                  borderRadius: BorderRadius.circular(6),
                  child: SizedBox(
                    width: 48,
                    height: 48,
                    child: DroneImageView(flightId: img.flightId, imageId: img.id),
                  ),
                ),
                title: Text(img.treeId ?? 'Waypoint ${img.waypointIndex}'),
                subtitle: subtitleLines.isEmpty ? null : Text(subtitleLines.join('\n')),
                isThreeLine: subtitleLines.length > 1,
                onTap: () async {
                  await Navigator.of(context).push(
                    MaterialPageRoute(builder: (_) => DroneImageDetailScreen(image: img)),
                  );
                  if (mounted) _refresh();
                },
                trailing: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    if (analyzing)
                      const Padding(
                        padding: EdgeInsets.all(8),
                        child: SizedBox(height: 18, width: 18, child: CircularProgressIndicator(strokeWidth: 2)),
                      )
                    else if (img.diagnosis == null)
                      IconButton(
                        icon: const Icon(Icons.auto_awesome, size: 20),
                        tooltip: 'Analyze with AI',
                        onPressed: () => _analyzeImage(img),
                      ),
                    IconButton(
                      icon: const Icon(Icons.delete_outline, size: 20),
                      onPressed: () => _deleteImage(img),
                    ),
                  ],
                ),
              );
            }).toList(),
          ),
        );
      },
    );
  }
}
