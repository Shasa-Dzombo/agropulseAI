import 'package:flutter/material.dart';

import '../../core/api_exception.dart';
import '../../core/kenya_counties.dart';
import '../../core/password_field.dart';
import '../home/home_screen.dart';
import 'auth_repository.dart';

class RegisterScreen extends StatefulWidget {
  const RegisterScreen({super.key});

  @override
  State<RegisterScreen> createState() => _RegisterScreenState();
}

class _RegisterScreenState extends State<RegisterScreen> {
  final _formKey = GlobalKey<FormState>();
  final _usernameController = TextEditingController();
  final _emailController = TextEditingController();
  final _phoneController = TextEditingController();
  final _fullNameController = TextEditingController();
  final _passwordController = TextEditingController();
  String? _selectedCounty;
  bool _loading = false;

  @override
  void dispose() {
    _usernameController.dispose();
    _emailController.dispose();
    _phoneController.dispose();
    _fullNameController.dispose();
    _passwordController.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    if (!_formKey.currentState!.validate()) return;
    setState(() => _loading = true);
    try {
      final user = await AuthRepository.instance.register(
        username: _usernameController.text.trim(),
        email: _emailController.text.trim(),
        phoneNumber: _phoneController.text.trim(),
        password: _passwordController.text,
        fullName: _fullNameController.text.trim(),
        county: _selectedCounty,
      );
      if (!mounted) return;
      Navigator.of(context).pushAndRemoveUntil(
        MaterialPageRoute(builder: (_) => HomeScreen(user: user)),
        (route) => false,
      );
    } on ApiException catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(e.message)));
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Create account')),
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(24),
          child: Form(
            key: _formKey,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                TextFormField(
                  controller: _fullNameController,
                  decoration: const InputDecoration(labelText: 'Full name', border: OutlineInputBorder()),
                  validator: (v) => (v == null || v.trim().length < 2) ? 'Enter your full name' : null,
                ),
                const SizedBox(height: 16),
                TextFormField(
                  controller: _usernameController,
                  decoration: const InputDecoration(labelText: 'Username', border: OutlineInputBorder()),
                  validator: (v) {
                    if (v == null || v.length < 3) return 'At least 3 characters';
                    if (!RegExp(r'^[a-zA-Z0-9_-]+$').hasMatch(v)) return 'Letters, numbers, - and _ only';
                    return null;
                  },
                ),
                const SizedBox(height: 16),
                TextFormField(
                  controller: _emailController,
                  keyboardType: TextInputType.emailAddress,
                  decoration: const InputDecoration(labelText: 'Email', border: OutlineInputBorder()),
                  validator: (v) => (v == null || !v.contains('@')) ? 'Enter a valid email' : null,
                ),
                const SizedBox(height: 16),
                TextFormField(
                  controller: _phoneController,
                  keyboardType: TextInputType.phone,
                  decoration: const InputDecoration(
                    labelText: 'Phone number',
                    hintText: '+254712345678',
                    border: OutlineInputBorder(),
                  ),
                  validator: (v) {
                    if (v == null || !RegExp(r'^\+?[0-9]{10,15}$').hasMatch(v)) {
                      return 'Enter a valid phone number (10-15 digits)';
                    }
                    return null;
                  },
                ),
                const SizedBox(height: 16),
                DropdownButtonFormField<String>(
                  initialValue: _selectedCounty,
                  decoration: const InputDecoration(labelText: 'County (optional)', border: OutlineInputBorder()),
                  isExpanded: true,
                  items: kenyaCounties
                      .map((county) => DropdownMenuItem(value: county, child: Text(county)))
                      .toList(),
                  onChanged: (value) => setState(() => _selectedCounty = value),
                ),
                const SizedBox(height: 16),
                PasswordField(
                  controller: _passwordController,
                  showGenerateAction: true,
                  validator: (v) => (v == null || v.length < 8) ? 'At least 8 characters' : null,
                ),
                const SizedBox(height: 24),
                FilledButton(
                  onPressed: _loading ? null : _submit,
                  child: _loading
                      ? const SizedBox(height: 20, width: 20, child: CircularProgressIndicator(strokeWidth: 2))
                      : const Text('Register'),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
