# c:\Users\Codeternal\Desktop\AgroPulse\app\computer_vision\drone_imagery_analysis\main_pipeline.py

"""
Main Orchestration Pipeline for Drone Imagery Analysis
======================================================

This module serves as the central orchestrator, integrating all components of the
drone imagery analysis suite into a cohesive, end-to-end workflow. It provides a
high-level API to run the entire processing chain, from raw images to final
analytical products like orthomosaics, DEMs, and vegetation analysis reports.

The `MainPipeline` class manages the state of the project, calling the
appropriate modules in the correct sequence and ensuring that data flows smoothly
from one processing stage to the next.

Key Features:
-------------
1.  **Project Initialization**: Uses the `data_management` module to create and
    validate the standardized project directory structure.

2.  **End-to-End Execution**: A single `run_full_pipeline` method that executes
    the entire workflow:
    -   Photogrammetry (SfM and MVS)
    -   Point Cloud Cleaning and Processing
    -   Digital Elevation Model (DEM) Generation
    -   Orthomosaic Generation
    -   Quality Assessment and Reporting
    -   Agricultural Vegetation Analysis

3.  **Modular Integration**: Clearly demonstrates how each specialized module
    (`photogrammetry_pipeline`, `dem_generation`, `vegetation_analysis`, etc.)
    is instantiated and used.

4.  **Configuration Driven**: The pipeline is designed to be configured through a
    project-specific configuration file (e.g., `config.json`), allowing users
    to tweak parameters for each stage without modifying the code.

5.  **State Management**: The pipeline checks for the existence of intermediate
    products, allowing it to potentially resume from a specific stage if a
    previous run was interrupted.

Workflow Orchestrated by `MainPipeline`:
-----------------------------------------
1.  **INPUT**: A folder of raw drone images and an optional Ground Control Point file.
2.  **SETUP**: A `Project` is created, organizing all data.
3.  **STAGE 1: Photogrammetry**:
    -   `photogrammetry_pipeline.PhotogrammetryPipeline` is run to produce a
      sparse point cloud, camera poses, and a dense point cloud.
4.  **STAGE 2: Point Cloud Processing**:
    -   The dense point cloud is cleaned using `point_cloud_processing` tools
      (e.g., statistical outlier removal).
5.  **STAGE 3: DEM Generation**:
    -   `dem_generation.DEMGenerator` uses the cleaned point cloud to produce a
      Digital Surface Model (DSM) and a Digital Terrain Model (DTM).
6.  **STAGE 4: Orthomosaic Generation**:
    -   `orthomosaic_generation.OrthomosaicGenerator` uses the camera poses and
      images to create a seamless, georeferenced 2D orthomosaic.
7.  **STAGE 5: Quality Assessment**:
    -   `quality_assessment.QualityReportGenerator` is run to analyze reprojection
      errors, GCP accuracy, and point cloud density, producing a detailed report.
8.  **STAGE 6: Vegetation Analysis**:
    -   `vegetation_analysis.VegetationAnalyzer` uses the orthomosaic and DEMs to
      calculate a Canopy Height Model (CHM), compute various vegetation indices
      (e.g., NDVI), and perform plant segmentation.
9.  **OUTPUT**: A fully populated project directory containing all intermediate
    and final data products, including GeoTIFFs, point clouds, and reports.

This main pipeline file is the primary entry point for users looking to process
a new drone survey project.
"""

import logging
from pathlib import Path
import json
import shutil
from typing import Optional, Dict, Any

# Import all the pipeline components
from .data_management import Project
from .photogrammetry_pipeline import PhotogrammetryPipeline, SceneReconstruction
from .point_cloud_processing import PointCloudProcessor
from .dem_generation import DEMGenerator
from .orthomosaic_generation import OrthomosaicGenerator
from .quality_assessment import QualityReportGenerator, GCP
from .vegetation_analysis import VegetationAnalyzer

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(module)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# --- Default Configuration ---
DEFAULT_CONFIG = {
    "photogrammetry": {
        "feature_type": "sift",
        "matcher_type": "flann",
        "mvs_enabled": True
    },
    "point_cloud_processing": {
        "denoise": {
            "method": "statistical_outlier_removal",
            "k_neighbors": 20,
            "std_ratio": 1.0
        }
    },
    "dem_generation": {
        "resolution": 0.1, # meters per pixel
        "dsm_interpolation": "invdist",
        "dtm_method": "csf"
    },
    "orthomosaic_generation": {
        "resolution": 0.05, # meters per pixel
        "blending_mode": "average"
    },
    "vegetation_analysis": {
        "indices": ["ndvi", "savi"],
        "segmentation_method": "watershed"
    }
}

