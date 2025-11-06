"""
� AgroPulse - Tier 4: Greenhouse Grower Community & Financial AI

This module implements AI services for greenhouse grower cooperatives,
fresh produce market intelligence, and quality dispute resolution.

Core Horticultural AI:
7. Grower Financial Health AI - Dynamic loan eligibility for greenhouse investments
8. Fresh Produce Market AI - Demand forecasting and price optimization
9. Quality Dispute Adjudicator - CV-based produce quality evidence analysis
10. Cooperative Buying AI - Group purchases of seeds, nutrients, growing media

Specialized for: Greenhouse grower cooperatives, hydroponic farm networks,
                 vertical farm consortiums, organic produce cooperatives

Author: AgroPulse Horticulture AI Team
Date: November 3, 2025
"""

import numpy as np
from typing import Dict, List, Tuple, Optional, Any
from datetime import datetime, timedelta
import json
from enum import Enum


class RiskCategory(str, Enum):
    """Risk categories for loan assessment."""
    VERY_LOW = "very_low"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    VERY_HIGH = "very_high"


class GrowerFinancialHealthAI:
    """
    AI model for greenhouse grower financial health and investment risk scoring.
    
    Evaluates greenhouse operation financial viability by analyzing:
    - Cooperative savings ledger (grower savings consistency)
    - Verified greenhouse assets (facility size, equipment, hydroponic systems)
    - AI yield predictions (production forecasts for greenhouse crops)
    - Payment history (past loan/input purchase repayments)
    - Fresh produce sales data (market performance)
    
    Outputs:
    - Dynamic risk score (0-100) for greenhouse investments
    - Recommended loan amount for expansions/equipment
    - Interest rate recommendation
    - Personalized financial guidance for growers
    
    Specialized for: Greenhouse infrastructure loans, hydroponic system financing,
                     climate control equipment purchases, expansion capital
    """
    
    def __init__(self):
        """Initialize greenhouse grower financial health AI model."""
        self.risk_weights = {
            "savings_consistency": 0.35,      # Consistent cooperative contributions
            "greenhouse_assets": 0.25,        # Facility value & equipment
            "production_forecast": 0.25,      # Expected crop yields
            "repayment_history": 0.15         # Past financial reliability
        }
        
    def calculate_risk_score(
        self,
        grower_id: str,
        savings_data: Dict,
        greenhouse_assets: Dict,
        production_forecast: Dict,
        repayment_history: Dict
    ) -> Dict:
        """
        Calculate comprehensive risk score for greenhouse investment loans.
        
        Args:
            grower_id: Cooperative grower identifier
            savings_data: Cooperative savings account history
            greenhouse_assets: Verified assets (greenhouse facility, hydroponic systems, climate control)
            production_forecast: AI-predicted yields for greenhouse crops
            repayment_history: Past loan/purchase repayment record
            
        Returns:
            Risk assessment with greenhouse investment recommendations
        """
        print(f"\n🧮 Calculating Risk Score for {member_id}...")
        
        # Component 1: Savings Consistency Score
        savings_score = self._calculate_savings_score(savings_data)
        print(f"   💰 Savings Score: {savings_score:.1f}/100")
        
        # Component 2: Farm Assets Score
        assets_score = self._calculate_assets_score(farm_assets)
        print(f"   🏡 Assets Score: {assets_score:.1f}/100")
        
        # Component 3: Yield Prediction Score
        yield_score = self._calculate_yield_score(yield_prediction)
        print(f"   🌾 Yield Score: {yield_score:.1f}/100")
        
        # Component 4: Repayment History Score
        repayment_score = self._calculate_repayment_score(repayment_history)
        print(f"   ✅ Repayment Score: {repayment_score:.1f}/100")
        
        # Weighted composite score
        total_score = (
            savings_score * self.risk_weights["savings_consistency"] +
            assets_score * self.risk_weights["farm_assets"] +
            yield_score * self.risk_weights["yield_prediction"] +
            repayment_score * self.risk_weights["repayment_history"]
        )
        
        print(f"   📊 Total Risk Score: {total_score:.1f}/100")
        
        # Determine risk category
        risk_category = self._categorize_risk(total_score)
        
        # Generate loan recommendation
        loan_recommendation = self._recommend_loan(
            total_score, risk_category, savings_data, yield_prediction
        )
        
        # Generate behavioral nudges
        nudges = self._generate_nudges(
            savings_score, assets_score, yield_score, repayment_score
        )
        
        return {
            "member_id": member_id,
            "risk_score": round(total_score, 1),
            "risk_category": risk_category.value,
            "component_scores": {
                "savings_consistency": round(savings_score, 1),
                "farm_assets": round(assets_score, 1),
                "yield_prediction": round(yield_score, 1),
                "repayment_history": round(repayment_score, 1)
            },
            "loan_recommendation": loan_recommendation,
            "behavioral_nudges": nudges,
            "calculation_timestamp": datetime.now().isoformat()
        }
    
    def _calculate_savings_score(self, savings_data: Dict) -> float:
        """
        Calculate savings consistency score.
        
        Factors:
        - Regularity of contributions
        - Average balance
        - Growth trend
        - Withdrawal patterns
        """
        monthly_contributions = savings_data.get("monthly_contributions", [])
        current_balance = savings_data.get("current_balance_ksh", 0)
        
        if not monthly_contributions:
            return 0.0
        
        # Consistency score (regular contributions)
        expected_months = len(monthly_contributions)
        actual_contributions = sum(1 for c in monthly_contributions if c > 0)
        consistency = (actual_contributions / expected_months) * 40  # Max 40 points
        
        # Balance score
        # Benchmark: KES 10,000 = 30 points
        balance_score = min((current_balance / 10000) * 30, 30)
        
        # Growth trend score
        if len(monthly_contributions) >= 2:
            trend = np.polyfit(
                range(len(monthly_contributions)),
                monthly_contributions,
                1
            )[0]
            growth_score = min((trend / 100) * 30, 30)  # Max 30 points
        else:
            growth_score = 0
        
        total = consistency + balance_score + growth_score
        return min(total, 100)
    
    def _calculate_assets_score(self, farm_assets: Dict) -> float:
        """
        Calculate farm assets score based on verified assets.
        
        Factors:
        - Land ownership (size and documentation)
        - Equipment value
        - Livestock count
        - Infrastructure (irrigation, greenhouse)
        """
        land_acres = farm_assets.get("land_acres", 0)
        land_owned = farm_assets.get("land_owned", False)
        equipment_value = farm_assets.get("equipment_value_ksh", 0)
        livestock_value = farm_assets.get("livestock_value_ksh", 0)
        infrastructure_value = farm_assets.get("infrastructure_value_ksh", 0)
        
        # Land score (max 40 points)
        land_score = min(land_acres * 10, 30)  # 3+ acres = 30 points
        if land_owned:
            land_score += 10  # Bonus for ownership
        
        # Equipment score (max 20 points)
        equipment_score = min((equipment_value / 20000) * 20, 20)
        
        # Livestock score (max 20 points)
        livestock_score = min((livestock_value / 30000) * 20, 20)
        
        # Infrastructure score (max 20 points)
        infrastructure_score = min((infrastructure_value / 50000) * 20, 20)
        
        total = land_score + equipment_score + livestock_score + infrastructure_score
        return min(total, 100)
    
    def _calculate_yield_score(self, yield_prediction: Dict) -> float:
        """
        Calculate yield prediction score.
        
        Uses AI-predicted yield for current season to assess ability to repay.
        """
        predicted_yield_kg = yield_prediction.get("predicted_yield_kg", 0)
        predicted_revenue_ksh = yield_prediction.get("predicted_revenue_ksh", 0)
        confidence = yield_prediction.get("confidence", 0.5)
        
        # Revenue score (max 60 points)
        # Benchmark: KES 100,000 revenue = 60 points
        revenue_score = min((predicted_revenue_ksh / 100000) * 60, 60)
        
        # Confidence score (max 40 points)
        confidence_score = confidence * 40
        
        total = revenue_score + confidence_score
        return min(total, 100)
    
    def _calculate_repayment_score(self, repayment_history: Dict) -> float:
        """
        Calculate repayment history score.
        
        Factors:
        - On-time payment rate
        - Default history
        - Total loans repaid
        """
        total_loans = repayment_history.get("total_loans", 0)
        on_time_payments = repayment_history.get("on_time_payments", 0)
        defaults = repayment_history.get("defaults", 0)
        
        if total_loans == 0:
            # New member - neutral score
            return 50.0
        
        # On-time payment rate (max 60 points)
        on_time_rate = on_time_payments / total_loans
        on_time_score = on_time_rate * 60
        
        # Default penalty (max -40 points)
        default_penalty = min(defaults * 20, 40)
        
        # Experience bonus (max 20 points)
        experience_bonus = min(total_loans * 5, 20)
        
        total = on_time_score + experience_bonus - default_penalty
        return max(min(total, 100), 0)
    
    def _categorize_risk(self, risk_score: float) -> RiskCategory:
        """Categorize risk score into risk category."""
        if risk_score >= 85:
            return RiskCategory.VERY_LOW
        elif risk_score >= 70:
            return RiskCategory.LOW
        elif risk_score >= 50:
            return RiskCategory.MEDIUM
        elif risk_score >= 30:
            return RiskCategory.HIGH
        else:
            return RiskCategory.VERY_HIGH
    
    def _recommend_loan(
        self,
        risk_score: float,
        risk_category: RiskCategory,
        savings_data: Dict,
        yield_prediction: Dict
    ) -> Dict:
        """
        Recommend loan amount and terms based on risk score.
        
        Conservative lending rules:
        - Loan ≤ 3x current savings
        - Loan ≤ 30% of predicted revenue
        - Monthly payment ≤ 20% of predicted monthly income
        """
        current_savings = savings_data.get("current_balance_ksh", 0)
        predicted_revenue = yield_prediction.get("predicted_revenue_ksh", 0)
        
        # Maximum loan based on savings
        max_loan_savings = current_savings * 3
        
        # Maximum loan based on yield
        max_loan_yield = predicted_revenue * 0.30
        
        # Take minimum for safety
        max_loan = min(max_loan_savings, max_loan_yield)
        
        # Adjust based on risk category
        risk_multipliers = {
            RiskCategory.VERY_LOW: 1.0,
            RiskCategory.LOW: 0.85,
            RiskCategory.MEDIUM: 0.65,
            RiskCategory.HIGH: 0.40,
            RiskCategory.VERY_HIGH: 0.20
        }
        
        recommended_loan = max_loan * risk_multipliers[risk_category]
        
        # Interest rate based on risk
        interest_rates = {
            RiskCategory.VERY_LOW: 3.0,
            RiskCategory.LOW: 4.5,
            RiskCategory.MEDIUM: 6.0,
            RiskCategory.HIGH: 8.5,
            RiskCategory.VERY_HIGH: 12.0
        }
        
        interest_rate = interest_rates[risk_category]
        
        # Calculate monthly payment (6-month term)
        term_months = 6
        monthly_interest_rate = interest_rate / 100 / 12
        monthly_payment = recommended_loan * (
            monthly_interest_rate * (1 + monthly_interest_rate) ** term_months
        ) / ((1 + monthly_interest_rate) ** term_months - 1)
        
        return {
            "recommended_amount_ksh": round(recommended_loan, 2),
            "interest_rate_percent": interest_rate,
            "term_months": term_months,
            "monthly_payment_ksh": round(monthly_payment, 2),
            "total_repayment_ksh": round(monthly_payment * term_months, 2),
            "approval_speed": "5_seconds",
            "rationale": self._get_recommendation_rationale(
                risk_category, max_loan_savings, max_loan_yield
            )
        }
    
    def _get_recommendation_rationale(
        self,
        risk_category: RiskCategory,
        max_savings: float,
        max_yield: float
    ) -> str:
        """Generate human-readable rationale for recommendation."""
        if risk_category == RiskCategory.VERY_LOW:
            return f"Excellent credit profile. Loan capped at 3x savings (KES {max_savings:.0f}) or 30% predicted revenue (KES {max_yield:.0f})."
        elif risk_category == RiskCategory.LOW:
            return f"Strong credit profile. Loan slightly reduced for safety margin."
        elif risk_category == RiskCategory.MEDIUM:
            return f"Moderate risk. Loan reduced to ensure comfortable repayment."
        elif risk_category == RiskCategory.HIGH:
            return f"Elevated risk. Small starter loan recommended to build credit history."
        else:
            return f"High risk. Minimal loan recommended. Focus on building savings first."
    
    def _generate_nudges(
        self,
        savings_score: float,
        assets_score: float,
        yield_score: float,
        repayment_score: float
    ) -> List[Dict]:
        """
        Generate personalized behavioral nudges for financial coaching.
        
        Nudges encourage positive financial behaviors.
        """
        nudges = []
        
        # Savings nudges
        if savings_score < 50:
            nudges.append({
                "category": "savings",
                "priority": "high",
                "message": "💰 Save KES 500 this week to improve your loan eligibility by 15%",
                "action": "Set up auto-save from M-Pesa",
                "impact": "+15 credit score points"
            })
        elif savings_score < 70:
            nudges.append({
                "category": "savings",
                "priority": "medium",
                "message": "📈 Great progress! Increase monthly savings by KES 200 to unlock larger loans",
                "action": "Review budget and identify savings opportunities",
                "impact": "+10 credit score points"
            })
        
        # Assets nudges
        if assets_score < 40:
            nudges.append({
                "category": "assets",
                "priority": "high",
                "message": "🏡 Register your farm assets with AgroPulse for instant credit boost",
                "action": "Complete asset verification (drone scan + GPS)",
                "impact": "+20 credit score points"
            })
        
        # Yield nudges
        if yield_score < 50:
            nudges.append({
                "category": "yield",
                "priority": "high",
                "message": "🌾 Low yield predictions hurt loan eligibility. Request free agronomy consultation",
                "action": "Book Smart Scouting session",
                "impact": "Higher predicted revenue = better loan terms"
            })
        
        # Repayment nudges
        if repayment_score < 60:
            nudges.append({
                "category": "repayment",
                "priority": "critical",
                "message": "⚠️ Past defaults detected. Make one on-time payment to rebuild trust",
                "action": "Set up payment reminder 3 days before due date",
                "impact": "+25 credit score points per on-time payment"
            })
        
        # Positive reinforcement
        if all(score >= 70 for score in [savings_score, assets_score, yield_score, repayment_score]):
            nudges.append({
                "category": "achievement",
                "priority": "info",
                "message": "🎉 Excellent financial health! You qualify for premium loan rates (3% APR)",
                "action": "Apply for larger loan for farm expansion",
                "impact": "Build wealth faster with better terms"
            })
        
        return nudges


