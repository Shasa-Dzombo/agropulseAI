"""
Data Loading Orchestrator for Yield Estimation
==============================================

This module provides high-level functions to create and manage PyTorch `DataLoader`
instances for the yield estimation tasks. It acts as a bridge between the
configuration system (`utils.config`), the `YieldDataset`, and the main training
script.

By centralizing the data loader creation logic, we ensure that all parts of the
application use the same data pipeline setup, promoting consistency and reducing
boilerplate code in the training and evaluation scripts.

Core Functionalities:
---------------------
1.  **`create_dataloaders` Function**:
    -   This is the main public function of the module.
    -   It takes the global `Settings` object as input, from which it derives all
      necessary configurations for data paths, training parameters (batch size,
      number of workers), and augmentation settings.
    -   It handles the creation of datasets for training, validation, and testing
      by correctly pointing to the respective data subdirectories.
    -   It instantiates the `YieldEstimationAugmenter` and the `YieldDataset` for
      each data split (train, val, test).
    -   It creates and returns a dictionary of `DataLoader` objects, one for each
      split.

2.  **Custom Collate Function (`collate_fn`)**:
    -   Object detection and other complex tasks often produce batches where the
      annotations (targets) have varying sizes (e.g., different numbers of
      bounding boxes per image).
    -   A standard `DataLoader` cannot stack these into a single tensor.
    -   The `collate_fn` is a custom function passed to the `DataLoader` that
      intelligently handles this by collecting images into a list and targets
      into a list, rather than trying to batch them into a tensor. This is the
      standard practice for tasks like object detection in PyTorch.

3.  **Configuration-Driven Setup**:
    -   The entire data loading pipeline is driven by the `Settings` object. This
      means that to change the batch size, image size, or augmentation strategy,
      one only needs to modify the configuration file or environment variables,
      without touching the data loading code.

Usage Example:
--------------
```python
from app.computer_vision.yield_estimation.utils.config import get_settings
from app.computer_vision.yield_estimation.data.loader import create_dataloaders

# 1. Get application settings
settings = get_settings()

# 2. Create data loaders for the 'detection' task
dataloaders = create_dataloaders(
    settings=settings,
    task='detection',
    modalities=['rgb', 'nir']
)

# 3. Use the data loaders in a training loop
train_loader = dataloaders['train']
for images, targets in train_loader:
    # images is a dict of tensors, targets is a list of dicts
    process_batch(images, targets)
```
"""

import torch
from torch.utils.data import DataLoader
from typing import List, Dict, Literal

from app.computer_vision.yield_estimation.utils.config import Settings
from app.computer_vision.yield_estimation.data.dataset import YieldDataset
from app.computer_vision.yield_estimation.data.augmentations import YieldEstimationAugmenter
import logging

logger = logging.getLogger(__name__)

def collate_fn(batch):
    """
    Custom collate function to handle batches with variable-sized targets.
    This is particularly important for object detection tasks.
    """
    # The batch is a list of tuples, where each tuple is (images_dict, target)
    
    # Separate images and targets
    image_dicts = [item[0] for item in batch]
    targets = [item[1] for item in batch]

    # Reorganize the list of image dicts into a dict of lists of images
    collated_images = {}
    if image_dicts:
        for key in image_dicts[0].keys():
            collated_images[key] = [d[key] for d in image_dicts]

    return collated_images, targets


def create_dataloaders(settings: Settings, task: Literal['detection', 'segmentation', 'regression'], modalities: List[str]) -> Dict[str, DataLoader]:
    """
    Creates and returns a dictionary of PyTorch DataLoaders for train, validation, and test sets.

    Args:
        settings (Settings): The global application settings object.
        task (str): The task type ('detection', 'segmentation', 'regression').
        modalities (List[str]): The image modalities to load.

    Returns:
        Dict[str, DataLoader]: A dictionary containing 'train', 'val', and 'test' DataLoaders.
    """
    logger.info(f"Creating dataloaders for task: {task} with modalities: {modalities}")

    # Initialize the augmenter from config
    augmenter = YieldEstimationAugmenter(
        config=settings.augmentation,
        image_size=settings.data.image_size
    )

    dataloaders = {}
    
    for split in ['train', 'val', 'test']:
        data_dir = settings.data.processed_data_dir # Assuming data is split into subdirs
        # In a real scenario, you'd have train/val/test subdirectories
        # For this example, we'll use the same dir but control augmentations
        is_train = (split == 'train')
        
        label_file = os.path.join(settings.data.raw_data_dir, f"{split}_labels.csv") if task == 'regression' else None

        dataset = YieldDataset(
            data_dir=data_dir,
            task=task,
            modalities=modalities,
            augmenter=augmenter,
            is_train=is_train,
            label_file=label_file
        )

        # Use the custom collate_fn for detection tasks
        use_collate_fn = (task == 'detection')

        loader = DataLoader(
            dataset,
            batch_size=settings.train.batch_size if is_train else settings.train.batch_size * 2,
            shuffle=(split == 'train'),
            num_workers=settings.train.num_workers,
            collate_fn=collate_fn if use_collate_fn else None,
            pin_memory=True
        )
        
        dataloaders[split] = loader
        logger.info(f"Created '{split}' dataloader with {len(dataset)} samples.")

    return dataloaders

