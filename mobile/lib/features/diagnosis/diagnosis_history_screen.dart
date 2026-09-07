import 'package:flutter/material.dart';

import '../../core/api_exception.dart';
import 'diagnosis_image_view.dart';
import 'diagnosis_models.dart';
import 'diagnosis_repository.dart';
import 'diagnosis_result_screen.dart';

/// Every completed diagnosis - both from this screen's own upload flow and
/// from drone photo "Analyze with AI" (see DroneAIService.analyze_image) -
/// they share the same backend Diagnosis table, so this one list already
/// covers both without any drone-specific code here.
class DiagnosisHistoryScreen extends StatefulWidget {
  const DiagnosisHistoryScreen({super.key});

  @override
  State<DiagnosisHistoryScreen> createState() => _DiagnosisHistoryScreenState();
}

class _DiagnosisHistoryScreenState extends State<DiagnosisHistoryScreen> {
  late Future<List<Diagnosis>> _future;

  @override
  void initState() {
    super.initState();
    _future = DiagnosisRepository.instance.listDiagnoses();
  }

  Future<void> _refresh() async {
    setState(() { _future = DiagnosisRepository.instance.listDiagnoses(); });
    await _future;
  }

  Color _severityColor(String? severity) {
    switch (severity) {
      case 'severe':
      case 'critical':
        return Colors.red;
      case 'moderate':
        return Colors.orange;
      case 'mild':
        return Colors.amber;
      case 'none':
        return Colors.green;
      default:
        return Colors.grey;
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Diagnosis history')),
      body: SafeArea(
        child: RefreshIndicator(
          onRefresh: _refresh,
          child: FutureBuilder<List<Diagnosis>>(
            future: _future,
            builder: (context, snapshot) {
              if (snapshot.connectionState == ConnectionState.waiting) {
                return const Center(child: CircularProgressIndicator());
              }
              if (snapshot.hasError) {
                final message = snapshot.error is ApiException ? (snapshot.error as ApiException).message : 'Could not load diagnoses';
                return ListView(children: [
                  Padding(padding: const EdgeInsets.all(24), child: Text(message, textAlign: TextAlign.center)),
                ]);
              }
              final items = snapshot.data!;
              if (items.isEmpty) {
                return ListView(children: const [
                  Padding(
                    padding: EdgeInsets.all(24),
                    child: Text('No diagnoses yet. Submit a photo for diagnosis, or analyze a drone photo, to see it here.', textAlign: TextAlign.center),
                  ),
                ]);
              }
              return ListView.separated(
                padding: const EdgeInsets.all(16),
                itemCount: items.length,
                separatorBuilder: (_, _) => const SizedBox(height: 8),
                itemBuilder: (context, index) {
                  final d = items[index];
                  final date = d.createdAt;
                  final dateLabel = '${date.year}-${date.month.toString().padLeft(2, '0')}-${date.day.toString().padLeft(2, '0')}';
                  return Card(
                    child: ListTile(
                      leading: d.imageUrls.isEmpty
                          ? Icon(
                              d.status == 'failed' ? Icons.error_outline : (d.diseaseCategory == 'healthy' ? Icons.check_circle : Icons.warning_amber),
                              color: d.status == 'failed'
                                  ? Colors.red
                                  : (d.diseaseCategory == 'healthy' ? Colors.green : _severityColor(d.severityLevel)),
                            )
                          : ClipRRect(
                              borderRadius: BorderRadius.circular(6),
                              child: SizedBox(width: 48, height: 48, child: DiagnosisImageView(diagnosisId: d.id)),
                            ),
                      title: Text(
                        d.status == 'failed' ? 'Diagnosis failed' : (d.primaryDiagnosis ?? 'No diagnosis'),
                        maxLines: 2,
                        overflow: TextOverflow.ellipsis,
                      ),
                      subtitle: Text([
                        dateLabel,
                        if (d.severityLevel != null) d.severityLevel!,
                        if (!d.isTerminal) 'Processing...',
                      ].join(' · ')),
                      onTap: () => Navigator.of(context).push(
                        MaterialPageRoute(builder: (_) => DiagnosisResultScreen(diagnosis: d)),
                      ),
                    ),
                  );
                },
              );
            },
          ),
        ),
      ),
    );
  }
}
