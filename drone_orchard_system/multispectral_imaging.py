"""
Multispectral Imaging & Aerial Disease Detection System
========================================================

Comprehensive imaging system for drone-based disease detection in tree crops.
Processes RGB, NIR, thermal imagery to identify diseases from aerial perspective.

TARGET: 100,000 Lines of Code (Multispectral Imaging & Disease Detection Module)

COMPONENTS:
-----------
1. RGB Camera Processing (20,000 LOC)
2. Near-Infrared (NIR) Sensors (15,000 LOC)
3. Thermal Imaging (FLIR) (15,000 LOC)
4. NDVI Vegetation Index (12,000 LOC)
5. Disease Signature Detection (25,000 LOC)
6. Tree Health Scoring (8,000 LOC)
7. Fruit Counting & Ripeness (5,000 LOC)

DISEASE DETECTION FROM AERIAL VIEW:
-----------------------------------
- Phytophthora root rot → Canopy wilting, yellowing (visible from above)
- Anthracnose → Fruit/leaf spots, defoliation patterns
- Powdery mildew → White powder on leaves (spectral signature)
- Bacterial blight → Leaf lesions, defoliation zones
- Rust → Orange pustules, premature defoliation
- Scab → Fruit spots, cosmetic damage
- Mummy berry → Mummified fruit detection
- Canker diseases → Branch dieback patterns

Author: AgroPulse Drone Systems
Date: November 2025
"""

import numpy as np
import cv2
from dataclasses import dataclass
from enum import Enum
from typing import List, Tuple, Dict, Optional
import math


class ImageryType(Enum):
    """Type of imagery captured"""
    RGB = "rgb"  # Visible light
    NIR = "nir"  # Near-infrared
    RED_EDGE = "red_edge"  # 700-750nm
    THERMAL = "thermal"  # FLIR
    NDVI = "ndvi"  # Normalized Difference Vegetation Index
    GNDVI = "gndvi"  # Green NDVI
    NDRE = "ndre"  # Normalized Difference Red Edge
    SAVI = "savi"  # Soil-Adjusted Vegetation Index


class TreeHealthStatus(Enum):
    """Tree health classification"""
    HEALTHY = "healthy"  # NDVI > 0.7, no visible disease
    MILD_STRESS = "mild_stress"  # NDVI 0.5-0.7, early symptoms
    MODERATE_STRESS = "moderate_stress"  # NDVI 0.3-0.5, visible disease
    SEVERE_STRESS = "severe_stress"  # NDVI < 0.3, significant damage
    DEAD = "dead"  # NDVI < 0.1, no vegetation


class AerialDiseaseType(Enum):
    """Diseases detectable from aerial imagery"""
    PHYTOPHTHORA_ROOT_ROT = "phytophthora_root_rot"  # Canopy wilting
    ANTHRACNOSE = "anthracnose"  # Fruit/leaf spots
    POWDERY_MILDEW = "powdery_mildew"  # White powder
    BACTERIAL_BLIGHT = "bacterial_blight"  # Leaf lesions
    RUST = "rust"  # Orange pustules
    SCAB = "scab"  # Fruit spots
    MUMMY_BERRY = "mummy_berry"  # Mummified fruit
    CANKER = "canker"  # Branch dieback
    VERTICILLIUM_WILT = "verticillium_wilt"  # Sector wilting
    HUANGLONGBING = "huanglongbing"  # Citrus greening (asymmetric canopy)
    FIRE_BLIGHT = "fire_blight"  # "Shepherd's crook" branch bending
    HULL_ROT = "hull_rot"  # Almond hull discoloration


@dataclass
class MultispectralImage:
    """Multispectral image data"""
    rgb: np.ndarray  # H x W x 3 (RGB)
    nir: np.ndarray  # H x W (Near-infrared)
    red_edge: Optional[np.ndarray] = None  # H x W
    thermal: Optional[np.ndarray] = None  # H x W (temperature in Celsius)
    timestamp: float = 0.0
    gps_latitude: float = 0.0
    gps_longitude: float = 0.0
    altitude: float = 0.0  # Meters AGL
    gimbal_pitch: float = -90.0  # Degrees
    ground_sampling_distance: float = 0.0  # cm/pixel


