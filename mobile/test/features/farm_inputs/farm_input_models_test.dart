// Guards against drift from app/schemas/farm_input.py's response shapes -
// matches actual live responses captured while wiring app/api/farm_inputs.py
// (see mobile/CHANGELOG.md).

import 'package:flutter_test/flutter_test.dart';
import 'package:agropulse_mobile/features/farm_inputs/farm_input_models.dart';

void main() {
  test('FarmInputRecord.fromJson parses a real purchase entry', () {
    final record = FarmInputRecord.fromJson({
      'id': 1, 'farm_id': 804, 'entry_type': 'purchase', 'category': 'fertilizer',
      'item_name': 'DAP fertilizer', 'quantity': 5.0, 'unit': 'bags', 'cost_ksh': '12500.00',
      'notes': null, 'entry_date': '2026-09-01', 'created_at': '2026-09-04T10:40:19.960376Z',
    });

    expect(record.entryType, 'purchase');
    expect(record.costKsh, closeTo(12500.0, 0.01));
    expect(record.unit, 'bags');
  });

  test('FarmInputRecord.fromJson parses a real application entry (no cost)', () {
    final record = FarmInputRecord.fromJson({
      'id': 2, 'farm_id': 804, 'entry_type': 'application', 'category': 'fertilizer',
      'item_name': 'DAP fertilizer', 'quantity': 2.0, 'unit': 'bags', 'cost_ksh': null,
      'notes': 'Top-dressed north plot', 'entry_date': '2026-09-03', 'created_at': '2026-09-04T10:40:20.362624Z',
    });

    expect(record.entryType, 'application');
    expect(record.costKsh, isNull);
    expect(record.notes, 'Top-dressed north plot');
  });

  test('FarmInputList.fromJson parses a real aggregate list', () {
    final list = FarmInputList.fromJson({
      'items': [
        {
          'id': 1, 'farm_id': 804, 'entry_type': 'purchase', 'category': 'fertilizer',
          'item_name': 'DAP fertilizer', 'quantity': 5.0, 'unit': 'bags', 'cost_ksh': '12500.00',
          'notes': null, 'entry_date': '2026-09-01', 'created_at': '2026-09-04T10:40:19.960376Z',
        },
      ],
      'total_cost_ksh': '12500.00',
    });

    expect(list.items, hasLength(1));
    expect(list.totalCostKsh, closeTo(12500.0, 0.01));
  });

  test('FarmYieldRecord.fromJson parses a record before and after harvest', () {
    final planted = FarmYieldRecord.fromJson({
      'id': 1, 'farm_id': 804, 'crop': 'Maize', 'season_label': '2026 long rains',
      'planted_date': '2026-03-15', 'expected_yield_kg': 1800.0, 'actual_yield_kg': null,
      'harvest_date': null, 'notes': null, 'created_at': '2026-09-04T10:40:21.034511Z',
      'estimated_yield_kg': 5055.0,
      'estimate_source': 'KNBS National Agriculture Production Report 2024 (national average, not county-adjusted)',
    });
    expect(planted.actualYieldKg, isNull);
    expect(planted.estimatedYieldKg, closeTo(5055.0, 0.01));

    final harvested = FarmYieldRecord.fromJson({
      'id': 1, 'farm_id': 804, 'crop': 'Maize', 'season_label': '2026 long rains',
      'planted_date': '2026-03-15', 'expected_yield_kg': 1800.0, 'actual_yield_kg': 1650.0,
      'harvest_date': '2026-08-20', 'notes': 'Slightly below expected due to dry spell in July',
      'created_at': '2026-09-04T10:40:21.034511Z', 'estimated_yield_kg': 5055.0,
      'estimate_source': 'KNBS National Agriculture Production Report 2024 (national average, not county-adjusted)',
    });
    expect(harvested.actualYieldKg, closeTo(1650.0, 0.01));
    expect(harvested.harvestDate, DateTime(2026, 8, 20));
  });

  test('FarmYieldRecord.fromJson leaves estimate null for a crop with no reference data', () {
    final record = FarmYieldRecord.fromJson({
      'id': 4, 'farm_id': 804, 'crop': 'Avocado', 'season_label': 'test', 'planted_date': null,
      'expected_yield_kg': null, 'actual_yield_kg': null, 'harvest_date': null, 'notes': null,
      'created_at': '2026-09-04T13:13:23.956807Z', 'estimated_yield_kg': null, 'estimate_source': null,
    });
    expect(record.estimatedYieldKg, isNull);
    expect(record.estimateSource, isNull);
  });
}
