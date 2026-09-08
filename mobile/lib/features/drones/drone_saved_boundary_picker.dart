import 'package:flutter/material.dart';
import 'package:latlong2/latlong.dart';

import '../../core/api_exception.dart';
import 'drone_repository.dart';

/// Bottom sheet listing a farm's saved boundary templates (see
/// app.models.database.SavedFlightBoundary) - tap one to use it, or delete
/// unwanted ones. Shared between DroneFlightCreateScreen and
/// DroneFlightDetailScreen so the two don't duplicate this flow. Returns the
/// selected polygon (still just points - not saved to a flight by itself),
/// or null if the farmer cancelled without picking one.
Future<List<LatLng>?> pickSavedBoundary(BuildContext context, int farmId) {
  return showModalBottomSheet<List<LatLng>>(
    context: context,
    isScrollControlled: true,
    showDragHandle: true,
    builder: (context) => _SavedBoundaryPickerSheet(farmId: farmId),
  );
}

class _SavedBoundaryPickerSheet extends StatefulWidget {
  final int farmId;
  const _SavedBoundaryPickerSheet({required this.farmId});

  @override
  State<_SavedBoundaryPickerSheet> createState() => _SavedBoundaryPickerSheetState();
}

class _SavedBoundaryPickerSheetState extends State<_SavedBoundaryPickerSheet> {
  late Future<List<SavedBoundary>> _future;

  @override
  void initState() {
    super.initState();
    _future = DroneRepository.instance.listSavedBoundaries(widget.farmId);
  }

  Future<void> _delete(SavedBoundary boundary) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Delete this template?'),
        content: Text('This removes "${boundary.name}". Flights already using this shape keep it - only the reusable template goes.'),
        actions: [
          TextButton(onPressed: () => Navigator.of(context).pop(false), child: const Text('Cancel')),
          TextButton(
            onPressed: () => Navigator.of(context).pop(true),
            child: const Text('Delete', style: TextStyle(color: Colors.red)),
          ),
        ],
      ),
    );
    if (confirmed != true) return;
    try {
      await DroneRepository.instance.deleteSavedBoundary(boundary.id);
      if (mounted) setState(() => _future = DroneRepository.instance.listSavedBoundaries(widget.farmId));
    } on ApiException catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(e.message)));
    }
  }

  @override
  Widget build(BuildContext context) {
    return ConstrainedBox(
      constraints: BoxConstraints(maxHeight: MediaQuery.of(context).size.height * 0.7),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Padding(
            padding: EdgeInsets.fromLTRB(20, 0, 20, 12),
            child: Text('Saved boundary templates', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16)),
          ),
          Flexible(
            child: FutureBuilder<List<SavedBoundary>>(
              future: _future,
              builder: (context, snapshot) {
                if (snapshot.connectionState == ConnectionState.waiting) {
                  return const Padding(padding: EdgeInsets.all(24), child: Center(child: CircularProgressIndicator()));
                }
                if (snapshot.hasError) {
                  return Padding(
                    padding: const EdgeInsets.all(24),
                    child: Text(snapshot.error is ApiException ? (snapshot.error as ApiException).message : 'Could not load templates'),
                  );
                }
                final items = snapshot.data!;
                if (items.isEmpty) {
                  return const Padding(
                    padding: EdgeInsets.all(24),
                    child: Text('No saved templates yet - trace or import a boundary, then tap the bookmark icon to save it for reuse.'),
                  );
                }
                return ListView.builder(
                  shrinkWrap: true,
                  itemCount: items.length,
                  itemBuilder: (context, index) {
                    final boundary = items[index];
                    return ListTile(
                      leading: const Icon(Icons.crop_free),
                      title: Text(boundary.name),
                      subtitle: Text('${boundary.polygon.length} points'),
                      onTap: () => Navigator.of(context).pop(boundary.polygon),
                      trailing: IconButton(
                        icon: const Icon(Icons.delete_outline, size: 20),
                        onPressed: () => _delete(boundary),
                      ),
                    );
                  },
                );
              },
            ),
          ),
          const SizedBox(height: 12),
        ],
      ),
    );
  }
}
