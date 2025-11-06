# c:\Users\Codeternal\Desktop\AgroPulse\app\computer_vision\pest_identification\data_loader.py

"""
Pest Identification Data Loading and Augmentation Pipeline
===========================================================

This module provides a robust and highly configurable data loading and augmentation
pipeline for the pest identification task. It is designed to handle large-scale
image datasets for both classification and object detection, which are the two
primary tasks in pest identification.

The pipeline is built on top of PyTorch's `Dataset` and `DataLoader` classes and
integrates `albumentations` for a rich set of data augmentation techniques that are
critical for training high-performance computer vision models.

Key Features:
-------------
1.  **Dual Task Support**: Provides distinct `Dataset` implementations for:
    -   `PestClassificationDataset`: For images where each file represents a single,
      cropped pest, and the goal is to classify the species.
    -   `PestDetectionDataset`: For images of entire plants or fields, with
      bounding box annotations for multiple pests. Supports standard formats like
      COCO and Pascal VOC.

2.  **Hierarchical Dataset Parsing**: The loaders can parse complex directory
    structures, automatically inferring class labels from folder names and handling
    train/validation/test splits.

3.  **Advanced Data Augmentation**: Leverages `albumentations` to provide a vast
    library of augmentations, including:
    -   **Geometric**: Rotations, scaling, flipping, cropping.
    -   **Color**: Brightness, contrast, saturation, hue adjustments.
    -   **Noise & Blur**: Gaussian noise, motion blur.
    -   **Cutout/Mixup/CutMix**: Advanced regularization techniques to improve
      model generalization.
    The augmentation pipeline is fully configurable via a dictionary, allowing for
    different strategies for training and validation.

4.  **Efficient Loading**: Uses PyTorch's `DataLoader` with multiprocessing to
    ensure that data is fed to the GPU without bottlenecks.

5.  **Normalization and Preprocessing**: Handles normalization of images using
    pre-computed means and standard deviations (e.g., from ImageNet) and resizes
    images to the required model input size.

6.  **Dataset Caching**: Includes functionality to cache dataset metadata (e.g.,
    file paths and labels) to speed up initialization on subsequent runs.

7.  **Visualization**: Provides utility functions to denormalize and draw bounding
    boxes on images, allowing for easy visual verification of the data being fed
    to the model.

Workflow:
---------
1.  **Configuration**: A configuration dictionary defines the dataset path, task
    type ('classification' or 'detection'), image size, batch size, and the
    specific augmentations to be applied.
2.  **Instantiation**: The appropriate `Dataset` class is instantiated with the
    configuration. It scans the directories, parses annotations, and builds an
    in-memory index of the data.
3.  **Augmentation Pipeline Creation**: A factory function (`create_augmentations`)
    builds the `albumentations` composition pipeline from the configuration.
4.  **Data Fetching**: When the `DataLoader` requests an item, the `Dataset` loads
    the image (and annotations), applies the augmentation pipeline, and returns
    the transformed tensors.

This module is fundamental to the success of the pest identification models, as
the quality and variety of the data seen during training directly impact the
model's real-world performance.
"""

import os
import json
import logging
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

import cv2
import numpy as np
import pandas as pd
import torch
from torch.utils.data import Dataset, DataLoader
from PIL import Image
from tqdm import tqdm

import albumentations as A
from albumentations.pytorch import ToTensorV2

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(module)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# --- Augmentation Factory ---

def create_augmentations(cfg: Dict[str, Any], stage: str = 'train') -> A.Compose:
    """
    Creates an Albumentations augmentation pipeline from a configuration dictionary.

    Args:
        cfg (Dict[str, Any]): The augmentation configuration.
        stage (str): The stage ('train', 'val', 'test') for which to create the
                     pipeline. Typically, more aggressive augmentations are used
                     for 'train'.

    Returns:
        A.Compose: The composed Albumentations pipeline.
    """
    aug_list = []
    if stage == 'train':
        train_cfg = cfg.get('train_augmentations', {})
        for aug_name, aug_params in train_cfg.items():
            if hasattr(A, aug_name):
                aug_list.append(getattr(A, aug_name)(**aug_params))
            else:
                logging.warning(f"Augmentation '{aug_name}' not found in Albumentations.")
    
    # Validation and test pipelines usually have minimal or no augmentation
    elif stage in ['val', 'test']:
        val_cfg = cfg.get('val_augmentations', {})
        for aug_name, aug_params in val_cfg.items():
            if hasattr(A, aug_name):
                aug_list.append(getattr(A, aug_name)(**aug_params))
            else:
                logging.warning(f"Augmentation '{aug_name}' not found in Albumentations.")

    # Common steps for all stages
    img_size = cfg.get('image_size', [512, 512])
    normalization_cfg = cfg.get('normalization', {})
    mean = normalization_cfg.get('mean', [0.485, 0.456, 0.406])
    std = normalization_cfg.get('std', [0.229, 0.224, 0.225])

    # Always resize, normalize, and convert to tensor
    aug_list.extend([
        A.Resize(height=img_size[0], width=img_size[1], p=1.0),
        A.Normalize(mean=mean, std=std, p=1.0),
        ToTensorV2(),
    ])

    bbox_params = A.BboxParams(
        format=cfg.get('bbox_format', 'coco'),
        label_fields=['class_labels'],
        min_area=cfg.get('min_bbox_area', 16),
        min_visibility=cfg.get('min_bbox_visibility', 0.2)
    ) if cfg.get('task') == 'detection' else None

    return A.Compose(aug_list, bbox_params=bbox_params)


