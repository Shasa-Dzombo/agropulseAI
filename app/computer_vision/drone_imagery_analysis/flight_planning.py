# c:\Users\Codeternal\Desktop\AgroPulse\app\computer_vision\drone_imagery_analysis\flight_planning.py

"""
Drone Flight Planning and Optimization for Agricultural Surveys
================================================================

This module provides a comprehensive framework for generating and optimizing
drone flight plans for agricultural surveys. Effective flight planning is
essential to ensure complete data coverage, consistent image quality, and
efficient use of battery life.

The goal is to automate the creation of flight paths that are tailored to the
specific requirements of a survey, such as the desired Ground Sample Distance (GSD),
image overlap, and the shape of the survey area.

Key Components:
---------------
1.  **`SurveyArea`**: A representation of the area to be surveyed, typically
    defined by a polygon. It handles the geometric calculations needed to
    determine the bounds and orientation of the flight grid.

2.  **`Camera` and `Drone` Models**: Data classes to store the specifications of
    the camera (sensor size, focal length, resolution) and the drone (flight
    speed, battery life). These parameters are crucial for all planning
    calculations.

3.  **`FlightParameters`**: A configuration object that holds all the user-defined
    requirements for the survey, including desired GSD, image overlap (frontlap
    and sidelap), and flight pattern type.

4.  **`CoveragePlanner`**: The core calculation engine. It takes the camera specs
    and flight parameters to determine:
    -   **Flight Altitude**: The required height above ground to achieve the desired GSD.
    -   **Footprint Size**: The area on the ground covered by a single image.
    -   **Line Spacing**: The distance between adjacent parallel flight lines (swaths).
    -   **Trigger Distance**: The distance the drone travels between taking photos.

5.  **`PathGenerator`**: Generates the actual sequence of waypoints for a given
    survey area and flight parameters. It supports various patterns:
    -   **Boustrophedon (Lawnmower) Pattern**: The most common pattern for 2D mapping,
      where the drone flies back and forth in parallel lines.
    -   **Grid Pattern**: A double-lawnmower pattern, flying the same area twice at a
      90-degree offset. This is ideal for 3D modeling as it provides better
      oblique views of objects.
    -   **Circular/Orbit Pattern**: Flies in circles around a point of interest,
      useful for detailed 3D reconstruction of a specific object (e.g., a water tower,
      a specific research plot).

6.  **`TerrainFollower`**: An advanced feature that adjusts the altitude of waypoints
    based on an underlying Digital Elevation Model (DEM). This ensures a constant
    GSD and image footprint, even over hilly or uneven terrain.

7.  **`FlightPlan`**: The final output, containing a list of waypoints, estimated
    flight time, distance, number of photos, and other summary statistics. It can
    be exported to common drone control formats like MAVLink `.plan` or simple CSV.

Workflow:
---------
1.  **Initialization**: Define the `SurveyArea`, `Camera`, `Drone`, and
    `FlightParameters`.
2.  **Planning**: The `CoveragePlanner` calculates the fundamental flight metrics
    (altitude, spacing).
3.  **Path Generation**: The `PathGenerator` creates the waypoints for the chosen
    flight pattern over the survey area.
4.  **(Optional) Terrain Following**: The `TerrainFollower` refines the waypoint
    altitudes using a DEM.
5.  **Finalization**: A `FlightPlan` object is created, summarizing the mission.
6.  **Export**: The flight plan is saved to a file that can be uploaded to a
    drone's ground control station.

Dependencies:
-------------
- NumPy: For numerical calculations.
- Shapely: For all geometric operations on the survey area polygon.
- GeoPandas: For handling georeferenced survey areas and exporting plans.
- Rasterio: For reading DEMs for the terrain-following feature.
"""

import numpy as np
from shapely.geometry import Polygon, LineString, Point
import geopandas as gpd
import rasterio
import logging
import time
import math
from dataclasses import dataclass, field
from typing import List, Tuple, Optional, Dict, Any

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(module)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# --- Data Models ---

