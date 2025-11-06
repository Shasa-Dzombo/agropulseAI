"""
Plant Disease Detection using Deep Learning

Comprehensive plant disease detection system using Convolutional Neural Networks.
Supports multiple crop types and disease categories with transfer learning.

Features:
- Multi-class disease classification
- Transfer learning (ResNet, EfficientNet, VGG, MobileNet)
- Data augmentation pipelines
- Model ensemble
- Grad-CAM visualization
- Real-time inference
- Mobile optimization
"""

import os
import numpy as np
import pandas as pd
import logging
from typing import Dict, List, Optional, Tuple, Union
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
import json
import pickle

try:
    import tensorflow as tf
    from tensorflow import keras
    from tensorflow.keras import layers, models, optimizers
    from tensorflow.keras.applications import (
        ResNet50, ResNet101, ResNet152,
        EfficientNetB0, EfficientNetB3, EfficientNetB7,
        MobileNetV2, MobileNetV3Large,
        VGG16, VGG19,
        InceptionV3, InceptionResNetV2
    )
    from tensorflow.keras.preprocessing.image import ImageDataGenerator
    from tensorflow.keras.callbacks import (
        ModelCheckpoint, EarlyStopping, ReduceLROnPlateau,
        TensorBoard, CSVLogger
    )
    TF_AVAILABLE = True
except ImportError:
    TF_AVAILABLE = False
    logging.warning("TensorFlow not available")

try:
    import cv2
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False
    logging.warning("OpenCV not available")

from PIL import Image
import albumentations as A
from sklearn.metrics import classification_report, confusion_matrix
import matplotlib.pyplot as plt
import seaborn as sns


logger = logging.getLogger(__name__)


# Disease taxonomy
CROP_DISEASES = {
    'tomato': [
        'bacterial_spot', 'early_blight', 'late_blight',
        'leaf_mold', 'septoria_leaf_spot', 'spider_mites',
        'target_spot', 'yellow_leaf_curl_virus',
        'mosaic_virus', 'healthy'
    ],
    'potato': [
        'early_blight', 'late_blight', 'healthy'
    ],
    'corn': [
        'cercospora_leaf_spot', 'common_rust', 'northern_leaf_blight',
        'healthy'
    ],
    'rice': [
        'bacterial_blight', 'blast', 'brown_spot',
        'tungro', 'healthy'
    ],
    'wheat': [
        'brown_rust', 'yellow_rust', 'powdery_mildew',
        'septoria', 'tan_spot', 'healthy'
    ],
    'apple': [
        'apple_scab', 'black_rot', 'cedar_apple_rust',
        'healthy'
    ],
    'grape': [
        'black_rot', 'esca', 'leaf_blight', 'healthy'
    ],
    'cotton': [
        'bacterial_blight', 'curl_virus', 'fusarium_wilt',
        'healthy'
    ],
    'soybean': [
        'bacterial_blight', 'downy_mildew', 'frog_eye_leaf_spot',
        'powdery_mildew', 'healthy'
    ],
    'sugarcane': [
        'bacterial_blight', 'red_rot', 'rust', 'healthy'
    ]
}


@dataclass
class DiseaseDetectionResult:
    """Disease detection result"""
    crop_type: str
    disease_class: str
    confidence: float
    top_k_predictions: List[Tuple[str, float]]
    severity: str  # 'mild', 'moderate', 'severe'
    affected_area_percent: Optional[float]
    timestamp: datetime
    image_path: Optional[str] = None
    visualization_path: Optional[str] = None
    treatment_recommendations: List[str] = field(default_factory=list)
    metadata: Dict = field(default_factory=dict)


@dataclass
class ModelPerformance:
    """Model performance metrics"""
    model_name: str
    accuracy: float
    precision: float
    recall: float
    f1_score: float
    per_class_metrics: Dict[str, Dict[str, float]]
    confusion_matrix: np.ndarray
    training_history: Dict
    timestamp: datetime


