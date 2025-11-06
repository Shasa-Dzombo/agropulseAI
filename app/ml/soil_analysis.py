"""
Soil Analysis and Recommendation Module

This module provides comprehensive soil analysis and recommendations:
- Soil health assessment
- Nutrient deficiency detection
- Fertilizer recommendations
- Soil amendment suggestions
- pH correction strategies
- Organic matter management
- Soil texture analysis
- Micronutrient analysis
"""

import numpy as np
import pandas as pd
from typing import Dict, Any, List, Optional, Tuple, Union
from datetime import datetime
from dataclasses import dataclass
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class SoilHealth(Enum):
    """Soil health levels."""
    EXCELLENT = "excellent"
    GOOD = "good"
    FAIR = "fair"
    POOR = "poor"
    CRITICAL = "critical"


class NutrientLevel(Enum):
    """Nutrient level categories."""
    DEFICIENT = "deficient"
    LOW = "low"
    ADEQUATE = "adequate"
    HIGH = "high"
    EXCESSIVE = "excessive"


class SoilTexture(Enum):
    """Soil texture classifications."""
    SAND = "sand"
    LOAMY_SAND = "loamy_sand"
    SANDY_LOAM = "sandy_loam"
    LOAM = "loam"
    SILT_LOAM = "silt_loam"
    SILT = "silt"
    SANDY_CLAY_LOAM = "sandy_clay_loam"
    CLAY_LOAM = "clay_loam"
    SILTY_CLAY_LOAM = "silty_clay_loam"
    SANDY_CLAY = "sandy_clay"
    SILTY_CLAY = "silty_clay"
    CLAY = "clay"


@dataclass
class SoilAnalysisResult:
    """
    Soil analysis result.
    
    Attributes:
        overall_health: Overall soil health
        ph_level: Soil pH
        ph_classification: pH classification
        organic_matter_pct: Organic matter percentage
        nitrogen_level: Nitrogen level
        phosphorus_level: Phosphorus level
        potassium_level: Potassium level
        texture: Soil texture
        cec: Cation Exchange Capacity
        moisture_content: Moisture content
        bulk_density: Bulk density
        issues: Identified issues
        recommendations: Recommendations
    """
    overall_health: SoilHealth
    ph_level: float
    ph_classification: str
    organic_matter_pct: float
    nitrogen_level: NutrientLevel
    phosphorus_level: NutrientLevel
    potassium_level: NutrientLevel
    texture: SoilTexture
    cec: float
    moisture_content: float
    bulk_density: float
    issues: List[str]
    recommendations: List[str]


@dataclass
class FertilizerRecommendation:
    """
    Fertilizer recommendation.
    
    Attributes:
        fertilizer_type: Type of fertilizer
        npk_ratio: NPK ratio
        application_rate_kg_per_ha: Application rate
        application_method: Application method
        timing: Application timing
        cost_estimate: Estimated cost
        expected_benefit: Expected benefit
    """
    fertilizer_type: str
    npk_ratio: str
    application_rate_kg_per_ha: float
    application_method: str
    timing: List[str]
    cost_estimate: float
    expected_benefit: str


