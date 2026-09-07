import 'package:flutter/material.dart';

import '../../core/api_config.dart';
import '../../core/token_storage.dart';

/// Loads one of a diagnosis's source photos from the ownership-checked
/// GET /diagnoses/{id}/images/{index} endpoint - same pattern as
/// features/drones/drone_image_view.dart's DroneImageView, since Diagnosis
/// only ever stores a backend-local file path, never a public URL.
class DiagnosisImageView extends StatelessWidget {
  final int diagnosisId;
  final int index;
  final double? height;
  final BoxFit fit;
  final BorderRadius? borderRadius;

  const DiagnosisImageView({
    super.key,
    required this.diagnosisId,
    this.index = 0,
    this.height,
    this.fit = BoxFit.cover,
    this.borderRadius,
  });

  @override
  Widget build(BuildContext context) {
    final url = '$apiBaseUrl/diagnoses/$diagnosisId/images/$index';

    return FutureBuilder<String?>(
      future: TokenStorage.instance.accessToken,
      builder: (context, snapshot) {
        Widget child;
        if (!snapshot.hasData) {
          child = const Center(child: CircularProgressIndicator());
        } else {
          child = Image.network(
            url,
            headers: {'Authorization': 'Bearer ${snapshot.data}'},
            fit: fit,
            errorBuilder: (context, error, stackTrace) =>
                const Center(child: Icon(Icons.broken_image_outlined, color: Colors.black26)),
            loadingBuilder: (context, child, progress) {
              if (progress == null) return child;
              return const Center(child: CircularProgressIndicator());
            },
          );
        }
        final sized = SizedBox(height: height, width: double.infinity, child: child);
        return borderRadius == null ? sized : ClipRRect(borderRadius: borderRadius!, child: sized);
      },
    );
  }
}
