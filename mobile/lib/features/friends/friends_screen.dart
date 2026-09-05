import 'package:flutter/material.dart';

import '../../core/api_exception.dart';
import 'friend_models.dart';
import 'friend_repository.dart';

/// Tabbed hub for the chama-discovery social layer: farmers in your own
/// county (see app/api/friends.py for why "nearby" means same-county, not
/// GPS), incoming friend requests, and accepted friends. Purpose is
/// deliberately narrow - help a farmer find a chama worth joining via
/// people they know or can see nearby - not a general social network.
class FriendsScreen extends StatefulWidget {
  const FriendsScreen({super.key});

  @override
  State<FriendsScreen> createState() => _FriendsScreenState();
}

class _FriendsScreenState extends State<FriendsScreen> with SingleTickerProviderStateMixin {
  late final TabController _tabController;
  late Future<List<NearbyFarmer>> _nearbyFuture;
  late Future<List<IncomingFriendRequest>> _requestsFuture;
  late Future<List<Friend>> _friendsFuture;

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 3, vsync: this);
    _loadNearby();
    _loadRequests();
    _loadFriends();
  }

  @override
  void dispose() {
    _tabController.dispose();
    super.dispose();
  }

  void _loadNearby() => _nearbyFuture = FriendRepository.instance.listNearbyFarmers();
  void _loadRequests() => _requestsFuture = FriendRepository.instance.listIncomingRequests();
  void _loadFriends() => _friendsFuture = FriendRepository.instance.listFriends();

  Future<void> _sendRequest(NearbyFarmer farmer) async {
    try {
      await FriendRepository.instance.sendFriendRequest(farmer.id);
      setState(_loadNearby);
    } on ApiException catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(e.message)));
    }
  }

  Future<void> _accept(IncomingFriendRequest request) async {
    try {
      await FriendRepository.instance.acceptFriendRequest(request.id);
      setState(() {
        _loadRequests();
        _loadFriends();
        _loadNearby();
      });
    } on ApiException catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(e.message)));
    }
  }

  Future<void> _reject(IncomingFriendRequest request) async {
    try {
      await FriendRepository.instance.rejectFriendRequest(request.id);
      setState(_loadRequests);
    } on ApiException catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(e.message)));
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Farmers near you'),
        bottom: TabBar(controller: _tabController, tabs: const [
          Tab(text: 'Nearby'),
          Tab(text: 'Requests'),
          Tab(text: 'Friends'),
        ]),
      ),
      body: TabBarView(controller: _tabController, children: [
        _buildNearbyTab(),
        _buildRequestsTab(),
        _buildFriendsTab(),
      ]),
    );
  }

  Widget _buildNearbyTab() {
    return RefreshIndicator(
      onRefresh: () async {
        setState(_loadNearby);
        await _nearbyFuture;
      },
      child: FutureBuilder<List<NearbyFarmer>>(
        future: _nearbyFuture,
        builder: (context, snapshot) {
          if (snapshot.connectionState == ConnectionState.waiting) {
            return const Center(child: CircularProgressIndicator());
          }
          if (snapshot.hasError) {
            return ListView(children: [
              Padding(
                padding: const EdgeInsets.all(24),
                child: Text(snapshot.error is ApiException ? (snapshot.error as ApiException).message : 'Could not load nearby farmers'),
              ),
            ]);
          }
          final farmers = snapshot.data!;
          if (farmers.isEmpty) {
            return ListView(children: const [
              Padding(
                padding: EdgeInsets.all(24),
                child: Text('No other farmers found in your county yet, or your county is not set.'),
              ),
            ]);
          }
          return ListView(
            padding: const EdgeInsets.all(16),
            children: [
              for (final farmer in farmers)
                Card(
                  child: Padding(
                    padding: const EdgeInsets.all(16),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Row(
                          children: [
                            Expanded(
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Text(farmer.name, style: Theme.of(context).textTheme.titleMedium),
                                  if (farmer.county != null) Text(farmer.county!),
                                ],
                              ),
                            ),
                            if (farmer.isFriend)
                              const Chip(label: Text('Friends'))
                            else if (farmer.requestPending)
                              const Chip(label: Text('Requested'))
                            else
                              OutlinedButton(onPressed: () => _sendRequest(farmer), child: const Text('Add friend')),
                          ],
                        ),
                        if (farmer.publicChamas.isNotEmpty) ...[
                          const SizedBox(height: 8),
                          Text('In: ${farmer.publicChamas.map((c) => c.name).join(', ')}', style: const TextStyle(color: Colors.black54)),
                        ],
                      ],
                    ),
                  ),
                ),
            ],
          );
        },
      ),
    );
  }

  Widget _buildRequestsTab() {
    return RefreshIndicator(
      onRefresh: () async {
        setState(_loadRequests);
        await _requestsFuture;
      },
      child: FutureBuilder<List<IncomingFriendRequest>>(
        future: _requestsFuture,
        builder: (context, snapshot) {
          if (snapshot.connectionState == ConnectionState.waiting) {
            return const Center(child: CircularProgressIndicator());
          }
          if (snapshot.hasError) {
            return ListView(children: [
              Padding(
                padding: const EdgeInsets.all(24),
                child: Text(snapshot.error is ApiException ? (snapshot.error as ApiException).message : 'Could not load requests'),
              ),
            ]);
          }
          final requests = snapshot.data!;
          if (requests.isEmpty) {
            return ListView(children: const [Padding(padding: EdgeInsets.all(24), child: Text('No pending requests'))]);
          }
          return ListView(
            padding: const EdgeInsets.all(16),
            children: [
              for (final request in requests)
                Card(
                  child: ListTile(
                    title: Text(request.requesterName),
                    subtitle: Text(request.requesterCounty ?? ''),
                    trailing: Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        IconButton(icon: const Icon(Icons.check, color: Colors.green), onPressed: () => _accept(request)),
                        IconButton(icon: const Icon(Icons.close, color: Colors.red), onPressed: () => _reject(request)),
                      ],
                    ),
                  ),
                ),
            ],
          );
        },
      ),
    );
  }

  Widget _buildFriendsTab() {
    return RefreshIndicator(
      onRefresh: () async {
        setState(_loadFriends);
        await _friendsFuture;
      },
      child: FutureBuilder<List<Friend>>(
        future: _friendsFuture,
        builder: (context, snapshot) {
          if (snapshot.connectionState == ConnectionState.waiting) {
            return const Center(child: CircularProgressIndicator());
          }
          if (snapshot.hasError) {
            return ListView(children: [
              Padding(
                padding: const EdgeInsets.all(24),
                child: Text(snapshot.error is ApiException ? (snapshot.error as ApiException).message : 'Could not load friends'),
              ),
            ]);
          }
          final friends = snapshot.data!;
          if (friends.isEmpty) {
            return ListView(children: const [Padding(padding: EdgeInsets.all(24), child: Text('No friends yet'))]);
          }
          return ListView(
            padding: const EdgeInsets.all(16),
            children: [
              for (final friend in friends)
                Card(child: ListTile(title: Text(friend.name), subtitle: Text(friend.county ?? ''))),
            ],
          );
        },
      ),
    );
  }
}
