import 'package:flutter/material.dart';

import '../../features/auth/auth_models.dart';
import '../../features/auth/auth_repository.dart';
import '../../features/auth/login_screen.dart';
import '../../features/farms/farm_list_screen.dart';
import '../../features/diagnosis/diagnosis_upload_screen.dart';

/// Landing screen post-login. More farmer flows come next.
class HomeScreen extends StatelessWidget {
  final UserInfo user;

  const HomeScreen({super.key, required this.user});

  Future<void> _logout(BuildContext context) async {
    await AuthRepository.instance.logout();
    if (!context.mounted) return;
    Navigator.of(context).pushAndRemoveUntil(
      MaterialPageRoute(builder: (_) => const LoginScreen()),
      (route) => false,
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('AgroPulse'),
        actions: [IconButton(icon: const Icon(Icons.logout), onPressed: () => _logout(context))],
      ),
      body: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('Welcome, ${user.fullName}', style: Theme.of(context).textTheme.headlineSmall),
            const SizedBox(height: 8),
            Text('@${user.username} · ${user.role} · ${user.subscriptionTier} tier'),
            Text(user.county == null || user.county!.isEmpty ? 'No county set' : user.county!),
            const SizedBox(height: 24),
            FilledButton.icon(
              onPressed: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => const FarmListScreen())),
              icon: const Icon(Icons.grass),
              label: const Text('View farms'),
            ),
            const SizedBox(height: 12),
            FilledButton.icon(
              onPressed: () =>
                  Navigator.of(context).push(MaterialPageRoute(builder: (_) => const DiagnosisUploadScreen())),
              icon: const Icon(Icons.camera_alt),
              label: const Text('Diagnose a plant'),
            ),
          ],
        ),
      ),
    );
  }
}
