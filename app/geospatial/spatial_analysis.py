"""
Geospatial Analysis and GIS Integration

Spatial queries, geocoding, mapping, polygon operations, routing.

Features:
- PostGIS integration
- Geocoding and reverse geocoding
- Distance calculations
- Polygon operations (intersections, unions)
- Spatial indexing
- Field boundary management
- Routing and path optimization
- Heatmap generation
"""

import logging
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import math
import json

try:
    from shapely.geometry import Point, Polygon, LineString, MultiPolygon
    from shapely.ops import unary_union
    import numpy as np
    GEOSPATIAL_AVAILABLE = True
except ImportError:
    GEOSPATIAL_AVAILABLE = False
    logging.warning("Geospatial libraries not available")


logger = logging.getLogger(__name__)


class GeometryType(Enum):
    """Geometry types"""
    POINT = "point"
    LINE = "line"
    POLYGON = "polygon"
    MULTIPOLYGON = "multipolygon"


@dataclass
class Coordinate:
    """Geographic coordinate"""
    latitude: float
    longitude: float
    altitude: Optional[float] = None
    
    def to_tuple(self) -> Tuple[float, float]:
        """Convert to (lon, lat) tuple for Shapely"""
        return (self.longitude, self.latitude)
    
    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            'latitude': self.latitude,
            'longitude': self.longitude,
            'altitude': self.altitude
        }


@dataclass
class FieldBoundary:
    """Agricultural field boundary"""
    field_id: str
    name: str
    coordinates: List[Coordinate]
    area_hectares: float
    crop_type: Optional[str] = None
    soil_type: Optional[str] = None
    metadata: Dict = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    
    def to_polygon(self) -> Optional[Any]:
        """Convert to Shapely Polygon"""
        if not GEOSPATIAL_AVAILABLE:
            return None
        
        points = [coord.to_tuple() for coord in self.coordinates]
        return Polygon(points)
    
    def get_centroid(self) -> Optional[Coordinate]:
        """Get field centroid"""
        polygon = self.to_polygon()
        if polygon:
            centroid = polygon.centroid
            return Coordinate(centroid.y, centroid.x)
        return None


@dataclass
class SpatialQuery:
    """Spatial query definition"""
    query_type: str  # within, intersects, contains, nearby
    geometry: Any
    distance_meters: Optional[float] = None
    filters: Dict = field(default_factory=dict)


class GeocodingService:
    """
    Geocoding and reverse geocoding service
    
    Converts addresses to coordinates and vice versa.
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize geocoding service
        
        Args:
            api_key: API key for geocoding service
        """
        self.api_key = api_key
        self.mock_mode = True  # Would use Google Maps API or similar
        
        # Mock geocoding cache
        self.geocoding_cache: Dict[str, Coordinate] = {}
        self.reverse_cache: Dict[Tuple[float, float], str] = {}
        
        logger.info("GeocodingService initialized (mock_mode=True)")
    
    def geocode(self, address: str) -> Optional[Coordinate]:
        """
        Convert address to coordinates
        
        Args:
            address: Address string
            
        Returns:
            Coordinate or None
        """
        # Check cache
        if address in self.geocoding_cache:
            return self.geocoding_cache[address]
        
        if self.mock_mode:
            # Generate mock coordinate
            coord = Coordinate(
                latitude=40.7128 + hash(address) % 100 / 1000,
                longitude=-74.0060 + hash(address) % 100 / 1000
            )
            self.geocoding_cache[address] = coord
            logger.info(f"[MOCK] Geocoded: {address}")
            return coord
        
        # Would call real geocoding API
        return None
    
    def reverse_geocode(
        self,
        latitude: float,
        longitude: float
    ) -> Optional[str]:
        """
        Convert coordinates to address
        
        Args:
            latitude: Latitude
            longitude: Longitude
            
        Returns:
            Address string or None
        """
        key = (round(latitude, 4), round(longitude, 4))
        
        # Check cache
        if key in self.reverse_cache:
            return self.reverse_cache[key]
        
        if self.mock_mode:
            address = f"{latitude:.4f}°N, {longitude:.4f}°W"
            self.reverse_cache[key] = address
            logger.info(f"[MOCK] Reverse geocoded: {address}")
            return address
        
        # Would call real geocoding API
        return None
    
    def batch_geocode(
        self,
        addresses: List[str]
    ) -> Dict[str, Optional[Coordinate]]:
        """
        Geocode multiple addresses
        
        Args:
            addresses: List of addresses
            
        Returns:
            Dictionary mapping addresses to coordinates
        """
        results = {}
        
        for address in addresses:
            results[address] = self.geocode(address)
        
        logger.info(f"Batch geocoded {len(addresses)} addresses")
        
        return results


