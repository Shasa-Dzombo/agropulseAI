# c:\Users\Codeternal\Desktop\AgroPulse\app\computer_vision\weed_detection\data_loader.py

"""
Data Loader and Augmentation for Weed Detection
===============================================

This module provides a robust data loading and augmentation pipeline for training
weed detection models. Object detection tasks require careful handling of images
and their corresponding bounding box annotations. This module is designed to
work with datasets in the popular PASCAL VOC format and provides a suite of
data augmentation techniques specifically tailored for object detection.

Core Components:
---------------
1.  **`WeedDataset`**:
    -   A custom PyTorch `Dataset` class for loading images and their annotations.
    -   It parses XML annotation files in the PASCAL VOC format to extract
      bounding boxes and class labels for each object (e.g., 'weed', 'crop').
    -   It maps class names to integer indices for model training.
    -   It is designed to be used with a `DataLoader` for efficient, batched
      data loading during training.

2.  **`AnnotationParser`**:
    -   A utility class responsible for parsing the PASCAL VOC XML files.
    -   It extracts the image size, and for each object, its name and bounding
      box coordinates (`xmin`, `ymin`, `xmax`, `ymax`).
    -   This decouples the parsing logic from the dataset class, making it
      easier to support other annotation formats in the future.

3.  **`DetectionAugmenter`**:
    -   A wrapper around the powerful `albumentations` library to apply a
      sequence of augmentations to both the image and its bounding boxes.
    -   **Importance of Coordinated Augmentation**: When an image is augmented
      (e.g., flipped, rotated, scaled), the bounding boxes must be transformed
      in the exact same way to remain valid. `albumentations` handles this
      automatically.
    -   **Supported Augmentations**:
        -   Geometric: Horizontal flips, rotations, scaling, cropping.
        -   Color: Changes in brightness, contrast, saturation, and hue.
        -   Noise and Blur: Adding random noise or applying blur to improve
          model robustness.
    -   The augmenter is configurable, allowing different augmentation strategies
      for training and validation (typically, only resizing is done for validation).

4.  **`collate_fn`**:
    -   A custom collate function for the PyTorch `DataLoader`.
    -   When creating a batch of data, images can have different numbers of
      objects. This function handles the variable-sized annotations by
      collecting them into lists, rather than trying to stack them into a
      single tensor. This is the standard way to handle object detection
      targets in PyTorch.

This module ensures that the model receives well-formed, augmented, and batched
data, which is a critical prerequisite for successful object detector training.
"""

import os
import xml.etree.ElementTree as ET
import torch
from torch.utils.data import Dataset, DataLoader
import cv2
import numpy as np
import albumentations as A
from albumentations.pytorch import ToTensorV2
from typing import List, Dict, Tuple, Any, Callable

from app.computer_vision.weed_detection.taxonomy import get_class_map

import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Annotation Parsing ---

class AnnotationParser:
    """Parses PASCAL VOC XML annotation files."""

    @staticmethod
    def parse_xml(xml_path: str) -> Dict[str, Any]:
        """
        Parses a single XML file to extract bounding boxes and labels.

        Args:
            xml_path (str): The path to the XML annotation file.

        Returns:
            Dict[str, Any]: A dictionary containing 'boxes' and 'labels'.
                            'boxes' is a list of [xmin, ymin, xmax, ymax] lists.
                            'labels' is a list of object class names.
        """
        if not os.path.exists(xml_path):
            raise FileNotFoundError(f"Annotation file not found: {xml_path}")

        tree = ET.parse(xml_path)
        root = tree.getroot()

        boxes = []
        labels = []

        for member in root.findall('object'):
            label = member.find('name').text
            
            bndbox = member.find('bndbox')
            xmin = int(bndbox.find('xmin').text)
            ymin = int(bndbox.find('ymin').text)
            xmax = int(bndbox.find('xmax').text)
            ymax = int(bndbox.find('ymax').text)
            
            boxes.append([xmin, ymin, xmax, ymax])
            labels.append(label)
            
        return {'boxes': boxes, 'labels': labels}

# --- Augmentations ---

