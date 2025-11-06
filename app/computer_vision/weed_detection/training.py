# c:\Users\Codeternal\Desktop\AgroPulse\app\computer_vision\weed_detection\training.py

"""
Main Training Orchestrator for Weed Detection
=============================================

This script serves as the main entry point for training a weed detection model.
It orchestrates the entire training pipeline, from data loading and model
creation to the training loop and final model saving.

Key Responsibilities:
---------------------
1.  **Configuration Management**:
    -   Uses `argparse` to define and parse command-line arguments, allowing for
      flexible configuration of the training process.
    -   Key configurations include dataset paths, model architecture, learning
      rate, batch size, number of epochs, and device selection (CPU/GPU).

2.  **Data Pipeline Setup**:
    -   Initializes the `WeedDataset` with the specified training and validation
      data paths.
    -   Creates `DetectionAugmenter` to apply data augmentation.
    -   Sets up PyTorch `DataLoader`s for both training and validation sets,
      using the custom `collate_fn` to handle batches of images and targets of
      varying sizes.

3.  **Model Initialization**:
    -   Uses the `WeedDetectionModelFactory` to create the specified object
      detection model (e.g., 'fasterrcnn_resnet50_fpn').
    -   The model is automatically configured for the number of classes present
      in the dataset.
    -   Moves the model to the selected device (e.g., 'cuda' if available).

4.  **Optimizer and Scheduler Setup**:
    -   Configures an optimizer (e.g., SGD) with the specified learning rate,
      momentum, and weight decay.
    -   Sets up a learning rate scheduler (e.g., `StepLR`) to adjust the learning
      rate during training, which is crucial for effective convergence.

5.  **Training and Evaluation Loop**:
    -   Iterates for the specified number of epochs.
    -   In each epoch, it calls the `train_one_epoch` function from the `engine`
      module to perform one full pass over the training data.
    -   After training, it calls the `evaluate` function from the `engine` to
      measure the model's performance on the validation set.
    -   The evaluation results, particularly the mAP, are used to track the
      best performing model.

6.  **Model Checkpointing**:
    -   Saves a checkpoint of the model, optimizer state, and other relevant info
      at the end of each epoch.
    -   Keeps track of the best model based on validation mAP and saves a
      separate 'best_model.pth' file, ensuring the best-performing version is
      preserved.

Usage Example:
--------------
```bash
python training.py \\
    --data-path /path/to/weed_dataset \\
    --model-name fasterrcnn_resnet50_fpn \\
    --epochs 25 \\
    --batch-size 4 \\
    --learning-rate 0.005 \\
    --output-dir /path/to/save/models
```
"""

import os
import argparse
import torch
import torch.utils.data
from torch.optim.lr_scheduler import StepLR
import logging

from data_loader import WeedDataset, DetectionAugmenter, collate_fn
from models import WeedDetectionModelFactory
from engine import train_one_epoch, evaluate
from coco_utils import get_coco_api_from_dataset

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def get_args_parser():
    """
    Defines and parses command-line arguments for the training script.
    """
    parser = argparse.ArgumentParser(description="Weed Detection Model Training")
    
    # Data and Model paths
    parser.add_argument('--data-path', required=True, help='Path to the root of the dataset')
    parser.add_argument('--output-dir', default='outputs', help='Path to save model checkpoints and logs')
    
    # Model configuration
    parser.add_argument('--model-name', default='fasterrcnn_resnet50_fpn',
                        choices=['fasterrcnn_resnet50_fpn', 'fasterrcnn_mobilenet_v3_large_fpn', 'ssd300_vgg16', 'retinanet_resnet50_fpn'],
                        help='Name of the object detection model to train')
    
    # Training parameters
    parser.add_argument('--device', default='cuda', help='Device to use for training (cuda or cpu)')
    parser.add_argument('--epochs', default=30, type=int, help='Number of training epochs')
    parser.add_argument('--batch-size', default=4, type=int, help='Batch size for training')
    parser.add_argument('--learning-rate', default=0.005, type=float, help='Initial learning rate')
    parser.add_argument('--momentum', default=0.9, type=float, help='Momentum for SGD optimizer')
    parser.add_argument('--weight-decay', default=0.0005, type=float, help='Weight decay for SGD optimizer')
    parser.add_argument('--lr-step-size', default=8, type=int, help='Step size for LR scheduler')
    parser.add_argument('--lr-gamma', default=0.1, type=float, help='Gamma for LR scheduler')
    
    # Other settings
    parser.add_argument('--num-workers', default=4, type=int, help='Number of workers for data loading')
    parser.add_argument('--print-freq', default=20, type=int, help='Frequency of printing training stats')
    parser.add_argument('--resume', default='', help='Path to checkpoint to resume training from')

    return parser

