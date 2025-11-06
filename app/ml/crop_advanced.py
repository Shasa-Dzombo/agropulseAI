"""
Advanced Crop Recommendation Features

This module provides advanced crop recommendation capabilities:
- Crop rotation optimization
- Intercropping recommendations
- Seasonal planning
- Risk assessment
- Economic optimization
- Climate change adaptation
"""

import numpy as np
import pandas as pd
from typing import Dict, Any, List, Optional, Set, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class RiskLevel(Enum):
    """Risk level for crop recommendations."""
    VERY_LOW = "very_low"
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    VERY_HIGH = "very_high"


class CropCategory(Enum):
    """Crop categories for rotation."""
    CEREALS = "cereals"
    LEGUMES = "legumes"
    VEGETABLES = "vegetables"
    ROOTS_TUBERS = "roots_tubers"
    CASH_CROPS = "cash_crops"


@dataclass
class CropRotationPlan:
    """
    Crop rotation plan.
    
    Attributes:
        seasons: List of crops per season
        benefits: Expected benefits
        nitrogen_balance: N balance over rotation
        risk_level: Overall risk level
        expected_yield: Total expected yield
        economic_value: Expected economic value
    """
    seasons: List[Dict[str, Any]]
    benefits: List[str]
    nitrogen_balance: float
    risk_level: RiskLevel
    expected_yield: float
    economic_value: float
    rotation_length_years: int


@dataclass
class IntercroppingRecommendation:
    """
    Intercropping recommendation.
    
    Attributes:
        main_crop: Primary crop
        companion_crops: List of companion crops
        spacing_pattern: Planting pattern
        benefits: Benefits of intercropping
        management_tips: Management recommendations
        yield_increase_pct: Expected yield increase
    """
    main_crop: str
    companion_crops: List[str]
    spacing_pattern: str
    benefits: List[str]
    management_tips: List[str]
    yield_increase_pct: float


@dataclass
class RiskAssessment:
    """
    Crop risk assessment.
    
    Attributes:
        overall_risk: Overall risk level
        pest_risk: Pest pressure risk
        disease_risk: Disease risk
        climate_risk: Climate-related risk
        market_risk: Market volatility risk
        mitigation_strategies: Risk mitigation strategies
    """
    overall_risk: RiskLevel
    pest_risk: RiskLevel
    disease_risk: RiskLevel
    climate_risk: RiskLevel
    market_risk: RiskLevel
    mitigation_strategies: List[str]


# Crop categories for rotation planning
CROP_CATEGORIES = {
    "maize": CropCategory.CEREALS,
    "wheat": CropCategory.CEREALS,
    "rice": CropCategory.CEREALS,
    "beans": CropCategory.LEGUMES,
    "potatoes": CropCategory.ROOTS_TUBERS,
    "tomatoes": CropCategory.VEGETABLES,
    "kale": CropCategory.VEGETABLES,
    "cabbage": CropCategory.VEGETABLES,
    "sugarcane": CropCategory.CASH_CROPS,
    "bananas": CropCategory.CASH_CROPS
}


# Nitrogen contribution (kg/ha/season)
NITROGEN_CONTRIBUTION = {
    "maize": -80,  # Heavy N consumer
    "wheat": -70,
    "rice": -90,
    "beans": 40,  # N fixer
    "potatoes": -60,
    "tomatoes": -100,
    "kale": -70,
    "cabbage": -80,
    "sugarcane": -150,
    "bananas": -120
}


# Intercropping compatibility matrix
INTERCROPPING_COMPATIBLE = {
    "maize": ["beans", "potatoes"],
    "beans": ["maize"],
    "potatoes": ["maize", "beans"],
    "tomatoes": ["kale", "cabbage"],
    "kale": ["tomatoes"],
    "cabbage": ["tomatoes"],
    "bananas": ["beans", "kale"]
}