@dataclass
class VegetationIndices:
    """Calculated vegetation health indices"""
    ndvi: float  # -1 to 1 (Normalized Difference Vegetation Index)
    gndvi: float  # Green NDVI
    ndre: float  # Red Edge index
    savi: float  # Soil-Adjusted Vegetation Index
    evi: float  # Enhanced Vegetation Index
    
    def get_health_status(self) -> TreeHealthStatus:
        """Determine tree health from NDVI"""
        if self.ndvi > 0.7:
            return TreeHealthStatus.HEALTHY
        elif self.ndvi > 0.5:
            return TreeHealthStatus.MILD_STRESS
        elif self.ndvi > 0.3:
            return TreeHealthStatus.MODERATE_STRESS
        elif self.ndvi > 0.1:
            return TreeHealthStatus.SEVERE_STRESS
        else:
            return TreeHealthStatus.DEAD


@dataclass
class TreeDetection:
    """Individual tree detected from aerial imagery"""
    tree_id: str
    gps_latitude: float
    gps_longitude: float
    canopy_area: float  # Square meters
    canopy_diameter: float  # Meters
    tree_height: float  # Meters (from LiDAR or stereo)
    vegetation_indices: VegetationIndices
    health_status: TreeHealthStatus
    disease_detected: Optional[AerialDiseaseType] = None
    disease_confidence: float = 0.0
    fruit_count: int = 0
    average_fruit_size: float = 0.0  # cm
    canopy_temperature: float = 0.0  # Celsius (thermal)
    stress_score: float = 0.0  # 0-100


@dataclass
class AerialDiseaseDetection:
    """Disease detection result from aerial imagery"""
    disease_type: AerialDiseaseType
    confidence: float  # 0-1
    affected_area: float  # Square meters
    affected_trees: List[str]  # Tree IDs
    severity: str  # "mild", "moderate", "severe"
    detection_method: str  # "spectral", "thermal", "rgb", "combined"
    symptoms_detected: List[str]
    recommended_action: str
    gps_hotspot: Tuple[float, float]  # Center of infection
    timestamp: float


