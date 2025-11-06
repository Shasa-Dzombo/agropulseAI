"""
Orchard Mapping & GIS Integration System
=========================================

Comprehensive GIS system for tree geo-tagging, 3D orchard reconstruction,
and spatial disease analysis for drone-based monitoring.

TARGET: 80,000 Lines of Code (Orchard Mapping & GIS Module)

COMPONENTS:
-----------
1. Tree Geo-Tagging & Database (15,000 LOC)
2. 3D Orchard Reconstruction (18,000 LOC)
3. Growth Tracking Over Time (12,000 LOC)
4. Yield Prediction Models (10,000 LOC)
5. Irrigation Zone Mapping (8,000 LOC)
6. Disease Hotspot Identification (10,000 LOC)
7. Elevation & Drainage Analysis (7,000 LOC)

Author: AgroPulse Drone Systems
Date: November 2025
"""

import numpy as np
from dataclasses import dataclass
from typing import List, Dict, Tuple, Optional
from datetime import datetime
import json


@dataclass
class GeoTaggedTree:
    """Individual tree with GPS coordinates and tracking data"""
    tree_id: str
    gps_latitude: float
    gps_longitude: float
    elevation: float  # Meters above sea level
    crop_type: str  # "mango", "avocado", etc.
    variety: str
    planting_date: datetime
    tree_age: float  # Years
    row_number: int
    position_in_row: int
    
    # Health tracking
    current_health_score: float  # 0-100
    health_history: List[Tuple[datetime, float]]  # Historical health scores
    
    # Disease history
    disease_detections: List[Dict]  # List of disease detection events
    treatment_history: List[Dict]  # Applied treatments
    
    # Growth metrics
    canopy_area_history: List[Tuple[datetime, float]]  # m² over time
    canopy_diameter_history: List[Tuple[datetime, float]]  # m over time
    tree_height_history: List[Tuple[datetime, float]]  # m over time
    
    # Yield tracking
    yield_history: List[Tuple[int, float]]  # Year, kg harvested
    fruit_count_history: List[Tuple[datetime, int]]  # Fruit counts over season
    
    # Environmental
    soil_type: str
    irrigation_zone: int
    drainage_quality: str  # "excellent", "good", "poor"
    
    def get_growth_rate(self, metric: str = "canopy_diameter") -> float:
        """Calculate growth rate (per year)"""
        if metric == "canopy_diameter":
            history = self.canopy_diameter_history
        elif metric == "canopy_area":
            history = self.canopy_area_history
        elif metric == "height":
            history = self.tree_height_history
        else:
            return 0.0
        
        if len(history) < 2:
            return 0.0
        
        # Linear regression on growth data
        dates = [(h[0] - history[0][0]).days / 365.25 for h in history]
        values = [h[1] for h in history]
        
        # Simple slope calculation
        if len(dates) > 1:
            slope = (values[-1] - values[0]) / (dates[-1] - dates[0]) if dates[-1] != dates[0] else 0
            return slope
        
        return 0.0
    
    def predict_next_yield(self) -> float:
        """Predict next year's yield based on historical data"""
        if len(self.yield_history) < 2:
            return 0.0
        
        # Simple linear trend
        years = [y[0] for y in self.yield_history]
        yields = [y[1] for y in self.yield_history]
        
        if len(years) > 1:
            # Linear regression
            slope = (yields[-1] - yields[0]) / (years[-1] - years[0]) if years[-1] != years[0] else 0
            intercept = yields[0] - slope * years[0]
            next_year = years[-1] + 1
            predicted = slope * next_year + intercept
            return max(0, predicted)
        
        return yields[-1] if yields else 0.0


@dataclass
class OrchardBlock:
    """Orchard management block (group of rows)"""
    block_id: str
    block_name: str
    crop_type: str
    variety: str
    total_trees: int
    trees: List[GeoTaggedTree]
    
    # Spatial boundaries (polygon)
    boundary_coordinates: List[Tuple[float, float]]  # GPS polygon
    
    # Block-level metrics
    average_health_score: float
    disease_prevalence: float  # Percentage of trees with disease
    irrigation_system: str  # "drip", "micro-sprinkler", "flood"
    irrigation_schedule: Dict
    
    # Yield
    block_yield_history: List[Tuple[int, float]]  # Year, total kg
    
    def calculate_disease_hotspots(self) -> List[Tuple[float, float, int]]:
        """Identify disease hotspots (lat, lon, affected_tree_count)"""
        # Clustering algorithm to find concentrations of diseased trees
        diseased_trees = [t for t in self.trees if len(t.disease_detections) > 0]
        
        # Simple grid-based clustering (real system uses DBSCAN)
        hotspots = []
        grid_size = 0.0001  # ~11m at equator
        
        # Create grid
        grid: Dict[Tuple[int, int], List[GeoTaggedTree]] = {}
        for tree in diseased_trees:
            grid_x = int(tree.gps_latitude / grid_size)
            grid_y = int(tree.gps_longitude / grid_size)
            key = (grid_x, grid_y)
            if key not in grid:
                grid[key] = []
            grid[key].append(tree)
        
        # Find hotspots (grid cells with 3+ diseased trees)
        for (grid_x, grid_y), trees_in_cell in grid.items():
            if len(trees_in_cell) >= 3:
                center_lat = grid_x * grid_size + grid_size / 2
                center_lon = grid_y * grid_size + grid_size / 2
                hotspots.append((center_lat, center_lon, len(trees_in_cell)))
        
        return hotspots


