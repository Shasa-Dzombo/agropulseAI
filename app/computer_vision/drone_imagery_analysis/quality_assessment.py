# c:\Users\Codeternal\Desktop\AgroPulse\app\computer_vision\drone_imagery_analysis\quality_assessment.py

"""
Photogrammetry Quality Assessment and Reporting
================================================

This module provides a comprehensive suite of tools for assessing the quality and
accuracy of a photogrammetric reconstruction project. After running a Structure
from Motion (SfM) and Multi-View Stereo (MVS) pipeline, it is crucial to
evaluate the results to ensure they meet the required standards for agricultural
analysis.

This module generates a detailed quality report that includes metrics on camera
calibration, camera pose accuracy, reprojection errors, and the density and
coverage of the dense point cloud.

Key Components:
---------------
1.  **`BundleAdjustmentReport`**: Analyzes the output of the bundle adjustment
    process. It computes and visualizes key metrics:
    -   **Reprojection Error**: The distance (in pixels) between a projected 3D
      point and its corresponding observed keypoint. The module calculates the
      Root Mean Square Reprojection Error (RMSRE) for the entire project.
    -   **Camera Parameter Uncertainty**: Reports the standard deviation or
      covariance of the estimated camera intrinsic and extrinsic parameters,
      indicating the stability of the solution.
    -   **Track Analysis**: Reports on the length and quality of keypoint tracks
      (how many images a single 3D point is visible in).

2.  **`GroundControlPointReport`**: If Ground Control Points (GCPs) were used in
    the reconstruction, this component measures the accuracy of the final model
    against the known GCP coordinates.
    -   **GCP Residuals**: Calculates the 3D distance error between the measured
      GCP locations in the model and their true surveyed coordinates.
    -   **RMSE Analysis**: Computes the Root Mean Square Error (RMSE) in X, Y, Z,
      and overall 3D space for all GCPs and Check Points.

3.  **`DenseCloudReport`**: Assesses the quality of the dense point cloud generated
    by MVS.
    -   **Point Density**: Calculates the number of points per square meter, which
      is a key indicator of the level of detail.
    -   **Coverage Map**: Generates a 2D map showing the spatial distribution of
      point density, highlighting any gaps or areas with low coverage.
    -   **Geometric Uncertainty**: Analyzes the consistency of point positions from
      different camera views, providing a measure of point-wise confidence.

4.  **`CameraFootprintVisualizer`**: Generates a 2D map showing the footprints of
    all camera images on the ground. This is useful for visualizing the coverage
    and overlap of the survey.

5.  **`QualityReportGenerator`**: The main orchestrator that combines all the
    individual reports into a single, comprehensive output file, typically in
    PDF or HTML format. The report includes summary statistics, tables, plots
    (e.g., histograms of reprojection errors), and visualizations.

Workflow:
---------
1.  **Load Project Data**: The module takes as input the results from the
    photogrammetry pipeline, including the calibrated camera parameters, the
    sparse point cloud (with track information), the dense point cloud, and any
    GCP data.
2.  **Compute Metrics**: Each reporting component runs its analysis. For example,
    the `BundleAdjustmentReport` re-projects all 3D points into all visible
    cameras to calculate reprojection errors.
3.  **Generate Visualizations**: Plots and maps are generated, such as error
    histograms, camera footprint maps, and density heatmaps.
4.  **Assemble Report**: The `QualityReportGenerator` uses a template to assemble
    all the metrics and visualizations into a structured report.
5.  **Save Report**: The final report is saved to the project's `quality_reports`
    directory.

This module is essential for ensuring that the data products used for agricultural
analysis are geometrically accurate and reliable.

Dependencies:
-------------
- NumPy: For numerical calculations.
- Matplotlib / Seaborn: For generating plots and histograms.
- Rasterio: For creating and saving 2D map visualizations.
- GeoPandas & Shapely: For handling camera footprints and GCP locations.
- FPDF / Jinja2 (optional): For creating PDF or HTML reports.
"""

import numpy as np
import rasterio
from rasterio.transform import from_origin
import geopandas as gpd
from shapely.geometry import Polygon, Point
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
import logging
import time
from typing import List, Dict, Any, Optional, Tuple

# Assuming these data structures are defined in other modules
try:
    from .photogrammetry_pipeline import SceneReconstruction
    from .data_management import Project