@dataclass
class Camera:
    """Stores camera specifications."""
    name: str
    sensor_width_mm: float  # Width of the camera sensor in millimeters
    sensor_height_mm: float # Height of the camera sensor in millimeters
    focal_length_mm: float  # Effective focal length in millimeters
    image_width_px: int     # Image resolution width in pixels
    image_height_px: int    # Image resolution height in pixels

@dataclass
class Drone:
    """Stores drone performance characteristics."""
    name: str
    speed_mps: float  # Cruising speed in meters per second
    max_flight_time_min: float # Maximum flight time on a single battery in minutes

@dataclass
class FlightParameters:
    """Stores user-defined survey requirements."""
    gsd_cm: float  # Desired Ground Sample Distance in centimeters per pixel
    sidelap_percent: float  # Overlap between adjacent flight lines (e.g., 60 for 60%)
    frontlap_percent: float # Overlap between consecutive photos in the same line (e.g., 80 for 80%)
    pattern: str = 'boustrophedon'  # 'boustrophedon', 'grid', 'orbit'
    flight_angle_deg: Optional[float] = None # Optional fixed angle for flight lines
    terrain_following: bool = False # Whether to use terrain following
    terrain_offset_m: float = 0 # Additional safety buffer for terrain following

@dataclass
class Waypoint:
    """Represents a single point in a flight plan."""
    latitude: float
    longitude: float
    altitude_msl: float # Altitude in meters above mean sea level
    actions: List[Dict[str, Any]] = field(default_factory=list) # e.g., {'type': 'take_photo'}

@dataclass
class FlightPlan:
    """The final, complete flight plan."""
    waypoints: List[Waypoint]
    survey_area: Polygon
    estimated_flight_time_sec: float
    estimated_distance_m: float
    estimated_num_photos: int
    summary: Dict[str, Any]

# --- Core Components ---

class CoveragePlanner:
    """
    Calculates fundamental flight metrics based on camera and survey parameters.
    """
    def __init__(self, camera: Camera, params: FlightParameters):
        self.camera = camera
        self.params = params
        self.metrics = self._calculate_metrics()

    def _calculate_metrics(self) -> Dict[str, float]:
        """Performs the core planning calculations."""
        logging.info("Calculating flight coverage metrics...")

        # 1. Calculate flight altitude from GSD
        # GSD = (SensorWidth * Altitude * 100) / (FocalLength * ImageWidth)
        # Altitude = (GSD * FocalLength * ImageWidth) / (SensorWidth * 100)
        altitude_m = (self.params.gsd_cm * self.camera.focal_length_mm * self.camera.image_width_px) / (self.camera.sensor_width_mm * 100)

        # 2. Calculate ground footprint of a single image
        footprint_width_m = (self.camera.sensor_width_mm * altitude_m) / self.camera.focal_length_mm
        footprint_height_m = (self.camera.sensor_height_mm * altitude_m) / self.camera.focal_length_mm

        # 3. Calculate line spacing (distance between swaths) based on sidelap
        line_spacing_m = footprint_width_m * (1 - self.params.sidelap_percent / 100)

        # 4. Calculate photo trigger distance based on frontlap
        trigger_distance_m = footprint_height_m * (1 - self.params.frontlap_percent / 100)

        metrics = {
            'altitude_m': altitude_m,
            'footprint_width_m': footprint_width_m,
            'footprint_height_m': footprint_height_m,
            'line_spacing_m': line_spacing_m,
            'trigger_distance_m': trigger_distance_m,
        }
        logging.info(f"Calculated metrics: {metrics}")
        return metrics

