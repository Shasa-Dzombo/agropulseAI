# ======================================================================================================================
# AgroPulse NVR - Geospatial Services
# GPS tracking, geofencing, spatial queries, map integration, distance calculations
# ======================================================================================================================

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
import math

logger = logging.getLogger(__name__)

# ======================================================================================================================
# GEOSPATIAL MODELS
# ======================================================================================================================

class CoordinateSystem(Enum):
    """Coordinate systems"""
    WGS84 = "wgs84"  # GPS standard
    WEB_MERCATOR = "web_mercator"
    UTM = "utm"

class GeofenceType(Enum):
    """Geofence types"""
    CIRCLE = "circle"
    POLYGON = "polygon"
    RECTANGLE = "rectangle"

class GeofenceEvent(Enum):
    """Geofence events"""
    ENTER = "enter"
    EXIT = "exit"
    DWELL = "dwell"

@dataclass
class Coordinates:
    """Geographic coordinates"""
    latitude: float
    longitude: float
    altitude: Optional[float] = None
    accuracy: Optional[float] = None
    timestamp: datetime = field(default_factory=datetime.now)

@dataclass
class BoundingBox:
    """Bounding box"""
    min_lat: float
    max_lat: float
    min_lon: float
    max_lon: float

@dataclass
class Geofence:
    """Geofence definition"""
    geofence_id: str
    name: str
    geofence_type: GeofenceType
    center: Optional[Coordinates] = None
    radius_meters: Optional[float] = None
    polygon_points: Optional[List[Coordinates]] = None
    bounds: Optional[BoundingBox] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)

@dataclass
class LocationUpdate:
    """Location update"""
    entity_id: str
    entity_type: str  # device, user, vehicle
    coordinates: Coordinates
    speed_mps: Optional[float] = None
    heading: Optional[float] = None
    timestamp: datetime = field(default_factory=datetime.now)

@dataclass
class GeofenceAlert:
    """Geofence alert"""
    alert_id: str
    geofence_id: str
    entity_id: str
    event_type: GeofenceEvent
    coordinates: Coordinates
    timestamp: datetime = field(default_factory=datetime.now)

# ======================================================================================================================
# DISTANCE CALCULATOR
# ======================================================================================================================

class DistanceCalculator:
    """Calculate distances and bearings"""
    
    EARTH_RADIUS_KM = 6371.0
    
    def __init__(self):
        logger.info("[DISTANCE] Distance calculator initialized")
    
    def haversine_distance(self, coord1: Coordinates,
                          coord2: Coordinates) -> float:
        """Calculate distance using Haversine formula (meters)"""
        lat1, lon1 = math.radians(coord1.latitude), math.radians(coord1.longitude)
        lat2, lon2 = math.radians(coord2.latitude), math.radians(coord2.longitude)
        
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        
        a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
        c = 2 * math.asin(math.sqrt(a))
        
        distance_km = self.EARTH_RADIUS_KM * c
        return distance_km * 1000  # Convert to meters
    
    def calculate_bearing(self, coord1: Coordinates,
                         coord2: Coordinates) -> float:
        """Calculate bearing between two points (degrees)"""
        lat1, lon1 = math.radians(coord1.latitude), math.radians(coord1.longitude)
        lat2, lon2 = math.radians(coord2.latitude), math.radians(coord2.longitude)
        
        dlon = lon2 - lon1
        
        x = math.sin(dlon) * math.cos(lat2)
        y = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(dlon)
        
        bearing = math.atan2(x, y)
        bearing_degrees = math.degrees(bearing)
        
        return (bearing_degrees + 360) % 360
    
    def destination_point(self, start: Coordinates, bearing: float,
                         distance_meters: float) -> Coordinates:
        """Calculate destination point given start, bearing, and distance"""
        lat1 = math.radians(start.latitude)
        lon1 = math.radians(start.longitude)
        bearing_rad = math.radians(bearing)
        
        distance_km = distance_meters / 1000
        angular_distance = distance_km / self.EARTH_RADIUS_KM
        
        lat2 = math.asin(
            math.sin(lat1) * math.cos(angular_distance) +
            math.cos(lat1) * math.sin(angular_distance) * math.cos(bearing_rad)
        )
        
        lon2 = lon1 + math.atan2(
            math.sin(bearing_rad) * math.sin(angular_distance) * math.cos(lat1),
            math.cos(angular_distance) - math.sin(lat1) * math.sin(lat2)
        )
        
        return Coordinates(
            latitude=math.degrees(lat2),
            longitude=math.degrees(lon2)
        )

# ======================================================================================================================
# GEOFENCE MANAGER
# ======================================================================================================================

