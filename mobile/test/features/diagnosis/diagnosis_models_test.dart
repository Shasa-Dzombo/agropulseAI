// Guards against drift from app/api/diagnoses.py's DiagnosisResponse shape
// - matches an actual live response captured while building that endpoint
// (see mobile/CHANGELOG.md 2026-08-31).

import 'package:flutter_test/flutter_test.dart';
import 'package:agropulse_mobile/features/diagnosis/diagnosis_models.dart';

void main() {
  test('Diagnosis.fromJson parses a completed diagnosis', () {
    final diagnosis = Diagnosis.fromJson({
      'id': 1,
      'diagnosis_id': 'DX-27d5aa9ce1a1',
      'status': 'completed',
      'status_message': null,
      'image_urls': ['local_uploads/diagnoses/abc.jpg'],
      'primary_diagnosis': 'Powdery mildew',
      'disease_category': 'fungal',
      'confidence_score': 0.87,
      'severity_level': 'moderate',
      'affected_area_percentage': 15.0,
      'alternative_diagnoses': [],
      'immediate_actions': ['Apply fungicide', 'Improve ventilation'],
      'preventive_measures': ['Avoid overhead watering'],
      'created_at': '2026-08-31T07:56:56.653888Z',
      'completed_at': '2026-08-31T07:56:59.469257Z',
    });

    expect(diagnosis.primaryDiagnosis, 'Powdery mildew');
    expect(diagnosis.isTerminal, isTrue);
    expect(diagnosis.immediateActions, hasLength(2));
  });

  test('Diagnosis.fromJson parses a failed diagnosis (real captured shape)', () {
    final diagnosis = Diagnosis.fromJson({
      'id': 1,
      'diagnosis_id': 'DX-27d5aa9ce1a1',
      'status': 'failed',
      'status_message': 'Your credit balance is too low to access the Anthropic API.',
      'image_urls': ['local_uploads/diagnoses/abc.jpg'],
      'primary_diagnosis': null,
      'disease_category': null,
      'confidence_score': null,
      'severity_level': null,
      'affected_area_percentage': null,
      'alternative_diagnoses': [],
      'immediate_actions': [],
      'preventive_measures': [],
      'created_at': '2026-08-31T07:56:56.653888Z',
      'completed_at': '2026-08-31T07:56:59.469257Z',
    });

    expect(diagnosis.isTerminal, isTrue);
    expect(diagnosis.primaryDiagnosis, isNull);
    expect(diagnosis.statusMessage, contains('credit balance'));
  });
}
