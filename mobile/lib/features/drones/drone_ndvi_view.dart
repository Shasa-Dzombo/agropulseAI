import 'package:flutter/material.dart';

import 'drone_models.dart';

/// Renders the always-on, free, local NDVI/vigor read (DroneImageAnalysis) -
/// shared between DroneImageCaptureScreen and DroneImageDetailScreen.
class DroneNdviView extends StatelessWidget {
  final DroneImageAnalysis? analysis;
  final bool hasRealNir;
  final bool hasOverlay;

  const DroneNdviView({
    super.key,
    required this.analysis,
    required this.hasRealNir,
    required this.hasOverlay,
  });

  String _plainSummary(DroneImageAnalysis analysis) {
    final health = plainHealthLabel(analysis.healthStatus);
    final vigor = plainVigorLabel(analysis.vigorLevel);
    return vigor == null ? health : '$health, $vigor';
  }

  @override
  Widget build(BuildContext context) {
    final analysis = this.analysis;
    if (analysis == null) return const Text('No NDVI analysis for this photo');

    final indicators = [...analysis.stressIndicators, ...analysis.vigorIndicators];

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            const Icon(Icons.check_circle, color: Colors.green),
            const SizedBox(width: 8),
            Text('Analyzed', style: Theme.of(context).textTheme.titleMedium),
          ],
        ),
        if (hasOverlay) ...[
          const SizedBox(height: 4),
          const Text(
            'Photo above is annotated: green traces the detected canopy, red boxes mark low-vigor areas.',
            style: TextStyle(color: Colors.black54, fontSize: 12),
          ),
        ],
        if (!hasRealNir) ...[
          const SizedBox(height: 12),
          Container(
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              color: Colors.orange.withValues(alpha: 0.12),
              borderRadius: BorderRadius.circular(8),
              border: Border.all(color: Colors.orange.shade300),
            ),
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Icon(Icons.info_outline, size: 18, color: Colors.orange.shade800),
                const SizedBox(width: 8),
                Expanded(
                  child: Text(
                    'Estimated from an ordinary photo, not a real infrared sensor. '
                    'Treat this as a rough scouting cue, not a precise reading.',
                    style: TextStyle(color: Colors.orange.shade900, fontSize: 13),
                  ),
                ),
              ],
            ),
          ),
        ],
        const SizedBox(height: 12),
        Text(_plainSummary(analysis), style: Theme.of(context).textTheme.bodyLarge),
        if (analysis.canopyCoveragePct != null) ...[
          const SizedBox(height: 4),
          Text('Canopy coverage: ${analysis.canopyCoveragePct!.toStringAsFixed(0)}%'),
        ],
        if (analysis.ndvi != null) ...[
          const SizedBox(height: 4),
          Text(
            'Vegetation index (NDVI): ${analysis.ndvi!.toStringAsFixed(2)}',
            style: const TextStyle(color: Colors.black54, fontSize: 12),
          ),
        ],
        if (indicators.isNotEmpty) ...[
          const SizedBox(height: 12),
          Text('What this suggests', style: Theme.of(context).textTheme.titleSmall),
          const SizedBox(height: 4),
          for (final indicator in indicators)
            Padding(padding: const EdgeInsets.only(top: 4), child: Text('• $indicator')),
        ],
      ],
    );
  }
}