class DataAugmentationPipeline:
    """
    Advanced data augmentation for plant disease images
    
    Uses Albumentations for high-quality augmentations.
    """
    
    def __init__(
        self,
        image_size: Tuple[int, int] = (224, 224),
        augmentation_strength: str = 'medium'  # 'light', 'medium', 'heavy'
    ):
        self.image_size = image_size
        self.augmentation_strength = augmentation_strength
        
        # Build augmentation pipeline
        if augmentation_strength == 'light':
            self.transform = A.Compose([
                A.Resize(*image_size),
                A.HorizontalFlip(p=0.5),
                A.RandomBrightnessContrast(p=0.3),
                A.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
            ])
        
        elif augmentation_strength == 'medium':
            self.transform = A.Compose([
                A.Resize(*image_size),
                A.HorizontalFlip(p=0.5),
                A.VerticalFlip(p=0.3),
                A.RandomRotate90(p=0.3),
                A.ShiftScaleRotate(shift_limit=0.1, scale_limit=0.2, rotate_limit=45, p=0.5),
                A.RandomBrightnessContrast(brightness_limit=0.2, contrast_limit=0.2, p=0.5),
                A.HueSaturationValue(hue_shift_limit=20, sat_shift_limit=30, val_shift_limit=20, p=0.5),
                A.GaussianBlur(blur_limit=(3, 5), p=0.3),
                A.GaussNoise(var_limit=(10.0, 50.0), p=0.3),
                A.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
            ])
        
        else:  # heavy
            self.transform = A.Compose([
                A.Resize(*image_size),
                A.HorizontalFlip(p=0.5),
                A.VerticalFlip(p=0.5),
                A.RandomRotate90(p=0.5),
                A.ShiftScaleRotate(shift_limit=0.2, scale_limit=0.3, rotate_limit=90, p=0.7),
                A.RandomBrightnessContrast(brightness_limit=0.3, contrast_limit=0.3, p=0.7),
                A.HueSaturationValue(hue_shift_limit=30, sat_shift_limit=40, val_shift_limit=30, p=0.7),
                A.OneOf([
                    A.GaussianBlur(blur_limit=(3, 7), p=1.0),
                    A.MotionBlur(blur_limit=7, p=1.0),
                    A.MedianBlur(blur_limit=7, p=1.0),
                ], p=0.5),
                A.OneOf([
                    A.GaussNoise(var_limit=(10.0, 100.0), p=1.0),
                    A.MultiplicativeNoise(multiplier=[0.8, 1.2], p=1.0),
                ], p=0.5),
                A.CoarseDropout(max_holes=8, max_height=32, max_width=32, p=0.3),
                A.GridDistortion(p=0.3),
                A.OpticalDistortion(p=0.3),
                A.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
            ])
        
        logger.info(f"DataAugmentation pipeline initialized (strength={augmentation_strength})")
    
    def augment(self, image: np.ndarray) -> np.ndarray:
        """Apply augmentation to image"""
        augmented = self.transform(image=image)
        return augmented['image']
    
    def augment_batch(self, images: List[np.ndarray]) -> List[np.ndarray]:
        """Apply augmentation to batch of images"""
        return [self.augment(img) for img in images]