class MarketPredictionAI:
    """
    Predictive analytics for group buying and market intelligence.
    
    Capabilities:
    - Forecast input demand (fertilizer, seeds, pesticides)
    - Predict optimal selling prices
    - Detect group buying opportunities
    - Market trend analysis
    """
    
    def __init__(self):
        """Initialize market prediction AI."""
        self.seasonal_patterns = self._load_seasonal_patterns()
        
    def _load_seasonal_patterns(self) -> Dict:
        """Load historical seasonal patterns for Kenya agriculture."""
        return {
            "maize": {
                "long_rains": {"planting": "March-April", "harvest": "August-September"},
                "short_rains": {"planting": "October-November", "harvest": "January-February"}
            },
            "beans": {
                "long_rains": {"planting": "March-April", "harvest": "June-July"},
                "short_rains": {"planting": "October", "harvest": "December"}
            },
            "potato": {
                "highland": {"planting": "March-April, September", "harvest": "June-July, December"}
            }
        }
    
    def forecast_input_demand(
        self,
        chama_id: str,
        member_farm_calendars: List[Dict],
        weather_forecast: Dict,
        historical_purchases: List[Dict]
    ) -> Dict:
        """
        Forecast future demand for farm inputs.
        
        Uses:
        - Member farm calendars (planting schedules)
        - Weather forecasts (seasonal predictions)
        - Historical purchase patterns
        - Crop growth models
        
        Args:
            chama_id: Chama identifier
            member_farm_calendars: All members' planting schedules
            weather_forecast: 30-day weather prediction
            historical_purchases: Past group purchases
            
        Returns:
            Demand forecast with group buy recommendations
        """
        print(f"\n📊 Forecasting Input Demand for Chama {chama_id}...")
        
        # Analyze upcoming planting windows
        upcoming_plantings = self._analyze_planting_windows(
            member_farm_calendars, weather_forecast
        )
        
        # Calculate input requirements
        input_demand = self._calculate_input_requirements(upcoming_plantings)
        
        # Identify bulk purchase opportunities
        group_buy_opportunities = self._identify_group_buy_opportunities(
            input_demand, historical_purchases
        )
        
        # Generate recommendations
        recommendations = self._generate_procurement_recommendations(
            group_buy_opportunities
        )
        
        return {
            "chama_id": chama_id,
            "forecast_period_days": 30,
            "upcoming_plantings": upcoming_plantings,
            "input_demand": input_demand,
            "group_buy_opportunities": group_buy_opportunities,
            "recommendations": recommendations,
            "forecast_timestamp": datetime.now().isoformat()
        }
    
    def _analyze_planting_windows(
        self,
        farm_calendars: List[Dict],
        weather: Dict
    ) -> List[Dict]:
        """Analyze when members plan to plant."""
        plantings = []
        
        for calendar in farm_calendars:
            farmer_id = calendar["farmer_id"]
            crops = calendar.get("planned_crops", [])
            
            for crop in crops:
                plantings.append({
                    "farmer_id": farmer_id,
                    "crop": crop["crop_type"],
                    "area_acres": crop["area_acres"],
                    "planting_date": crop["planting_date"],
                    "urgency": self._calculate_urgency(crop["planting_date"])
                })
        
        return plantings
    
    def _calculate_urgency(self, planting_date: str) -> str:
        """Calculate urgency based on planting date."""
        planting_dt = datetime.fromisoformat(planting_date)
        days_until = (planting_dt - datetime.now()).days
        
        if days_until <= 7:
            return "critical"
        elif days_until <= 14:
            return "high"
        elif days_until <= 30:
            return "medium"
        else:
            return "low"
    
    def _calculate_input_requirements(
        self,
        plantings: List[Dict]
    ) -> Dict:
        """Calculate input requirements for all plantings."""
        
        # Standard input requirements per acre
        input_rates = {
            "maize": {
                "DAP_kg": 50,
                "CAN_kg": 50,
                "seed_kg": 20,
                "pesticide_liters": 2
            },
            "beans": {
                "DAP_kg": 30,
                "CAN_kg": 20,
                "seed_kg": 40,
                "pesticide_liters": 1
            },
            "potato": {
                "DAP_kg": 100,
                "CAN_kg": 75,
                "seed_kg": 1000,  # Seed tubers
                "fungicide_kg": 3
            }
        }
        
        demand = {
            "DAP_kg": 0,
            "CAN_kg": 0,
            "seed_kg": 0,
            "pesticide_liters": 0
        }
        
        for planting in plantings:
            crop = planting["crop"]
            area = planting["area_acres"]
            
            if crop in input_rates:
                rates = input_rates[crop]
                for input_type, rate in rates.items():
                    if input_type in demand:
                        demand[input_type] += rate * area
        
        return {
            input_type: round(quantity, 1)
            for input_type, quantity in demand.items()
            if quantity > 0
        }
    
    def _identify_group_buy_opportunities(
        self,
        demand: Dict,
        historical: List[Dict]
    ) -> List[Dict]:
        """Identify bulk purchase opportunities."""
        
        opportunities = []
        
        # Bulk discount thresholds (supplier-specific)
        bulk_thresholds = {
            "DAP_kg": {
                "min_kg": 1000,
                "discount_percent": 15,
                "supplier": "Yara East Africa"
            },
            "CAN_kg": {
                "min_kg": 500,
                "discount_percent": 12,
                "supplier": "MEA Fertilizers"
            },
            "seed_kg": {
                "min_kg": 200,
                "discount_percent": 10,
                "supplier": "Kenya Seed Company"
            }
        }
        
        for input_type, quantity in demand.items():
            if input_type in bulk_thresholds:
                threshold = bulk_thresholds[input_type]
                
                if quantity >= threshold["min_kg"]:
                    # Calculate savings
                    retail_price_per_kg = self._get_retail_price(input_type)
                    discount_price = retail_price_per_kg * (1 - threshold["discount_percent"] / 100)
                    
                    total_retail = quantity * retail_price_per_kg
                    total_discounted = quantity * discount_price
                    savings = total_retail - total_discounted
                    
                    opportunities.append({
                        "input_type": input_type,
                        "required_quantity_kg": quantity,
                        "bulk_threshold_kg": threshold["min_kg"],
                        "threshold_met": True,
                        "discount_percent": threshold["discount_percent"],
                        "supplier": threshold["supplier"],
                        "retail_price_ksh": round(total_retail, 2),
                        "discounted_price_ksh": round(total_discounted, 2),
                        "savings_ksh": round(savings, 2),
                        "savings_percent": round((savings / total_retail) * 100, 1)
                    })
        
        return opportunities
    
    def _get_retail_price(self, input_type: str) -> float:
        """Get current retail price per kg."""
        prices = {
            "DAP_kg": 120,  # KES per kg
            "CAN_kg": 80,
            "seed_kg": 250
        }
        return prices.get(input_type, 100)
    
    def _generate_procurement_recommendations(
        self,
        opportunities: List[Dict]
    ) -> List[Dict]:
        """Generate actionable procurement recommendations."""
        
        recommendations = []
        
        for opp in opportunities:
            recommendations.append({
                "action": "start_group_buy",
                "input_type": opp["input_type"],
                "message": f"🎯 Group Buy Alert: {opp['input_type']} - Save {opp['savings_percent']}%!",
                "details": f"Chama needs {opp['required_quantity_kg']} kg. Bulk order saves KES {opp['savings_ksh']:.0f}",
                "deadline": (datetime.now() + timedelta(days=7)).isoformat(),
                "supplier": opp["supplier"],
                "priority": "high"
            })
        
        return recommendations
    
    def predict_optimal_selling_price(
        self,
        crop_type: str,
        quality_grade: str,
        quantity_kg: float,
        harvest_date: str,
        market_data: Dict
    ) -> Dict:
        """
        Predict optimal selling price for harvest.
        
        Considers:
        - Current market prices
        - Seasonal trends
        - Quality grade premium
        - Supply/demand forecast
        
        Args:
            crop_type: Type of crop
            quality_grade: Grade A/B/C
            quantity_kg: Harvest quantity
            harvest_date: Expected harvest date
            market_data: Current market intelligence
            
        Returns:
            Price recommendation
        """
        # Current market price (wholesale)
        base_prices = {
            "maize": 45,  # KES per kg
            "beans": 80,
            "potato": 50,
            "tomato": 60,
            "cabbage": 25
        }
        
        base_price = base_prices.get(crop_type, 50)
        
        # Quality premium
        quality_multipliers = {
            "grade_a": 1.20,
            "grade_b": 1.00,
            "reject": 0.60
        }
        
        quality_price = base_price * quality_multipliers.get(quality_grade, 1.0)
        
        # Seasonal adjustment
        harvest_dt = datetime.fromisoformat(harvest_date)
        seasonal_factor = self._calculate_seasonal_factor(crop_type, harvest_dt)
        
        adjusted_price = quality_price * seasonal_factor
        
        # Supply/demand forecast
        supply_factor = self._forecast_supply_demand(crop_type, harvest_dt)
        
        final_price = adjusted_price * supply_factor
        
        # Generate recommendation
        total_revenue = final_price * quantity_kg
        
        return {
            "crop_type": crop_type,
            "quality_grade": quality_grade,
            "recommended_price_per_kg": round(final_price, 2),
            "price_range": {
                "min_ksh": round(final_price * 0.90, 2),
                "max_ksh": round(final_price * 1.10, 2)
            },
            "total_revenue_ksh": round(total_revenue, 2),
            "market_intelligence": {
                "base_price": base_price,
                "quality_premium": round((quality_multipliers[quality_grade] - 1) * 100, 1),
                "seasonal_factor": round((seasonal_factor - 1) * 100, 1),
                "supply_demand_factor": round((supply_factor - 1) * 100, 1)
            },
            "confidence": 0.85,
            "recommendation": self._generate_price_recommendation(
                final_price, base_price, seasonal_factor
            )
        }
    
    def _calculate_seasonal_factor(
        self,
        crop_type: str,
        harvest_date: datetime
    ) -> float:
        """Calculate seasonal price factor."""
        # Prices peak during off-season, drop during harvest glut
        month = harvest_date.month
        
        # Simplified seasonal model
        if crop_type == "maize":
            # Peak: Feb-March (before Long Rains harvest)
            # Low: August-September (harvest glut)
            if month in [2, 3]:
                return 1.25
            elif month in [8, 9]:
                return 0.85
            else:
                return 1.0
        else:
            return 1.0
    
    def _forecast_supply_demand(
        self,
        crop_type: str,
        harvest_date: datetime
    ) -> float:
        """Forecast supply/demand balance."""
        # Placeholder for ML-based forecasting
        # In production, this uses time series models
        
        # Simulate supply shock (e.g., drought reduces supply)
        return 1.05  # 5% price increase due to tight supply
    
    def _generate_price_recommendation(
        self,
        final_price: float,
        base_price: float,
        seasonal_factor: float
    ) -> str:
        """Generate human-readable price recommendation."""
        if seasonal_factor > 1.1:
            return f"🎯 Excellent timing! Market prices {((seasonal_factor - 1) * 100):.0f}% above baseline. Sell immediately."
        elif seasonal_factor < 0.9:
            return f"⚠️ Harvest glut expected. Prices {((1 - seasonal_factor) * 100):.0f}% below baseline. Consider storage or processing."
        else:
            return f"✅ Fair market conditions. Recommended price: KES {final_price:.2f}/kg"


