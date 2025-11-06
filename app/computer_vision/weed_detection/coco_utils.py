# c:\Users\Codeternal\Desktop\AgroPulse\app\computer_vision\weed_detection\coco_utils.py

"""
COCO-style Dataset Utilities
============================

This module provides utility functions for working with datasets in a way that's
compatible with the COCO (Common Objects in Context) API and evaluation scripts.
These functions are inspired by and adapted from the official PyTorch vision
references for object detection.

The primary purpose of this module is to bridge the gap between a custom PyTorch
`Dataset` and the `pycocotools` library, which expects a specific JSON-like
structure for ground truth data.

Core Components:
----------------
1.  **`get_coco_api_from_dataset(dataset)`**:
    -   **Purpose**: Converts a standard PyTorch `Dataset` into a `COCO` object
      without needing to write an intermediate annotation file to disk.
    -   **Process**:
        -   It iterates through the provided `dataset`.
        -   For each item, it extracts the target information (bounding boxes,
          labels, etc.).
        -   It dynamically builds the `images` and `annotations` lists in the
          format required by the COCO API.
        -   Bounding boxes are converted from `[x_min, y_min, x_max, y_max]` to
          the COCO format `[x_min, y_min, width, height]`.
        -   It creates an in-memory `COCO` object, which can then be used by the
          `CocoEvaluator`.
    -   **Benefit**: This is highly efficient as it avoids disk I/O and allows
      for seamless integration with standard evaluation metrics.

2.  **`convert_to_coco_api(ds)`**:
    -   This is the core conversion function called by `get_coco_api_from_dataset`.
    -   It handles the detailed work of iterating over the dataset, formatting
      each annotation, and ensuring all required fields (`image_id`, `category_id`,
      `bbox`, `area`, `iscrowd`) are correctly populated.
    -   It also prepares the list of categories based on the dataset's class
      information.

This utility is crucial for robust model evaluation, as it allows the use of
the official and widely accepted COCO evaluation protocol (mAP, etc.) on custom
datasets without significant manual effort.
"""

import torch
from pycocotools.coco import COCO
import logging

def convert_to_coco_api(ds):
    """
    Converts a dataset to a COCO-like API object.
    This is an in-memory conversion, avoiding the need to create a JSON file.
    """
    coco_ds = COCO()
    
    # Create the 'images' and 'annotations' lists
    ann_id = 0
    dataset = {"images": [], "annotations": [], "categories": []}
    
    # Assuming the dataset has a method to get category info
    # For example, `ds.get_categories()` which returns a list of dicts
    # like [{'id': 1, 'name': 'weed'}, {'id': 2, 'name': 'crop'}]
    # If not, you might need to manually define this.
    try:
        # This is a placeholder for how you might get categories.
        # You'll need to implement `get_categories` in your WeedDataset class.
        categories = ds.get_categories()
        dataset["categories"] = categories
    except AttributeError:
        logging.warning("Dataset does not have a 'get_categories' method. Using placeholder categories.")
        # Example placeholder if the method doesn't exist
        num_classes = ds.num_classes
        for i in range(num_classes):
             dataset["categories"].append({
                 'id': i + 1, # COCO category IDs are typically 1-indexed
                 'name': f'class_{i+1}',
                 'supercategory': 'object'
             })


    logging.info(f"Converting dataset with {len(ds)} images to COCO format...")

    for img_idx in range(len(ds)):
        # The dataset should return image and target. We only need the target here.
        # We call `get_raw_item` to get data without augmentations
        try:
            img, target = ds.get_raw_item(img_idx)
        except AttributeError:
            # Fallback if get_raw_item is not implemented
            img, target = ds[img_idx]


        image_id = target["image_id"].item()
        
        # Add image info
        dataset["images"].append({"id": image_id, "height": img.shape[1], "width": img.shape[2]})

        boxes = target["boxes"]
        # Convert boxes from [xmin, ymin, xmax, ymax] to [xmin, ymin, width, height]
        boxes[:, 2:] -= boxes[:, :2]
        
        labels = target["labels"].tolist()
        areas = target["area"].tolist()
        iscrowd = target["iscrowd"].tolist()
        
        for i in range(len(labels)):
            ann = {
                "image_id": image_id,
                "bbox": boxes[i].tolist(),
                "category_id": labels[i],
                "area": areas[i],
                "iscrowd": iscrowd[i],
                "id": ann_id,
            }
            dataset["annotations"].append(ann)
            ann_id += 1
            
    logging.info("Conversion finished.")
    
    coco_ds.dataset = dataset
    coco_ds.createIndex()
    return coco_ds


def get_coco_api_from_dataset(dataset):
    """
    Helper function to get the COCO API from a dataset.
    """
    # Check if the dataset has a pre-computed coco object
    if hasattr(dataset, "coco"):
        return dataset.coco

    # If not, create it on the fly
    return convert_to_coco_api(dataset)
```