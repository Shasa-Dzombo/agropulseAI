import 'package:flutter/material.dart';

import 'diagnosis_models.dart';

class DiagnosisResultScreen extends StatelessWidget {
  final Diagnosis diagnosis;

  const DiagnosisResultScreen({super.key, required this.diagnosis});

  @override
  Widget build(BuildContext context) {
    final isFailed = diagnosis.status == 'failed';
    final isPending = !diagnosis.isTerminal;

    return Scaffold(
      appBar: AppBar(title: const Text('Diagnosis result')),
      body: ListView(
        padding: const EdgeInsets.all(24),
        children: [
          if (isPending) ...[
            const Center(child: CircularProgressIndicator()),
            const SizedBox(height: 16),
            Text('Status: ${diagnosis.status}', textAlign: TextAlign.center),
          ] else if (isFailed) ...[
            Row(
              children: [
                const Icon(Icons.error_outline, color: Colors.red),
                const SizedBox(width: 8),
                Expanded(child: Text('Diagnosis failed', style: Theme.of(context).textTheme.titleMedium)),
              ],
            ),
            const SizedBox(height: 8),
            Text(diagnosis.statusMessage ?? 'Unknown error', style: const TextStyle(color: Colors.red)),
          ] else ...[
            Text(diagnosis.primaryDiagnosis ?? 'No diagnosis', style: Theme.of(context).textTheme.headlineSmall),
            const SizedBox(height: 4),
            Wrap(
              spacing: 8,
              children: [
                if (diagnosis.diseaseCategory != null) Chip(label: Text(diagnosis.diseaseCategory!)),
                if (diagnosis.severityLevel != null) Chip(label: Text('Severity: ${diagnosis.severityLevel}')),
                if (diagnosis.confidenceScore != null)
                  Chip(label: Text('${(diagnosis.confidenceScore! * 100).toStringAsFixed(0)}% confidence')),
              ],
            ),
            if (diagnosis.immediateActions.isNotEmpty) ...[
              const SizedBox(height: 24),
              Text('Treatment', style: Theme.of(context).textTheme.titleMedium),
              const SizedBox(height: 8),
              ...diagnosis.immediateActions.map((a) => Padding(
                    padding: const EdgeInsets.only(bottom: 4),
                    child: Text('• $a'),
                  )),
            ],
            if (diagnosis.preventiveMeasures.isNotEmpty) ...[
              const SizedBox(height: 24),
              Text('Prevention', style: Theme.of(context).textTheme.titleMedium),
              const SizedBox(height: 8),
              ...diagnosis.preventiveMeasures.map((a) => Padding(
                    padding: const EdgeInsets.only(bottom: 4),
                    child: Text('• $a'),
                  )),
            ],
          ],
        ],
      ),
    );
  }
}