class SoilAnalyzer:
    """
    Comprehensive soil analysis system.
    """
    
    def __init__(self):
        """Initialize soil analyzer."""
        logger.info("Soil Analyzer initialized")
    
    def analyze_soil(self, soil_data: Dict[str, float]) -> SoilAnalysisResult:
        """
        Perform comprehensive soil analysis.
        
        Args:
            soil_data: Soil test results
            
        Returns:
            Soil analysis result
        """
        logger.info("Performing soil analysis")
        
        # Extract soil parameters
        ph = soil_data.get("ph", 7.0)
        nitrogen = soil_data.get("nitrogen", 50)
        phosphorus = soil_data.get("phosphorus", 30)
        potassium = soil_data.get("potassium", 40)
        organic_matter = soil_data.get("organic_matter", 2.5)
        moisture = soil_data.get("moisture", 50)
        sand_pct = soil_data.get("sand_pct", 40)
        silt_pct = soil_data.get("silt_pct", 30)
        clay_pct = soil_data.get("clay_pct", 30)
        cec = soil_data.get("cec", 15)
        bulk_density = soil_data.get("bulk_density", 1.3)
        
        # Analyze pH
        ph_classification = self._classify_ph(ph)
        
        # Analyze nutrients
        n_level = self._classify_nutrient(nitrogen, "nitrogen")
        p_level = self._classify_nutrient(phosphorus, "phosphorus")
        k_level = self._classify_nutrient(potassium, "potassium")
        
        # Determine soil texture
        texture = self._determine_texture(sand_pct, silt_pct, clay_pct)
        
        # Assess overall health
        overall_health = self._assess_overall_health(
            ph, nitrogen, phosphorus, potassium, organic_matter, cec
        )
        
        # Identify issues
        issues = self._identify_issues(
            ph, nitrogen, phosphorus, potassium, organic_matter, 
            moisture, bulk_density, texture
        )
        
        # Generate recommendations
        recommendations = self._generate_soil_recommendations(
            ph, n_level, p_level, k_level, organic_matter, texture, issues
        )
        
        return SoilAnalysisResult(
            overall_health=overall_health,
            ph_level=ph,
            ph_classification=ph_classification,
            organic_matter_pct=organic_matter,
            nitrogen_level=n_level,
            phosphorus_level=p_level,
            potassium_level=k_level,
            texture=texture,
            cec=cec,
            moisture_content=moisture,
            bulk_density=bulk_density,
            issues=issues,
            recommendations=recommendations
        )
    
    def _classify_ph(self, ph: float) -> str:
        """Classify soil pH."""
        if ph < 4.5:
            return "Extremely Acidic"
        elif ph < 5.5:
            return "Very Strongly Acidic"
        elif ph < 6.0:
            return "Strongly Acidic"
        elif ph < 6.5:
            return "Moderately Acidic"
        elif ph < 7.0:
            return "Slightly Acidic"
        elif ph == 7.0:
            return "Neutral"
        elif ph < 7.5:
            return "Slightly Alkaline"
        elif ph < 8.0:
            return "Moderately Alkaline"
        elif ph < 8.5:
            return "Strongly Alkaline"
        else:
            return "Very Strongly Alkaline"
    
    def _classify_nutrient(self, value: float, nutrient: str) -> NutrientLevel:
        """Classify nutrient level."""
        # Thresholds (kg/ha)
        thresholds = {
            "nitrogen": {"deficient": 30, "low": 60, "adequate": 120, "high": 180},
            "phosphorus": {"deficient": 15, "low": 30, "adequate": 60, "high": 100},
            "potassium": {"deficient": 20, "low": 40, "adequate": 80, "high": 120}
        }
        
        if nutrient not in thresholds:
            return NutrientLevel.ADEQUATE
        
        thresh = thresholds[nutrient]
        
        if value < thresh["deficient"]:
            return NutrientLevel.DEFICIENT
        elif value < thresh["low"]:
            return NutrientLevel.LOW
        elif value < thresh["adequate"]:
            return NutrientLevel.ADEQUATE
        elif value < thresh["high"]:
            return NutrientLevel.HIGH
        else:
            return NutrientLevel.EXCESSIVE
    
    def _determine_texture(self, sand: float, silt: float, clay: float) -> SoilTexture:
        """Determine soil texture using USDA textural triangle."""
        # Simplified texture classification
        if clay >= 40:
            if silt >= 40:
                return SoilTexture.SILTY_CLAY
            elif sand >= 45:
                return SoilTexture.SANDY_CLAY
            else:
                return SoilTexture.CLAY
        elif clay >= 27:
            if sand >= 45:
                return SoilTexture.SANDY_CLAY_LOAM
            elif silt >= 50:
                return SoilTexture.SILTY_CLAY_LOAM
            else:
                return SoilTexture.CLAY_LOAM
        elif clay >= 12:
            if sand >= 52:
                return SoilTexture.SANDY_LOAM
            elif silt >= 50:
                return SoilTexture.SILT_LOAM
            else:
                return SoilTexture.LOAM
        else:
            if sand >= 85:
                return SoilTexture.SAND
            elif sand >= 70:
                return SoilTexture.LOAMY_SAND
            elif silt >= 80:
                return SoilTexture.SILT
            else:
                return SoilTexture.SANDY_LOAM
    
    def _assess_overall_health(
        self,
        ph: float,
        nitrogen: float,
        phosphorus: float,
        potassium: float,
        organic_matter: float,
        cec: float
    ) -> SoilHealth:
        """Assess overall soil health."""
        score = 0
        max_score = 6
        
        # pH score
        if 6.0 <= ph <= 7.5:
            score += 1
        elif 5.5 <= ph <= 8.0:
            score += 0.5
        
        # Nutrient scores
        if nitrogen >= 60:
            score += 1
        elif nitrogen >= 30:
            score += 0.5
        
        if phosphorus >= 30:
            score += 1
        elif phosphorus >= 15:
            score += 0.5
        
        if potassium >= 40:
            score += 1
        elif potassium >= 20:
            score += 0.5
        
        # Organic matter score
        if organic_matter >= 3.0:
            score += 1
        elif organic_matter >= 2.0:
            score += 0.5
        
        # CEC score
        if cec >= 15:
            score += 1
        elif cec >= 10:
            score += 0.5
        
        # Convert to health level
        health_pct = (score / max_score) * 100
        
        if health_pct >= 85:
            return SoilHealth.EXCELLENT
        elif health_pct >= 70:
            return SoilHealth.GOOD
        elif health_pct >= 50:
            return SoilHealth.FAIR
        elif health_pct >= 30:
            return SoilHealth.POOR
        else:
            return SoilHealth.CRITICAL
    
    def _identify_issues(
        self,
        ph: float,
        nitrogen: float,
        phosphorus: float,
        potassium: float,
        organic_matter: float,
        moisture: float,
        bulk_density: float,
        texture: SoilTexture
    ) -> List[str]:
        """Identify soil issues."""
        issues = []
        
        # pH issues
        if ph < 5.5:
            issues.append(f"Soil is too acidic (pH {ph:.1f}) - may limit nutrient availability")
        elif ph > 8.0:
            issues.append(f"Soil is too alkaline (pH {ph:.1f}) - may cause micronutrient deficiencies")
        
        # Nutrient issues
        if nitrogen < 60:
            issues.append(f"Nitrogen deficiency detected ({nitrogen:.1f} kg/ha) - crops may show yellowing")
        if phosphorus < 30:
            issues.append(f"Low phosphorus levels ({phosphorus:.1f} kg/ha) - may affect root development")
        if potassium < 40:
            issues.append(f"Low potassium levels ({potassium:.1f} kg/ha) - may reduce disease resistance")
        
        # Organic matter
        if organic_matter < 2.0:
            issues.append(f"Low organic matter ({organic_matter:.1f}%) - poor soil structure and fertility")
        
        # Moisture issues
        if moisture < 30:
            issues.append("Low soil moisture - irrigation recommended")
        elif moisture > 80:
            issues.append("Excessive soil moisture - drainage issues possible")
        
        # Compaction
        if bulk_density > 1.6:
            issues.append(f"High bulk density ({bulk_density:.2f} g/cm³) - soil compaction limiting root growth")
        
        # Texture-specific issues
        if texture in [SoilTexture.SAND, SoilTexture.LOAMY_SAND]:
            issues.append("Sandy soil - low water and nutrient retention, frequent irrigation needed")
        elif texture in [SoilTexture.CLAY, SoilTexture.SILTY_CLAY]:
            issues.append("Heavy clay soil - poor drainage and aeration, susceptible to waterlogging")
        
        return issues
    
    def _generate_soil_recommendations(
        self,
        ph: float,
        n_level: NutrientLevel,
        p_level: NutrientLevel,
        k_level: NutrientLevel,
        organic_matter: float,
        texture: SoilTexture,
        issues: List[str]
    ) -> List[str]:
        """Generate soil improvement recommendations."""
        recommendations = []
        
        # pH corrections
        if ph < 5.5:
            lime_rate = (6.5 - ph) * 2000  # Simplified lime requirement
            recommendations.append(f"Apply agricultural lime at {lime_rate:.0f} kg/ha to raise pH")
            recommendations.append("Split lime application: half before plowing, half after")
        elif ph > 8.0:
            recommendations.append("Apply sulfur or acidifying fertilizers to lower pH")
            recommendations.append("Use ammonium-based fertilizers which have acidifying effect")
        
        # Nutrient recommendations
        if n_level in [NutrientLevel.DEFICIENT, NutrientLevel.LOW]:
            recommendations.append("Apply nitrogen fertilizer (Urea or CAN) at recommended rates")
            recommendations.append("Consider split application: 1/3 at planting, 1/3 at vegetative, 1/3 at flowering")
        
        if p_level in [NutrientLevel.DEFICIENT, NutrientLevel.LOW]:
            recommendations.append("Apply phosphate fertilizer (DAP or TSP) before planting")
            recommendations.append("Incorporate phosphorus into soil as it has low mobility")
        
        if k_level in [NutrientLevel.DEFICIENT, NutrientLevel.LOW]:
            recommendations.append("Apply potassium fertilizer (Muriate of Potash)")
            recommendations.append("Split potassium application for sandy soils to reduce leaching")
        
        # Organic matter
        if organic_matter < 3.0:
            recommendations.append("Increase organic matter by applying compost or manure (5-10 tons/ha)")
            recommendations.append("Practice crop residue incorporation")
            recommendations.append("Consider cover cropping during off-season")
        
        # Texture-specific recommendations
        if texture in [SoilTexture.SAND, SoilTexture.LOAMY_SAND]:
            recommendations.append("Add organic matter to improve water and nutrient retention")
            recommendations.append("Use mulching to reduce water evaporation")
            recommendations.append("Apply nutrients in smaller, more frequent doses")
        elif texture in [SoilTexture.CLAY, SoilTexture.SILTY_CLAY]:
            recommendations.append("Improve drainage by creating raised beds or installing drainage systems")
            recommendations.append("Add organic matter and sand to improve soil structure")
            recommendations.append("Avoid working soil when too wet to prevent compaction")
        
        # General recommendations
        recommendations.append("Conduct soil tests annually to monitor changes")
        recommendations.append("Practice crop rotation to maintain soil health")
        
        return recommendations


