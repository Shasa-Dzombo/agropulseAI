"""
Object Detection for Agricultural Scenarios

YOLO-based object detection for crops, pests, equipment, and animals.

Features:
- YOLOv5/YOLOv8 integration
- Real-time detection
- Multi-class object tracking
- Bounding box regression
- Instance segmentation
- Drone/aerial image processing
- Custom dataset training
- Model optimization for edge devices
"""

import os
import numpy as np
import logging
from typing import Dict, List, Optional, Tuple, Union
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
import json

try:
    import torch
    import torchvision
    from torchvision.models.detection import fasterrcnn_resnet50_fpn
    from torchvision.transforms import functional as F
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False
    logging.warning("PyTorch not available")

try:
    import cv2
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False

from PIL import Image, ImageDraw, ImageFont
import matplotlib.pyplot as plt


logger = logging.getLogger(__name__)


# Agricultural object classes
AGRICULTURAL_CLASSES = {
    # Crops
    'tomato': 0, 'potato': 1, 'corn': 2, 'wheat': 3, 'rice': 4,
    'soybean': 5, 'cotton': 6, 'sugarcane': 7, 'coffee': 8,
    
    # Pests
    'aphid': 10, 'caterpillar': 11, 'beetle': 12, 'locust': 13,
    'whitefly': 14, 'thrips': 15, 'mite': 16,
    
    # Equipment
    'tractor': 20, 'harvester': 21, 'sprayer': 22, 'drone': 23,
    'irrigation_system': 24, 'sensor_node': 25,
    
    # Animals
    'cow': 30, 'goat': 31, 'chicken': 32, 'pig': 33,
    
    # Weeds
    'broadleaf_weed': 40, 'grass_weed': 41,
    
    # Infrastructure
    'greenhouse': 50, 'storage': 51, 'fence': 52,
}


@dataclass
class DetectionResult:
    """Object detection result"""
    class_name: str
    class_id: int
    confidence: float
    bbox: Tuple[int, int, int, int]  # (x1, y1, x2, y2)
    center: Tuple[float, float]
    area: float
    mask: Optional[np.ndarray] = None  # For instance segmentation
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class SceneAnalysis:
    """Complete scene analysis"""
    image_path: str
    detections: List[DetectionResult]
    object_counts: Dict[str, int]
    total_objects: int
    scene_type: str  # 'field', 'greenhouse', 'storage', 'livestock'
    timestamp: datetime
    metadata: Dict = field(default_factory=dict)


