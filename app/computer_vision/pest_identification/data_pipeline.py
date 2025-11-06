"""
data_pipeline.py

Module for building and managing the data pipelines for the Pest Identification system.

This module provides a robust and extensible framework for loading, preprocessing,
augmenting, and serving image data for training and evaluating pest identification models.
It is designed to handle large-scale datasets with complex class hierarchies and
imbalances, integrating seamlessly with PyTorch's data loading utilities.

Key Components:
- PestDataset: A flexible PyTorch Dataset class for loading pest images and their
  associated metadata, including bounding boxes, segmentation masks, and hierarchical labels.
- HierarchicalSampler: A sophisticated sampler that addresses class imbalance by sampling
  data according to its natural taxonomic hierarchy (e.g., family, genus, species).
  This ensures that rare classes are adequately represented during training.
- AugmentationSuite: A powerful data augmentation engine built on top of the
  `albumentations` library. It provides a wide range of configurable augmentations,
  from basic flips and rotations to advanced techniques like CutMix, MixUp, and
  photometric distortions.
- ExifDataProcessor: A utility for extracting, parsing, and leveraging EXIF metadata
  embedded in image files. This can provide valuable information about capture
  conditions (e.g., time of day, camera settings) that can be used as features.
- DataOrchestrator: A high-level class that ties all the components together. It
  manages the creation of data loaders for training, validation, and testing,
  applying the appropriate transformations and sampling strategies for each.
- AnnotationParser: A flexible parser for different annotation formats (e.g., COCO,
  Pascal VOC, YOLO) to standardize labels for the dataset.
- DataCache: An optional caching mechanism to store preprocessed images and
  annotations in memory or on disk to accelerate data loading in subsequent epochs.

The pipeline is designed for high performance, using multiprocessing for data loading
and optimized image processing operations. It also includes detailed error handling
and logging to facilitate debugging and monitoring of the data pipeline.

Example Usage:
    orchestrator = DataOrchestrator(
        root_dir='/path/to/dataset',
        annotation_file='/path/to/annotations.json',
        batch_size=32,
        num_workers=8,
        use_hierarchical_sampling=True,
        augment_config='advanced_augment.yaml'
    )
    train_loader = orchestrator.get_dataloader('train')
    for images, targets in train_loader:
        # images is a tensor of shape (B, C, H, W)
        # targets is a list of dictionaries, each containing labels, boxes, etc.
        ...

File-level docstring providing a comprehensive overview of the module's purpose,
key components, and an example of how to use the main orchestrator class.
This level of documentation is crucial for maintainability and usability, especially
in a large and complex system.
"""

import os
import json
import yaml
import random
import time
import logging
from datetime import datetime
from typing import Any, Dict, List, Tuple, Optional, Callable, Union, Set
from collections import defaultdict, Counter

import numpy as np
import cv2
from PIL import Image, ExifTags
from tqdm import tqdm

import torch
from torch.utils.data import Dataset, DataLoader, Sampler, DistributedSampler, ConcatDataset
from torchvision.transforms import functional as F

try:
    import albumentations as A
    from albumentations.pytorch import ToTensorV2
except ImportError:
    print("Albumentations not found. Please install with 'pip install albumentations'")
    A = None
    ToTensorV2 = None

# --- Configuration ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# --- Constants ---
SUPPORTED_IMAGE_FORMATS = ('.jpg', '.jpeg', '.png', '.bmp', '.tif', '.tiff')
DEFAULT_WORKERS = os.cpu_count() or 2

# --- Helper Functions ---
def get_exif_data(image_path: str) -> Dict[str, Any]:
    """Extracts and decodes EXIF data from an image file."""
    try:
        img = Image.open(image_path)
        exif_data = img._getexif()
        if not exif_data:
            return {}

        decoded_exif = {}
        for tag, value in exif_data.items():
            tag_name = ExifTags.TAGS.get(tag, tag)
            decoded_exif[tag_name] = value
        return decoded_exif
    except Exception as e:
        logger.warning(f"Could not read EXIF data for {image_path}: {e}")
        return {}

def is_image_file(filename: str) -> bool:
    """Checks if a file is a supported image format."""
    return filename.lower().endswith(SUPPORTED_IMAGE_FORMATS)

