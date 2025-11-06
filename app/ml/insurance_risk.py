"""
Crop Insurance and Risk Management Module

This module provides intelligent crop insurance recommendations:
- Insurance need assessment
- Premium calculation
- Coverage optimization
- Claim likelihood prediction
- Weather-indexed insurance
- Yield-based insurance
- Loss estimation and mitigation
- Risk transfer strategies
"""

import numpy as np
import pandas as pd
from typing import Dict, Any, List, Optional, Tuple, Union
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class InsuranceType(Enum):
    """Types of crop insurance."""
    MULTI_PERIL = "multi_peril"
    NAMED_PERIL = "named_peril"
    WEATHER_INDEX = "weather_index"
    YIELD_BASED = "yield_based"
    REVENUE = "revenue"
    AREA_YIELD = "area_yield"


class RiskLevel(Enum):
    """Farm risk levels."""
    VERY_LOW = "very_low"
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    VERY_HIGH = "very_high"
    EXTREME = "extreme"


class ClaimLikelihood(Enum):
    """Claim probability levels."""
    VERY_UNLIKELY = "very_unlikely"
    UNLIKELY = "unlikely"
    POSSIBLE = "possible"
    LIKELY = "likely"
    VERY_LIKELY = "very_likely"


class InsuranceRecommendation(Enum):
    """Insurance recommendations."""
    NOT_NEEDED = "not_needed"
    OPTIONAL = "optional"
    RECOMMENDED = "recommended"
    HIGHLY_RECOMMENDED = "highly_recommended"
    ESSENTIAL = "essential"


@dataclass
class InsuranceProduct:
    """
    Insurance product details.
    
    Attributes:
        product_name: Product name
        insurance_type: Type of insurance
        covered_perils: List of covered perils
        coverage_level_pct: Coverage level percentage
        base_premium_rate: Base premium rate
        deductible_pct: Deductible percentage
        maximum_payout: Maximum payout amount
        minimum_area_ha: Minimum insurable area
        crops_covered: Eligible crops
        features: Product features
    """
    product_name: str
    insurance_type: InsuranceType
    covered_perils: List[str]
    coverage_level_pct: float
    base_premium_rate: float
    deductible_pct: float
    maximum_payout: float
    minimum_area_ha: float
    crops_covered: List[str]
    features: List[str]


@dataclass
class RiskAssessment:
    """
    Farm risk assessment.
    
    Attributes:
        overall_risk: Overall risk level
        risk_score: Numeric risk score
        weather_risk: Weather-related risk
        pest_disease_risk: Pest and disease risk
        market_risk: Market price risk
        financial_risk: Financial risk
        operational_risk: Operational risk
        risk_factors: Identified risk factors
        high_risk_periods: High-risk time periods
        mitigation_strategies: Risk mitigation strategies
    """
    overall_risk: RiskLevel
    risk_score: float
    weather_risk: float
    pest_disease_risk: float
    market_risk: float
    financial_risk: float
    operational_risk: float
    risk_factors: List[str]
    high_risk_periods: List[Tuple[str, str]]
    mitigation_strategies: List[str]


@dataclass
class InsuranceRecommendationResult:
    """
    Insurance recommendation result.
    
    Attributes:
        recommendation: Overall recommendation
        recommended_products: Recommended insurance products
        estimated_premium: Estimated annual premium
        coverage_amount: Recommended coverage amount
        cost_benefit_ratio: Cost-benefit analysis
        claim_probability: Probability of claim
        expected_payout: Expected payout amount
        net_benefit: Net expected benefit
        reasoning: Recommendation reasoning
        alternatives: Alternative options
    """
    recommendation: InsuranceRecommendation
    recommended_products: List[InsuranceProduct]
    estimated_premium: float
    coverage_amount: float
    cost_benefit_ratio: float
    claim_probability: float
    expected_payout: float
    net_benefit: float
    reasoning: List[str]
    alternatives: List[str]


@dataclass
class ClaimPrediction:
    """
    Claim prediction analysis.
    
    Attributes:
        likelihood: Claim likelihood level
        probability: Numeric probability
        expected_claim_amount: Expected claim amount
        trigger_conditions: Likely trigger conditions
        historical_pattern: Historical claim pattern
        confidence: Prediction confidence
        factors: Contributing factors
        prevention_measures: Preventive measures
    """
    likelihood: ClaimLikelihood
    probability: float
    expected_claim_amount: float
    trigger_conditions: List[str]
    historical_pattern: str
    confidence: float
    factors: List[Tuple[str, float]]
    prevention_measures: List[str]