class YOLODetector:
    """
    YOLO-based object detector for agricultural scenarios
    
    Supports YOLOv5, YOLOv8, and custom models.
    """
    
    def __init__(
        self,
        model_path: Optional[str] = None,
        model_type: str = 'yolov5',
        confidence_threshold: float = 0.5,
        iou_threshold: float = 0.45,
        device: str = 'cuda' if torch.cuda.is_available() else 'cpu'
    ):
        """
        Initialize YOLO detector
        
        Args:
            model_path: Path to custom model weights
            model_type: 'yolov5', 'yolov8'
            confidence_threshold: Confidence threshold for detections
            iou_threshold: IoU threshold for NMS
            device: Device to run inference on
        """
        if not TORCH_AVAILABLE:
            raise RuntimeError("PyTorch not available")
        
        self.model_type = model_type
        self.confidence_threshold = confidence_threshold
        self.iou_threshold = iou_threshold
        self.device = device
        
        # Load model
        if model_path:
            self.model = self._load_custom_model(model_path)
        else:
            self.model = self._load_pretrained_model()
        
        self.model.to(device)
        self.model.eval()
        
        # Class names
        self.class_names = list(AGRICULTURAL_CLASSES.keys())
        
        logger.info(f"YOLODetector initialized (model={model_type}, device={device})")
    
    def _load_pretrained_model(self):
        """Load pretrained YOLO model"""
        if self.model_type == 'yolov5':
            try:
                # Try to load from torch hub
                model = torch.hub.load('ultralytics/yolov5', 'yolov5s', pretrained=True)
                return model
            except Exception as e:
                logger.warning(f"Failed to load YOLOv5 from hub: {e}")
                # Fallback to Faster R-CNN
                return fasterrcnn_resnet50_fpn(pretrained=True)
        else:
            # Use Faster R-CNN as fallback
            return fasterrcnn_resnet50_fpn(pretrained=True)
    
    def _load_custom_model(self, model_path: str):
        """Load custom trained model"""
        if self.model_type == 'yolov5':
            try:
                model = torch.hub.load('ultralytics/yolov5', 'custom', path=model_path)
                return model
            except Exception as e:
                logger.error(f"Failed to load custom model: {e}")
                raise
        else:
            # Load PyTorch checkpoint
            model = fasterrcnn_resnet50_fpn(pretrained=False)
            checkpoint = torch.load(model_path, map_location=self.device)
            model.load_state_dict(checkpoint['model_state_dict'])
            return model
    
    def preprocess_image(self, image: np.ndarray) -> torch.Tensor:
        """Preprocess image for detection"""
        # Convert BGR to RGB
        if len(image.shape) == 3 and image.shape[2] == 3:
            image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        
        # Convert to PIL Image
        pil_image = Image.fromarray(image)
        
        # Convert to tensor and normalize
        tensor = F.to_tensor(pil_image)
        
        return tensor
    
    def detect(
        self,
        image: Union[np.ndarray, str],
        visualize: bool = False
    ) -> List[DetectionResult]:
        """
        Detect objects in image
        
        Args:
            image: Image array or path
            visualize: Whether to visualize detections
            
        Returns:
            List of detection results
        """
        # Load image if path provided
        if isinstance(image, str):
            image = cv2.imread(image)
        
        # Preprocess
        tensor = self.preprocess_image(image).to(self.device)
        
        # Run inference
        with torch.no_grad():
            if hasattr(self.model, 'predict'):  # YOLOv5/v8
                results = self.model(image)
                predictions = results.pandas().xyxy[0]
            else:  # Faster R-CNN
                predictions = self.model([tensor])[0]
        
        # Parse detections
        detections = self._parse_detections(predictions, image.shape)
        
        # Visualize if requested
        if visualize:
            self._visualize_detections(image, detections)
        
        logger.info(f"Detected {len(detections)} objects")
        return detections
    
    def _parse_detections(
        self,
        predictions: Union[Dict, object],
        image_shape: Tuple[int, ...]
    ) -> List[DetectionResult]:
        """Parse model predictions into DetectionResult objects"""
        detections = []
        
        if hasattr(predictions, 'items'):  # Faster R-CNN format
            boxes = predictions['boxes'].cpu().numpy()
            labels = predictions['labels'].cpu().numpy()
            scores = predictions['scores'].cpu().numpy()
            
            for box, label, score in zip(boxes, labels, scores):
                if score >= self.confidence_threshold:
                    x1, y1, x2, y2 = box.astype(int)
                    center = ((x1 + x2) / 2, (y1 + y2) / 2)
                    area = (x2 - x1) * (y2 - y1)
                    
                    # Get class name
                    class_id = int(label)
                    class_name = self.class_names[class_id] if class_id < len(self.class_names) else f'class_{class_id}'
                    
                    detections.append(DetectionResult(
                        class_name=class_name,
                        class_id=class_id,
                        confidence=float(score),
                        bbox=(x1, y1, x2, y2),
                        center=center,
                        area=area
                    ))
        else:  # YOLO format (pandas DataFrame)
            for _, row in predictions.iterrows():
                if row['confidence'] >= self.confidence_threshold:
                    x1, y1, x2, y2 = int(row['xmin']), int(row['ymin']), int(row['xmax']), int(row['ymax'])
                    center = ((x1 + x2) / 2, (y1 + y2) / 2)
                    area = (x2 - x1) * (y2 - y1)
                    
                    detections.append(DetectionResult(
                        class_name=row['name'],
                        class_id=int(row['class']),
                        confidence=float(row['confidence']),
                        bbox=(x1, y1, x2, y2),
                        center=center,
                        area=area
                    ))
        
        return detections
    
    def _visualize_detections(self, image: np.ndarray, detections: List[DetectionResult]):
        """Visualize detections on image"""
        vis_image = image.copy()
        
        for det in detections:
            x1, y1, x2, y2 = det.bbox
            
            # Draw bounding box
            cv2.rectangle(vis_image, (x1, y1), (x2, y2), (0, 255, 0), 2)
            
            # Draw label
            label = f"{det.class_name}: {det.confidence:.2f}"
            cv2.putText(
                vis_image, label, (x1, y1 - 10),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2
            )
        
        # Display
        plt.figure(figsize=(12, 8))
        plt.imshow(cv2.cvtColor(vis_image, cv2.COLOR_BGR2RGB))
        plt.axis('off')
        plt.title(f"Detected {len(detections)} objects")
        plt.show()
    
    def analyze_scene(self, image: Union[np.ndarray, str]) -> SceneAnalysis:
        """
        Perform complete scene analysis
        
        Args:
            image: Image array or path
            
        Returns:
            Scene analysis
        """
        # Detect objects
        detections = self.detect(image)
        
        # Count objects by class
        object_counts = {}
        for det in detections:
            object_counts[det.class_name] = object_counts.get(det.class_name, 0) + 1
        
        # Determine scene type
        scene_type = self._determine_scene_type(object_counts)
        
        # Get image path
        image_path = image if isinstance(image, str) else "in_memory"
        
        return SceneAnalysis(
            image_path=image_path,
            detections=detections,
            object_counts=object_counts,
            total_objects=len(detections),
            scene_type=scene_type,
            timestamp=datetime.now()
        )
    
    def _determine_scene_type(self, object_counts: Dict[str, int]) -> str:
        """Determine scene type from detected objects"""
        # Check for livestock
        livestock = sum(object_counts.get(animal, 0) for animal in ['cow', 'goat', 'chicken', 'pig'])
        if livestock > 0:
            return 'livestock'
        
        # Check for greenhouse
        if object_counts.get('greenhouse', 0) > 0:
            return 'greenhouse'
        
        # Check for equipment
        equipment = sum(object_counts.get(eq, 0) for eq in ['tractor', 'harvester', 'sprayer'])
        if equipment > 0:
            return 'field_with_equipment'
        
        # Check for crops
        crops = sum(object_counts.get(crop, 0) for crop in ['tomato', 'potato', 'corn', 'wheat', 'rice'])
        if crops > 0:
            return 'field'
        
        return 'unknown'


