import 'package:flutter/material.dart';

import 'features/auth/auth_repository.dart';
import 'features/auth/login_screen.dart';
import 'features/home/home_screen.dart';

void main() {
  runApp(const AgroPulseApp());
}

class AgroPulseApp extends StatelessWidget {
  const AgroPulseApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'AgroPulse',
      theme: ThemeData(colorScheme: ColorScheme.fromSeed(seedColor: Colors.green), useMaterial3: true),
      home: const _SessionGate(),
    );
  }
}

/// Shows a stored-token session's home screen directly, or the login screen
/// otherwise. Just checks whether a token *exists* - an expired access token
/// still lands on HomeScreen, whose first authenticated call triggers the
/// ApiClient's refresh-on-401 flow.
class _SessionGate extends StatelessWidget {
  const _SessionGate();

  @override
  Widget build(BuildContext context) {
    return FutureBuilder(
      future: AuthRepository.instance.isLoggedIn,
      builder: (context, snapshot) {
        if (!snapshot.hasData) {
          return const Scaffold(body: Center(child: CircularProgressIndicator()));
        }
        if (snapshot.data == true) {
          return FutureBuilder(
            future: AuthRepository.instance.me(),
            builder: (context, meSnapshot) {
              if (meSnapshot.hasError) return const LoginScreen();
              if (!meSnapshot.hasData) {
                return const Scaffold(body: Center(child: CircularProgressIndicator()));
              }
              return HomeScreen(user: meSnapshot.data!);
            },
          );
        }
        return const LoginScreen();
      },
    );
  }
}
