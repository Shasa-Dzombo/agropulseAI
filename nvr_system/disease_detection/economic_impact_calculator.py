"""
Economic Impact Calculator
Quantifies disease losses and treatment economics

YIELD LOSS SCENARIOS:

CATASTROPHIC DISEASES (50-100% LOSS):
- Late blight (untreated): 100% loss in 7-14 days
- Panama Disease TR4 (banana): 100% loss + field abandoned 40+ years
- Coffee leaf rust epidemic: 80-100% loss
- Fire blight (apple/pear): 100% orchard loss possible
- Citrus greening HLB: 100% tree death (slow decline)

SEVERE DISEASES (30-70% LOSS):
- Black Sigatoka (banana): 35-50% untreated
- Downy mildew: 30-60% loss
- Powdery mildew (fruit): 40-60% loss
- Fusarium wilt: 50-80% loss
- Anthracnose (mango): 40-100% post-harvest

MODERATE DISEASES (10-30% LOSS):
- Early blight: 15-30% loss
- Bacterial spot: 10-30% yield + quality downgrade
- Common scab (potato): 5-20% cosmetic loss
- Septoria leaf spot: 10-25% loss

QUALITY DOWNGRADES:

FRESH MARKET LOSSES:
- Cosmetic damage: 50-80% price reduction
- Size reduction: 30-60% price reduction
- Bacterial spot lesions: 70-80% downgrade to processing
- Apple scab: 100% fresh market rejection
- Citrus canker: Export banned (trade loss)

POST-HARVEST LOSSES:
- Mango anthracnose: 40-100% post-harvest loss
- Peach brown rot: 30-80% storage loss
- Banana crown rot: 20-40% transport loss
- Botrytis (strawberry): 50-90% shelf life reduction

TREATMENT ECONOMICS:

FUNGICIDE COSTS (per hectare):
- Mancozeb: $15/application
- Copper: $20/application
- Azoxystrobin (QoI): $45/application
- Propiconazole (DMI): $30/application
- Captan: $18/application

INTENSIVE PROGRAMS:
- Potato late blight: $180-250/ha (7-10 applications)
- Banana Black Sigatoka: $500-800/ha (25-50 applications!)
- Apple scab: $150-200/ha (8-12 applications)
- Grape downy/powdery: $200-300/ha (6-10 applications)

Author: AgroPulse AI Team
Version: 1.0.0
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Tuple, Optional
from datetime import datetime


class LossType(Enum):
    """Type of economic loss"""
    YIELD_LOSS = "yield_loss"
    QUALITY_DOWNGRADE = "quality_downgrade"
    POST_HARVEST_LOSS = "post_harvest_loss"
    QUARANTINE_RESTRICTION = "quarantine_restriction"
    ERADICATION_COST = "eradication_cost"
    FIELD_ABANDONMENT = "field_abandonment"


class MarketGrade(Enum):
    """Market quality grades"""
    PREMIUM = "premium"  # Top grade
    FRESH_MARKET = "fresh_market"  # Standard fresh
    PROCESSING = "processing"  # Processing grade
    ANIMAL_FEED = "animal_feed"  # Severe damage
    UNMARKETABLE = "unmarketable"  # Total loss


@dataclass
class CropValue:
    """Crop market values"""
    crop: str
    
    # Yield and value
    typical_yield_tons_per_ha: float
    
    # Market prices (USD per ton)
    premium_price: float
    fresh_market_price: float
    processing_price: float
    
    # Production costs
    production_cost_per_ha: float
    
    notes: str = ""


@dataclass
class DiseaseImpact:
    """Disease economic impact parameters"""
    disease: str
    crop: str
    
    # Yield loss
    yield_loss_min: float  # Minimum % loss
    yield_loss_typical: float  # Typical % loss
    yield_loss_max: float  # Maximum % loss
    
    # Quality impact
    quality_downgrade: bool
    downgrade_percentage: float  # % of crop downgraded
    grade_reduction: str  # fresh→processing, etc
    
    # Post-harvest
    post_harvest_loss: float  # % loss in storage/transport
    
    # Special impacts
    field_abandonment_years: int = 0  # Panama TR4 = 40 years!
    quarantine_restrictions: bool = False
    export_banned: bool = False
    
    # Treatment costs
    treatment_cost_per_ha: float = 0.0
    applications_per_season: int = 0
    
    notes: str = ""


@dataclass
class EconomicAnalysis:
    """Complete economic impact analysis"""
    crop: str
    disease: str
    area_hectares: float
    
    # Yield impacts
    baseline_yield_tons: float
    diseased_yield_tons: float
    yield_loss_tons: float
    yield_loss_percentage: float
    
    # Value impacts
    baseline_value_usd: float
    diseased_value_usd: float
    gross_loss_usd: float
    
    # Quality impacts
    fresh_market_loss_tons: float
    processing_grade_tons: float
    quality_loss_usd: float
    
    # Treatment costs
    treatment_cost_usd: float
    treatment_applications: int
    
    # Net impact
    net_loss_usd: float  # Includes treatment cost
    
    # ROI analysis
    treatment_benefit_usd: float
    roi_ratio: float  # benefit/cost
    
    # Per hectare metrics
    loss_per_hectare_usd: float
    
    recommendations: List[str] = field(default_factory=list)
    notes: str = ""


class EconomicImpactCalculator:
    """
    Economic impact calculator
    
    FEATURES:
    - Yield loss estimation
    - Quality downgrade valuation
    - Treatment ROI analysis
    - Break-even calculations
    """
    
    def __init__(self):
        self.crop_values = self._initialize_crop_values()
        self.disease_impacts = self._initialize_disease_impacts()
    
    def _initialize_crop_values(self) -> Dict[str, CropValue]:
        """Market values for crops"""
        return {
            'potato': CropValue(
                crop='Potato',
                typical_yield_tons_per_ha=40.0,
                premium_price=500.0,  # Fresh market premium
                fresh_market_price=350.0,  # Standard fresh
                processing_price=180.0,  # Processing/fries
                production_cost_per_ha=3500.0,
                notes='Fresh market 2x value of processing'
            ),
            
            'tomato': CropValue(
                crop='Tomato',
                typical_yield_tons_per_ha=60.0,
                premium_price=800.0,
                fresh_market_price=550.0,
                processing_price=150.0,
                production_cost_per_ha=5000.0,
                notes='Fresh market tomatoes 3-4x processing value'
            ),
            
            'apple': CropValue(
                crop='Apple',
                typical_yield_tons_per_ha=35.0,
                premium_price=1200.0,
                fresh_market_price=800.0,
                processing_price=200.0,
                production_cost_per_ha=4500.0,
                notes='Cosmetic damage = processing grade (75% value loss)'
            ),
            
            'banana': CropValue(
                crop='Banana',
                typical_yield_tons_per_ha=40.0,
                premium_price=600.0,
                fresh_market_price=450.0,
                processing_price=150.0,
                production_cost_per_ha=3000.0,
                notes='Export quality critical - cosmetic damage severe'
            ),
            
            'coffee': CropValue(
                crop='Coffee',
                typical_yield_tons_per_ha=2.0,  # Green coffee
                premium_price=8000.0,  # Specialty
                fresh_market_price=5000.0,  # Commercial arabica
                processing_price=3000.0,  # Low grade
                production_cost_per_ha=2500.0,
                notes='High value crop - leaf rust devastating'
            ),
            
            'grape': CropValue(
                crop='Grape',
                typical_yield_tons_per_ha=20.0,
                premium_price=2000.0,  # Wine grapes premium
                fresh_market_price=1500.0,  # Standard wine
                processing_price=400.0,  # Table/juice
                production_cost_per_ha=4000.0,
                notes='Wine grapes - quality critical for premium prices'
            )
        }
    
    def _initialize_disease_impacts(self) -> Dict[str, DiseaseImpact]:
        """Disease economic impact profiles"""
        return {
            'late_blight_potato': DiseaseImpact(
                disease='Late Blight',
                crop='Potato',
                yield_loss_min=30.0,
                yield_loss_typical=60.0,
                yield_loss_max=100.0,  # Complete loss in 7-14 days!
                quality_downgrade=True,
                downgrade_percentage=40.0,
                grade_reduction='fresh→processing',
                post_harvest_loss=20.0,
                treatment_cost_per_ha=35.0,
                applications_per_season=7,
                notes='CATASTROPHIC: Can destroy entire crop in 2 weeks. $245/ha spray program'
            ),
            
            'banana_panama_tr4': DiseaseImpact(
                disease='Panama Disease TR4',
                crop='Banana',
                yield_loss_min=100.0,
                yield_loss_typical=100.0,
                yield_loss_max=100.0,
                quality_downgrade=False,
                downgrade_percentage=0.0,
                grade_reduction='',
                post_harvest_loss=0.0,
                field_abandonment_years=40,  # Soil infested 40+ years!
                quarantine_restrictions=True,
                treatment_cost_per_ha=0.0,  # NO CURE
                notes='WORST DISEASE: 100% loss + field permanently lost (40+ years). NO TREATMENT'
            ),
            
            'black_sigatoka_banana': DiseaseImpact(
                disease='Black Sigatoka',
                crop='Banana',
                yield_loss_min=35.0,
                yield_loss_typical=42.0,
                yield_loss_max=50.0,
                quality_downgrade=True,
                downgrade_percentage=30.0,
                grade_reduction='premium→standard',
                post_harvest_loss=15.0,
                treatment_cost_per_ha=20.0,
                applications_per_season=35,  # 25-50 applications per year!
                notes='MOST EXPENSIVE: $700/ha spray program (35 applications). Global crisis'
            ),
            
            'coffee_leaf_rust': DiseaseImpact(
                disease='Coffee Leaf Rust',
                crop='Coffee',
                yield_loss_min=50.0,
                yield_loss_typical=70.0,
                yield_loss_max=100.0,
                quality_downgrade=True,
                downgrade_percentage=50.0,
                grade_reduction='specialty→commercial',
                post_harvest_loss=0.0,
                treatment_cost_per_ha=30.0,
                applications_per_season=4,
                notes='EPIDEMIC: 2012-2013 Central America lost 50-80% production'
            ),
            
            'apple_scab': DiseaseImpact(
                disease='Apple Scab',
                crop='Apple',
                yield_loss_min=10.0,
                yield_loss_typical=20.0,
                yield_loss_max=50.0,
                quality_downgrade=True,
                downgrade_percentage=80.0,  # Most fruit downgraded
                grade_reduction='fresh→processing',
                post_harvest_loss=5.0,
                treatment_cost_per_ha=20.0,
                applications_per_season=8,
                notes='COSMETIC: Scabby apples = 75% value loss (processing only)'
            ),
            
            'powdery_mildew_grape': DiseaseImpact(
                disease='Powdery Mildew',
                crop='Grape',
                yield_loss_min=20.0,
                yield_loss_typical=40.0,
                yield_loss_max=60.0,
                quality_downgrade=True,
                downgrade_percentage=60.0,
                grade_reduction='premium→standard',
                post_harvest_loss=10.0,
                treatment_cost_per_ha=25.0,
                applications_per_season=6,
                notes='WINE QUALITY: Reduces sugar, increases off-flavors'
            )
        }
    
    def calculate_impact(
        self,
        crop: str,
        disease: str,
        area_hectares: float,
        disease_severity: float = 1.0,  # 0-1 scale
        treatment_applied: bool = False
    ) -> EconomicAnalysis:
        """
        Calculate complete economic impact
        
        Args:
            crop: Crop type
            disease: Disease name
            area_hectares: Affected area
            disease_severity: 0-1 scale (0=no disease, 1=severe)
            treatment_applied: Whether treatment was used
        """
        # Get crop and disease data
        crop_key = crop.lower()
        disease_key = f"{disease.lower().replace(' ', '_')}_{crop_key}"
        
        if crop_key not in self.crop_values:
            raise ValueError(f"Crop '{crop}' not in database")
        
        crop_data = self.crop_values[crop_key]
        disease_data = self.disease_impacts.get(disease_key)
        
        if not disease_data:
            # Generic disease impact
            disease_data = DiseaseImpact(
                disease=disease,
                crop=crop,
                yield_loss_min=10.0,
                yield_loss_typical=30.0,
                yield_loss_max=60.0,
                quality_downgrade=True,
                downgrade_percentage=30.0,
                grade_reduction='fresh→processing',
                post_harvest_loss=10.0,
                treatment_cost_per_ha=25.0,
                applications_per_season=5
            )
        
        # Baseline production
        baseline_yield = crop_data.typical_yield_tons_per_ha * area_hectares
        baseline_value = baseline_yield * crop_data.fresh_market_price
        
        # Yield loss calculation
        if treatment_applied:
            # Treatment reduces loss by 70-90%
            effective_severity = disease_severity * 0.2  # 80% control
            yield_loss_pct = disease_data.yield_loss_typical * effective_severity
        else:
            yield_loss_pct = disease_data.yield_loss_typical * disease_severity
        
        diseased_yield = baseline_yield * (1.0 - yield_loss_pct / 100.0)
        yield_loss = baseline_yield - diseased_yield
        
        # Quality downgrade calculation
        if disease_data.quality_downgrade:
            # Portion of remaining yield is downgraded
            downgraded_tons = diseased_yield * (disease_data.downgrade_percentage / 100.0)
            fresh_market_tons = diseased_yield - downgraded_tons
            processing_tons = downgraded_tons
            
            # Calculate value with downgrade
            diseased_value = (
                fresh_market_tons * crop_data.fresh_market_price +
                processing_tons * crop_data.processing_price
            )
            
            quality_loss = (downgraded_tons * 
                          (crop_data.fresh_market_price - crop_data.processing_price))
        else:
            fresh_market_tons = diseased_yield
            processing_tons = 0.0
            diseased_value = diseased_yield * crop_data.fresh_market_price
            quality_loss = 0.0
        
        # Post-harvest loss
        post_harvest_loss_tons = diseased_yield * (disease_data.post_harvest_loss / 100.0)
        post_harvest_loss_value = post_harvest_loss_tons * crop_data.fresh_market_price
        
        # Treatment costs
        if treatment_applied:
            treatment_cost = (disease_data.treatment_cost_per_ha * 
                            disease_data.applications_per_season * 
                            area_hectares)
            treatment_applications = disease_data.applications_per_season
        else:
            treatment_cost = 0.0
            treatment_applications = 0
        
        # Calculate losses
        gross_loss = baseline_value - diseased_value + post_harvest_loss_value
        net_loss = gross_loss + treatment_cost
        
        # ROI analysis
        if treatment_applied:
            # Benefit = prevented loss
            untreated_yield_loss = baseline_yield * (disease_data.yield_loss_typical / 100.0)
            treated_yield_loss = yield_loss
            prevented_loss = (untreated_yield_loss - treated_yield_loss) * crop_data.fresh_market_price
            
            treatment_benefit = prevented_loss
            roi_ratio = treatment_benefit / treatment_cost if treatment_cost > 0 else 0.0
        else:
            treatment_benefit = 0.0
            roi_ratio = 0.0
        
        # Recommendations
        recommendations = []
        
        if not treatment_applied and disease_data.treatment_cost_per_ha > 0:
            # Calculate if treatment would be economical
            potential_benefit = gross_loss * 0.7  # Assume 70% protection
            potential_cost = (disease_data.treatment_cost_per_ha * 
                            disease_data.applications_per_season * area_hectares)
            potential_roi = potential_benefit / potential_cost if potential_cost > 0 else 0.0
            
            if potential_roi > 2.0:
                recommendations.append(
                    f"💰 HIGHLY RECOMMENDED: Treatment ROI = {potential_roi:.1f}x "
                    f"(${potential_benefit:,.0f} benefit vs ${potential_cost:,.0f} cost)"
                )
            elif potential_roi > 1.0:
                recommendations.append(
                    f"✅ RECOMMENDED: Treatment ROI = {potential_roi:.1f}x (economically justified)"
                )
        
        if disease_data.field_abandonment_years > 0:
            field_value_loss = (crop_data.fresh_market_price * 
                              crop_data.typical_yield_tons_per_ha * 
                              area_hectares * 
                              disease_data.field_abandonment_years)
            recommendations.append(
                f"🚨 FIELD ABANDONMENT: Soil infested {disease_data.field_abandonment_years} years "
                f"= ${field_value_loss:,.0f} TOTAL LOSS"
            )
        
        if quality_loss > gross_loss * 0.3:
            recommendations.append(
                f"⚠️ QUALITY IMPACT: ${quality_loss:,.0f} lost to quality downgrade "
                f"({quality_loss/gross_loss*100:.0f}% of total loss)"
            )
        
        return EconomicAnalysis(
            crop=crop,
            disease=disease,
            area_hectares=area_hectares,
            baseline_yield_tons=baseline_yield,
            diseased_yield_tons=diseased_yield,
            yield_loss_tons=yield_loss,
            yield_loss_percentage=yield_loss_pct,
            baseline_value_usd=baseline_value,
            diseased_value_usd=diseased_value,
            gross_loss_usd=gross_loss,
            fresh_market_loss_tons=baseline_yield - fresh_market_tons,
            processing_grade_tons=processing_tons,
            quality_loss_usd=quality_loss,
            treatment_cost_usd=treatment_cost,
            treatment_applications=treatment_applications,
            net_loss_usd=net_loss,
            treatment_benefit_usd=treatment_benefit,
            roi_ratio=roi_ratio,
            loss_per_hectare_usd=net_loss / area_hectares if area_hectares > 0 else 0.0,
            recommendations=recommendations,
            notes=disease_data.notes
        )


def main():
    """Example usage"""
    calc = EconomicImpactCalculator()
    
    print("=== AgroPulse Economic Impact Calculator ===")
    print(f"\nCrops in database: {len(calc.crop_values)}")
    print(f"Disease profiles: {len(calc.disease_impacts)}")
    
    print("\n💰 CROP VALUES (per hectare):")
    print("\nCrop      | Yield    | Fresh Market | Processing | Ratio")
    print("-" * 65)
    for crop, data in calc.crop_values.items():
        fm_value = data.typical_yield_tons_per_ha * data.fresh_market_price
        proc_value = data.typical_yield_tons_per_ha * data.processing_price
        ratio = fm_value / proc_value if proc_value > 0 else 0
        print(f"{crop:10} | {data.typical_yield_tons_per_ha:5.1f}t | ${fm_value:10,.0f} | ${proc_value:9,.0f} | {ratio:.1f}x")
    
    print("\n📊 ECONOMIC IMPACT SCENARIOS:")
    
    # Scenario 1: Late blight untreated
    print("\n1. 🥔 LATE BLIGHT (Potato) - UNTREATED")
    analysis1 = calc.calculate_impact('Potato', 'Late Blight', 10.0, 0.8, False)
    print(f"   Area: {analysis1.area_hectares} hectares")
    print(f"   Baseline value: ${analysis1.baseline_value_usd:,.0f}")
    print(f"   Yield loss: {analysis1.yield_loss_tons:.1f}t ({analysis1.yield_loss_percentage:.1f}%)")
    print(f"   Quality loss: ${analysis1.quality_loss_usd:,.0f}")
    print(f"   TOTAL LOSS: ${analysis1.net_loss_usd:,.0f}")
    print(f"   Loss per hectare: ${analysis1.loss_per_hectare_usd:,.0f}/ha")
    for rec in analysis1.recommendations:
        print(f"   {rec}")
    
    # Scenario 2: Late blight treated
    print("\n2. 🥔 LATE BLIGHT (Potato) - TREATED")
    analysis2 = calc.calculate_impact('Potato', 'Late Blight', 10.0, 0.8, True)
    print(f"   Treatment cost: ${analysis2.treatment_cost_usd:,.0f} ({analysis2.treatment_applications} applications)")
    print(f"   Yield loss: {analysis2.yield_loss_tons:.1f}t ({analysis2.yield_loss_percentage:.1f}%)")
    print(f"   Treatment benefit: ${analysis2.treatment_benefit_usd:,.0f}")
    print(f"   ROI: {analysis2.roi_ratio:.1f}x")
    print(f"   Net loss: ${analysis2.net_loss_usd:,.0f}")
    print(f"   💰 Treatment SAVED: ${analysis1.net_loss_usd - analysis2.net_loss_usd:,.0f}")
    
    # Scenario 3: Panama TR4 (catastrophic)
    print("\n3. 🍌 PANAMA DISEASE TR4 (Banana) - NO CURE")
    analysis3 = calc.calculate_impact('Banana', 'Panama Disease TR4', 5.0, 1.0, False)
    print(f"   Yield loss: {analysis3.yield_loss_percentage:.0f}%")
    print(f"   TOTAL LOSS: ${analysis3.net_loss_usd:,.0f}")
    for rec in analysis3.recommendations:
        print(f"   {rec}")
    
    # Scenario 4: Black Sigatoka (expensive treatment)
    print("\n4. 🍌 BLACK SIGATOKA (Banana) - TREATED")
    analysis4 = calc.calculate_impact('Banana', 'Black Sigatoka', 10.0, 0.7, True)
    print(f"   Treatment cost: ${analysis4.treatment_cost_usd:,.0f} ({analysis4.treatment_applications} applications!)")
    print(f"   Yield loss: {analysis4.yield_loss_percentage:.1f}%")
    print(f"   ROI: {analysis4.roi_ratio:.1f}x")
    print(f"   ⚠️ MOST EXPENSIVE disease to manage globally")
    
    print("\n✅ SYSTEM STATUS: Economic calculator operational")


if __name__ == "__main__":
    main()
