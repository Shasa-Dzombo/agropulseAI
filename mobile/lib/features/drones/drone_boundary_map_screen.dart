import 'dart:math' as math;

import 'package:flutter/material.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:latlong2/latlong.dart';

/// Real Earth-radius equirectangular projection, accurate enough for a
/// single field's footprint (a few hundred metres across) - the shoelace
/// formula needs flat coordinates, not raw lat/lng degrees.
double _polygonAreaHectares(List<LatLng> points) {
  if (points.length < 3) return 0;
  const earthRadiusM = 6371000.0;
  final avgLatRad = points.map((p) => p.latitude).reduce((a, b) => a + b) / points.length * math.pi / 180;
  final xy = points
      .map((p) => (
            x: p.longitude * math.pi / 180 * math.cos(avgLatRad) * earthRadiusM,
            y: p.latitude * math.pi / 180 * earthRadiusM,
          ))
      .toList();
  double sum = 0;
  for (var i = 0; i < xy.length; i++) {
    final a = xy[i];
    final b = xy[(i + 1) % xy.length];
    sum += a.x * b.y - b.x * a.y;
  }
  final areaM2 = sum.abs() / 2;
  return areaM2 / 10000;
}

/// Lets a farmer trace their field's outline directly on a satellite map by
/// tapping each corner - the result becomes a DroneFlight.boundaryPolygon
/// (a survey-area shape, not a flight path; see app/models/drone.py).
/// Pass initialPoints to review/adjust an existing boundary rather than
/// starting blank (e.g. one parsed from a KML file, or a previously-saved
/// flight's boundary being edited).
class DroneBoundaryMapScreen extends StatefulWidget {
  final LatLng initialCenter;
  final List<LatLng>? initialPoints;

  const DroneBoundaryMapScreen({
    super.key,
    required this.initialCenter,
    this.initialPoints,
  });

  @override
  State<DroneBoundaryMapScreen> createState() => _DroneBoundaryMapScreenState();
}

class _DroneBoundaryMapScreenState extends State<DroneBoundaryMapScreen> {
  late List<LatLng> _points;

  @override
  void initState() {
    super.initState();
    _points = List.of(widget.initialPoints ?? const []);
  }

  void _addPoint(LatLng point) => setState(() => _points.add(point));

  void _undo() {
    if (_points.isEmpty) return;
    setState(() => _points.removeLast());
  }

  void _clear() => setState(() => _points.clear());

  void _save() => Navigator.of(context).pop(_points);

  @override
  Widget build(BuildContext context) {
    final areaHa = _polygonAreaHectares(_points);
    return Scaffold(
      appBar: AppBar(
        title: const Text('Trace flight boundary'),
        actions: [
          IconButton(icon: const Icon(Icons.undo), onPressed: _points.isEmpty ? null : _undo, tooltip: 'Undo last point'),
          IconButton(icon: const Icon(Icons.delete_sweep_outlined), onPressed: _points.isEmpty ? null : _clear, tooltip: 'Clear all'),
        ],
      ),
      body: SafeArea(
        child: Column(
          children: [
            Container(
              width: double.infinity,
              color: Theme.of(context).colorScheme.surfaceContainerHighest,
              padding: const EdgeInsets.all(12),
              child: const Text(
                'Tap each corner of the field in order to trace its outline. Add at least 3 points.',
                textAlign: TextAlign.center,
                style: TextStyle(fontSize: 13),
              ),
            ),
            Expanded(
              child: FlutterMap(
                options: MapOptions(
                  initialCenter: widget.initialCenter,
                  initialZoom: 17,
                  minZoom: 3,
                  maxZoom: 20,
                  onTap: (_, point) => _addPoint(point),
                ),
                children: [
                  TileLayer(
                    urlTemplate: 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
                    userAgentPackageName: 'com.agropulse.agropulse_mobile',
                  ),
                  if (_points.length >= 3)
                    PolygonLayer(polygons: [
                      Polygon(
                        points: _points,
                        color: Colors.lightGreenAccent.withValues(alpha: 0.35),
                        borderColor: Colors.greenAccent.shade700,
                        borderStrokeWidth: 3,
                      ),
                    ]),
                  if (_points.length == 2)
                    PolylineLayer(polylines: [
                      Polyline(points: _points, color: Colors.greenAccent.shade700, strokeWidth: 3),
                    ]),
                  MarkerLayer(
                    markers: [
                      for (var i = 0; i < _points.length; i++)
                        Marker(
                          point: _points[i],
                          width: 28,
                          height: 28,
                          child: Container(
                            alignment: Alignment.center,
                            decoration: BoxDecoration(
                              color: Colors.white,
                              shape: BoxShape.circle,
                              border: Border.all(color: Colors.greenAccent.shade700, width: 2),
                            ),
                            child: Text('${i + 1}', style: const TextStyle(fontSize: 11, fontWeight: FontWeight.bold)),
                          ),
                        ),
                    ],
                  ),
                  RichAttributionWidget(
                    attributions: [TextSourceAttribution('Esri, Maxar, Earthstar Geographics')],
                  ),
                ],
              ),
            ),
            Padding(
              padding: const EdgeInsets.all(16),
              child: Row(
                children: [
                  Expanded(
                    child: Text(
                      _points.length < 3
                          ? '${_points.length} point${_points.length == 1 ? '' : 's'} - need at least 3'
                          : '${_points.length} points · ${areaHa.toStringAsFixed(2)} ha',
                      style: Theme.of(context).textTheme.bodyMedium,
                    ),
                  ),
                  const SizedBox(width: 12),
                  FilledButton(
                    onPressed: _points.length >= 3 ? _save : null,
                    child: const Text('Save boundary'),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}
