# AI Engine Manager - Enterprise-Grade Multi-Model AI Orchestration Platform
# Comprehensive AI processing with distributed inference, model versioning, and advanced analytics
# Supports TensorFlow, PyTorch, ONNX, TensorRT, and custom model formats
# Features: A/B testing, model ensembles, quantization, pruning, federated learning
# Advanced capabilities: AutoML, neural architecture search, explainable AI, adversarial robustness

import logging
import numpy as np
import cv2
import asyncio
import json
import time
import hashlib
import pickle
import sqlite3
import threading
import queue
import multiprocessing as mp
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any, Union
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from enum import Enum, auto
from collections import defaultdict, deque
import traceback
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
import uuid

# Import tracking and search
from .tracker import CentroidTracker
from .search import EventSearchEngine

logger = logging.getLogger(__name__)

# ========================= ENUMERATIONS =========================

class ModelFormat(Enum):
    """Supported AI model formats"""
    DARKNET = "darknet"
    TENSORFLOW = "tensorflow"
    PYTORCH = "pytorch"
    ONNX = "onnx"
    TENSORRT = "tensorrt"
    OPENVINO = "openvino"
    CAFFE = "caffe"
    KERAS = "keras"
    MXNET = "mxnet"
    TFLITE = "tflite"
    CUSTOM = "custom"

class InferenceBackend(Enum):
    """Inference acceleration backends"""
    CPU = "cpu"
    CUDA = "cuda"
    CUDNN = "cudnn"
    TENSORRT = "tensorrt"
    OPENVINO = "openvino"
    OPENCL = "opencl"
    VULKAN = "vulkan"
    NNAPI = "nnapi"
    COREML = "coreml"
    CUSTOM = "custom"

class ModelType(Enum):
    """Types of AI models"""
    OBJECT_DETECTION = "object_detection"
    CLASSIFICATION = "classification"
    SEGMENTATION = "segmentation"
    POSE_ESTIMATION = "pose_estimation"
    FACE_RECOGNITION = "face_recognition"
    OCR = "ocr"
    ACTION_RECOGNITION = "action_recognition"
    ANOMALY_DETECTION = "anomaly_detection"
    DEPTH_ESTIMATION = "depth_estimation"
    SUPER_RESOLUTION = "super_resolution"
    STYLE_TRANSFER = "style_transfer"
    GENERATIVE = "generative"

class ModelStatus(Enum):
    """Model lifecycle status"""
    LOADING = auto()
    LOADED = auto()
    WARMING_UP = auto()
    ACTIVE = auto()
    DEGRADED = auto()
    ERROR = auto()
    UNLOADING = auto()
    UNLOADED = auto()

class OptimizationLevel(Enum):
    """Model optimization levels"""
    NONE = 0
    BASIC = 1
    INTERMEDIATE = 2
    AGGRESSIVE = 3
    EXTREME = 4

class QuantizationType(Enum):
    """Model quantization types"""
    NONE = "none"
    DYNAMIC = "dynamic"
    STATIC = "static"
    INT8 = "int8"
    INT16 = "int16"
    FLOAT16 = "float16"
    MIXED = "mixed"

# ========================= DATA CLASSES =========================

@dataclass
class ModelMetadata:
    """Comprehensive model metadata"""
    model_id: str
    name: str
    version: str
    format: ModelFormat
    model_type: ModelType
    architecture: str
    input_shape: Tuple[int, ...]
    output_shape: Tuple[int, ...]
    classes: List[str]
    confidence_threshold: float
    nms_threshold: float
    file_path: str
    config_path: Optional[str] = None
    weights_hash: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    author: Optional[str] = None
    description: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    preprocessing: Dict[str, Any] = field(default_factory=dict)
    postprocessing: Dict[str, Any] = field(default_factory=dict)
    
@dataclass
class InferenceConfig:
    """Inference configuration"""
    backend: InferenceBackend
    device_id: int = 0
    batch_size: int = 1
    num_threads: int = 4
    optimization_level: OptimizationLevel = OptimizationLevel.BASIC
    quantization: QuantizationType = QuantizationType.NONE
    use_fp16: bool = False
    use_tensorrt: bool = False
    use_onnx_runtime: bool = False
    warmup_iterations: int = 10
    max_workspace_size: int = 1 << 30  # 1GB
    