class PlantDiseaseModel:
    """
    Plant disease detection model with transfer learning
    
    Supports multiple architectures and custom training.
    """
    
    def __init__(
        self,
        crop_type: str,
        architecture: str = 'efficientnet_b3',
        input_shape: Tuple[int, int, int] = (224, 224, 3),
        num_classes: Optional[int] = None,
        weights: str = 'imagenet',
        trainable_base: bool = False,
        dropout_rate: float = 0.3
    ):
        """
        Initialize disease detection model
        
        Args:
            crop_type: Type of crop
            architecture: Base architecture
            input_shape: Input image shape
            num_classes: Number of disease classes
            weights: Pre-trained weights
            trainable_base: Whether to train base model
            dropout_rate: Dropout rate
        """
        if not TF_AVAILABLE:
            raise RuntimeError("TensorFlow not available")
        
        self.crop_type = crop_type
        self.architecture = architecture
        self.input_shape = input_shape
        
        # Get disease classes
        if crop_type in CROP_DISEASES:
            self.disease_classes = CROP_DISEASES[crop_type]
            self.num_classes = len(self.disease_classes)
        elif num_classes:
            self.num_classes = num_classes
            self.disease_classes = [f'class_{i}' for i in range(num_classes)]
        else:
            raise ValueError(f"Unknown crop type: {crop_type}")
        
        self.dropout_rate = dropout_rate
        self.model = None
        self.training_history = None
        
        # Build model
        self._build_model(weights, trainable_base)
        
        logger.info(
            f"PlantDiseaseModel initialized (crop={crop_type}, "
            f"arch={architecture}, classes={self.num_classes})"
        )
    
    def _get_base_model(self, weights: str):
        """Get base model architecture"""
        base_models = {
            'resnet50': ResNet50,
            'resnet101': ResNet101,
            'resnet152': ResNet152,
            'efficientnet_b0': EfficientNetB0,
            'efficientnet_b3': EfficientNetB3,
            'efficientnet_b7': EfficientNetB7,
            'mobilenet_v2': MobileNetV2,
            'mobilenet_v3': MobileNetV3Large,
            'vgg16': VGG16,
            'vgg19': VGG19,
            'inception_v3': InceptionV3,
            'inception_resnet_v2': InceptionResNetV2,
        }
        
        if self.architecture not in base_models:
            raise ValueError(f"Unknown architecture: {self.architecture}")
        
        base_model = base_models[self.architecture](
            weights=weights,
            include_top=False,
            input_shape=self.input_shape
        )
        
        return base_model
    
    def _build_model(self, weights: str, trainable_base: bool):
        """Build complete model"""
        # Get base model
        base_model = self._get_base_model(weights)
        base_model.trainable = trainable_base
        
        # Build top layers
        inputs = keras.Input(shape=self.input_shape)
        x = base_model(inputs, training=False)
        x = layers.GlobalAveragePooling2D()(x)
        x = layers.BatchNormalization()(x)
        x = layers.Dropout(self.dropout_rate)(x)
        x = layers.Dense(512, activation='relu')(x)
        x = layers.BatchNormalization()(x)
        x = layers.Dropout(self.dropout_rate)(x)
        x = layers.Dense(256, activation='relu')(x)
        x = layers.BatchNormalization()(x)
        x = layers.Dropout(self.dropout_rate / 2)(x)
        outputs = layers.Dense(self.num_classes, activation='softmax')(x)
        
        self.model = keras.Model(inputs, outputs)
        
        logger.info(
            f"Model built with {self.model.count_params():,} parameters "
            f"({sum([tf.size(w).numpy() for w in base_model.trainable_weights]):,} trainable)"
        )
    
    def compile_model(
        self,
        learning_rate: float = 0.001,
        optimizer: str = 'adam'
    ):
        """Compile model"""
        if optimizer == 'adam':
            opt = optimizers.Adam(learning_rate=learning_rate)
        elif optimizer == 'sgd':
            opt = optimizers.SGD(learning_rate=learning_rate, momentum=0.9, nesterov=True)
        elif optimizer == 'adamw':
            opt = optimizers.experimental.AdamW(learning_rate=learning_rate)
        else:
            raise ValueError(f"Unknown optimizer: {optimizer}")
        
        self.model.compile(
            optimizer=opt,
            loss='categorical_crossentropy',
            metrics=['accuracy', keras.metrics.TopKCategoricalAccuracy(k=3, name='top3_acc')]
        )
        
        logger.info(f"Model compiled with {optimizer} optimizer (lr={learning_rate})")
    
    def train(
        self,
        train_data: Union[tf.data.Dataset, keras.utils.Sequence],
        val_data: Optional[Union[tf.data.Dataset, keras.utils.Sequence]] = None,
        epochs: int = 50,
        batch_size: int = 32,
        callbacks: Optional[List] = None,
        class_weights: Optional[Dict[int, float]] = None
    ) -> Dict:
        """
        Train model
        
        Args:
            train_data: Training data
            val_data: Validation data
            epochs: Number of epochs
            batch_size: Batch size
            callbacks: Keras callbacks
            class_weights: Class weights for imbalanced data
            
        Returns:
            Training history
        """
        if callbacks is None:
            callbacks = [
                EarlyStopping(
                    monitor='val_loss' if val_data else 'loss',
                    patience=10,
                    restore_best_weights=True
                ),
                ReduceLROnPlateau(
                    monitor='val_loss' if val_data else 'loss',
                    factor=0.5,
                    patience=5,
                    min_lr=1e-7
                )
            ]
        
        history = self.model.fit(
            train_data,
            validation_data=val_data,
            epochs=epochs,
            callbacks=callbacks,
            class_weight=class_weights,
            verbose=1
        )
        
        self.training_history = history.history
        
        logger.info("Model training completed")
        return self.training_history
    
    def predict(
        self,
        image: np.ndarray,
        top_k: int = 3
    ) -> DiseaseDetectionResult:
        """
        Predict disease from image
        
        Args:
            image: Input image
            top_k: Number of top predictions to return
            
        Returns:
            Detection result
        """
        # Preprocess image
        if image.shape[:2] != self.input_shape[:2]:
            image = cv2.resize(image, self.input_shape[:2])
        
        # Normalize
        image = image.astype(np.float32) / 255.0
        image = (image - [0.485, 0.456, 0.406]) / [0.229, 0.224, 0.225]
        
        # Add batch dimension
        image_batch = np.expand_dims(image, axis=0)
        
        # Predict
        predictions = self.model.predict(image_batch, verbose=0)[0]
        
        # Get top K predictions
        top_indices = np.argsort(predictions)[-top_k:][::-1]
        top_k_predictions = [
            (self.disease_classes[idx], float(predictions[idx]))
            for idx in top_indices
        ]
        
        # Primary prediction
        disease_class = self.disease_classes[top_indices[0]]
        confidence = float(predictions[top_indices[0]])
        
        # Determine severity based on confidence and disease type
        if disease_class == 'healthy':
            severity = 'none'
        elif confidence > 0.8:
            severity = 'severe'
        elif confidence > 0.6:
            severity = 'moderate'
        else:
            severity = 'mild'
        
        # Generate treatment recommendations
        treatment = self._get_treatment_recommendations(disease_class, severity)
        
        return DiseaseDetectionResult(
            crop_type=self.crop_type,
            disease_class=disease_class,
            confidence=confidence,
            top_k_predictions=top_k_predictions,
            severity=severity,
            affected_area_percent=None,  # Would need segmentation model
            timestamp=datetime.now(),
            treatment_recommendations=treatment
        )
    
    def _get_treatment_recommendations(
        self,
        disease_class: str,
        severity: str
    ) -> List[str]:
        """Generate treatment recommendations"""
        if disease_class == 'healthy':
            return ["Continue regular monitoring", "Maintain current care practices"]
        
        # Generic recommendations (would be disease-specific in production)
        recommendations = [
            f"Disease detected: {disease_class.replace('_', ' ').title()}",
            f"Severity: {severity}",
        ]
        
        if 'blight' in disease_class:
            recommendations.extend([
                "Remove and destroy infected leaves immediately",
                "Apply copper-based fungicide",
                "Improve air circulation",
                "Avoid overhead watering",
                "Consider crop rotation for next season"
            ])
        elif 'rust' in disease_class:
            recommendations.extend([
                "Apply sulfur or copper-based fungicide",
                "Remove heavily infected leaves",
                "Ensure proper plant spacing",
                "Monitor weather conditions"
            ])
        elif 'spot' in disease_class:
            recommendations.extend([
                "Apply appropriate fungicide",
                "Remove infected plant material",
                "Avoid working with wet plants",
                "Improve drainage"
            ])
        elif 'virus' in disease_class:
            recommendations.extend([
                "Remove and destroy infected plants",
                "Control insect vectors",
                "Use virus-resistant varieties",
                "Sanitize tools between plants"
            ])
        elif 'bacterial' in disease_class:
            recommendations.extend([
                "Apply copper-based bactericide",
                "Remove infected plant parts",
                "Avoid overhead irrigation",
                "Disinfect tools regularly"
            ])
        else:
            recommendations.extend([
                "Consult with local agricultural extension",
                "Consider laboratory diagnosis",
                "Monitor disease progression",
                "Isolate affected plants if possible"
            ])
        
        return recommendations
    
    def evaluate(
        self,
        test_data: Union[tf.data.Dataset, keras.utils.Sequence]
    ) -> ModelPerformance:
        """
        Evaluate model performance
        
        Args:
            test_data: Test dataset
            
        Returns:
            Performance metrics
        """
        # Get predictions and labels
        y_true = []
        y_pred = []
        
        for batch in test_data:
            if isinstance(batch, tuple):
                images, labels = batch
            else:
                images = batch
                labels = None
            
            predictions = self.model.predict(images, verbose=0)
            y_pred.extend(np.argmax(predictions, axis=1))
            
            if labels is not None:
                if len(labels.shape) > 1:  # One-hot encoded
                    y_true.extend(np.argmax(labels, axis=1))
                else:
                    y_true.extend(labels)
        
        y_true = np.array(y_true)
        y_pred = np.array(y_pred)
        
        # Calculate metrics
        from sklearn.metrics import accuracy_score, precision_recall_fscore_support
        
        accuracy = accuracy_score(y_true, y_pred)
        precision, recall, f1, _ = precision_recall_fscore_support(
            y_true, y_pred, average='weighted'
        )
        
        # Per-class metrics
        precision_per_class, recall_per_class, f1_per_class, _ = \
            precision_recall_fscore_support(y_true, y_pred, average=None)
        
        per_class_metrics = {}
        for i, class_name in enumerate(self.disease_classes):
            per_class_metrics[class_name] = {
                'precision': float(precision_per_class[i]),
                'recall': float(recall_per_class[i]),
                'f1_score': float(f1_per_class[i])
            }
        
        # Confusion matrix
        cm = confusion_matrix(y_true, y_pred)
        
        return ModelPerformance(
            model_name=f"{self.crop_type}_{self.architecture}",
            accuracy=float(accuracy),
            precision=float(precision),
            recall=float(recall),
            f1_score=float(f1),
            per_class_metrics=per_class_metrics,
            confusion_matrix=cm,
            training_history=self.training_history or {},
            timestamp=datetime.now()
        )
    
    def save(self, save_path: str):
        """Save model"""
        os.makedirs(save_path, exist_ok=True)
        
        # Save model
        self.model.save(os.path.join(save_path, 'model.h5'))
        
        # Save metadata
        metadata = {
            'crop_type': self.crop_type,
            'architecture': self.architecture,
            'input_shape': self.input_shape,
            'num_classes': self.num_classes,
            'disease_classes': self.disease_classes,
            'dropout_rate': self.dropout_rate,
        }
        
        with open(os.path.join(save_path, 'metadata.json'), 'w') as f:
            json.dump(metadata, f, indent=2)
        
        logger.info(f"Model saved to {save_path}")
    
    def load(self, load_path: str):
        """Load model"""
        # Load model
        self.model = keras.models.load_model(os.path.join(load_path, 'model.h5'))
        
        # Load metadata
        with open(os.path.join(load_path, 'metadata.json'), 'r') as f:
            metadata = json.load(f)
        
        self.crop_type = metadata['crop_type']
        self.architecture = metadata['architecture']
        self.input_shape = tuple(metadata['input_shape'])
        self.num_classes = metadata['num_classes']
        self.disease_classes = metadata['disease_classes']
        self.dropout_rate = metadata['dropout_rate']
        
        logger.info(f"Model loaded from {load_path}")