class PathGenerator:
    """
    Generates waypoint sequences for different flight patterns.
    
    Note: This class works with Cartesian coordinates for path generation.
    Conversion to/from Lat/Lon should be handled by the main orchestrator,
    as it requires a proper CRS and projection.
    """
    def __init__(self, survey_polygon: Polygon, planner: CoveragePlanner):
        self.survey_polygon = survey_polygon
        self.planner = planner
        self.metrics = planner.metrics

    def generate_path(self) -> Tuple[List[np.ndarray], int]:
        """
        Main method to generate a path based on the specified pattern.
        
        Returns:
            A tuple containing a list of waypoint coordinates (as NumPy arrays)
            and the estimated number of photos.
        """
        pattern = self.planner.params.pattern
        if pattern == 'boustrophedon':
            return self._generate_boustrophedon()
        elif pattern == 'grid':
            return self._generate_grid()
        elif pattern == 'orbit':
            return self._generate_orbit()
        else:
            raise ValueError(f"Unknown flight pattern: {pattern}")

    def _get_optimal_angle(self) -> float:
        """Finds the angle that minimizes the number of turns (longest swath)."""
        if self.planner.params.flight_angle_deg is not None:
            return np.deg2rad(self.planner.params.flight_angle_deg)

        # Use the angle of the longest edge of the minimum rotated rectangle
        min_rect = self.survey_polygon.minimum_rotated_rectangle
        coords = np.array(min_rect.exterior.coords)
        edge_lengths = np.linalg.norm(np.diff(coords, axis=0), axis=1)
        longest_edge_index = np.argmax(edge_lengths)
        p1 = coords[longest_edge_index]
        p2 = coords[longest_edge_index + 1]
        return np.arctan2(p2[1] - p1[1], p2[0] - p1[0])

    def _generate_boustrophedon(self, angle_rad: Optional[float] = None) -> Tuple[List[np.ndarray], int]:
        """Generates a lawnmower-style path."""
        logging.info("Generating Boustrophedon (lawnmower) path...")
        if angle_rad is None:
            angle_rad = self._get_optimal_angle()
        
        # Rotate the polygon so that flight lines are horizontal
        from shapely.affinity import rotate
        rotated_poly = rotate(self.survey_polygon, -np.rad2deg(angle_rad), origin='center')
        
        min_x, min_y, max_x, max_y = rotated_poly.bounds
        line_spacing = self.metrics['line_spacing_m']
        
        # Generate horizontal flight lines
        lines = []
        y = min_y + line_spacing / 2
        while y <= max_y:
            line = LineString([(min_x - 10, y), (max_x + 10, y)]) # Extend lines to ensure full intersection
            intersection = rotated_poly.intersection(line)
            if not intersection.is_empty:
                lines.append(intersection)
            y += line_spacing
            
        if not lines:
            logging.warning("No flight lines generated. Check survey area and parameters.")
            return [], 0

        # Order the lines and create waypoints
        waypoints = []
        for i, line in enumerate(lines):
            coords = list(line.coords)
            # Alternate direction for each line
            if i % 2 == 1:
                coords = coords[::-1]
            waypoints.extend(coords)

        # Rotate waypoints back to original orientation
        rotation_matrix = np.array([
            [np.cos(angle_rad), -np.sin(angle_rad)],
            [np.sin(angle_rad), np.cos(angle_rad)]
        ])
        center = np.array(self.survey_polygon.centroid.coords[0])
        
        rotated_waypoints = []
        for wp in waypoints:
            p = np.array(wp) - center
            rotated_p = rotation_matrix @ p + center
            rotated_waypoints.append(rotated_p)

        # Add photo trigger points
        final_path, num_photos = self._interpolate_triggers(rotated_waypoints)
        
        return final_path, num_photos

    def _generate_grid(self) -> Tuple[List[np.ndarray], int]:
        """Generates a double-boustrophedon path at 90-degree offset."""
        logging.info("Generating Grid path...")
        angle1 = self._get_optimal_angle()
        angle2 = angle1 + np.pi / 2

        path1, photos1 = self._generate_boustrophedon(angle_rad=angle1)
        path2, photos2 = self._generate_boustrophedon(angle_rad=angle2)
        
        return path1 + path2, photos1 + photos2

    def _generate_orbit(self) -> Tuple[List[np.ndarray], int]:
        """Generates a circular path around the center of the survey area."""
        logging.info("Generating Orbit path...")
        center = np.array(self.survey_polygon.centroid.coords[0])
        
        # Determine radius from the farthest point of the polygon
        radius = max(Point(center).distance(Point(p)) for p in self.survey_polygon.exterior.coords)
        
        num_points = 36 # Number of waypoints in the circle
        angles = np.linspace(0, 2 * np.pi, num_points, endpoint=False)
        
        waypoints = [
            center + np.array([radius * np.cos(a), radius * np.sin(a)]) for a in angles
        ]
        # Close the loop
        waypoints.append(waypoints[0])

        final_path, num_photos = self._interpolate_triggers(waypoints)
        return final_path, num_photos

    def _interpolate_triggers(self, path_nodes: List[np.ndarray]) -> Tuple[List[np.ndarray], int]:
        """Adds intermediate waypoints for photo triggers along a path."""
        if not path_nodes:
            return [], 0
            
        trigger_dist = self.metrics['trigger_distance_m']
        full_path = [path_nodes[0]]
        num_photos = 0

        for i in range(len(path_nodes) - 1):
            start_node = path_nodes[i]
            end_node = path_nodes[i+1]
            
            segment = end_node - start_node
            segment_length = np.linalg.norm(segment)
            if segment_length == 0:
                continue
            
            segment_dir = segment / segment_length
            
            num_triggers = math.floor(segment_length / trigger_dist)
            
            for j in range(1, num_triggers + 1):
                new_point = start_node + segment_dir * j * trigger_dist
                full_path.append(new_point)
                num_photos += 1
            
            full_path.append(end_node)
        
        return full_path, num_photos