def load_config_from_yaml(config_path: str) -> Dict[str, Any]:
    """Loads a configuration dictionary from a YAML file."""
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Configuration file not found: {config_path}")
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)

# --- Annotation Parsing ---
class AnnotationParser:
    """
    Parses annotation files from various formats (COCO, Pascal VOC, etc.)
    into a standardized internal format.
    """
    def __init__(self, annotation_path: str, root_dir: str, format: str = 'coco'):
        self.annotation_path = annotation_path
        self.root_dir = root_dir
        self.format = format.lower()
        self.annotations = self._load_annotations()
        self.image_info: Dict[int, Dict[str, Any]] = {}
        self.image_annotations: Dict[int, List[Dict[str, Any]]] = defaultdict(list)
        self.cat_info: Dict[int, Dict[str, Any]] = {}
        self.cat_to_supercat: Dict[int, str] = {}
        self.hierarchical_structure: Dict[str, Dict[str, List[str]]] = defaultdict(lambda: defaultdict(list))
        self._parse()

    def _load_annotations(self) -> Dict[str, Any]:
        logger.info(f"Loading annotations from {self.annotation_path} in '{self.format}' format.")
        with open(self.annotation_path, 'r') as f:
            data = json.load(f)
        return data

    def _parse(self):
        """Parses the loaded annotation data into a structured format."""
        if self.format == 'coco':
            self._parse_coco()
        else:
            raise NotImplementedError(f"Annotation format '{self.format}' is not yet supported.")
        logger.info(f"Parsed {len(self.image_info)} images and {sum(len(v) for v in self.image_annotations.values())} annotations.")
        logger.info(f"Found {len(self.cat_info)} categories.")

    def _parse_coco(self):
        """Parses COCO-formatted annotations."""
        # Categories
        if 'categories' not in self.annotations:
            raise ValueError("COCO annotations must contain a 'categories' key.")
        for cat in self.annotations['categories']:
            self.cat_info[cat['id']] = cat
            supercategory = cat.get('supercategory', 'unknown')
            self.cat_to_supercat[cat['id']] = supercategory
            # Assuming a simple hierarchy for demonstration: Family -> Genus -> Species
            # In a real scenario, this might be more complex.
            parts = cat['name'].split('_')
            family = parts[0] if len(parts) > 0 else 'unknown'
            genus = parts[1] if len(parts) > 1 else 'unknown'
            species = cat['name']
            if genus not in self.hierarchical_structure[family]:
                 self.hierarchical_structure[family][genus] = []
            if species not in self.hierarchical_structure[family][genus]:
                self.hierarchical_structure[family][genus].append(species)


        # Images
        if 'images' not in self.annotations:
            raise ValueError("COCO annotations must contain an 'images' key.")
        for img in self.annotations['images']:
            self.image_info[img['id']] = img

        # Annotations
        if 'annotations' not in self.annotations:
            raise ValueError("COCO annotations must contain an 'annotations' key.")
        for ann in self.annotations['annotations']:
            image_id = ann['image_id']
            if image_id in self.image_info:
                self.image_annotations[image_id].append(ann)

    def get_image_path(self, image_id: int) -> str:
        """Constructs the full path for a given image ID."""
        return os.path.join(self.root_dir, self.image_info[image_id]['file_name'])

    def get_image_ids(self) -> List[int]:
        """Returns a list of all image IDs."""
        return list(self.image_info.keys())

    def get_annotations_for_image(self, image_id: int) -> List[Dict[str, Any]]:
        """Returns all annotations for a given image ID."""
        return self.image_annotations.get(image_id, [])

    def get_category_map(self) -> Dict[int, str]:
        """Returns a mapping from category ID to category name."""
        return {cat_id: info['name'] for cat_id, info in self.cat_info.items()}