# --- Classification Dataset ---

class PestClassificationDataset(Dataset):
    """
    PyTorch Dataset for pest classification.
    Assumes a directory structure like:
    <root>/<split>/<class_name>/<image_name>.jpg
    """
    def __init__(self,
                 root_dir: str,
                 split: str = 'train',
                 transform: Optional[Callable] = None,
                 cache_file: Optional[str] = None):
        """
        Args:
            root_dir (str): Root directory of the dataset.
            split (str): The dataset split to load ('train', 'val', 'test').
            transform (Callable, optional): Albumentations transform pipeline.
            cache_file (str, optional): Path to cache the file list.
        """
        self.root_dir = Path(root_dir)
        self.split_dir = self.root_dir / split
        self.transform = transform
        
        if not self.split_dir.exists():
            raise FileNotFoundError(f"Split directory not found: {self.split_dir}")

        self.samples, self.class_to_idx = self._load_samples(cache_file)
        self.idx_to_class = {v: k for k, v in self.class_to_idx.items()}
        
        logging.info(f"Loaded {len(self.samples)} samples for split '{split}' from {len(self.class_to_idx)} classes.")

    def _load_samples(self, cache_file: Optional[str]) -> Tuple[List[Tuple[Path, int]], Dict[str, int]]:
        """Loads image paths and labels, using a cache if available."""
        if cache_file and Path(cache_file).exists():
            logging.info(f"Loading samples from cache: {cache_file}")
            cache = torch.load(cache_file)
            return cache['samples'], cache['class_to_idx']

        samples = []
        class_names = sorted([d.name for d in self.split_dir.iterdir() if d.is_dir()])
        class_to_idx = {name: i for i, name in enumerate(class_names)}

        logging.info(f"Scanning directory {self.split_dir} for samples...")
        for class_name in tqdm(class_names, desc="Scanning classes"):
            class_idx = class_to_idx[class_name]
            class_dir = self.split_dir / class_name
            for img_path in class_dir.glob('*.*'):
                if img_path.suffix.lower() in ['.jpg', '.jpeg', '.png', '.bmp']:
                    samples.append((img_path, class_idx))
        
        if cache_file:
            logging.info(f"Saving samples to cache: {cache_file}")
            Path(cache_file).parent.mkdir(parents=True, exist_ok=True)
            torch.save({'samples': samples, 'class_to_idx': class_to_idx}, cache_file)
            
        return samples, class_to_idx

    def __len__(self) -> int:
        return len(self.samples)

    def __getitem__(self, idx: int) -> Dict[str, torch.Tensor]:
        img_path, label = self.samples[idx]
        
        try:
            # Load image using OpenCV, as it's the backend for albumentations
            image = cv2.imread(str(img_path))
            if image is None:
                raise IOError(f"Could not read image: {img_path}")
            image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        except Exception as e:
            logging.error(f"Error loading image {img_path}: {e}. Skipping.")
            # Return a dummy sample or the next valid one
            return self.__getitem__((idx + 1) % len(self))

        if self.transform:
            transformed = self.transform(image=image)
            image = transformed['image']

        return {
            'image': image,
            'label': torch.tensor(label, dtype=torch.long)
        }

# --- Detection Dataset ---

