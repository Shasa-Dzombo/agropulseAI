/// Mirrors app/api/diagnoses.py's DiagnosisResponse.
class Diagnosis {
  final int id;
  final String diagnosisId;
  final String status; // pending, processing, completed, failed
  final String? statusMessage;
  final List<String> imageUrls;
  final String? primaryDiagnosis;
  final String? diseaseCategory;
  final double? confidenceScore;
  final String? severityLevel;
  final double? affectedAreaPercentage;
  final List<dynamic> alternativeDiagnoses;
  final List<dynamic> immediateActions;
  final List<dynamic> preventiveMeasures;
  final DateTime createdAt;
  final DateTime? completedAt;

  Diagnosis({
    required this.id,
    required this.diagnosisId,
    required this.status,
    required this.statusMessage,
    required this.imageUrls,
    required this.primaryDiagnosis,
    required this.diseaseCategory,
    required this.confidenceScore,
    required this.severityLevel,
    required this.affectedAreaPercentage,
    required this.alternativeDiagnoses,
    required this.immediateActions,
    required this.preventiveMeasures,
    required this.createdAt,
    required this.completedAt,
  });

  bool get isTerminal => status == 'completed' || status == 'failed';

  factory Diagnosis.fromJson(Map<String, dynamic> json) => Diagnosis(
        id: json['id'] as int,
        diagnosisId: json['diagnosis_id'] as String,
        status: json['status'] as String,
        statusMessage: json['status_message'] as String?,
        imageUrls: (json['image_urls'] as List).cast<String>(),
        primaryDiagnosis: json['primary_diagnosis'] as String?,
        diseaseCategory: json['disease_category'] as String?,
        confidenceScore: (json['confidence_score'] as num?)?.toDouble(),
        severityLevel: json['severity_level'] as String?,
        affectedAreaPercentage: (json['affected_area_percentage'] as num?)?.toDouble(),
        alternativeDiagnoses: (json['alternative_diagnoses'] as List?) ?? const [],
        immediateActions: (json['immediate_actions'] as List?) ?? const [],
        preventiveMeasures: (json['preventive_measures'] as List?) ?? const [],
        createdAt: DateTime.parse(json['created_at'] as String),
        completedAt: json['completed_at'] != null ? DateTime.parse(json['completed_at'] as String) : null,
      );
}
