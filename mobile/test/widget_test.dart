// Smoke test for LoginScreen - the old counter-app test no longer applies
// since main.dart was replaced. LoginScreen itself makes no network calls on
// build, so this doesn't need a mocked backend.

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:agropulse_mobile/features/auth/login_screen.dart';

void main() {
  testWidgets('LoginScreen shows identifier and password fields', (WidgetTester tester) async {
    await tester.pumpWidget(const MaterialApp(home: LoginScreen()));

    expect(find.text('Username or email'), findsOneWidget);
    expect(find.text('Password'), findsOneWidget);
    expect(find.text('Log in'), findsOneWidget);
  });

  testWidgets('Submitting an empty form shows validation errors', (WidgetTester tester) async {
    await tester.pumpWidget(const MaterialApp(home: LoginScreen()));

    await tester.tap(find.text('Log in'));
    await tester.pump();

    expect(find.text('Required'), findsWidgets);
  });
}