class FertilizerCalculator:
    """
    Calculate fertilizer requirements.
    """
    
    def __init__(self):
        """Initialize fertilizer calculator."""
        self.fertilizer_database = self._initialize_fertilizer_database()
        logger.info("Fertilizer Calculator initialized")
    
    def _initialize_fertilizer_database(self) -> Dict[str, Dict[str, Any]]:
        """Initialize fertilizer database."""
        return {
            "urea": {
                "npk": "46-0-0",
                "nitrogen_pct": 46,
                "phosphorus_pct": 0,
                "potassium_pct": 0,
                "price_per_kg": 80,  # KES
                "application_method": "broadcast or topdressing"
            },
            "dap": {
                "npk": "18-46-0",
                "nitrogen_pct": 18,
                "phosphorus_pct": 46,
                "potassium_pct": 0,
                "price_per_kg": 100,
                "application_method": "band placement at planting"
            },
            "can": {
                "npk": "26-0-0",
                "nitrogen_pct": 26,
                "phosphorus_pct": 0,
                "potassium_pct": 0,
                "price_per_kg": 75,
                "application_method": "topdressing"
            },
            "mop": {
                "npk": "0-0-60",
                "nitrogen_pct": 0,
                "phosphorus_pct": 0,
                "potassium_pct": 60,
                "price_per_kg": 70,
                "application_method": "broadcast before planting"
            },
            "npk_17_17_17": {
                "npk": "17-17-17",
                "nitrogen_pct": 17,
                "phosphorus_pct": 17,
                "potassium_pct": 17,
                "price_per_kg": 90,
                "application_method": "broadcast at planting"
            },
            "npk_23_23_0": {
                "npk": "23-23-0",
                "nitrogen_pct": 23,
                "phosphorus_pct": 23,
                "potassium_pct": 0,
                "price_per_kg": 85,
                "application_method": "band placement at planting"
            }
        }
    
    def calculate_fertilizer_requirement(
        self,
        crop: str,
        area_ha: float,
        soil_analysis: SoilAnalysisResult,
        target_yield: Optional[float] = None
    ) -> List[FertilizerRecommendation]:
        """
        Calculate fertilizer requirements.
        
        Args:
            crop: Crop type
            area_ha: Farm area in hectares
            soil_analysis: Soil analysis result
            target_yield: Target yield (tons/ha)
            
        Returns:
            List of fertilizer recommendations
        """
        logger.info(f"Calculating fertilizer requirements for {crop}")
        
        # Get crop nutrient requirements
        crop_requirements = self._get_crop_requirements(crop, target_yield)
        
        # Calculate nutrient deficit
        n_deficit = self._calculate_nutrient_deficit(
            crop_requirements["nitrogen"],
            self._nutrient_level_to_kg(soil_analysis.nitrogen_level)
        )
        
        p_deficit = self._calculate_nutrient_deficit(
            crop_requirements["phosphorus"],
            self._nutrient_level_to_kg(soil_analysis.phosphorus_level)
        )
        
        k_deficit = self._calculate_nutrient_deficit(
            crop_requirements["potassium"],
            self._nutrient_level_to_kg(soil_analysis.potassium_level)
        )
        
        # Generate fertilizer recommendations
        recommendations = []
        
        # Basal fertilizer (at planting)
        if p_deficit > 0 or n_deficit > 0:
            recommendations.append(self._recommend_basal_fertilizer(
                n_deficit, p_deficit, k_deficit, area_ha
            ))
        
        # Topdressing fertilizer
        if n_deficit > 50:
            recommendations.append(self._recommend_topdress_fertilizer(
                n_deficit, area_ha
            ))
        
        # Potassium fertilizer
        if k_deficit > 30:
            recommendations.append(self._recommend_potassium_fertilizer(
                k_deficit, area_ha
            ))
        
        return recommendations
    
    def _get_crop_requirements(self, crop: str, target_yield: Optional[float]) -> Dict[str, float]:
        """Get crop nutrient requirements."""
        # Simplified crop requirements (kg/ha)
        base_requirements = {
            "maize": {"nitrogen": 120, "phosphorus": 60, "potassium": 60},
            "wheat": {"nitrogen": 100, "phosphorus": 50, "potassium": 50},
            "rice": {"nitrogen": 140, "phosphorus": 60, "potassium": 60},
            "beans": {"nitrogen": 40, "phosphorus": 60, "potassium": 50},
            "potatoes": {"nitrogen": 120, "phosphorus": 80, "potassium": 150},
            "tomatoes": {"nitrogen": 150, "phosphorus": 100, "potassium": 120},
            "cabbage": {"nitrogen": 150, "phosphorus": 80, "potassium": 120},
            "kale": {"nitrogen": 120, "phosphorus": 60, "potassium": 80}
        }
        
        requirements = base_requirements.get(crop, {"nitrogen": 100, "phosphorus": 60, "potassium": 60})
        
        # Adjust for target yield if provided
        if target_yield:
            factor = min(1.5, target_yield / 5.0)  # Scale based on yield target
            requirements = {k: v * factor for k, v in requirements.items()}
        
        return requirements
    
    def _nutrient_level_to_kg(self, level: NutrientLevel) -> float:
        """Convert nutrient level to kg/ha estimate."""
        mapping = {
            NutrientLevel.DEFICIENT: 20,
            NutrientLevel.LOW: 45,
            NutrientLevel.ADEQUATE: 75,
            NutrientLevel.HIGH: 110,
            NutrientLevel.EXCESSIVE: 150
        }
        return mapping.get(level, 60)
    
    def _calculate_nutrient_deficit(self, requirement: float, available: float) -> float:
        """Calculate nutrient deficit."""
        return max(0, requirement - available)
    
    def _recommend_basal_fertilizer(
        self,
        n_deficit: float,
        p_deficit: float,
        k_deficit: float,
        area_ha: float
    ) -> FertilizerRecommendation:
        """Recommend basal fertilizer."""
        # Use DAP for both N and P
        if p_deficit > n_deficit * 0.5:
            fertilizer = "dap"
            info = self.fertilizer_database[fertilizer]
            
            # Calculate rate based on P requirement
            rate = (p_deficit / info["phosphorus_pct"]) * 100
        else:
            # Use NPK 17-17-17 for balanced nutrition
            fertilizer = "npk_17_17_17"
            info = self.fertilizer_database[fertilizer]
            rate = max(
                (n_deficit / info["nitrogen_pct"]) * 100,
                (p_deficit / info["phosphorus_pct"]) * 100
            )
        
        total_cost = rate * area_ha * info["price_per_kg"]
        
        return FertilizerRecommendation(
            fertilizer_type=fertilizer.upper(),
            npk_ratio=info["npk"],
            application_rate_kg_per_ha=rate,
            application_method=info["application_method"],
            timing=["At planting", "Apply in bands 5cm from seed"],
            cost_estimate=total_cost,
            expected_benefit="Provides essential nutrients for early growth and root development"
        )
    
    def _recommend_topdress_fertilizer(self, n_deficit: float, area_ha: float) -> FertilizerRecommendation:
        """Recommend topdressing fertilizer."""
        fertilizer = "can"
        info = self.fertilizer_database[fertilizer]
        
        # Calculate rate for remaining N
        rate = (n_deficit * 0.6 / info["nitrogen_pct"]) * 100  # 60% as topdressing
        total_cost = rate * area_ha * info["price_per_kg"]
        
        return FertilizerRecommendation(
            fertilizer_type=fertilizer.upper(),
            npk_ratio=info["npk"],
            application_rate_kg_per_ha=rate,
            application_method=info["application_method"],
            timing=[
                "30-35 days after planting (vegetative stage)",
                "Apply when soil is moist",
                "Cover with soil after application"
            ],
            cost_estimate=total_cost,
            expected_benefit="Boosts vegetative growth and increases yield potential"
        )
    
    def _recommend_potassium_fertilizer(self, k_deficit: float, area_ha: float) -> FertilizerRecommendation:
        """Recommend potassium fertilizer."""
        fertilizer = "mop"
        info = self.fertilizer_database[fertilizer]
        
        rate = (k_deficit / info["potassium_pct"]) * 100
        total_cost = rate * area_ha * info["price_per_kg"]
        
        return FertilizerRecommendation(
            fertilizer_type=fertilizer.upper(),
            npk_ratio=info["npk"],
            application_rate_kg_per_ha=rate,
            application_method=info["application_method"],
            timing=[
                "Before planting",
                "Incorporate into soil during land preparation"
            ],
            cost_estimate=total_cost,
            expected_benefit="Improves disease resistance, water use efficiency, and crop quality"
        )