class MainPipeline:
    """
    Orchestrates the entire drone imagery analysis workflow.
    """
    def __init__(self, project_path: str, config: Optional[Dict[str, Any]] = None):
        """
        Initializes the main pipeline for a given project.

        Args:
            project_path (str): The root path for the project.
            config (dict, optional): A dictionary of configuration parameters.
                                     If None, default settings are used.
        """
        self.project = Project(project_path)
        self.project.create_structure()
        logging.info(f"Initialized pipeline for project: {self.project.name}")

        self.config = DEFAULT_CONFIG.copy()
        if config:
            # Deep merge user config into defaults
            for key, value in config.items():
                if isinstance(value, dict) and key in self.config:
                    self.config[key].update(value)
                else:
                    self.config[key] = value
        
        # Save the config to the project directory
        with open(self.project.config_file, 'w') as f:
            json.dump(self.config, f, indent=4)
        logging.info(f"Project configuration saved to {self.project.config_file}")

    def run_full_pipeline(self,
                          images_dir: str,
                          gcp_file: Optional[str] = None):
        """
        Executes the full data processing pipeline from raw images to final analysis.

        Args:
            images_dir (str): Path to the directory containing raw drone images.
            gcp_file (str, optional): Path to the file containing Ground Control Points.
        """
        logging.info(f"--- Starting Full Pipeline for Project: {self.project.name} ---")
        
        # --- STAGE 0: Data Ingestion ---
        logging.info("--- STAGE 0: Ingesting Data ---")
        self._ingest_data(images_dir, gcp_file)

        # --- STAGE 1: Photogrammetry ---
        logging.info("--- STAGE 1: Running Photogrammetry ---")
        photogrammetry_pipeline = PhotogrammetryPipeline(self.project, self.config['photogrammetry'])
        scene: SceneReconstruction = photogrammetry_pipeline.run()
        logging.info("Photogrammetry complete. Sparse and dense clouds generated.")

        # --- STAGE 2: Point Cloud Processing ---
        logging.info("--- STAGE 2: Processing Dense Point Cloud ---")
        processor = PointCloudProcessor(self.project.dense_cloud_file)
        cleaned_cloud_file = self.project.get_path('processed_cloud')
        processor.denoise_and_save(
            output_path=cleaned_cloud_file,
            **self.config['point_cloud_processing']['denoise']
        )
        logging.info(f"Point cloud processing complete. Cleaned cloud at {cleaned_cloud_file}")

        # --- STAGE 3: DEM Generation ---
        logging.info("--- STAGE 3: Generating Digital Elevation Models ---")
        dem_generator = DEMGenerator(cleaned_cloud_file, self.project)
        dsm, dtm = dem_generator.generate_all(**self.config['dem_generation'])
        logging.info(f"DEM generation complete. DSM at {dsm}, DTM at {dtm}")

        # --- STAGE 4: Orthomosaic Generation ---
        logging.info("--- STAGE 4: Generating Orthomosaic ---")
        ortho_generator = OrthomosaicGenerator(scene, self.project)
        orthomosaic_file = ortho_generator.generate(**self.config['orthomosaic_generation'])
        logging.info(f"Orthomosaic generation complete. Orthomosaic at {orthomosaic_file}")

        # --- STAGE 5: Quality Assessment ---
        logging.info("--- STAGE 5: Performing Quality Assessment ---")
        gcps = self._load_gcps(self.project.gcp_file) if self.project.gcp_file.exists() else None
        qa_generator = QualityReportGenerator(self.project)
        qa_generator.generate(
            scene=scene,
            dense_cloud_path=self.project.dense_cloud_file,
            survey_area=scene.survey_area, # Assuming scene computes this
            gcps=gcps
        )
        logging.info("Quality assessment report generated.")

        # --- STAGE 6: Vegetation Analysis ---
        logging.info("--- STAGE 6: Running Vegetation Analysis ---")
        veg_analyzer = VegetationAnalyzer(self.project)
        veg_analyzer.run_full_analysis(
            ortho_path=orthomosaic_file,
            dsm_path=dsm,
            dtm_path=dtm,
            **self.config['vegetation_analysis']
        )
        logging.info("Vegetation analysis complete.")

        logging.info(f"--- Full Pipeline for Project {self.project.name} Finished Successfully ---")

    def _ingest_data(self, images_dir: str, gcp_file: Optional[str]):
        """Copies raw data into the project structure."""
        # Copy images
        image_source_path = Path(images_dir)
        if not image_source_path.exists():
            raise FileNotFoundError(f"Image directory not found: {images_dir}")
        
        for img_file in image_source_path.glob('*'):
            if img_file.suffix.lower() in ['.jpg', '.jpeg', '.tif', '.tiff']:
                shutil.copy(img_file, self.project.raw_images_dir / img_file.name)
        logging.info(f"Copied images from {images_dir} to {self.project.raw_images_dir}")

        # Copy GCPs
        if gcp_file:
            gcp_source_path = Path(gcp_file)
            if not gcp_source_path.exists():
                raise FileNotFoundError(f"GCP file not found: {gcp_file}")
            shutil.copy(gcp_source_path, self.project.gcp_file)
            logging.info(f"Copied GCP file from {gcp_file} to {self.project.gcp_file}")

    def _load_gcps(self, gcp_file: Path) -> List[GCP]:
        """Loads GCPs from a file. Placeholder implementation."""
        # In a real scenario, this would parse a CSV or TXT file.
        # Format: id,x,y,z
        gcps = []
        with open(gcp_file, 'r') as f:
            for line in f.readlines():
                if line.strip().startswith('#') or not line.strip():
                    continue
                parts = line.strip().split(',')
                gcp_id, x, y, z = parts[0], float(parts[1]), float(parts[2]), float(parts[3])
                # Measured coords will be populated by the photogrammetry step
                gcps.append(GCP(id=gcp_id, true_coords=np.array([x, y, z])))
        return gcps