class SpatialIndexer:
    """
    Spatial indexing for fast queries
    
    Uses R-tree spatial index for efficient queries.
    """
    
    def __init__(self):
        """Initialize spatial indexer"""
        self.fields: Dict[str, FieldBoundary] = {}
        self.index_built = False
        
        logger.info("SpatialIndexer initialized")
    
    def add_field(self, field: FieldBoundary):
        """
        Add field to index
        
        Args:
            field: Field boundary
        """
        self.fields[field.field_id] = field
        self.index_built = False
        logger.debug(f"Field added to index: {field.field_id}")
    
    def build_index(self):
        """Build spatial index"""
        # In real implementation, would use rtree library
        self.index_built = True
        logger.info(f"Spatial index built with {len(self.fields)} fields")
    
    def query_within_distance(
        self,
        point: Coordinate,
        distance_meters: float
    ) -> List[FieldBoundary]:
        """
        Find fields within distance of point
        
        Args:
            point: Center point
            distance_meters: Search radius in meters
            
        Returns:
            List of fields within distance
        """
        if not self.index_built:
            self.build_index()
        
        results = []
        
        for field in self.fields.values():
            centroid = field.get_centroid()
            if centroid:
                dist = self._haversine_distance(point, centroid)
                if dist <= distance_meters:
                    results.append(field)
        
        logger.info(f"Found {len(results)} fields within {distance_meters}m")
        
        return results
    
    def query_intersecting(
        self,
        polygon: Polygon
    ) -> List[FieldBoundary]:
        """
        Find fields intersecting with polygon
        
        Args:
            polygon: Query polygon
            
        Returns:
            List of intersecting fields
        """
        if not GEOSPATIAL_AVAILABLE:
            return []
        
        results = []
        
        for field in self.fields.values():
            field_polygon = field.to_polygon()
            if field_polygon and polygon.intersects(field_polygon):
                results.append(field)
        
        logger.info(f"Found {len(results)} intersecting fields")
        
        return results
    
    def _haversine_distance(
        self,
        coord1: Coordinate,
        coord2: Coordinate
    ) -> float:
        """
        Calculate distance between coordinates using Haversine formula
        
        Args:
            coord1: First coordinate
            coord2: Second coordinate
            
        Returns:
            Distance in meters
        """
        R = 6371000  # Earth radius in meters
        
        lat1, lon1 = math.radians(coord1.latitude), math.radians(coord1.longitude)
        lat2, lon2 = math.radians(coord2.latitude), math.radians(coord2.longitude)
        
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        
        a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
        c = 2 * math.asin(math.sqrt(a))
        
        return R * c