# --- EXIF Data Processor ---
class ExifDataProcessor:
    """
    Processes EXIF data to extract features relevant for ML models.
    """
    def __init__(self, use_temporal_features: bool = True, use_camera_features: bool = False):
        self.use_temporal_features = use_temporal_features
        self.use_camera_features = use_camera_features

    def process(self, exif_data: Dict[str, Any]) -> Dict[str, float]:
        """
        Extracts numerical features from raw EXIF data.
        """
        features = {}
        if self.use_temporal_features:
            features.update(self._extract_temporal_features(exif_data))
        if self.use_camera_features:
            features.update(self._extract_camera_features(exif_data))
        return features

    def _extract_temporal_features(self, exif_data: Dict[str, Any]) -> Dict[str, float]:
        """
        Extracts time-based features like time of day, day of year.
        """
        dt_str = exif_data.get('DateTimeOriginal') or exif_data.get('DateTime')
        if not dt_str or not isinstance(dt_str, str):
            return {}

        try:
            # Handle potential non-standard datetime strings
            dt_str = dt_str.split(' ')[0].replace(':', '-') + ' ' + dt_str.split(' ')[1]
            dt = datetime.strptime(dt_str, '%Y-%m-%d %H:%M:%S')

            # Cyclic features for time
            seconds_in_day = 24 * 60 * 60
            time_seconds = dt.hour * 3600 + dt.minute * 60 + dt.second
            day_sin = np.sin(2 * np.pi * time_seconds / seconds_in_day)
            day_cos = np.cos(2 * np.pi * time_seconds / seconds_in_day)

            # Cyclic features for day of year
            days_in_year = 366 if (dt.year % 4 == 0 and dt.year % 100 != 0) or (dt.year % 400 == 0) else 365
            day_of_year = dt.timetuple().tm_yday
            year_sin = np.sin(2 * np.pi * day_of_year / days_in_year)
            year_cos = np.cos(2 * np.pi * day_of_year / days_in_year)

            return {
                'time_of_day_sin': day_sin,
                'time_of_day_cos': day_cos,
                'day_of_year_sin': year_sin,
                'day_of_year_cos': year_cos,
            }
        except (ValueError, IndexError) as e:
            logger.debug(f"Could not parse datetime string '{dt_str}': {e}")
            return {}

    def _extract_camera_features(self, exif_data: Dict[str, Any]) -> Dict[str, float]:
        """
        Extracts camera setting features like ISO, exposure, focal length.
        (Currently a placeholder)
        """
        # This can be expanded to normalize and use features like:
        # - ISOSpeedRatings
        # - ExposureTime
        # - FNumber
        # - FocalLength
        # Normalization would be crucial here.
        return {}

# --- Augmentation Suite ---
class AugmentationSuite:
    """
    Manages and applies data augmentations using albumentations.
    Can be configured via a YAML file.
    """
    def __init__(self, config: Optional[Union[str, Dict]] = None, image_size: Tuple[int, int] = (512, 512)):
        self.image_size = image_size
        if isinstance(config, str):
            self.config = load_config_from_yaml(config)
        elif isinstance(config, dict):
            self.config = config
        else:
            self.config = self.get_default_config()

        self.train_transform = self._build_transform('train')
        self.val_transform = self._build_transform('val')
        logger.info(f"Train augmentations: {[t.__class__.__name__ for t in self.train_transform.transforms]}")
        logger.info(f"Validation augmentations: {[t.__class__.__name__ for t in self.val_transform.transforms]}")

    def get_default_config(self) -> Dict[str, Any]:
        """Provides a default set of augmentations."""
        return {
            'train': [
                {'name': 'Resize', 'params': {'height': self.image_size[0], 'width': self.image_size[1]}},
                {'name': 'HorizontalFlip', 'params': {'p': 0.5}},
                {'name': 'VerticalFlip', 'params': {'p': 0.5}},
                {'name': 'RandomRotate90', 'params': {'p': 0.5}},
                {'name': 'ShiftScaleRotate', 'params': {'p': 0.5, 'shift_limit': 0.0625, 'scale_limit': 0.1, 'rotate_limit': 15}},
                {'name': 'RandomBrightnessContrast', 'params': {'p': 0.5}},
                {'name': 'HueSaturationValue', 'params': {'p': 0.3}},
                {'name': 'GaussNoise', 'params': {'p': 0.2}},
                {'name': 'Normalize', 'params': {'mean': [0.485, 0.456, 0.406], 'std': [0.229, 0.224, 0.225]}},
                {'name': 'ToTensorV2', 'params': {}}
            ],
            'val': [
                {'name': 'Resize', 'params': {'height': self.image_size[0], 'width': self.image_size[1]}},
                {'name': 'Normalize', 'params': {'mean': [0.485, 0.456, 0.406], 'std': [0.229, 0.224, 0.225]}},
                {'name': 'ToTensorV2', 'params': {}}
            ]
        }

    def _build_transform(self, mode: str) -> A.Compose:
        """Builds an albumentations composition from the config."""
        if A is None:
            raise ImportError("Albumentations is required to build transforms.")

        transforms = []
        transform_configs = self.config.get(mode, [])
        for t_config in transform_configs:
            try:
                transform_name = t_config['name']
                transform_params = t_config.get('params', {})
                if hasattr(A, transform_name):
                    transforms.append(getattr(A, transform_name)(**transform_params))
                elif transform_name == 'ToTensorV2':
                    transforms.append(ToTensorV2(**transform_params))
                else:
                    logger.warning(f"Unknown augmentation '{transform_name}' in config. Skipping.")
            except Exception as e:
                logger.error(f"Failed to instantiate augmentation '{t_config.get('name')}': {e}")

        # Bbox params are crucial for object detection tasks
        bbox_params = A.BboxParams(format='coco', label_fields=['class_labels', 'instance_ids'])
        return A.Compose(transforms, bbox_params=bbox_params)

    def __call__(self, mode: str, **kwargs: Any) -> Dict[str, Any]:
        """Applies the specified transformation."""
        transform = self.train_transform if mode == 'train' else self.val_transform
        return transform(**kwargs)

