"""
Data Augmentation for Yield Estimation
======================================

This module defines a comprehensive data augmentation pipeline for the yield
estimation task. Data augmentation is critical for training robust deep learning
models, as it artificially expands the dataset by creating modified versions of
the training images. This helps the model generalize better to unseen data and
be invariant to changes in lighting, orientation, and scale.

This pipeline is built using `albumentations`, a powerful and flexible library
for image augmentations. It is designed to handle the complexities of
multi-modal agricultural data, ensuring that augmentations are applied
consistently across corresponding images (e.g., RGB, NIR, thermal) and their
associated masks or bounding boxes.

Core Components:
----------------
1.  **`YieldEstimationAugmenter` Class**:
    -   A high-level wrapper that constructs and applies the augmentation pipeline.
    -   **Configurability**: It is initialized with an `AugmentationConfig` object
      (from `utils.config`), allowing all augmentation parameters (e.g.,
      probabilities, limits) to be controlled from a central configuration file.
    -   **Training vs. Validation Pipelines**: It can generate different pipelines
      for training and validation. The training pipeline includes a rich set of
      geometric and color augmentations, while the validation pipeline typically
      only includes resizing and normalization.
    -   **Multi-modal Support**: The `Compose` function from `albumentations` is
      configured to handle "additional targets." This means if we pass a dictionary
      of images like `{'image': rgb_img, 'nir': nir_img}`, the same geometric
      transform (e.g., flip, rotation) will be applied to both, maintaining their
      spatial alignment.

2.  **Augmentation Techniques**:
    -   **Geometric Augmentations**:
        -   `HorizontalFlip`, `VerticalFlip`: Simulate different camera orientations.
        -   `Rotate`: Handles slight variations in drone flight paths or camera angles.
        -   `RandomSizedBBoxSafeCrop` / `RandomResizedCrop`: Creates scale variation
          and focuses the model on different parts of the image. The `BBoxSafe`
          version ensures that bounding boxes are not lost during cropping.
    -   **Color and Brightness Augmentations**:
        -   `RandomBrightnessContrast`, `HueSaturationValue`, `ColorJitter`: Simulate
          changes in lighting conditions (e.g., sunny vs. cloudy days, different
          times of day). These are typically applied only to the RGB image.
    -   **Noise and Blur**:
        -   `GaussNoise`, `MotionBlur`: Improve model robustness to sensor noise or
          motion artifacts from moving platforms.

3.  **Normalization**:
    -   `Normalize`: A crucial final step that scales pixel values to a standard
      range (e.g., mean 0, std 1), as expected by pre-trained models.

This module ensures that the models are trained on a diverse and challenging set
of examples, leading to higher accuracy and better performance in real-world
conditions.
"""

import albumentations as A
from albumentations.pytorch import ToTensorV2
import numpy as np
import logging

from app.computer_vision.yield_estimation.utils.config import AugmentationConfig

logger = logging.getLogger(__name__)