class SoilHealthMonitor:
    """
    Monitor soil health over time.
    """
    
    def __init__(self):
        """Initialize soil health monitor."""
        self.historical_data: Dict[str, List[Dict[str, Any]]] = {}
        logger.info("Soil Health Monitor initialized")
    
    def record_soil_test(self, farm_id: str, analysis: SoilAnalysisResult):
        """
        Record soil test result.
        
        Args:
            farm_id: Farm identifier
            analysis: Soil analysis result
        """
        if farm_id not in self.historical_data:
            self.historical_data[farm_id] = []
        
        record = {
            "timestamp": datetime.now().isoformat(),
            "ph": analysis.ph_level,
            "nitrogen": self._nutrient_level_to_kg(analysis.nitrogen_level),
            "phosphorus": self._nutrient_level_to_kg(analysis.phosphorus_level),
            "potassium": self._nutrient_level_to_kg(analysis.potassium_level),
            "organic_matter": analysis.organic_matter_pct,
            "health": analysis.overall_health.value
        }
        
        self.historical_data[farm_id].append(record)
        logger.info(f"Recorded soil test for farm {farm_id}")
    
    def _nutrient_level_to_kg(self, level: NutrientLevel) -> float:
        """Convert nutrient level to kg estimate."""
        mapping = {
            NutrientLevel.DEFICIENT: 20,
            NutrientLevel.LOW: 45,
            NutrientLevel.ADEQUATE: 75,
            NutrientLevel.HIGH: 110,
            NutrientLevel.EXCESSIVE: 150
        }
        return mapping.get(level, 60)
    
    def analyze_trends(self, farm_id: str) -> Dict[str, Any]:
        """
        Analyze soil health trends.
        
        Args:
            farm_id: Farm identifier
            
        Returns:
            Trend analysis
        """
        if farm_id not in self.historical_data or len(self.historical_data[farm_id]) < 2:
            return {"status": "insufficient_data", "message": "Need at least 2 soil tests for trend analysis"}
        
        data = self.historical_data[farm_id]
        
        # Calculate trends
        ph_trend = self._calculate_trend([d["ph"] for d in data])
        n_trend = self._calculate_trend([d["nitrogen"] for d in data])
        p_trend = self._calculate_trend([d["phosphorus"] for d in data])
        k_trend = self._calculate_trend([d["potassium"] for d in data])
        om_trend = self._calculate_trend([d["organic_matter"] for d in data])
        
        trends = {
            "farm_id": farm_id,
            "tests_count": len(data),
            "first_test": data[0]["timestamp"],
            "last_test": data[-1]["timestamp"],
            "ph_trend": ph_trend,
            "nitrogen_trend": n_trend,
            "phosphorus_trend": p_trend,
            "potassium_trend": k_trend,
            "organic_matter_trend": om_trend,
            "overall_assessment": self._assess_overall_trend(
                ph_trend, n_trend, p_trend, k_trend, om_trend
            )
        }
        
        return trends
    
    def _calculate_trend(self, values: List[float]) -> str:
        """Calculate trend direction."""
        if len(values) < 2:
            return "stable"
        
        # Simple linear trend
        changes = [values[i+1] - values[i] for i in range(len(values)-1)]
        avg_change = np.mean(changes)
        
        if avg_change > 0.1:
            return "increasing"
        elif avg_change < -0.1:
            return "declining"
        else:
            return "stable"
    
    def _assess_overall_trend(
        self,
        ph_trend: str,
        n_trend: str,
        p_trend: str,
        k_trend: str,
        om_trend: str
    ) -> str:
        """Assess overall soil health trend."""
        positive_trends = sum([
            1 for t in [n_trend, p_trend, k_trend, om_trend]
            if t == "increasing"
        ])
        
        negative_trends = sum([
            1 for t in [n_trend, p_trend, k_trend, om_trend]
            if t == "declining"
        ])
        
        if positive_trends >= 3:
            return "improving"
        elif negative_trends >= 3:
            return "deteriorating"
        else:
            return "stable"