class InsuranceProductCatalog:
    """
    Catalog of available insurance products.
    """
    
    def __init__(self):
        """Initialize insurance product catalog."""
        self.products = self._initialize_products()
        logger.info("Insurance Product Catalog initialized")
    
    def _initialize_products(self) -> List[InsuranceProduct]:
        """Initialize insurance products."""
        return [
            InsuranceProduct(
                product_name="Comprehensive Farm Protection",
                insurance_type=InsuranceType.MULTI_PERIL,
                covered_perils=[
                    "drought", "flood", "hail", "frost", "fire",
                    "pests", "diseases", "wind damage"
                ],
                coverage_level_pct=80,
                base_premium_rate=0.05,
                deductible_pct=10,
                maximum_payout=5000000,
                minimum_area_ha=0.5,
                crops_covered=["all"],
                features=[
                    "Covers multiple perils",
                    "Flexible coverage levels",
                    "Farm visit assessment",
                    "Claims within 30 days"
                ]
            ),
            InsuranceProduct(
                product_name="Weather Smart Insurance",
                insurance_type=InsuranceType.WEATHER_INDEX,
                covered_perils=["drought", "excess_rainfall", "extreme_temperature"],
                coverage_level_pct=70,
                base_premium_rate=0.03,
                deductible_pct=0,
                maximum_payout=3000000,
                minimum_area_ha=1.0,
                crops_covered=["maize", "wheat", "beans", "potatoes"],
                features=[
                    "No farm visits required",
                    "Automatic payouts",
                    "Based on weather station data",
                    "Fast claim processing"
                ]
            ),
            InsuranceProduct(
                product_name="Yield Protection Plus",
                insurance_type=InsuranceType.YIELD_BASED,
                covered_perils=["yield_loss"],
                coverage_level_pct=75,
                base_premium_rate=0.04,
                deductible_pct=15,
                maximum_payout=4000000,
                minimum_area_ha=1.0,
                crops_covered=["maize", "wheat", "rice", "beans", "potatoes"],
                features=[
                    "Protects against yield loss",
                    "Covers all causes of loss",
                    "Based on historical yields",
                    "Flexible coverage levels (50-85%)"
                ]
            ),
            InsuranceProduct(
                product_name="Drought Shield",
                insurance_type=InsuranceType.NAMED_PERIL,
                covered_perils=["drought"],
                coverage_level_pct=65,
                base_premium_rate=0.025,
                deductible_pct=5,
                maximum_payout=2000000,
                minimum_area_ha=0.5,
                crops_covered=["maize", "beans", "sorghum", "millet"],
                features=[
                    "Specialized drought coverage",
                    "Low premium rates",
                    "Suitable for arid regions",
                    "Government subsidy available"
                ]
            ),
            InsuranceProduct(
                product_name="Premium Revenue Insurance",
                insurance_type=InsuranceType.REVENUE,
                covered_perils=["price_decline", "yield_loss"],
                coverage_level_pct=85,
                base_premium_rate=0.06,
                deductible_pct=10,
                maximum_payout=10000000,
                minimum_area_ha=5.0,
                crops_covered=["maize", "wheat", "coffee", "tea", "horticultural"],
                features=[
                    "Protects revenue not just yield",
                    "Covers price volatility",
                    "Higher coverage levels",
                    "Suitable for commercial farms"
                ]
            ),
            InsuranceProduct(
                product_name="Area Yield Index",
                insurance_type=InsuranceType.AREA_YIELD,
                covered_perils=["area_yield_loss"],
                coverage_level_pct=70,
                base_premium_rate=0.035,
                deductible_pct=0,
                maximum_payout=2500000,
                minimum_area_ha=2.0,
                crops_covered=["maize", "wheat", "rice"],
                features=[
                    "Based on area average yields",
                    "No individual farm assessment",
                    "Lower administrative costs",
                    "Suitable for smallholders"
                ]
            )
        ]
    
    def get_products_for_crop(self, crop: str) -> List[InsuranceProduct]:
        """Get insurance products available for a crop."""
        eligible_products = []
        for product in self.products:
            if "all" in product.crops_covered or crop in product.crops_covered:
                eligible_products.append(product)
        return eligible_products
    
    def get_product_by_type(self, insurance_type: InsuranceType) -> List[InsuranceProduct]:
        """Get products by insurance type."""
        return [p for p in self.products if p.insurance_type == insurance_type]


