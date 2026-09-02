// Guards against drift from app/api/farms.py's FarmListResponse/
// PaginatedFarmsResponse shape - matches an actual live response captured
// while fixing that endpoint (see mobile/CHANGELOG.md 2026-08-31).

import 'package:flutter_test/flutter_test.dart';
import 'package:agropulse_mobile/features/farms/farm_models.dart';

void main() {
  test('Farm.fromJson parses a real backend response, including null primary_crop', () {
    final farm = Farm.fromJson({
      'id': 561,
      'uuid': '25e483ec-ce9f-4d94-943c-e0f8a3527c19',
      'name': "James's Farm 1",
      'county': 'Thika',
      'size_acres': 35.66088631211406,
      'primary_crop': null,
      'latitude': -0.5913495310969747,
      'longitude': 36.93454267791075,
      'is_active': true,
      'verification_status': null,
      'created_at': '2026-07-13T11:44:17.088979Z',
    });

    expect(farm.name, "James's Farm 1");
    expect(farm.primaryCrop, isNull);
    expect(farm.sizeAcres, closeTo(35.66, 0.01));
  });

  test('FarmWeather.fromJson parses a real GET /farms/{id}/weather response', () {
    final weather = FarmWeather.fromJson({
      'farm_id': 803,
      'current': {
        'temperature_c': 16.02,
        'feels_like_c': 15.98,
        'humidity_pct': 88,
        'wind_speed_ms': 4.63,
        'rainfall_mm': 0.0,
        'conditions': 'overcast clouds',
        'observed_at': '2026-09-02T09:43:27',
      },
      'disease_pressure': {
        'risk_level': 'high',
        'indicators': [
          'High humidity (88%) with moderate temperature (16.0°C) favors extended leaf wetness and fungal spore germination',
        ],
      },
      'agricultural_alerts': [],
    });

    expect(weather.temperatureC, closeTo(16.02, 0.01));
    expect(weather.humidityPct, 88);
    expect(weather.diseaseRiskLevel, 'high');
    expect(weather.diseaseIndicators, hasLength(1));
    expect(weather.alerts, isEmpty);
  });

  test('AgriculturalAlert.fromJson parses a real alert shape', () {
    final alert = AgriculturalAlert.fromJson({
      'alert_type': 'frost',
      'severity': 'critical',
      'description': 'Frost conditions detected. Crops at risk.',
      'recommendations': ['Cover sensitive plants', 'Harvest vulnerable crops immediately'],
    });

    expect(alert.alertType, 'frost');
    expect(alert.severity, 'critical');
    expect(alert.recommendations, hasLength(2));
  });

  test('PaginatedFarms.fromJson parses the envelope and item list', () {
    final page = PaginatedFarms.fromJson({
      'items': [
        {
          'id': 1, 'uuid': 'uuid-1', 'name': 'Farm A', 'county': 'Kiambu',
          'size_acres': 2.0, 'primary_crop': null, 'latitude': 0.0, 'longitude': 0.0,
          'is_active': true, 'verification_status': null, 'created_at': '2026-01-01T00:00:00Z',
        },
      ],
      'total': 240,
      'page': 1,
      'page_size': 20,
      'pages': 12,
    });

    expect(page.items.length, 1);
    expect(page.total, 240);
    expect(page.pages, 12);
  });
}