class GradCAMVisualizer:
    """
    Gradient-weighted Class Activation Mapping
    
    Visualizes which parts of the image the model focuses on.
    """
    
    def __init__(self, model: keras.Model, layer_name: Optional[str] = None):
        """
        Initialize Grad-CAM visualizer
        
        Args:
            model: Keras model
            layer_name: Name of convolutional layer to visualize
        """
        self.model = model
        
        # Find last convolutional layer if not specified
        if layer_name is None:
            for layer in reversed(model.layers):
                if len(layer.output_shape) == 4:  # Conv layer
                    layer_name = layer.name
                    break
        
        self.layer_name = layer_name
        self.grad_model = keras.Model(
            inputs=[model.inputs],
            outputs=[model.get_layer(layer_name).output, model.output]
        )
        
        logger.info(f"GradCAM initialized with layer: {layer_name}")
    
    def generate_heatmap(
        self,
        image: np.ndarray,
        class_index: Optional[int] = None
    ) -> np.ndarray:
        """
        Generate Grad-CAM heatmap
        
        Args:
            image: Input image
            class_index: Target class index (uses predicted if None)
            
        Returns:
            Heatmap array
        """
        # Add batch dimension
        image_batch = np.expand_dims(image, axis=0)
        
        # Get gradients
        with tf.GradientTape() as tape:
            conv_outputs, predictions = self.grad_model(image_batch)
            
            if class_index is None:
                class_index = tf.argmax(predictions[0])
            
            class_channel = predictions[:, class_index]
        
        # Compute gradients
        grads = tape.gradient(class_channel, conv_outputs)
        
        # Global average pooling
        pooled_grads = tf.reduce_mean(grads, axis=(0, 1, 2))
        
        # Weight feature maps
        conv_outputs = conv_outputs[0]
        heatmap = conv_outputs @ pooled_grads[..., tf.newaxis]
        heatmap = tf.squeeze(heatmap)
        
        # Normalize heatmap
        heatmap = tf.maximum(heatmap, 0) / tf.math.reduce_max(heatmap)
        heatmap = heatmap.numpy()
        
        return heatmap
    
    def overlay_heatmap(
        self,
        image: np.ndarray,
        heatmap: np.ndarray,
        alpha: float = 0.4,
        colormap: int = cv2.COLORMAP_JET
    ) -> np.ndarray:
        """
        Overlay heatmap on original image
        
        Args:
            image: Original image
            heatmap: Grad-CAM heatmap
            alpha: Overlay transparency
            colormap: OpenCV colormap
            
        Returns:
            Overlayed image
        """
        # Resize heatmap to match image
        heatmap_resized = cv2.resize(heatmap, (image.shape[1], image.shape[0]))
        
        # Convert to 0-255 range
        heatmap_uint8 = np.uint8(255 * heatmap_resized)
        
        # Apply colormap
        heatmap_colored = cv2.applyColorMap(heatmap_uint8, colormap)
        
        # Ensure image is uint8
        if image.dtype != np.uint8:
            image = np.uint8(255 * image)
        
        # Overlay
        superimposed = cv2.addWeighted(image, 1 - alpha, heatmap_colored, alpha, 0)
        
        return superimposed