class FarmRiskAssessor:
    """
    Assess farm-level risks.
    """
    
    def __init__(self):
        """Initialize farm risk assessor."""
        logger.info("Farm Risk Assessor initialized")
    
    def assess_farm_risk(
        self,
        location: Dict[str, Any],
        crops: List[Dict[str, Any]],
        historical_data: Dict[str, Any],
        financial_data: Dict[str, float],
        current_season: Dict[str, Any]
    ) -> RiskAssessment:
        """
        Assess overall farm risk.
        
        Args:
            location: Farm location details
            crops: Crops being grown
            historical_data: Historical farm data
            financial_data: Financial information
            current_season: Current season data
            
        Returns:
            Risk assessment
        """
        logger.info("Assessing farm risk")
        
        # Calculate individual risk components
        weather_risk = self._assess_weather_risk(location, current_season)
        pest_disease_risk = self._assess_pest_disease_risk(crops, location)
        market_risk = self._assess_market_risk(crops, financial_data)
        financial_risk = self._assess_financial_risk(financial_data)
        operational_risk = self._assess_operational_risk(
            historical_data,
            crops
        )
        
        # Calculate overall risk score
        risk_score = (
            weather_risk * 0.30 +
            pest_disease_risk * 0.25 +
            market_risk * 0.20 +
            financial_risk * 0.15 +
            operational_risk * 0.10
        ) * 100
        
        # Classify overall risk
        overall_risk = self._classify_risk(risk_score)
        
        # Identify risk factors
        risk_factors = self._identify_risk_factors(
            weather_risk, pest_disease_risk, market_risk,
            financial_risk, operational_risk
        )
        
        # Identify high-risk periods
        high_risk_periods = self._identify_high_risk_periods(
            crops, location
        )
        
        # Generate mitigation strategies
        mitigation = self._generate_mitigation_strategies(
            overall_risk, risk_factors
        )
        
        return RiskAssessment(
            overall_risk=overall_risk,
            risk_score=risk_score,
            weather_risk=weather_risk * 100,
            pest_disease_risk=pest_disease_risk * 100,
            market_risk=market_risk * 100,
            financial_risk=financial_risk * 100,
            operational_risk=operational_risk * 100,
            risk_factors=risk_factors,
            high_risk_periods=high_risk_periods,
            mitigation_strategies=mitigation
        )
    
    def _assess_weather_risk(
        self,
        location: Dict[str, Any],
        season: Dict[str, Any]
    ) -> float:
        """Assess weather-related risk."""
        # Location climate risk
        climate_zone = location.get("climate_zone", "moderate")
        zone_risk = {
            "arid": 0.8,
            "semi_arid": 0.65,
            "moderate": 0.4,
            "humid": 0.5
        }
        climate_risk = zone_risk.get(climate_zone, 0.5)
        
        # Seasonal risk
        rainfall_variability = season.get("rainfall_variability", 0.3)
        temp_extremes = season.get("temperature_extremes", 0.2)
        
        # Historical weather events
        historical_droughts = location.get("drought_frequency", 0.2)
        historical_floods = location.get("flood_frequency", 0.1)
        
        # Combined weather risk
        weather_risk = (
            climate_risk * 0.35 +
            rainfall_variability * 0.25 +
            temp_extremes * 0.20 +
            historical_droughts * 0.12 +
            historical_floods * 0.08
        )
        
        return min(1.0, weather_risk)
    
    def _assess_pest_disease_risk(
        self,
        crops: List[Dict[str, Any]],
        location: Dict[str, Any]
    ) -> float:
        """Assess pest and disease risk."""
        if not crops:
            return 0.3
        
        # Crop susceptibility
        total_susceptibility = 0
        for crop in crops:
            susceptibility = crop.get("disease_susceptibility", 0.5)
            pest_pressure = crop.get("pest_pressure", 0.4)
            total_susceptibility += (susceptibility + pest_pressure) / 2
        
        avg_susceptibility = total_susceptibility / len(crops)
        
        # Regional pest pressure
        regional_pressure = location.get("pest_disease_pressure", 0.5)
        
        # Control practices
        control_effectiveness = 0.7  # Assume moderate control
        
        # Combined risk
        pest_disease_risk = (
            avg_susceptibility * 0.5 +
            regional_pressure * 0.3
        ) * (1 - control_effectiveness * 0.2)
        
        return min(1.0, pest_disease_risk)
    
    def _assess_market_risk(
        self,
        crops: List[Dict[str, Any]],
        financial: Dict[str, float]
    ) -> float:
        """Assess market and price risk."""
        if not crops:
            return 0.3
        
        # Price volatility
        total_volatility = 0
        for crop in crops:
            price_volatility = crop.get("price_volatility", 0.3)
            market_access = crop.get("market_access_score", 0.7)
            crop_risk = price_volatility * (1 - market_access * 0.3)
            total_volatility += crop_risk
        
        avg_volatility = total_volatility / len(crops)
        
        # Diversification
        crop_diversity = min(len(crops) / 5, 1.0)  # Max benefit at 5 crops
        diversification_benefit = crop_diversity * 0.3
        
        # Market risk
        market_risk = avg_volatility * (1 - diversification_benefit)
        
        return min(1.0, market_risk)
    
    def _assess_financial_risk(self, financial: Dict[str, float]) -> float:
        """Assess financial risk."""
        # Debt-to-asset ratio
        debt = financial.get("total_debt", 0)
        assets = financial.get("total_assets", 1000000)
        debt_ratio = debt / assets if assets > 0 else 0
        
        # Liquidity
        current_assets = financial.get("current_assets", 500000)
        current_liabilities = financial.get("current_liabilities", 300000)
        liquidity_ratio = current_assets / current_liabilities if current_liabilities > 0 else 2.0
        
        # Income stability
        income_variability = financial.get("income_variability", 0.3)
        
        # Financial risk score
        debt_risk = min(1.0, debt_ratio / 0.7)  # 70% debt ratio is high risk
        liquidity_risk = max(0, 1 - liquidity_ratio / 1.5)  # 1.5 is healthy
        
        financial_risk = (
            debt_risk * 0.4 +
            liquidity_risk * 0.35 +
            income_variability * 0.25
        )
        
        return min(1.0, financial_risk)
    
    def _assess_operational_risk(
        self,
        historical: Dict[str, Any],
        crops: List[Dict[str, Any]]
    ) -> float:
        """Assess operational risk."""
        # Management experience
        experience_years = historical.get("farming_experience_years", 5)
        experience_factor = max(0.2, 1 - (experience_years / 20))
        
        # Technology adoption
        tech_adoption = historical.get("technology_adoption_score", 0.5)
        
        # Labor availability
        labor_reliability = historical.get("labor_reliability", 0.7)
        
        # Equipment condition
        equipment_age = historical.get("equipment_age_years", 5)
        equipment_factor = min(1.0, equipment_age / 15)
        
        # Operational risk
        operational_risk = (
            experience_factor * 0.35 +
            (1 - tech_adoption) * 0.25 +
            (1 - labor_reliability) * 0.25 +
            equipment_factor * 0.15
        )
        
        return min(1.0, operational_risk)
    
    def _classify_risk(self, score: float) -> RiskLevel:
        """Classify risk level from score."""
        if score < 20:
            return RiskLevel.VERY_LOW
        elif score < 35:
            return RiskLevel.LOW
        elif score < 50:
            return RiskLevel.MODERATE
        elif score < 65:
            return RiskLevel.HIGH
        elif score < 80:
            return RiskLevel.VERY_HIGH
        else:
            return RiskLevel.EXTREME
    
    def _identify_risk_factors(
        self,
        weather: float,
        pest: float,
        market: float,
        financial: float,
        operational: float
    ) -> List[str]:
        """Identify specific risk factors."""
        factors = []
        
        if weather > 0.6:
            factors.append("High weather variability and climate risk")
        if pest > 0.5:
            factors.append("Elevated pest and disease pressure")
        if market > 0.5:
            factors.append("Significant market price volatility")
        if financial > 0.6:
            factors.append("Financial stress and liquidity concerns")
        if operational > 0.5:
            factors.append("Operational challenges and capacity constraints")
        
        return factors
    
    def _identify_high_risk_periods(
        self,
        crops: List[Dict[str, Any]],
        location: Dict[str, Any]
    ) -> List[Tuple[str, str]]:
        """Identify high-risk time periods."""
        periods = []
        
        # Dry season
        if location.get("has_dry_season", True):
            periods.append(("June-September", "Drought risk during dry season"))
        
        # Planting season
        periods.append(("March-April", "Planting season weather uncertainty"))
        
        # Critical growth stages
        periods.append(("Flowering", "Critical stage vulnerable to stress"))
        
        return periods
    
    def _generate_mitigation_strategies(
        self,
        risk_level: RiskLevel,
        factors: List[str]
    ) -> List[str]:
        """Generate risk mitigation strategies."""
        strategies = []
        
        if risk_level in [RiskLevel.HIGH, RiskLevel.VERY_HIGH, RiskLevel.EXTREME]:
            strategies.append("Crop insurance essential for risk transfer")
        
        strategies.extend([
            "Diversify crop portfolio to reduce concentration risk",
            "Adopt improved varieties with stress tolerance",
            "Implement water conservation and irrigation",
            "Maintain emergency fund for unexpected expenses",
            "Establish relationships with multiple buyers",
            "Invest in soil health for resilience",
            "Use weather forecasting for decision making"
        ])
        
        if "Financial stress" in str(factors):
            strategies.append("Focus on debt reduction and cash flow management")
        
        if "pest and disease" in str(factors):
            strategies.append("Strengthen integrated pest management practices")
        
        return strategies