class GeofenceManager:
    """Manage geofences"""
    
    def __init__(self, distance_calculator: DistanceCalculator):
        self.distance_calculator = distance_calculator
        self.geofences: Dict[str, Geofence] = {}
        
        logger.info("[GEOFENCE-MGR] Geofence manager initialized")
    
    def create_circle_geofence(self, geofence_id: str, name: str,
                              center: Coordinates,
                              radius_meters: float) -> Geofence:
        """Create circular geofence"""
        geofence = Geofence(
            geofence_id=geofence_id,
            name=name,
            geofence_type=GeofenceType.CIRCLE,
            center=center,
            radius_meters=radius_meters
        )
        
        self.geofences[geofence_id] = geofence
        
        logger.info(f"[GEOFENCE-MGR] Created circle geofence: {geofence_id} (radius: {radius_meters}m)")
        return geofence
    
    def create_polygon_geofence(self, geofence_id: str, name: str,
                               points: List[Coordinates]) -> Geofence:
        """Create polygon geofence"""
        if len(points) < 3:
            raise ValueError("Polygon must have at least 3 points")
        
        # Calculate bounding box
        lats = [p.latitude for p in points]
        lons = [p.longitude for p in points]
        
        bounds = BoundingBox(
            min_lat=min(lats),
            max_lat=max(lats),
            min_lon=min(lons),
            max_lon=max(lons)
        )
        
        geofence = Geofence(
            geofence_id=geofence_id,
            name=name,
            geofence_type=GeofenceType.POLYGON,
            polygon_points=points,
            bounds=bounds
        )
        
        self.geofences[geofence_id] = geofence
        
        logger.info(f"[GEOFENCE-MGR] Created polygon geofence: {geofence_id} ({len(points)} points)")
        return geofence
    
    def check_geofence(self, geofence_id: str,
                      coordinates: Coordinates) -> bool:
        """Check if coordinates are inside geofence"""
        geofence = self.geofences.get(geofence_id)
        
        if not geofence:
            return False
        
        if geofence.geofence_type == GeofenceType.CIRCLE:
            return self._check_circle(geofence, coordinates)
        elif geofence.geofence_type == GeofenceType.POLYGON:
            return self._check_polygon(geofence, coordinates)
        
        return False
    
    def _check_circle(self, geofence: Geofence, coord: Coordinates) -> bool:
        """Check if point is inside circle"""
        distance = self.distance_calculator.haversine_distance(
            geofence.center,
            coord
        )
        
        return distance <= geofence.radius_meters
    
    def _check_polygon(self, geofence: Geofence, coord: Coordinates) -> bool:
        """Check if point is inside polygon using ray casting"""
        # Quick bounding box check
        if geofence.bounds:
            if not (geofence.bounds.min_lat <= coord.latitude <= geofence.bounds.max_lat and
                   geofence.bounds.min_lon <= coord.longitude <= geofence.bounds.max_lon):
                return False
        
        # Ray casting algorithm
        inside = False
        points = geofence.polygon_points
        
        j = len(points) - 1
        for i in range(len(points)):
            xi, yi = points[i].latitude, points[i].longitude
            xj, yj = points[j].latitude, points[j].longitude
            
            if ((yi > coord.longitude) != (yj > coord.longitude)) and \
               (coord.latitude < (xj - xi) * (coord.longitude - yi) / (yj - yi) + xi):
                inside = not inside
            
            j = i
        
        return inside
    
    def get_nearby_geofences(self, coordinates: Coordinates,
                            max_distance_meters: float = 1000) -> List[Geofence]:
        """Get geofences near coordinates"""
        nearby = []
        
        for geofence in self.geofences.values():
            if geofence.geofence_type == GeofenceType.CIRCLE:
                distance = self.distance_calculator.haversine_distance(
                    geofence.center,
                    coordinates
                )
                
                if distance <= max_distance_meters:
                    nearby.append(geofence)
        
        return nearby

# ======================================================================================================================
# LOCATION TRACKER
# ======================================================================================================================