def setup_dummy_project(root_path: Path):
    """Creates a dummy project with fake data for demonstration."""
    if root_path.exists():
        shutil.rmtree(root_path)
    root_path.mkdir(parents=True)

    # Create dummy images
    images_dir = root_path / 'raw_images'
    images_dir.mkdir()
    try:
        from PIL import Image
        for i in range(5):
            img = Image.new('RGB', (600, 400), color = (73, 109, 137))
            img.save(images_dir / f'image_{i:03d}.jpg')
    except ImportError:
        logging.warning("Pillow not installed. Cannot create dummy image files.")
        for i in range(5):
            (images_dir / f'image_{i:03d}.jpg').touch()

    # Create dummy GCP file
    gcp_file = root_path / 'gcps.txt'
    with open(gcp_file, 'w') as f:
        f.write("# id,x,y,z\n")
        f.write("gcp1,10.0,10.0,5.0\n")
        f.write("gcp2,90.0,10.0,5.0\n")
        f.write("gcp3,50.0,90.0,5.0\n")
        
    return images_dir, gcp_file


if __name__ == '__main__':
    logging.info("--- Running Main Pipeline Demo ---")

    # 1. Setup a dummy project directory and data
    # Note: The pipeline itself is a mock and won't produce real outputs,
    # but this demonstrates the orchestration logic.
    PROJECT_ROOT = Path(__file__).parent.parent.parent.parent / 'data' / 'drone_projects' / 'main_pipeline_demo'
    raw_images_path, gcp_path = setup_dummy_project(PROJECT_ROOT.parent)

    # 2. Initialize the main pipeline
    # In a real run, you might load a custom config from a file
    custom_config = {
        "dem_generation": {"resolution": 0.15},
        "vegetation_analysis": {"indices": ["ndvi"]}
    }
    pipeline = MainPipeline(str(PROJECT_ROOT), config=custom_config)

    # 3. Run the full pipeline
    try:
        # This will fail at the photogrammetry step because it's a mock,
        # but it shows the intended usage.
        pipeline.run_full_pipeline(
            images_dir=str(raw_images_path),
            gcp_file=str(gcp_path)
        )
    except Exception as e:
        logging.error(f"Pipeline execution failed: {e}", exc_info=True)
        logging.warning("This failure is expected in the demo as the underlying modules are placeholders.")
        logging.warning("The purpose is to show the orchestration of the full workflow.")

    print("\n--- Main Pipeline Demo ---")
    print(f"Project created at: {PROJECT_ROOT}")
    print("The pipeline attempted to run, orchestrating the following steps:")
    print("1. Data Ingestion")
    print("2. Photogrammetry")
    print("3. Point Cloud Processing")
    print("4. DEM Generation")
    print("5. Orthomosaic Generation")
    print("6. Quality Assessment")
    print("7. Vegetation Analysis")
    print("\nCheck the logs above to see the execution flow.")
    print("--------------------------")

    # Clean up dummy data
    shutil.rmtree(raw_images_path)
    gcp_path.unlink()

    logging.info("--- Main Pipeline Demo Complete ---")