def main(args):
    """
    Main training function.
    """
    # --- Setup ---
    if not os.path.exists(args.output_dir):
        os.makedirs(args.output_dir)

    device = torch.device(args.device if torch.cuda.is_available() else "cpu")
    logging.info(f"Using device: {device}")

    # --- Data Loading ---
    logging.info("Loading data...")
    
    # Define paths for training and validation sets
    train_images_dir = os.path.join(args.data_path, 'images', 'train')
    train_annots_dir = os.path.join(args.data_path, 'annotations', 'train')
    val_images_dir = os.path.join(args.data_path, 'images', 'val')
    val_annots_dir = os.path.join(args.data_path, 'annotations', 'val')

    # Create datasets
    train_augmenter = DetectionAugmenter(image_size=(512, 512), is_train=True)
    dataset_train = WeedDataset(
        image_dir=train_images_dir, 
        annotation_dir=train_annots_dir, 
        augmenter=train_augmenter
    )

    val_augmenter = DetectionAugmenter(image_size=(512, 512), is_train=False)
    dataset_val = WeedDataset(
        image_dir=val_images_dir, 
        annotation_dir=val_annots_dir, 
        augmenter=val_augmenter
    )

    logging.info(f"Found {len(dataset_train)} images in the training set.")
    logging.info(f"Found {len(dataset_val)} images in the validation set.")

    # Create data loaders
    data_loader_train = torch.utils.data.DataLoader(
        dataset_train, batch_size=args.batch_size, shuffle=True, num_workers=args.num_workers,
        collate_fn=collate_fn
    )
    data_loader_val = torch.utils.data.DataLoader(
        dataset_val, batch_size=1, shuffle=False, num_workers=args.num_workers,
        collate_fn=collate_fn
    )

    # --- Model Initialization ---
    logging.info(f"Creating model: {args.model_name}")
    # The number of classes is the size of the class map from the dataset.
    # The class map from the taxonomy already includes the '__background__' class.
    num_classes = len(dataset_train.class_map)
    model_factory = WeedDetectionModelFactory(num_classes=num_classes)
    model = model_factory.create_model(args.model_name, pretrained=True)
    model.to(device)

    # --- Optimizer and Scheduler ---
    params = [p for p in model.parameters() if p.requires_grad]
    optimizer = torch.optim.SGD(
        params, lr=args.learning_rate, momentum=args.momentum, weight_decay=args.weight_decay
    )
    lr_scheduler = StepLR(optimizer, step_size=args.lr_step_size, gamma=args.lr_gamma)

    # --- Training Loop ---
    logging.info("Starting training...")
    start_epoch = 0
    best_map = 0.0

    # Optional: Resume from checkpoint
    if args.resume:
        if os.path.isfile(args.resume):
            logging.info(f"Loading checkpoint '{args.resume}'")
            checkpoint = torch.load(args.resume, map_location=device)
            model.load_state_dict(checkpoint['model_state_dict'])
            optimizer.load_state_dict(checkpoint['optimizer_state_dict'])
            lr_scheduler.load_state_dict(checkpoint['scheduler_state_dict'])
            start_epoch = checkpoint['epoch'] + 1
            best_map = checkpoint.get('best_map', 0.0)
            logging.info(f"Resumed from epoch {start_epoch}")
        else:
            logging.warning(f"Checkpoint file not found at '{args.resume}'")


    for epoch in range(start_epoch, args.epochs):
        # Train for one epoch
        train_one_epoch(model, optimizer, data_loader_train, device, epoch, args.print_freq)
        
        # Update the learning rate
        lr_scheduler.step()
        
        # Evaluate on the validation set
        coco_evaluator = evaluate(model, data_loader_val, device=device)
        
        # Extract the main mAP metric to track performance
        # This is typically the first value in the stats summary
        current_map = coco_evaluator.coco_eval['bbox'].stats[0]
        
        logging.info(f"Epoch {epoch} - mAP@0.5:0.95: {current_map:.4f}")

        # --- Save Checkpoint ---
        checkpoint_path = os.path.join(args.output_dir, f'checkpoint_epoch_{epoch}.pth')
        save_dict = {
            'epoch': epoch,
            'model_state_dict': model.state_dict(),
            'optimizer_state_dict': optimizer.state_dict(),
            'scheduler_state_dict': lr_scheduler.state_dict(),
            'args': args,
            'best_map': best_map
        }
        torch.save(save_dict, checkpoint_path)
        
        # Save the best model
        if current_map > best_map:
            best_map = current_map
            best_model_path = os.path.join(args.output_dir, 'best_model.pth')
            logging.info(f"New best model found with mAP: {best_map:.4f}. Saving to {best_model_path}")
            torch.save({
                'model_state_dict': model.state_dict(),
                'args': args,
                'map': best_map
            }, best_model_path)

    logging.info("Training finished.")


if __name__ == "__main__":
    parser = get_args_parser()
    args = parser.parse_args()
    main(args)
```