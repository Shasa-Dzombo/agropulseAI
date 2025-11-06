# c:\Users\Codeternal\Desktop\AgroPulse\app\computer_vision\drone_imagery_analysis\data_management.py

"""
Data Management for Drone Imagery Projects
===========================================

This module provides a robust framework for managing the lifecycle of data in a
drone-based agricultural survey project. A typical project generates a large
volume of data, from raw images to intermediate files and final analytical products.
This module imposes a standardized structure and provides an API to create,
access, and manage these datasets, ensuring consistency, traceability, and ease of use.

The core concept is the `Project`, which represents a single survey campaign.
All data associated with that campaign is stored within a dedicated project
directory, organized into a predefined folder structure.

Key Components:
---------------
1.  **`Project` Class**: The main entry point for interacting with a survey project.
    It provides methods to:
    -   Create a new project with a standardized directory structure.
    -   Load an existing project.
    -   Access different data products through dedicated properties (e.g.,
      `project.raw_images`, `project.orthomosaic`).
    -   Manage project-level metadata, stored in a `project.json` file.

2.  **Standardized Directory Structure**: When a new project is created, the
    following structure is generated:
    ```
    <project_root>/
    ├── project.json
    ├── 01_raw_images/
    ├── 02_intermediate/
    │   ├── camera_poses/
    │   ├── dense_cloud/
    │   └── quality_reports/
    ├── 03_products/
    │   ├── orthomosaic/
    │   ├── dem/
    │   └── vegetation_indices/
    └── 04_analysis/
        ├── plant_metrics/
        ├── change_maps/
        └── flight_plans/
    ```

3.  **`DataManager` Classes**: A set of specialized classes to manage different
    types of data products. Each manager handles the reading, writing, and
    metadata associated with its data type.
    -   `ImageManager`: Manages raw imagery, including reading EXIF metadata.
    -   `PointCloudManager`: Handles point clouds (PLY, LAS formats).
    -   `RasterManager`: A generic manager for geospatial rasters like DEMs,
      orthomosaics, and VI maps.
    -   `VectorManager`: Manages vector data like shapefiles (e.g., plant locations,
      survey boundaries).
    -   `MetadataManager`: Handles the reading and writing of the `project.json` file.

4.  **`DataProduct`**: A dataclass that represents a single data asset within the
    project. It contains the file path, data type, creation timestamp, and any
    relevant metadata (e.g., CRS, resolution).

5.  **`ProjectScanner`**: A utility to scan an existing project directory and
    populate the `Project` object with all available `DataProduct` instances,
    making it easy to work with projects that may have been partially processed.

This structured approach to data management is crucial for building scalable and
reproducible data processing pipelines. It decouples the processing logic in other
modules from the specifics of file paths and storage, allowing them to simply
request a data product (e.g., "get the DSM") from the `Project` object.

Dependencies:
-------------
- NumPy: For data manipulation.
- Rasterio: For reading/writing raster data.
- GeoPandas: For reading/writing vector data.
- Laspy: For point cloud I/O.
- Pillow (PIL): For reading image EXIF data.
- PyYAML or JSON: For metadata management.
"""

import os
import json
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional, Union
from dataclasses import dataclass, field, asdict

import rasterio
import geopandas as gpd
from PIL import Image
from PIL.ExifTags import TAGS

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(module)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# --- Data Structures ---

@dataclass
class DataProduct:
    """Represents a single data asset in a project."""
    name: str
    path: str
    data_type: str  # e.g., 'raw_image', 'orthomosaic', 'dsm', 'point_cloud', 'shapefile'
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)

# --- Manager Classes ---

class BaseManager:
    """Base class for data managers."""
    def __init__(self, project_root: Path):
        self.project_root = project_root

    def get_path(self, *args) -> Path:
        raise NotImplementedError

    def save(self, data: Any, name: str, **kwargs):
        raise NotImplementedError

    def load(self, name: str) -> Any:
        raise NotImplementedError

class MetadataManager(BaseManager):
    """Manages the project.json file."""
    def get_path(self) -> Path:
        return self.project_root / 'project.json'

    def save(self, metadata: Dict[str, Any]):
        """Saves the project metadata dictionary to project.json."""
        path = self.get_path()
        logging.info(f"Saving project metadata to {path}")
        with open(path, 'w') as f:
            json.dump(metadata, f, indent=4)

    def load(self) -> Dict[str, Any]:
        """Loads the project metadata from project.json."""
        path = self.get_path()
        if not path.exists():
            return {}
        logging.info(f"Loading project metadata from {path}")
        with open(path, 'r') as f:
            return json.load(f)