# --- Example Usage ---
if __name__ == '__main__':
    import os
    import cv2
    import pandas as pd
    from app.computer_vision.yield_estimation.utils.config import get_settings

    print("--- Data Loader Creation Demo ---")

    # 1. Get settings
    settings = get_settings()

    # 2. Create dummy data for the demo
    temp_dir = "c:/temp/yield_loader_demo"
    img_dir = os.path.join(temp_dir, "processed/images")
    ann_dir = os.path.join(temp_dir, "processed/annotations")
    raw_dir = os.path.join(temp_dir, "raw")
    os.makedirs(img_dir, exist_ok=True)
    os.makedirs(ann_dir, exist_ok=True)
    os.makedirs(raw_dir, exist_ok=True)

    # Override data paths in settings for the demo
    settings.data.processed_data_dir = os.path.join(temp_dir, "processed")
    settings.data.raw_data_dir = os.path.join(temp_dir, "raw")
    settings.train.batch_size = 2
    settings.train.num_workers = 0 # Use 0 for main process in simple demos

    # Create dummy files for detection task
    for i in range(4): # 4 samples
        cv2.imwrite(os.path.join(img_dir, f"train_sample_{i}_rgb.png"), np.random.randint(0, 255, (512, 512, 3), dtype=np.uint8))
        xml_content = f"""
        <annotation>
            <object><name>fruit</name><bndbox><xmin>{100+i}</xmin><ymin>100</ymin><xmax>150</xmax><ymax>150</ymax></bndbox></object>
        </annotation>
        """
        with open(os.path.join(ann_dir, f"train_sample_{i}.xml"), 'w') as f:
            f.write(xml_content)
    
    # Create dummy files for regression task
    df = pd.DataFrame({
        'sample_id': [f'train_sample_{i}' for i in range(4)],
        'yield': [10.5, 12.1, 9.8, 11.2]
    })
    df.to_csv(os.path.join(raw_dir, "train_labels.csv"), index=False)
    df.to_csv(os.path.join(raw_dir, "val_labels.csv"), index=False)
    df.to_csv(os.path.join(raw_dir, "test_labels.csv"), index=False)


    # 3. Create dataloaders for a detection task
    print("\n[1. Creating DataLoaders for 'detection' task]")
    detection_loaders = create_dataloaders(settings, task='detection', modalities=['rgb'])
    
    # 4. Fetch one batch from the training loader
    train_loader = detection_loaders['train']
    images_batch, targets_batch = next(iter(train_loader))

    print("\n[2. Inspected one batch from the detection train loader]")
    print(f"  Batch size: {len(images_batch['rgb'])}")
    print(f"  Image tensor shape: {images_batch['rgb'][0].shape}")
    print(f"  Number of targets in batch: {len(targets_batch)}")
    print(f"  First target in batch: {targets_batch[0]}")
    assert len(images_batch['rgb']) == settings.train.batch_size
    assert len(targets_batch) == settings.train.batch_size

    # 5. Create dataloaders for a regression task
    print("\n[3. Creating DataLoaders for 'regression' task]")
    regression_loaders = create_dataloaders(settings, task='regression', modalities=['rgb'])
    
    # 6. Fetch one batch from the regression loader
    reg_train_loader = regression_loaders['train']
    reg_images_batch, reg_targets_batch = next(iter(reg_train_loader))
    
    print("\n[4. Inspected one batch from the regression train loader]")
    print(f"  Batch size: {reg_images_batch['rgb'].shape[0]}")
    print(f"  Image tensor shape: {reg_images_batch['rgb'].shape}")
    print(f"  Targets tensor shape: {reg_targets_batch.shape}")
    print(f"  First target value: {reg_targets_batch[0]}")
    assert reg_images_batch['rgb'].shape[0] == settings.train.batch_size
    assert reg_targets_batch.shape[0] == settings.train.batch_size

    print("\nData loader creation demo successful.")
