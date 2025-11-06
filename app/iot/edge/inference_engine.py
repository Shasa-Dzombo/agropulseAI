"""
Edge AI Inference Engine

Provides on-device machine learning inference using TensorFlow Lite,
ONNX Runtime, and custom optimized models for resource-constrained devices.

Features:
- TensorFlow Lite inference
- ONNX model support
- Model quantization (INT8, FP16)
- Batch inference optimization
- Model caching and warming
- Hardware acceleration (GPU, NPU, DSP)
- Dynamic model loading
- A/B testing support
"""

import os
import time
import logging
import hashlib
import pickle
from typing import Dict, List, Optional, Tuple, Union, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
import numpy as np
import json

try:
    import tensorflow as tf
    import tflite_runtime.interpreter as tflite
    TFLITE_AVAILABLE = True
except ImportError:
    TFLITE_AVAILABLE = False
    logging.warning("TensorFlow Lite not available")

try:
    import onnxruntime as ort
    ONNX_AVAILABLE = True
except ImportError:
    ONNX_AVAILABLE = False
    logging.warning("ONNX Runtime not available")

from redis import Redis
from threading import Lock, Thread
from queue import Queue, Empty
from concurrent.futures import ThreadPoolExecutor


logger = logging.getLogger(__name__)


@dataclass
class ModelMetadata:
    """Metadata for edge AI models"""
    model_id: str
    model_name: str
    version: str
    framework: str  # 'tflite', 'onnx', 'pytorch_mobile'
    input_shape: Tuple[int, ...]
    output_shape: Tuple[int, ...]
    quantization: str  # 'none', 'int8', 'fp16', 'dynamic'
    size_bytes: int
    hash_md5: str
    created_at: datetime
    accuracy_metrics: Dict[str, float] = field(default_factory=dict)
    hardware_requirements: Dict[str, Any] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)


