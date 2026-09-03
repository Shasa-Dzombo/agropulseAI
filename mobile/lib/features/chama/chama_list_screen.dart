import 'package:flutter/material.dart';

import '../../core/api_exception.dart';
import 'chama_create_screen.dart';
import 'chama_detail_screen.dart';
import 'chama_models.dart';
import 'chama_repository.dart';

class ChamaListScreen extends StatefulWidget {
  const ChamaListScreen({super.key});

  @override
  State<ChamaListScreen> createState() => _ChamaListScreenState();
}

class _ChamaListScreenState extends State<ChamaListScreen> {
  bool _mineOnly = false;
  late Future<List<Chama>> _future;

  @override
  void initState() {
    super.initState();
    _future = ChamaRepository.instance.listChamas(mineOnly: _mineOnly);
  }

  Future<void> _refresh() async {
    setState(() => _future = ChamaRepository.instance.listChamas(mineOnly: _mineOnly));
    await _future;
  }

  void _setMineOnly(bool value) {
    if (value == _mineOnly) return;
    setState(() {
      _mineOnly = value;
      _future = ChamaRepository.instance.listChamas(mineOnly: _mineOnly);
    });
  }

  Future<void> _addChama() async {
    final created = await Navigator.of(context).push<Chama>(
      MaterialPageRoute(builder: (_) => const ChamaCreateScreen()),
    );
    if (created != null) _refresh();
  }

  Future<void> _openDetail(Chama chama) async {
    await Navigator.of(context).push(
      MaterialPageRoute(builder: (_) => ChamaDetailScreen(chama: chama)),
    );
    _refresh();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Chamas')),
      floatingActionButton: FloatingActionButton(
        onPressed: _addChama,
        tooltip: 'Start a chama',
        child: const Icon(Icons.add),
      ),
      body: SafeArea(
        child: Column(
          children: [
            Padding(
              padding: const EdgeInsets.fromLTRB(16, 12, 16, 4),
              child: SegmentedButton<bool>(
                segments: const [
                  ButtonSegment(value: false, label: Text('Discover'), icon: Icon(Icons.explore)),
                  ButtonSegment(value: true, label: Text('Mine'), icon: Icon(Icons.groups)),
                ],
                selected: {_mineOnly},
                onSelectionChanged: (s) => _setMineOnly(s.first),
              ),
            ),
            Expanded(child: _buildList()),
          ],
        ),
      ),
    );
  }

  Widget _buildList() {
    return FutureBuilder<List<Chama>>(
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

        final chamas = snapshot.data!;
        if (chamas.isEmpty) {
          return Center(child: Text(_mineOnly ? "You haven't joined a chama yet" : 'No chamas to discover yet'));
        }

        return RefreshIndicator(
          onRefresh: _refresh,
          child: ListView.separated(
            padding: const EdgeInsets.only(bottom: 80),
            itemCount: chamas.length,
            separatorBuilder: (_, _) => const Divider(height: 1),
            itemBuilder: (context, index) {
              final chama = chamas[index];
              return ListTile(
                leading: const Icon(Icons.groups),
                title: Text(chama.name),
                subtitle: Text('${chama.chamaType} · ${chama.memberCount} members · KSh ${chama.totalSavingsKsh.toStringAsFixed(0)} saved'),
                trailing: chama.isMember
                    ? const Chip(label: Text('Member'))
                    : chama.isPending
                        ? const Chip(label: Text('Pending'))
                        : null,
                onTap: () => _openDetail(chama),
              );
            },
          ),
        );
      },
    );
  }
}