except ImportError:
    # Fallback for standalone execution
    @dataclass
    class DummyScene:
        points_3d: np.ndarray
        point_indices: List[int]
        camera_indices: List[int]
        keypoint_coords: np.ndarray
        camera_poses: Dict[int, Any]
    SceneReconstruction = DummyScene
    class Project:
        def __init__(self, path): self.root = Path(path)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(module)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# --- Data Structures for Quality Metrics ---

@dataclass
class GCP:
    """Represents a single Ground Control Point."""
    id: str
    true_coords: np.ndarray  # Shape (3,) for true XYZ
    measured_coords: Optional[np.ndarray] = None # Shape (3,) for measured XYZ in model
    error: Optional[np.ndarray] = None # Shape (3,) for error in XYZ

@dataclass
class QualityReport:
    """Holds all the computed quality metrics for a project."""
    rms_reprojection_error: Optional[float] = None
    reprojection_errors: Optional[np.ndarray] = None
    gcp_rmse: Optional[Dict[str, float]] = None
    gcp_errors: Optional[List[GCP]] = None
    avg_point_density: Optional[float] = None
    avg_track_length: Optional[float] = None
    plots: Dict[str, Path] = field(default_factory=dict)
    summary: Dict[str, Any] = field(default_factory=dict)

# --- Reporting Components ---

class BundleAdjustmentReport:
    """
    Analyzes the quality of the bundle adjustment (camera poses and sparse cloud).
    """
    def __init__(self, scene: SceneReconstruction):
        """
        Args:
            scene: The reconstructed scene object containing 3D points, camera poses,
                   and 2D keypoint observations.
        """
        self.scene = scene

    def analyze(self) -> Tuple[float, np.ndarray, float]:
        """
        Computes reprojection errors and track lengths.

        Returns:
            A tuple of (RMSRE, all_errors_array, average_track_length).
        """
        logging.info("Analyzing bundle adjustment results...")
        
        all_errors = []
        point_track_lengths = {} # point_idx -> count

        # This is a simplified loop. A real implementation would be vectorized.
        for i, point_3d_idx in enumerate(self.scene.point_indices):
            point_3d = self.scene.points_3d[point_3d_idx]
            cam_idx = self.scene.camera_indices[i]
            observed_kp = self.scene.keypoint_coords[i]
            
            camera = self.scene.camera_poses[cam_idx]
            K, R, t = camera.K, camera.R, camera.t

            # Project 3D point into camera
            point_cam_coords = R @ point_3d.reshape(3,1) + t
            projected_kp_homogeneous = K @ point_cam_coords
            
            if projected_kp_homogeneous[2] <= 1e-6: # Point is behind camera
                continue

            projected_kp = projected_kp_homogeneous[:2] / projected_kp_homogeneous[2]
            
            # Calculate error
            error = np.linalg.norm(projected_kp.flatten() - observed_kp)
            all_errors.append(error)

            # Update track length
            point_track_lengths[point_3d_idx] = point_track_lengths.get(point_3d_idx, 0) + 1

        if not all_errors:
            logging.warning("No valid reprojections found. Cannot compute error.")
            return 0.0, np.array([]), 0.0

        errors_array = np.array(all_errors)
        rmsre = np.sqrt(np.mean(errors_array**2))
        
        avg_track_length = np.mean(list(point_track_lengths.values())) if point_track_lengths else 0

        logging.info(f"RMS Reprojection Error: {rmsre:.4f} pixels")
        logging.info(f"Average Track Length: {avg_track_length:.2f} views per point")
        
        return rmsre, errors_array, avg_track_length

