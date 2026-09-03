import 'package:flutter/material.dart';

import '../../core/api_exception.dart';
import 'chama_models.dart';
import 'chama_repository.dart';

class ChamaDetailScreen extends StatefulWidget {
  final Chama chama;

  const ChamaDetailScreen({super.key, required this.chama});

  @override
  State<ChamaDetailScreen> createState() => _ChamaDetailScreenState();
}

class _ChamaDetailScreenState extends State<ChamaDetailScreen> {
  late Chama _chama;
  late Future<List<ChamaMember>> _membersFuture;
  late Future<List<Contribution>> _contributionsFuture;
  late Future<List<ChamaMember>> _joinRequestsFuture;
  bool _joining = false;

  @override
  void initState() {
    super.initState();
    _chama = widget.chama;
    _loadLists();
  }

  void _loadLists() {
    _membersFuture = _chama.isMember
        ? ChamaRepository.instance.listMembers(_chama.id)
        : Future.value(<ChamaMember>[]);
    _contributionsFuture = _chama.isMember
        ? ChamaRepository.instance.listContributions(_chama.id)
        : Future.value(<Contribution>[]);
    _joinRequestsFuture = _chama.isLeader
        ? ChamaRepository.instance.listJoinRequests(_chama.id)
        : Future.value(<ChamaMember>[]);
  }

  Future<void> _join() async {
    setState(() => _joining = true);
    try {
      final updated = await ChamaRepository.instance.joinChama(_chama.id);
      if (!mounted) return;
      setState(() {
        _chama = updated;
        _loadLists();
      });
    } on ApiException catch (e) {
      _showError(e.message);
    } finally {
      if (mounted) setState(() => _joining = false);
    }
  }

  Future<void> _approveRequest(int userId) async {
    try {
      await ChamaRepository.instance.approveJoinRequest(_chama.id, userId);
      await _refresh();
    } on ApiException catch (e) {
      if (mounted) _showError(e.message);
    }
  }

  Future<void> _rejectRequest(int userId) async {
    try {
      await ChamaRepository.instance.rejectJoinRequest(_chama.id, userId);
      await _refresh();
    } on ApiException catch (e) {
      if (mounted) _showError(e.message);
    }
  }

  Future<void> _refresh() async {
    final updated = await ChamaRepository.instance.getChama(_chama.id);
    if (!mounted) return;
    setState(() {
      _chama = updated;
      _loadLists();
    });
    await Future.wait([_membersFuture, _contributionsFuture, _joinRequestsFuture]);
  }

