import 'package:flutter/material.dart';

import 'password_generator.dart';

/// Password field with a show/hide toggle, and - when [onGenerate] is set
/// (register screen only, not login) - a "generate a strong password"
/// action that fills the field and reveals it so the user can see what
/// they got before submitting.
class PasswordField extends StatefulWidget {
  final TextEditingController controller;
  final String labelText;
  final String? Function(String?)? validator;
  final bool showGenerateAction;
  final void Function(String)? onFieldSubmitted;

  const PasswordField({
    super.key,
    required this.controller,
    this.labelText = 'Password',
    this.validator,
    this.showGenerateAction = false,
    this.onFieldSubmitted,
  });

  @override
  State<PasswordField> createState() => _PasswordFieldState();
}

class _PasswordFieldState extends State<PasswordField> {
  bool _obscured = true;

  void _generate() {
    setState(() {
      widget.controller.text = generateStrongPassword();
      _obscured = false; // show it immediately - the whole point is to let them see/save it
    });
  }

  @override
  Widget build(BuildContext context) {
    return TextFormField(
      controller: widget.controller,
      obscureText: _obscured,
      decoration: InputDecoration(
        labelText: widget.labelText,
        border: const OutlineInputBorder(),
        suffixIcon: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            if (widget.showGenerateAction)
              IconButton(
                icon: const Icon(Icons.auto_fix_high),
                tooltip: 'Generate a strong password',
                onPressed: _generate,
              ),
            IconButton(
              icon: Icon(_obscured ? Icons.visibility : Icons.visibility_off),
              tooltip: _obscured ? 'Show password' : 'Hide password',
              onPressed: () => setState(() => _obscured = !_obscured),
            ),
          ],
        ),
      ),
      validator: widget.validator,
      onFieldSubmitted: widget.onFieldSubmitted,
    );
  }
}