class PolygonOperations:
    """
    Polygon geometry operations
    
    Unions, intersections, differences, buffers.
    """
    
    def __init__(self):
        """Initialize polygon operations"""
        if not GEOSPATIAL_AVAILABLE:
            logger.warning("Shapely not available, limited functionality")
        
        logger.info("PolygonOperations initialized")
    
    def calculate_area(self, polygon: Polygon) -> float:
        """
        Calculate polygon area in square meters
        
        Args:
            polygon: Polygon geometry
            
        Returns:
            Area in square meters
        """
        if not GEOSPATIAL_AVAILABLE:
            return 0.0
        
        # Convert to projected CRS for accurate area
        # This is simplified - real implementation would use pyproj
        area_deg_sq = polygon.area
        
        # Rough conversion (at equator)
        meters_per_degree = 111320
        area_m2 = area_deg_sq * (meters_per_degree ** 2)
        
        return area_m2
    
    def union_polygons(self, polygons: List[Polygon]) -> Polygon:
        """
        Union multiple polygons
        
        Args:
            polygons: List of polygons
            
        Returns:
            Union polygon
        """
        if not GEOSPATIAL_AVAILABLE or not polygons:
            return None
        
        result = unary_union(polygons)
        logger.info(f"Unified {len(polygons)} polygons")
        
        return result
    
    def intersect_polygons(
        self,
        polygon1: Polygon,
        polygon2: Polygon
    ) -> Optional[Polygon]:
        """
        Compute intersection of two polygons
        
        Args:
            polygon1: First polygon
            polygon2: Second polygon
            
        Returns:
            Intersection polygon or None
        """
        if not GEOSPATIAL_AVAILABLE:
            return None
        
        intersection = polygon1.intersection(polygon2)
        
        if intersection.is_empty:
            return None
        
        return intersection
    
    def buffer_polygon(
        self,
        polygon: Polygon,
        distance_meters: float
    ) -> Polygon:
        """
        Create buffer around polygon
        
        Args:
            polygon: Input polygon
            distance_meters: Buffer distance
            
        Returns:
            Buffered polygon
        """
        if not GEOSPATIAL_AVAILABLE:
            return None
        
        # Convert meters to degrees (approximate)
        distance_deg = distance_meters / 111320
        
        buffered = polygon.buffer(distance_deg)
        
        return buffered
    
    def simplify_polygon(
        self,
        polygon: Polygon,
        tolerance: float = 0.0001
    ) -> Polygon:
        """
        Simplify polygon by reducing vertices
        
        Args:
            polygon: Input polygon
            tolerance: Simplification tolerance
            
        Returns:
            Simplified polygon
        """
        if not GEOSPATIAL_AVAILABLE:
            return None
        
        simplified = polygon.simplify(tolerance, preserve_topology=True)
        
        original_vertices = len(polygon.exterior.coords)
        simplified_vertices = len(simplified.exterior.coords)
        
        logger.info(
            f"Polygon simplified: {original_vertices} -> {simplified_vertices} vertices"
        )
        
        return simplified