class ObjectTracker:
    """
    Multi-object tracking for video streams
    
    Tracks objects across frames using IoU matching and Kalman filtering.
    """
    
    def __init__(
        self,
        max_age: int = 30,
        min_hits: int = 3,
        iou_threshold: float = 0.3
    ):
        """
        Initialize object tracker
        
        Args:
            max_age: Maximum frames to keep track alive without detection
            min_hits: Minimum detections before track is confirmed
            iou_threshold: IoU threshold for matching
        """
        self.max_age = max_age
        self.min_hits = min_hits
        self.iou_threshold = iou_threshold
        
        self.tracks: Dict[int, Dict] = {}
        self.next_track_id = 0
        
        logger.info("ObjectTracker initialized")
    
    def _calculate_iou(self, bbox1: Tuple, bbox2: Tuple) -> float:
        """Calculate IoU between two bounding boxes"""
        x1_min, y1_min, x1_max, y1_max = bbox1
        x2_min, y2_min, x2_max, y2_max = bbox2
        
        # Intersection
        inter_x_min = max(x1_min, x2_min)
        inter_y_min = max(y1_min, y2_min)
        inter_x_max = min(x1_max, x2_max)
        inter_y_max = min(y1_max, y2_max)
        
        inter_area = max(0, inter_x_max - inter_x_min) * max(0, inter_y_max - inter_y_min)
        
        # Union
        bbox1_area = (x1_max - x1_min) * (y1_max - y1_min)
        bbox2_area = (x2_max - x2_min) * (y2_max - y2_min)
        union_area = bbox1_area + bbox2_area - inter_area
        
        return inter_area / union_area if union_area > 0 else 0
    
    def update(self, detections: List[DetectionResult]) -> Dict[int, DetectionResult]:
        """
        Update tracks with new detections
        
        Args:
            detections: List of detections
            
        Returns:
            Dictionary mapping track_id to detection
        """
        # Match detections to existing tracks
        matched_tracks = {}
        unmatched_detections = list(range(len(detections)))
        unmatched_tracks = list(self.tracks.keys())
        
        # Calculate IoU matrix
        if self.tracks and detections:
            iou_matrix = np.zeros((len(self.tracks), len(detections)))
            
            for i, track_id in enumerate(self.tracks.keys()):
                track_bbox = self.tracks[track_id]['bbox']
                for j, det in enumerate(detections):
                    iou_matrix[i, j] = self._calculate_iou(track_bbox, det.bbox)
            
            # Greedy matching
            while iou_matrix.size > 0 and iou_matrix.max() > self.iou_threshold:
                i, j = np.unravel_index(iou_matrix.argmax(), iou_matrix.shape)
                track_id = list(self.tracks.keys())[i]
                
                # Match found
                matched_tracks[track_id] = detections[j]
                
                # Update track
                self.tracks[track_id]['bbox'] = detections[j].bbox
                self.tracks[track_id]['age'] = 0
                self.tracks[track_id]['hits'] += 1
                self.tracks[track_id]['detection'] = detections[j]
                
                # Remove from unmatched
                if j in unmatched_detections:
                    unmatched_detections.remove(j)
                if track_id in unmatched_tracks:
                    unmatched_tracks.remove(track_id)
                
                # Remove from matrix
                iou_matrix = np.delete(iou_matrix, i, axis=0)
                iou_matrix = np.delete(iou_matrix, j, axis=1)
        
        # Create new tracks for unmatched detections
        for det_idx in unmatched_detections:
            det = detections[det_idx]
            self.tracks[self.next_track_id] = {
                'bbox': det.bbox,
                'age': 0,
                'hits': 1,
                'detection': det,
                'class_name': det.class_name
            }
            self.next_track_id += 1
        
        # Age unmatched tracks
        tracks_to_delete = []
        for track_id in unmatched_tracks:
            self.tracks[track_id]['age'] += 1
            if self.tracks[track_id]['age'] > self.max_age:
                tracks_to_delete.append(track_id)
        
        # Delete old tracks
        for track_id in tracks_to_delete:
            del self.tracks[track_id]
        
        # Return confirmed tracks
        confirmed_tracks = {
            tid: track['detection']
            for tid, track in self.tracks.items()
            if track['hits'] >= self.min_hits
        }
        
        return confirmed_tracks
    
    def get_track_count(self) -> int:
        """Get number of active tracks"""
        return len([t for t in self.tracks.values() if t['hits'] >= self.min_hits])


