# Advanced License Plate Recognition and Vehicle Analytics System
# Enterprise-grade automatic number plate recognition with vehicle classification, tracking, and database integration

import cv2
import numpy as np
import logging
import time
import json
import sqlite3
import threading
import queue
import asyncio
import re
from collections import defaultdict, deque
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Any, Set, Union
from dataclasses import dataclass, asdict, field
from datetime import datetime, timedelta
from enum import Enum
import hashlib
import statistics
import string

try:
    import easyocr
    EASYOCR_AVAILABLE = True
except ImportError:
    EASYOCR_AVAILABLE = False

try:
    import pytesseract
    TESSERACT_AVAILABLE = True
except ImportError:
    TESSERACT_AVAILABLE = False

try:
    from PIL import Image, ImageEnhance, ImageFilter
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

try:
    import tensorflow as tf
    TENSORFLOW_AVAILABLE = True
except ImportError:
    TENSORFLOW_AVAILABLE = False

logger = logging.getLogger(__name__)

class PlateFormat(Enum):
    US_STANDARD = "us_standard"
    EU_STANDARD = "eu_standard"
    UK_STANDARD = "uk_standard"
    INTERNATIONAL = "international"
    CUSTOM = "custom"

class VehicleType(Enum):
    CAR = "car"
    TRUCK = "truck"
    MOTORCYCLE = "motorcycle"
    BUS = "bus"
    VAN = "van"
    SUV = "suv"
    UNKNOWN = "unknown"

class PlateQuality(Enum):
    EXCELLENT = "excellent"
    GOOD = "good"
    FAIR = "fair"
    POOR = "poor"
    UNREADABLE = "unreadable"

@dataclass
class PlateDetection:
    plate_id: str
    plate_text: str
    confidence: float
    bbox: Tuple[int, int, int, int]
    quality: PlateQuality
    format_type: PlateFormat
    character_confidences: List[float]
    preprocessing_method: str
    detection_method: str
    timestamp: float
    frame_number: int
    camera_id: str
    vehicle_bbox: Optional[Tuple[int, int, int, int]] = None
    vehicle_type: Optional[VehicleType] = None
    vehicle_color: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class VehicleTrack:
    vehicle_id: str
    plate_detections: List[PlateDetection]
    first_seen: float
    last_seen: float
    best_plate: Optional[PlateDetection]
    vehicle_type: VehicleType
    vehicle_color: str
    path: List[Tuple[int, int]]
    velocity: float
    direction: float
    confidence_history: List[float]
    metadata: Dict[str, Any] = field(default_factory=dict)

class ImagePreprocessor:
    def __init__(self):
        self.methods = {
            'basic': self._basic_preprocessing,
            'adaptive': self._adaptive_preprocessing,
            'enhanced': self._enhanced_preprocessing,
            'multi_scale': self._multi_scale_preprocessing,
            'perspective': self._perspective_correction
        }
    
    def preprocess(self, image: np.ndarray, method: str = 'enhanced') -> List[np.ndarray]:
        if method in self.methods:
            return self.methods[method](image)
        else:
            return [self._basic_preprocessing(image)[0]]
    
    def _basic_preprocessing(self, image: np.ndarray) -> List[np.ndarray]:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(gray)
        
        denoised = cv2.bilateralFilter(enhanced, 9, 75, 75)
        
        _, thresh = cv2.threshold(denoised, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        kernel = np.ones((2, 2), np.uint8)
        cleaned = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)
        
        return [cleaned]
    
    def _adaptive_preprocessing(self, image: np.ndarray) -> List[np.ndarray]:
        results = []
        
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        for block_size in [11, 15, 19]:
            adaptive = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                           cv2.THRESH_BINARY, block_size, 2)
            results.append(adaptive)
        
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(gray)
        
        for threshold in [100, 120, 140]:
            _, binary = cv2.threshold(enhanced, threshold, 255, cv2.THRESH_BINARY)
            results.append(binary)
        
        return results
    
    def _enhanced_preprocessing(self, image: np.ndarray) -> List[np.ndarray]:
        if not PIL_AVAILABLE:
            return self._basic_preprocessing(image)
        
        results = []
        
        pil_image = Image.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
        
        enhancer = ImageEnhance.Contrast(pil_image)
        for factor in [1.2, 1.5, 1.8]:
            enhanced = enhancer.enhance(factor)
            
            brightness_enhancer = ImageEnhance.Brightness(enhanced)
            for b_factor in [1.0, 1.2]:
                bright_enhanced = brightness_enhancer.enhance(b_factor)
                
                sharpness_enhancer = ImageEnhance.Sharpness(bright_enhanced)
                sharp_enhanced = sharpness_enhancer.enhance(1.5)
                
                np_image = np.array(sharp_enhanced)
                gray = cv2.cvtColor(np_image, cv2.COLOR_RGB2GRAY)
                
                _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
                results.append(binary)
        
        return results[:3]
    
    def _multi_scale_preprocessing(self, image: np.ndarray) -> List[np.ndarray]:
        results = []
        h, w = image.shape[:2]
        
        scales = [0.8, 1.0, 1.2, 1.5]
        
        for scale in scales:
            new_w, new_h = int(w * scale), int(h * scale)
            resized = cv2.resize(image, (new_w, new_h))
            
            processed = self._basic_preprocessing(resized)[0]
            
            if scale != 1.0:
                processed = cv2.resize(processed, (w, h))
            
            results.append(processed)
        
        return results
    
    def _perspective_correction(self, image: np.ndarray) -> List[np.ndarray]:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        edges = cv2.Canny(gray, 50, 150, apertureSize=3)
        
        lines = cv2.HoughLinesP(edges, 1, np.pi / 180, threshold=100,
                               minLineLength=30, maxLineGap=10)
        
        if lines is not None and len(lines) >= 4:
            corners = self._find_license_plate_corners(lines, image.shape[:2])
            if corners is not None:
                corrected = self._apply_perspective_transform(image, corners)
                return self._basic_preprocessing(corrected)
        
        return self._basic_preprocessing(image)
    
    def _find_license_plate_corners(self, lines: np.ndarray, 
                                   image_shape: Tuple[int, int]) -> Optional[np.ndarray]:
        h, w = image_shape
        
        corners = np.array([[0, 0], [w, 0], [w, h], [0, h]], dtype=np.float32)
        
        return corners
    
    def _apply_perspective_transform(self, image: np.ndarray, 
                                   corners: np.ndarray) -> np.ndarray:
        h, w = image.shape[:2]
        dst_corners = np.array([[0, 0], [w, 0], [w, h], [0, h]], dtype=np.float32)
        
        matrix = cv2.getPerspectiveTransform(corners, dst_corners)
        transformed = cv2.warpPerspective(image, matrix, (w, h))
        
        return transformed