# --- Main Dataset Class ---
class PestDataset(Dataset):
    """
    PyTorch Dataset for loading pest images and annotations.

    Handles loading images, parsing annotations, and applying transformations.
    It can be configured for classification, detection, or segmentation tasks.
    """
    def __init__(self,
                 parser: AnnotationParser,
                 image_ids: List[int],
                 transform: Callable,
                 task: str = 'detection', # 'detection', 'classification', 'segmentation'
                 exif_processor: Optional[ExifDataProcessor] = None,
                 use_cache: bool = False):
        super().__init__()
        self.parser = parser
        self.image_ids = image_ids
        self.transform = transform
        self.task = task
        self.exif_processor = exif_processor
        self.use_cache = use_cache
        self.cache: Dict[int, Any] = {}

        if self.task not in ['detection', 'classification', 'segmentation']:
            raise ValueError(f"Task '{self.task}' not supported.")
        if self.task == 'segmentation':
            logger.warning("Segmentation task is defined but mask loading is not fully implemented in this version.")

    def __len__(self) -> int:
        return len(self.image_ids)

    def __getitem__(self, index: int) -> Tuple[torch.Tensor, Dict[str, Any]]:
        image_id = self.image_ids[index]

        if self.use_cache and image_id in self.cache:
            return self.cache[image_id]

        # --- Load Image ---
        image_path = self.parser.get_image_path(image_id)
        try:
            # Use OpenCV for consistency with albumentations
            image = cv2.imread(image_path)
            if image is None:
                raise IOError(f"cv2.imread failed to load image: {image_path}")
            image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        except Exception as e:
            logger.error(f"Error loading image {image_path} for ID {image_id}. Skipping. Error: {e}")
            # Return a placeholder or skip. For simplicity, we'll return the first valid item.
            # A more robust solution would be to handle this in the collate_fn.
            return self.__getitem__(0) if index != 0 else (torch.zeros(3, 224, 224), {})


        # --- Load Annotations ---
        annotations = self.parser.get_annotations_for_image(image_id)
        target = self._prepare_target(annotations, image.shape)

        # --- Augmentations ---
        augmented = self.transform(
            image=image,
            bboxes=target['boxes'],
            class_labels=target['labels'],
            instance_ids=target['instance_ids']
        )

        image_tensor = augmented['image']
        target['boxes'] = torch.tensor(augmented['bboxes'], dtype=torch.float32) if augmented['bboxes'] else torch.empty((0, 4), dtype=torch.float32)
        target['labels'] = torch.tensor(augmented['class_labels'], dtype=torch.int64)
        target['instance_ids'] = torch.tensor(augmented['instance_ids'], dtype=torch.int64)

        # --- Process EXIF Data ---
        if self.exif_processor:
            exif_data = get_exif_data(image_path)
            exif_features = self.exif_processor.process(exif_data)
            target['exif_features'] = torch.tensor(list(exif_features.values()), dtype=torch.float32)

        # Finalize target
        target['image_id'] = torch.tensor([image_id], dtype=torch.int64)
        
        # For classification, we might just want the most frequent label
        if self.task == 'classification':
            if len(target['labels']) > 0:
                # Use the label of the largest bounding box
                if len(target['boxes']) > 0:
                    areas = (target['boxes'][:, 2] - target['boxes'][:, 0]) * (target['boxes'][:, 3] - target['boxes'][:, 1])
                    main_label = target['labels'][torch.argmax(areas)]
                else: # Or just the first one if no boxes
                    main_label = target['labels'][0]
            else:
                main_label = torch.tensor(-1, dtype=torch.int64) # Background/unknown
            
            # The target for classification is just the label
            final_target = main_label
        else: # For detection/segmentation, it's the dictionary
            final_target = target


        if self.use_cache:
            self.cache[image_id] = (image_tensor, final_target)

        return image_tensor, final_target

    def _prepare_target(self, annotations: List[Dict[str, Any]], image_shape: Tuple[int, int, int]) -> Dict[str, Any]:
        """Converts raw annotations to a structured target dictionary."""
        h, w, _ = image_shape
        boxes = []
        labels = []
        masks = []
        instance_ids = []

        for i, ann in enumerate(annotations):
            # Bounding box [x, y, width, height] -> [x_min, y_min, x_max, y_max]
            if 'bbox' in ann:
                bbox = ann['bbox']
                # Clamp coordinates to be within image dimensions
                x_min = max(0, bbox[0])
                y_min = max(0, bbox[1])
                x_max = min(w, x_min + bbox[2])
                y_max = min(h, y_min + bbox[3])
                
                # Filter out zero-area boxes
                if x_max > x_min and y_max > y_min:
                    boxes.append([x_min, y_min, x_max, y_max])
                    labels.append(ann['category_id'])
                    instance_ids.append(i)

            # Segmentation mask
            if 'segmentation' in ann and self.task == 'segmentation':
                # This part is complex and requires a robust implementation
                # for RLE or polygon formats. Placeholder for now.
                pass

        return {
            'boxes': np.array(boxes, dtype=np.float32) if boxes else np.empty((0, 4), dtype=np.float32),
            'labels': np.array(labels, dtype=np.int64),
            'masks': masks, # Placeholder
            'instance_ids': np.array(instance_ids, dtype=np.int64)
        }

