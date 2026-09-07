import 'package:flutter/material.dart';

import 'drone_models.dart';

/// Renders a DroneDiagnosis (or the "not analyzed yet" call-to-action when
/// there isn't one) - shared between DroneImageCaptureScreen (just-captured
/// photo) and DroneImageDetailScreen (viewing an existing one from the
/// flight's photo list) so the two don't drift.
class DroneDiagnosisView extends StatelessWidget {
  final DroneDiagnosis? diagnosis;
  final bool analyzing;
  final VoidCallback? onAnalyze;

  const DroneDiagnosisView({
    super.key,
    required this.diagnosis,
    this.analyzing = false,
    this.onAnalyze,
  });

  @override
  Widget build(BuildContext context) {
    final diagnosis = this.diagnosis;
    if (diagnosis == null) {
      return Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          const Text(
            'The NDVI read above is instant and free. For a deeper read - disease/pest '
            'diagnosis, treatment advice, or a rough plant count - send this photo to the AI. '
            'Takes about 15-20 seconds.',
            style: TextStyle(color: Colors.black54, fontSize: 12),
          ),
          const SizedBox(height: 12),
          OutlinedButton.icon(
            onPressed: analyzing ? null : onAnalyze,
            icon: analyzing
                ? const SizedBox(height: 16, width: 16, child: CircularProgressIndicator(strokeWidth: 2))
                : const Icon(Icons.auto_awesome),
            label: Text(analyzing ? 'Analyzing...' : 'Analyze with AI'),
          ),
        ],
      );
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            Icon(diagnosis.isHealthy ? Icons.check_circle : Icons.warning_amber, color: diagnosis.isHealthy ? Colors.green : Colors.orange),
            const SizedBox(width: 8),
            Expanded(child: Text('AI analysis', style: Theme.of(context).textTheme.titleSmall)),
            if (diagnosis.severity != null)
              Chip(label: Text(diagnosis.severity!), visualDensity: VisualDensity.compact),
          ],
        ),
        const SizedBox(height: 8),
        if (diagnosis.diseaseName != null) Text(diagnosis.diseaseName!),
        if (diagnosis.confidence != null) ...[
          const SizedBox(height: 4),
          Text('Confidence: ${(diagnosis.confidence! * 100).toStringAsFixed(0)}%', style: const TextStyle(color: Colors.black54, fontSize: 12)),
        ],
        if (diagnosis.estimatedCount != null) ...[
          const SizedBox(height: 12),
          Text('Estimated count: ${diagnosis.estimatedCount}', style: Theme.of(context).textTheme.titleSmall),
          if (diagnosis.countNotes != null)
            Padding(
              padding: const EdgeInsets.only(top: 2),
              child: Text(diagnosis.countNotes!, style: const TextStyle(color: Colors.black54, fontSize: 12)),
            ),
        ],
        if (diagnosis.topTreatmentActions.isNotEmpty) ...[
          const SizedBox(height: 12),
          Text('Recommended actions', style: Theme.of(context).textTheme.titleSmall),
          const SizedBox(height: 4),
          for (final action in diagnosis.topTreatmentActions)
            Padding(padding: const EdgeInsets.only(top: 4), child: Text('• $action')),
        ],
      ],
    );
  }
}