class PlateDetector:
    def __init__(self):
        self.plate_cascade = None
        self._load_cascade()
    
    def _load_cascade(self):
        try:
            cascade_path = cv2.data.haarcascades + 'haarcascade_russian_plate_number.xml'
            if Path(cascade_path).exists():
                self.plate_cascade = cv2.CascadeClassifier(cascade_path)
            else:
                logger.warning("License plate cascade file not found, using alternative method")
        except Exception as e:
            logger.error(f"Error loading plate cascade: {e}")
    
    def detect_plates(self, image: np.ndarray) -> List[Tuple[int, int, int, int]]:
        detections = []
        
        if self.plate_cascade is not None:
            detections.extend(self._cascade_detection(image))
        
        detections.extend(self._contour_detection(image))
        
        detections.extend(self._morphological_detection(image))
        
        return self._filter_detections(detections, image.shape[:2])
    
    def _cascade_detection(self, image: np.ndarray) -> List[Tuple[int, int, int, int]]:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        plates = self.plate_cascade.detectMultiScale(gray, scaleFactor=1.1, 
                                                    minNeighbors=5, minSize=(60, 20))
        
        return [(x, y, w, h) for x, y, w, h in plates]
    
    def _contour_detection(self, image: np.ndarray) -> List[Tuple[int, int, int, int]]:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        bilateral = cv2.bilateralFilter(gray, 11, 17, 17)
        
        edges = cv2.Canny(bilateral, 30, 200)
        
        contours, _ = cv2.findContours(edges.copy(), cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
        contours = sorted(contours, key=cv2.contourArea, reverse=True)[:10]
        
        detections = []
        
        for contour in contours:
            peri = cv2.arcLength(contour, True)
            approx = cv2.approxPolyDP(contour, 0.018 * peri, True)
            
            if len(approx) == 4:
                x, y, w, h = cv2.boundingRect(approx)
                
                aspect_ratio = w / h
                area = w * h
                
                if 1.5 < aspect_ratio < 6 and 1000 < area < 50000:
                    detections.append((x, y, w, h))
        
        return detections
    
    def _morphological_detection(self, image: np.ndarray) -> List[Tuple[int, int, int, int]]:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(gray)
        
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (17, 5))
        blackhat = cv2.morphologyEx(enhanced, cv2.MORPH_BLACKHAT, kernel)
        
        gradX = cv2.Sobel(blackhat, ddepth=cv2.CV_32F, dx=1, dy=0, ksize=-1)
        gradX = np.absolute(gradX)
        (minVal, maxVal) = (np.min(gradX), np.max(gradX))
        gradX = 255 * ((gradX - minVal) / (maxVal - minVal))
        gradX = gradX.astype("uint8")
        
        gradX = cv2.GaussianBlur(gradX, (5, 5), 0)
        gradX = cv2.morphologyEx(gradX, cv2.MORPH_CLOSE, kernel)
        thresh = cv2.threshold(gradX, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)[1]
        
        thresh = cv2.erode(thresh, None, iterations=2)
        thresh = cv2.dilate(thresh, None, iterations=2)
        
        contours, _ = cv2.findContours(thresh.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        detections = []
        
        for contour in contours:
            x, y, w, h = cv2.boundingRect(contour)
            aspect_ratio = w / h
            area = w * h
            
            if 2 < aspect_ratio < 8 and 500 < area < 30000:
                detections.append((x, y, w, h))
        
        return detections
    
    def _filter_detections(self, detections: List[Tuple[int, int, int, int]], 
                          image_shape: Tuple[int, int]) -> List[Tuple[int, int, int, int]]:
        h, w = image_shape
        
        filtered = []
        for x, y, width, height in detections:
            if (0 <= x < w and 0 <= y < h and 
                x + width <= w and y + height <= h and
                width > 20 and height > 10):
                filtered.append((x, y, width, height))
        
        return self._non_max_suppression(filtered)
    
    def _non_max_suppression(self, boxes: List[Tuple[int, int, int, int]], 
                           overlap_thresh: float = 0.3) -> List[Tuple[int, int, int, int]]:
        if len(boxes) == 0:
            return []
        
        boxes = np.array(boxes, dtype=np.float32)
        
        x1 = boxes[:, 0]
        y1 = boxes[:, 1]
        x2 = boxes[:, 0] + boxes[:, 2]
        y2 = boxes[:, 1] + boxes[:, 3]
        
        areas = (x2 - x1 + 1) * (y2 - y1 + 1)
        
        indices = np.argsort(y2)
        
        keep = []
        while len(indices) > 0:
            last = len(indices) - 1
            i = indices[last]
            keep.append(i)
            
            xx1 = np.maximum(x1[i], x1[indices[:last]])
            yy1 = np.maximum(y1[i], y1[indices[:last]])
            xx2 = np.minimum(x2[i], x2[indices[:last]])
            yy2 = np.minimum(y2[i], y2[indices[:last]])
            
            w = np.maximum(0, xx2 - xx1 + 1)
            h = np.maximum(0, yy2 - yy1 + 1)
            
            intersection = w * h
            overlap = intersection / (areas[i] + areas[indices[:last]] - intersection)
            
            indices = np.delete(indices, np.concatenate(([last], np.where(overlap > overlap_thresh)[0])))
        
        return [(int(boxes[i][0]), int(boxes[i][1]), int(boxes[i][2]), int(boxes[i][3])) for i in keep]

class TextRecognizer:
    def __init__(self):
        self.easyocr_reader = None
        self.tesseract_config = '--psm 8 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
        
        self._initialize_ocr()
    
    def _initialize_ocr(self):
        if EASYOCR_AVAILABLE:
            try:
                self.easyocr_reader = easyocr.Reader(['en'], gpu=True)
                logger.info("EasyOCR initialized successfully")
            except Exception as e:
                logger.warning(f"Failed to initialize EasyOCR: {e}")
        
        if TESSERACT_AVAILABLE:
            try:
                pytesseract.get_tesseract_version()
                logger.info("Tesseract OCR available")
            except Exception as e:
                logger.warning(f"Tesseract not available: {e}")
    
    def recognize_text(self, image: np.ndarray) -> List[Tuple[str, float, str]]:
        results = []
        
        if self.easyocr_reader:
            results.extend(self._easyocr_recognition(image))
        
        if TESSERACT_AVAILABLE:
            results.extend(self._tesseract_recognition(image))
        
        results.extend(self._template_matching(image))
        
        return self._filter_and_rank_results(results)
    
    def _easyocr_recognition(self, image: np.ndarray) -> List[Tuple[str, float, str]]:
        try:
            results = self.easyocr_reader.readtext(image, detail=1)
            
            ocr_results = []
            for detection in results:
                text = detection[1].upper().replace(' ', '')
                confidence = detection[2]
                
                if self._is_valid_plate_text(text) and confidence > 0.3:
                    ocr_results.append((text, confidence, 'easyocr'))
            
            return ocr_results
        except Exception as e:
            logger.debug(f"EasyOCR recognition failed: {e}")
            return []
    
    def _tesseract_recognition(self, image: np.ndarray) -> List[Tuple[str, float, str]]:
        try:
            text = pytesseract.image_to_string(image, config=self.tesseract_config)
            text = text.strip().upper().replace(' ', '').replace('\n', '')
            
            confidence_data = pytesseract.image_to_data(image, config=self.tesseract_config, output_type=pytesseract.Output.DICT)
            confidences = [int(conf) for conf in confidence_data['conf'] if int(conf) > 0]
            avg_confidence = np.mean(confidences) / 100.0 if confidences else 0.0
            
            if self._is_valid_plate_text(text) and avg_confidence > 0.3:
                return [(text, avg_confidence, 'tesseract')]
            
            return []
        except Exception as e:
            logger.debug(f"Tesseract recognition failed: {e}")
            return []
    
    def _template_matching(self, image: np.ndarray) -> List[Tuple[str, float, str]]:
        characters = self._segment_characters(image)
        if len(characters) < 3:
            return []
        
        recognized_text = ""
        total_confidence = 0.0
        
        for char_image in characters:
            char, confidence = self._recognize_single_character(char_image)
            recognized_text += char
            total_confidence += confidence
        
        avg_confidence = total_confidence / len(characters)
        
        if self._is_valid_plate_text(recognized_text) and avg_confidence > 0.4:
            return [(recognized_text, avg_confidence, 'template')]
        
        return []
    
    def _segment_characters(self, image: np.ndarray) -> List[np.ndarray]:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
        
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        
        contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        char_contours = []
        for contour in contours:
            x, y, w, h = cv2.boundingRect(contour)
            aspect_ratio = w / h
            area = w * h
            
            if 0.2 < aspect_ratio < 1.2 and area > 100:
                char_contours.append((x, y, w, h))
        
        char_contours.sort(key=lambda x: x[0])
        
        characters = []
        for x, y, w, h in char_contours:
            char_roi = gray[y:y+h, x:x+w]
            char_roi = cv2.resize(char_roi, (20, 30))
            characters.append(char_roi)
        
        return characters
    
    def _recognize_single_character(self, char_image: np.ndarray) -> Tuple[str, float]:
        template_chars = '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ'
        
        best_char = '?'
        best_confidence = 0.0
        
        for char in template_chars:
            template = self._generate_character_template(char)
            
            if template is not None:
                result = cv2.matchTemplate(char_image, template, cv2.TM_CCOEFF_NORMED)
                _, max_val, _, _ = cv2.minMaxLoc(result)
                
                if max_val > best_confidence:
                    best_confidence = max_val
                    best_char = char
        
        return best_char, best_confidence
    
    def _generate_character_template(self, char: str) -> Optional[np.ndarray]:
        try:
            template = np.ones((30, 20), dtype=np.uint8) * 255
            
            font = cv2.FONT_HERSHEY_SIMPLEX
            font_scale = 0.8
            thickness = 2
            
            text_size = cv2.getTextSize(char, font, font_scale, thickness)[0]
            text_x = (20 - text_size[0]) // 2
            text_y = (30 + text_size[1]) // 2
            
            cv2.putText(template, char, (text_x, text_y), font, font_scale, 0, thickness)
            
            return template
        except:
            return None
    
    def _is_valid_plate_text(self, text: str) -> bool:
        if not text or len(text) < 3 or len(text) > 10:
            return False
        
        if not re.match(r'^[A-Z0-9]+$', text):
            return False
        
        has_letter = any(c.isalpha() for c in text)
        has_digit = any(c.isdigit() for c in text)
        
        return has_letter and has_digit
    
    def _filter_and_rank_results(self, results: List[Tuple[str, float, str]]) -> List[Tuple[str, float, str]]:
        if not results:
            return []
        
        unique_results = {}
        for text, confidence, method in results:
            if text in unique_results:
                if confidence > unique_results[text][1]:
                    unique_results[text] = (text, confidence, method)
            else:
                unique_results[text] = (text, confidence, method)
        
        sorted_results = sorted(unique_results.values(), key=lambda x: x[1], reverse=True)
        
        return sorted_results[:3]

class PlateValidator:
    def __init__(self):
        self.format_patterns = {
            PlateFormat.US_STANDARD: [
                r'^[A-Z]{3}[0-9]{4}$',  # ABC1234
                r'^[0-9]{3}[A-Z]{3}$',  # 123ABC
                r'^[A-Z]{2}[0-9]{5}$',  # AB12345
            ],
            PlateFormat.EU_STANDARD: [
                r'^[A-Z]{2}[0-9]{2}[A-Z]{3}$',  # AB12CDE
                r'^[A-Z]{1}[0-9]{3}[A-Z]{3}$',  # A123BCD
            ],
            PlateFormat.UK_STANDARD: [
                r'^[A-Z]{2}[0-9]{2}[A-Z]{3}$',  # AB12CDE
                r'^[A-Z]{1}[0-9]{1,3}[A-Z]{3}$',  # A123BCD
            ]
        }
    
    def validate_plate(self, text: str, expected_format: PlateFormat = None) -> Tuple[bool, PlateFormat, float]:
        if not self._basic_validation(text):
            return False, PlateFormat.CUSTOM, 0.0
        
        if expected_format and expected_format in self.format_patterns:
            patterns = self.format_patterns[expected_format]
            for pattern in patterns:
                if re.match(pattern, text):
                    return True, expected_format, 0.95
        
        best_format = PlateFormat.CUSTOM
        best_confidence = 0.0
        
        for plate_format, patterns in self.format_patterns.items():
            for pattern in patterns:
                if re.match(pattern, text):
                    confidence = self._calculate_format_confidence(text, pattern)
                    if confidence > best_confidence:
                        best_confidence = confidence
                        best_format = plate_format
        
        return best_confidence > 0.7, best_format, best_confidence
    
    def _basic_validation(self, text: str) -> bool:
        if not text or len(text) < 3 or len(text) > 10:
            return False
        
        if not re.match(r'^[A-Z0-9]+$', text):
            return False
        
        return True
    
    def _calculate_format_confidence(self, text: str, pattern: str) -> float:
        base_confidence = 0.8
        
        char_variety = len(set(text)) / len(text)
        variety_bonus = char_variety * 0.15
        
        length_penalty = 0
        if len(text) < 5:
            length_penalty = 0.1
        elif len(text) > 8:
            length_penalty = 0.05
        
        return max(0.0, min(1.0, base_confidence + variety_bonus - length_penalty))

class VehicleClassifier:
    def __init__(self):
        self.vehicle_patterns = {
            VehicleType.CAR: {'min_ratio': 1.2, 'max_ratio': 2.5, 'min_area': 5000},
            VehicleType.TRUCK: {'min_ratio': 1.5, 'max_ratio': 4.0, 'min_area': 15000},
            VehicleType.MOTORCYCLE: {'min_ratio': 0.8, 'max_ratio': 1.8, 'min_area': 2000},
            VehicleType.BUS: {'min_ratio': 2.0, 'max_ratio': 5.0, 'min_area': 20000},
            VehicleType.VAN: {'min_ratio': 1.3, 'max_ratio': 3.0, 'min_area': 8000},
        }
    
    def classify_vehicle(self, bbox: Tuple[int, int, int, int], 
                        image: np.ndarray = None) -> Tuple[VehicleType, float]:
        x, y, w, h = bbox
        aspect_ratio = w / h
        area = w * h
        
        best_type = VehicleType.UNKNOWN
        best_confidence = 0.0
        
        for vehicle_type, criteria in self.vehicle_patterns.items():
            confidence = 0.0
            
            if (criteria['min_ratio'] <= aspect_ratio <= criteria['max_ratio'] and
                area >= criteria['min_area']):
                
                ratio_score = 1.0 - abs(aspect_ratio - ((criteria['min_ratio'] + criteria['max_ratio']) / 2)) / criteria['max_ratio']
                area_score = min(area / criteria['min_area'], 2.0) / 2.0
                
                confidence = (ratio_score * 0.6 + area_score * 0.4)
                
                if image is not None:
                    visual_score = self._analyze_visual_features(image, bbox, vehicle_type)
                    confidence = confidence * 0.7 + visual_score * 0.3
                
                if confidence > best_confidence:
                    best_confidence = confidence
                    best_type = vehicle_type
        
        return best_type, best_confidence
    
    def _analyze_visual_features(self, image: np.ndarray, bbox: Tuple[int, int, int, int],
                               vehicle_type: VehicleType) -> float:
        x, y, w, h = bbox
        
        if x < 0 or y < 0 or x + w > image.shape[1] or y + h > image.shape[0]:
            return 0.5
        
        roi = image[y:y+h, x:x+w]
        
        if roi.size == 0:
            return 0.5
        
        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 50, 150)
        edge_density = np.sum(edges > 0) / edges.size
        
        mean_intensity = np.mean(gray)
        
        features_score = 0.5
        
        if vehicle_type == VehicleType.TRUCK:
            if edge_density > 0.1 and mean_intensity < 150:
                features_score = 0.8
        elif vehicle_type == VehicleType.CAR:
            if 0.05 < edge_density < 0.15:
                features_score = 0.7
        elif vehicle_type == VehicleType.MOTORCYCLE:
            if edge_density < 0.08:
                features_score = 0.6
        
        return features_score