class TerrainFollower:
    """
    Adjusts waypoint altitudes based on a DEM.
    """
    def __init__(self, dem_path: str):
        self.dem_path = dem_path
        self.dem_src = rasterio.open(dem_path)

    def adjust_altitudes(self, waypoints_2d: List[np.ndarray], base_alt_agl: float, safety_offset: float) -> List[np.ndarray]:
        """
        Takes a list of 2D waypoints and returns a list of 3D waypoints with
        terrain-adjusted altitudes.

        Args:
            waypoints_2d: List of (x, y) coordinates.
            base_alt_agl: The target altitude above ground level.
            safety_offset: Additional safety buffer.

        Returns:
            List of (x, y, z) coordinates where z is altitude MSL.
        """
        logging.info("Applying terrain following...")
        if self.dem_src.crs is None:
            raise ValueError("DEM must have a valid CRS for terrain following.")

        # Assuming waypoints are in the same CRS as the DEM
        xs = [wp[0] for wp in waypoints_2d]
        ys = [wp[1] for wp in waypoints_2d]

        # Sample DEM for ground elevations
        ground_elevations = [val[0] for val in self.dem_src.sample(zip(xs, ys))]
        
        waypoints_3d = []
        for i, wp in enumerate(waypoints_2d):
            ground_elevation_msl = ground_elevations[i]
            target_altitude_msl = ground_elevation_msl + base_alt_agl + safety_offset
            waypoints_3d.append(np.array([wp[0], wp[1], target_altitude_msl]))
            
        return waypoints_3d

    def __del__(self):
        if hasattr(self, 'dem_src') and not self.dem_src.closed:
            self.dem_src.close()

# --- Main Orchestrator ---