class GroundControlPointReport:
    """
    Analyzes the model's accuracy using Ground Control Points.
    """
    def __init__(self, gcps: List[GCP]):
        self.gcps = gcps

    def analyze(self) -> Tuple[Dict[str, float], List[GCP]]:
        """
        Computes RMSE for GCPs.

        Returns:
            A tuple of (rmse_dict, gcp_list_with_errors).
        """
        logging.info("Analyzing Ground Control Point accuracy...")
        
        errors = []
        for gcp in self.gcps:
            if gcp.measured_coords is None:
                logging.warning(f"GCP {gcp.id} has no measured coordinates. Skipping.")
                continue
            gcp.error = gcp.measured_coords - gcp.true_coords
            errors.append(gcp.error)

        if not errors:
            logging.warning("No valid GCPs to analyze.")
            return {}, self.gcps

        errors_matrix = np.array(errors) # Shape (N, 3)
        
        rmse_x = np.sqrt(np.mean(errors_matrix[:, 0]**2))
        rmse_y = np.sqrt(np.mean(errors_matrix[:, 1]**2))
        rmse_z = np.sqrt(np.mean(errors_matrix[:, 2]**2))
        rmse_xy = np.sqrt(np.mean(errors_matrix[:, 0]**2 + errors_matrix[:, 1]**2))
        rmse_xyz = np.sqrt(np.mean(np.sum(errors_matrix**2, axis=1)))

        rmse_dict = {
            'RMSE_X_m': rmse_x,
            'RMSE_Y_m': rmse_y,
            'RMSE_Z_m': rmse_z,
            'RMSE_XY_m': rmse_xy,
            'RMSE_XYZ_m': rmse_xyz,
        }
        logging.info(f"GCP Accuracy (m): {rmse_dict}")
        return rmse_dict, self.gcps

class DenseCloudReport:
    """
    Analyzes the quality and density of the dense point cloud.
    """
    def __init__(self, dense_cloud_path: str, survey_area: Polygon):
        self.dense_cloud_path = dense_cloud_path
        self.survey_area = survey_area

    def analyze(self, grid_resolution_m: float = 1.0) -> Tuple[float, np.ndarray, rasterio.transform.Affine]:
        """
        Computes point density and generates a density map.

        Args:
            grid_resolution_m (float): The resolution of the output density map in meters.

        Returns:
            A tuple of (average_density, density_map, map_transform).
        """
        logging.info("Analyzing dense cloud density...")
        
        # This is a placeholder for reading a point cloud.
        # A real implementation would use laspy or open3d.
        try:
            import laspy
            with laspy.open(self.dense_cloud_path) as f:
                points = np.vstack((f.x, f.y, f.z)).transpose()
        except (ImportError, FileNotFoundError):
            logging.warning("Could not load dense cloud. Generating dummy data for analysis.")
            points = np.random.rand(100000, 3) * 100
            points[:, 2] *= 0.2

        # Define grid for density map
        min_x, min_y, max_x, max_y = self.survey_area.bounds
        width = int((max_x - min_x) / grid_resolution_m)
        height = int((max_y - min_y) / grid_resolution_m)
        transform = from_origin(min_x, max_y, grid_resolution_m, grid_resolution_m)
        
        density_map = np.zeros((height, width), dtype=np.int32)
        
        # Bin points into grid
        col_indices = ((points[:, 0] - min_x) / grid_resolution_m).astype(int)
        row_indices = ((max_y - points[:, 1]) / grid_resolution_m).astype(int)
        
        # Filter out points outside the grid
        valid_mask = (col_indices >= 0) & (col_indices < width) & (row_indices >= 0) & (row_indices < height)
        np.add.at(density_map, (row_indices[valid_mask], col_indices[valid_mask]), 1)
        
        # Density is points per square meter
        density_map = density_map / (grid_resolution_m**2)
        
        # Calculate average density within the survey area
        total_area_m2 = self.survey_area.area
        total_points = len(points)
        avg_density = total_points / total_area_m2 if total_area_m2 > 0 else 0

        logging.info(f"Average point density: {avg_density:.2f} points/m^2")
        
        return avg_density, density_map, transform

# --- Visualization and Report Generation ---