class DisputeAdjudicatorAI:
    """
    AI-powered dispute resolution for marketplace transactions.
    
    Uses computer vision to compare:
    - Grading belt's Digital Manifest images
    - Buyer's evidence photos
    
    Provides fast, impartial first-line adjudication.
    """
    
    def __init__(self):
        """Initialize dispute adjudicator."""
        self.similarity_threshold = 0.85
        
    def adjudicate_dispute(
        self,
        dispute_id: str,
        contract_hash: str,
        manifest_data: Dict,
        buyer_evidence: Dict
    ) -> Dict:
        """
        Adjudicate marketplace dispute using AI.
        
        Args:
            dispute_id: Dispute case identifier
            contract_hash: Smart contract hash (blockchain)
            manifest_data: Original grading belt manifest
            buyer_evidence: Buyer's photos and claims
            
        Returns:
            Adjudication decision with reasoning
        """
        print(f"\n⚖️ Adjudicating Dispute {dispute_id}...")
        
        # Step 1: Verify contract integrity
        contract_valid = self._verify_contract_integrity(contract_hash)
        
        if not contract_valid:
            return {
                "dispute_id": dispute_id,
                "decision": "invalid_contract",
                "message": "Smart contract integrity compromised. Escalate to human arbitration.",
                "confidence": 0.0
            }
        
        # Step 2: Compare images using CV
        visual_comparison = self._compare_images(
            manifest_data["images"],
            buyer_evidence["photos"]
        )
        
        # Step 3: Analyze quality claims
        quality_analysis = self._analyze_quality_discrepancy(
            manifest_data["quality_distribution"],
            buyer_evidence["reported_quality"]
        )
        
        # Step 4: Make decision
        decision = self._make_decision(visual_comparison, quality_analysis)
        
        return {
            "dispute_id": dispute_id,
            "decision": decision["verdict"],
            "confidence": decision["confidence"],
            "reasoning": decision["reasoning"],
            "evidence_analysis": {
                "visual_similarity": visual_comparison["similarity_score"],
                "quality_discrepancy": quality_analysis["discrepancy_percent"],
                "contract_verified": contract_valid
            },
            "recommended_resolution": decision["resolution"],
            "adjudication_timestamp": datetime.now().isoformat()
        }
    
    def _verify_contract_integrity(self, contract_hash: str) -> bool:
        """Verify smart contract hash on blockchain."""
        # In production, this queries blockchain
        # For demo, assume valid
        return True
    
    def _compare_images(
        self,
        manifest_images: List[str],
        buyer_photos: List[str]
    ) -> Dict:
        """
        Compare grading belt images with buyer evidence using CV.
        
        Uses perceptual hashing and structural similarity.
        """
        # Placeholder for CV comparison
        # In production, uses deep learning similarity models
        
        # Simulate similarity score
        similarity = 0.92  # 92% similar (likely same produce)
        
        return {
            "similarity_score": similarity,
            "matches": len(manifest_images),
            "analysis": "High visual similarity detected. Likely same batch."
        }
    
    def _analyze_quality_discrepancy(
        self,
        manifest_quality: Dict,
        buyer_reported: Dict
    ) -> Dict:
        """Analyze discrepancy between grading belt and buyer claims."""
        
        manifest_grade_a = manifest_quality.get("grade_a_count", 0)
        manifest_total = manifest_quality.get("total_count", 1)
        
        buyer_grade_a = buyer_reported.get("grade_a_count", 0)
        buyer_total = buyer_reported.get("total_count", 1)
        
        manifest_percentage = (manifest_grade_a / manifest_total) * 100
        buyer_percentage = (buyer_grade_a / buyer_total) * 100
        
        discrepancy = abs(manifest_percentage - buyer_percentage)
        
        return {
            "manifest_grade_a_percent": round(manifest_percentage, 1),
            "buyer_reported_percent": round(buyer_percentage, 1),
            "discrepancy_percent": round(discrepancy, 1),
            "significant": discrepancy > 10
        }
    
    def _make_decision(
        self,
        visual: Dict,
        quality: Dict
    ) -> Dict:
        """Make adjudication decision based on evidence."""
        
        similarity = visual["similarity_score"]
        discrepancy = quality["discrepancy_percent"]
        
        # Decision logic
        if similarity >= 0.90 and discrepancy < 5:
            # Clear match, minimal discrepancy
            return {
                "verdict": "favor_farmer",
                "confidence": 0.95,
                "reasoning": "Visual evidence matches Digital Manifest. Quality discrepancy within acceptable variance (<5%).",
                "resolution": "Reject buyer claim. No refund."
            }
        
        elif similarity >= 0.85 and discrepancy < 15:
            # Good match, small discrepancy
            return {
                "verdict": "partial_favor_buyer",
                "confidence": 0.75,
                "reasoning": f"Visual match confirmed but {discrepancy:.1f}% quality discrepancy detected.",
                "resolution": f"Partial refund: {discrepancy:.0f}% of contract value."
            }
        
        elif similarity < 0.70 or discrepancy > 25:
            # Poor match or large discrepancy
            return {
                "verdict": "favor_buyer",
                "confidence": 0.85,
                "reasoning": f"Significant evidence of quality substitution. Similarity: {similarity:.1%}, Discrepancy: {discrepancy:.1f}%",
                "resolution": "Full refund to buyer. Investigate farmer."
            }
        
        else:
            # Unclear case
            return {
                "verdict": "escalate_to_human",
                "confidence": 0.50,
                "reasoning": "Inconclusive evidence. Requires human arbitration.",
                "resolution": "Schedule video mediation between parties."
            }