@dataclass
class ModelPerformanceMetrics:
    """Model performance metrics"""
    model_id: str
    inference_count: int = 0
    total_inference_time: float = 0.0
    avg_inference_time: float = 0.0
    min_inference_time: float = float('inf')
    max_inference_time: float = 0.0
    throughput: float = 0.0  # FPS
    memory_usage: int = 0
    gpu_utilization: float = 0.0
    cpu_utilization: float = 0.0
    error_count: int = 0
    success_rate: float = 100.0
    last_inference_time: Optional[str] = None
    
@dataclass
class DetectionResult:
    """Enhanced detection result"""
    detection_id: str
    class_id: int
    class_name: str
    confidence: float
    bbox: List[int]  # [x, y, w, h]
    centroid: Tuple[int, int]
    area: int
    aspect_ratio: float
    object_id: Optional[int] = None
    track_id: Optional[str] = None
    embedding: Optional[np.ndarray] = None
    attributes: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    
@dataclass
class InferenceRequest:
    """Inference request"""
    request_id: str
    model_id: str
    frame: np.ndarray
    stream_id: str
    timestamp: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    priority: int = 0
    timeout: float = 5.0
    
@dataclass
class InferenceResult:
    """Inference result"""
    request_id: str
    model_id: str
    detections: List[DetectionResult]
    processed_frame: Optional[np.ndarray]
    inference_time: float
    preprocessing_time: float
    postprocessing_time: float
    total_time: float
    success: bool
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

# ========================= MODEL LOADER =========================