class FlightPlanner:
    """
    Orchestrates the entire flight planning process.
    """
    def __init__(self, survey_gdf: gpd.GeoDataFrame, camera: Camera, drone: Drone, params: FlightParameters):
        """
        Args:
            survey_gdf: A GeoDataFrame containing a single polygon for the survey area.
                        Must have a defined CRS.
        """
        if survey_gdf.crs is None:
            raise ValueError("Survey GeoDataFrame must have a CRS.")
        if len(survey_gdf) != 1 or not isinstance(survey_gdf.geometry.iloc[0], Polygon):
            raise ValueError("Survey GeoDataFrame must contain exactly one Polygon.")
            
        self.survey_gdf = survey_gdf
        self.camera = camera
        self.drone = drone
        self.params = params
        self.coverage_planner = CoveragePlanner(camera, params)

    def generate_flight_plan(self, dem_path: Optional[str] = None) -> FlightPlan:
        """
        Generates the full flight plan.

        Args:
            dem_path (str, optional): Path to a DEM for terrain following.

        Returns:
            A FlightPlan object.
        """
        logging.info("--- Starting Flight Plan Generation ---")
        start_time = time.time()

        survey_polygon = self.survey_gdf.geometry.iloc[0]
        
        # 1. Generate 2D path
        path_generator = PathGenerator(survey_polygon, self.coverage_planner)
        waypoints_2d, num_photos = path_generator.generate_path()

        if not waypoints_2d:
            raise RuntimeError("Failed to generate a valid 2D path.")

        # 2. Determine altitudes
        base_altitude_agl = self.coverage_planner.metrics['altitude_m']
        
        if self.params.terrain_following and dem_path:
            terrain_follower = TerrainFollower(dem_path)
            # Ensure DEM and survey area are in the same CRS
            if self.survey_gdf.crs != terrain_follower.dem_src.crs:
                logging.info(f"Re-projecting survey area to match DEM CRS ({terrain_follower.dem_src.crs})...")
                reprojected_gdf = self.survey_gdf.to_crs(terrain_follower.dem_src.crs)
                # Re-generate 2D path in the new CRS
                path_generator = PathGenerator(reprojected_gdf.geometry.iloc[0], self.coverage_planner)
                waypoints_2d, num_photos = path_generator.generate_path()

            waypoints_3d = terrain_follower.adjust_altitudes(
                waypoints_2d, base_altitude_agl, self.params.terrain_offset_m
            )
        else:
            # Use constant altitude AGL + base elevation of the area
            # A simple approximation for base elevation: centroid of the polygon
            base_elevation = 0
            if dem_path:
                with rasterio.open(dem_path) as src:
                    centroid = survey_polygon.centroid
                    base_elevation = list(src.sample([(centroid.x, centroid.y)]))[0][0]
            
            waypoints_3d = [np.array([wp[0], wp[1], base_elevation + base_altitude_agl]) for wp in waypoints_2d]

        # 3. Convert waypoints to Lat/Lon (WGS84) for export
        waypoints_gdf = gpd.GeoDataFrame(
            geometry=[Point(wp) for wp in waypoints_3d],
            crs=self.survey_gdf.crs
        )
        waypoints_wgs84 = waypoints_gdf.to_crs("EPSG:4326")

        final_waypoints = []
        for idx, row in waypoints_wgs84.iterrows():
            actions = [{'type': 'take_photo'}] if idx > 0 and idx < len(waypoints_wgs84) -1 else []
            final_waypoints.append(Waypoint(
                latitude=row.geometry.y,
                longitude=row.geometry.x,
                altitude_msl=row.geometry.z,
                actions=actions
            ))

        # 4. Calculate summary stats
        total_distance = np.sum(np.linalg.norm(np.diff(np.array(waypoints_2d), axis=0), axis=1))
        flight_time_sec = total_distance / self.drone.speed_mps
        
        summary = {
            'gsd_cm': self.params.gsd_cm,
            'altitude_agl_m': base_altitude_agl,
            'sidelap_%': self.params.sidelap_percent,
            'frontlap_%': self.params.frontlap_percent,
            'pattern': self.params.pattern,
        }

        flight_plan = FlightPlan(
            waypoints=final_waypoints,
            survey_area=survey_polygon,
            estimated_flight_time_sec=flight_time_sec,
            estimated_distance_m=total_distance,
            estimated_num_photos=num_photos,
            summary=summary
        )
        
        logging.info(f"Flight plan generated in {time.time() - start_time:.2f}s.")
        logging.info(f"  - Estimated Distance: {total_distance / 1000:.2f} km")
        logging.info(f"  - Estimated Time: {flight_time_sec / 60:.2f} min")
        logging.info(f"  - Estimated Photos: {num_photos}")

        return flight_plan

    def export_to_mavlink_plan(self, flight_plan: FlightPlan, output_path: str):
        """Exports the flight plan to a MAVLink `.plan` file (JSON format)."""
        logging.info(f"Exporting to MAVLink plan file: {output_path}")
        
        # MAVLink plan file structure
        plan_data = {
            "fileType": "Plan",
            "geoFence": {"polygon": [], "version": 1},
            "groundStation": "QGroundControl",
            "mission": {
                "cruiseSpeed": self.drone.speed_mps,
                "firmwareType": 12, # 12 for PX4
                "hoverSpeed": 5.0,
                "items": [],
                "plannedHomePosition": [flight_plan.waypoints[0].latitude, flight_plan.waypoints[0].longitude, flight_plan.waypoints[0].altitude_msl],
                "vehicleType": 2, # 2 for VTOL
                "version": 2
            },
            "rallyPoints": {"points": [], "version": 1},
            "version": 1
        }

        # Add waypoints
        for i, wp in enumerate(flight_plan.waypoints):
            item = {
                "autoContinue": True,
                "command": 16, # MAV_CMD_NAV_WAYPOINT
                "doJumpId": i + 1,
                "frame": 3, # FRAME_GLOBAL_REL_ALT
                "params": [0, 0, 0, np.nan, wp.latitude, wp.longitude, wp.altitude_msl],
                "type": "SimpleItem"
            }
            plan_data["mission"]["items"].append(item)
            
            # Add camera trigger action
            if any(action['type'] == 'take_photo' for action in wp.actions):
                trigger_item = {
                    "autoContinue": True,
                    "command": 2000, # MAV_CMD_IMAGE_START_CAPTURE
                    "doJumpId": i + 1000, # Just needs to be unique
                    "frame": 2,
                    "params": [0, 0, 1, 0, 0, 0, 0], # Capture one image
                    "type": "SimpleItem"
                }
                plan_data["mission"]["items"].append(trigger_item)

        import json
        with open(output_path, 'w') as f:
            json.dump(plan_data, f, indent=4)
        logging.info("Export complete.")


