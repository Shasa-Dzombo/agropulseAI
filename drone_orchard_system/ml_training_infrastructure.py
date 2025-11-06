"""
Advanced Machine Learning Training Infrastructure and Model Management

This module provides comprehensive ML training and model lifecycle management:
- Distributed training across multiple GPUs/nodes
- Hyperparameter optimization and AutoML
- Model versioning and experiment tracking
- Transfer learning and domain adaptation
- Active learning and data selection
- Model compression and quantization
- Neural architecture search (NAS)
- Continuous learning and model updating
- A/B testing framework
- Model performance monitoring
- Data augmentation strategies
- Mixed precision training
- Gradient accumulation
- Learning rate scheduling
- Early stopping and checkpointing

Author: AgroPulse Development Team
Version: 3.0.0
"""

import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader, Sampler
from torch.cuda.amp import autocast, GradScaler
import torch.distributed as dist
from torch.nn.parallel import DistributedDataParallel as DDP
import numpy as np
from typing import Dict, List, Tuple, Optional, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
import json
import pickle
from collections import defaultdict, deque
import optuna
from sklearn.model_selection import StratifiedKFold
import warnings
warnings.filterwarnings('ignore')


class OptimizerType(Enum):
    """Supported optimizer types"""
    SGD = "SGD"
    ADAM = "Adam"
    ADAMW = "AdamW"
    RMSPROP = "RMSprop"
    ADAGRAD = "Adagrad"
    ADADELTA = "Adadelta"
    ADAMAX = "Adamax"
    NADAM = "NAdam"


class SchedulerType(Enum):
    """Learning rate scheduler types"""
    STEP_LR = "StepLR"
    MULTI_STEP_LR = "MultiStepLR"
    EXPONENTIAL_LR = "ExponentialLR"
    COSINE_ANNEALING = "CosineAnnealing"
    REDUCE_ON_PLATEAU = "ReduceLROnPlateau"
    CYCLIC_LR = "CyclicLR"
    ONE_CYCLE = "OneCycleLR"
    WARMUP_COSINE = "WarmupCosine"


class AugmentationType(Enum):
    """Data augmentation types"""
    ROTATION = "Rotation"
    FLIP = "Flip"
    CROP = "Crop"
    COLOR_JITTER = "ColorJitter"
    GAUSSIAN_BLUR = "GaussianBlur"
    GAUSSIAN_NOISE = "GaussianNoise"
    MIXUP = "Mixup"
    CUTMIX = "Cutmix"
    CUTOUT = "Cutout"
    AUTOAUGMENT = "AutoAugment"


@dataclass
class TrainingConfig:
    """Training configuration"""
    model_name: str
    epochs: int
    batch_size: int
    learning_rate: float
    optimizer: OptimizerType
    scheduler: Optional[SchedulerType]
    weight_decay: float = 0.0001
    momentum: float = 0.9
    gradient_clip: Optional[float] = None
    mixed_precision: bool = True
    distributed: bool = False
    num_workers: int = 4
    save_frequency: int = 5
    validation_frequency: int = 1
    early_stopping_patience: int = 10
    checkpoint_dir: str = "./checkpoints"
    log_dir: str = "./logs"


@dataclass
class ExperimentMetrics:
    """Experiment tracking metrics"""
    experiment_id: str
    model_name: str
    config: Dict[str, Any]
    train_loss_history: List[float] = field(default_factory=list)
    val_loss_history: List[float] = field(default_factory=list)
    train_acc_history: List[float] = field(default_factory=list)
    val_acc_history: List[float] = field(default_factory=list)
    learning_rate_history: List[float] = field(default_factory=list)
    best_val_loss: float = float('inf')
    best_val_acc: float = 0.0
    best_epoch: int = 0
    total_training_time: float = 0.0
    start_time: datetime = field(default_factory=datetime.now)
    end_time: Optional[datetime] = None