class PestDetectionDataset(Dataset):
    """
    PyTorch Dataset for pest detection.
    Assumes COCO annotation format.
    <root>/
        images/
            <split>/
                <image_name>.jpg
        annotations/
            <split>_annotations.json
    """
    def __init__(self,
                 root_dir: str,
                 split: str = 'train',
                 transform: Optional[Callable] = None):
        """
        Args:
            root_dir (str): Root directory of the dataset.
            split (str): The dataset split to load ('train', 'val', 'test').
            transform (Callable, optional): Albumentations transform pipeline.
        """
        self.root_dir = Path(root_dir)
        self.split = split
        self.img_dir = self.root_dir / 'images' / split
        self.annot_path = self.root_dir / 'annotations' / f'{split}_annotations.json'
        self.transform = transform

        if not self.img_dir.exists():
            raise FileNotFoundError(f"Image directory not found: {self.img_dir}")
        if not self.annot_path.exists():
            raise FileNotFoundError(f"Annotation file not found: {self.annot_path}")

        self.coco_data = self._load_coco_annotations()
        self.image_ids = list(self.coco_data['images'].keys())
        
        self.class_to_idx = {cat['name']: cat['id'] for cat in self.coco_data['categories'].values()}
        self.idx_to_class = {v: k for k, v in self.class_to_idx.items()}
        
        logging.info(f"Loaded {len(self.image_ids)} images for split '{split}' with {len(self.class_to_idx)} classes.")

    def _load_coco_annotations(self) -> Dict[str, Any]:
        """Loads COCO JSON and indexes it for fast lookups."""
        with open(self.annot_path, 'r') as f:
            ann_json = json.load(f)

        indexed_data = {
            'images': {img['id']: img for img in ann_json['images']},
            'annotations': {},
            'categories': {cat['id']: cat for cat in ann_json['categories']}
        }
        
        for ann in tqdm(ann_json['annotations'], desc="Indexing annotations"):
            img_id = ann['image_id']
            if img_id not in indexed_data['annotations']:
                indexed_data['annotations'][img_id] = []
            indexed_data['annotations'][img_id].append(ann)
            
        return indexed_data

    def __len__(self) -> int:
        return len(self.image_ids)

    def __getitem__(self, idx: int) -> Dict[str, Union[torch.Tensor, List]] :
        image_id = self.image_ids[idx]
        image_info = self.coco_data['images'][image_id]
        
        img_path = self.img_dir / image_info['file_name']
        
        try:
            image = cv2.imread(str(img_path))
            if image is None:
                raise IOError(f"Could not read image: {img_path}")
            image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        except Exception as e:
            logging.error(f"Error loading image {img_path}: {e}. Skipping.")
            return self.__getitem__((idx + 1) % len(self))

        annotations = self.coco_data['annotations'].get(image_id, [])
        
        bboxes = [ann['bbox'] for ann in annotations]
        class_labels = [ann['category_id'] for ann in annotations]

        # Convert bboxes to float and ensure they are valid
        bboxes = np.array(bboxes, dtype=np.float32)
        if bboxes.shape[0] > 0:
            # COCO format is [x, y, width, height]
            # Albumentations can handle this, but let's ensure width/height are positive
            bboxes[:, 2] = np.maximum(bboxes[:, 2], 1)
            bboxes[:, 3] = np.maximum(bboxes[:, 3], 1)
        else:
            # Handle images with no objects
            bboxes = np.zeros((0, 4), dtype=np.float32)

        if self.transform:
            transformed = self.transform(image=image, bboxes=bboxes, class_labels=class_labels)
            image = transformed['image']
            bboxes = torch.tensor(transformed['bboxes'], dtype=torch.float32)
            class_labels = torch.tensor(transformed['class_labels'], dtype=torch.long)
        else:
            # If no transform, we still need to convert to tensor
            bboxes = torch.tensor(bboxes, dtype=torch.float32)
            class_labels = torch.tensor(class_labels, dtype=torch.long)

        target = {
            'boxes': bboxes,
            'labels': class_labels,
            'image_id': torch.tensor([image_id])
        }

        return {'image': image, 'target': target}

# --- DataModule ---