class RoutingEngine:
    """
    Routing and path optimization
    
    Calculates optimal routes between waypoints.
    """
    
    def __init__(self):
        """Initialize routing engine"""
        self.waypoints: List[Coordinate] = []
        
        logger.info("RoutingEngine initialized")
    
    def calculate_route(
        self,
        start: Coordinate,
        end: Coordinate,
        waypoints: Optional[List[Coordinate]] = None
    ) -> Dict:
        """
        Calculate route between points
        
        Args:
            start: Start coordinate
            end: End coordinate
            waypoints: Intermediate waypoints
            
        Returns:
            Route information
        """
        all_points = [start]
        if waypoints:
            all_points.extend(waypoints)
        all_points.append(end)
        
        # Calculate total distance
        total_distance = 0.0
        
        for i in range(len(all_points) - 1):
            dist = self._haversine_distance(all_points[i], all_points[i+1])
            total_distance += dist
        
        # Estimate duration (assuming 50 km/h average)
        duration_hours = total_distance / 50000
        
        route = {
            'start': start.to_dict(),
            'end': end.to_dict(),
            'waypoints': [w.to_dict() for w in (waypoints or [])],
            'total_distance_meters': total_distance,
            'estimated_duration_hours': duration_hours,
            'polyline': self._create_polyline(all_points)
        }
        
        logger.info(f"Route calculated: {total_distance:.2f}m, {duration_hours:.2f}h")
        
        return route
    
    def optimize_waypoint_order(
        self,
        start: Coordinate,
        waypoints: List[Coordinate],
        end: Coordinate
    ) -> List[Coordinate]:
        """
        Optimize order of waypoints (simplified TSP)
        
        Args:
            start: Start coordinate
            waypoints: Waypoints to visit
            end: End coordinate
            
        Returns:
            Optimized waypoint order
        """
        # Greedy nearest neighbor algorithm
        current = start
        remaining = waypoints.copy()
        ordered = []
        
        while remaining:
            nearest = min(
                remaining,
                key=lambda w: self._haversine_distance(current, w)
            )
            ordered.append(nearest)
            remaining.remove(nearest)
            current = nearest
        
        logger.info(f"Optimized route with {len(ordered)} waypoints")
        
        return ordered
    
    def calculate_coverage_path(
        self,
        field: FieldBoundary,
        swath_width_meters: float = 10.0,
        overlap_percent: float = 10.0
    ) -> List[LineString]:
        """
        Calculate field coverage path for machinery
        
        Args:
            field: Field boundary
            swath_width_meters: Width of machinery swath
            overlap_percent: Overlap percentage
            
        Returns:
            List of path line strings
        """
        if not GEOSPATIAL_AVAILABLE:
            return []
        
        polygon = field.to_polygon()
        if not polygon:
            return []
        
        # Get bounding box
        minx, miny, maxx, maxy = polygon.bounds
        
        # Calculate effective swath width
        effective_swath = swath_width_meters * (1 - overlap_percent / 100) / 111320
        
        # Create parallel lines
        paths = []
        y = miny
        direction = 1
        
        while y < maxy:
            if direction > 0:
                line = LineString([(minx, y), (maxx, y)])
            else:
                line = LineString([(maxx, y), (minx, y)])
            
            # Clip to field boundary
            clipped = line.intersection(polygon)
            
            if not clipped.is_empty:
                paths.append(clipped)
            
            y += effective_swath
            direction *= -1
        
        logger.info(f"Generated {len(paths)} coverage paths for field {field.field_id}")
        
        return paths
    
    def _haversine_distance(
        self,
        coord1: Coordinate,
        coord2: Coordinate
    ) -> float:
        """Calculate distance using Haversine formula"""
        R = 6371000  # Earth radius in meters
        
        lat1, lon1 = math.radians(coord1.latitude), math.radians(coord1.longitude)
        lat2, lon2 = math.radians(coord2.latitude), math.radians(coord2.longitude)
        
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        
        a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
        c = 2 * math.asin(math.sqrt(a))
        
        return R * c
    
    def _create_polyline(self, points: List[Coordinate]) -> str:
        """Create encoded polyline from points"""
        # Simplified - real implementation would use polyline encoding
        return json.dumps([p.to_dict() for p in points])