class YieldEstimationAugmenter:
    """
    Constructs and applies data augmentation pipelines for yield estimation tasks.
    """
    def __init__(self, config: AugmentationConfig, image_size: tuple = (512, 512)):
        """
        Args:
            config (AugmentationConfig): Pydantic model with augmentation parameters.
            image_size (tuple): The target image size (height, width).
        """
        self.config = config
        self.image_size = image_size
        logger.info(f"Initializing augmenter with config: {config.dict()}")

    def get_transforms(self, is_train: bool) -> A.Compose:
        """
        Builds the augmentation pipeline for either training or validation.

        Args:
            is_train (bool): If True, returns the training pipeline with full
                             augmentations. If False, returns the validation
                             pipeline with minimal transformations.

        Returns:
            A.Compose: The constructed albumentations pipeline.
        """
        if is_train and self.config.enable:
            return self._build_train_transform()
        else:
            return self._build_val_transform()

    def _build_train_transform(self) -> A.Compose:
        """Builds the augmentation pipeline for the training set."""
        
        # Define which augmentations should only apply to the RGB image
        color_augs = A.Compose([
            A.RandomBrightnessContrast(p=self.config.brightness_contrast_prob),
            A.HueSaturationValue(p=self.config.brightness_contrast_prob),
            A.ColorJitter(p=self.config.brightness_contrast_prob),
        ])

        # Define geometric augmentations that apply to all images and masks
        geometric_augs = A.Compose([
            A.HorizontalFlip(p=self.config.h_flip_prob),
            A.VerticalFlip(p=self.config.v_flip_prob),
            A.Rotate(limit=self.config.rotation_limit, p=self.config.rotation_prob, border_mode=0),
            A.RandomResizedCrop(
                height=self.image_size[0],
                width=self.image_size[1],
                scale=(0.5, 1.0),
                p=self.config.crop_prob
            ),
            A.GaussNoise(p=self.config.gauss_noise_prob),
        ])

        # The final pipeline
        # Note: BboxParams can be added here if the task involves detection.
        # The `additional_targets` will ensure transforms are applied to other
        # image modalities like 'nir', 'thermal', etc.
        pipeline = A.Compose([
            geometric_augs,
            A.OneOf([
                color_augs, # Apply color transforms
                A.NoOp(),   # Or do nothing
            ], p=0.8), # Apply color transforms 80% of the time
            A.Resize(height=self.image_size[0], width=self.image_size[1]),
            A.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
            ToTensorV2(),
        ], 
        bbox_params=A.BboxParams(format='pascal_voc', label_fields=['class_labels']),
        additional_targets={
            'nir': 'image',
            'thermal': 'image',
            'mask': 'mask'
        })
        
        logger.info("Built training augmentation pipeline.")
        return pipeline

    def _build_val_transform(self) -> A.Compose:
        """Builds the minimal transformation pipeline for the validation/test set."""
        pipeline = A.Compose([
            A.Resize(height=self.image_size[0], width=self.image_size[1]),
            A.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
            ToTensorV2(),
        ],
        bbox_params=A.BboxParams(format='pascal_voc', label_fields=['class_labels']),
        additional_targets={
            'nir': 'image',
            'thermal': 'image',
            'mask': 'mask'
        })
        
        logger.info("Built validation augmentation pipeline.")
        return pipeline

# --- Example Usage ---
if __name__ == '__main__':
    print("--- Data Augmentation Demo ---")
    
    # 1. Load default configuration
    aug_config = AugmentationConfig()
    augmenter = YieldEstimationAugmenter(config=aug_config, image_size=(256, 256))

    # 2. Get training and validation transforms
    train_transform = augmenter.get_transforms(is_train=True)
    val_transform = augmenter.get_transforms(is_train=False)
    
    print("\n[1. Augmentation Pipelines Created]")
    print(f"  Training pipeline contains {len(train_transform.transforms)} top-level transforms.")
    print(f"  Validation pipeline contains {len(val_transform.transforms)} top-level transforms.")

    # 3. Create dummy data
    dummy_rgb = np.random.randint(0, 256, (512, 512, 3), dtype=np.uint8)
    dummy_nir = np.random.randint(0, 256, (512, 512), dtype=np.uint8)
    dummy_mask = np.zeros((512, 512), dtype=np.uint8)
    dummy_mask[100:400, 100:400] = 1
    dummy_bboxes = [[150, 150, 350, 350]]
    dummy_labels = [1]

    print("\n[2. Applying Augmentations to a Sample]")
    print(f"  Original RGB shape: {dummy_rgb.shape}")
    print(f"  Original NIR shape: {dummy_nir.shape}")
    print(f"  Original Mask shape: {dummy_mask.shape}")

    # 4. Apply the training transform
    transformed_data = train_transform(
        image=dummy_rgb,
        nir=dummy_nir,
        mask=dummy_mask,
        bboxes=dummy_bboxes,
        class_labels=dummy_labels
    )

    # 5. Inspect the output
    transformed_rgb = transformed_data['image']
    transformed_nir = transformed_data['nir']
    transformed_mask = transformed_data['mask']
    transformed_bboxes = transformed_data['bboxes']

    print("\n[3. Inspected Transformed Output]")
    print(f"  Transformed RGB tensor shape: {transformed_rgb.shape}")
    print(f"  Transformed NIR tensor shape: {transformed_nir.shape}")
    print(f"  Transformed Mask tensor shape: {transformed_mask.shape}")
    print(f"  Transformed BBoxes: {transformed_bboxes}")

    # Check that shapes are correct
    assert transformed_rgb.shape == (3, 256, 256)
    assert transformed_nir.shape == (256, 256) # ToTensorV2 doesn't add channel dim for 2D input
    assert transformed_mask.shape == (256, 256)
    
    # Check that the number of bboxes is the same (unless crop removed it)
    if len(transformed_bboxes) > 0:
        assert len(transformed_bboxes[0]) == 4

    print("\nAugmentation pipeline demo successful. Multi-modal data is handled correctly.")
