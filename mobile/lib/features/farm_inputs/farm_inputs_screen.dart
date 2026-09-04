import 'package:flutter/material.dart';

import '../../core/api_exception.dart';
import 'farm_input_create_screen.dart';
import 'farm_input_models.dart';
import 'farm_input_repository.dart';
import 'farm_yield_create_screen.dart';

class FarmInputsScreen extends StatefulWidget {
  final int farmId;

  const FarmInputsScreen({super.key, required this.farmId});

  @override
  State<FarmInputsScreen> createState() => _FarmInputsScreenState();
}

class _FarmInputsScreenState extends State<FarmInputsScreen> with SingleTickerProviderStateMixin {
  late final TabController _tabController;
  late Future<FarmInputList> _inputsFuture;
  late Future<List<FarmYieldRecord>> _yieldsFuture;

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 2, vsync: this)..addListener(() => setState(() {}));
    _loadInputs();
    _loadYields();
  }

  @override
  void dispose() {
    _tabController.dispose();
    super.dispose();
  }

  void _loadInputs() => _inputsFuture = FarmInputRepository.instance.listInputRecords(widget.farmId);
  void _loadYields() => _yieldsFuture = FarmInputRepository.instance.listYieldRecords(widget.farmId);

  Future<void> _addInput() async {
    final created = await Navigator.of(context).push<FarmInputRecord>(
      MaterialPageRoute(builder: (_) => FarmInputCreateScreen(farmId: widget.farmId)),
    );
    if (created != null) setState(_loadInputs);
  }

  Future<void> _addYield() async {
    final created = await Navigator.of(context).push<FarmYieldRecord>(
      MaterialPageRoute(builder: (_) => FarmYieldCreateScreen(farmId: widget.farmId)),
    );
    if (created != null) setState(_loadYields);
  }

  Future<void> _deleteInput(FarmInputRecord record) async {
    try {
      await FarmInputRepository.instance.deleteInputRecord(widget.farmId, record.id);
      setState(_loadInputs);
    } on ApiException catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(e.message)));
    }
  }

  Future<void> _recordHarvest(FarmYieldRecord record) async {
    final actualController = TextEditingController();
    DateTime harvestDate = DateTime.now();
    final result = await showDialog<bool>(
      context: context,
      builder: (context) => StatefulBuilder(
        builder: (context, setDialogState) => AlertDialog(
          title: const Text('Record harvest'),
          content: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              TextField(
                controller: actualController,
                keyboardType: const TextInputType.numberWithOptions(decimal: true),
                decoration: const InputDecoration(labelText: 'Actual yield, kg'),
              ),
              const SizedBox(height: 12),
              ListTile(
                contentPadding: EdgeInsets.zero,
                title: const Text('Harvest date'),
                subtitle: Text('${harvestDate.year}-${harvestDate.month.toString().padLeft(2, '0')}-${harvestDate.day.toString().padLeft(2, '0')}'),
                trailing: const Icon(Icons.calendar_today),
                onTap: () async {
                  final picked = await showDatePicker(
                    context: context,
                    initialDate: harvestDate,
                    firstDate: DateTime(2020),
                    lastDate: DateTime.now().add(const Duration(days: 1)),
                  );
                  if (picked != null) setDialogState(() => harvestDate = picked);
                },
              ),
            ],
          ),
          actions: [
            TextButton(onPressed: () => Navigator.of(context).pop(false), child: const Text('Cancel')),
            FilledButton(onPressed: () => Navigator.of(context).pop(true), child: const Text('Save')),
          ],
        ),
      ),
    );

    if (result != true) return;
    final actual = double.tryParse(actualController.text.trim());
    if (actual == null) return;
    try {
      await FarmInputRepository.instance.recordHarvest(widget.farmId, record.id, actualYieldKg: actual, harvestDate: harvestDate);
      setState(_loadYields);
    } on ApiException catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(e.message)));
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Inputs & yield'),
        bottom: TabBar(controller: _tabController, tabs: const [Tab(text: 'Input log'), Tab(text: 'Yield')]),
      ),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: () => _tabController.index == 0 ? _addInput() : _addYield(),
        icon: const Icon(Icons.add),
        label: Text(_tabController.index == 0 ? 'Log input' : 'New season'),
      ),
      body: TabBarView(
        controller: _tabController,
        children: [_buildInputsTab(), _buildYieldsTab()],
      ),
    );
  }

  Widget _buildInputsTab() {
    return RefreshIndicator(
      onRefresh: () async {
        setState(_loadInputs);
        await _inputsFuture;
      },
      child: FutureBuilder<FarmInputList>(
        future: _inputsFuture,
        builder: (context, snapshot) {
          if (snapshot.connectionState == ConnectionState.waiting) {
            return const Center(child: CircularProgressIndicator());
          }
          if (snapshot.hasError) {
            return ListView(children: [
              Padding(
                padding: const EdgeInsets.all(24),
                child: Text(snapshot.error is ApiException ? (snapshot.error as ApiException).message : 'Could not load inputs'),
              ),
            ]);
          }
          final list = snapshot.data!;
          return ListView(
            padding: const EdgeInsets.all(16),
            children: [
              Card(
                child: Padding(
                  padding: const EdgeInsets.all(16),
                  child: Text('Total spent: KSh ${list.totalCostKsh.toStringAsFixed(0)}', style: Theme.of(context).textTheme.titleMedium),
                ),
              ),
              const SizedBox(height: 16),
              if (list.items.isEmpty) const Padding(padding: EdgeInsets.all(16), child: Text('No inputs logged yet')),
              for (final record in list.items)
                Dismissible(
                  key: ValueKey(record.id),
                  direction: DismissDirection.endToStart,
                  background: Container(
                    color: Colors.red,
                    alignment: Alignment.centerRight,
                    padding: const EdgeInsets.only(right: 20),
                    child: const Icon(Icons.delete, color: Colors.white),
                  ),
                  onDismissed: (_) => _deleteInput(record),
                  child: Card(
                    child: ListTile(
                      leading: Icon(record.entryType == 'purchase' ? Icons.shopping_cart : Icons.grass),
                      title: Text(record.itemName),
                      subtitle: Text([
                        record.entryType == 'purchase' ? 'Bought' : 'Applied',
                        if (record.quantity != null) '${record.quantity} ${record.unit ?? ''}'.trim(),
                        '${record.entryDate.year}-${record.entryDate.month.toString().padLeft(2, '0')}-${record.entryDate.day.toString().padLeft(2, '0')}',
                      ].join(' · ')),
                      trailing: record.costKsh != null ? Text('KSh ${record.costKsh!.toStringAsFixed(0)}') : null,
                    ),
                  ),
                ),
            ],
          );
        },
      ),
    );
  }

  Widget _buildYieldsTab() {
    return RefreshIndicator(
      onRefresh: () async {
        setState(_loadYields);
        await _yieldsFuture;
      },
      child: FutureBuilder<List<FarmYieldRecord>>(
        future: _yieldsFuture,
        builder: (context, snapshot) {
          if (snapshot.connectionState == ConnectionState.waiting) {
            return const Center(child: CircularProgressIndicator());
          }
          if (snapshot.hasError) {
            return ListView(children: [
              Padding(
                padding: const EdgeInsets.all(24),
                child: Text(snapshot.error is ApiException ? (snapshot.error as ApiException).message : 'Could not load yield records'),
              ),
            ]);
          }
          final records = snapshot.data!;
          if (records.isEmpty) {
            return ListView(children: const [Padding(padding: EdgeInsets.all(24), child: Text('No yield records yet'))]);
          }
          return ListView(
            padding: const EdgeInsets.all(16),
            children: [
              for (final record in records) _YieldCard(farmId: widget.farmId, record: record, onRecordHarvest: () => _recordHarvest(record)),
            ],
          );
        },
      ),
    );
  }
}