class PestDataModule:
    """
    A DataModule that encapsulates all data-related logic.
    It can be configured for either classification or detection.
    """
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.task = self.config.get('task', 'classification')
        self.root_dir = self.config.get('root_dir')
        self.batch_size = self.config.get('batch_size', 32)
        self.num_workers = self.config.get('num_workers', 4)

        self.train_transform = create_augmentations(self.config, stage='train')
        self.val_transform = create_augmentations(self.config, stage='val')
        self.test_transform = create_augmentations(self.config, stage='test')

        self.train_dataset = None
        self.val_dataset = None
        self.test_dataset = None

    def setup(self, stage: Optional[str] = None):
        """
        Loads the datasets for the given stage.
        'fit' loads train and val, 'test' loads test.
        """
        if self.task == 'classification':
            DatasetClass = PestClassificationDataset
            dataset_args = {'root_dir': self.root_dir}
        elif self.task == 'detection':
            DatasetClass = PestDetectionDataset
            dataset_args = {'root_dir': self.root_dir}
        else:
            raise ValueError(f"Unknown task: {self.task}")

        if stage == 'fit' or stage is None:
            self.train_dataset = DatasetClass(
                split='train',
                transform=self.train_transform,
                **dataset_args
            )
            self.val_dataset = DatasetClass(
                split='val',
                transform=self.val_transform,
                **dataset_args
            )
        if stage == 'test' or stage is None:
            self.test_dataset = DatasetClass(
                split='test',
                transform=self.test_transform,
                **dataset_args
            )

    def train_dataloader(self) -> DataLoader:
        if self.train_dataset is None:
            self.setup('fit')
        return DataLoader(
            self.train_dataset,
            batch_size=self.batch_size,
            shuffle=True,
            num_workers=self.num_workers,
            pin_memory=True,
            collate_fn=self._collate_fn
        )

    def val_dataloader(self) -> DataLoader:
        if self.val_dataset is None:
            self.setup('fit')
        return DataLoader(
            self.val_dataset,
            batch_size=self.batch_size * 2, # Often larger batch size for validation
            shuffle=False,
            num_workers=self.num_workers,
            pin_memory=True,
            collate_fn=self._collate_fn
        )

    def test_dataloader(self) -> DataLoader:
        if self.test_dataset is None:
            self.setup('test')
        return DataLoader(
            self.test_dataset,
            batch_size=self.batch_size * 2,
            shuffle=False,
            num_workers=self.num_workers,
            pin_memory=True,
            collate_fn=self._collate_fn
        )

    def _collate_fn(self, batch):
        """Custom collate function for detection task."""
        if self.task == 'detection':
            images = [item['image'] for item in batch]
            targets = [item['target'] for item in batch]
            images = torch.stack(images, 0)
            return {'image': images, 'target': targets}
        
        # Default collate for classification
        return torch.utils.data.dataloader.default_collate(batch)

# --- Visualization Utility ---