@dataclass
class InferenceResult:
    """Result from edge inference"""
    model_id: str
    predictions: np.ndarray
    confidence_scores: Optional[np.ndarray]
    latency_ms: float
    preprocessing_ms: float
    inference_ms: float
    postprocessing_ms: float
    timestamp: datetime
    device_id: str
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class ModelRegistry:
    """
    Registry for managing edge AI models
    
    Features:
    - Model versioning
    - Model discovery
    - Automatic updates
    - Model validation
    - Performance tracking
    """
    
    def __init__(
        self,
        registry_path: str,
        redis_client: Optional[Redis] = None,
        cache_ttl: int = 3600
    ):
        self.registry_path = Path(registry_path)
        self.registry_path.mkdir(parents=True, exist_ok=True)
        self.redis = redis_client
        self.cache_ttl = cache_ttl
        self.models: Dict[str, ModelMetadata] = {}
        self._lock = Lock()
        
        # Load existing models
        self._load_registry()
        
        logger.info(f"ModelRegistry initialized with {len(self.models)} models")
    
    def _load_registry(self):
        """Load model registry from disk"""
        registry_file = self.registry_path / 'registry.json'
        if registry_file.exists():
            try:
                with open(registry_file, 'r') as f:
                    data = json.load(f)
                    for model_id, model_data in data.items():
                        # Convert datetime strings back to datetime objects
                        model_data['created_at'] = datetime.fromisoformat(
                            model_data['created_at']
                        )
                        self.models[model_id] = ModelMetadata(**model_data)
                logger.info(f"Loaded {len(self.models)} models from registry")
            except Exception as e:
                logger.error(f"Error loading registry: {e}")
    
    def _save_registry(self):
        """Save model registry to disk"""
        registry_file = self.registry_path / 'registry.json'
        try:
            data = {}
            for model_id, metadata in self.models.items():
                model_dict = {
                    'model_id': metadata.model_id,
                    'model_name': metadata.model_name,
                    'version': metadata.version,
                    'framework': metadata.framework,
                    'input_shape': metadata.input_shape,
                    'output_shape': metadata.output_shape,
                    'quantization': metadata.quantization,
                    'size_bytes': metadata.size_bytes,
                    'hash_md5': metadata.hash_md5,
                    'created_at': metadata.created_at.isoformat(),
                    'accuracy_metrics': metadata.accuracy_metrics,
                    'hardware_requirements': metadata.hardware_requirements,
                    'tags': metadata.tags,
                }
                data[model_id] = model_dict
            
            with open(registry_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving registry: {e}")
    
    def register_model(
        self,
        model_path: str,
        model_name: str,
        version: str,
        framework: str,
        input_shape: Tuple[int, ...],
        output_shape: Tuple[int, ...],
        quantization: str = 'none',
        accuracy_metrics: Optional[Dict[str, float]] = None,
        tags: Optional[List[str]] = None
    ) -> str:
        """
        Register a new model in the registry
        
        Args:
            model_path: Path to model file
            model_name: Name of the model
            version: Model version
            framework: Framework ('tflite', 'onnx')
            input_shape: Model input shape
            output_shape: Model output shape
            quantization: Quantization type
            accuracy_metrics: Model accuracy metrics
            tags: Model tags
            
        Returns:
            Model ID
        """
        with self._lock:
            # Calculate model hash
            with open(model_path, 'rb') as f:
                model_bytes = f.read()
                hash_md5 = hashlib.md5(model_bytes).hexdigest()
            
            # Generate model ID
            model_id = f"{model_name}_{version}_{hash_md5[:8]}"
            
            # Copy model to registry
            model_file = self.registry_path / f"{model_id}.{framework}"
            with open(model_file, 'wb') as f:
                f.write(model_bytes)
            
            # Create metadata
            metadata = ModelMetadata(
                model_id=model_id,
                model_name=model_name,
                version=version,
                framework=framework,
                input_shape=input_shape,
                output_shape=output_shape,
                quantization=quantization,
                size_bytes=len(model_bytes),
                hash_md5=hash_md5,
                created_at=datetime.now(),
                accuracy_metrics=accuracy_metrics or {},
                tags=tags or []
            )
            
            self.models[model_id] = metadata
            self._save_registry()
            
            # Cache in Redis
            if self.redis:
                cache_key = f"model_metadata:{model_id}"
                self.redis.setex(
                    cache_key,
                    self.cache_ttl,
                    pickle.dumps(metadata)
                )
            
            logger.info(f"Registered model: {model_id}")
            return model_id
    
    def get_model(self, model_id: str) -> Optional[ModelMetadata]:
        """Get model metadata"""
        # Try cache first
        if self.redis:
            cache_key = f"model_metadata:{model_id}"
            cached = self.redis.get(cache_key)
            if cached:
                return pickle.loads(cached)
        
        # Get from memory
        return self.models.get(model_id)
    
    def get_model_path(self, model_id: str) -> Optional[Path]:
        """Get path to model file"""
        metadata = self.get_model(model_id)
        if not metadata:
            return None
        
        model_file = self.registry_path / f"{model_id}.{metadata.framework}"
        return model_file if model_file.exists() else None
    
    def list_models(
        self,
        model_name: Optional[str] = None,
        tags: Optional[List[str]] = None
    ) -> List[ModelMetadata]:
        """List models with optional filtering"""
        models = list(self.models.values())
        
        if model_name:
            models = [m for m in models if m.model_name == model_name]
        
        if tags:
            models = [
                m for m in models
                if any(tag in m.tags for tag in tags)
            ]
        
        return sorted(models, key=lambda m: m.created_at, reverse=True)
    
    def delete_model(self, model_id: str) -> bool:
        """Delete model from registry"""
        with self._lock:
            if model_id not in self.models:
                return False
            
            metadata = self.models[model_id]
            
            # Delete model file
            model_file = self.registry_path / f"{model_id}.{metadata.framework}"
            if model_file.exists():
                model_file.unlink()
            
            # Remove from registry
            del self.models[model_id]
            self._save_registry()
            
            # Remove from cache
            if self.redis:
                cache_key = f"model_metadata:{model_id}"
                self.redis.delete(cache_key)
            
            logger.info(f"Deleted model: {model_id}")
            return True


class EdgeInferenceEngine:
    """
    Edge AI inference engine with multi-framework support
    
    Features:
    - TensorFlow Lite inference
    - ONNX Runtime inference
    - Batch processing
    - Model warming
    - Hardware acceleration
    - Performance monitoring
    """
    
    def __init__(
        self,
        model_registry: ModelRegistry,
        num_threads: int = 4,
        use_gpu: bool = False,
        use_npu: bool = False,
        batch_size: int = 1,
        enable_profiling: bool = False
    ):
        self.registry = model_registry
        self.num_threads = num_threads
        self.use_gpu = use_gpu
        self.use_npu = use_npu
        self.batch_size = batch_size
        self.enable_profiling = enable_profiling
        
        # Model cache
        self.loaded_models: Dict[str, Any] = {}
        self.model_locks: Dict[str, Lock] = {}
        self._cache_lock = Lock()
        
        # Performance tracking
        self.inference_times: Dict[str, List[float]] = {}
        self.inference_counts: Dict[str, int] = {}
        
        # Inference queue for batch processing
        self.inference_queue: Queue = Queue(maxsize=1000)
        self.batch_processor: Optional[Thread] = None
        
        logger.info(
            f"EdgeInferenceEngine initialized (threads={num_threads}, "
            f"gpu={use_gpu}, npu={use_npu})"
        )
    
    def _get_model_lock(self, model_id: str) -> Lock:
        """Get or create lock for model"""
        with self._cache_lock:
            if model_id not in self.model_locks:
                self.model_locks[model_id] = Lock()
            return self.model_locks[model_id]
    
    def _load_tflite_model(self, model_path: Path) -> Any:
        """Load TensorFlow Lite model"""
        if not TFLITE_AVAILABLE:
            raise RuntimeError("TensorFlow Lite not available")
        
        # Create interpreter with options
        delegates = []
        if self.use_gpu:
            try:
                delegates.append(tf.lite.experimental.load_delegate('libGLES_mali.so'))
            except Exception as e:
                logger.warning(f"Failed to load GPU delegate: {e}")
        
        interpreter = tflite.Interpreter(
            model_path=str(model_path),
            num_threads=self.num_threads,
            experimental_delegates=delegates
        )
        interpreter.allocate_tensors()
        
        return interpreter
    
    def _load_onnx_model(self, model_path: Path) -> Any:
        """Load ONNX model"""
        if not ONNX_AVAILABLE:
            raise RuntimeError("ONNX Runtime not available")
        
        # Set execution providers
        providers = ['CPUExecutionProvider']
        if self.use_gpu:
            providers.insert(0, 'CUDAExecutionProvider')
        
        session_options = ort.SessionOptions()
        session_options.intra_op_num_threads = self.num_threads
        session_options.execution_mode = ort.ExecutionMode.ORT_SEQUENTIAL
        
        if self.enable_profiling:
            session_options.enable_profiling = True
        
        session = ort.InferenceSession(
            str(model_path),
            sess_options=session_options,
            providers=providers
        )
        
        return session
    
    def load_model(self, model_id: str, warm_up: bool = True) -> bool:
        """
        Load model into memory
        
        Args:
            model_id: Model ID
            warm_up: Perform warm-up inference
            
        Returns:
            Success status
        """
        lock = self._get_model_lock(model_id)
        with lock:
            if model_id in self.loaded_models:
                logger.info(f"Model {model_id} already loaded")
                return True
            
            # Get model metadata
            metadata = self.registry.get_model(model_id)
            if not metadata:
                logger.error(f"Model {model_id} not found in registry")
                return False
            
            # Get model path
            model_path = self.registry.get_model_path(model_id)
            if not model_path:
                logger.error(f"Model file not found: {model_id}")
                return False
            
            try:
                # Load model based on framework
                if metadata.framework == 'tflite':
                    model = self._load_tflite_model(model_path)
                elif metadata.framework == 'onnx':
                    model = self._load_onnx_model(model_path)
                else:
                    logger.error(f"Unsupported framework: {metadata.framework}")
                    return False
                
                self.loaded_models[model_id] = model
                
                # Warm up model
                if warm_up:
                    self._warm_up_model(model_id, metadata)
                
                logger.info(f"Loaded model: {model_id}")
                return True
                
            except Exception as e:
                logger.error(f"Error loading model {model_id}: {e}")
                return False
    
    def _warm_up_model(self, model_id: str, metadata: ModelMetadata):
        """Perform warm-up inference"""
        try:
            # Create dummy input
            dummy_input = np.random.randn(*metadata.input_shape).astype(np.float32)
            
            # Run inference
            self.predict(model_id, dummy_input)
            
            logger.info(f"Model {model_id} warmed up")
        except Exception as e:
            logger.warning(f"Error warming up model {model_id}: {e}")
    
    def _infer_tflite(
        self,
        interpreter: Any,
        input_data: np.ndarray
    ) -> np.ndarray:
        """Run inference with TensorFlow Lite"""
        # Get input/output details
        input_details = interpreter.get_input_details()
        output_details = interpreter.get_output_details()
        
        # Set input tensor
        interpreter.set_tensor(input_details[0]['index'], input_data)
        
        # Run inference
        interpreter.invoke()
        
        # Get output tensor
        output_data = interpreter.get_tensor(output_details[0]['index'])
        
        return output_data
    
    def _infer_onnx(
        self,
        session: Any,
        input_data: np.ndarray
    ) -> np.ndarray:
        """Run inference with ONNX Runtime"""
        # Get input name
        input_name = session.get_inputs()[0].name
        
        # Run inference
        outputs = session.run(None, {input_name: input_data})
        
        return outputs[0]
    
    def predict(
        self,
        model_id: str,
        input_data: np.ndarray,
        device_id: str = 'edge_device',
        preprocess_fn: Optional[callable] = None,
        postprocess_fn: Optional[callable] = None
    ) -> InferenceResult:
        """
        Run inference on input data
        
        Args:
            model_id: Model ID
            input_data: Input data array
            device_id: Device ID
            preprocess_fn: Optional preprocessing function
            postprocess_fn: Optional postprocessing function
            
        Returns:
            Inference result
        """
        start_time = time.time()
        
        # Get model metadata
        metadata = self.registry.get_model(model_id)
        if not metadata:
            return InferenceResult(
                model_id=model_id,
                predictions=np.array([]),
                confidence_scores=None,
                latency_ms=0,
                preprocessing_ms=0,
                inference_ms=0,
                postprocessing_ms=0,
                timestamp=datetime.now(),
                device_id=device_id,
                error="Model not found in registry"
            )
        
        # Load model if not loaded
        if model_id not in self.loaded_models:
            if not self.load_model(model_id):
                return InferenceResult(
                    model_id=model_id,
                    predictions=np.array([]),
                    confidence_scores=None,
                    latency_ms=0,
                    preprocessing_ms=0,
                    inference_ms=0,
                    postprocessing_ms=0,
                    timestamp=datetime.now(),
                    device_id=device_id,
                    error="Failed to load model"
                )
        
        try:
            # Preprocessing
            preprocess_start = time.time()
            if preprocess_fn:
                input_data = preprocess_fn(input_data)
            preprocessing_ms = (time.time() - preprocess_start) * 1000
            
            # Inference
            inference_start = time.time()
            model = self.loaded_models[model_id]
            
            if metadata.framework == 'tflite':
                predictions = self._infer_tflite(model, input_data)
            elif metadata.framework == 'onnx':
                predictions = self._infer_onnx(model, input_data)
            else:
                raise ValueError(f"Unsupported framework: {metadata.framework}")
            
            inference_ms = (time.time() - inference_start) * 1000
            
            # Postprocessing
            postprocess_start = time.time()
            confidence_scores = None
            if postprocess_fn:
                predictions, confidence_scores = postprocess_fn(predictions)
            postprocessing_ms = (time.time() - postprocess_start) * 1000
            
            # Total latency
            latency_ms = (time.time() - start_time) * 1000
            
            # Track performance
            if model_id not in self.inference_times:
                self.inference_times[model_id] = []
                self.inference_counts[model_id] = 0
            
            self.inference_times[model_id].append(latency_ms)
            self.inference_counts[model_id] += 1
            
            # Keep only last 1000 times
            if len(self.inference_times[model_id]) > 1000:
                self.inference_times[model_id] = self.inference_times[model_id][-1000:]
            
            return InferenceResult(
                model_id=model_id,
                predictions=predictions,
                confidence_scores=confidence_scores,
                latency_ms=latency_ms,
                preprocessing_ms=preprocessing_ms,
                inference_ms=inference_ms,
                postprocessing_ms=postprocessing_ms,
                timestamp=datetime.now(),
                device_id=device_id
            )
            
        except Exception as e:
            logger.error(f"Error during inference: {e}")
            return InferenceResult(
                model_id=model_id,
                predictions=np.array([]),
                confidence_scores=None,
                latency_ms=(time.time() - start_time) * 1000,
                preprocessing_ms=0,
                inference_ms=0,
                postprocessing_ms=0,
                timestamp=datetime.now(),
                device_id=device_id,
                error=str(e)
            )
    
    def get_model_stats(self, model_id: str) -> Dict[str, Any]:
        """Get performance statistics for model"""
        if model_id not in self.inference_times:
            return {}
        
        times = self.inference_times[model_id]
        count = self.inference_counts[model_id]
        
        return {
            'model_id': model_id,
            'inference_count': count,
            'avg_latency_ms': np.mean(times),
            'p50_latency_ms': np.percentile(times, 50),
            'p95_latency_ms': np.percentile(times, 95),
            'p99_latency_ms': np.percentile(times, 99),
            'min_latency_ms': np.min(times),
            'max_latency_ms': np.max(times),
        }
    
    def unload_model(self, model_id: str):
        """Unload model from memory"""
        lock = self._get_model_lock(model_id)
        with lock:
            if model_id in self.loaded_models:
                del self.loaded_models[model_id]
                logger.info(f"Unloaded model: {model_id}")
    
    def clear_cache(self):
        """Clear all loaded models"""
        with self._cache_lock:
            self.loaded_models.clear()
            logger.info("Cleared model cache")