@dataclass
class Orchard3DModel:
    """3D reconstruction of orchard"""
    orchard_id: str
    point_cloud: np.ndarray  # N x 3 (X, Y, Z coordinates)
    tree_positions: List[Tuple[float, float, float]]  # 3D tree locations
    digital_elevation_model: np.ndarray  # Elevation grid
    canopy_height_model: np.ndarray  # Tree height grid
    resolution: float  # Meters per pixel
    
    def calculate_drainage_flow(self) -> np.ndarray:
        """Calculate water flow direction based on elevation"""
        # Gradient-based flow direction (D8 algorithm)
        dy, dx = np.gradient(self.digital_elevation_model)
        
        # Flow direction: 0=N, 45=NE, 90=E, etc.
        flow_direction = np.arctan2(dy, dx) * 180 / np.pi
        
        return flow_direction
    
    def identify_low_spots(self, threshold_depth: float = 0.5) -> List[Tuple[float, float]]:
        """Identify low spots prone to waterlogging"""
        # Find local minima in DEM
        from scipy.ndimage import minimum_filter
        
        local_min = minimum_filter(self.digital_elevation_model, size=5)
        is_minimum = (self.digital_elevation_model == local_min)
        
        # Calculate depth relative to surroundings
        from scipy.ndimage import maximum_filter
        local_max = maximum_filter(self.digital_elevation_model, size=10)
        depth = local_max - self.digital_elevation_model
        
        # Find significant low spots
        significant_lows = is_minimum & (depth > threshold_depth)
        
        # Convert to GPS coordinates
        low_spots = []
        rows, cols = np.where(significant_lows)
        for row, col in zip(rows, cols):
            # Convert pixel to GPS (simplified)
            lat = row * self.resolution  # In real system, georeference properly
            lon = col * self.resolution
            low_spots.append((lat, lon))
        
        return low_spots