class CropRotationOptimizer:
    """
    Optimize crop rotation for sustainability and profitability.
    """
    
    def __init__(self):
        """Initialize crop rotation optimizer."""
        self.crop_categories = CROP_CATEGORIES
        self.nitrogen_contrib = NITROGEN_CONTRIBUTION
        logger.info("Crop Rotation Optimizer initialized")
    
    def generate_rotation_plan(
        self,
        farm_size_ha: float,
        available_crops: List[str],
        years: int = 3,
        objectives: Optional[Dict[str, float]] = None
    ) -> CropRotationPlan:
        """
        Generate optimal crop rotation plan.
        
        Args:
            farm_size_ha: Farm size in hectares
            available_crops: List of crops to include
            years: Rotation length in years
            objectives: Weights for objectives (nitrogen_balance, yield, profit)
            
        Returns:
            Crop rotation plan
        """
        if objectives is None:
            objectives = {
                "nitrogen_balance": 0.3,
                "yield": 0.4,
                "profit": 0.3
            }
        
        # Generate rotation sequences
        best_rotation = self._optimize_rotation_sequence(
            available_crops,
            years,
            objectives
        )
        
        # Calculate benefits
        benefits = self._analyze_rotation_benefits(best_rotation)
        
        # Calculate N balance
        n_balance = sum(
            self.nitrogen_contrib.get(crop, 0)
            for crop in best_rotation
        )
        
        # Assess risk
        risk_level = self._assess_rotation_risk(best_rotation)
        
        # Estimate yields and economic value
        expected_yield = self._estimate_rotation_yield(best_rotation, farm_size_ha)
        economic_value = self._estimate_rotation_value(best_rotation, farm_size_ha)
        
        # Create seasonal plan
        seasons = []
        for year in range(years):
            long_rains_crop = best_rotation[year * 2] if year * 2 < len(best_rotation) else best_rotation[0]
            short_rains_crop = best_rotation[year * 2 + 1] if year * 2 + 1 < len(best_rotation) else best_rotation[1]
            
            seasons.append({
                "year": year + 1,
                "long_rains": long_rains_crop,
                "short_rains": short_rains_crop,
                "management_notes": self._get_management_notes(long_rains_crop, short_rains_crop)
            })
        
        return CropRotationPlan(
            seasons=seasons,
            benefits=benefits,
            nitrogen_balance=n_balance,
            risk_level=risk_level,
            expected_yield=expected_yield,
            economic_value=economic_value,
            rotation_length_years=years
        )
    
    def _optimize_rotation_sequence(
        self,
        crops: List[str],
        years: int,
        objectives: Dict[str, float]
    ) -> List[str]:
        """Optimize crop sequence using simple heuristics."""
        sequence = []
        n_seasons = years * 2  # Two seasons per year
        
        # Ensure diversity - alternate categories
        remaining_crops = crops.copy()
        last_category = None
        
        for i in range(n_seasons):
            # Select next crop
            if i % 4 == 0 and "beans" in remaining_crops:
                # Every 4th season, plant legume for N fixation
                next_crop = "beans"
            else:
                # Select from different category than last
                candidates = [
                    c for c in remaining_crops
                    if self.crop_categories.get(c) != last_category
                ]
                if not candidates:
                    candidates = remaining_crops
                
                # Score candidates based on objectives
                scores = {}
                for crop in candidates:
                    score = 0
                    score += self.nitrogen_contrib.get(crop, 0) * objectives.get("nitrogen_balance", 0.3)
                    # Add yield and profit factors (simplified)
                    score += np.random.uniform(0, 1) * objectives.get("yield", 0.4)
                    scores[crop] = score
                
                next_crop = max(scores, key=scores.get)
            
            sequence.append(next_crop)
            last_category = self.crop_categories.get(next_crop)
            
            # Replenish if all used
            if next_crop in remaining_crops:
                remaining_crops.remove(next_crop)
            if not remaining_crops:
                remaining_crops = crops.copy()
        
        return sequence
    
    def _analyze_rotation_benefits(self, rotation: List[str]) -> List[str]:
        """Analyze benefits of rotation plan."""
        benefits = []
        
        # Check for legumes
        if any(self.crop_categories.get(c) == CropCategory.LEGUMES for c in rotation):
            benefits.append("Nitrogen fixation from legumes reduces fertilizer costs")
        
        # Check for diversity
        categories = set(self.crop_categories.get(c) for c in rotation)
        if len(categories) >= 3:
            benefits.append("High crop diversity reduces pest and disease pressure")
        
        # Check for N balance
        n_balance = sum(self.nitrogen_contrib.get(c, 0) for c in rotation)
        if n_balance > -50:
            benefits.append("Good nitrogen balance maintains soil fertility")
        
        benefits.append("Crop rotation breaks pest and disease cycles")
        benefits.append("Improved soil structure and organic matter")
        
        return benefits
    
    def _assess_rotation_risk(self, rotation: List[str]) -> RiskLevel:
        """Assess risk level of rotation plan."""
        # Simple risk assessment
        categories = set(self.crop_categories.get(c) for c in rotation)
        
        if len(categories) >= 4:
            return RiskLevel.VERY_LOW
        elif len(categories) >= 3:
            return RiskLevel.LOW
        elif len(categories) >= 2:
            return RiskLevel.MODERATE
        else:
            return RiskLevel.HIGH
    
    def _estimate_rotation_yield(self, rotation: List[str], farm_size: float) -> float:
        """Estimate total yield over rotation."""
        # Simplified yield estimation
        from app.ml.crop_recommendation import CROP_DATABASE
        
        total_yield = 0
        for crop in rotation:
            if crop in CROP_DATABASE:
                yield_avg = np.mean(CROP_DATABASE[crop]["yield_potential"])
                total_yield += yield_avg * farm_size
        
        return total_yield
    
    def _estimate_rotation_value(self, rotation: List[str], farm_size: float) -> float:
        """Estimate economic value over rotation."""
        # Simplified economic estimation (tons * average price)
        total_yield = self._estimate_rotation_yield(rotation, farm_size)
        average_price_per_ton = 20000  # KES (simplified)
        return total_yield * average_price_per_ton
    
    def _get_management_notes(self, crop1: str, crop2: str) -> List[str]:
        """Get management notes for crop pairing."""
        notes = []
        
        if crop1 == crop2:
            notes.append(f"Consider splitting farm for {crop1} in both seasons")
        else:
            notes.append(f"Alternate {crop1} and {crop2} for optimal land use")
        
        # Check for legumes
        if self.crop_categories.get(crop1) == CropCategory.LEGUMES:
            notes.append(f"{crop1} will fix nitrogen for subsequent crops")
        
        return notes


