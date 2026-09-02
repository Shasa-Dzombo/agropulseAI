/// Mirrors app/api/farms.py's FarmListResponse / PaginatedFarmsResponse.
class Farm {
  final int id;
  final String uuid;
  final String name;
  final String county;
  final double sizeAcres;
  final String? primaryCrop;
  final double latitude;
  final double longitude;
  final bool isActive;

  Farm({
    required this.id,
    required this.uuid,
    required this.name,
    required this.county,
    required this.sizeAcres,
    required this.primaryCrop,
    required this.latitude,
    required this.longitude,
    required this.isActive,
  });

  factory Farm.fromJson(Map<String, dynamic> json) => Farm(
        id: json['id'] as int,
        uuid: json['uuid'] as String,
        name: json['name'] as String,
        county: json['county'] as String,
        sizeAcres: (json['size_acres'] as num).toDouble(),
        primaryCrop: json['primary_crop'] as String?,
        latitude: (json['latitude'] as num).toDouble(),
        longitude: (json['longitude'] as num).toDouble(),
        isActive: json['is_active'] as bool,
      );
}

/// Mirrors app/api/farms.py's AgriculturalAlertOut.
class AgriculturalAlert {
  final String alertType;
  final String severity;
  final String description;
  final List<String> recommendations;

  AgriculturalAlert({
    required this.alertType,
    required this.severity,
    required this.description,
    required this.recommendations,
  });

  factory AgriculturalAlert.fromJson(Map<String, dynamic> json) => AgriculturalAlert(
        alertType: json['alert_type'] as String,
        severity: json['severity'] as String,
        description: json['description'] as String,
        recommendations: (json['recommendations'] as List).map((e) => e as String).toList(),
      );
}

/// Mirrors app/api/farms.py's FarmWeatherOut (GET /farms/{id}/weather).
class FarmWeather {
  final double temperatureC;
  final double feelsLikeC;
  final int humidityPct;
  final double windSpeedMs;
  final double rainfallMm;
  final String conditions;
  final DateTime observedAt;
  final String diseaseRiskLevel;
  final List<String> diseaseIndicators;
  final List<AgriculturalAlert> alerts;

  FarmWeather({
    required this.temperatureC,
    required this.feelsLikeC,
    required this.humidityPct,
    required this.windSpeedMs,
    required this.rainfallMm,
    required this.conditions,
    required this.observedAt,
    required this.diseaseRiskLevel,
    required this.diseaseIndicators,
    required this.alerts,
  });

  factory FarmWeather.fromJson(Map<String, dynamic> json) {
    final current = json['current'] as Map<String, dynamic>;
    final diseasePressure = json['disease_pressure'] as Map<String, dynamic>;
    return FarmWeather(
      temperatureC: (current['temperature_c'] as num).toDouble(),
      feelsLikeC: (current['feels_like_c'] as num).toDouble(),
      humidityPct: current['humidity_pct'] as int,
      windSpeedMs: (current['wind_speed_ms'] as num).toDouble(),
      rainfallMm: (current['rainfall_mm'] as num).toDouble(),
      conditions: current['conditions'] as String,
      observedAt: DateTime.parse(current['observed_at'] as String),
      diseaseRiskLevel: diseasePressure['risk_level'] as String,
      diseaseIndicators: (diseasePressure['indicators'] as List).map((e) => e as String).toList(),
      alerts: (json['agricultural_alerts'] as List)
          .map((e) => AgriculturalAlert.fromJson(e as Map<String, dynamic>))
          .toList(),
    );
  }
}

class PaginatedFarms {
  final List<Farm> items;
  final int total;
  final int page;
  final int pages;

  PaginatedFarms({required this.items, required this.total, required this.page, required this.pages});

  factory PaginatedFarms.fromJson(Map<String, dynamic> json) => PaginatedFarms(
        items: (json['items'] as List).map((e) => Farm.fromJson(e as Map<String, dynamic>)).toList(),
        total: json['total'] as int,
        page: json['page'] as int,
        pages: json['pages'] as int,
      );
}