class MultispectralProcessor:
    """
    Process multispectral imagery from drones for disease detection
    """
    
    def __init__(self):
        self.rgb_resolution = (5280, 2970)  # 4K+ resolution
        self.nir_resolution = (1280, 960)
        self.thermal_resolution = (640, 512)  # FLIR Tau 2
        
        # Camera calibration parameters
        self.rgb_focal_length = 8.8  # mm
        self.nir_focal_length = 5.4  # mm
        self.sensor_width = 13.2  # mm
        self.sensor_height = 8.8  # mm
        
        # Disease spectral signatures (NIR/Red ratios)
        self.disease_signatures = {
            AerialDiseaseType.PHYTOPHTHORA_ROOT_ROT: {
                "ndvi_range": (0.2, 0.4),  # Severe stress
                "thermal_delta": 3.0,  # Degrees above ambient (water stress)
                "canopy_yellowing": True
            },
            AerialDiseaseType.ANTHRACNOSE: {
                "ndvi_range": (0.4, 0.6),
                "rgb_spots": True,  # Dark spots visible
                "defoliation": True
            },
            AerialDiseaseType.POWDERY_MILDEW: {
                "ndvi_range": (0.5, 0.7),
                "white_coating_rgb": True,  # High reflectance in RGB
                "nir_reflectance_increase": True
            },
            AerialDiseaseType.RUST: {
                "ndvi_range": (0.3, 0.5),
                "orange_color_rgb": True,
                "premature_defoliation": True
            },
            AerialDiseaseType.VERTICILLIUM_WILT: {
                "ndvi_range": (0.2, 0.4),
                "sector_wilting": True,  # One side of tree
                "asymmetric_canopy": True
            },
            AerialDiseaseType.HUANGLONGBING: {
                "ndvi_range": (0.3, 0.5),
                "asymmetric_canopy": True,  # Citrus greening signature
                "yellow_shoots": True,
                "fruit_drop": True
            }
        }
        
        print("[Multispectral Processor] Initialized")
        print(f"  RGB Resolution: {self.rgb_resolution[0]} x {self.rgb_resolution[1]}")
        print(f"  NIR Resolution: {self.nir_resolution[0]} x {self.nir_resolution[1]}")
        print(f"  Thermal Resolution: {self.thermal_resolution[0]} x {self.thermal_resolution[1]}")
        print(f"  Disease Signatures: {len(self.disease_signatures)}")
    
    def calculate_ndvi(self, nir: np.ndarray, red: np.ndarray) -> np.ndarray:
        """
        Calculate NDVI (Normalized Difference Vegetation Index)
        NDVI = (NIR - Red) / (NIR + Red)
        Range: -1 to 1 (healthy vegetation > 0.6)
        """
        # Avoid division by zero
        denominator = nir.astype(float) + red.astype(float)
        denominator[denominator == 0] = 1e-10
        
        ndvi = (nir.astype(float) - red.astype(float)) / denominator
        
        # Clip to valid range
        ndvi = np.clip(ndvi, -1.0, 1.0)
        
        return ndvi
    
    def calculate_gndvi(self, nir: np.ndarray, green: np.ndarray) -> np.ndarray:
        """
        Calculate Green NDVI
        GNDVI = (NIR - Green) / (NIR + Green)
        More sensitive to chlorophyll than NDVI
        """
        denominator = nir.astype(float) + green.astype(float)
        denominator[denominator == 0] = 1e-10
        
        gndvi = (nir.astype(float) - green.astype(float)) / denominator
        return np.clip(gndvi, -1.0, 1.0)
    
    def calculate_ndre(self, nir: np.ndarray, red_edge: np.ndarray) -> np.ndarray:
        """
        Calculate Normalized Difference Red Edge Index
        NDRE = (NIR - Red Edge) / (NIR + Red Edge)
        Sensitive to nitrogen status
        """
        denominator = nir.astype(float) + red_edge.astype(float)
        denominator[denominator == 0] = 1e-10
        
        ndre = (nir.astype(float) - red_edge.astype(float)) / denominator
        return np.clip(ndre, -1.0, 1.0)
    
    def calculate_savi(self, nir: np.ndarray, red: np.ndarray, L: float = 0.5) -> np.ndarray:
        """
        Calculate Soil-Adjusted Vegetation Index
        SAVI = ((NIR - Red) / (NIR + Red + L)) * (1 + L)
        L = 0.5 for intermediate vegetation cover
        """
        denominator = nir.astype(float) + red.astype(float) + L
        denominator[denominator == 0] = 1e-10
        
        savi = ((nir.astype(float) - red.astype(float)) / denominator) * (1 + L)
        return np.clip(savi, -1.0, 1.0)
    
    def process_multispectral_image(self, image: MultispectralImage) -> VegetationIndices:
        """Process multispectral image and calculate vegetation indices"""
        
        # Extract red channel from RGB
        red = image.rgb[:, :, 2]
        green = image.rgb[:, :, 1]
        
        # Resize NIR to match RGB if needed
        if image.nir.shape != red.shape:
            nir_resized = cv2.resize(image.nir, (red.shape[1], red.shape[0]))
        else:
            nir_resized = image.nir
        
        # Calculate NDVI
        ndvi = self.calculate_ndvi(nir_resized, red)
        mean_ndvi = np.mean(ndvi[ndvi > 0])  # Exclude non-vegetation
        
        # Calculate GNDVI
        gndvi = self.calculate_gndvi(nir_resized, green)
        mean_gndvi = np.mean(gndvi[gndvi > 0])
        
        # Calculate NDRE (if red edge available)
        if image.red_edge is not None:
            red_edge_resized = cv2.resize(image.red_edge, (red.shape[1], red.shape[0]))
            ndre = self.calculate_ndre(nir_resized, red_edge_resized)
            mean_ndre = np.mean(ndre[ndre > 0])
        else:
            mean_ndre = 0.0
        
        # Calculate SAVI
        savi = self.calculate_savi(nir_resized, red)
        mean_savi = np.mean(savi[savi > 0])
        
        # Calculate EVI (Enhanced Vegetation Index)
        # EVI = 2.5 * ((NIR - Red) / (NIR + 6*Red - 7.5*Blue + 1))
        blue = image.rgb[:, :, 0]
        denominator = nir_resized.astype(float) + 6*red - 7.5*blue + 1
        denominator[denominator == 0] = 1e-10
        evi = 2.5 * ((nir_resized.astype(float) - red) / denominator)
        mean_evi = np.mean(evi[(evi > -1) & (evi < 1)])
        
        indices = VegetationIndices(
            ndvi=float(mean_ndvi),
            gndvi=float(mean_gndvi),
            ndre=float(mean_ndre),
            savi=float(mean_savi),
            evi=float(mean_evi)
        )
        
        return indices
    
    def detect_tree_from_aerial(self, 
                                image: MultispectralImage,
                                tree_id: str) -> TreeDetection:
        """Detect individual tree and assess health from aerial imagery"""
        
        # Calculate vegetation indices
        indices = self.process_multispectral_image(image)
        health_status = indices.get_health_status()
        
        # Segment tree canopy from background
        canopy_mask = self._segment_tree_canopy(image.rgb, image.nir)
        
        # Calculate canopy metrics
        canopy_area = np.sum(canopy_mask) * (image.ground_sampling_distance / 100) ** 2  # m²
        canopy_diameter = self._estimate_canopy_diameter(canopy_mask, image.ground_sampling_distance)
        
        # Estimate tree height (if thermal available, use stereo or LiDAR in real system)
        tree_height = self._estimate_tree_height(image.altitude, canopy_diameter)
        
        # Detect disease
        disease, disease_conf = self._detect_disease_from_spectral(image, indices)
        
        # Count fruit (if visible)
        fruit_count, avg_fruit_size = self._count_fruit(image.rgb, canopy_mask)
        
        # Calculate canopy temperature (if thermal available)
        if image.thermal is not None:
            canopy_temp = np.mean(image.thermal[canopy_mask > 0])
        else:
            canopy_temp = 0.0
        
        # Calculate stress score (0-100)
        stress_score = self._calculate_stress_score(indices, disease_conf, canopy_temp)
        
        detection = TreeDetection(
            tree_id=tree_id,
            gps_latitude=image.gps_latitude,
            gps_longitude=image.gps_longitude,
            canopy_area=canopy_area,
            canopy_diameter=canopy_diameter,
            tree_height=tree_height,
            vegetation_indices=indices,
            health_status=health_status,
            disease_detected=disease,
            disease_confidence=disease_conf,
            fruit_count=fruit_count,
            average_fruit_size=avg_fruit_size,
            canopy_temperature=canopy_temp,
            stress_score=stress_score
        )
        
        return detection
    
    def _segment_tree_canopy(self, rgb: np.ndarray, nir: np.ndarray) -> np.ndarray:
        """Segment tree canopy from background using NDVI threshold"""
        # Calculate NDVI
        red = rgb[:, :, 2]
        nir_resized = cv2.resize(nir, (red.shape[1], red.shape[0]))
        ndvi = self.calculate_ndvi(nir_resized, red)
        
        # Threshold: NDVI > 0.4 = vegetation
        canopy_mask = (ndvi > 0.4).astype(np.uint8) * 255
        
        # Morphological operations to clean up mask
        kernel = np.ones((5, 5), np.uint8)
        canopy_mask = cv2.morphologyEx(canopy_mask, cv2.MORPH_CLOSE, kernel)
        canopy_mask = cv2.morphologyEx(canopy_mask, cv2.MORPH_OPEN, kernel)
        
        return canopy_mask
    
    def _estimate_canopy_diameter(self, canopy_mask: np.ndarray, gsd: float) -> float:
        """Estimate canopy diameter from segmented mask"""
        # Find contours
        contours, _ = cv2.findContours(canopy_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        if len(contours) == 0:
            return 0.0
        
        # Largest contour = tree canopy
        largest_contour = max(contours, key=cv2.contourArea)
        
        # Fit ellipse to estimate diameter
        if len(largest_contour) >= 5:
            ellipse = cv2.fitEllipse(largest_contour)
            major_axis = max(ellipse[1]) * (gsd / 100)  # Convert to meters
            return major_axis
        
        return 0.0
    
    def _estimate_tree_height(self, altitude: float, canopy_diameter: float) -> float:
        """Estimate tree height from altitude and canopy diameter (empirical)"""
        # Empirical relationship: height ≈ canopy_diameter * 0.8 for most trees
        # In real system, uses stereo photogrammetry or LiDAR
        return canopy_diameter * 0.8
    
    def _detect_disease_from_spectral(self,
                                     image: MultispectralImage,
                                     indices: VegetationIndices) -> Tuple[Optional[AerialDiseaseType], float]:
        """Detect disease from spectral signatures"""
        
        best_match = None
        best_confidence = 0.0
        
        for disease, signature in self.disease_signatures.items():
            confidence = 0.0
            
            # Check NDVI range
            ndvi_min, ndvi_max = signature["ndvi_range"]
            if ndvi_min <= indices.ndvi <= ndvi_max:
                confidence += 0.4
            
            # Check thermal signature (if available)
            if image.thermal is not None and "thermal_delta" in signature:
                ambient_temp = np.percentile(image.thermal, 10)  # Cool areas = ambient
                canopy_temp = np.mean(image.thermal)
                temp_diff = canopy_temp - ambient_temp
                
                if abs(temp_diff - signature["thermal_delta"]) < 1.0:
                    confidence += 0.3
            
            # Check RGB signatures
            if signature.get("white_coating_rgb"):
                white_score = self._detect_white_coating(image.rgb)
                confidence += white_score * 0.3
            
            if signature.get("orange_color_rgb"):
                orange_score = self._detect_orange_color(image.rgb)
                confidence += orange_score * 0.3
            
            # Update best match
            if confidence > best_confidence:
                best_confidence = confidence
                best_match = disease
        
        # Threshold: require 50% confidence minimum
        if best_confidence < 0.5:
            return None, 0.0
        
        return best_match, best_confidence
    
    def _detect_white_coating(self, rgb: np.ndarray) -> float:
        """Detect white coating (powdery mildew) in RGB image"""
        # Convert to HSV
        hsv = cv2.cvtColor(rgb, cv2.COLOR_BGR2HSV)
        
        # White: low saturation, high value
        white_lower = np.array([0, 0, 200])
        white_upper = np.array([180, 50, 255])
        white_mask = cv2.inRange(hsv, white_lower, white_upper)
        
        # Calculate coverage
        coverage = np.sum(white_mask > 0) / white_mask.size
        
        return min(1.0, coverage * 20)  # Scale to 0-1
    
    def _detect_orange_color(self, rgb: np.ndarray) -> float:
        """Detect orange color (rust) in RGB image"""
        hsv = cv2.cvtColor(rgb, cv2.COLOR_BGR2HSV)
        
        # Orange: hue 10-25
        orange_lower = np.array([10, 100, 100])
        orange_upper = np.array([25, 255, 255])
        orange_mask = cv2.inRange(hsv, orange_lower, orange_upper)
        
        coverage = np.sum(orange_mask > 0) / orange_mask.size
        
        return min(1.0, coverage * 25)
    
    def _count_fruit(self, rgb: np.ndarray, canopy_mask: np.ndarray) -> Tuple[int, float]:
        """Count visible fruit in RGB image"""
        # Fruit detection varies by crop type
        # Mango: Yellow-orange color
        # Avocado: Dark green (difficult from foliage)
        # Citrus: Orange/yellow
        
        hsv = cv2.cvtColor(rgb, cv2.COLOR_BGR2HSV)
        
        # Detect fruit color (example: yellow-orange for mango)
        fruit_lower = np.array([20, 100, 100])
        fruit_upper = np.array([35, 255, 255])
        fruit_mask = cv2.inRange(hsv, fruit_lower, fruit_upper)
        
        # Apply canopy mask (only count fruit in canopy area)
        fruit_mask = cv2.bitwise_and(fruit_mask, canopy_mask)
        
        # Find fruit blobs
        contours, _ = cv2.findContours(fruit_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # Filter by size (fruit typically 50-500 pixels at 30m altitude)
        fruit_contours = [c for c in contours if 50 < cv2.contourArea(c) < 500]
        
        fruit_count = len(fruit_contours)
        
        # Calculate average fruit size
        if fruit_count > 0:
            avg_area = np.mean([cv2.contourArea(c) for c in fruit_contours])
            # Convert to cm (rough estimate based on GSD)
            avg_size = math.sqrt(avg_area) * 0.03  # Simplified
        else:
            avg_size = 0.0
        
        return fruit_count, avg_size
    
    def _calculate_stress_score(self,
                                indices: VegetationIndices,
                                disease_conf: float,
                                canopy_temp: float) -> float:
        """Calculate tree stress score (0-100, higher = more stress)"""
        
        # NDVI component (0-40 points)
        # Healthy NDVI > 0.7 = 0 stress, Dead NDVI < 0.1 = 40 stress
        ndvi_stress = max(0, 40 * (1 - indices.ndvi / 0.7))
        
        # Disease component (0-40 points)
        disease_stress = disease_conf * 40
        
        # Thermal component (0-20 points)
        # Assume ambient = 25°C, water stress = +5°C
        if canopy_temp > 0:
            temp_diff = max(0, canopy_temp - 25)
            temp_stress = min(20, temp_diff * 4)
        else:
            temp_stress = 0
        
        total_stress = ndvi_stress + disease_stress + temp_stress
        
        return min(100.0, total_stress)


def generate_ndvi_heatmap(ndvi: np.ndarray) -> np.ndarray:
    """Generate color-coded NDVI heatmap for visualization"""
    # Normalize NDVI to 0-255
    ndvi_normalized = ((ndvi + 1) / 2 * 255).astype(np.uint8)
    
    # Apply colormap (red = stressed, green = healthy)
    heatmap = cv2.applyColorMap(ndvi_normalized, cv2.COLORMAP_RdYlGn)
    
    return heatmap


if __name__ == "__main__":
    print("=" * 80)
    print("MULTISPECTRAL IMAGING & AERIAL DISEASE DETECTION")
    print("=" * 80)
    
    # Initialize processor
    processor = MultispectralProcessor()
    
    # Simulate multispectral image (mango tree)
    rgb_img = np.random.randint(0, 255, (2970, 5280, 3), dtype=np.uint8)
    nir_img = np.random.randint(100, 255, (960, 1280), dtype=np.uint8)
    thermal_img = np.random.uniform(20, 35, (512, 640))
    
    multispectral = MultispectralImage(
        rgb=rgb_img,
        nir=nir_img,
        thermal=thermal_img,
        timestamp=time.time(),
        gps_latitude=37.7749,
        gps_longitude=-122.4194,
        altitude=30.0,
        ground_sampling_distance=3.0  # 3 cm/pixel at 30m
    )
    
    # Process image
    print("\n📊 Processing Multispectral Image...")
    indices = processor.process_multispectral_image(multispectral)
    print(f"  NDVI: {indices.ndvi:.3f}")
    print(f"  GNDVI: {indices.gndvi:.3f}")
    print(f"  SAVI: {indices.savi:.3f}")
    print(f"  EVI: {indices.evi:.3f}")
    print(f"  Health Status: {indices.get_health_status().value}")
    
    # Detect tree
    print("\n🌳 Detecting Tree...")
    tree = processor.detect_tree_from_aerial(multispectral, tree_id="MANGO_001")
    print(f"  Canopy Area: {tree.canopy_area:.1f} m²")
    print(f"  Canopy Diameter: {tree.canopy_diameter:.1f} m")
    print(f"  Tree Height: {tree.tree_height:.1f} m")
    print(f"  Stress Score: {tree.stress_score:.1f}/100")
    if tree.disease_detected:
        print(f"  ⚠️  Disease Detected: {tree.disease_detected.value}")
        print(f"  Confidence: {tree.disease_confidence * 100:.1f}%")
    
    print("=" * 80)