class DetectionAugmenter:
    """
    Applies augmentations to images and bounding boxes using albumentations.
    """
    def __init__(self, image_size: Tuple[int, int], is_train: bool = True):
        """
        Args:
            image_size (Tuple[int, int]): The target image size (height, width).
            is_train (bool): If True, applies a full set of augmentations.
                             If False, applies only resizing and normalization.
        """
        self.image_size = image_size
        self.is_train = is_train
        self.transform = self._get_transform()
        logging.info(f"Initialized DetectionAugmenter for {'training' if is_train else 'validation'}.")

    def _get_transform(self) -> A.Compose:
        """Constructs the albumentations transformation pipeline."""
        if self.is_train:
            # A rich set of augmentations for training
            return A.Compose([
                A.HorizontalFlip(p=0.5),
                A.RandomBrightnessContrast(p=0.3),
                A.HueSaturationValue(p=0.3),
                A.ColorJitter(p=0.3),
                A.GaussNoise(p=0.2),
                A.OneOf([
                    A.MotionBlur(p=0.2),
                    A.MedianBlur(blur_limit=3, p=0.1),
                    A.Blur(blur_limit=3, p=0.1),
                ], p=0.3),
                A.Rotate(limit=30, p=0.3, border_mode=cv2.BORDER_CONSTANT),
                # RandomSizedBBoxSafeCrop is great for detection as it ensures
                # that the crop contains at least one bounding box.
                A.RandomSizedBBoxSafeCrop(height=self.image_size[0], width=self.image_size[1], erosion_rate=0.2, p=0.5),
                A.Resize(height=self.image_size[0], width=self.image_size[1]),
                A.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
                ToTensorV2(),
            ], bbox_params=A.BboxParams(format='pascal_voc', label_fields=['class_labels']))
        else:
            # A minimal set of transformations for validation/testing
            return A.Compose([
                A.Resize(height=self.image_size[0], width=self.image_size[1]),
                A.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
                ToTensorV2(),
            ], bbox_params=A.BboxParams(format='pascal_voc', label_fields=['class_labels']))

    def __call__(self, image: np.ndarray, boxes: List[List[int]], labels: List[int]) -> Dict[str, Any]:
        """
        Applies the transform to an image and its annotations.

        Args:
            image (np.ndarray): The input image (H, W, C).
            boxes (List[List[int]]): List of bounding boxes.
            labels (List[int]): List of class labels (as integers).

        Returns:
            Dict[str, Any]: A dictionary containing the transformed 'image',
                            'boxes', and 'class_labels'.
        """
        return self.transform(image=image, bboxes=boxes, class_labels=labels)

# --- Dataset Class ---

class WeedDataset(Dataset):
    """
    A PyTorch Dataset for loading weed detection data.
    """
    def __init__(self, image_dir: str, annotation_dir: str, augmenter: DetectionAugmenter):
        """
        Args:
            image_dir (str): Directory containing the images.
            annotation_dir (str): Directory containing the XML annotations.
            augmenter (DetectionAugmenter): The augmentation pipeline to use.
        """
        self.image_dir = image_dir
        self.annotation_dir = annotation_dir
        self.augmenter = augmenter
        
        # Generate class map dynamically from the taxonomy
        self.class_map = get_class_map()
        self.class_names = {v: k for k, v in self.class_map.items()}
        logging.info(f"Using {len(self.class_map)} classes from taxonomy.")

        # Get a sorted list of image filenames (without extension)
        self.image_filenames = sorted([os.path.splitext(f)[0] for f in os.listdir(image_dir) if f.endswith(('.jpg', '.jpeg', '.png'))])
        
        logging.info(f"Found {len(self.image_filenames)} images in {image_dir}")

    def __len__(self) -> int:
        return len(self.image_filenames)

    def __getitem__(self, idx: int) -> Tuple[torch.Tensor, Dict[str, torch.Tensor]]:
        """
        Retrieves and processes one sample from the dataset.

        Args:
            idx (int): The index of the sample.

        Returns:
            Tuple[torch.Tensor, Dict[str, torch.Tensor]]:
                - The transformed image tensor.
                - A target dictionary containing 'boxes' and 'labels' tensors.
        """
        image_filename = self.image_filenames[idx]
        image_path = os.path.join(self.image_dir, f"{image_filename}.jpg") # Assuming .jpg, can be improved
        xml_path = os.path.join(self.annotation_dir, f"{image_filename}.xml")

        # Load image
        image = cv2.imread(image_path)
        if image is None:
            # Try other extensions if .jpg fails
            for ext in ['.jpeg', '.png']:
                image_path = os.path.join(self.image_dir, f"{image_filename}{ext}")
                image = cv2.imread(image_path)
                if image is not None:
                    break
            if image is None:
                logging.error(f"Could not read image: {image_filename}")
                # Return a dummy sample to avoid crashing the loader
                return torch.zeros((3, *self.augmenter.image_size)), {}

        image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

        # Parse annotations
        annotations = AnnotationParser.parse_xml(xml_path)
        boxes = annotations['boxes']
        labels_str = annotations['labels']
        
        # Convert string labels to integer indices
        # Handle cases where an annotation might not be in our detailed taxonomy
        labels_int = [self.class_map[label] for label in labels_str if label in self.class_map]
        
        # Filter boxes to match the labels that were kept
        boxes_filtered = [box for i, box in enumerate(boxes) if labels_str[i] in self.class_map]

        if not boxes_filtered:
            # If no valid objects are found in this image, return an empty sample
            return self.return_empty_sample()

        # Apply augmentations
        transformed = self.augmenter(image=image, boxes=boxes_filtered, labels=labels_int)
        
        image_tensor = transformed['image']
        
        # Prepare target dictionary
        target = {}
        # Ensure boxes are float tensors and have at least one box
        if len(transformed['bboxes']) > 0:
            target['boxes'] = torch.as_tensor(transformed['bboxes'], dtype=torch.float32)
            target['labels'] = torch.as_tensor(transformed['class_labels'], dtype=torch.int64)
        else:
            # If augmentations remove all boxes, return empty tensors
            target['boxes'] = torch.empty((0, 4), dtype=torch.float32)
            target['labels'] = torch.empty((0,), dtype=torch.int64)
            
        return image_tensor, target

    def return_empty_sample(self) -> Tuple[torch.Tensor, Dict[str, torch.Tensor]]:
        """Returns a dummy sample for images with no valid annotations."""
        image_tensor = torch.zeros((3, *self.augmenter.image_size))
        target = {
            'boxes': torch.empty((0, 4), dtype=torch.float32),
            'labels': torch.empty((0,), dtype=torch.int64)
        }
        return image_tensor, target