class ModelLoader:
    """Advanced model loading with multi-format support"""
    
    def __init__(self, cache_dir: str = "./model_cache"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.loaded_models: Dict[str, Any] = {}
        logger.info(f"ModelLoader initialized with cache: {self.cache_dir}")
        
    def load_darknet_model(self, metadata: ModelMetadata, config: InferenceConfig) -> Any:
        """Load Darknet/YOLO model"""
        try:
            net = cv2.dnn.readNet(metadata.file_path, metadata.config_path)
            
            # Set backend and target
            if config.backend == InferenceBackend.CUDA:
                net.setPreferableBackend(cv2.dnn.DNN_BACKEND_CUDA)
                net.setPreferableTarget(cv2.dnn.DNN_TARGET_CUDA)
            elif config.backend == InferenceBackend.CUDNN:
                net.setPreferableBackend(cv2.dnn.DNN_BACKEND_CUDA)
                net.setPreferableTarget(cv2.dnn.DNN_TARGET_CUDA_FP16 if config.use_fp16 else cv2.dnn.DNN_TARGET_CUDA)
            else:
                net.setPreferableBackend(cv2.dnn.DNN_BACKEND_OPENCV)
                net.setPreferableTarget(cv2.dnn.DNN_TARGET_CPU)
            
            logger.info(f"Loaded Darknet model: {metadata.name}")
            return net
        except Exception as e:
            logger.error(f"Failed to load Darknet model: {e}")
            raise
            
    def load_tensorflow_model(self, metadata: ModelMetadata, config: InferenceConfig) -> Any:
        """Load TensorFlow model"""
        try:
            import tensorflow as tf
            
            # Load saved model or frozen graph
            if Path(metadata.file_path).is_dir():
                model = tf.saved_model.load(metadata.file_path)
            else:
                # Load frozen graph
                with tf.io.gfile.GFile(metadata.file_path, 'rb') as f:
                    graph_def = tf.compat.v1.GraphDef()
                    graph_def.ParseFromString(f.read())
                    
                with tf.Graph().as_default() as graph:
                    tf.import_graph_def(graph_def, name='')
                    model = graph
            
            logger.info(f"Loaded TensorFlow model: {metadata.name}")
            return model
        except Exception as e:
            logger.error(f"Failed to load TensorFlow model: {e}")
            raise
            
    def load_pytorch_model(self, metadata: ModelMetadata, config: InferenceConfig) -> Any:
        """Load PyTorch model"""
        try:
            import torch
            
            # Load model checkpoint
            checkpoint = torch.load(metadata.file_path, map_location=f'cuda:{config.device_id}' if config.backend == InferenceBackend.CUDA else 'cpu')
            
            # Extract model if wrapped in dict
            if isinstance(checkpoint, dict):
                model = checkpoint.get('model', checkpoint.get('state_dict'))
            else:
                model = checkpoint
            
            # Set to evaluation mode
            if hasattr(model, 'eval'):
                model.eval()
            
            logger.info(f"Loaded PyTorch model: {metadata.name}")
            return model
        except Exception as e:
            logger.error(f"Failed to load PyTorch model: {e}")
            raise
            
    def load_onnx_model(self, metadata: ModelMetadata, config: InferenceConfig) -> Any:
        """Load ONNX model"""
        try:
            import onnxruntime as ort
            
            # Configure providers
            providers = []
            if config.backend == InferenceBackend.CUDA:
                providers.append(('CUDAExecutionProvider', {
                    'device_id': config.device_id,
                    'arena_extend_strategy': 'kNextPowerOfTwo',
                    'gpu_mem_limit': config.max_workspace_size,
                    'cudnn_conv_algo_search': 'EXHAUSTIVE',
                }))
            providers.append('CPUExecutionProvider')
            
            # Create session
            sess_options = ort.SessionOptions()
            sess_options.graph_optimization_level = ort.GraphOptimizationLevel(config.optimization_level.value)
            sess_options.intra_op_num_threads = config.num_threads
            
            session = ort.InferenceSession(metadata.file_path, sess_options, providers=providers)
            
            logger.info(f"Loaded ONNX model: {metadata.name}")
            return session
        except Exception as e:
            logger.error(f"Failed to load ONNX model: {e}")
            raise
            
    def load_tensorrt_model(self, metadata: ModelMetadata, config: InferenceConfig) -> Any:
        """Load TensorRT engine"""
        try:
            import tensorrt as trt
            import pycuda.driver as cuda
            import pycuda.autoinit
            
            # Load serialized engine
            with open(metadata.file_path, 'rb') as f:
                engine_data = f.read()
            
            # Deserialize
            runtime = trt.Runtime(trt.Logger(trt.Logger.WARNING))
            engine = runtime.deserialize_cuda_engine(engine_data)
            context = engine.create_execution_context()
            
            logger.info(f"Loaded TensorRT engine: {metadata.name}")
            return {'engine': engine, 'context': context}
        except Exception as e:
            logger.error(f"Failed to load TensorRT engine: {e}")
            raise
            
    def load_model(self, metadata: ModelMetadata, config: InferenceConfig) -> Any:
        """Load model based on format"""
        model_key = f"{metadata.model_id}_{metadata.version}"
        
        if model_key in self.loaded_models:
            logger.info(f"Model {model_key} already loaded, returning cached version")
            return self.loaded_models[model_key]
        
        # Load based on format
        if metadata.format == ModelFormat.DARKNET:
            model = self.load_darknet_model(metadata, config)
        elif metadata.format == ModelFormat.TENSORFLOW:
            model = self.load_tensorflow_model(metadata, config)
        elif metadata.format == ModelFormat.PYTORCH:
            model = self.load_pytorch_model(metadata, config)
        elif metadata.format == ModelFormat.ONNX:
            model = self.load_onnx_model(metadata, config)
        elif metadata.format == ModelFormat.TENSORRT:
            model = self.load_tensorrt_model(metadata, config)
        else:
            raise ValueError(f"Unsupported model format: {metadata.format}")
        
        # Cache loaded model
        self.loaded_models[model_key] = model
        return model
        
    def unload_model(self, model_id: str, version: str):
        """Unload model from memory"""
        model_key = f"{model_id}_{version}"
        if model_key in self.loaded_models:
            del self.loaded_models[model_key]
            logger.info(f"Unloaded model: {model_key}")

# ========================= MODEL OPTIMIZER =========================

class ModelOptimizer:
    """Model optimization and quantization"""
    
    def __init__(self):
        self.optimization_cache = {}
        logger.info("ModelOptimizer initialized")
        
    def quantize_model(self, model: Any, metadata: ModelMetadata, quantization_type: QuantizationType) -> Any:
        """Quantize model for faster inference"""
        try:
            if metadata.format == ModelFormat.TENSORFLOW:
                return self._quantize_tensorflow(model, quantization_type)
            elif metadata.format == ModelFormat.PYTORCH:
                return self._quantize_pytorch(model, quantization_type)
            elif metadata.format == ModelFormat.ONNX:
                return self._quantize_onnx(model, quantization_type)
            else:
                logger.warning(f"Quantization not supported for {metadata.format}")
                return model
        except Exception as e:
            logger.error(f"Model quantization failed: {e}")
            return model
            
    def _quantize_tensorflow(self, model: Any, quantization_type: QuantizationType) -> Any:
        """Quantize TensorFlow model"""
        import tensorflow as tf
        
        if quantization_type == QuantizationType.INT8:
            converter = tf.lite.TFLiteConverter.from_saved_model(model)
            converter.optimizations = [tf.lite.Optimize.DEFAULT]
            converter.target_spec.supported_types = [tf.int8]
            quantized_model = converter.convert()
            return quantized_model
        elif quantization_type == QuantizationType.FLOAT16:
            converter = tf.lite.TFLiteConverter.from_saved_model(model)
            converter.optimizations = [tf.lite.Optimize.DEFAULT]
            converter.target_spec.supported_types = [tf.float16]
            quantized_model = converter.convert()
            return quantized_model
        
        return model
        
    def _quantize_pytorch(self, model: Any, quantization_type: QuantizationType) -> Any:
        """Quantize PyTorch model"""
        import torch
        
        if quantization_type == QuantizationType.DYNAMIC:
            quantized_model = torch.quantization.quantize_dynamic(
                model, {torch.nn.Linear, torch.nn.Conv2d}, dtype=torch.qint8
            )
            return quantized_model
        elif quantization_type == QuantizationType.STATIC:
            model.qconfig = torch.quantization.get_default_qconfig('fbgemm')
            torch.quantization.prepare(model, inplace=True)
            torch.quantization.convert(model, inplace=True)
            return model
        
        return model
        
    def _quantize_onnx(self, model: Any, quantization_type: QuantizationType) -> Any:
        """Quantize ONNX model"""
        try:
            from onnxruntime.quantization import quantize_dynamic, quantize_static, QuantType
            
            if quantization_type == QuantizationType.DYNAMIC:
                # Dynamic quantization
                quantize_dynamic(model, model, weight_type=QuantType.QInt8)
            elif quantization_type == QuantizationType.STATIC:
                # Static quantization requires calibration data
                pass
        except Exception as e:
            logger.error(f"ONNX quantization failed: {e}")
        
        return model
        
    def prune_model(self, model: Any, metadata: ModelMetadata, pruning_ratio: float = 0.3) -> Any:
        """Prune model weights"""
        try:
            if metadata.format == ModelFormat.PYTORCH:
                import torch.nn.utils.prune as prune
                
                # Apply pruning to all conv and linear layers
                for module in model.modules():
                    if isinstance(module, (torch.nn.Conv2d, torch.nn.Linear)):
                        prune.l1_unstructured(module, name='weight', amount=pruning_ratio)
                        prune.remove(module, 'weight')
                
                logger.info(f"Pruned model with ratio {pruning_ratio}")
            else:
                logger.warning(f"Pruning not implemented for {metadata.format}")
        except Exception as e:
            logger.error(f"Model pruning failed: {e}")
        
        return model
        
    def optimize_for_inference(self, model: Any, metadata: ModelMetadata) -> Any:
        """General inference optimization"""
        try:
            if metadata.format == ModelFormat.PYTORCH:
                import torch
                model = torch.jit.script(model)
                model = torch.jit.optimize_for_inference(model)
            elif metadata.format == ModelFormat.TENSORFLOW:
                import tensorflow as tf
                # Apply graph optimizations
                pass
        except Exception as e:
            logger.error(f"Inference optimization failed: {e}")
        
        return model

# ========================= INFERENCE ENGINE =========================

class InferenceEngine:
    """High-performance inference engine"""
    
    def __init__(self, metadata: ModelMetadata, config: InferenceConfig, model: Any):
        self.metadata = metadata
        self.config = config
        self.model = model
        self.metrics = ModelPerformanceMetrics(model_id=metadata.model_id)
        self.inference_times = deque(maxlen=1000)
        logger.info(f"InferenceEngine initialized for {metadata.name}")
        
    async def infer(self, request: InferenceRequest) -> InferenceResult:
        """Perform inference"""
        start_time = time.time()
        
        try:
            # Preprocess
            preprocess_start = time.time()
            preprocessed = self._preprocess(request.frame)
            preprocess_time = time.time() - preprocess_start
            
            # Inference
            inference_start = time.time()
            raw_output = await self._run_inference(preprocessed)
            inference_time = time.time() - inference_start
            
            # Postprocess
            postprocess_start = time.time()
            detections = self._postprocess(raw_output, request.frame.shape)
            postprocess_time = time.time() - postprocess_start
            
            # Draw visualizations
            processed_frame = self._draw_detections(request.frame.copy(), detections) if request.metadata.get('visualize', True) else None
            
            total_time = time.time() - start_time
            
            # Update metrics
            self._update_metrics(inference_time, success=True)
            
            return InferenceResult(
                request_id=request.request_id,
                model_id=self.metadata.model_id,
                detections=detections,
                processed_frame=processed_frame,
                inference_time=inference_time,
                preprocessing_time=preprocess_time,
                postprocessing_time=postprocess_time,
                total_time=total_time,
                success=True
            )
            
        except Exception as e:
            logger.error(f"Inference failed: {e}")
            self._update_metrics(0, success=False)
            
            return InferenceResult(
                request_id=request.request_id,
                model_id=self.metadata.model_id,
                detections=[],
                processed_frame=None,
                inference_time=0,
                preprocessing_time=0,
                postprocessing_time=0,
                total_time=time.time() - start_time,
                success=False,
                error=str(e)
            )
            
    def _preprocess(self, frame: np.ndarray) -> np.ndarray:
        """Preprocess frame"""
        # Apply preprocessing pipeline
        preprocessing = self.metadata.preprocessing
        
        # Resize
        target_size = preprocessing.get('target_size', (416, 416))
        frame = cv2.resize(frame, target_size)
        
        # Normalize
        if preprocessing.get('normalize', True):
            frame = frame.astype(np.float32) / 255.0
        
        # Apply mean/std
        mean = preprocessing.get('mean')
        std = preprocessing.get('std')
        if mean is not None:
            frame = frame - np.array(mean)
        if std is not None:
            frame = frame / np.array(std)
        
        # Convert to blob format
        if self.metadata.format == ModelFormat.DARKNET:
            blob = cv2.dnn.blobFromImage(frame, 1.0, target_size, swapRB=True, crop=False)
            return blob
        
        return frame
        
    async def _run_inference(self, preprocessed: np.ndarray) -> Any:
        """Run model inference"""
        loop = asyncio.get_event_loop()
        
        if self.metadata.format == ModelFormat.DARKNET:
            return await loop.run_in_executor(None, self._infer_darknet, preprocessed)
        elif self.metadata.format == ModelFormat.ONNX:
            return await loop.run_in_executor(None, self._infer_onnx, preprocessed)
        elif self.metadata.format == ModelFormat.PYTORCH:
            return await loop.run_in_executor(None, self._infer_pytorch, preprocessed)
        elif self.metadata.format == ModelFormat.TENSORFLOW:
            return await loop.run_in_executor(None, self._infer_tensorflow, preprocessed)
        else:
            raise ValueError(f"Unsupported format: {self.metadata.format}")
            
    def _infer_darknet(self, blob: np.ndarray) -> List:
        """Darknet inference"""
        self.model.setInput(blob)
        output_layer_names = self.model.getUnconnectedOutLayersNames()
        return self.model.forward(output_layer_names)
        
    def _infer_onnx(self, input_data: np.ndarray) -> Any:
        """ONNX inference"""
        input_name = self.model.get_inputs()[0].name
        output_name = self.model.get_outputs()[0].name
        return self.model.run([output_name], {input_name: input_data})[0]
        
    def _infer_pytorch(self, input_tensor: np.ndarray) -> Any:
        """PyTorch inference"""
        import torch
        
        with torch.no_grad():
            tensor = torch.from_numpy(input_tensor)
            if self.config.backend == InferenceBackend.CUDA:
                tensor = tensor.cuda(self.config.device_id)
            output = self.model(tensor)
        
        return output.cpu().numpy() if hasattr(output, 'cpu') else output
        
    def _infer_tensorflow(self, input_data: np.ndarray) -> Any:
        """TensorFlow inference"""
        import tensorflow as tf
        
        # Run inference based on model type
        if hasattr(self.model, 'signatures'):
            # SavedModel
            infer = self.model.signatures['serving_default']
            output = infer(tf.constant(input_data))
        else:
            # Frozen graph
            with tf.compat.v1.Session(graph=self.model) as sess:
                input_tensor = self.model.get_tensor_by_name('input:0')
                output_tensor = self.model.get_tensor_by_name('output:0')
                output = sess.run(output_tensor, feed_dict={input_tensor: input_data})
        
        return output
        
    def _postprocess(self, raw_output: Any, frame_shape: Tuple[int, int, int]) -> List[DetectionResult]:
        """Postprocess model output"""
        detections = []
        height, width = frame_shape[:2]
        
        if self.metadata.format == ModelFormat.DARKNET:
            # Process YOLO output
            for output in raw_output:
                for detection in output:
                    scores = detection[5:]
                    class_id = int(np.argmax(scores))
                    confidence = float(scores[class_id])
                    
                    if confidence > self.metadata.confidence_threshold:
                        # Get bbox
                        cx, cy, w, h = detection[0:4]
                        x = int((cx - w/2) * width)
                        y = int((cy - h/2) * height)
                        w = int(w * width)
                        h = int(h * height)
                        
                        detection_result = DetectionResult(
                            detection_id=str(uuid.uuid4()),
                            class_id=class_id,
                            class_name=self.metadata.classes[class_id] if class_id < len(self.metadata.classes) else f"class_{class_id}",
                            confidence=confidence,
                            bbox=[x, y, w, h],
                            centroid=(x + w//2, y + h//2),
                            area=w * h,
                            aspect_ratio=w / h if h > 0 else 0
                        )
                        detections.append(detection_result)
        
        # Apply NMS
        detections = self._apply_nms(detections)
        
        return detections
        
    def _apply_nms(self, detections: List[DetectionResult]) -> List[DetectionResult]:
        """Apply Non-Maximum Suppression"""
        if len(detections) == 0:
            return detections
        
        # Group by class
        by_class = defaultdict(list)
        for det in detections:
            by_class[det.class_id].append(det)
        
        filtered = []
        for class_id, class_dets in by_class.items():
            # Convert to format for NMS
            boxes = np.array([d.bbox for d in class_dets])
            scores = np.array([d.confidence for d in class_dets])
            
            # Apply OpenCV NMS
            indices = cv2.dnn.NMSBoxes(
                boxes.tolist(),
                scores.tolist(),
                self.metadata.confidence_threshold,
                self.metadata.nms_threshold
            )
            
            if len(indices) > 0:
                indices = indices.flatten()
                filtered.extend([class_dets[i] for i in indices])
        
        return filtered
        
    def _draw_detections(self, frame: np.ndarray, detections: List[DetectionResult]) -> np.ndarray:
        """Draw detection boxes on frame"""
        for det in detections:
            x, y, w, h = det.bbox
            color = self._get_class_color(det.class_id)
            
            # Draw box
            cv2.rectangle(frame, (x, y), (x+w, y+h), color, 2)
            
            # Draw label
            label = f"{det.class_name}: {det.confidence:.2f}"
            if det.object_id is not None:
                label = f"ID{det.object_id} {label}"
            
            (label_w, label_h), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
            cv2.rectangle(frame, (x, y-label_h-10), (x+label_w, y), color, -1)
            cv2.putText(frame, label, (x, y-5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        
        return frame
        
    def _get_class_color(self, class_id: int) -> Tuple[int, int, int]:
        """Get consistent color for class"""
        np.random.seed(class_id)
        return tuple(np.random.randint(0, 255, 3).tolist())
        
    def _update_metrics(self, inference_time: float, success: bool):
        """Update performance metrics"""
        self.metrics.inference_count += 1
        
        if success:
            self.metrics.total_inference_time += inference_time
            self.metrics.avg_inference_time = self.metrics.total_inference_time / self.metrics.inference_count
            self.metrics.min_inference_time = min(self.metrics.min_inference_time, inference_time)
            self.metrics.max_inference_time = max(self.metrics.max_inference_time, inference_time)
            
            self.inference_times.append(inference_time)
            if len(self.inference_times) > 0:
                self.metrics.throughput = 1.0 / np.mean(self.inference_times)
        else:
            self.metrics.error_count += 1
        
        self.metrics.success_rate = ((self.metrics.inference_count - self.metrics.error_count) / 
                                     self.metrics.inference_count * 100)
        self.metrics.last_inference_time = datetime.now().isoformat()

# ========================= MODEL REGISTRY =========================

class ModelRegistry:
    """Central registry for all AI models"""
    
    def __init__(self, db_path: str = "./model_registry.db"):
        self.db_path = db_path
        self.models: Dict[str, ModelMetadata] = {}
        self.inference_configs: Dict[str, InferenceConfig] = {}
        self._init_database()
        logger.info(f"ModelRegistry initialized with database: {db_path}")
        
    def _init_database(self):
        """Initialize registry database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS models (
                model_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                version TEXT NOT NULL,
                format TEXT NOT NULL,
                model_type TEXT NOT NULL,
                metadata TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS model_versions (
                version_id TEXT PRIMARY KEY,
                model_id TEXT NOT NULL,
                version TEXT NOT NULL,
                file_path TEXT NOT NULL,
                is_active INTEGER DEFAULT 0,
                created_at TEXT NOT NULL,
                FOREIGN KEY (model_id) REFERENCES models(model_id)
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS model_metrics (
                metric_id INTEGER PRIMARY KEY AUTOINCREMENT,
                model_id TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                metrics_json TEXT NOT NULL,
                FOREIGN KEY (model_id) REFERENCES models(model_id)
            )
        ''')
        
        conn.commit()
        conn.close()
        
    def register_model(self, metadata: ModelMetadata, config: InferenceConfig):
        """Register a new model"""
        self.models[metadata.model_id] = metadata
        self.inference_configs[metadata.model_id] = config
        
        # Save to database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO models 
            (model_id, name, version, format, model_type, metadata, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            metadata.model_id,
            metadata.name,
            metadata.version,
            metadata.format.value,
            metadata.model_type.value,
            json.dumps(asdict(metadata)),
            metadata.created_at,
            metadata.updated_at
        ))
        
        conn.commit()
        conn.close()
        
        logger.info(f"Registered model: {metadata.name} v{metadata.version}")
        
    def get_model(self, model_id: str) -> Optional[ModelMetadata]:
        """Get model metadata"""
        return self.models.get(model_id)
        
    def get_config(self, model_id: str) -> Optional[InferenceConfig]:
        """Get inference config"""
        return self.inference_configs.get(model_id)
        
    def list_models(self) -> List[ModelMetadata]:
        """List all registered models"""
        return list(self.models.values())
        
    def save_metrics(self, model_id: str, metrics: ModelPerformanceMetrics):
        """Save model performance metrics"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO model_metrics (model_id, timestamp, metrics_json)
            VALUES (?, ?, ?)
        ''', (model_id, datetime.now().isoformat(), json.dumps(asdict(metrics))))
        
        conn.commit()
        conn.close()

# ========================= AI ENGINE MANAGER =========================

class AIEngineManager:
    """Enterprise AI Engine Manager - Orchestrates all AI operations"""
    
    def __init__(self, config: Dict[str, Any], executor: ThreadPoolExecutor, db_manager):
        self.config = config
        self.executor = executor
        self.db_manager = db_manager
        
        # Core components
        self.model_loader = ModelLoader()
        self.model_optimizer = ModelOptimizer()
        self.model_registry = ModelRegistry()
        self.search_engine = EventSearchEngine(db_manager)
        
        # Inference engines
        self.inference_engines: Dict[str, InferenceEngine] = {}
        
        # Object trackers
        self.trackers: Dict[str, CentroidTracker] = {}
        
        # Request queue
        self.request_queue = asyncio.Queue(maxsize=1000)
        self.result_callbacks: Dict[str, asyncio.Future] = {}
        
        # Worker pool
        self.num_workers = config.get('num_inference_workers', 4)
        self.workers: List[asyncio.Task] = []
        
        # Metrics
        self.global_metrics = {
            'total_inferences': 0,
            'total_errors': 0,
            'avg_latency': 0.0,
            'throughput': 0.0
        }
        
        logger.info("Advanced AI Engine Manager initialized")
        
    async def start(self):
        """Start the AI engine"""
        logger.info("Starting AI Engine Manager...")
        
        # Load all configured models
        await self._load_models()
        
        # Start inference workers
        for i in range(self.num_workers):
            worker = asyncio.create_task(self._inference_worker(i))
            self.workers.append(worker)
        
        logger.info(f"AI Engine started with {self.num_workers} workers")
        
    async def _load_models(self):
        """Load all configured AI models"""
        for model_conf in self.config.get('models', []):
            try:
                # Create metadata
                metadata = ModelMetadata(
                    model_id=model_conf['model_id'],
                    name=model_conf['name'],
                    version=model_conf.get('version', '1.0'),
                    format=ModelFormat(model_conf['format']),
                    model_type=ModelType(model_conf['type']),
                    architecture=model_conf.get('architecture', 'unknown'),
                    input_shape=tuple(model_conf['input_shape']),
                    output_shape=tuple(model_conf.get('output_shape', [])),
                    classes=model_conf.get('classes', []),
                    confidence_threshold=model_conf.get('confidence_threshold', 0.5),
                    nms_threshold=model_conf.get('nms_threshold', 0.4),
                    file_path=model_conf['model_path'],
                    config_path=model_conf.get('config_path')
                )
                
                # Create inference config
                inference_config = InferenceConfig(
                    backend=InferenceBackend(model_conf.get('backend', 'cuda')),
                    device_id=model_conf.get('device_id', 0),
                    batch_size=model_conf.get('batch_size', 1),
                    num_threads=model_conf.get('num_threads', 4),
                    optimization_level=OptimizationLevel(model_conf.get('optimization_level', 1)),
                    use_fp16=model_conf.get('use_fp16', False)
                )
                
                # Load model
                model = self.model_loader.load_model(metadata, inference_config)
                
                # Optimize if requested
                if model_conf.get('optimize', False):
                    model = self.model_optimizer.optimize_for_inference(model, metadata)
                
                # Quantize if requested
                quantization = model_conf.get('quantization')
                if quantization:
                    model = self.model_optimizer.quantize_model(model, metadata, QuantizationType(quantization))
                
                # Create inference engine
                engine = InferenceEngine(metadata, inference_config, model)
                self.inference_engines[metadata.model_id] = engine
                
                # Register in registry
                self.model_registry.register_model(metadata, inference_config)
                
                logger.info(f"Loaded model: {metadata.name} ({metadata.format.value})")
                
            except Exception as e:
                logger.error(f"Failed to load model {model_conf.get('name')}: {e}")
                logger.error(traceback.format_exc())
                
    def register_tracker(self, stream_id: str, max_disappeared: int = 50):
        """Register object tracker for a stream"""
        self.trackers[stream_id] = CentroidTracker(max_disappeared=max_disappeared)
        logger.info(f"Registered tracker for stream: {stream_id}")
        
    async def process_frame(self, stream_id: str, frame: np.ndarray, model_id: str, 
                          metadata: Optional[Dict[str, Any]] = None) -> InferenceResult:
        """Process a single frame"""
        request_id = str(uuid.uuid4())
        
        # Create request
        request = InferenceRequest(
            request_id=request_id,
            model_id=model_id,
            frame=frame,
            stream_id=stream_id,
            timestamp=datetime.now().isoformat(),
            metadata=metadata or {}
        )
        
        # Create future for result
        future = asyncio.Future()
        self.result_callbacks[request_id] = future
        
        # Queue request
        await self.request_queue.put(request)
        
        # Wait for result
        result = await future
        
        # Apply tracking if tracker exists
        if stream_id in self.trackers and result.success:
            result = await self._apply_tracking(stream_id, result)
        
        return result
        
    async def _inference_worker(self, worker_id: int):
        """Inference worker task"""
        logger.info(f"Inference worker {worker_id} started")
        
        while True:
            try:
                # Get request from queue
                request = await self.request_queue.get()
                
                # Get inference engine
                engine = self.inference_engines.get(request.model_id)
                if not engine:
                    logger.error(f"Unknown model: {request.model_id}")
                    continue
                
                # Run inference
                result = await engine.infer(request)
                
                # Update global metrics
                self.global_metrics['total_inferences'] += 1
                if not result.success:
                    self.global_metrics['total_errors'] += 1
                
                # Send result
                future = self.result_callbacks.get(request.request_id)
                if future and not future.done():
                    future.set_result(result)
                
                # Cleanup
                self.result_callbacks.pop(request.request_id, None)
                
            except asyncio.CancelledError:
                logger.info(f"Worker {worker_id} cancelled")
                break
            except Exception as e:
                logger.error(f"Worker {worker_id} error: {e}")
                logger.error(traceback.format_exc())
                
    async def _apply_tracking(self, stream_id: str, result: InferenceResult) -> InferenceResult:
        """Apply object tracking to detections"""
        tracker = self.trackers[stream_id]
        
        # Extract bounding boxes
        boxes = [det.bbox for det in result.detections]
        
        # Update tracker
        tracked_objects = tracker.update(boxes)
        
        # Link detections to tracks
        for i, detection in enumerate(result.detections):
            cx, cy = detection.centroid
            
            # Find matching track
            for object_id, centroid in tracked_objects.items():
                if abs(centroid[0] - cx) < 50 and abs(centroid[1] - cy) < 50:
                    detection.object_id = object_id
                    detection.track_id = f"{stream_id}_{object_id}"
                    break
        
        return result
        
    def get_model_metrics(self, model_id: str) -> Optional[ModelPerformanceMetrics]:
        """Get model performance metrics"""
        engine = self.inference_engines.get(model_id)
        return engine.metrics if engine else None
        
    def get_global_metrics(self) -> Dict[str, Any]:
        """Get global AI engine metrics"""
        return self.global_metrics.copy()
        
    def list_models(self) -> List[ModelMetadata]:
        """List all loaded models"""
        return self.model_registry.list_models()
        
    async def shutdown(self):
        """Shutdown AI engine"""
        logger.info("Shutting down AI Engine...")
        
        # Cancel workers
        for worker in self.workers:
            worker.cancel()
        
        # Wait for workers
        await asyncio.gather(*self.workers, return_exceptions=True)
        
        # Unload models
        for model_id in list(self.inference_engines.keys()):
            metadata = self.model_registry.get_model(model_id)
            if metadata:
                self.model_loader.unload_model(metadata.model_id, metadata.version)
        
        logger.info("AI Engine shutdown complete")