class _YieldCard extends StatefulWidget {
  final int farmId;
  final FarmYieldRecord record;
  final VoidCallback onRecordHarvest;

  const _YieldCard({required this.farmId, required this.record, required this.onRecordHarvest});

  @override
  State<_YieldCard> createState() => _YieldCardState();
}

class _YieldCardState extends State<_YieldCard> {
  late Future<List<String>> _tipsFuture;

  @override
  void initState() {
    super.initState();
    _tipsFuture = FarmInputRepository.instance.getYieldTips(widget.farmId, widget.record.id);
  }

  @override
  Widget build(BuildContext context) {
    final record = widget.record;
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('${record.crop} · ${record.seasonLabel}', style: Theme.of(context).textTheme.titleMedium),
            const SizedBox(height: 4),
            if (record.expectedYieldKg != null) Text('Expected: ${record.expectedYieldKg!.toStringAsFixed(0)} kg'),
            if (record.actualYieldKg != null)
              Text('Actual: ${record.actualYieldKg!.toStringAsFixed(0)} kg', style: const TextStyle(fontWeight: FontWeight.bold))
            else
              Padding(
                padding: const EdgeInsets.only(top: 8),
                child: OutlinedButton(onPressed: widget.onRecordHarvest, child: const Text('Record harvest')),
              ),
            if (record.estimatedYieldKg != null) ...[
              const SizedBox(height: 8),
              Text('Estimated: ${record.estimatedYieldKg!.toStringAsFixed(0)} kg', style: const TextStyle(color: Colors.black54, fontSize: 12)),
              Text(record.estimateSource!, style: const TextStyle(color: Colors.black38, fontSize: 11)),
            ],
            FutureBuilder<List<String>>(
              future: _tipsFuture,
              builder: (context, snapshot) {
                final tips = snapshot.data;
                if (tips == null || tips.isEmpty) return const SizedBox.shrink();
                return Padding(
                  padding: const EdgeInsets.only(top: 12),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text('Tips', style: Theme.of(context).textTheme.titleSmall),
                      const SizedBox(height: 4),
                      for (final tip in tips)
                        Padding(padding: const EdgeInsets.only(top: 4), child: Text('• $tip')),
                    ],
                  ),
                );
              },
            ),
          ],
        ),
      ),
    );
  }
}