  Future<void> _openContributeSheet() async {
    final amountController = TextEditingController();
    final notesController = TextEditingController();
    String? paymentMethod;
    final formKey = GlobalKey<FormState>();

    final result = await showModalBottomSheet<bool>(
      context: context,
      isScrollControlled: true,
      builder: (sheetContext) {
        return Padding(
          padding: EdgeInsets.only(
            left: 24, right: 24, top: 24,
            bottom: MediaQuery.of(sheetContext).viewInsets.bottom + 24,
          ),
          child: StatefulBuilder(
            builder: (sheetContext, setSheetState) => Form(
              key: formKey,
              child: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  Text('Record a contribution', style: Theme.of(sheetContext).textTheme.titleLarge),
                  const SizedBox(height: 16),
                  TextFormField(
                    controller: amountController,
                    autofocus: true,
                    keyboardType: const TextInputType.numberWithOptions(decimal: true),
                    decoration: const InputDecoration(labelText: 'Amount, KSh', border: OutlineInputBorder()),
                    validator: (v) {
                      final n = double.tryParse(v ?? '');
                      if (n == null || n <= 0) return 'Enter a valid amount';
                      return null;
                    },
                  ),
                  const SizedBox(height: 16),
                  DropdownButtonFormField<String>(
                    initialValue: paymentMethod,
                    decoration: const InputDecoration(labelText: 'Payment method (optional)', border: OutlineInputBorder()),
                    items: const [
                      DropdownMenuItem(value: 'mpesa', child: Text('M-Pesa')),
                      DropdownMenuItem(value: 'bank', child: Text('Bank')),
                      DropdownMenuItem(value: 'cash', child: Text('Cash')),
                      DropdownMenuItem(value: 'card', child: Text('Card')),
                    ],
                    onChanged: (v) => setSheetState(() => paymentMethod = v),
                  ),
                  const SizedBox(height: 16),
                  TextFormField(
                    controller: notesController,
                    decoration: const InputDecoration(labelText: 'Notes (optional)', border: OutlineInputBorder()),
                  ),
                  const SizedBox(height: 24),
                  FilledButton(
                    onPressed: () {
                      if (formKey.currentState!.validate()) {
                        Navigator.of(sheetContext).pop(true);
                      }
                    },
                    child: const Text('Record contribution'),
                  ),
                  const SizedBox(height: 8),
                ],
              ),
            ),
          ),
        );
      },
    );

    if (result != true || !mounted) return;

    try {
      await ChamaRepository.instance.recordContribution(
        _chama.id,
        amountKsh: double.parse(amountController.text.trim()),
        paymentMethod: paymentMethod,
        notes: notesController.text.trim().isEmpty ? null : notesController.text.trim(),
      );
      await _refresh();
    } on ApiException catch (e) {
      if (mounted) _showError(e.message);
    }
  }

  void _showError(String message) {
    ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(message)));
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text(_chama.name)),
      floatingActionButton: _chama.isMember
          ? FloatingActionButton.extended(
              onPressed: _openContributeSheet,
              icon: const Icon(Icons.savings),
              label: const Text('Contribute'),
            )
          : null,
      body: SafeArea(
        child: RefreshIndicator(
          onRefresh: _refresh,
          child: ListView(
            padding: const EdgeInsets.all(16),
            children: [
              _buildInfoCard(),
              const SizedBox(height: 16),
              if (_chama.isPending) ...[
                const Card(
                  child: ListTile(
                    leading: Icon(Icons.hourglass_top),
                    title: Text('Request pending'),
                    subtitle: Text("A chama leader needs to approve you before you're a member"),
                  ),
                ),
                const SizedBox(height: 16),
              ] else if (!_chama.isMember) ...[
                FilledButton(
                  onPressed: _joining ? null : _join,
                  child: _joining
                      ? const SizedBox(height: 20, width: 20, child: CircularProgressIndicator(strokeWidth: 2))
                      : const Text('Request to join'),
                ),
                const SizedBox(height: 16),
              ],
              if (_chama.isLeader) ...[
                Text('Join requests', style: Theme.of(context).textTheme.titleMedium),
                const SizedBox(height: 8),
                _buildJoinRequestsList(),
                const SizedBox(height: 24),
              ],
              if (_chama.isMember) ...[
                Text('Members', style: Theme.of(context).textTheme.titleMedium),
                const SizedBox(height: 8),
                _buildMembersList(),
                const SizedBox(height: 24),
                Text('Contributions', style: Theme.of(context).textTheme.titleMedium),
                const SizedBox(height: 8),
                _buildContributionsList(),
                const SizedBox(height: 80),
              ],
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildInfoCard() {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Expanded(child: Text(_chama.name, style: Theme.of(context).textTheme.titleLarge)),
                if (_chama.isMember) const Chip(label: Text('Member')),
              ],
            ),
            if (_chama.description != null && _chama.description!.isNotEmpty) ...[
              const SizedBox(height: 4),
              Text(_chama.description!),
            ],
            const SizedBox(height: 12),
            Wrap(
              spacing: 16,
              runSpacing: 8,
              children: [
                _stat(Icons.category, _chama.chamaType),
                _stat(Icons.groups, '${_chama.memberCount} members'),
                _stat(Icons.savings, 'KSh ${_chama.totalSavingsKsh.toStringAsFixed(0)} saved'),
                if (_chama.monthlyContributionKsh != null)
                  _stat(Icons.calendar_month, 'KSh ${_chama.monthlyContributionKsh!.toStringAsFixed(0)}/month'),
              ],
            ),
            if (_chama.isMember && _chama.mpesaPaybillNumber != null) ...[
              const SizedBox(height: 12),
              Container(
                padding: const EdgeInsets.all(10),
                decoration: BoxDecoration(
                  color: Theme.of(context).colorScheme.secondaryContainer,
                  borderRadius: BorderRadius.circular(6),
                ),
                child: Row(
                  children: [
                    const Icon(Icons.point_of_sale, size: 18),
                    const SizedBox(width: 8),
                    Expanded(child: Text('Pay via M-Pesa Paybill ${_chama.mpesaPaybillNumber}')),
                  ],
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }

  Widget _stat(IconData icon, String label) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Icon(icon, size: 18),
        const SizedBox(width: 4),
        Text(label),
      ],
    );
  }

  Widget _buildJoinRequestsList() {
    return FutureBuilder<List<ChamaMember>>(
      future: _joinRequestsFuture,
      builder: (context, snapshot) {
        if (snapshot.connectionState == ConnectionState.waiting) {
          return const Padding(padding: EdgeInsets.all(16), child: Center(child: CircularProgressIndicator()));
        }
        if (snapshot.hasError) {
          return Text(snapshot.error is ApiException ? (snapshot.error as ApiException).message : 'Could not load join requests');
        }
        final requests = snapshot.data!;
        if (requests.isEmpty) return const Text('No pending requests');
        return Card(
          child: Column(
            children: requests
                .map((r) => ListTile(
                      leading: const Icon(Icons.person_add),
                      title: Text(r.fullName ?? r.username ?? 'User #${r.userId}'),
                      trailing: Row(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          IconButton(
                            icon: const Icon(Icons.check_circle, color: Colors.green),
                            tooltip: 'Approve',
                            onPressed: () => _approveRequest(r.userId),
                          ),
                          IconButton(
                            icon: const Icon(Icons.cancel, color: Colors.red),
                            tooltip: 'Reject',
                            onPressed: () => _rejectRequest(r.userId),
                          ),
                        ],
                      ),
                    ))
                .toList(),
          ),
        );
      },
    );
  }

  Widget _buildMembersList() {
    return FutureBuilder<List<ChamaMember>>(
      future: _membersFuture,
      builder: (context, snapshot) {
        if (snapshot.connectionState == ConnectionState.waiting) {
          return const Padding(padding: EdgeInsets.all(16), child: Center(child: CircularProgressIndicator()));
        }
        if (snapshot.hasError) {
          return Text(snapshot.error is ApiException ? (snapshot.error as ApiException).message : 'Could not load members');
        }
        final members = snapshot.data!;
        if (members.isEmpty) return const Text('No members yet');
        return Card(
          child: Column(
            children: members
                .map((m) => ListTile(
                      leading: const Icon(Icons.person),
                      title: Text(m.fullName ?? m.username ?? 'Member #${m.userId}'),
                      trailing: Text(m.role),
                    ))
                .toList(),
          ),
        );
      },
    );
  }

  Widget _buildContributionsList() {
    return FutureBuilder<List<Contribution>>(
      future: _contributionsFuture,
      builder: (context, snapshot) {
        if (snapshot.connectionState == ConnectionState.waiting) {
          return const Padding(padding: EdgeInsets.all(16), child: Center(child: CircularProgressIndicator()));
        }
        if (snapshot.hasError) {
          return Text(snapshot.error is ApiException ? (snapshot.error as ApiException).message : 'Could not load contributions');
        }
        final contributions = snapshot.data!;
        if (contributions.isEmpty) return const Text('No contributions yet');
        return Card(
          child: Column(
            children: contributions
                .map((c) => ListTile(
                      leading: const Icon(Icons.arrow_downward, color: Colors.green),
                      title: Text('KSh ${c.amountKsh.toStringAsFixed(0)}'),
                      subtitle: Text([
                        if (c.paymentMethod != null) c.paymentMethod!,
                        if (c.notes != null && c.notes!.isNotEmpty) c.notes!,
                      ].join(' · ')),
                      trailing: c.initiatedAt == null
                          ? null
                          : Text('${c.initiatedAt!.month}/${c.initiatedAt!.day}'),
                    ))
                .toList(),
          ),
        );
      },
    );
  }
}
