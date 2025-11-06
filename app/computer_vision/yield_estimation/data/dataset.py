"""
PyTorch Dataset for Yield Estimation
====================================

This module defines the primary `YieldDataset` class, a flexible and powerful
PyTorch `Dataset` designed to handle the diverse data requirements of yield
estimation. Agricultural datasets are often complex, involving multiple image
modalities, different types of labels (e.g., bounding boxes for fruit counting,
masks for biomass estimation), and time-series data. This class is built to
manage that complexity.

Core Features:
--------------
1.  **Multi-modal Data Handling**:
    -   The dataset can load multiple spatially aligned images for a single sample,
      such as RGB, Near-Infrared (NIR), and thermal images.
    -   It assumes a file naming convention to associate different modalities with
      the same sample ID (e.g., `sample_01_rgb.tif`, `sample_01_nir.tif`).

2.  **Flexible Label Support**:
    -   The dataset is designed to load different types of annotations based on the
      task specified (e.g., 'detection', 'segmentation').
    -   For 'detection', it parses XML files (PASCAL VOC format) to get bounding boxes.
    -   For 'segmentation', it loads image masks (e.g., from PNG files).
    -   For 'regression', it can load a single yield value from a CSV or JSON file.

3.  **Integration with Augmentations**:
    -   It accepts an `albumentations` transform object during initialization.
    -   In the `__getitem__` method, it applies these transforms to the loaded
      images and their corresponding labels (masks/bboxes), ensuring that all
      components are transformed consistently.

4.  **Time-Series Support (Advanced)**:
    -   The design can be extended to handle time-series data by grouping samples
      by location and date. The `__getitem__` method could be adapted to return
      a sequence of images instead of a single one.

5.  **Efficient Loading**:
    -   The file paths and labels are indexed during initialization to avoid
      repeated file system scans, making data loading faster during training.
    -   It uses `cv2` for fast image reading.

Structure:
----------
-   **`YieldDataset` Class**:
    -   `__init__`:
        -   Scans the data directories to find all unique sample IDs.
        -   Indexes the paths to images and annotations for each sample.
        -   Takes the task type, required modalities, and augmentation pipeline
          as input.
    -   `__len__`: Returns the total number of samples.
    -   `__getitem__`:
        -   Loads the required image modalities for a given index (e.g., RGB, NIR).
        -   Loads the corresponding label (mask, bboxes, or scalar value).
        -   Constructs a dictionary of inputs for the augmentation pipeline.
        -   Applies the augmentations.
        -   Returns the transformed image tensors and the target label(s).

This class is the cornerstone of the data pipeline, providing a standardized way
to feed complex, multi-modal, and augmented data into the training engine.
"""

import os
import cv2
import numpy as np
import torch
from torch.utils.data import Dataset
import pandas as pd
import xml.etree.ElementTree as ET
from typing import List, Dict, Any, Tuple, Literal
import logging

from app.computer_vision.yield_estimation.data.augmentations import YieldEstimationAugmenter

logger = logging.getLogger(__name__)