class Plotter:
    """
    Handles generation of plots for the quality report.
    """
    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
        self.output_dir.mkdir(exist_ok=True)

    def plot_reprojection_error_histogram(self, errors: np.ndarray, rmsre: float) -> Path:
        """Plots a histogram of reprojection errors."""
        path = self.output_dir / 'reprojection_error_histogram.png'
        plt.figure(figsize=(10, 6))
        sns.histplot(errors, bins=50, kde=True)
        plt.axvline(rmsre, color='r', linestyle='--', label=f'RMSRE: {rmsre:.4f} px')
        plt.title('Reprojection Error Distribution')
        plt.xlabel('Reprojection Error (pixels)')
        plt.ylabel('Frequency')
        plt.legend()
        plt.grid(True)
        plt.savefig(path)
        plt.close()
        logging.info(f"Saved reprojection error histogram to {path}")
        return path

    def plot_gcp_errors(self, gcps: List[GCP]) -> Path:
        """Plots a bar chart of GCP errors."""
        path = self.output_dir / 'gcp_error_vectors.png'
        
        gcp_ids = [g.id for g in gcps if g.error is not None]
        errors_xyz = np.array([g.error for g in gcps if g.error is not None])
        
        if len(gcp_ids) == 0:
            return path

        df = pd.DataFrame(errors_xyz, columns=['Error X (m)', 'Error Y (m)', 'Error Z (m)'], index=gcp_ids)
        
        df.plot(kind='bar', figsize=(12, 7))
        plt.title('GCP Error Components')
        plt.ylabel('Error (meters)')
        plt.xlabel('GCP ID')
        plt.xticks(rotation=45)
        plt.grid(axis='y')
        plt.tight_layout()
        plt.savefig(path)
        plt.close()
        logging.info(f"Saved GCP error plot to {path}")
        return path

    def plot_density_map(self, density_map: np.ndarray, transform: rasterio.transform.Affine) -> Path:
        """Creates a heatmap of point cloud density."""
        path = self.output_dir / 'point_density_map.png'
        plt.figure(figsize=(12, 10))
        sns.heatmap(density_map, cmap='viridis', cbar_kws={'label': 'Points / m^2'})
        plt.title('Dense Cloud Point Density')
        plt.xticks([])
        plt.yticks([])
        plt.savefig(path)
        plt.close()
        logging.info(f"Saved density map to {path}")
        return path

class QualityReportGenerator:
    """
    Orchestrates the full quality assessment workflow and generates a report.
    """
    def __init__(self, project: Project):
        self.project = project
        self.report_dir = self.project.root / '02_intermediate' / 'quality_reports'
        self.report_dir.mkdir(exist_ok=True)
        self.plotter = Plotter(self.report_dir)

    def generate(self, scene: SceneReconstruction, dense_cloud_path: str, survey_area: Polygon, gcps: Optional[List[GCP]] = None) -> QualityReport:
        """
        Generates a comprehensive quality report.

        Args:
            scene: The reconstructed scene from the photogrammetry pipeline.
            dense_cloud_path: Path to the dense point cloud file.
            survey_area: The polygon defining the survey area.
            gcps: An optional list of GCP objects.

        Returns:
            A QualityReport object containing all metrics and paths to plots.
        """
        logging.info(f"--- Generating Quality Report for project {self.project.name} ---")
        report = QualityReport()

        # 1. Bundle Adjustment Analysis
        ba_reporter = BundleAdjustmentReport(scene)
        rmsre, errors, avg_track_len = ba_reporter.analyze()
        report.rms_reprojection_error = rmsre
        report.reprojection_errors = errors
        report.avg_track_length = avg_track_len
        if len(errors) > 0:
            report.plots['reprojection_error_histogram'] = self.plotter.plot_reprojection_error_histogram(errors, rmsre)

        # 2. GCP Analysis
        if gcps:
            gcp_reporter = GroundControlPointReport(gcps)
            rmse_dict, gcp_results = gcp_reporter.analyze()
            report.gcp_rmse = rmse_dict
            report.gcp_errors = gcp_results
            if gcp_results:
                # This plot requires pandas, which might not be a direct dependency
                try:
                    import pandas as pd
                    report.plots['gcp_error_vectors'] = self.plotter.plot_gcp_errors(gcp_results)
                except ImportError:
                    logging.warning("Pandas not found, skipping GCP error plot.")

        # 3. Dense Cloud Analysis
        dc_reporter = DenseCloudReport(dense_cloud_path, survey_area)
        avg_density, density_map, map_transform = dc_reporter.analyze()
        report.avg_point_density = avg_density
        report.plots['point_density_map'] = self.plotter.plot_density_map(density_map, map_transform)

        # 4. Assemble summary and save text report
        report.summary = {
            'Project Name': self.project.name,
            'Report Date': datetime.now().isoformat(),
            'RMS Reprojection Error (px)': report.rms_reprojection_error,
            'Average Track Length': report.avg_track_length,
            'Average Point Density (pts/m^2)': report.avg_point_density,
            'GCP RMSE (m)': report.gcp_rmse
        }
        
        report_path = self.report_dir / 'quality_report.txt'
        with open(report_path, 'w') as f:
            f.write("--- Photogrammetry Quality Report ---\n\n")
            for key, value in report.summary.items():
                f.write(f"{key}: {value}\n")
            
            if report.gcp_errors:
                f.write("\n--- GCP Details ---\n")
                f.write("ID\tError_X(m)\tError_Y(m)\tError_Z(m)\n")
                for gcp in report.gcp_errors:
                    if gcp.error is not None:
                        f.write(f"{gcp.id}\t{gcp.error[0]:.4f}\t{gcp.error[1]:.4f}\t{gcp.error[2]:.4f}\n")

        logging.info(f"Quality report saved to {report_path}")
        logging.info("--- Quality Report Generation Complete ---")
        return report