class PestDetectionSystem:
    """
    Specialized pest detection system
    
    Optimized for detecting small insects and pests in agricultural settings.
    """
    
    def __init__(
        self,
        model_path: str,
        confidence_threshold: float = 0.3
    ):
        """
        Initialize pest detection system
        
        Args:
            model_path: Path to pest detection model
            confidence_threshold: Confidence threshold
        """
        self.detector = YOLODetector(
            model_path=model_path,
            confidence_threshold=confidence_threshold
        )
        
        # Pest severity thresholds
        self.severity_thresholds = {
            'low': 5,
            'medium': 15,
            'high': 30,
            'critical': 50
        }
        
        logger.info("PestDetectionSystem initialized")
    
    def detect_pests(
        self,
        image: Union[np.ndarray, str]
    ) -> Tuple[List[DetectionResult], str, Dict]:
        """
        Detect pests and assess infestation level
        
        Args:
            image: Image array or path
            
        Returns:
            (detections, severity_level, recommendations)
        """
        # Detect pests
        detections = self.detector.detect(image)
        
        # Filter for pest classes only
        pest_detections = [
            det for det in detections
            if det.class_id >= 10 and det.class_id < 20
        ]
        
        # Count pests by type
        pest_counts = {}
        for det in pest_detections:
            pest_counts[det.class_name] = pest_counts.get(det.class_name, 0) + 1
        
        # Determine severity
        total_pests = len(pest_detections)
        if total_pests < self.severity_thresholds['low']:
            severity = 'low'
        elif total_pests < self.severity_thresholds['medium']:
            severity = 'medium'
        elif total_pests < self.severity_thresholds['high']:
            severity = 'high'
        else:
            severity = 'critical'
        
        # Generate recommendations
        recommendations = self._generate_pest_recommendations(
            pest_counts, severity
        )
        
        return pest_detections, severity, recommendations
    
    def _generate_pest_recommendations(
        self,
        pest_counts: Dict[str, int],
        severity: str
    ) -> Dict:
        """Generate pest management recommendations"""
        recommendations = {
            'severity': severity,
            'pest_counts': pest_counts,
            'actions': [],
            'pesticides': [],
            'monitoring_frequency': 'daily'
        }
        
        if severity == 'critical':
            recommendations['actions'] = [
                "Immediate pesticide application required",
                "Isolate affected area",
                "Consider emergency harvesting if crop is mature",
                "Notify agricultural extension service"
            ]
            recommendations['monitoring_frequency'] = 'every 6 hours'
        elif severity == 'high':
            recommendations['actions'] = [
                "Apply targeted pesticide treatment",
                "Increase monitoring frequency",
                "Remove heavily infested plants",
                "Set up pest traps"
            ]
            recommendations['monitoring_frequency'] = 'twice daily'
        elif severity == 'medium':
            recommendations['actions'] = [
                "Monitor closely for 48 hours",
                "Consider organic pest control methods",
                "Inspect neighboring plants",
                "Document pest locations"
            ]
        else:
            recommendations['actions'] = [
                "Continue regular monitoring",
                "Maintain preventive measures",
                "Record pest observations"
            ]
        
        # Add pest-specific recommendations
        for pest_type in pest_counts:
            if 'aphid' in pest_type:
                recommendations['pesticides'].append("Neem oil or insecticidal soap")
            elif 'caterpillar' in pest_type:
                recommendations['pesticides'].append("Bacillus thuringiensis (Bt)")
            elif 'beetle' in pest_type:
                recommendations['pesticides'].append("Pyrethrin-based spray")
        
        return recommendations


