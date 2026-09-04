/// Mirrors app/schemas/farm_input.py's FarmInputRecordResponse.
class FarmInputRecord {
  final int id;
  final int farmId;
  final String entryType; // 'purchase' | 'application'
  final String category; // seed | fertilizer | pesticide | labor | other
  final String itemName;
  final double? quantity;
  final String? unit;
  final double? costKsh;
  final String? notes;
  final DateTime entryDate;

  FarmInputRecord({
    required this.id,
    required this.farmId,
    required this.entryType,
    required this.category,
    required this.itemName,
    required this.quantity,
    required this.unit,
    required this.costKsh,
    required this.notes,
    required this.entryDate,
  });

  factory FarmInputRecord.fromJson(Map<String, dynamic> json) => FarmInputRecord(
        id: json['id'] as int,
        farmId: json['farm_id'] as int,
        entryType: json['entry_type'] as String,
        category: json['category'] as String,
        itemName: json['item_name'] as String,
        quantity: (json['quantity'] as num?)?.toDouble(),
        unit: json['unit'] as String?,
        costKsh: json['cost_ksh'] == null ? null : double.parse(json['cost_ksh'].toString()),
        notes: json['notes'] as String?,
        entryDate: DateTime.parse(json['entry_date'] as String),
      );
}

/// Mirrors app/schemas/farm_input.py's FarmInputListResponse.
class FarmInputList {
  final List<FarmInputRecord> items;
  final double totalCostKsh;

  FarmInputList({required this.items, required this.totalCostKsh});

  factory FarmInputList.fromJson(Map<String, dynamic> json) => FarmInputList(
        items: (json['items'] as List).map((e) => FarmInputRecord.fromJson(e as Map<String, dynamic>)).toList(),
        totalCostKsh: double.parse(json['total_cost_ksh'].toString()),
      );
}

/// Mirrors app/schemas/farm_input.py's FarmYieldRecordResponse.
class FarmYieldRecord {
  final int id;
  final int farmId;
  final String crop;
  final String seasonLabel;
  final DateTime? plantedDate;
  final double? expectedYieldKg;
  final double? actualYieldKg;
  final DateTime? harvestDate;
  final String? notes;
  // Computed server-side from app.services.yield_estimation - a real
  // national-average reference multiplied by farm size, not a prediction.
  // Null when the crop isn't in the reference table yet (only maize/beans
  // today) - never a guessed number.
  final double? estimatedYieldKg;
  final String? estimateSource;

  FarmYieldRecord({
    required this.id,
    required this.farmId,
    required this.crop,
    required this.seasonLabel,
    required this.plantedDate,
    required this.expectedYieldKg,
    required this.actualYieldKg,
    required this.harvestDate,
    required this.notes,
    required this.estimatedYieldKg,
    required this.estimateSource,
  });

  factory FarmYieldRecord.fromJson(Map<String, dynamic> json) => FarmYieldRecord(
        id: json['id'] as int,
        farmId: json['farm_id'] as int,
        crop: json['crop'] as String,
        seasonLabel: json['season_label'] as String,
        plantedDate: json['planted_date'] == null ? null : DateTime.parse(json['planted_date'] as String),
        expectedYieldKg: (json['expected_yield_kg'] as num?)?.toDouble(),
        actualYieldKg: (json['actual_yield_kg'] as num?)?.toDouble(),
        harvestDate: json['harvest_date'] == null ? null : DateTime.parse(json['harvest_date'] as String),
        notes: json['notes'] as String?,
        estimatedYieldKg: (json['estimated_yield_kg'] as num?)?.toDouble(),
        estimateSource: json['estimate_source'] as String?,
      );
}
