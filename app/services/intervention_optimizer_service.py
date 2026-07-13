"""
AI-Powered Intervention Optimization Service
From Diagnosis to Actionable Decision

Core Idea 7: From Diagnosis to Decision
- After 99% diagnosis, access localized treatment database
- Run cost-benefit optimization: treatment cost vs efficacy vs yield loss
- Provide ranked, actionable recommendations with financial analysis
- Transform complex agronomic problem into simple financial decision
"""

import logging
from typing import Dict, List, Optional
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import numpy as np

from app.models.cctv import CropHealthReading
from app.models.treatment import TreatmentOption, TreatmentEfficacy
from app.config import settings

logger = logging.getLogger(__name__)


class InterventionOptimizationService:
    """
    AI-powered treatment recommendation and cost-benefit optimizer
    
    Architecture:
    1. Receive 99% confident diagnosis
    2. Query localized treatment database
    3. Calculate cost-benefit for each treatment option
    4. Rank by ROI, efficacy, and farmer constraints
    5. Present clear, actionable recommendations
    
    Output format:
    "Diagnosis: Fall Armyworm (92% confidence)
     
     Option 1: Brand X Chemical (Cost: 1,200 KSh, Efficacy: 98%, ROI: 4.2×)
     Option 2: Neem Oil Organic (Cost: 800 KSh, Efficacy: 85%, ROI: 3.5×)
     Option 3: BT Biopesticide (Cost: 1,000 KSh, Efficacy: 90%, ROI: 3.8×)"
    
    Benefits:
    - Reduces decision paralysis
    - Maximizes financial outcome
    - Considers farmer budget constraints
    - Includes organic/chemical/biological options
    - Shows expected ROI and timeline
    """
    
    def __init__(self):
        self.treatment_database = self._load_treatment_database()
        self.market_prices = self._load_market_prices()
        
        logger.info("✅ Intervention Optimization Service initialized")
        logger.info(f"   Treatment options loaded: {len(self.treatment_database)}")
    
    
    async def recommend_interventions(
        self,
        db: AsyncSession,
        diagnosis: Dict,
        crop_type: str,
        field_area_ha: float,
        farmer_budget_ksh: Optional[float] = None,
        preferences: Optional[Dict] = None
    ) -> Dict:
        """
        Generate ranked treatment recommendations with cost-benefit analysis
        
        Args:
            diagnosis: Full diagnosis (disease, confidence, severity, yield_loss)
            crop_type: Type of crop (maize, tomato, etc.)
            field_area_ha: Field size in hectares
            farmer_budget_ksh: Available budget (optional, for filtering)
            preferences: Farmer preferences (organic_only, fast_acting, etc.)
        
        Returns:
            Ranked list of treatment options with financial analysis
        """
        logger.info(f"🎯 Optimizing intervention for {crop_type}")
        logger.info(f"   Diagnosis: {diagnosis.get('disease')} ({diagnosis.get('confidence')*100:.0f}% confidence)")
        logger.info(f"   Severity: {diagnosis.get('severity')}")
        logger.info(f"   Field size: {field_area_ha} ha")
        
        disease = diagnosis.get('disease', 'unknown')
        severity = diagnosis.get('severity', 'medium')
        estimated_yield_loss_percent = diagnosis.get('estimated_yield_loss_percent', 20)
        
        # Step 1: Get all applicable treatments for this disease
        applicable_treatments = self._get_applicable_treatments(
            disease, crop_type
        )
        
        logger.info(f"   📋 Applicable treatments: {len(applicable_treatments)}")
        
        if len(applicable_treatments) == 0:
            return {
                "status": "no_treatments_found",
                "message": "No treatments available for this disease",
                "recommendation": "Consult local agronomist"
            }
        
        # Step 2: Calculate cost-benefit for each treatment
        options = []
        for treatment in applicable_treatments:
            option = self._calculate_treatment_roi(
                treatment=treatment,
                severity=severity,
                field_area_ha=field_area_ha,
                estimated_yield_loss_percent=estimated_yield_loss_percent,
                crop_type=crop_type
            )
            options.append(option)
        
        # Step 3: Filter by budget (if provided)
        if farmer_budget_ksh:
            options = [opt for opt in options if opt['total_cost_ksh'] <= farmer_budget_ksh]
            logger.info(f"   💰 Filtered by budget ({farmer_budget_ksh} KSh): {len(options)} options")
        
        # Step 4: Filter by preferences
        if preferences:
            if preferences.get('organic_only'):
                options = [opt for opt in options if opt['treatment_type'] in ['organic', 'biological']]
            if preferences.get('fast_acting'):
                options = [opt for opt in options if opt['time_to_effect_days'] <= 3]
        
        # Step 5: Rank by composite score (ROI × Efficacy × Speed)
        for option in options:
            option['composite_score'] = (
                option['roi'] * 0.4 +
                option['efficacy'] * 0.3 +
                (1.0 / (option['time_to_effect_days'] + 1)) * 0.3
            )
        
        options = sorted(options, key=lambda x: x['composite_score'], reverse=True)
        
        # Step 6: Add ranks and explanations
        for i, option in enumerate(options, 1):
            option['rank'] = i
            option['explanation'] = self._generate_explanation(option, i)
        
        # Step 7: Calculate no-action scenario (baseline)
        no_action_loss = self._calculate_no_action_loss(
            estimated_yield_loss_percent, field_area_ha, crop_type
        )
        
        logger.info(f"✅ Optimization complete")
        logger.info(f"   Top recommendation: {options[0]['treatment_name']}")
        logger.info(f"   Expected ROI: {options[0]['roi']:.1f}×")
        logger.info(f"   Expected savings: {options[0]['expected_savings_ksh']:.0f} KSh")
        
        return {
            "status": "optimized",
            "diagnosis": {
                "disease": disease,
                "confidence": diagnosis.get('confidence'),
                "severity": severity
            },
            "field_info": {
                "crop_type": crop_type,
                "area_hectares": field_area_ha,
                "estimated_yield_loss_percent": estimated_yield_loss_percent
            },
            "no_action_scenario": no_action_loss,
            "treatment_options": options[:5],  # Top 5 recommendations
            "total_options_evaluated": len(applicable_treatments),
            "farmer_budget_ksh": farmer_budget_ksh,
            "preferences_applied": preferences,
            "recommendation_summary": self._generate_summary(options[0], no_action_loss),
            "generated_at": datetime.utcnow().isoformat()
        }
    
    
    def _get_applicable_treatments(
        self,
        disease: str,
        crop_type: str
    ) -> List[Dict]:
        """
        Get all treatments applicable to this disease and crop
        """
        applicable = []
        
        for treatment_id, treatment in self.treatment_database.items():
            # Check if treatment targets this disease
            if disease in treatment['target_diseases'] or 'all' in treatment['target_diseases']:
                # Check if treatment is approved for this crop
                if crop_type in treatment['approved_crops'] or 'all' in treatment['approved_crops']:
                    applicable.append(treatment)
        
        return applicable
    
    
    def _calculate_treatment_roi(
        self,
        treatment: Dict,
        severity: str,
        field_area_ha: float,
        estimated_yield_loss_percent: float,
        crop_type: str
    ) -> Dict:
        """
        Calculate ROI for a single treatment option
        
        Formula:
        ROI = (Yield Saved × Market Price - Treatment Cost) / Treatment Cost
        
        Where:
        Yield Saved = Baseline Yield × Yield Loss % × Treatment Efficacy
        """
        # Get treatment details
        treatment_name = treatment['name']
        treatment_type = treatment['type']  # chemical, organic, biological
        
        # Base efficacy (adjusted for severity)
        base_efficacy = treatment['efficacy'][severity]
        
        # Application rate (L/ha or kg/ha)
        application_rate = treatment['application_rate_per_ha']
        
        # Unit cost (KSh per L or kg)
        unit_cost = treatment['unit_cost_ksh']
        
        # Calculate total cost
        units_needed = application_rate * field_area_ha
        product_cost = units_needed * unit_cost
        application_cost = treatment['application_cost_ksh'] * field_area_ha
        total_cost = product_cost + application_cost
        
        # Calculate expected yield saved
        baseline_yield_kg = self._get_baseline_yield(crop_type) * field_area_ha
        yield_at_risk_kg = baseline_yield_kg * (estimated_yield_loss_percent / 100.0)
        yield_saved_kg = yield_at_risk_kg * base_efficacy
        
        # Calculate revenue from saved yield
        market_price_per_kg = self.market_prices.get(crop_type, 50)
        revenue_saved = yield_saved_kg * market_price_per_kg
        
        # Calculate ROI
        net_benefit = revenue_saved - total_cost
        roi = net_benefit / total_cost if total_cost > 0 else 0
        
        # Time to effect
        time_to_effect_days = treatment['time_to_effect_days']
        
        # Build option object
        option = {
            "treatment_name": treatment_name,
            "treatment_type": treatment_type,
            "active_ingredient": treatment.get('active_ingredient', 'N/A'),
            "efficacy": base_efficacy,
            "total_cost_ksh": round(total_cost, 0),
            "product_cost_ksh": round(product_cost, 0),
            "application_cost_ksh": round(application_cost, 0),
            "units_needed": round(units_needed, 2),
            "unit_type": treatment['unit_type'],
            "expected_yield_saved_kg": round(yield_saved_kg, 0),
            "expected_revenue_saved_ksh": round(revenue_saved, 0),
            "expected_savings_ksh": round(net_benefit, 0),
            "roi": round(roi, 2),
            "time_to_effect_days": time_to_effect_days,
            "reapplication_needed": treatment.get('reapplication_needed', False),
            "reapplication_days": treatment.get('reapplication_days', 14),
            "organic_certified": treatment_type in ['organic', 'biological'],
            "safety_rating": treatment.get('safety_rating', 'medium'),
            "local_availability": treatment.get('local_availability', 'common'),
            "supplier": treatment.get('supplier', 'Local agrodealers')
        }
        
        return option
    
    
    def _calculate_no_action_loss(
        self,
        estimated_yield_loss_percent: float,
        field_area_ha: float,
        crop_type: str
    ) -> Dict:
        """
        Calculate financial loss if farmer takes no action
        """
        baseline_yield_kg = self._get_baseline_yield(crop_type) * field_area_ha
        yield_loss_kg = baseline_yield_kg * (estimated_yield_loss_percent / 100.0)
        market_price_per_kg = self.market_prices.get(crop_type, 50)
        revenue_loss_ksh = yield_loss_kg * market_price_per_kg
        
        return {
            "scenario": "no_action",
            "estimated_yield_loss_kg": round(yield_loss_kg, 0),
            "estimated_revenue_loss_ksh": round(revenue_loss_ksh, 0),
            "warning": "Without intervention, losses will likely increase over time"
        }
    
    
    def _get_baseline_yield(self, crop_type: str) -> float:
        """
        Get baseline yield in kg/ha for crop type
        """
        baseline_yields = {
            "maize": 3000,
            "tomato": 15000,
            "potato": 12000,
            "beans": 1500,
            "kale": 8000,
            "cabbage": 20000
        }
        
        return baseline_yields.get(crop_type, 2000)
    
    
    def _generate_explanation(self, option: Dict, rank: int) -> str:
        """
        Generate human-readable explanation for this option
        """
        if rank == 1:
            return f"✅ Best overall value: {option['roi']:.1f}× ROI with {option['efficacy']*100:.0f}% efficacy"
        elif option['organic_certified']:
            return f"🌿 Organic option: Lower cost but slightly lower efficacy"
        elif option['time_to_effect_days'] <= 2:
            return f"⚡ Fast-acting: Shows results within {option['time_to_effect_days']} days"
        elif option['efficacy'] >= 0.95:
            return f"🎯 Highest efficacy: {option['efficacy']*100:.0f}% success rate"
        else:
            return f"💰 Good value: {option['roi']:.1f}× ROI"
    
    
    def _generate_summary(self, top_option: Dict, no_action: Dict) -> str:
        """
        Generate executive summary for farmer
        """
        summary = f"""
💊 **Recommended Treatment**: {top_option['treatment_name']}

📊 **Financial Analysis**:
• Investment: {top_option['total_cost_ksh']:.0f} KSh
• Expected savings: {top_option['expected_savings_ksh']:.0f} KSh
• ROI: {top_option['roi']:.1f}× your investment
• Break-even: {top_option['time_to_effect_days']} days

⚠️ **Without Treatment**:
• Projected loss: {no_action['estimated_revenue_loss_ksh']:.0f} KSh

✅ **Our Recommendation**:
Applying {top_option['treatment_name']} will save you {top_option['expected_savings_ksh']:.0f} KSh 
compared to no action. This is a {top_option['roi']:.1f}× return on your {top_option['total_cost_ksh']:.0f} KSh investment.
"""
        
        return summary.strip()
    
    
    def _load_treatment_database(self) -> Dict:
        """
        Load localized treatment database
        
        In production: Load from database with regional pricing
        For now: Use hardcoded common treatments
        """
        return {
            # Fall Armyworm treatments
            "faw_chemical_1": {
                "name": "Lambda-cyhalothrin 2.5% EC",
                "type": "chemical",
                "active_ingredient": "Lambda-cyhalothrin",
                "target_diseases": ["fall_armyworm", "stem_borer"],
                "approved_crops": ["maize", "beans", "tomato"],
                "efficacy": {"low": 0.98, "medium": 0.95, "high": 0.90, "critical": 0.85},
                "application_rate_per_ha": 0.5,  # Liters
                "unit_type": "liter",
                "unit_cost_ksh": 2400,
                "application_cost_ksh": 300,
                "time_to_effect_days": 2,
                "reapplication_needed": True,
                "reapplication_days": 14,
                "safety_rating": "medium",
                "local_availability": "common",
                "supplier": "Local agrodealers"
            },
            
            "faw_biological_1": {
                "name": "BT (Bacillus thuringiensis) Biopesticide",
                "type": "biological",
                "active_ingredient": "Bacillus thuringiensis",
                "target_diseases": ["fall_armyworm", "stem_borer"],
                "approved_crops": ["maize", "beans", "tomato", "cabbage"],
                "efficacy": {"low": 0.92, "medium": 0.88, "high": 0.80, "critical": 0.70},
                "application_rate_per_ha": 1.0,  # Liters
                "unit_type": "liter",
                "unit_cost_ksh": 1000,
                "application_cost_ksh": 300,
                "time_to_effect_days": 3,
                "reapplication_needed": True,
                "reapplication_days": 7,
                "safety_rating": "high",
                "local_availability": "common",
                "supplier": "KALRO, Agrodealers"
            },
            
            "faw_organic_1": {
                "name": "Neem Oil Extract",
                "type": "organic",
                "active_ingredient": "Azadirachtin",
                "target_diseases": ["fall_armyworm", "aphid_infestation"],
                "approved_crops": ["all"],
                "efficacy": {"low": 0.88, "medium": 0.82, "high": 0.75, "critical": 0.65},
                "application_rate_per_ha": 2.0,  # Liters
                "unit_type": "liter",
                "unit_cost_ksh": 400,
                "application_cost_ksh": 300,
                "time_to_effect_days": 5,
                "reapplication_needed": True,
                "reapplication_days": 7,
                "safety_rating": "high",
                "local_availability": "very_common",
                "supplier": "Local markets, Agrodealers"
            },
            
            # Fungal disease treatments
            "fungal_chemical_1": {
                "name": "Mancozeb 80% WP",
                "type": "chemical",
                "active_ingredient": "Mancozeb",
                "target_diseases": ["downy_mildew", "late_blight", "early_blight"],
                "approved_crops": ["tomato", "potato", "beans"],
                "efficacy": {"low": 0.95, "medium": 0.92, "high": 0.88, "critical": 0.80},
                "application_rate_per_ha": 2.5,  # kg
                "unit_type": "kilogram",
                "unit_cost_ksh": 800,
                "application_cost_ksh": 400,
                "time_to_effect_days": 3,
                "reapplication_needed": True,
                "reapplication_days": 10,
                "safety_rating": "medium",
                "local_availability": "very_common",
                "supplier": "All agrodealers"
            },
            
            "fungal_organic_1": {
                "name": "Copper Hydroxide (Organic Approved)",
                "type": "organic",
                "active_ingredient": "Copper hydroxide",
                "target_diseases": ["downy_mildew", "bacterial_wilt"],
                "approved_crops": ["tomato", "potato", "beans"],
                "efficacy": {"low": 0.85, "medium": 0.80, "high": 0.72, "critical": 0.65},
                "application_rate_per_ha": 3.0,  # kg
                "unit_type": "kilogram",
                "unit_cost_ksh": 600,
                "application_cost_ksh": 400,
                "time_to_effect_days": 4,
                "reapplication_needed": True,
                "reapplication_days": 7,
                "safety_rating": "high",
                "local_availability": "common",
                "supplier": "Organic agrodealers"
            }
        }
    
    
    def _load_market_prices(self) -> Dict:
        """
        Load current market prices (KSh per kg)
        
        In production: Fetch from live market data API
        """
        return {
            "maize": 45,
            "tomato": 80,
            "potato": 60,
            "beans": 120,
            "kale": 40,
            "cabbage": 35
        }


# Singleton instance
intervention_optimizer = InterventionOptimizationService()
