import 'package:flutter/material.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:latlong2/latlong.dart';

/// Satellite view of a farm's location - Esri World Imagery tiles, free and
/// keyless (unlike Google/Mapbox satellite layers, which both need a billed
/// API key). Resolution is noticeably coarser than paid providers when
/// zoomed in tight on a small plot, but it's a real aerial photo, not a
/// rendered map, and costs nothing to embed.
class FarmSatelliteMap extends StatelessWidget {
  final double latitude;
  final double longitude;
  final String farmName;

  const FarmSatelliteMap({
    super.key,
    required this.latitude,
    required this.longitude,
    required this.farmName,
  });

  @override
  Widget build(BuildContext context) {
    final center = LatLng(latitude, longitude);
    return ClipRRect(
      borderRadius: BorderRadius.circular(4),
      child: SizedBox(
        height: 220,
        child: FlutterMap(
          options: MapOptions(
            initialCenter: center,
            initialZoom: 16,
            minZoom: 3,
            maxZoom: 18,
            interactionOptions: const InteractionOptions(
              flags: InteractiveFlag.pinchZoom | InteractiveFlag.drag | InteractiveFlag.doubleTapZoom,
            ),
          ),
          children: [
            TileLayer(
              urlTemplate: 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
              userAgentPackageName: 'com.agropulse.agropulse_mobile',
            ),
            MarkerLayer(
              markers: [
                Marker(
                  point: center,
                  width: 40,
                  height: 40,
                  child: const Icon(Icons.location_pin, color: Colors.redAccent, size: 40),
                ),
              ],
            ),
            RichAttributionWidget(
              attributions: [
                TextSourceAttribution('Esri, Maxar, Earthstar Geographics'),
              ],
            ),
          ],
        ),
      ),
    );
  }
}