class IntercroppingAdvisor:
    """
    Advise on intercropping opportunities.
    """
    
    def __init__(self):
        """Initialize intercropping advisor."""
        self.compatibility = INTERCROPPING_COMPATIBLE
        logger.info("Intercropping Advisor initialized")
    
    def recommend_intercropping(
        self,
        main_crop: str,
        farm_conditions: Dict[str, Any]
    ) -> Optional[IntercroppingRecommendation]:
        """
        Recommend intercropping pattern.
        
        Args:
            main_crop: Primary crop
            farm_conditions: Farm conditions
            
        Returns:
            Intercropping recommendation or None
        """
        # Check if intercropping is suitable
        if main_crop not in self.compatibility:
            logger.info(f"No intercropping patterns available for {main_crop}")
            return None
        
        compatible_crops = self.compatibility[main_crop]
        
        if not compatible_crops:
            return None
        
        # Analyze benefits
        benefits = self._analyze_intercropping_benefits(main_crop, compatible_crops)
        
        # Determine spacing pattern
        spacing = self._determine_spacing_pattern(main_crop, compatible_crops[0])
        
        # Management tips
        tips = self._get_management_tips(main_crop, compatible_crops)
        
        # Estimate yield increase
        yield_increase = self._estimate_yield_increase(main_crop, compatible_crops)
        
        return IntercroppingRecommendation(
            main_crop=main_crop,
            companion_crops=compatible_crops,
            spacing_pattern=spacing,
            benefits=benefits,
            management_tips=tips,
            yield_increase_pct=yield_increase
        )
    
    def _analyze_intercropping_benefits(
        self,
        main_crop: str,
        companions: List[str]
    ) -> List[str]:
        """Analyze intercropping benefits."""
        benefits = []
        
        # Check for legumes
        from app.ml.crop_recommendation import CROP_DATABASE
        
        for companion in companions:
            if CROP_CATEGORIES.get(companion) == CropCategory.LEGUMES:
                benefits.append(f"{companion} fixes nitrogen for {main_crop}")
        
        benefits.append("Better land use efficiency")
        benefits.append("Reduced pest pressure through diversity")
        benefits.append("Improved soil cover and weed suppression")
        benefits.append("Risk diversification - multiple income sources")
        
        return benefits
    
    def _determine_spacing_pattern(self, main_crop: str, companion: str) -> str:
        """Determine planting pattern."""
        # Simplified spacing patterns
        patterns = {
            ("maize", "beans"): "2 rows maize : 2 rows beans",
            ("beans", "maize"): "2 rows beans : 2 rows maize",
            ("maize", "potatoes"): "Alternate rows",
            ("tomatoes", "kale"): "Border planting - kale around tomato beds"
        }
        
        return patterns.get((main_crop, companion), "Alternate rows or strips")
    
    def _get_management_tips(self, main_crop: str, companions: List[str]) -> List[str]:
        """Get management tips."""
        tips = [
            f"Plant {main_crop} first, then {companions[0]} 2-3 weeks later",
            "Adjust fertilizer rates - reduce N if planting with legumes",
            "Monitor spacing to avoid competition",
            "Harvest companion crop first if it matures earlier",
            "Consider staggered planting for continuous harvest"
        ]
        return tips
    
    def _estimate_yield_increase(self, main_crop: str, companions: List[str]) -> float:
        """Estimate yield increase from intercropping."""
        # Land Equivalent Ratio typically 1.2-1.5 for good intercropping
        # Translates to 20-50% increase in productivity per unit area
        return np.random.uniform(15, 35)  # 15-35% increase