# --- Collate Function ---

def collate_fn(batch: List[Tuple]) -> Tuple[List, List]:
    """
    Custom collate function for the DataLoader to handle variable-sized targets.
    """
    images = [item[0] for item in batch if item[0] is not None]
    targets = [item[1] for item in batch if item[1] is not None]
    return images, targets

# --- Example Usage ---
if __name__ == '__main__':
    print("--- Weed Detection Data Loader Demo ---")

    # 1. Create a dummy dataset for demonstration
    temp_dir = "c:/temp/weed_detection_demo"
    image_dir = os.path.join(temp_dir, "images")
    anno_dir = os.path.join(temp_dir, "annotations")
    os.makedirs(image_dir, exist_ok=True)
    os.makedirs(anno_dir, exist_ok=True)

    # Define a sample of weeds from our taxonomy for the demo
    demo_weeds = list(get_class_map().keys())[1:4] # Get first 3 weeds, skipping background
    if not demo_weeds:
        demo_weeds = ['common_lambsquarters', 'redroot_pigweed', 'velvetleaf']


    # Create a dummy image and annotation
    for i in range(5):
        img = np.zeros((512, 512, 3), dtype=np.uint8)
        img[:] = (40, 50, 60) # Soil background
        
        # Add a "weed"
        weed_name = demo_weeds[i % len(demo_weeds)]
        cv2.rectangle(img, (100, 100), (200, 200), (0, 180, 0), -1)
        
        img_path = os.path.join(image_dir, f"dummy_img_{i}.jpg")
        cv2.imwrite(img_path, img)

        # Create corresponding XML annotation
        xml_content = f"""
        <annotation>
            <folder>images</folder>
            <filename>dummy_img_{i}.jpg</filename>
            <size>
                <width>512</width>
                <height>512</height>
                <depth>3</depth>
            </size>
            <object>
                <name>{weed_name}</name>
                <bndbox>
                    <xmin>100</xmin>
                    <ymin>100</ymin>
                    <xmax>200</xmax>
                    <ymax>200</ymax>
                </bndbox>
            </object>
        </annotation>
        """
        xml_path = os.path.join(anno_dir, f"dummy_img_{i}.xml")
        with open(xml_path, 'w') as f:
            f.write(xml_content)

    print(f"Created dummy dataset in: {temp_dir}")

    # 2. Initialize augmenter and dataset
    image_size = (416, 416)
    train_augmenter = DetectionAugmenter(image_size=image_size, is_train=True)
    
    try:
        weed_dataset = WeedDataset(
            image_dir=image_dir,
            annotation_dir=anno_dir,
            augmenter=train_augmenter
        )

        # 3. Create a DataLoader
        batch_size = 2
        data_loader = DataLoader(
            weed_dataset,
            batch_size=batch_size,
            shuffle=True,
            collate_fn=collate_fn
        )

        print(f"\nInitialized Dataset with {len(weed_dataset)} samples.")
        print(f"Initialized DataLoader with batch size {batch_size}.")

        # 4. Fetch and inspect one batch
        images, targets = next(iter(data_loader))

        print(f"\n--- Inspecting one batch ---")
        print(f"Batch contains {len(images)} images.")
        
        # Check image tensor shape
        img_tensor = images[0]
        print(f"Image tensor shape: {img_tensor.shape}")
        assert img_tensor.shape == (3, image_size[0], image_size[1])
        
        # Check target format
        target_sample = targets[0]
        print(f"Target for first image: {target_sample}")
        assert 'boxes' in target_sample
        assert 'labels' in target_sample
        assert isinstance(target_sample['boxes'], torch.Tensor)
        assert isinstance(target_sample['labels'], torch.Tensor)
        
        print("\nData loader demo successful. The pipeline is correctly preparing batched data for training.")

    except Exception as e:
        logging.error(f"An error occurred during the data loader demo: {e}", exc_info=True)
```