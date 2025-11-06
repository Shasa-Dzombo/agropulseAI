"""
Drone Imagery Analysis Package
==============================

This package provides a comprehensive suite of tools for processing drone-captured
imagery to generate high-value data products for agricultural and environmental
monitoring. It covers the entire workflow from flight planning to final analysis.

Main Components:
----------------

- `MainPipeline`:
  The primary entry point for running the end-to-end processing workflow. It
  orchestrates all other modules in the correct sequence.

- `Project`:
  A data management class from the `data_management` module that handles the
  creation and organization of a standardized project directory structure.

- `PhotogrammetryPipeline`:
  Implements the core Structure from Motion (SfM) and Multi-View Stereo (MVS)
  algorithms to reconstruct a 3D scene from 2D images.

- `DEMGenerator`:
  Generates Digital Elevation Models (DSMs) and Digital Terrain Models (DTMs)
  from dense point clouds.

- `OrthomosaicGenerator`:
  Creates seamless, georeferenced 2D orthomosaics by stitching together
  ortho-rectified images.

- `VegetationAnalyzer`:
  Performs agricultural-specific analyses, such as calculating vegetation
  indices (e.g., NDVI), creating Canopy Height Models (CHMs), and segmenting
  individual plants.

- `QualityReportGenerator`:
  Assesses the geometric accuracy and quality of the reconstruction and
  generates detailed reports.

- `FlightPlanner`:
  Tools for generating optimal flight paths for drone surveys based on
  user-defined parameters like Ground Sample Distance (GSD) and overlap.

- `ChangeDetector`:
  Provides methods for detecting and quantifying changes between two datasets
  of the same area captured at different times.

- `PointCloudProcessor`:
  A set of tools for cleaning, filtering, and analyzing dense point clouds.

Example Usage:
--------------
To process a new project, the typical workflow involves using the `MainPipeline`:

```python
from app.computer_vision.drone_imagery_analysis import MainPipeline

# Define the path for the new project
project_path = "/path/to/my_drone_project"

# Initialize the main pipeline
pipeline = MainPipeline(project_path)

# Run the entire workflow on a directory of raw images
pipeline.run_full_pipeline(
    images_dir="/path/to/raw_images",
    gcp_file="/path/to/gcp_coordinates.txt"  # Optional
)
```
"""

# Expose the main entry points and data structures for easier access.
# This allows users to import them directly from the package.

# The main orchestrator
from .main_pipeline import MainPipeline

# Core data management class
from .data_management import Project

# Individual pipeline stages and tools
from .photogrammetry_pipeline import PhotogrammetryPipeline
from .dem_generation import DEMGenerator
from .orthomosaic_generation import OrthomosaicGenerator
from .vegetation_analysis import VegetationAnalyzer
from .quality_assessment import QualityReportGenerator, GCP
from .point_cloud_processing import PointCloudProcessor
from .flight_planning import FlightPlanner
from .change_detection import ChangeDetector

# Data structures that might be useful for users
from .photogrammetry_pipeline import SceneReconstruction

__all__ = [
    # High-level API
    "MainPipeline",
    "Project",

    # Individual Components
    "PhotogrammetryPipeline",
    "DEMGenerator",
    "OrthomosaicGenerator",
    "VegetationAnalyzer",
    "QualityReportGenerator",
    "PointCloudProcessor",
    "FlightPlanner",
    "ChangeDetector",

    # Data Structures
    "GCP",
    "SceneReconstruction",
]

__version__ = "0.1.0"
    FlightPathVisualizer,
)

__all__ = [
    # photogrammetry_pipeline
    "PhotogrammetryPipeline",
    "KeypointExtractor",
    "FeatureMatcher",
    "BundleAdjuster",
    "DenseReconstructor",
    # orthomosaic_generation
    "OrthomosaicGenerator",
    "SeamlineOptimizer",
    "ColorBalancer",
    # dem_generation
    "PointCloudFilter",
    "DEMInterpolator",
    "DTMGenerator",
    # flight_planning
    "FlightPlanner",
    "Mission",
    "GridMission",
    "CorridorMission",
    "CircularMission",
    "TerrainFollower",
    # analytics_suite
    "PlantCounter",
    "CanopyCoverCalculator",
    "TopographicAnalyzer",
    "VolumeCalculator",
    # visualization
    "PointCloudVisualizer",
    "MeshVisualizer",
    "FlightPathVisualizer",
]