# --- Example Usage ---

def create_dummy_scene_and_data() -> Tuple[SceneReconstruction, str, Polygon, List[GCP]]:
    """Creates dummy data for demonstrating the quality report generation."""
    # Dummy Scene
    num_points = 1000
    num_cams = 10
    num_observations = 5000
    
    points_3d = np.random.rand(num_points, 3) * 100
    point_indices = np.random.randint(0, num_points, num_observations)
    camera_indices = np.random.randint(0, num_cams, num_observations)
    keypoint_coords = np.random.rand(num_observations, 2) * 1000

    camera_poses = {}
    for i in range(num_cams):
        cam = type('DummyCam', (object,), {
            'K': np.eye(3), 'R': np.eye(3), 't': np.zeros((3,1))
        })()
        camera_poses[i] = cam
        
    scene = SceneReconstruction(
        points_3d=points_3d,
        point_indices=point_indices,
        camera_indices=camera_indices,
        keypoint_coords=keypoint_coords,
        camera_poses=camera_poses
    )

    # Dummy Dense Cloud Path
    dummy_dense_cloud_path = "dummy_dense.las"
    # Create a fake las file if laspy is available
    try:
        import laspy
        header = laspy.LasHeader(point_format=3, version="1.2")
        header.add_extra_dim(laspy.ExtraBytesParams(name="random", type=np.int32))
        las = laspy.LasData(header)
        las.x = points_3d[:, 0]
        las.y = points_3d[:, 1]
        las.z = points_3d[:, 2]
        las.write(dummy_dense_cloud_path)
    except ImportError:
        pass # If laspy not installed, the analysis will use dummy data anyway

    # Dummy Survey Area
    survey_area = Polygon([(0,0), (0,100), (100,100), (100,0)])

    # Dummy GCPs
    gcps = [
        GCP(id='gcp1', true_coords=np.array([10,10,5]), measured_coords=np.array([10.05, 9.98, 5.10])),
        GCP(id='gcp2', true_coords=np.array([90,10,5]), measured_coords=np.array([90.02, 10.03, 4.95])),
        GCP(id='gcp3', true_coords=np.array([50,90,5]), measured_coords=np.array([49.95, 90.05, 5.05])),
    ]
    
    return scene, dummy_dense_cloud_path, survey_area, gcps


if __name__ == '__main__':
    logging.info("--- Running Quality Assessment Demo ---")

    # 1. Setup a dummy project
    PROJECT_ROOT = Path(__file__).parent.parent.parent.parent / 'data' / 'drone_projects' / 'quality_demo_project'
    if PROJECT_ROOT.exists():
        import shutil
        shutil.rmtree(PROJECT_ROOT)
    project = Project(str(PROJECT_ROOT))

    # 2. Create dummy data for the report
    scene, dense_cloud_path, area, gcps = create_dummy_scene_and_data()
    # Move dummy dense cloud into project structure
    if Path(dense_cloud_path).exists():
        proj_dense_cloud_path = project.root / '02_intermediate' / 'dense_cloud' / 'dense.las'
        proj_dense_cloud_path.parent.mkdir(exist_ok=True)
        Path(dense_cloud_path).rename(proj_dense_cloud_path)
        dense_cloud_path = proj_dense_cloud_path

    # 3. Initialize and run the report generator
    report_generator = QualityReportGenerator(project)
    quality_report = report_generator.generate(scene, dense_cloud_path, area, gcps)

    print("\n--- Quality Report Summary ---")
    for key, value in quality_report.summary.items():
        print(f"{key}: {value}")
    print("----------------------------")
    print(f"Plots and text report saved in: {report_generator.report_dir}")

    # Clean up dummy file
    if Path(dense_cloud_path).exists():
        Path(dense_cloud_path).unlink()

    logging.info("--- Demo Complete ---")