class InsuranceAdvisor:
    """
    Provide insurance recommendations.
    """
    
    def __init__(self):
        """Initialize insurance advisor."""
        self.catalog = InsuranceProductCatalog()
        self.risk_assessor = FarmRiskAssessor()
        logger.info("Insurance Advisor initialized")
    
    def recommend_insurance(
        self,
        crop: str,
        farm_area_ha: float,
        expected_yield_kg: float,
        crop_value_per_kg: float,
        location: Dict[str, Any],
        historical_data: Dict[str, Any],
        financial_data: Dict[str, float]
    ) -> InsuranceRecommendationResult:
        """
        Recommend insurance products.
        
        Args:
            crop: Crop name
            farm_area_ha: Farm area in hectares
            expected_yield_kg: Expected yield
            crop_value_per_kg: Crop value per kg
            location: Location details
            historical_data: Historical farm data
            financial_data: Financial information
            
        Returns:
            Insurance recommendation
        """
        logger.info(f"Generating insurance recommendation for {crop}")
        
        # Assess farm risk
        crops_data = [{
            "crop": crop,
            "area_ha": farm_area_ha,
            "disease_susceptibility": 0.5,
            "pest_pressure": 0.5,
            "price_volatility": 0.3,
            "market_access_score": 0.7
        }]
        
        risk_assessment = self.risk_assessor.assess_farm_risk(
            location, crops_data, historical_data,
            financial_data, {}
        )
        
        # Calculate crop value
        total_crop_value = expected_yield_kg * crop_value_per_kg
        
        # Get eligible products
        eligible_products = self.catalog.get_products_for_crop(crop)
        
        # Filter by farm size
        suitable_products = [
            p for p in eligible_products
            if farm_area_ha >= p.minimum_area_ha
        ]
        
        # Rank products
        recommended_products = self._rank_products(
            suitable_products,
            risk_assessment,
            total_crop_value
        )
        
        # Calculate premium
        if recommended_products:
            best_product = recommended_products[0]
            premium = self._calculate_premium(
                best_product,
                total_crop_value,
                risk_assessment
            )
            coverage = total_crop_value * (best_product.coverage_level_pct / 100)
        else:
            premium = 0
            coverage = 0
        
        # Predict claim probability
        claim_prob = self._estimate_claim_probability(risk_assessment)
        
        # Expected payout
        expected_payout = coverage * claim_prob * 0.7  # Average claim is 70% of coverage
        
        # Net benefit
        net_benefit = expected_payout - premium
        
        # Cost-benefit ratio
        if premium > 0:
            cost_benefit = expected_payout / premium
        else:
            cost_benefit = 0
        
        # Overall recommendation
        recommendation = self._determine_recommendation(
            risk_assessment.overall_risk,
            cost_benefit,
            financial_data.get("total_assets", 0),
            total_crop_value
        )
        
        # Reasoning
        reasoning = self._generate_reasoning(
            risk_assessment,
            claim_prob,
            cost_benefit
        )
        
        # Alternatives
        alternatives = self._suggest_alternatives(
            recommendation,
            recommended_products
        )
        
        return InsuranceRecommendationResult(
            recommendation=recommendation,
            recommended_products=recommended_products[:3],  # Top 3
            estimated_premium=premium,
            coverage_amount=coverage,
            cost_benefit_ratio=cost_benefit,
            claim_probability=claim_prob,
            expected_payout=expected_payout,
            net_benefit=net_benefit,
            reasoning=reasoning,
            alternatives=alternatives
        )
    
    def _rank_products(
        self,
        products: List[InsuranceProduct],
        risk: RiskAssessment,
        crop_value: float
    ) -> List[InsuranceProduct]:
        """Rank insurance products by suitability."""
        scored_products = []
        
        for product in products:
            score = 0
            
            # High risk needs comprehensive coverage
            if risk.overall_risk in [RiskLevel.HIGH, RiskLevel.VERY_HIGH]:
                if product.insurance_type == InsuranceType.MULTI_PERIL:
                    score += 30
                elif product.insurance_type == InsuranceType.REVENUE:
                    score += 25
            
            # Weather risk needs weather index
            if risk.weather_risk > 60:
                if product.insurance_type == InsuranceType.WEATHER_INDEX:
                    score += 20
            
            # Coverage level
            score += product.coverage_level_pct / 5
            
            # Number of perils
            score += len(product.covered_perils) * 2
            
            scored_products.append((score, product))
        
        # Sort by score
        scored_products.sort(reverse=True, key=lambda x: x[0])
        
        return [p[1] for p in scored_products]
    
    def _calculate_premium(
        self,
        product: InsuranceProduct,
        insured_value: float,
        risk: RiskAssessment
    ) -> float:
        """Calculate insurance premium."""
        # Base premium
        base_premium = insured_value * product.base_premium_rate
        
        # Risk adjustment
        risk_multiplier = 1.0
        if risk.overall_risk == RiskLevel.VERY_LOW:
            risk_multiplier = 0.7
        elif risk.overall_risk == RiskLevel.LOW:
            risk_multiplier = 0.85
        elif risk.overall_risk == RiskLevel.MODERATE:
            risk_multiplier = 1.0
        elif risk.overall_risk == RiskLevel.HIGH:
            risk_multiplier = 1.3
        elif risk.overall_risk == RiskLevel.VERY_HIGH:
            risk_multiplier = 1.6
        else:  # EXTREME
            risk_multiplier = 2.0
        
        # Adjusted premium
        premium = base_premium * risk_multiplier
        
        return premium
    
    def _estimate_claim_probability(self, risk: RiskAssessment) -> float:
        """Estimate probability of insurance claim."""
        # Convert risk score to claim probability
        base_prob = risk.risk_score / 100
        
        # Adjust for risk level
        if risk.overall_risk == RiskLevel.VERY_LOW:
            claim_prob = base_prob * 0.5
        elif risk.overall_risk == RiskLevel.LOW:
            claim_prob = base_prob * 0.7
        elif risk.overall_risk == RiskLevel.MODERATE:
            claim_prob = base_prob * 0.9
        elif risk.overall_risk == RiskLevel.HIGH:
            claim_prob = base_prob * 1.1
        elif risk.overall_risk == RiskLevel.VERY_HIGH:
            claim_prob = base_prob * 1.3
        else:  # EXTREME
            claim_prob = base_prob * 1.5
        
        return min(0.95, claim_prob)
    
    def _determine_recommendation(
        self,
        risk: RiskLevel,
        cost_benefit: float,
        assets: float,
        crop_value: float
    ) -> InsuranceRecommendation:
        """Determine overall insurance recommendation."""
        # Risk-based recommendation
        if risk in [RiskLevel.EXTREME, RiskLevel.VERY_HIGH]:
            return InsuranceRecommendation.ESSENTIAL
        elif risk == RiskLevel.HIGH:
            return InsuranceRecommendation.HIGHLY_RECOMMENDED
        elif risk == RiskLevel.MODERATE:
            if cost_benefit > 1.0:
                return InsuranceRecommendation.RECOMMENDED
            else:
                return InsuranceRecommendation.OPTIONAL
        else:  # LOW or VERY_LOW
            if cost_benefit > 1.5:
                return InsuranceRecommendation.RECOMMENDED
            else:
                return InsuranceRecommendation.OPTIONAL
    
    def _generate_reasoning(
        self,
        risk: RiskAssessment,
        claim_prob: float,
        cost_benefit: float
    ) -> List[str]:
        """Generate recommendation reasoning."""
        reasoning = []
        
        reasoning.append(
            f"Farm risk assessment: {risk.overall_risk.value} "
            f"(score: {risk.risk_score:.1f}/100)"
        )
        
        reasoning.append(
            f"Estimated claim probability: {claim_prob*100:.1f}%"
        )
        
        if cost_benefit > 1.0:
            reasoning.append(
                f"Positive cost-benefit ratio ({cost_benefit:.2f}): "
                f"Expected payout exceeds premium"
            )
        else:
            reasoning.append(
                f"Cost-benefit ratio: {cost_benefit:.2f}"
            )
        
        # Key risks
        if risk.weather_risk > 60:
            reasoning.append("High weather risk identified")
        
        if risk.pest_disease_risk > 50:
            reasoning.append("Elevated pest and disease risk")
        
        if risk.market_risk > 50:
            reasoning.append("Significant market volatility")
        
        return reasoning
    
    def _suggest_alternatives(
        self,
        recommendation: InsuranceRecommendation,
        products: List[InsuranceProduct]
    ) -> List[str]:
        """Suggest alternative risk management options."""
        alternatives = []
        
        if recommendation in [InsuranceRecommendation.NOT_NEEDED, InsuranceRecommendation.OPTIONAL]:
            alternatives.extend([
                "Self-insure through emergency savings fund",
                "Focus on risk prevention and mitigation",
                "Diversify crops to spread risk"
            ])
        
        alternatives.extend([
            "Contract farming for price stability",
            "Forward contracts with buyers",
            "Savings and credit cooperative (SACCO) membership",
            "Government disaster relief programs"
        ])
        
        if len(products) > 3:
            alternatives.append(
                f"Consider {len(products) - 3} additional insurance products available"
            )
        
        return alternatives