class OrchardGISDatabase:
    """
    Comprehensive GIS database for orchard management
    """
    
    def __init__(self, orchard_name: str):
        self.orchard_name = orchard_name
        self.trees: Dict[str, GeoTaggedTree] = {}
        self.blocks: Dict[str, OrchardBlock] = {}
        self.orchard_3d_model: Optional[Orchard3DModel] = None
        
        # Spatial index for fast nearest-neighbor queries
        self.spatial_index = {}
        
        print(f"[OrchardGIS] Initialized: {orchard_name}")
    
    def add_tree(self, tree: GeoTaggedTree):
        """Add tree to database"""
        self.trees[tree.tree_id] = tree
        
        # Update spatial index
        grid_key = self._get_spatial_grid_key(tree.gps_latitude, tree.gps_longitude)
        if grid_key not in self.spatial_index:
            self.spatial_index[grid_key] = []
        self.spatial_index[grid_key].append(tree.tree_id)
    
    def _get_spatial_grid_key(self, lat: float, lon: float) -> Tuple[int, int]:
        """Get spatial grid key for indexing"""
        grid_size = 0.001  # ~111m
        return (int(lat / grid_size), int(lon / grid_size))
    
    def find_trees_near(self, lat: float, lon: float, radius_m: float) -> List[GeoTaggedTree]:
        """Find trees within radius of GPS coordinate"""
        nearby_trees = []
        
        # Search nearby grid cells
        grid_key = self._get_spatial_grid_key(lat, lon)
        search_cells = [
            grid_key,
            (grid_key[0] + 1, grid_key[1]),
            (grid_key[0] - 1, grid_key[1]),
            (grid_key[0], grid_key[1] + 1),
            (grid_key[0], grid_key[1] - 1),
        ]
        
        for cell in search_cells:
            if cell in self.spatial_index:
                for tree_id in self.spatial_index[cell]:
                    tree = self.trees[tree_id]
                    distance = self._haversine_distance(lat, lon, tree.gps_latitude, tree.gps_longitude)
                    if distance <= radius_m:
                        nearby_trees.append(tree)
        
        return nearby_trees
    
    def _haversine_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate distance between GPS coordinates (meters)"""
        import math
        R = 6371000  # Earth radius
        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        dphi = math.radians(lat2 - lat1)
        dlambda = math.radians(lon2 - lon1)
        
        a = math.sin(dphi/2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda/2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        
        return R * c
    
    def generate_disease_heatmap(self, grid_resolution: float = 50.0) -> np.ndarray:
        """Generate disease prevalence heatmap (grid_resolution in meters)"""
        # Get orchard bounds
        lats = [t.gps_latitude for t in self.trees.values()]
        lons = [t.gps_longitude for t in self.trees.values()]
        
        if not lats:
            return np.array([])
        
        lat_min, lat_max = min(lats), max(lats)
        lon_min, lon_max = min(lons), max(lons)
        
        # Create grid
        lat_range = lat_max - lat_min
        lon_range = lon_max - lon_min
        
        # Convert to meters (approximate)
        lat_m = lat_range * 111000
        lon_m = lon_range * 111000
        
        grid_rows = int(lat_m / grid_resolution) + 1
        grid_cols = int(lon_m / grid_resolution) + 1
        
        heatmap = np.zeros((grid_rows, grid_cols))
        
        # Populate grid with disease counts
        for tree in self.trees.values():
            if len(tree.disease_detections) > 0:
                # Convert GPS to grid coordinates
                row = int((tree.gps_latitude - lat_min) / lat_range * grid_rows)
                col = int((tree.gps_longitude - lon_min) / lon_range * grid_cols)
                
                if 0 <= row < grid_rows and 0 <= col < grid_cols:
                    heatmap[row, col] += 1
        
        return heatmap
    
    def analyze_irrigation_efficiency(self) -> Dict:
        """Analyze irrigation system efficiency by zone"""
        # Group trees by irrigation zone
        zone_analysis = {}
        
        for tree in self.trees.values():
            zone = tree.irrigation_zone
            if zone not in zone_analysis:
                zone_analysis[zone] = {
                    "tree_count": 0,
                    "average_health": 0.0,
                    "stressed_trees": 0,
                    "yield_per_tree": 0.0
                }
            
            zone_analysis[zone]["tree_count"] += 1
            zone_analysis[zone]["average_health"] += tree.current_health_score
            
            if tree.current_health_score < 60:
                zone_analysis[zone]["stressed_trees"] += 1
            
            if tree.yield_history:
                zone_analysis[zone]["yield_per_tree"] += tree.yield_history[-1][1]
        
        # Calculate averages
        for zone in zone_analysis:
            count = zone_analysis[zone]["tree_count"]
            zone_analysis[zone]["average_health"] /= count
            zone_analysis[zone]["yield_per_tree"] /= count
            zone_analysis[zone]["stress_percentage"] = (
                zone_analysis[zone]["stressed_trees"] / count * 100
            )
        
        return zone_analysis
    
    def export_to_geojson(self, filename: str):
        """Export orchard data to GeoJSON format"""
        features = []
        
        for tree in self.trees.values():
            feature = {
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [tree.gps_longitude, tree.gps_latitude]
                },
                "properties": {
                    "tree_id": tree.tree_id,
                    "crop_type": tree.crop_type,
                    "variety": tree.variety,
                    "health_score": tree.current_health_score,
                    "diseases": len(tree.disease_detections),
                    "age": tree.tree_age
                }
            }
            features.append(feature)
        
        geojson = {
            "type": "FeatureCollection",
            "features": features
        }
        
        with open(filename, 'w') as f:
            json.dump(geojson, f, indent=2)
        
        print(f"Exported {len(features)} trees to {filename}")


if __name__ == "__main__":
    print("=" * 80)
    print("ORCHARD MAPPING & GIS INTEGRATION SYSTEM")
    print("=" * 80)
    
    # Create orchard database
    orchard_gis = OrchardGISDatabase("Mango Valley Orchard")
    
    # Add sample trees
    for i in range(100):
        tree = GeoTaggedTree(
            tree_id=f"MANGO_{i:03d}",
            gps_latitude=37.7749 + i * 0.00001,
            gps_longitude=-122.4194 + (i % 10) * 0.00001,
            elevation=100.0,
            crop_type="mango",
            variety="Tommy Atkins",
            planting_date=datetime(2015, 3, 15),
            tree_age=10.0,
            row_number=i // 10,
            position_in_row=i % 10,
            current_health_score=75.0 + np.random.normal(0, 10),
            health_history=[],
            disease_detections=[],
            treatment_history=[],
            canopy_area_history=[],
            canopy_diameter_history=[],
            tree_height_history=[],
            yield_history=[(2023, 45.0), (2024, 52.0)],
            fruit_count_history=[],
            soil_type="loamy",
            irrigation_zone=i % 5,
            drainage_quality="good"
        )
        orchard_gis.add_tree(tree)
    
    print(f"\n✓ Added {len(orchard_gis.trees)} trees to database")
    
    # Find nearby trees
    nearby = orchard_gis.find_trees_near(37.7749, -122.4194, radius_m=50.0)
    print(f"\n🌳 Found {len(nearby)} trees within 50m of center")
    
    # Generate disease heatmap
    heatmap = orchard_gis.generate_disease_heatmap()
    print(f"\n📊 Disease heatmap: {heatmap.shape}")
    
    # Analyze irrigation
    irrigation_analysis = orchard_gis.analyze_irrigation_efficiency()
    print(f"\n💧 Irrigation Analysis:")
    for zone, data in irrigation_analysis.items():
        print(f"  Zone {zone}: {data['tree_count']} trees, "
              f"Health: {data['average_health']:.1f}, "
              f"Yield: {data['yield_per_tree']:.1f} kg/tree")
    
    # Export
    orchard_gis.export_to_geojson("orchard_map.geojson")
    
    print("=" * 80)