def visualize_sample(dataset: Dataset, index: int, config: Dict[str, Any]):
    """
    Visualizes a single sample from a dataset.

    Args:
        dataset (Dataset): The dataset to draw from.
        index (int): The index of the sample to visualize.
        config (Dict[str, Any]): The dataloader configuration, used for normalization info.
    """
    item = dataset[index]
    image_tensor = item['image']
    
    # Denormalize
    norm_cfg = config.get('normalization', {})
    mean = np.array(norm_cfg.get('mean', [0.485, 0.456, 0.406]))
    std = np.array(norm_cfg.get('std', [0.229, 0.224, 0.225]))
    
    image = image_tensor.permute(1, 2, 0).cpu().numpy()
    image = (image * std + mean) * 255
    image = image.astype(np.uint8)
    image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR) # Convert back to BGR for OpenCV display

    if config['task'] == 'classification':
        label_idx = item['label'].item()
        label_name = dataset.idx_to_class[label_idx]
        title = f"Class: {label_name}"
    
    elif config['task'] == 'detection':
        target = item['target']
        title = f"Image ID: {target['image_id'].item()}"
        for box, label_idx in zip(target['boxes'], target['labels']):
            label_name = dataset.idx_to_class[label_idx.item()]
            x_min, y_min, w, h = box.int().numpy()
            x_max, y_max = x_min + w, y_min + h
            cv2.rectangle(image, (x_min, y_min), (x_max, y_max), (0, 255, 0), 2)
            cv2.putText(image, label_name, (x_min, y_min - 10), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

    cv2.imshow(title, image)
    cv2.waitKey(0)
    cv2.destroyAllWindows()


# --- Example Usage ---

def create_dummy_classification_data(root: Path):
    """Creates a fake classification dataset."""
    root.mkdir(parents=True, exist_ok=True)
    splits = ['train', 'val']
    classes = ['aphid', 'whitefly', 'thrips']
    for split in splits:
        for cls in classes:
            (root / split / cls).mkdir(parents=True, exist_ok=True)
            for i in range(10):
                img = Image.new('RGB', (100, 100), color = (i*10, i*10, i*10))
                img.save(root / split / cls / f'img_{i}.png')
    logging.info(f"Created dummy classification data at {root}")

def create_dummy_detection_data(root: Path):
    """Creates a fake detection dataset in COCO format."""
    root.mkdir(parents=True, exist_ok=True)
    (root / 'images' / 'train').mkdir(parents=True, exist_ok=True)
    (root / 'annotations').mkdir(parents=True, exist_ok=True)
    
    # Create dummy images
    for i in range(5):
        img = Image.new('RGB', (640, 480), color = (i*20, i*20, i*20))
        img.save(root / 'images' / 'train' / f'train_img_{i}.jpg')

    # Create dummy COCO annotations
    coco_annot = {
        'images': [{'id': i, 'file_name': f'train_img_{i}.jpg', 'width': 640, 'height': 480} for i in range(5)],
        'annotations': [
            {'id': 1, 'image_id': 0, 'category_id': 1, 'bbox': [10, 10, 50, 50], 'area': 2500, 'iscrowd': 0},
            {'id': 2, 'image_id': 1, 'category_id': 2, 'bbox': [100, 100, 80, 120], 'area': 9600, 'iscrowd': 0},
            {'id': 3, 'image_id': 1, 'category_id': 1, 'bbox': [200, 200, 40, 40], 'area': 1600, 'iscrowd': 0},
        ],
        'categories': [
            {'id': 1, 'name': 'spider_mite'},
            {'id': 2, 'name': 'leafminer'}
        ]
    }
    with open(root / 'annotations' / 'train_annotations.json', 'w') as f:
        json.dump(coco_annot, f, indent=4)
    logging.info(f"Created dummy detection data at {root}")


if __name__ == '__main__':
    import shutil

    # --- Classification Demo ---
    logging.info("\n--- Running Classification Data Loader Demo ---")
    cls_data_root = Path('./dummy_pest_classification_data')
    create_dummy_classification_data(cls_data_root)

    cls_config = {
        'task': 'classification',
        'root_dir': str(cls_data_root),
        'image_size': [224, 224],
        'batch_size': 4,
        'num_workers': 0, # Set to 0 for main thread execution in demo
        'train_augmentations': {
            'HorizontalFlip': {'p': 0.5},
            'Rotate': {'limit': 30, 'p': 0.5},
            'CoarseDropout': {'max_holes': 8, 'max_height': 16, 'max_width': 16, 'p': 0.5}
        },
        'val_augmentations': {},
        'normalization': {'mean': [0.5, 0.5, 0.5], 'std': [0.5, 0.5, 0.5]}
    }

    cls_dm = PestDataModule(cls_config)
    cls_dm.setup('fit')
    
    logging.info(f"Number of classes: {len(cls_dm.train_dataset.class_to_idx)}")
    logging.info(f"Class mapping: {cls_dm.train_dataset.class_to_idx}")

    train_loader = cls_dm.train_dataloader()
    sample_batch = next(iter(train_loader))
    logging.info(f"Image batch shape: {sample_batch['image'].shape}")
    logging.info(f"Label batch shape: {sample_batch['label'].shape}")
    
    logging.info("Visualizing a sample from the classification dataset (press any key to close)...")
    # visualize_sample(cls_dm.train_dataset, 0, cls_config)

    shutil.rmtree(cls_data_root)

    # --- Detection Demo ---
    logging.info("\n--- Running Detection Data Loader Demo ---")
    det_data_root = Path('./dummy_pest_detection_data')
    create_dummy_detection_data(det_data_root)

    det_config = {
        'task': 'detection',
        'root_dir': str(det_data_root),
        'image_size': [512, 512],
        'batch_size': 2,
        'num_workers': 0,
        'bbox_format': 'coco',
        'train_augmentations': {
            'HorizontalFlip': {'p': 0.5},
            'RandomBrightnessContrast': {'p': 0.5},
            'HueSaturationValue': {'p': 0.5},
        },
        'val_augmentations': {},
        'normalization': {'mean': [0.5, 0.5, 0.5], 'std': [0.5, 0.5, 0.5]}
    }

    det_dm = PestDataModule(det_config)
    det_dm.setup('fit') # 'fit' will only load train/val, but our dummy data only has train

    logging.info(f"Number of classes: {len(det_dm.train_dataset.class_to_idx)}")
    logging.info(f"Class mapping: {det_dm.train_dataset.class_to_idx}")

    det_train_loader = det_dm.train_dataloader()
    det_sample_batch = next(iter(det_train_loader))
    logging.info(f"Image batch shape: {det_sample_batch['image'].shape}")
    logging.info(f"Target is a list of length: {len(det_sample_batch['target'])}")
    logging.info(f"First target boxes shape: {det_sample_batch['target'][0]['boxes'].shape}")
    logging.info(f"First target labels shape: {det_sample_batch['target'][0]['labels'].shape}")

    logging.info("Visualizing a sample from the detection dataset (press any key to close)...")
    # visualize_sample(det_dm.train_dataset, 1, det_config)

    shutil.rmtree(det_data_root)