class ImageManager(BaseManager):
    """Manages raw images and their EXIF data."""
    def get_path(self) -> Path:
        return self.project_root / '01_raw_images'

    def list(self) -> List[DataProduct]:
        """Lists all raw images in the project."""
        image_dir = self.get_path()
        if not image_dir.exists():
            return []
        
        products = []
        for img_path in image_dir.glob('*.[jJ][pP][gG]'):
            metadata = self.read_exif(img_path)
            product = DataProduct(
                name=img_path.name,
                path=str(img_path),
                data_type='raw_image',
                created_at=datetime.fromtimestamp(img_path.stat().st_ctime).isoformat(),
                metadata=metadata
            )
            products.append(product)
        return products

    def read_exif(self, image_path: Path) -> Dict[str, Any]:
        """Reads and decodes EXIF data from an image."""
        try:
            with Image.open(image_path) as img:
                exif_data = img._getexif()
                if not exif_data:
                    return {}
                
                decoded_exif = {}
                for tag_id, value in exif_data.items():
                    tag = TAGS.get(tag_id, tag_id)
                    if isinstance(value, bytes):
                        try:
                            value = value.decode('utf-8', errors='ignore')
                        except Exception:
                            value = repr(value)
                    decoded_exif[str(tag)] = value
                return decoded_exif
        except Exception as e:
            logging.warning(f"Could not read EXIF data from {image_path}: {e}")
            return {}

class RasterManager(BaseManager):
    """Manages geospatial raster data products."""
    def __init__(self, project_root: Path, product_type: str):
        super().__init__(project_root)
        self.product_type = product_type
        self.base_dir = self._get_base_dir()

    def _get_base_dir(self) -> Path:
        """Determines the directory based on product type."""
        if self.product_type in ['orthomosaic', 'dsm', 'dtm', 'chm']:
            return self.project_root / '03_products' / self.product_type
        elif self.product_type in ['ndvi', 'ndre', 'gndvi']:
            return self.project_root / '03_products' / 'vegetation_indices'
        else:
            return self.project_root / '03_products' / 'other_rasters'

    def get_path(self, name: str) -> Path:
        """Gets the full path for a named raster product."""
        return self.base_dir / f"{name}.tif"

    def save(self, data: np.ndarray, name: str, profile: Dict[str, Any]):
        """Saves a raster dataset."""
        self.base_dir.mkdir(parents=True, exist_ok=True)
        path = self.get_path(name)
        logging.info(f"Saving {self.product_type} raster to {path}...")
        with rasterio.open(path, 'w', **profile) as dst:
            dst.write(data)

    def load(self, name: str) -> Tuple[np.ndarray, Dict[str, Any]]:
        """Loads a raster dataset and its profile."""
        path = self.get_path(name)
        if not path.exists():
            raise FileNotFoundError(f"Raster product '{name}' not found at {path}")
        logging.info(f"Loading {self.product_type} raster from {path}...")
        with rasterio.open(path) as src:
            return src.read(), src.profile

    def get_product(self, name: str) -> Optional[DataProduct]:
        """Gets a DataProduct representation of a raster."""
        path = self.get_path(name)
        if not path.exists():
            return None
        
        with rasterio.open(path) as src:
            metadata = {
                'crs': src.crs.to_string() if src.crs else None,
                'transform': list(src.transform),
                'width': src.width,
                'height': src.height,
                'count': src.count,
                'dtype': str(src.dtypes[0]),
            }
        
        return DataProduct(
            name=name,
            path=str(path),
            data_type=self.product_type,
            created_at=datetime.fromtimestamp(path.stat().st_ctime).isoformat(),
            metadata=metadata
        )

