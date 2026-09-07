import 'package:flutter/material.dart';

import '../../core/api_exception.dart';
import 'drone_flight_create_screen.dart';
import 'drone_flight_detail_screen.dart';
import 'drone_models.dart';
import 'drone_repository.dart';

class DroneFlightListScreen extends StatefulWidget {
  final int farmId;
  final double farmLatitude;
  final double farmLongitude;

  const DroneFlightListScreen({
    super.key,
    required this.farmId,
    required this.farmLatitude,
    required this.farmLongitude,
  });

  @override
  State<DroneFlightListScreen> createState() => _DroneFlightListScreenState();
}

class _DroneFlightListScreenState extends State<DroneFlightListScreen> {
  late Future<List<DroneFlight>> _future;

  @override
  void initState() {
    super.initState();
    _future = DroneRepository.instance.listFlights(widget.farmId);
  }

  Future<void> _refresh() async {
    setState(() { _future = DroneRepository.instance.listFlights(widget.farmId); });
    await _future;
  }

  Future<void> _startFlight() async {
    final created = await Navigator.of(context).push<DroneFlight>(
      MaterialPageRoute(
        builder: (_) => DroneFlightCreateScreen(
          farmId: widget.farmId,
          farmLatitude: widget.farmLatitude,
          farmLongitude: widget.farmLongitude,
        ),
      ),
    );
    if (created == null || !mounted) return;
    await Navigator.of(context).push(
      MaterialPageRoute(builder: (_) => DroneFlightDetailScreen(flight: created)),
    );
    _refresh();
  }

  Future<void> _openDetail(DroneFlight flight) async {
    await Navigator.of(context).push(
      MaterialPageRoute(builder: (_) => DroneFlightDetailScreen(flight: flight)),
    );
    _refresh();
  }

  Future<bool> _confirmDeleteFlight(DroneFlight flight) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Delete flight?'),
        content: Text('This removes "${flight.droneId}" and all its captured photos and analysis. This can\'t be undone.'),
        actions: [
          TextButton(onPressed: () => Navigator.of(context).pop(false), child: const Text('Cancel')),
          TextButton(
            onPressed: () => Navigator.of(context).pop(true),
            child: const Text('Delete', style: TextStyle(color: Colors.red)),
          ),
        ],
      ),
    );
    if (confirmed != true) return false;
    try {
      await DroneRepository.instance.deleteFlight(flight.id);
      return true;
    } on ApiException catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(e.message)));
      return false;
    }
  }

  Color _statusColor(String status) {
    switch (status) {
      case 'in_progress':
        return Colors.blue;
      case 'completed':
        return Colors.green;
      case 'aborted':
      case 'failed':
        return Colors.red;
      default:
        return Colors.grey;
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Drone flights')),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: _startFlight,
        icon: const Icon(Icons.flight_takeoff),
        label: const Text('Start flight'),
      ),
      body: SafeArea(child: _buildList()),
    );
  }

  Widget _buildList() {
    return FutureBuilder<List<DroneFlight>>(
      future: _future,
      builder: (context, snapshot) {
        if (snapshot.connectionState == ConnectionState.waiting) {
          return const Center(child: CircularProgressIndicator());
        }
        if (snapshot.hasError) {
          final message = snapshot.error is ApiException ? (snapshot.error as ApiException).message : 'Something went wrong';
          return Center(
            child: Padding(
              padding: const EdgeInsets.all(24),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Text(message, textAlign: TextAlign.center),
                  const SizedBox(height: 12),
                  FilledButton(onPressed: _refresh, child: const Text('Retry')),
                ],
              ),
            ),
          );
        }

        final flights = snapshot.data!;
        if (flights.isEmpty) {
          return const Center(child: Text('No drone flights yet'));
        }

        return RefreshIndicator(
          onRefresh: _refresh,
          child: ListView.separated(
            padding: const EdgeInsets.only(bottom: 80),
            itemCount: flights.length,
            separatorBuilder: (_, _) => const Divider(height: 1),
            itemBuilder: (context, index) {
              final flight = flights[index];
              return Dismissible(
                key: ValueKey(flight.id),
                direction: DismissDirection.endToStart,
                confirmDismiss: (_) => _confirmDeleteFlight(flight),
                onDismissed: (_) => _refresh(),
                background: Container(
                  color: Colors.red,
                  alignment: Alignment.centerRight,
                  padding: const EdgeInsets.only(right: 20),
                  child: const Icon(Icons.delete, color: Colors.white),
                ),
                child: ListTile(
                  leading: const Icon(Icons.flight),
                  title: Text(flight.droneId),
                  subtitle: Text(flight.startedAt == null
                      ? flight.status
                      : '${flight.startedAt!.year}-${flight.startedAt!.month.toString().padLeft(2, '0')}-${flight.startedAt!.day.toString().padLeft(2, '0')}'),
                  trailing: Chip(
                    label: Text(flight.status.replaceAll('_', ' ')),
                    backgroundColor: _statusColor(flight.status).withValues(alpha: 0.15),
                    labelStyle: TextStyle(color: _statusColor(flight.status)),
                  ),
                  onTap: () => _openDetail(flight),
                ),
              );
            },
          ),
        );
      },
    );
  }
}