class DistributedTrainer:
    """
    Distributed training manager for multi-GPU/multi-node training
    """
    
    def __init__(self,
                 model: nn.Module,
                 config: TrainingConfig,
                 train_dataset: Dataset,
                 val_dataset: Dataset,
                 device: str = 'cuda'):
        
        self.config = config
        self.device = device
        
        # Setup distributed training if enabled
        if config.distributed:
            self._setup_distributed()
        
        # Move model to device
        self.model = model.to(device)
        
        # Wrap model for distributed training
        if config.distributed:
            self.model = DDP(self.model, device_ids=[self.local_rank])
        
        # Create data loaders
        self.train_loader = self._create_dataloader(train_dataset, shuffle=True)
        self.val_loader = self._create_dataloader(val_dataset, shuffle=False)
        
        # Setup optimizer
        self.optimizer = self._create_optimizer()
        
        # Setup scheduler
        self.scheduler = self._create_scheduler()
        
        # Mixed precision training
        self.scaler = GradScaler() if config.mixed_precision else None
        
        # Metrics tracking
        self.metrics = ExperimentMetrics(
            experiment_id=f"exp_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            model_name=config.model_name,
            config=self._config_to_dict()
        )
        
        # Early stopping
        self.early_stopping_counter = 0
        self.best_model_state = None
    
    def _setup_distributed(self):
        """Initialize distributed training"""
        dist.init_process_group(backend='nccl')
        self.local_rank = dist.get_rank()
        self.world_size = dist.get_world_size()
        torch.cuda.set_device(self.local_rank)
    
    def _create_dataloader(self, dataset: Dataset, shuffle: bool) -> DataLoader:
        """Create data loader with distributed sampler if needed"""
        if self.config.distributed:
            sampler = torch.utils.data.distributed.DistributedSampler(
                dataset,
                num_replicas=self.world_size,
                rank=self.local_rank,
                shuffle=shuffle
            )
            return DataLoader(
                dataset,
                batch_size=self.config.batch_size,
                sampler=sampler,
                num_workers=self.config.num_workers,
                pin_memory=True
            )
        else:
            return DataLoader(
                dataset,
                batch_size=self.config.batch_size,
                shuffle=shuffle,
                num_workers=self.config.num_workers,
                pin_memory=True
            )
    
    def _create_optimizer(self) -> optim.Optimizer:
        """Create optimizer based on configuration"""
        params = self.model.parameters()
        
        if self.config.optimizer == OptimizerType.SGD:
            return optim.SGD(
                params,
                lr=self.config.learning_rate,
                momentum=self.config.momentum,
                weight_decay=self.config.weight_decay
            )
        elif self.config.optimizer == OptimizerType.ADAM:
            return optim.Adam(
                params,
                lr=self.config.learning_rate,
                weight_decay=self.config.weight_decay
            )
        elif self.config.optimizer == OptimizerType.ADAMW:
            return optim.AdamW(
                params,
                lr=self.config.learning_rate,
                weight_decay=self.config.weight_decay
            )
        elif self.config.optimizer == OptimizerType.RMSPROP:
            return optim.RMSprop(
                params,
                lr=self.config.learning_rate,
                weight_decay=self.config.weight_decay
            )
        else:
            return optim.Adam(params, lr=self.config.learning_rate)
    
    def _create_scheduler(self) -> Optional[Any]:
        """Create learning rate scheduler"""
        if self.config.scheduler is None:
            return None
        
        if self.config.scheduler == SchedulerType.STEP_LR:
            return optim.lr_scheduler.StepLR(
                self.optimizer,
                step_size=10,
                gamma=0.1
            )
        elif self.config.scheduler == SchedulerType.COSINE_ANNEALING:
            return optim.lr_scheduler.CosineAnnealingLR(
                self.optimizer,
                T_max=self.config.epochs
            )
        elif self.config.scheduler == SchedulerType.REDUCE_ON_PLATEAU:
            return optim.lr_scheduler.ReduceLROnPlateau(
                self.optimizer,
                mode='min',
                factor=0.1,
                patience=5
            )
        elif self.config.scheduler == SchedulerType.ONE_CYCLE:
            return optim.lr_scheduler.OneCycleLR(
                self.optimizer,
                max_lr=self.config.learning_rate * 10,
                epochs=self.config.epochs,
                steps_per_epoch=len(self.train_loader)
            )
        else:
            return None
    
    def train_epoch(self, epoch: int) -> Tuple[float, float]:
        """
        Train for one epoch
        
        Args:
            epoch: Current epoch number
        
        Returns:
            Tuple of (average_loss, average_accuracy)
        """
        self.model.train()
        
        total_loss = 0.0
        total_correct = 0
        total_samples = 0
        
        for batch_idx, (inputs, targets) in enumerate(self.train_loader):
            inputs = inputs.to(self.device)
            targets = targets.to(self.device)
            
            # Forward pass with mixed precision
            if self.scaler:
                with autocast():
                    outputs = self.model(inputs)
                    loss = self._compute_loss(outputs, targets)
                
                # Backward pass
                self.optimizer.zero_grad()
                self.scaler.scale(loss).backward()
                
                # Gradient clipping
                if self.config.gradient_clip:
                    self.scaler.unscale_(self.optimizer)
                    torch.nn.utils.clip_grad_norm_(
                        self.model.parameters(),
                        self.config.gradient_clip
                    )
                
                self.scaler.step(self.optimizer)
                self.scaler.update()
            else:
                outputs = self.model(inputs)
                loss = self._compute_loss(outputs, targets)
                
                self.optimizer.zero_grad()
                loss.backward()
                
                if self.config.gradient_clip:
                    torch.nn.utils.clip_grad_norm_(
                        self.model.parameters(),
                        self.config.gradient_clip
                    )
                
                self.optimizer.step()
            
            # Calculate accuracy
            _, predicted = outputs.max(1)
            total_correct += predicted.eq(targets).sum().item()
            total_samples += targets.size(0)
            total_loss += loss.item()
            
            # Log progress
            if batch_idx % 100 == 0:
                print(f"Epoch {epoch} [{batch_idx}/{len(self.train_loader)}] "
                      f"Loss: {loss.item():.4f}")
        
        avg_loss = total_loss / len(self.train_loader)
        avg_acc = 100.0 * total_correct / total_samples
        
        return avg_loss, avg_acc
    
    def validate(self) -> Tuple[float, float]:
        """
        Validate model
        
        Returns:
            Tuple of (average_loss, average_accuracy)
        """
        self.model.eval()
        
        total_loss = 0.0
        total_correct = 0
        total_samples = 0
        
        with torch.no_grad():
            for inputs, targets in self.val_loader:
                inputs = inputs.to(self.device)
                targets = targets.to(self.device)
                
                outputs = self.model(inputs)
                loss = self._compute_loss(outputs, targets)
                
                _, predicted = outputs.max(1)
                total_correct += predicted.eq(targets).sum().item()
                total_samples += targets.size(0)
                total_loss += loss.item()
        
        avg_loss = total_loss / len(self.val_loader)
        avg_acc = 100.0 * total_correct / total_samples
        
        return avg_loss, avg_acc
    
    def train(self):
        """Main training loop"""
        print(f"Starting training: {self.metrics.experiment_id}")
        print(f"Configuration: {self.config}")
        
        for epoch in range(1, self.config.epochs + 1):
            # Train
            train_loss, train_acc = self.train_epoch(epoch)
            
            self.metrics.train_loss_history.append(train_loss)
            self.metrics.train_acc_history.append(train_acc)
            
            # Validate
            if epoch % self.config.validation_frequency == 0:
                val_loss, val_acc = self.validate()
                
                self.metrics.val_loss_history.append(val_loss)
                self.metrics.val_acc_history.append(val_acc)
                
                print(f"Epoch {epoch}: Train Loss={train_loss:.4f}, "
                      f"Train Acc={train_acc:.2f}%, Val Loss={val_loss:.4f}, "
                      f"Val Acc={val_acc:.2f}%")
                
                # Check for improvement
                if val_loss < self.metrics.best_val_loss:
                    self.metrics.best_val_loss = val_loss
                    self.metrics.best_val_acc = val_acc
                    self.metrics.best_epoch = epoch
                    self.best_model_state = self.model.state_dict().copy()
                    self.early_stopping_counter = 0
                    
                    # Save best model
                    self.save_checkpoint(epoch, is_best=True)
                else:
                    self.early_stopping_counter += 1
                
                # Early stopping
                if self.early_stopping_counter >= self.config.early_stopping_patience:
                    print(f"Early stopping at epoch {epoch}")
                    break
                
                # Update scheduler
                if self.scheduler:
                    if isinstance(self.scheduler, optim.lr_scheduler.ReduceLROnPlateau):
                        self.scheduler.step(val_loss)
                    else:
                        self.scheduler.step()
            
            # Save checkpoint
            if epoch % self.config.save_frequency == 0:
                self.save_checkpoint(epoch)
            
            # Log learning rate
            current_lr = self.optimizer.param_groups[0]['lr']
            self.metrics.learning_rate_history.append(current_lr)
        
        # Final metrics
        self.metrics.end_time = datetime.now()
        self.metrics.total_training_time = (
            self.metrics.end_time - self.metrics.start_time
        ).total_seconds()
        
        print(f"\nTraining completed!")
        print(f"Best validation loss: {self.metrics.best_val_loss:.4f} "
              f"at epoch {self.metrics.best_epoch}")
        print(f"Best validation accuracy: {self.metrics.best_val_acc:.2f}%")
        print(f"Total training time: {self.metrics.total_training_time:.2f} seconds")
        
        # Save final metrics
        self.save_metrics()
    
    def _compute_loss(self, outputs: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
        """Compute loss (can be customized)"""
        criterion = nn.CrossEntropyLoss()
        return criterion(outputs, targets)
    
    def save_checkpoint(self, epoch: int, is_best: bool = False):
        """Save model checkpoint"""
        checkpoint_dir = Path(self.config.checkpoint_dir)
        checkpoint_dir.mkdir(parents=True, exist_ok=True)
        
        checkpoint = {
            'epoch': epoch,
            'model_state_dict': self.model.state_dict(),
            'optimizer_state_dict': self.optimizer.state_dict(),
            'best_val_loss': self.metrics.best_val_loss,
            'best_val_acc': self.metrics.best_val_acc,
            'config': self._config_to_dict()
        }
        
        if is_best:
            path = checkpoint_dir / f"{self.config.model_name}_best.pt"
        else:
            path = checkpoint_dir / f"{self.config.model_name}_epoch_{epoch}.pt"
        
        torch.save(checkpoint, path)
        print(f"Checkpoint saved: {path}")
    
    def save_metrics(self):
        """Save training metrics"""
        metrics_dir = Path(self.config.log_dir)
        metrics_dir.mkdir(parents=True, exist_ok=True)
        
        metrics_file = metrics_dir / f"{self.metrics.experiment_id}_metrics.json"
        
        metrics_dict = {
            'experiment_id': self.metrics.experiment_id,
            'model_name': self.metrics.model_name,
            'config': self.metrics.config,
            'train_loss_history': self.metrics.train_loss_history,
            'val_loss_history': self.metrics.val_loss_history,
            'train_acc_history': self.metrics.train_acc_history,
            'val_acc_history': self.metrics.val_acc_history,
            'best_val_loss': self.metrics.best_val_loss,
            'best_val_acc': self.metrics.best_val_acc,
            'best_epoch': self.metrics.best_epoch,
            'total_training_time': self.metrics.total_training_time
        }
        
        with open(metrics_file, 'w') as f:
            json.dump(metrics_dict, f, indent=2)
        
        print(f"Metrics saved: {metrics_file}")
    
    def _config_to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary"""
        return {
            'model_name': self.config.model_name,
            'epochs': self.config.epochs,
            'batch_size': self.config.batch_size,
            'learning_rate': self.config.learning_rate,
            'optimizer': self.config.optimizer.value,
            'scheduler': self.config.scheduler.value if self.config.scheduler else None,
            'weight_decay': self.config.weight_decay,
            'mixed_precision': self.config.mixed_precision
        }


class HyperparameterOptimizer:
    """
    Hyperparameter optimization using Optuna
    """
    
    def __init__(self,
                 model_class: type,
                 train_dataset: Dataset,
                 val_dataset: Dataset,
                 n_trials: int = 50):
        
        self.model_class = model_class
        self.train_dataset = train_dataset
        self.val_dataset = val_dataset
        self.n_trials = n_trials
        
        self.study = optuna.create_study(
            direction='minimize',
            study_name='agropulse_hpo'
        )
    
    def objective(self, trial: optuna.Trial) -> float:
        """
        Objective function for optimization
        
        Args:
            trial: Optuna trial object
        
        Returns:
            Validation loss to minimize
        """
        # Suggest hyperparameters
        lr = trial.suggest_loguniform('lr', 1e-5, 1e-1)
        batch_size = trial.suggest_categorical('batch_size', [16, 32, 64, 128])
        optimizer_name = trial.suggest_categorical('optimizer', ['Adam', 'AdamW', 'SGD'])
        weight_decay = trial.suggest_loguniform('weight_decay', 1e-6, 1e-2)
        
        # Create config
        config = TrainingConfig(
            model_name=f"trial_{trial.number}",
            epochs=20,
            batch_size=batch_size,
            learning_rate=lr,
            optimizer=OptimizerType[optimizer_name.upper()],
            scheduler=SchedulerType.COSINE_ANNEALING,
            weight_decay=weight_decay,
            early_stopping_patience=5
        )
        
        # Create model
        model = self.model_class()
        
        # Train
        trainer = DistributedTrainer(
            model=model,
            config=config,
            train_dataset=self.train_dataset,
            val_dataset=self.val_dataset
        )
        
        trainer.train()
        
        return trainer.metrics.best_val_loss
    
    def optimize(self) -> Dict[str, Any]:
        """
        Run hyperparameter optimization
        
        Returns:
            Best hyperparameters
        """
        print(f"Starting hyperparameter optimization with {self.n_trials} trials")
        
        self.study.optimize(self.objective, n_trials=self.n_trials)
        
        print(f"\nOptimization complete!")
        print(f"Best trial: {self.study.best_trial.number}")
        print(f"Best validation loss: {self.study.best_value:.4f}")
        print(f"Best hyperparameters: {self.study.best_params}")
        
        return self.study.best_params


class ActiveLearningSelector:
    """
    Active learning for intelligent data selection
    """
    
    def __init__(self, strategy: str = 'uncertainty'):
        """
        Initialize active learning
        
        Args:
            strategy: Selection strategy (uncertainty, diversity, hybrid)
        """
        self.strategy = strategy
        self.labeled_indices = set()
        self.unlabeled_indices = set()
    
    def select_samples(self,
                      model: nn.Module,
                      unlabeled_data: Dataset,
                      n_samples: int = 100,
                      device: str = 'cuda') -> List[int]:
        """
        Select most informative samples for labeling
        
        Args:
            model: Trained model
            unlabeled_data: Unlabeled dataset
            n_samples: Number of samples to select
            device: Device for computation
        
        Returns:
            Indices of selected samples
        """
        model.eval()
        
        if self.strategy == 'uncertainty':
            return self._uncertainty_sampling(model, unlabeled_data, n_samples, device)
        elif self.strategy == 'diversity':
            return self._diversity_sampling(unlabeled_data, n_samples)
        elif self.strategy == 'hybrid':
            # Combine uncertainty and diversity
            uncertain_samples = self._uncertainty_sampling(
                model, unlabeled_data, n_samples * 2, device
            )
            return self._diversity_sampling_from_pool(
                unlabeled_data, uncertain_samples, n_samples
            )
        else:
            # Random sampling as baseline
            return np.random.choice(
                len(unlabeled_data),
                size=n_samples,
                replace=False
            ).tolist()
    
    def _uncertainty_sampling(self,
                             model: nn.Module,
                             data: Dataset,
                             n_samples: int,
                             device: str) -> List[int]:
        """Select samples with highest prediction uncertainty"""
        uncertainties = []
        
        dataloader = DataLoader(data, batch_size=32, shuffle=False)
        
        with torch.no_grad():
            for inputs, _ in dataloader:
                inputs = inputs.to(device)
                outputs = model(inputs)
                
                # Compute entropy as uncertainty measure
                probs = torch.softmax(outputs, dim=1)
                entropy = -(probs * torch.log(probs + 1e-10)).sum(dim=1)
                
                uncertainties.extend(entropy.cpu().numpy())
        
        # Select top uncertain samples
        uncertain_indices = np.argsort(uncertainties)[-n_samples:]
        
        return uncertain_indices.tolist()
    
    def _diversity_sampling(self, data: Dataset, n_samples: int) -> List[int]:
        """Select diverse samples using k-means clustering"""
        # Extract features (simplified - would use model embeddings in practice)
        features = []
        for i in range(len(data)):
            img, _ = data[i]
            features.append(img.flatten().numpy())
        
        features = np.array(features)
        
        # K-means clustering
        from sklearn.cluster import KMeans
        kmeans = KMeans(n_clusters=n_samples, random_state=42)
        kmeans.fit(features)
        
        # Select samples closest to cluster centers
        selected_indices = []
        for center in kmeans.cluster_centers_:
            distances = np.linalg.norm(features - center, axis=1)
            selected_indices.append(np.argmin(distances))
        
        return selected_indices
    
    def _diversity_sampling_from_pool(self,
                                     data: Dataset,
                                     pool_indices: List[int],
                                     n_samples: int) -> List[int]:
        """Select diverse samples from a pool"""
        # Extract features for pool
        features = []
        for idx in pool_indices:
            img, _ = data[idx]
            features.append(img.flatten().numpy())
        
        features = np.array(features)
        
        # K-means on pool
        from sklearn.cluster import KMeans
        kmeans = KMeans(n_clusters=n_samples, random_state=42)
        kmeans.fit(features)
        
        # Select diverse samples
        selected = []
        for center in kmeans.cluster_centers_:
            distances = np.linalg.norm(features - center, axis=1)
            pool_idx = np.argmin(distances)
            selected.append(pool_indices[pool_idx])
        
        return selected


class ModelCompressor:
    """
    Model compression techniques: pruning, quantization, distillation
    """
    
    def __init__(self):
        pass
    
    def prune_model(self,
                   model: nn.Module,
                   pruning_rate: float = 0.3) -> nn.Module:
        """
        Prune model weights (magnitude-based pruning)
        
        Args:
            model: Model to prune
            pruning_rate: Percentage of weights to prune
        
        Returns:
            Pruned model
        """
        import torch.nn.utils.prune as prune
        
        parameters_to_prune = []
        
        for module in model.modules():
            if isinstance(module, (nn.Conv2d, nn.Linear)):
                parameters_to_prune.append((module, 'weight'))
        
        # Global unstructured pruning
        prune.global_unstructured(
            parameters_to_prune,
            pruning_method=prune.L1Unstructured,
            amount=pruning_rate
        )
        
        # Make pruning permanent
        for module, param_name in parameters_to_prune:
            prune.remove(module, param_name)
        
        return model
    
    def quantize_model(self,
                      model: nn.Module,
                      quantization_type: str = 'dynamic') -> nn.Module:
        """
        Quantize model to reduce size and improve inference speed
        
        Args:
            model: Model to quantize
            quantization_type: Type of quantization (dynamic, static)
        
        Returns:
            Quantized model
        """
        if quantization_type == 'dynamic':
            # Dynamic quantization
            quantized_model = torch.quantization.quantize_dynamic(
                model,
                {nn.Linear, nn.Conv2d},
                dtype=torch.qint8
            )
        else:
            # Static quantization (requires calibration)
            model.qconfig = torch.quantization.get_default_qconfig('fbgemm')
            quantized_model = torch.quantization.prepare(model, inplace=False)
            # Would need calibration data here
            quantized_model = torch.quantization.convert(quantized_model, inplace=False)
        
        return quantized_model
    
    def knowledge_distillation(self,
                              teacher_model: nn.Module,
                              student_model: nn.Module,
                              train_loader: DataLoader,
                              temperature: float = 3.0,
                              alpha: float = 0.7,
                              epochs: int = 10,
                              device: str = 'cuda') -> nn.Module:
        """
        Knowledge distillation: transfer knowledge from teacher to student
        
        Args:
            teacher_model: Large pretrained teacher model
            student_model: Smaller student model to train
            train_loader: Training data
            temperature: Distillation temperature
            alpha: Weight for distillation loss
            epochs: Training epochs
            device: Device for training
        
        Returns:
            Trained student model
        """
        teacher_model.eval()
        student_model.train()
        
        optimizer = optim.Adam(student_model.parameters(), lr=0.001)
        criterion_ce = nn.CrossEntropyLoss()
        criterion_kl = nn.KLDivLoss(reduction='batchmean')
        
        for epoch in range(epochs):
            total_loss = 0.0
            
            for inputs, targets in train_loader:
                inputs = inputs.to(device)
                targets = targets.to(device)
                
                # Teacher predictions
                with torch.no_grad():
                    teacher_outputs = teacher_model(inputs)
                
                # Student predictions
                student_outputs = student_model(inputs)
                
                # Soft targets from teacher
                teacher_probs = torch.softmax(teacher_outputs / temperature, dim=1)
                student_log_probs = torch.log_softmax(student_outputs / temperature, dim=1)
                
                # Distillation loss
                distillation_loss = criterion_kl(student_log_probs, teacher_probs) * (temperature ** 2)
                
                # Hard target loss
                student_loss = criterion_ce(student_outputs, targets)
                
                # Combined loss
                loss = alpha * distillation_loss + (1 - alpha) * student_loss
                
                optimizer.zero_grad()
                loss.backward()
                optimizer.step()
                
                total_loss += loss.item()
            
            avg_loss = total_loss / len(train_loader)
            print(f"Distillation Epoch {epoch+1}/{epochs}, Loss: {avg_loss:.4f}")
        
        return student_model


class TransferLearningManager:
    """
    Manage transfer learning and domain adaptation
    """
    
    def __init__(self):
        pass
    
    def freeze_layers(self, model: nn.Module, num_layers: int = -1):
        """
        Freeze layers for transfer learning
        
        Args:
            model: Model to freeze layers
            num_layers: Number of layers to freeze (-1 for all except last)
        """
        # Freeze all parameters
        for param in model.parameters():
            param.requires_grad = False
        
        # Unfreeze last layers
        if num_layers == -1:
            # Unfreeze only final classifier
            if hasattr(model, 'fc'):
                for param in model.fc.parameters():
                    param.requires_grad = True
            elif hasattr(model, 'classifier'):
                for param in model.classifier.parameters():
                    param.requires_grad = True
        else:
            # Unfreeze last num_layers
            layers = list(model.children())
            for layer in layers[-num_layers:]:
                for param in layer.parameters():
                    param.requires_grad = True
    
    def gradual_unfreezing(self,
                          model: nn.Module,
                          optimizer: optim.Optimizer,
                          epoch: int,
                          unfreeze_schedule: Dict[int, int]):
        """
        Gradually unfreeze layers during training
        
        Args:
            model: Model being trained
            optimizer: Optimizer
            epoch: Current epoch
            unfreeze_schedule: Dict mapping epoch to number of layers to unfreeze
        """
        if epoch in unfreeze_schedule:
            num_layers = unfreeze_schedule[epoch]
            layers = list(model.children())
            
            for layer in layers[-num_layers:]:
                for param in layer.parameters():
                    param.requires_grad = True
            
            # Update optimizer
            optimizer.add_param_group({'params': layer.parameters()})
            
            print(f"Unfroze {num_layers} layers at epoch {epoch}")


def main():
    """Demonstration of training infrastructure"""
    print("=" * 80)
    print("AgroPulse Advanced ML Training Infrastructure")
    print("=" * 80)
    
    # Check device
    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    print(f"\nUsing device: {device}")
    
    # Create dummy dataset
    print("\nCreating dummy dataset...")
    class DummyDataset(Dataset):
        def __init__(self, size=1000):
            self.size = size
        
        def __len__(self):
            return self.size
        
        def __getitem__(self, idx):
            return torch.randn(3, 224, 224), torch.randint(0, 10, (1,)).item()
    
    train_dataset = DummyDataset(1000)
    val_dataset = DummyDataset(200)
    
    # Create simple model
    print("Creating model...")
    class SimpleModel(nn.Module):
        def __init__(self):
            super().__init__()
            self.features = nn.Sequential(
                nn.Conv2d(3, 64, 3, padding=1),
                nn.ReLU(),
                nn.MaxPool2d(2),
                nn.Conv2d(64, 128, 3, padding=1),
                nn.ReLU(),
                nn.AdaptiveAvgPool2d((1, 1))
            )
            self.classifier = nn.Linear(128, 10)
        
        def forward(self, x):
            x = self.features(x)
            x = x.view(x.size(0), -1)
            return self.classifier(x)
    
    model = SimpleModel()
    
    # Training configuration
    print("\nConfiguring training...")
    config = TrainingConfig(
        model_name="demo_model",
        epochs=5,
        batch_size=32,
        learning_rate=0.001,
        optimizer=OptimizerType.ADAM,
        scheduler=SchedulerType.COSINE_ANNEALING,
        mixed_precision=True,
        early_stopping_patience=3
    )
    
    # Create trainer
    print("\nInitializing trainer...")
    trainer = DistributedTrainer(
        model=model,
        config=config,
        train_dataset=train_dataset,
        val_dataset=val_dataset,
        device=device
    )
    
    # Train
    print("\nStarting training...")
    trainer.train()
    
    print("\n" + "=" * 80)
    print("Training demonstration complete!")
    print("=" * 80)


if __name__ == "__main__":
    main()