class VectorManager(BaseManager):
    """Manages vector data (e.g., shapefiles)."""
    def get_path(self, name: str, subfolder: str = 'plant_metrics') -> Path:
        return self.project_root / '04_analysis' / subfolder / f"{name}.shp"

    def save(self, gdf: gpd.GeoDataFrame, name: str, subfolder: str = 'plant_metrics'):
        """Saves a GeoDataFrame to a shapefile."""
        path = self.get_path(name, subfolder)
        path.parent.mkdir(parents=True, exist_ok=True)
        logging.info(f"Saving vector data to {path}...")
        gdf.to_file(path)

    def load(self, name: str, subfolder: str = 'plant_metrics') -> gpd.GeoDataFrame:
        """Loads a shapefile into a GeoDataFrame."""
        path = self.get_path(name, subfolder)
        if not path.exists():
            raise FileNotFoundError(f"Vector data '{name}' not found at {path}")
        logging.info(f"Loading vector data from {path}...")
        return gpd.read_file(path)

# --- Main Project Class ---

class Project:
    """
    Main class for managing a drone survey project.
    """
    PROJECT_DIRS = [
        '01_raw_images',
        '02_intermediate/camera_poses',
        '02_intermediate/dense_cloud',
        '02_intermediate/quality_reports',
        '03_products/orthomosaic',
        '03_products/dem',
        '03_products/vegetation_indices',
        '04_analysis/plant_metrics',
        '04_analysis/change_maps',
        '04_analysis/flight_plans',
    ]

    def __init__(self, project_path: str):
        self.root = Path(project_path)
        self.name = self.root.name
        self.metadata: Dict[str, Any] = {'name': self.name, 'created_at': datetime.now().isoformat(), 'products': {}}
        
        # Initialize managers
        self.meta_manager = MetadataManager(self.root)
        self.image_manager = ImageManager(self.root)
        self.vector_manager = VectorManager(self.root)
        
        # Raster managers for different product types
        self.ortho_manager = RasterManager(self.root, 'orthomosaic')
        self.dsm_manager = RasterManager(self.root, 'dsm')
        self.dtm_manager = RasterManager(self.root, 'dtm')
        self.chm_manager = RasterManager(self.root, 'chm')
        self.ndvi_manager = RasterManager(self.root, 'ndvi')

        if (self.root / 'project.json').exists():
            self._load_project()
        else:
            self._create_project()

    def _create_project(self):
        """Creates the project directory structure and initial metadata file."""
        logging.info(f"Creating new project: '{self.name}' at {self.root}")
        self.root.mkdir(parents=True, exist_ok=True)
        for d in self.PROJECT_DIRS:
            (self.root / d).mkdir(parents=True, exist_ok=True)
        self.save_metadata()

    def _load_project(self):
        """Loads an existing project's metadata."""
        logging.info(f"Loading existing project: '{self.name}'")
        self.metadata = self.meta_manager.load()

    def save_metadata(self):
        """Saves the current state of the project metadata."""
        self.meta_manager.save(self.metadata)

    def add_product(self, product: DataProduct):
        """Adds a data product to the project's metadata."""
        if product.data_type not in self.metadata['products']:
            self.metadata['products'][product.data_type] = []
        
        # Avoid duplicates
        self.metadata['products'][product.data_type] = [
            p for p in self.metadata['products'][product.data_type] if p['name'] != product.name
        ]
        self.metadata['products'][product.data_type].append(asdict(product))
        self.save_metadata()
        logging.info(f"Added product '{product.name}' of type '{product.data_type}' to project.")

    def get_product(self, name: str, data_type: str) -> Optional[DataProduct]:
        """Retrieves a data product by name and type."""
        if data_type in self.metadata['products']:
            for p_dict in self.metadata['products'][data_type]:
                if p_dict['name'] == name:
                    return DataProduct(**p_dict)
        return None

    def list_products(self, data_type: Optional[str] = None) -> List[DataProduct]:
        """Lists all products, optionally filtered by type."""
        products = []
        if data_type:
            if data_type in self.metadata['products']:
                products.extend([DataProduct(**p) for p in self.metadata['products'][data_type]])
        else:
            for dtype in self.metadata['products']:
                products.extend([DataProduct(**p) for p in self.metadata['products'][dtype]])
        return products

    def scan(self):
        """
        Scans the project directory to discover and register all existing data products.
        """
        logging.info("Scanning project directory for data products...")
        
        # Scan for raw images
        for img_product in self.image_manager.list():
            self.add_product(img_product)
            
        # Scan for raster products
        raster_managers = {
            'orthomosaic': self.ortho_manager,
            'dsm': self.dsm_manager,
            'dtm': self.dtm_manager,
            'chm': self.chm_manager,
            'ndvi': self.ndvi_manager,
        }
        for prod_type, manager in raster_managers.items():
            if manager.base_dir.exists():
                for tif_file in manager.base_dir.glob('*.tif'):
                    product = manager.get_product(tif_file.stem)
                    if product:
                        self.add_product(product)
        
        # Scan for vector products
        if self.vector_manager.get_path(name='*', subfolder='*').parent.exists():
            for shp_file in self.root.glob('04_analysis/**/*.shp'):
                product = DataProduct(
                    name=shp_file.stem,
                    path=str(shp_file),
                    data_type='shapefile',
                    created_at=datetime.fromtimestamp(shp_file.stat().st_ctime).isoformat(),
                    metadata={'crs': gpd.read_file(shp_file).crs.to_string()}
                )
                self.add_product(product)

        self.save_metadata()
        logging.info("Project scan complete.")