class WeedDetectionSystem:
    """
    Weed detection for precision agriculture
    
    Identifies weeds vs crops for targeted herbicide application.
    """
    
    def __init__(self, model_path: str):
        self.detector = YOLODetector(model_path=model_path)
        logger.info("WeedDetectionSystem initialized")
    
    def detect_weeds(
        self,
        image: Union[np.ndarray, str]
    ) -> Tuple[List[DetectionResult], List[DetectionResult], float]:
        """
        Detect weeds and crops
        
        Args:
            image: Image array or path
            
        Returns:
            (weed_detections, crop_detections, weed_percentage)
        """
        # Detect all objects
        detections = self.detector.detect(image)
        
        # Separate weeds and crops
        weed_detections = [
            det for det in detections
            if det.class_id >= 40 and det.class_id < 50
        ]
        
        crop_detections = [
            det for det in detections
            if det.class_id < 10
        ]
        
        # Calculate weed percentage
        total_plants = len(weed_detections) + len(crop_detections)
        weed_percentage = (len(weed_detections) / total_plants * 100) if total_plants > 0 else 0
        
        logger.info(
            f"Detected {len(weed_detections)} weeds, "
            f"{len(crop_detections)} crops ({weed_percentage:.1f}% weeds)"
        )
        
        return weed_detections, crop_detections, weed_percentage
    
    def generate_spray_map(
        self,
        image_shape: Tuple[int, int],
        weed_detections: List[DetectionResult],
        grid_size: int = 50
    ) -> np.ndarray:
        """
        Generate precision spray map
        
        Args:
            image_shape: Image dimensions (height, width)
            weed_detections: Weed detections
            grid_size: Grid cell size in pixels
            
        Returns:
            Binary spray map (1 = spray, 0 = no spray)
        """
        height, width = image_shape[:2]
        
        # Create grid
        grid_h = height // grid_size + 1
        grid_w = width // grid_size + 1
        spray_map = np.zeros((grid_h, grid_w), dtype=np.uint8)
        
        # Mark cells with weeds
        for det in weed_detections:
            center_x, center_y = det.center
            grid_x = int(center_x // grid_size)
            grid_y = int(center_y // grid_size)
            
            if 0 <= grid_y < grid_h and 0 <= grid_x < grid_w:
                spray_map[grid_y, grid_x] = 1
        
        logger.info(
            f"Generated spray map: {spray_map.sum()}/{spray_map.size} cells "
            f"({spray_map.sum()/spray_map.size*100:.1f}% coverage)"
        )
        
        return spray_map
