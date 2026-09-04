import 'package:flutter/material.dart';

import '../../core/api_exception.dart';
import '../drones/drone_flight_list_screen.dart';
import '../farm_inputs/farm_inputs_screen.dart';
import 'farm_models.dart';
import 'farm_repository.dart';
import 'farm_satellite_map.dart';

class FarmDetailScreen extends StatefulWidget {
  final Farm farm;

  const FarmDetailScreen({super.key, required this.farm});

  @override
  State<FarmDetailScreen> createState() => _FarmDetailScreenState();
}

class _FarmDetailScreenState extends State<FarmDetailScreen> {
  late Future<FarmWeather> _weatherFuture;

  @override
  void initState() {
    super.initState();
    _weatherFuture = FarmRepository.instance.getFarmWeather(widget.farm.id);
  }

  void _retry() {
    setState(() => _weatherFuture = FarmRepository.instance.getFarmWeather(widget.farm.id));
  }

  Color _riskColor(String level) {
    switch (level) {
      case 'high':
        return Colors.red;
      case 'moderate':
        return Colors.orange;
      default:
        return Colors.green;
    }
  }

  Color _severityColor(String severity) {
    switch (severity) {
      case 'critical':
        return Colors.red.shade900;
      case 'high':
        return Colors.red;
      case 'medium':
        return Colors.orange;
      default:
        return Colors.blueGrey;
    }
  }

  @override
  Widget build(BuildContext context) {
    final farm = widget.farm;
    return Scaffold(
      appBar: AppBar(title: Text(farm.name)),
      body: SafeArea(
        child: ListView(
          padding: const EdgeInsets.all(16),
          children: [
            Card(
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(farm.name, style: Theme.of(context).textTheme.titleLarge),
                    const SizedBox(height: 4),
                    Text('${farm.county} · ${farm.sizeAcres.toStringAsFixed(1)} acres'),
                    if (farm.primaryCrop != null) Text('Growing: ${farm.primaryCrop}'),
                    if (!farm.isActive) const Padding(
                      padding: EdgeInsets.only(top: 8),
                      child: Chip(label: Text('Inactive')),
                    ),
                  ],
                ),
              ),
            ),
            const SizedBox(height: 16),
            OutlinedButton.icon(
              onPressed: () => Navigator.of(context).push(MaterialPageRoute(
                builder: (_) => DroneFlightListScreen(
                  farmId: farm.id, farmLatitude: farm.latitude, farmLongitude: farm.longitude,
                ),
              )),
              icon: const Icon(Icons.flight_takeoff),
              label: const Text('Drone flights'),
            ),
            const SizedBox(height: 8),
            OutlinedButton.icon(
              onPressed: () => Navigator.of(context).push(MaterialPageRoute(
                builder: (_) => FarmInputsScreen(farmId: farm.id),
              )),
              icon: const Icon(Icons.receipt_long),
              label: const Text('Inputs & yield'),
            ),
            const SizedBox(height: 16),
            Text('Satellite view', style: Theme.of(context).textTheme.titleMedium),
            const SizedBox(height: 8),
            FarmSatelliteMap(
              latitude: farm.latitude,
              longitude: farm.longitude,
              farmName: farm.name,
            ),
            const SizedBox(height: 16),
            Text('Weather', style: Theme.of(context).textTheme.titleMedium),
            const SizedBox(height: 8),
            FutureBuilder<FarmWeather>(
              future: _weatherFuture,
              builder: (context, snapshot) {
                if (snapshot.connectionState == ConnectionState.waiting) {
                  return const Padding(
                    padding: EdgeInsets.symmetric(vertical: 32),
                    child: Center(child: CircularProgressIndicator()),
                  );
                }
                if (snapshot.hasError) {
                  final message =
                      snapshot.error is ApiException ? (snapshot.error as ApiException).message : 'Could not load weather';
                  return Card(
                    child: Padding(
                      padding: const EdgeInsets.all(16),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(message),
                          const SizedBox(height: 8),
                          OutlinedButton(onPressed: _retry, child: const Text('Retry')),
                        ],
                      ),
                    ),
                  );
                }

                final weather = snapshot.data!;
                return Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Card(
                      child: Padding(
                        padding: const EdgeInsets.all(16),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              '${weather.temperatureC.round()}°C',
                              style: Theme.of(context).textTheme.headlineMedium,
                            ),
                            Text(weather.conditions),
                            Text('Feels like ${weather.feelsLikeC.round()}°C'),
                            const SizedBox(height: 12),
                            Wrap(
                              spacing: 16,
                              runSpacing: 8,
                              children: [
                                _statChip(Icons.water_drop, '${weather.humidityPct}% humidity'),
                                _statChip(Icons.air, '${weather.windSpeedMs.toStringAsFixed(1)} m/s wind'),
                                _statChip(Icons.umbrella, '${weather.rainfallMm.toStringAsFixed(1)} mm rain'),
                              ],
                            ),
                          ],
                        ),
                      ),
                    ),
                    const SizedBox(height: 12),
                    Card(
                      child: Padding(
                        padding: const EdgeInsets.all(16),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Row(
                              children: [
                                Icon(Icons.coronavirus, color: _riskColor(weather.diseaseRiskLevel)),
                                const SizedBox(width: 8),
                                Text(
                                  'Disease pressure: ${weather.diseaseRiskLevel}',
                                  style: TextStyle(color: _riskColor(weather.diseaseRiskLevel), fontWeight: FontWeight.bold),
                                ),
                              ],
                            ),
                            for (final indicator in weather.diseaseIndicators)
                              Padding(
                                padding: const EdgeInsets.only(top: 6),
                                child: Text('• $indicator'),
                              ),
                          ],
                        ),
                      ),
                    ),
                    if (weather.alerts.isNotEmpty) ...[
                      const SizedBox(height: 12),
                      Text('Alerts', style: Theme.of(context).textTheme.titleMedium),
                      const SizedBox(height: 8),
                      for (final alert in weather.alerts)
                        Card(
                          color: _severityColor(alert.severity).withValues(alpha: 0.08),
                          child: Padding(
                            padding: const EdgeInsets.all(16),
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Text(
                                  '${alert.alertType.toUpperCase()} · ${alert.severity}',
                                  style: TextStyle(color: _severityColor(alert.severity), fontWeight: FontWeight.bold),
                                ),
                                const SizedBox(height: 4),
                                Text(alert.description),
                                for (final rec in alert.recommendations)
                                  Padding(
                                    padding: const EdgeInsets.only(top: 4),
                                    child: Text('• $rec'),
                                  ),
                              ],
                            ),
                          ),
                        ),
                    ],
                  ],
                );
              },
            ),
          ],
        ),
      ),
    );
  }

  Widget _statChip(IconData icon, String label) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Icon(icon, size: 18),
        const SizedBox(width: 4),
        Text(label),
      ],
    );
  }
}