class LocationTracker:
    """Track entity locations"""
    
    def __init__(self):
        self.locations: Dict[str, LocationUpdate] = {}  # entity_id -> last location
        self.location_history: Dict[str, List[LocationUpdate]] = {}
        self.max_history = 1000
        
        logger.info("[TRACKER] Location tracker initialized")
    
    def update_location(self, entity_id: str, entity_type: str,
                       coordinates: Coordinates,
                       speed_mps: Optional[float] = None,
                       heading: Optional[float] = None):
        """Update entity location"""
        location_update = LocationUpdate(
            entity_id=entity_id,
            entity_type=entity_type,
            coordinates=coordinates,
            speed_mps=speed_mps,
            heading=heading
        )
        
        self.locations[entity_id] = location_update
        
        # Add to history
        if entity_id not in self.location_history:
            self.location_history[entity_id] = []
        
        self.location_history[entity_id].append(location_update)
        
        # Trim history
        if len(self.location_history[entity_id]) > self.max_history:
            self.location_history[entity_id] = self.location_history[entity_id][-self.max_history:]
        
        logger.debug(f"[TRACKER] Updated location: {entity_id}")
    
    def get_location(self, entity_id: str) -> Optional[LocationUpdate]:
        """Get current location"""
        return self.locations.get(entity_id)
    
    def get_location_history(self, entity_id: str,
                           start_time: Optional[datetime] = None,
                           end_time: Optional[datetime] = None) -> List[LocationUpdate]:
        """Get location history"""
        history = self.location_history.get(entity_id, [])
        
        if start_time:
            history = [loc for loc in history if loc.timestamp >= start_time]
        
        if end_time:
            history = [loc for loc in history if loc.timestamp <= end_time]
        
        return history
    
    def get_entities_in_area(self, center: Coordinates,
                            radius_meters: float) -> List[str]:
        """Get entities within radius"""
        from firmware.nvr_system.geospatial_services import DistanceCalculator
        
        calculator = DistanceCalculator()
        entities = []
        
        for entity_id, location in self.locations.items():
            distance = calculator.haversine_distance(
                center,
                location.coordinates
            )
            
            if distance <= radius_meters:
                entities.append(entity_id)
        
        return entities

# ======================================================================================================================
# GEOFENCE MONITOR
# ======================================================================================================================

class GeofenceMonitor:
    """Monitor geofence events"""
    
    def __init__(self, geofence_manager: GeofenceManager,
                 location_tracker: LocationTracker):
        self.geofence_manager = geofence_manager
        self.location_tracker = location_tracker
        self.entity_states: Dict[str, Dict[str, bool]] = {}  # entity_id -> {geofence_id: inside}
        self.alerts: List[GeofenceAlert] = []
        
        logger.info("[MONITOR] Geofence monitor initialized")
    
    def check_entity(self, entity_id: str) -> List[GeofenceAlert]:
        """Check entity against all geofences"""
        location = self.location_tracker.get_location(entity_id)
        
        if not location:
            return []
        
        alerts = []
        
        for geofence_id, geofence in self.geofence_manager.geofences.items():
            alert = self._check_geofence_transition(
                entity_id,
                geofence_id,
                location.coordinates
            )
            
            if alert:
                alerts.append(alert)
        
        return alerts
    
    def _check_geofence_transition(self, entity_id: str,
                                   geofence_id: str,
                                   coordinates: Coordinates) -> Optional[GeofenceAlert]:
        """Check for geofence entry/exit"""
        # Get previous state
        if entity_id not in self.entity_states:
            self.entity_states[entity_id] = {}
        
        was_inside = self.entity_states[entity_id].get(geofence_id, False)
        is_inside = self.geofence_manager.check_geofence(geofence_id, coordinates)
        
        # Update state
        self.entity_states[entity_id][geofence_id] = is_inside
        
        # Check for transition
        if is_inside and not was_inside:
            # Enter event
            alert = GeofenceAlert(
                alert_id=f"alert_{datetime.now().timestamp()}",
                geofence_id=geofence_id,
                entity_id=entity_id,
                event_type=GeofenceEvent.ENTER,
                coordinates=coordinates
            )
            
            self.alerts.append(alert)
            logger.info(f"[MONITOR] Geofence ENTER: {entity_id} -> {geofence_id}")
            return alert
            
        elif not is_inside and was_inside:
            # Exit event
            alert = GeofenceAlert(
                alert_id=f"alert_{datetime.now().timestamp()}",
                geofence_id=geofence_id,
                entity_id=entity_id,
                event_type=GeofenceEvent.EXIT,
                coordinates=coordinates
            )
            
            self.alerts.append(alert)
            logger.info(f"[MONITOR] Geofence EXIT: {entity_id} -> {geofence_id}")
            return alert
        
        return None

# ======================================================================================================================
# MAP TILE GENERATOR
# ======================================================================================================================

