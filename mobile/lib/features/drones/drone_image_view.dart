import 'package:flutter/material.dart';

import '../../core/api_config.dart';
import '../../core/token_storage.dart';

/// Loads a captured drone photo (or its annotated overlay) from the
/// ownership-checked GET /drones/flights/{flightId}/images/{id}/rgb|overlay
/// endpoints - the DB only ever stores a backend-local file:// path
/// (app/services/local_image_storage.py), so this is the only way to
/// actually display one. Needs the bearer token as a request header, which
/// Image.network supports directly - no extra image-loading package needed.
class DroneImageView extends StatelessWidget {
  final int flightId;
  final int imageId;
  final bool overlay;
  final double? height;
  final BoxFit fit;
  final BorderRadius? borderRadius;

  const DroneImageView({
    super.key,
    required this.flightId,
    required this.imageId,
    this.overlay = false,
    this.height,
    this.fit = BoxFit.cover,
    this.borderRadius,
  });

  @override
  Widget build(BuildContext context) {
    final path = overlay ? 'overlay' : 'rgb';
    final url = '$apiBaseUrl/drones/flights/$flightId/images/$imageId/$path';

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