# --- Example Usage ---

if __name__ == '__main__':
    logging.info("--- Running Flight Planning Demo ---")

    # 1. Define inputs
    camera = Camera(
        name="Sony a7R IV",
        sensor_width_mm=35.7, sensor_height_mm=23.8,
        focal_length_mm=35,
        image_width_px=9504, image_height_px=6336
    )
    drone = Drone(name="DJI Matrice 300", speed_mps=15, max_flight_time_min=45)
    params = FlightParameters(
        gsd_cm=2.0,
        sidelap_percent=70,
        frontlap_percent=80,
        pattern='boustrophedon'
    )

    # 2. Create a survey area (a simple square for demo)
    survey_poly = Polygon([(0, 0), (0, 500), (500, 500), (500, 0), (0, 0)])
    # Create a GeoDataFrame with a projected CRS (e.g., UTM)
    survey_gdf = gpd.GeoDataFrame([1], geometry=[survey_poly], crs="EPSG:32632")

    # 3. Initialize and run the planner
    planner = FlightPlanner(survey_gdf, camera, drone, params)
    flight_plan = planner.generate_flight_plan()

    # 4. Export the plan
    output_dir = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'data', 'flight_plans')
    os.makedirs(output_dir, exist_ok=True)
    plan_file_path = os.path.join(output_dir, 'demo_flight_plan.plan')
    planner.export_to_mavlink_plan(flight_plan, plan_file_path)

    logging.info(f"--- Demo Complete. Plan saved to {plan_file_path} ---")