class MapTileGenerator:
    """Generate map tiles for web display"""
    
    def __init__(self):
        logger.info("[MAP-TILE] Map tile generator initialized")
    
    def lat_lon_to_tile(self, latitude: float, longitude: float,
                       zoom: int) -> Tuple[int, int]:
        """Convert lat/lon to tile coordinates"""
        n = 2.0 ** zoom
        
        x = int((longitude + 180.0) / 360.0 * n)
        
        lat_rad = math.radians(latitude)
        y = int((1.0 - math.asinh(math.tan(lat_rad)) / math.pi) / 2.0 * n)
        
        return (x, y)
    
    def tile_to_lat_lon(self, x: int, y: int, zoom: int) -> Tuple[float, float]:
        """Convert tile coordinates to lat/lon"""
        n = 2.0 ** zoom
        
        lon = x / n * 360.0 - 180.0
        
        lat_rad = math.atan(math.sinh(math.pi * (1 - 2 * y / n)))
        lat = math.degrees(lat_rad)
        
        return (lat, lon)
    
    def get_tile_bounds(self, x: int, y: int, zoom: int) -> BoundingBox:
        """Get bounding box for tile"""
        north, west = self.tile_to_lat_lon(x, y, zoom)
        south, east = self.tile_to_lat_lon(x + 1, y + 1, zoom)
        
        return BoundingBox(
            min_lat=south,
            max_lat=north,
            min_lon=west,
            max_lon=east
        )

# ======================================================================================================================
# GEOSPATIAL ORCHESTRATOR
# ======================================================================================================================

class GeospatialOrchestrator:
    """Main geospatial orchestrator"""
    
    def __init__(self):
        self.distance_calculator = DistanceCalculator()
        self.geofence_manager = GeofenceManager(self.distance_calculator)
        self.location_tracker = LocationTracker()
        self.geofence_monitor = GeofenceMonitor(
            self.geofence_manager,
            self.location_tracker
        )
        self.map_tile_generator = MapTileGenerator()
        
        logger.info("[GEO-ORCH] Geospatial orchestrator initialized")
        
        self._create_default_geofences()
    
    def _create_default_geofences(self):
        """Create default geofences"""
        # Farm boundary geofence
        self.geofence_manager.create_circle_geofence(
            "farm_main",
            "Main Farm Area",
            Coordinates(latitude=40.7128, longitude=-74.0060),
            radius_meters=1000
        )
    
    def update_device_location(self, device_id: str,
                              latitude: float, longitude: float):
        """Update device location"""
        coordinates = Coordinates(latitude=latitude, longitude=longitude)
        
        self.location_tracker.update_location(
            device_id,
            "device",
            coordinates
        )
        
        # Check geofences
        alerts = self.geofence_monitor.check_entity(device_id)
        
        return {
            'location_updated': True,
            'alerts': [
                {
                    'alert_id': alert.alert_id,
                    'geofence_id': alert.geofence_id,
                    'event_type': alert.event_type.value
                }
                for alert in alerts
            ]
        }
    
    def calculate_distance(self, lat1: float, lon1: float,
                         lat2: float, lon2: float) -> float:
        """Calculate distance between two points (meters)"""
        coord1 = Coordinates(latitude=lat1, longitude=lon1)
        coord2 = Coordinates(latitude=lat2, longitude=lon2)
        
        return self.distance_calculator.haversine_distance(coord1, coord2)
    
    def get_nearby_devices(self, latitude: float, longitude: float,
                          radius_meters: float = 1000) -> List[Dict[str, Any]]:
        """Get devices near location"""
        center = Coordinates(latitude=latitude, longitude=longitude)
        entity_ids = self.location_tracker.get_entities_in_area(center, radius_meters)
        
        results = []
        for entity_id in entity_ids:
            location = self.location_tracker.get_location(entity_id)
            if location:
                distance = self.distance_calculator.haversine_distance(
                    center,
                    location.coordinates
                )
                
                results.append({
                    'device_id': entity_id,
                    'latitude': location.coordinates.latitude,
                    'longitude': location.coordinates.longitude,
                    'distance_meters': distance
                })
        
        return sorted(results, key=lambda x: x['distance_meters'])
    
    def get_stats(self) -> Dict[str, Any]:
        """Get geospatial statistics"""
        return {
            'total_geofences': len(self.geofence_manager.geofences),
            'tracked_entities': len(self.location_tracker.locations),
            'total_alerts': len(self.geofence_monitor.alerts),
            'geofence_types': {
                gtype.value: len([
                    g for g in self.geofence_manager.geofences.values()
                    if g.geofence_type == gtype
                ])
                for gtype in GeofenceType
            }
        }

# ======================================================================================================================
# END OF GEOSPATIAL SERVICES MODULE
# Lines in this file: ~750+
# Combined total: ~36,850+
# Remaining for 50k: ~13,150 lines
# ======================================================================================================================