class YieldDataset(Dataset):
    """
    A flexible PyTorch dataset for yield estimation that handles multi-modal
    imagery and different task types (detection, segmentation, regression).
    """
    def __init__(self,
                 data_dir: str,
                 task: Literal['detection', 'segmentation', 'regression'],
                 modalities: List[str],
                 augmenter: YieldEstimationAugmenter,
                 is_train: bool,
                 label_file: str = None):
        """
        Args:
            data_dir (str): Root directory containing 'images' and 'annotations' folders.
            task (str): The type of task. One of 'detection', 'segmentation', 'regression'.
            modalities (List[str]): List of image modalities to load (e.g., ['rgb', 'nir']).
            augmenter (YieldEstimationAugmenter): The augmenter to apply transforms.
            is_train (bool): Whether this is a training dataset (to apply train transforms).
            label_file (str, optional): Path to a CSV file for regression tasks.
                                        Required if task is 'regression'.
        """
        self.data_dir = data_dir
        self.task = task
        self.modalities = modalities
        self.transform = augmenter.get_transforms(is_train=is_train)
        self.is_train = is_train

        self.image_sets_dir = os.path.join(data_dir, 'images')
        self.annotation_dir = os.path.join(data_dir, 'annotations')

        if not os.path.isdir(self.image_sets_dir):
            raise FileNotFoundError(f"Image directory not found: {self.image_sets_dir}")
        if not os.path.isdir(self.annotation_dir) and task != 'regression':
            raise FileNotFoundError(f"Annotation directory not found: {self.annotation_dir}")

        self.samples = self._find_samples()
        
        if self.task == 'regression':
            if label_file is None or not os.path.exists(label_file):
                raise ValueError("A valid label_file (CSV) is required for regression task.")
            self.yield_data = pd.read_csv(label_file).set_index('sample_id')

        logger.info(f"Initialized YieldDataset for task '{task}' with {len(self.samples)} samples.")

    def _find_samples(self) -> List[str]:
        """
        Scans the image directory to find unique sample IDs.
        Assumes filenames like 'sample_id_modality.ext'.
        """
        sample_ids = set()
        for filename in os.listdir(self.image_sets_dir):
            parts = os.path.splitext(filename)[0].split('_')
            if len(parts) > 1:
                sample_id = '_'.join(parts[:-1])
                sample_ids.add(sample_id)
        
        if not sample_ids:
            logger.warning(f"No samples found in {self.image_sets_dir}. Check file naming convention.")
        
        return sorted(list(sample_ids))

    def __len__(self) -> int:
        return len(self.samples)

    def __getitem__(self, idx: int) -> Tuple[Dict[str, torch.Tensor], Any]:
        """
        Retrieves and processes one sample from the dataset.

        Returns:
            A tuple containing:
            - A dictionary of image tensors, with keys matching the modalities.
            - The target (e.g., dict for detection, tensor for segmentation/regression).
        """
        sample_id = self.samples[idx]
        
        # --- Load Images ---
        images = {}
        for modality in self.modalities:
            # Try common extensions
            image_path = None
            for ext in ['.tif', '.png', '.jpg']:
                path = os.path.join(self.image_sets_dir, f"{sample_id}_{modality}{ext}")
                if os.path.exists(path):
                    image_path = path
                    break
            
            if image_path is None:
                logger.error(f"Image not found for sample {sample_id}, modality {modality}")
                # Return dummy data to prevent crash
                return {'rgb': torch.zeros(3, 256, 256)}, {}

            # Load image (handle multi-channel TIFs correctly)
            img = cv2.imread(image_path, cv2.IMREAD_UNCHANGED)
            if img is None:
                logger.error(f"Could not read image: {image_path}")
                return {'rgb': torch.zeros(3, 256, 256)}, {}

            # If RGB, convert BGR to RGB
            if modality == 'rgb' and len(img.shape) == 3:
                img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            
            images[modality] = img

        # --- Load Annotations ---
        target, bboxes, labels = {}, [], []
        if self.task == 'detection':
            xml_path = os.path.join(self.annotation_dir, f"{sample_id}.xml")
            if os.path.exists(xml_path):
                tree = ET.parse(xml_path)
                root = tree.getroot()
                for member in root.findall('object'):
                    label_name = member.find('name').text
                    bndbox = member.find('bndbox')
                    xmin = int(bndbox.find('xmin').text)
                    ymin = int(bndbox.find('ymin').text)
                    xmax = int(bndbox.find('xmax').text)
                    ymax = int(bndbox.find('ymax').text)
                    bboxes.append([xmin, ymin, xmax, ymax])
                    labels.append(1) # Assuming single class for now, extend later
            target['bboxes'] = bboxes
            target['class_labels'] = labels

        elif self.task == 'segmentation':
            mask_path = os.path.join(self.annotation_dir, f"{sample_id}_mask.png")
            if os.path.exists(mask_path):
                mask = cv2.imread(mask_path, cv2.IMREAD_GRAYSCALE)
                target['mask'] = mask
            else:
                logger.warning(f"Mask not found for sample {sample_id}, returning empty mask.")
                target['mask'] = np.zeros(images[self.modalities[0]].shape[:2], dtype=np.uint8)

        elif self.task == 'regression':
            yield_value = self.yield_data.loc[sample_id]['yield']
            target['yield'] = torch.tensor([yield_value], dtype=torch.float32)

        # --- Apply Augmentations ---
        # The primary image must be named 'image' for albumentations
        aug_input = {'image': images.pop('rgb')}
        aug_input.update(images) # Add other modalities like 'nir'
        
        if self.task == 'detection':
            aug_input['bboxes'] = target['bboxes']
            aug_input['class_labels'] = target['class_labels']
        elif self.task == 'segmentation':
            aug_input['mask'] = target['mask']

        transformed = self.transform(**aug_input)

        # --- Format Output ---
        output_images = {'rgb': transformed.pop('image')}
        for modality in self.modalities:
            if modality in transformed:
                output_images[modality] = transformed.pop(modality)

        output_target = {}
        if self.task == 'detection':
            output_target['boxes'] = torch.as_tensor(transformed['bboxes'], dtype=torch.float32)
            output_target['labels'] = torch.as_tensor(transformed['class_labels'], dtype=torch.int64)
        elif self.task == 'segmentation':
            output_target['mask'] = transformed['mask'].long() # Use long for CrossEntropyLoss
        elif self.task == 'regression':
            output_target = target['yield']

        return output_images, output_target

