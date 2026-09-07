import 'package:flutter/material.dart';

import '../../core/api_exception.dart';
import 'drone_analysis_tracker.dart';
import 'drone_diagnosis_view.dart';
import 'drone_image_view.dart';
import 'drone_models.dart';
import 'drone_ndvi_view.dart';

/// Full view of one already-captured photo - the NDVI/vigor read it always
/// had, plus its AI diagnosis once requested. Reached by tapping a photo in
/// the flight's photo list (see DroneFlightDetailScreen._buildImagesList).
class DroneImageDetailScreen extends StatefulWidget {
  final DroneImage image;

  const DroneImageDetailScreen({super.key, required this.image});

  @override
  State<DroneImageDetailScreen> createState() => _DroneImageDetailScreenState();
}

class _DroneImageDetailScreenState extends State<DroneImageDetailScreen> {
  late DroneImage _image;
  bool _analyzing = false;

  @override
  void initState() {
    super.initState();
    _image = widget.image;
  }

  Future<void> _analyzeWithAI() async {
    final analyzingImageId = _image.id;
    setState(() => _analyzing = true);
    try {
      final updated = await DroneAnalysisTracker.instance.start(_image.flightId, _image.id);
      if (!mounted || _image.id != analyzingImageId) return;
      setState(() => _image = updated);
    } on ApiException catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(e.message)));
    } finally {
      if (mounted && _image.id == analyzingImageId) setState(() => _analyzing = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text(_image.treeId ?? 'Waypoint ${_image.waypointIndex}')),
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              AspectRatio(
                aspectRatio: 1,
                child: ClipRRect(
                  borderRadius: BorderRadius.circular(12),
                  child: InteractiveViewer(
                    minScale: 1,
                    maxScale: 5,
                    child: DroneImageView(
                      flightId: _image.flightId,
                      imageId: _image.id,
                      overlay: _image.analysis?.hasOverlay == true,
                    ),
                  ),
                ),
              ),
              const Padding(
                padding: EdgeInsets.only(top: 4),
                child: Text('Pinch to zoom in on the photo', style: TextStyle(color: Colors.black45, fontSize: 11)),
              ),
              const SizedBox(height: 16),
              Card(
                child: Padding(
                  padding: const EdgeInsets.all(16),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      DroneNdviView(
                        analysis: _image.analysis,
                        hasRealNir: _image.hasRealNir,
                        hasOverlay: _image.analysis?.hasOverlay == true,
                      ),
                      const Divider(height: 32),
                      DroneDiagnosisView(diagnosis: _image.diagnosis, analyzing: _analyzing, onAnalyze: _analyzeWithAI),
                    ],
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