class CropRiskAssessor:
    """
    Assess risks for crop recommendations.
    """
    
    def __init__(self):
        """Initialize risk assessor."""
        logger.info("Crop Risk Assessor initialized")
    
    def assess_crop_risk(
        self,
        crop: str,
        conditions: Dict[str, Any],
        historical_data: Optional[Dict[str, Any]] = None
    ) -> RiskAssessment:
        """
        Assess risk for crop under given conditions.
        
        Args:
            crop: Crop name
            conditions: Current conditions
            historical_data: Historical performance data
            
        Returns:
            Risk assessment
        """
        # Assess individual risk factors
        pest_risk = self._assess_pest_risk(crop, conditions)
        disease_risk = self._assess_disease_risk(crop, conditions)
        climate_risk = self._assess_climate_risk(crop, conditions)
        market_risk = self._assess_market_risk(crop)
        
        # Calculate overall risk
        risk_scores = {
            RiskLevel.VERY_LOW: 1,
            RiskLevel.LOW: 2,
            RiskLevel.MODERATE: 3,
            RiskLevel.HIGH: 4,
            RiskLevel.VERY_HIGH: 5
        }
        
        avg_risk_score = np.mean([
            risk_scores[pest_risk],
            risk_scores[disease_risk],
            risk_scores[climate_risk],
            risk_scores[market_risk]
        ])
        
        if avg_risk_score < 2:
            overall_risk = RiskLevel.VERY_LOW
        elif avg_risk_score < 2.5:
            overall_risk = RiskLevel.LOW
        elif avg_risk_score < 3.5:
            overall_risk = RiskLevel.MODERATE
        elif avg_risk_score < 4.5:
            overall_risk = RiskLevel.HIGH
        else:
            overall_risk = RiskLevel.VERY_HIGH
        
        # Generate mitigation strategies
        mitigation = self._generate_mitigation_strategies(
            crop,
            pest_risk,
            disease_risk,
            climate_risk,
            market_risk
        )
        
        return RiskAssessment(
            overall_risk=overall_risk,
            pest_risk=pest_risk,
            disease_risk=disease_risk,
            climate_risk=climate_risk,
            market_risk=market_risk,
            mitigation_strategies=mitigation
        )
    
    def _assess_pest_risk(self, crop: str, conditions: Dict[str, Any]) -> RiskLevel:
        """Assess pest risk."""
        # Simplified pest risk assessment
        temperature = conditions.get("temperature", 25)
        humidity = conditions.get("humidity", 60)
        
        # High temp + high humidity = higher pest risk
        if temperature > 28 and humidity > 70:
            return RiskLevel.HIGH
        elif temperature > 25 and humidity > 60:
            return RiskLevel.MODERATE
        else:
            return RiskLevel.LOW
    
    def _assess_disease_risk(self, crop: str, conditions: Dict[str, Any]) -> RiskLevel:
        """Assess disease risk."""
        # Simplified disease risk assessment
        humidity = conditions.get("humidity", 60)
        rainfall = conditions.get("rainfall", 0)
        
        # High humidity + rainfall = higher disease risk
        if humidity > 80 or rainfall > 100:
            return RiskLevel.HIGH
        elif humidity > 70 or rainfall > 50:
            return RiskLevel.MODERATE
        else:
            return RiskLevel.LOW
    
    def _assess_climate_risk(self, crop: str, conditions: Dict[str, Any]) -> RiskLevel:
        """Assess climate risk."""
        from app.ml.crop_recommendation import CROP_DATABASE
        
        if crop not in CROP_DATABASE:
            return RiskLevel.MODERATE
        
        crop_info = CROP_DATABASE[crop]
        temp = conditions.get("temperature", 25)
        rainfall = conditions.get("total_rainfall_season", 500)
        
        # Check temperature deviation
        temp_range = crop_info["temperature_range"]
        temp_deviation = 0
        if temp < temp_range[0]:
            temp_deviation = temp_range[0] - temp
        elif temp > temp_range[1]:
            temp_deviation = temp - temp_range[1]
        
        # Check rainfall deviation
        rain_req = crop_info["rainfall_requirement"]
        rain_deviation_pct = abs(rainfall - np.mean(rain_req)) / np.mean(rain_req)
        
        if temp_deviation > 5 or rain_deviation_pct > 0.4:
            return RiskLevel.HIGH
        elif temp_deviation > 3 or rain_deviation_pct > 0.25:
            return RiskLevel.MODERATE
        else:
            return RiskLevel.LOW
    
    def _assess_market_risk(self, crop: str) -> RiskLevel:
        """Assess market risk."""
        from app.ml.crop_recommendation import CROP_DATABASE
        
        if crop not in CROP_DATABASE:
            return RiskLevel.MODERATE
        
        market_demand = CROP_DATABASE[crop]["market_demand"]
        
        if market_demand == "very_high":
            return RiskLevel.VERY_LOW
        elif market_demand == "high":
            return RiskLevel.LOW
        else:
            return RiskLevel.MODERATE
    
    def _generate_mitigation_strategies(
        self,
        crop: str,
        pest_risk: RiskLevel,
        disease_risk: RiskLevel,
        climate_risk: RiskLevel,
        market_risk: RiskLevel
    ) -> List[str]:
        """Generate risk mitigation strategies."""
        strategies = []
        
        # Pest risk mitigation
        if pest_risk in [RiskLevel.HIGH, RiskLevel.VERY_HIGH]:
            strategies.extend([
                "Implement Integrated Pest Management (IPM) practices",
                "Use pest-resistant varieties",
                "Regular crop monitoring and early intervention",
                "Maintain field hygiene and remove crop residues"
            ])
        
        # Disease risk mitigation
        if disease_risk in [RiskLevel.HIGH, RiskLevel.VERY_HIGH]:
            strategies.extend([
                "Ensure good drainage to reduce waterlogging",
                "Use disease-resistant varieties",
                "Practice proper spacing for air circulation",
                "Apply preventive fungicides if necessary"
            ])
        
        # Climate risk mitigation
        if climate_risk in [RiskLevel.HIGH, RiskLevel.VERY_HIGH]:
            strategies.extend([
                "Install irrigation system for drought resilience",
                "Use mulching to conserve soil moisture",
                "Consider greenhouse or shade net for temperature control",
                "Adjust planting dates based on weather forecasts"
            ])
        
        # Market risk mitigation
        if market_risk in [RiskLevel.HIGH, RiskLevel.VERY_HIGH]:
            strategies.extend([
                "Secure buyer contracts before planting",
                "Diversify crops to spread market risk",
                "Join farmer cooperatives for better market access",
                "Consider value addition (processing, packaging)"
            ])
        
        return strategies