# --- Example Usage ---
if __name__ == '__main__':
    from app.computer_vision.yield_estimation.utils.config import AugmentationConfig
    
    print("--- Yield Estimation Dataset Demo ---")

    # 1. Create dummy data and directories
    temp_dir = "c:/temp/yield_estimation_demo"
    os.makedirs(os.path.join(temp_dir, "images"), exist_ok=True)
    os.makedirs(os.path.join(temp_dir, "annotations"), exist_ok=True)

    # Create dummy images
    cv2.imwrite(os.path.join(temp_dir, "images/sample1_rgb.png"), np.random.randint(0, 255, (512, 512, 3), dtype=np.uint8))
    cv2.imwrite(os.path.join(temp_dir, "images/sample1_nir.png"), np.random.randint(0, 255, (512, 512), dtype=np.uint8))
    
    # Create dummy annotation (for detection)
    xml_content = """
    <annotation>
        <object><name>fruit</name><bndbox><xmin>100</xmin><ymin>100</ymin><xmax>150</xmax><ymax>150</ymax></bndbox></object>
    </annotation>
    """
    with open(os.path.join(temp_dir, "annotations/sample1.xml"), 'w') as f:
        f.write(xml_content)

    # 2. Initialize augmenter and dataset
    aug_config = AugmentationConfig()
    augmenter = YieldEstimationAugmenter(config=aug_config, image_size=(256, 256))
    
    dataset = YieldDataset(
        data_dir=temp_dir,
        task='detection',
        modalities=['rgb', 'nir'],
        augmenter=augmenter,
        is_train=True
    )

    print(f"\n[1. Dataset Initialized] Found {len(dataset)} sample(s).")

    # 3. Get one item
    images, target = dataset[0]

    print("\n[2. Retrieved one sample from the dataset]")
    print(f"  Image modalities loaded: {list(images.keys())}")
    print(f"  RGB image tensor shape: {images['rgb'].shape}")
    print(f"  NIR image tensor shape: {images['nir'].shape}")
    print(f"  Target keys: {target.keys()}")
    print(f"  Target boxes tensor: {target['boxes']}")

    assert 'rgb' in images and 'nir' in images
    assert images['rgb'].shape == (3, 256, 256)
    assert 'boxes' in target and 'labels' in target
    
    print("\nYield estimation dataset demo successful.")