class ClaimPredictor:
    """
    Predict insurance claim likelihood.
    """
    
    def __init__(self):
        """Initialize claim predictor."""
        logger.info("Claim Predictor initialized")
    
    def predict_claim(
        self,
        insured_crop: str,
        coverage_type: InsuranceType,
        weather_forecast: Dict[str, Any],
        current_conditions: Dict[str, Any],
        historical_claims: List[Dict[str, Any]]
    ) -> ClaimPrediction:
        """
        Predict likelihood of insurance claim.
        
        Args:
            insured_crop: Insured crop
            coverage_type: Type of insurance coverage
            weather_forecast: Weather forecast
            current_conditions: Current farm conditions
            historical_claims: Historical claim data
            
        Returns:
            Claim prediction
        """
        logger.info(f"Predicting claim likelihood for {insured_crop}")
        
        # Calculate claim probability factors
        factors = self._calculate_claim_factors(
            insured_crop,
            coverage_type,
            weather_forecast,
            current_conditions
        )
        
        # Overall probability
        probability = sum(score for _, score in factors) / len(factors) if factors else 0.2
        
        # Classify likelihood
        likelihood = self._classify_likelihood(probability)
        
        # Identify trigger conditions
        triggers = self._identify_triggers(
            coverage_type,
            weather_forecast,
            current_conditions
        )
        
        # Analyze historical pattern
        pattern = self._analyze_historical_pattern(historical_claims)
        
        # Calculate confidence
        confidence = self._calculate_confidence(
            len(historical_claims),
            weather_forecast.get("forecast_confidence", 0.7)
        )
        
        # Estimate claim amount
        expected_claim = self._estimate_claim_amount(
            probability,
            current_conditions.get("insured_value", 0),
            coverage_type
        )
        
        # Prevention measures
        prevention = self._suggest_prevention(triggers, factors)
        
        return ClaimPrediction(
            likelihood=likelihood,
            probability=probability,
            expected_claim_amount=expected_claim,
            trigger_conditions=triggers,
            historical_pattern=pattern,
            confidence=confidence,
            factors=factors,
            prevention_measures=prevention
        )
    
    def _calculate_claim_factors(
        self,
        crop: str,
        coverage: InsuranceType,
        weather: Dict[str, Any],
        conditions: Dict[str, Any]
    ) -> List[Tuple[str, float]]:
        """Calculate factors contributing to claim probability."""
        factors = []
        
        # Weather factors
        if coverage in [InsuranceType.WEATHER_INDEX, InsuranceType.MULTI_PERIL]:
            # Drought probability
            rainfall_deficit = weather.get("rainfall_deficit_pct", 0)
            if rainfall_deficit > 30:
                factors.append(("Significant rainfall deficit", 0.7))
            elif rainfall_deficit > 15:
                factors.append(("Moderate rainfall deficit", 0.4))
            
            # Extreme temperatures
            heat_stress_days = weather.get("heat_stress_days", 0)
            if heat_stress_days > 10:
                factors.append(("Excessive heat stress", 0.6))
            
            # Frost risk
            frost_probability = weather.get("frost_probability", 0)
            if frost_probability > 0.3:
                factors.append(("Frost risk", frost_probability))
        
        # Yield factors
        if coverage in [InsuranceType.YIELD_BASED, InsuranceType.MULTI_PERIL]:
            current_health = conditions.get("crop_health_score", 70)
            if current_health < 50:
                factors.append(("Poor crop health", 0.8))
            elif current_health < 70:
                factors.append(("Below average crop health", 0.5))
        
        # Pest/disease
        pest_pressure = conditions.get("pest_pressure", 0.3)
        if pest_pressure > 0.6:
            factors.append(("High pest/disease pressure", pest_pressure))
        
        return factors
    
    def _classify_likelihood(self, probability: float) -> ClaimLikelihood:
        """Classify claim likelihood."""
        if probability < 0.15:
            return ClaimLikelihood.VERY_UNLIKELY
        elif probability < 0.30:
            return ClaimLikelihood.UNLIKELY
        elif probability < 0.50:
            return ClaimLikelihood.POSSIBLE
        elif probability < 0.70:
            return ClaimLikelihood.LIKELY
        else:
            return ClaimLikelihood.VERY_LIKELY
    
    def _identify_triggers(
        self,
        coverage: InsuranceType,
        weather: Dict[str, Any],
        conditions: Dict[str, Any]
    ) -> List[str]:
        """Identify potential claim triggers."""
        triggers = []
        
        if coverage == InsuranceType.WEATHER_INDEX:
            if weather.get("rainfall_deficit_pct", 0) > 40:
                triggers.append("Rainfall below index trigger level")
            if weather.get("heat_stress_days", 0) > 15:
                triggers.append("Excessive heat days above threshold")
        
        if coverage == InsuranceType.YIELD_BASED:
            expected_yield = conditions.get("expected_yield_kg_ha", 0)
            guaranteed_yield = expected_yield * 0.75
            if conditions.get("projected_yield", expected_yield) < guaranteed_yield:
                triggers.append("Projected yield below guaranteed level")
        
        return triggers
    
    def _analyze_historical_pattern(
        self,
        claims: List[Dict[str, Any]]
    ) -> str:
        """Analyze historical claim pattern."""
        if not claims:
            return "No historical claims on record"
        
        recent_claims = [c for c in claims if c.get("years_ago", 10) < 5]
        
        if len(recent_claims) >= 3:
            return "Frequent claims in recent years (high risk pattern)"
        elif len(recent_claims) == 2:
            return "Moderate claim history"
        elif len(recent_claims) == 1:
            return "Single recent claim"
        else:
            return "No recent claims (low risk pattern)"
    
    def _calculate_confidence(
        self,
        historical_records: int,
        forecast_confidence: float
    ) -> float:
        """Calculate prediction confidence."""
        # More historical data increases confidence
        data_confidence = min(1.0, historical_records / 10)
        
        # Combined confidence
        confidence = (data_confidence * 0.4 + forecast_confidence * 0.6)
        
        return confidence
    
    def _estimate_claim_amount(
        self,
        probability: float,
        insured_value: float,
        coverage: InsuranceType
    ) -> float:
        """Estimate expected claim amount."""
        if probability < 0.2:
            return 0
        
        # Average claim severity
        severity_factors = {
            InsuranceType.MULTI_PERIL: 0.6,
            InsuranceType.WEATHER_INDEX: 0.5,
            InsuranceType.YIELD_BASED: 0.65,
            InsuranceType.NAMED_PERIL: 0.7,
            InsuranceType.REVENUE: 0.6,
            InsuranceType.AREA_YIELD: 0.55
        }
        
        severity = severity_factors.get(coverage, 0.6)
        
        expected_claim = insured_value * probability * severity
        
        return expected_claim
    
    def _suggest_prevention(
        self,
        triggers: List[str],
        factors: List[Tuple[str, float]]
    ) -> List[str]:
        """Suggest claim prevention measures."""
        measures = []
        
        if any("rainfall" in t.lower() for t in triggers):
            measures.extend([
                "Implement supplementary irrigation if available",
                "Apply mulch to conserve soil moisture",
                "Consider drought-tolerant crop varieties"
            ])
        
        if any("heat" in t.lower() for t in triggers):
            measures.extend([
                "Increase irrigation during heat waves",
                "Provide temporary shade for high-value crops"
            ])
        
        if any("pest" in str(factors).lower()):
            measures.append("Intensify pest and disease monitoring and control")
        
        if any("yield" in t.lower() for t in triggers):
            measures.extend([
                "Focus on crop health improvement",
                "Ensure adequate nutrition",
                "Address any visible stress factors"
            ])
        
        measures.append("Maintain detailed records for potential claim documentation")
        
        return measures
