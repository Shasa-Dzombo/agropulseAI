import 'dart:math';

/// Generates a random password that's comfortably clear of the backend's
/// minimum (8 chars, see app/api/auth.py's RegisterRequest) and mixes
/// character classes. Uses Random.secure() (CSPRNG), not Random() - this
/// value is a real account credential, not test/UI data.
String generateStrongPassword({int length = 14}) {
  const upper = 'ABCDEFGHJKLMNPQRSTUVWXYZ'; // no I/O - easy to misread
  const lower = 'abcdefghijkmnopqrstuvwxyz'; // no l
  const digits = '23456789'; // no 0/1
  const symbols = '!@#\$%^&*-_+=';
  const all = upper + lower + digits + symbols;

  final random = Random.secure();
  final chars = <String>[
    upper[random.nextInt(upper.length)],
    lower[random.nextInt(lower.length)],
    digits[random.nextInt(digits.length)],
    symbols[random.nextInt(symbols.length)],
  ];
  for (var i = chars.length; i < length; i++) {
    chars.add(all[random.nextInt(all.length)]);
  }
  chars.shuffle(random);
  return chars.join();
}