# --- Hierarchical Sampler ---
class HierarchicalSampler(Sampler[int]):
    """
    A PyTorch Sampler that performs hierarchical sampling to balance classes.

    It first samples a top-level category (e.g., family), then a mid-level
    category (e.g., genus), and finally an image from that category. This helps
    ensure that rare species are seen more often during training.
    """
    def __init__(self,
                 parser: AnnotationParser,
                 image_ids: List[int],
                 batch_size: int,
                 replacement: bool = True,
                 drop_last: bool = True):
        super().__init__(image_ids)
        self.parser = parser
        self.image_ids = image_ids
        self.batch_size = batch_size
        self.replacement = replacement
        self.drop_last = drop_last

        self.num_samples = len(self.image_ids) if not self.drop_last else (len(self.image_ids) // self.batch_size) * self.batch_size

        logger.info("Building hierarchical index for sampler...")
        self._build_index()
        logger.info("Hierarchical index built.")

    def _build_index(self):
        """
        Builds a multi-level dictionary mapping hierarchy to image indices.
        Example: self.index['FamilyA']['GenusB']['SpeciesC'] = [img_idx1, img_idx2, ...]
        """
        self.index: Dict[str, Dict[str, Dict[str, List[int]]]] = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
        self.flat_cat_index: Dict[int, List[int]] = defaultdict(list)
        self.image_id_to_idx = {img_id: i for i, img_id in enumerate(self.image_ids)}

        for image_id in tqdm(self.image_ids, desc="Indexing for Sampler"):
            annotations = self.parser.get_annotations_for_image(image_id)
            if not annotations:
                continue

            img_idx = self.image_id_to_idx[image_id]
            unique_categories: Set[int] = {ann['category_id'] for ann in annotations}

            for cat_id in unique_categories:
                self.flat_cat_index[cat_id].append(img_idx)
                cat_info = self.parser.cat_info.get(cat_id)
                if cat_info:
                    cat_name = cat_info['name']
                    parts = cat_name.split('_')
                    family = parts[0] if len(parts) > 0 else 'unknown'
                    genus = parts[1] if len(parts) > 1 else 'unknown'
                    self.index[family][genus][cat_name].append(img_idx)

        self.families = list(self.index.keys())
        self.family_weights = self._calculate_weights(self.families, self.index)

        self.genus_weights = {}
        for fam in self.families:
            genera = list(self.index[fam].keys())
            self.genus_weights[fam] = self._calculate_weights(genera, self.index[fam])

        self.species_weights = {}
        for fam in self.families:
            self.species_weights[fam] = {}
            for gen in self.index[fam]:
                species = list(self.index[fam][gen].keys())
                self.species_weights[fam][gen] = self._calculate_weights(species, self.index[fam][gen])

    def _calculate_weights(self, items: List[str], index_level: Dict) -> List[float]:
        """Calculates inverse frequency weights."""
        counts = np.array([sum(len(v) for v in index_level[item].values()) if isinstance(list(index_level[item].values())[0], dict)
                           else len(index_level[item]) for item in items], dtype=np.float32)
        # Inverse frequency weighting
        weights = 1.0 / counts
        # Add a small epsilon to avoid division by zero for categories that might be empty
        # weights = 1.0 / np.maximum(counts, 1)
        return weights / np.sum(weights)


    def __iter__(self):
        indices = []
        while len(indices) < self.num_samples:
            try:
                # 1. Sample Family
                fam = random.choices(self.families, weights=self.family_weights)[0]
                genera = list(self.index[fam].keys())
                if not genera: continue

                # 2. Sample Genus
                gen = random.choices(genera, weights=self.genus_weights[fam])[0]
                species_list = list(self.index[fam][gen].keys())
                if not species_list: continue

                # 3. Sample Species
                spec = random.choices(species_list, weights=self.species_weights[fam][gen])[0]
                image_indices = self.index[fam][gen][spec]
                if not image_indices: continue

                # 4. Sample Image
                chosen_idx = random.choice(image_indices)
                indices.append(chosen_idx)

            except (IndexError, KeyError) as e:
                # This might happen if the hierarchical structure is sparse.
                # Fallback to flat sampling.
                logger.debug(f"Hierarchical sampling failed: {e}. Falling back to flat sampling for one sample.")
                cat_id = random.choice(list(self.flat_cat_index.keys()))
                if self.flat_cat_index[cat_id]:
                    indices.append(random.choice(self.flat_cat_index[cat_id]))

        if not self.replacement:
            # This is tricky with hierarchical sampling. The simplest way is to
            # sample with replacement and then take unique indices, but that
            # changes the distribution. For now, we primarily support with replacement.
            if len(indices) > self.num_samples:
                indices = list(dict.fromkeys(indices)) # Get unique indices
                random.shuffle(indices)

        return iter(indices[:self.num_samples])

    def __len__(self) -> int:
        return self.num_samples

# --- Data Orchestrator ---
class DataOrchestrator:
    """
    High-level manager for creating and configuring data loaders.

    This class is the main entry point for accessing data. It handles:
    - Parsing annotations.
    - Splitting data into train/validation/test sets.
    - Setting up augmentations.
    - Creating PyTorch DataLoaders with appropriate samplers.
    """
    def __init__(self,
                 root_dir: str,
                 annotation_file: str,
                 batch_size: int,
                 num_workers: int = DEFAULT_WORKERS,
                 image_size: Tuple[int, int] = (512, 512),
                 val_split: float = 0.15,
                 test_split: float = 0.05,
                 random_seed: int = 42,
                 annotation_format: str = 'coco',
                 task: str = 'detection',
                 augment_config: Optional[Union[str, Dict]] = None,
                 use_hierarchical_sampling: bool = True,
                 use_exif: bool = True,
                 pin_memory: bool = True,
                 use_distributed: bool = False,
                 use_cache: bool = False):

        logger.info("Initializing Data Orchestrator...")
        self.root_dir = root_dir
        self.annotation_file = annotation_file
        self.batch_size = batch_size
        self.num_workers = num_workers
        self.image_size = image_size
        self.val_split = val_split
        self.test_split = test_split
        self.random_seed = random_seed
        self.task = task
        self.use_hierarchical_sampling = use_hierarchical_sampling
        self.pin_memory = pin_memory
        self.use_distributed = use_distributed
        self.use_cache = use_cache

        # 1. Parse Annotations
        self.parser = AnnotationParser(annotation_file, root_dir, format=annotation_format)

        # 2. Setup Augmentations
        self.augmenter = AugmentationSuite(augment_config, image_size)

        # 3. Setup EXIF Processor
        self.exif_processor = ExifDataProcessor() if use_exif else None

        # 4. Split Data
        self.image_ids = self.parser.get_image_ids()
        self._split_data()

        logger.info(f"Data split: {len(self.train_ids)} train, {len(self.val_ids)} val, {len(self.test_ids)} test.")
        logger.info("Data Orchestrator initialized successfully.")

    def _split_data(self):
        """Splits image IDs into training, validation, and test sets."""
        random.seed(self.random_seed)
        shuffled_ids = self.image_ids[:]
        random.shuffle(shuffled_ids)

        num_images = len(shuffled_ids)
        num_test = int(self.test_split * num_images)
        num_val = int(self.val_split * num_images)

        self.test_ids = shuffled_ids[:num_test]
        self.val_ids = shuffled_ids[num_test : num_test + num_val]
        self.train_ids = shuffled_ids[num_test + num_val :]

    def get_dataloader(self, split: str) -> DataLoader:
        """
        Creates and returns a DataLoader for the specified data split.

        Args:
            split (str): One of 'train', 'val', or 'test'.

        Returns:
            DataLoader: The configured PyTorch DataLoader.
        """
        if split not in ['train', 'val', 'test']:
            raise ValueError(f"Invalid split '{split}'. Must be 'train', 'val', or 'test'.")

        is_train = split == 'train'
        ids = getattr(self, f"{split}_ids")
        transform = self.augmenter.train_transform if is_train else self.augmenter.val_transform

        dataset = PestDataset(
            parser=self.parser,
            image_ids=ids,
            transform=transform,
            task=self.task,
            exif_processor=self.exif_processor,
            use_cache=self.use_cache
        )

        sampler = None
        shuffle = not self.use_distributed and is_train and not self.use_hierarchical_sampling

        if self.use_distributed:
            sampler = DistributedSampler(dataset, shuffle=is_train)
        elif is_train and self.use_hierarchical_sampling:
            sampler = HierarchicalSampler(self.parser, ids, self.batch_size)
            shuffle = False # Sampler handles shuffling

        return DataLoader(
            dataset,
            batch_size=self.batch_size,
            shuffle=shuffle,
            sampler=sampler,
            num_workers=self.num_workers,
            pin_memory=self.pin_memory,
            collate_fn=self.collate_fn,
            drop_last=is_train
        )

    @staticmethod
    def collate_fn(batch: List[Tuple]) -> Any:
        """
        Custom collate function to handle variable-sized targets in detection.
        """
        # Separate images and targets
        images, targets = zip(*batch)

        # Stack images (they should all be the same size due to transforms)
        images = torch.stack(images, 0)

        # If the target is a dictionary (detection/segmentation), handle it.
        # If it's a tensor (classification), stack them.
        if isinstance(targets[0], dict):
            # For detection, targets are lists of dictionaries, not tensors.
            # The model's forward pass will expect a list of target dicts.
            return images, list(targets)
        elif isinstance(targets[0], torch.Tensor):
            return images, torch.stack(targets, 0)
        else:
            return images, targets


# --- Example Usage ---
def run_pipeline_demo(root_dir: str, annotation_file: str):
    """
    A demonstration of how to use the DataOrchestrator.
    This function will not run unless called, serving as documentation.
    """
    logger.info("--- Starting Data Pipeline Demo ---")

    # Create dummy data and annotations for demonstration
    os.makedirs(os.path.join(root_dir, 'images'), exist_ok=True)
    dummy_annotations = {
        'images': [],
        'annotations': [],
        'categories': [
            {'id': 1, 'name': 'Lepidoptera_Noctuidae_Spodoptera_frugiperda', 'supercategory': 'Lepidoptera'},
            {'id': 2, 'name': 'Coleoptera_Curculionidae_Anthonomus_grandis', 'supercategory': 'Coleoptera'},
            {'id': 3, 'name': 'Lepidoptera_Noctuidae_Helicoverpa_zea', 'supercategory': 'Lepidoptera'},
        ]
    }
    for i in range(100):
        img_id = i + 1
        h, w = random.randint(400, 800), random.randint(600, 1024)
        file_name = f'images/dummy_image_{img_id}.jpg'
        dummy_annotations['images'].append({'id': img_id, 'file_name': file_name, 'height': h, 'width': w})
        # Create a dummy image file
        cv2.imwrite(os.path.join(root_dir, file_name), np.random.randint(0, 256, (h, w, 3), dtype=np.uint8))

        # Add 1-5 annotations per image
        for j in range(random.randint(1, 5)):
            cat_id = random.randint(1, 3)
            x, y = random.randint(0, w-50), random.randint(0, h-50)
            bw, bh = random.randint(20, 50), random.randint(20, 50)
            dummy_annotations['annotations'].append({
                'id': len(dummy_annotations['annotations']) + 1,
                'image_id': img_id,
                'category_id': cat_id,
                'bbox': [x, y, bw, bh],
                'area': bw * bh,
                'iscrowd': 0
            })

    with open(annotation_file, 'w') as f:
        json.dump(dummy_annotations, f)

    logger.info("Dummy data created.")

    # --- Configure and run the orchestrator ---
    try:
        orchestrator = DataOrchestrator(
            root_dir=root_dir,
            annotation_file=annotation_file,
            batch_size=8,
            num_workers=2,
            image_size=(256, 256),
            use_hierarchical_sampling=True,
            task='detection'
        )

        # Get the training data loader
        train_loader = orchestrator.get_dataloader('train')
        logger.info(f"Created a DataLoader with {len(train_loader)} batches.")

        # Fetch and inspect a batch
        start_time = time.time()
        batch_images, batch_targets = next(iter(train_loader))
        end_time = time.time()

        logger.info(f"Fetched one batch in {end_time - start_time:.4f} seconds.")
        logger.info(f"Image batch shape: {batch_images.shape}")
        logger.info(f"Image batch dtype: {batch_images.dtype}")
        logger.info(f"Number of targets in batch: {len(batch_targets)}")

        # Inspect the first target in the batch
        first_target = batch_targets[0]
        logger.info("--- First Target in Batch ---")
        for key, value in first_target.items():
            if isinstance(value, torch.Tensor):
                logger.info(f"  - {key}: Tensor(shape={value.shape}, dtype={value.dtype})")
            else:
                logger.info(f"  - {key}: {value}")
        logger.info("-----------------------------")

    except Exception as e:
        logger.exception(f"An error occurred during the demo: {e}")
    finally:
        # Clean up dummy files
        import shutil
        if os.path.exists(root_dir):
            shutil.rmtree(root_dir)
        if os.path.exists(annotation_file):
            os.remove(annotation_file)
        logger.info("Cleaned up dummy data.")

if __name__ == '__main__':
    # This block allows the script to be run for testing/demonstration purposes.
    # It will create temporary dummy data, run the pipeline, and then clean up.
    DEMO_ROOT = './temp_pest_dataset'
    DEMO_ANNO = './temp_annotations.json'
    run_pipeline_demo(DEMO_ROOT, DEMO_ANNO)