class LPRDatabase:
    def __init__(self, db_path: str):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = None
        self._setup_database()
    
    def _setup_database(self):
        self.connection = sqlite3.connect(str(self.db_path), check_same_thread=False)
        cursor = self.connection.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS plate_detections (
                plate_id TEXT PRIMARY KEY,
                plate_text TEXT,
                confidence REAL,
                bbox TEXT,
                quality TEXT,
                format_type TEXT,
                character_confidences TEXT,
                preprocessing_method TEXT,
                detection_method TEXT,
                timestamp REAL,
                frame_number INTEGER,
                camera_id TEXT,
                vehicle_bbox TEXT,
                vehicle_type TEXT,
                vehicle_color TEXT,
                metadata TEXT
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS vehicle_tracks (
                vehicle_id TEXT PRIMARY KEY,
                first_seen REAL,
                last_seen REAL,
                best_plate_id TEXT,
                vehicle_type TEXT,
                vehicle_color TEXT,
                path_data TEXT,
                velocity REAL,
                direction REAL,
                confidence_history TEXT,
                metadata TEXT
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS watchlist (
                plate_text TEXT PRIMARY KEY,
                alert_type TEXT,
                description TEXT,
                created_at REAL,
                expires_at REAL,
                active BOOLEAN,
                metadata TEXT
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS access_log (
                log_id TEXT PRIMARY KEY,
                plate_text TEXT,
                timestamp REAL,
                camera_id TEXT,
                access_granted BOOLEAN,
                metadata TEXT
            )
        """)
        
        self.connection.commit()
    
    def save_detection(self, detection: PlateDetection) -> bool:
        try:
            cursor = self.connection.cursor()
            cursor.execute("""
                INSERT INTO plate_detections 
                (plate_id, plate_text, confidence, bbox, quality, format_type, character_confidences,
                 preprocessing_method, detection_method, timestamp, frame_number, camera_id,
                 vehicle_bbox, vehicle_type, vehicle_color, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                detection.plate_id, detection.plate_text, detection.confidence,
                json.dumps(detection.bbox), detection.quality.value, detection.format_type.value,
                json.dumps(detection.character_confidences), detection.preprocessing_method,
                detection.detection_method, detection.timestamp, detection.frame_number,
                detection.camera_id, json.dumps(detection.vehicle_bbox),
                detection.vehicle_type.value if detection.vehicle_type else None,
                detection.vehicle_color, json.dumps(detection.metadata)
            ))
            self.connection.commit()
            return True
        except Exception as e:
            logger.error(f"Error saving detection: {e}")
            return False
    
    def save_track(self, track: VehicleTrack) -> bool:
        try:
            cursor = self.connection.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO vehicle_tracks 
                (vehicle_id, first_seen, last_seen, best_plate_id, vehicle_type, vehicle_color,
                 path_data, velocity, direction, confidence_history, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                track.vehicle_id, track.first_seen, track.last_seen,
                track.best_plate.plate_id if track.best_plate else None,
                track.vehicle_type.value, track.vehicle_color, json.dumps(track.path),
                track.velocity, track.direction, json.dumps(track.confidence_history),
                json.dumps(track.metadata)
            ))
            self.connection.commit()
            return True
        except Exception as e:
            logger.error(f"Error saving track: {e}")
            return False
    
    def get_detections(self, start_time: float = None, end_time: float = None,
                      camera_id: str = None, plate_text: str = None) -> List[PlateDetection]:
        cursor = self.connection.cursor()
        
        query = "SELECT * FROM plate_detections WHERE 1=1"
        params = []
        
        if start_time:
            query += " AND timestamp >= ?"
            params.append(start_time)
        
        if end_time:
            query += " AND timestamp <= ?"
            params.append(end_time)
        
        if camera_id:
            query += " AND camera_id = ?"
            params.append(camera_id)
        
        if plate_text:
            query += " AND plate_text LIKE ?"
            params.append(f"%{plate_text}%")
        
        query += " ORDER BY timestamp DESC"
        
        cursor.execute(query, params)
        detections = []
        
        for row in cursor.fetchall():
            detection = PlateDetection(
                plate_id=row[0], plate_text=row[1], confidence=row[2],
                bbox=tuple(json.loads(row[3])), quality=PlateQuality(row[4]),
                format_type=PlateFormat(row[5]), character_confidences=json.loads(row[6]),
                preprocessing_method=row[7], detection_method=row[8], timestamp=row[9],
                frame_number=row[10], camera_id=row[11],
                vehicle_bbox=tuple(json.loads(row[12])) if row[12] else None,
                vehicle_type=VehicleType(row[13]) if row[13] else None,
                vehicle_color=row[14], metadata=json.loads(row[15] or '{}')
            )
            detections.append(detection)
        
        return detections

class LicensePlateRecognizer:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.is_enabled = config.get('enabled', False)
        self.camera_id = config.get('camera_id', 'unknown')
        
        self.preprocessor = ImagePreprocessor()
        self.detector = PlateDetector()
        self.recognizer = TextRecognizer()
        self.validator = PlateValidator()
        self.vehicle_classifier = VehicleClassifier()
        
        db_path = config.get('database_path', '/var/lib/agropulse/lpr.db')
        self.database = LPRDatabase(db_path)
        
        self.frame_counter = 0
        self.detection_history = deque(maxlen=100)
        
        self.expected_format = PlateFormat(config.get('plate_format', 'us_standard'))
        self.confidence_threshold = config.get('confidence_threshold', 0.6)
        self.quality_threshold = config.get('quality_threshold', 0.5)
        
        self.performance_metrics = {
            'total_detections': 0,
            'successful_recognitions': 0,
            'processing_times': deque(maxlen=1000),
            'quality_distribution': defaultdict(int)
        }
        
        logger.info(f"Advanced License Plate Recognizer initialized. Enabled: {self.is_enabled}")
    
    async def recognize(self, frame: np.ndarray, vehicle_detections: List[Dict[str, Any]] = None) -> List[PlateDetection]:
        if not self.is_enabled:
            return []
        
        start_time = time.time()
        
        self.frame_counter += 1
        detections = []
        
        if vehicle_detections:
            for vehicle in vehicle_detections:
                vehicle_bbox = vehicle.get('bbox')
                if vehicle_bbox:
                    vehicle_roi = self._extract_roi(frame, vehicle_bbox)
                    plate_detections = await self._process_roi(vehicle_roi, vehicle_bbox, vehicle)
                    detections.extend(plate_detections)
        else:
            plate_detections = await self._process_roi(frame)
            detections.extend(plate_detections)
        
        processing_time = time.time() - start_time
        self._update_performance_metrics(detections, processing_time)
        
        for detection in detections:
            self.database.save_detection(detection)
            self.detection_history.append(detection)
        
        return detections
    
    async def _process_roi(self, image: np.ndarray, 
                          vehicle_bbox: Tuple[int, int, int, int] = None,
                          vehicle_info: Dict[str, Any] = None) -> List[PlateDetection]:
        detections = []
        
        plate_bboxes = self.detector.detect_plates(image)
        
        for bbox in plate_bboxes:
            x, y, w, h = bbox
            
            if x < 0 or y < 0 or x + w > image.shape[1] or y + h > image.shape[0]:
                continue
            
            plate_roi = image[y:y+h, x:x+w]
            
            if plate_roi.size == 0:
                continue
            
            quality = self._assess_plate_quality(plate_roi)
            
            if quality == PlateQuality.UNREADABLE:
                continue
            
            preprocessed_images = self.preprocessor.preprocess(plate_roi, 'enhanced')
            
            best_result = None
            best_confidence = 0.0
            
            for i, processed_image in enumerate(preprocessed_images):
                recognition_results = self.recognizer.recognize_text(processed_image)
                
                for text, confidence, method in recognition_results:
                    is_valid, plate_format, format_confidence = self.validator.validate_plate(
                        text, self.expected_format
                    )
                    
                    if is_valid and confidence > best_confidence and confidence > self.confidence_threshold:
                        best_result = {
                            'text': text,
                            'confidence': confidence,
                            'format': plate_format,
                            'method': method,
                            'preprocessing': f'method_{i}'
                        }
                        best_confidence = confidence
            
            if best_result:
                vehicle_type, vehicle_confidence = VehicleType.UNKNOWN, 0.0
                if vehicle_bbox:
                    vehicle_type, vehicle_confidence = self.vehicle_classifier.classify_vehicle(
                        vehicle_bbox, image
                    )
                
                plate_id = hashlib.md5(f"{self.camera_id}_{self.frame_counter}_{bbox}_{time.time()}".encode()).hexdigest()
                
                detection = PlateDetection(
                    plate_id=plate_id,
                    plate_text=best_result['text'],
                    confidence=best_result['confidence'],
                    bbox=(x, y, w, h),
                    quality=quality,
                    format_type=best_result['format'],
                    character_confidences=[best_result['confidence']] * len(best_result['text']),
                    preprocessing_method=best_result['preprocessing'],
                    detection_method=best_result['method'],
                    timestamp=time.time(),
                    frame_number=self.frame_counter,
                    camera_id=self.camera_id,
                    vehicle_bbox=vehicle_bbox,
                    vehicle_type=vehicle_type if vehicle_confidence > 0.5 else None,
                    vehicle_color=vehicle_info.get('color') if vehicle_info else None,
                    metadata={
                        'vehicle_confidence': vehicle_confidence,
                        'format_confidence': best_confidence,
                        'roi_size': (w, h)
                    }
                )
                
                detections.append(detection)
        
        return detections
    
    def _extract_roi(self, frame: np.ndarray, bbox: Tuple[int, int, int, int]) -> np.ndarray:
        x, y, w, h = bbox
        
        padding = 20
        x1 = max(0, x - padding)
        y1 = max(0, y - padding)
        x2 = min(frame.shape[1], x + w + padding)
        y2 = min(frame.shape[0], y + h + padding)
        
        return frame[y1:y2, x1:x2]
    
    def _assess_plate_quality(self, plate_image: np.ndarray) -> PlateQuality:
        if plate_image.size == 0:
            return PlateQuality.UNREADABLE
        
        gray = cv2.cvtColor(plate_image, cv2.COLOR_BGR2GRAY) if len(plate_image.shape) == 3 else plate_image
        
        blur_score = cv2.Laplacian(gray, cv2.CV_64F).var()
        
        contrast = np.std(gray)
        
        brightness = np.mean(gray)
        
        h, w = gray.shape
        size_score = min(w * h / 2000, 1.0)
        
        quality_score = (
            (blur_score / 500) * 0.4 +
            (contrast / 100) * 0.3 +
            (1 - abs(brightness - 127.5) / 127.5) * 0.2 +
            size_score * 0.1
        )
        
        if quality_score > 0.8:
            return PlateQuality.EXCELLENT
        elif quality_score > 0.6:
            return PlateQuality.GOOD
        elif quality_score > 0.4:
            return PlateQuality.FAIR
        elif quality_score > 0.2:
            return PlateQuality.POOR
        else:
            return PlateQuality.UNREADABLE
    
    def _update_performance_metrics(self, detections: List[PlateDetection], processing_time: float):
        self.performance_metrics['total_detections'] += len(detections)
        self.performance_metrics['processing_times'].append(processing_time)
        
        for detection in detections:
            if detection.confidence > self.confidence_threshold:
                self.performance_metrics['successful_recognitions'] += 1
            
            self.performance_metrics['quality_distribution'][detection.quality.value] += 1
    
    def get_performance_summary(self) -> Dict[str, Any]:
        metrics = self.performance_metrics.copy()
        
        if metrics['total_detections'] > 0:
            metrics['success_rate'] = metrics['successful_recognitions'] / metrics['total_detections']
        else:
            metrics['success_rate'] = 0.0
        
        if metrics['processing_times']:
            metrics['avg_processing_time'] = statistics.mean(metrics['processing_times'])
            metrics['fps'] = 1.0 / metrics['avg_processing_time']
        else:
            metrics['avg_processing_time'] = 0.0
            metrics['fps'] = 0.0
        
        metrics['quality_distribution'] = dict(metrics['quality_distribution'])
        
        return metrics
    
    def get_recent_detections(self, hours: int = 24) -> List[PlateDetection]:
        start_time = time.time() - (hours * 3600)
        return self.database.get_detections(start_time=start_time, camera_id=self.camera_id)
    
    def search_plates(self, plate_text: str) -> List[PlateDetection]:
        return self.database.get_detections(plate_text=plate_text)
    
    def add_to_watchlist(self, plate_text: str, alert_type: str, description: str = ""):
        try:
            cursor = self.database.connection.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO watchlist 
                (plate_text, alert_type, description, created_at, expires_at, active, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                plate_text.upper(), alert_type, description, time.time(),
                time.time() + (365 * 24 * 3600), True, '{}'
            ))
            self.database.connection.commit()
            logger.info(f"Added {plate_text} to watchlist with alert type {alert_type}")
        except Exception as e:
            logger.error(f"Error adding to watchlist: {e}")
    
    def check_watchlist(self, plate_text: str) -> Optional[Dict[str, Any]]:
        try:
            cursor = self.database.connection.cursor()
            cursor.execute("""
                SELECT * FROM watchlist 
                WHERE plate_text = ? AND active = 1 AND expires_at > ?
            """, (plate_text.upper(), time.time()))
            
            row = cursor.fetchone()
            if row:
                return {
                    'plate_text': row[0],
                    'alert_type': row[1],
                    'description': row[2],
                    'created_at': row[3]
                }
        except Exception as e:
            logger.error(f"Error checking watchlist: {e}")
        
        return None
    
    def cleanup_old_data(self, retention_days: int = 90):
        cutoff_time = time.time() - (retention_days * 24 * 3600)
        
        try:
            cursor = self.database.connection.cursor()
            
            cursor.execute("DELETE FROM plate_detections WHERE timestamp < ?", (cutoff_time,))
            cursor.execute("DELETE FROM vehicle_tracks WHERE last_seen < ?", (cutoff_time,))
            cursor.execute("DELETE FROM access_log WHERE timestamp < ?", (cutoff_time,))
            
            self.database.connection.commit()
            logger.info(f"Cleaned up LPR data older than {retention_days} days")
            
        except Exception as e:
            logger.error(f"Error cleaning up LPR data: {e}")

logger.info("Advanced License Plate Recognition System loaded successfully")