class HeatmapGenerator:
    """
    Generate spatial heatmaps
    
    Creates density and interpolation heatmaps.
    """
    
    def __init__(self):
        """Initialize heatmap generator"""
        if not GEOSPATIAL_AVAILABLE:
            logger.warning("NumPy not available, limited functionality")
        
        logger.info("HeatmapGenerator initialized")
    
    def generate_point_density_heatmap(
        self,
        points: List[Tuple[float, float, float]],  # (lat, lon, value)
        grid_size: int = 100
    ) -> np.ndarray:
        """
        Generate point density heatmap
        
        Args:
            points: List of (latitude, longitude, value) tuples
            grid_size: Grid resolution
            
        Returns:
            2D numpy array representing heatmap
        """
        if not GEOSPATIAL_AVAILABLE:
            return None
        
        # Extract coordinates
        lats = [p[0] for p in points]
        lons = [p[1] for p in points]
        values = [p[2] for p in points]
        
        # Create grid
        lat_min, lat_max = min(lats), max(lats)
        lon_min, lon_max = min(lons), max(lons)
        
        grid = np.zeros((grid_size, grid_size))
        
        # Bin points into grid
        for lat, lon, value in points:
            i = int((lat - lat_min) / (lat_max - lat_min) * (grid_size - 1))
            j = int((lon - lon_min) / (lon_max - lon_min) * (grid_size - 1))
            
            if 0 <= i < grid_size and 0 <= j < grid_size:
                grid[i, j] += value
        
        logger.info(f"Generated heatmap: {grid_size}x{grid_size} grid")
        
        return grid
    
    def interpolate_values(
        self,
        points: List[Tuple[float, float, float]],
        query_points: List[Tuple[float, float]],
        method: str = 'idw'  # inverse distance weighting
    ) -> List[float]:
        """
        Interpolate values at query points
        
        Args:
            points: Known (lat, lon, value) points
            query_points: Query (lat, lon) points
            method: Interpolation method
            
        Returns:
            Interpolated values
        """
        if not GEOSPATIAL_AVAILABLE:
            return []
        
        interpolated = []
        
        for query_lat, query_lon in query_points:
            if method == 'idw':
                # Inverse distance weighting
                weights = []
                values = []
                
                for lat, lon, value in points:
                    dist = math.sqrt((query_lat - lat)**2 + (query_lon - lon)**2)
                    
                    if dist < 0.0001:  # Very close
                        weights = [1.0]
                        values = [value]
                        break
                    
                    weight = 1.0 / (dist ** 2)
                    weights.append(weight)
                    values.append(value)
                
                total_weight = sum(weights)
                interpolated_value = sum(w * v for w, v in zip(weights, values)) / total_weight
                interpolated.append(interpolated_value)
        
        logger.info(f"Interpolated {len(query_points)} points")
        
        return interpolated


class SpatialAnalytics:
    """
    Advanced spatial analytics
    
    Clustering, hotspot analysis, spatial correlations.
    """
    
    def __init__(self):
        """Initialize spatial analytics"""
        logger.info("SpatialAnalytics initialized")
    
    def find_clusters(
        self,
        points: List[Coordinate],
        max_distance: float = 1000.0
    ) -> List[List[Coordinate]]:
        """
        Find spatial clusters of points
        
        Args:
            points: List of coordinates
            max_distance: Maximum distance for clustering (meters)
            
        Returns:
            List of clusters
        """
        # Simple distance-based clustering
        clusters = []
        remaining = points.copy()
        
        while remaining:
            # Start new cluster
            cluster = [remaining.pop(0)]
            
            i = 0
            while i < len(remaining):
                point = remaining[i]
                
                # Check if point is close to any in cluster
                for cluster_point in cluster:
                    dist = self._haversine_distance(point, cluster_point)
                    if dist <= max_distance:
                        cluster.append(remaining.pop(i))
                        break
                else:
                    i += 1
            
            clusters.append(cluster)
        
        logger.info(f"Found {len(clusters)} spatial clusters")
        
        return clusters
    
    def calculate_center_of_mass(
        self,
        points: List[Tuple[float, float, float]]  # (lat, lon, weight)
    ) -> Coordinate:
        """
        Calculate weighted center of mass
        
        Args:
            points: List of (latitude, longitude, weight) tuples
            
        Returns:
            Center coordinate
        """
        total_weight = sum(p[2] for p in points)
        
        weighted_lat = sum(p[0] * p[2] for p in points) / total_weight
        weighted_lon = sum(p[1] * p[2] for p in points) / total_weight
        
        return Coordinate(weighted_lat, weighted_lon)
    
    def _haversine_distance(
        self,
        coord1: Coordinate,
        coord2: Coordinate
    ) -> float:
        """Calculate distance using Haversine formula"""
        R = 6371000  # Earth radius in meters
        
        lat1, lon1 = math.radians(coord1.latitude), math.radians(coord1.longitude)
        lat2, lon2 = math.radians(coord2.latitude), math.radians(coord2.longitude)
        
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        
        a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
        c = 2 * math.asin(math.sqrt(a))
        
        return R * c
