import 'package:flutter/material.dart';

import '../../core/api_exception.dart';
import 'farm_create_screen.dart';
import 'farm_detail_screen.dart';
import 'farm_models.dart';
import 'farm_repository.dart';

class FarmListScreen extends StatefulWidget {
  const FarmListScreen({super.key});

  @override
  State<FarmListScreen> createState() => _FarmListScreenState();
}

class _FarmListScreenState extends State<FarmListScreen> {
  late Future<PaginatedFarms> _future;

  @override
  void initState() {
    super.initState();
    _future = FarmRepository.instance.listFarms();
  }

  Future<void> _refresh() async {
    setState(() => _future = FarmRepository.instance.listFarms());
    await _future;
  }

  Future<void> _addFarm() async {
    final created = await Navigator.of(context).push<bool>(
      MaterialPageRoute(builder: (_) => const FarmCreateScreen()),
    );
    if (created == true) _refresh();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Farms')),
      floatingActionButton: FloatingActionButton(
        onPressed: _addFarm,
        tooltip: 'Add farm',
        child: const Icon(Icons.add),
      ),
      body: FutureBuilder<PaginatedFarms>(
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

          final data = snapshot.data!;
          if (data.items.isEmpty) {
            return const Center(child: Text('No farms yet'));
          }

          return RefreshIndicator(
            onRefresh: _refresh,
            child: ListView.separated(
              itemCount: data.items.length,
              separatorBuilder: (_, _) => const Divider(height: 1),
              itemBuilder: (context, index) {
                final farm = data.items[index];
                return ListTile(
                  leading: const Icon(Icons.grass),
                  title: Text(farm.name),
                  subtitle: Text('${farm.county} · ${farm.sizeAcres.toStringAsFixed(1)} acres'),
                  trailing: farm.isActive ? null : const Chip(label: Text('Inactive')),
                  onTap: () => Navigator.of(context).push(
                    MaterialPageRoute(builder: (_) => FarmDetailScreen(farm: farm)),
                  ),
                );
              },
            ),
          );
        },
      ),
    );
  }
}
