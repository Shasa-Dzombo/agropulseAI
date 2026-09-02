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
  final _scrollController = ScrollController();
  final List<Farm> _farms = [];

  bool _loading = true;
  bool _loadingMore = false;
  String? _error;
  int _page = 1;
  int _pages = 1;

  @override
  void initState() {
    super.initState();
    _scrollController.addListener(_onScroll);
    _loadFirstPage();
  }

  @override
  void dispose() {
    _scrollController.removeListener(_onScroll);
    _scrollController.dispose();
    super.dispose();
  }

  void _onScroll() {
    if (_loading || _loadingMore || _page >= _pages) return;
    if (_scrollController.position.pixels >= _scrollController.position.maxScrollExtent - 300) {
      _loadNextPage();
    }
  }

  Future<void> _loadFirstPage() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final result = await FarmRepository.instance.listFarms();
      if (!mounted) return;
      setState(() {
        _farms
          ..clear()
          ..addAll(result.items);
        _page = result.page;
        _pages = result.pages;
        _loading = false;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _error = e is ApiException ? e.message : 'Something went wrong';
        _loading = false;
      });
    }
  }

  Future<void> _loadNextPage() async {
    setState(() => _loadingMore = true);
    try {
      final result = await FarmRepository.instance.listFarms(page: _page + 1);
      if (!mounted) return;
      setState(() {
        _farms.addAll(result.items);
        _page = result.page;
        _pages = result.pages;
        _loadingMore = false;
      });
    } catch (_) {
      // Leave the list as-is - scrolling back up to trigger _onScroll again
      // will retry, and the user hasn't lost what's already loaded.
      if (!mounted) return;
      setState(() => _loadingMore = false);
    }
  }

  Future<void> _addFarm() async {
    final created = await Navigator.of(context).push<Farm>(
      MaterialPageRoute(builder: (_) => const FarmCreateScreen()),
    );
    // Insert locally instead of reloading - the backend lists farms
    // oldest-first, so a reload would bury a brand-new farm at the very
    // end of a potentially large list instead of showing it right away.
    if (created != null) {
      setState(() => _farms.insert(0, created));
    }
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
      body: _buildBody(),
    );
  }

  Widget _buildBody() {
    if (_loading) {
      return const Center(child: CircularProgressIndicator());
    }
    if (_error != null) {
      return Center(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Text(_error!, textAlign: TextAlign.center),
              const SizedBox(height: 12),
              FilledButton(onPressed: _loadFirstPage, child: const Text('Retry')),
            ],
          ),
        ),
      );
    }
    if (_farms.isEmpty) {
      return const Center(child: Text('No farms yet'));
    }

    return RefreshIndicator(
      onRefresh: _loadFirstPage,
      child: ListView.separated(
        controller: _scrollController,
        itemCount: _farms.length + 1,
        separatorBuilder: (_, _) => const Divider(height: 1),
        itemBuilder: (context, index) {
          if (index == _farms.length) {
            if (!_loadingMore) return const SizedBox.shrink();
            return const Padding(
              padding: EdgeInsets.symmetric(vertical: 24),
              child: Center(child: CircularProgressIndicator()),
            );
          }

          final farm = _farms[index];
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
  }
}