class SeasonalPlanner:
    """
    Plan seasonal crop activities.
    """
    
    def __init__(self):
        """Initialize seasonal planner."""
        logger.info("Seasonal Planner initialized")
    
    def create_seasonal_calendar(
        self,
        crops: List[str],
        location: Dict[str, Any]
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Create seasonal planting calendar.
        
        Args:
            crops: List of crops to plan for
            location: Location information
            
        Returns:
            Calendar with activities per month
        """
        from app.ml.crop_recommendation import CROP_DATABASE
        
        calendar = {month: [] for month in [
            "January", "February", "March", "April", "May", "June",
            "July", "August", "September", "October", "November", "December"
        ]}
        
        # Kenyan seasons
        long_rains = ["March", "April", "May"]
        short_rains = ["October", "November"]
        
        for crop in crops:
            if crop not in CROP_DATABASE:
                continue
            
            crop_info = CROP_DATABASE[crop]
            suitable_seasons = crop_info["season"]
            duration_days = crop_info["growth_duration"]
            
            # Long rains planting
            if "long_rains" in suitable_seasons or "all_year" in suitable_seasons:
                calendar["March"].append({
                    "activity": "planting",
                    "crop": crop,
                    "notes": f"Start of long rains season - optimal for {crop}"
                })
                
                # Calculate harvest month
                harvest_month_offset = int(duration_days / 30) + 2  # 2 = March (0-indexed would be better)
                harvest_months = ["January", "February", "March", "April", "May", "June",
                                "July", "August", "September", "October", "November", "December"]
                harvest_month = harvest_months[harvest_month_offset % 12]
                
                calendar[harvest_month].append({
                    "activity": "harvest",
                    "crop": crop,
                    "notes": f"Expected harvest after ~{duration_days} days"
                })
            
            # Short rains planting
            if "short_rains" in suitable_seasons or "all_year" in suitable_seasons:
                calendar["October"].append({
                    "activity": "planting",
                    "crop": crop,
                    "notes": f"Start of short rains season - suitable for {crop}"
                })
        
        return calendar