# --- Example Usage ---

if __name__ == '__main__':
    logging.info("--- Running Data Management Demo ---")

    # 1. Define project path
    PROJECT_ROOT = Path(__file__).parent.parent.parent.parent / 'data' / 'drone_projects' / 'field_A_2025-10-28'
    
    # Clean up previous demo run if it exists
    if PROJECT_ROOT.exists():
        import shutil
        logging.warning(f"Removing existing demo project at {PROJECT_ROOT}")
        shutil.rmtree(PROJECT_ROOT)

    # 2. Create a new project
    project = Project(str(PROJECT_ROOT))
    logging.info(f"Project '{project.name}' created.")
    print("Initial project metadata:", json.dumps(project.metadata, indent=2))

    # 3. Simulate adding data to the project directories (manually)
    # In a real workflow, other modules would save their outputs here.
    logging.info("\nSimulating the creation of data products...")
    
    # Create a dummy raw image
    dummy_img_path = project.image_manager.get_path() / 'DJI_0001.JPG'
    dummy_img_path.touch()

    # Create a dummy DSM raster
    dsm_profile = {
        'driver': 'GTiff', 'dtype': 'float32', 'nodata': -9999,
        'width': 100, 'height': 100, 'count': 1,
        'crs': rasterio.crs.CRS.from_epsg(32632),
        'transform': rasterio.transform.from_origin(300000, 5000000, 0.1, 0.1)
    }
    dummy_dsm_data = np.random.rand(1, 100, 100).astype(np.float32) * 10 + 50
    project.dsm_manager.save(dummy_dsm_data, name='dsm_run1', profile=dsm_profile)

    # Create a dummy plant metrics shapefile
    dummy_gdf = gpd.GeoDataFrame(
        {'plant_id': [1, 2], 'height': [1.2, 1.5]},
        geometry=[Point(300001, 5000001), Point(300002, 5000002)],
        crs="EPSG:32632"
    )
    project.vector_manager.save(dummy_gdf, name='plant_metrics_run1')

    # 4. Scan the project to discover and register the new files
    logging.info("\nScanning project to register files...")
    project.scan()
    print("Metadata after scan:", json.dumps(project.metadata, indent=2))

    # 5. Accessing data through the project object
    logging.info("\nAccessing data products via the project API...")
    
    # Get a list of raw images
    raw_images = project.list_products('raw_image')
    if raw_images:
        print(f"Found {len(raw_images)} raw images. First one: {raw_images[0].name}")
        print(f"  - EXIF data (simulated): {raw_images[0].metadata}")

    # Load the DSM
    try:
        dsm_product = project.get_product('dsm_run1', 'dsm')
        if dsm_product:
            print(f"Found DSM product: {dsm_product.name}")
            print(f"  - CRS: {dsm_product.metadata.get('crs')}")
            # dsm_data, dsm_profile = project.dsm_manager.load('dsm_run1')
            # print(f"  - Loaded DSM data with shape: {dsm_data.shape}")
    except FileNotFoundError as e:
        print(e)

    # Load the vector data
    try:
        plants_gdf = project.vector_manager.load('plant_metrics_run1')
        print(f"Loaded plant metrics GeoDataFrame with {len(plants_gdf)} records.")
    except FileNotFoundError as e:
        print(e)

    logging.info("--- Demo Complete ---")