if __name__ == "__main__":
    # Demo: Financial Health AI
    print("=" * 60)
    print("🌾 AgroPulse Community & Financial AI Demo")
    print("=" * 60)
    
    financial_ai = FinancialHealthAI()
    
    # Sample farmer data
    savings_data = {
        "monthly_contributions": [500, 500, 700, 500, 600, 800],  # KES
        "current_balance_ksh": 15000
    }
    
    farm_assets = {
        "land_acres": 2.5,
        "land_owned": True,
        "equipment_value_ksh": 25000,
        "livestock_value_ksh": 15000,
        "infrastructure_value_ksh": 10000
    }
    
    yield_prediction = {
        "predicted_yield_kg": 2500,
        "predicted_revenue_ksh": 125000,
        "confidence": 0.88
    }
    
    repayment_history = {
        "total_loans": 3,
        "on_time_payments": 3,
        "defaults": 0
    }
    
    risk_assessment = financial_ai.calculate_risk_score(
        member_id="MEMBER-001",
        savings_data=savings_data,
        farm_assets=farm_assets,
        yield_prediction=yield_prediction,
        repayment_history=repayment_history
    )
    
    print(f"\n📊 RISK ASSESSMENT SUMMARY")
    print(f"   Risk Score: {risk_assessment['risk_score']}/100")
    print(f"   Category: {risk_assessment['risk_category'].upper()}")
    print(f"   Recommended Loan: KES {risk_assessment['loan_recommendation']['recommended_amount_ksh']}")
    print(f"   Interest Rate: {risk_assessment['loan_recommendation']['interest_rate_percent']}% APR")
    print(f"   Monthly Payment: KES {risk_assessment['loan_recommendation']['monthly_payment_ksh']}")
    
    print(f"\n💡 BEHAVIORAL NUDGES ({len(risk_assessment['behavioral_nudges'])} total):")
    for nudge in risk_assessment['behavioral_nudges'][:2]:
        print(f"   • {nudge['message']}")
        print(f"     Impact: {nudge['impact']}")
    
    # Demo: Market Prediction AI
    print("\n" + "="*60)
    print("📈 Market Prediction AI Demo")
    print("="*60)
    
    market_ai = MarketPredictionAI()
    
    # Forecast input demand
    farm_calendars = [
        {
            "farmer_id": "F001",
            "planned_crops": [
                {"crop_type": "maize", "area_acres": 2.0, "planting_date": "2025-11-15"}
            ]
        },
        {
            "farmer_id": "F002",
            "planned_crops": [
                {"crop_type": "maize", "area_acres": 3.0, "planting_date": "2025-11-20"}
            ]
        }
    ]
    
    demand_forecast = market_ai.forecast_input_demand(
        chama_id="CHAMA-001",
        member_farm_calendars=farm_calendars,
        weather_forecast={},
        historical_purchases=[]
    )
    
    print(f"\n📊 INPUT DEMAND FORECAST")
    print(f"   DAP Fertilizer: {demand_forecast['input_demand'].get('DAP_kg', 0)} kg")
    print(f"   CAN Fertilizer: {demand_forecast['input_demand'].get('CAN_kg', 0)} kg")
    
    if demand_forecast["group_buy_opportunities"]:
        print(f"\n💰 GROUP BUY OPPORTUNITIES:")
        for opp in demand_forecast["group_buy_opportunities"]:
            print(f"   • {opp['input_type']}: Save {opp['savings_percent']}% (KES {opp['savings_ksh']})")
    
    # Demo: Dispute Adjudicator
    print("\n" + "="*60)
    print("⚖️ Dispute Adjudicator AI Demo")
    print("="*60)
    
    adjudicator = DisputeAdjudicatorAI()
    
    manifest = {
        "images": ["img1.jpg", "img2.jpg"],
        "quality_distribution": {
            "grade_a_count": 80,
            "grade_b_count": 15,
            "reject_count": 5,
            "total_count": 100
        }
    }
    
    buyer_evidence = {
        "photos": ["evidence1.jpg", "evidence2.jpg"],
        "reported_quality": {
            "grade_a_count": 70,
            "grade_b_count": 20,
            "reject_count": 10,
            "total_count": 100
        }
    }
    
    decision = adjudicator.adjudicate_dispute(
        dispute_id="DISP-001",
        contract_hash="0xabc123...",
        manifest_data=manifest,
        buyer_evidence=buyer_evidence
    )
    
    print(f"\n⚖️ DISPUTE RESOLUTION")
    print(f"   Decision: {decision['decision'].upper()}")
    print(f"   Confidence: {decision['confidence'] * 100:.0f}%")
    print(f"   Reasoning: {decision['reasoning']}")
    print(f"   Resolution: {decision['recommended_resolution']}")
    
    print("\n✅ Community & Financial AI demonstration complete!")
