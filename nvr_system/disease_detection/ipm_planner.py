"""
Integrated Pest Management (IPM) Planner
Holistic disease management combining cultural, biological, and chemical controls

IPM PRINCIPLES:

1. PREVENTION (First line of defense):
   - Resistant varieties (genetic resistance)
   - Crop rotation (break disease cycles)
   - Sanitation (remove inoculum sources)
   - Site selection (avoid disease-prone areas)
   - Planting date (avoid infection periods)

2. MONITORING (Know your enemy):
   - Scouting (regular field inspection)
   - Traps (spore traps, disease forecasting)
   - Thresholds (economic injury level)
   - Weather monitoring (infection conditions)

3. CULTURAL CONTROLS (Modify environment):
   - Irrigation management (drip vs overhead)
   - Spacing (air circulation)
   - Pruning (remove infected tissue)
   - Mulching (reduce soil splash)
   - Nutrition (avoid excess nitrogen)

4. BIOLOGICAL CONTROLS (Nature's weapons):
   - Trichoderma (antagonistic fungus)
   - Bacillus subtilis (bacterial antagonist)
   - Streptomyces (antibiotic producer)
   - Pseudomonas fluorescens (colonizes roots)

5. CHEMICAL CONTROLS (Last resort, strategic):
   - Threshold-based (only when needed)
   - FRAC rotation (resistance management)
   - Tank mixes (multi-site protection)
   - Timing (protectant before infection)

SUCCESSFUL IPM EXAMPLES:

APPLE SCAB IPM:
- Resistant varieties (Liberty, Enterprise with Vf gene)
- Fall sanitation (remove infected leaves = 50% reduction)
- Weather-based sprays (Mills table infection periods)
- FRAC rotation (M4 captan + FRAC 3 DMI)
- Result: 60-80% fungicide reduction possible

TOMATO LATE BLIGHT IPM:
- Resistant varieties (Mountain Merit, Iron Lady Ph-2/Ph-3)
- Crop rotation (3-year minimum)
- Drip irrigation (avoid leaf wetness)
- Weather forecasting (BlightCast model)
- Protectant fungicides (mancozeb before infection)
- Result: Epidemic prevention vs reactive spraying

COFFEE LEAF RUST IPM:
- Resistant varieties (Castillo, Lempira SH genes)
- Shade management (reduce humidity)
- Pruning (increase air circulation)
- Copper sprays (protectant)
- Nutrition (balanced N-K, avoid excess nitrogen)
- Result: Sustainable production without epidemic

Author: AgroPulse AI Team
Version: 1.0.0
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Tuple, Optional, Set
from datetime import datetime, timedelta


class ControlType(Enum):
    """Type of disease control measure"""
    CULTURAL = "cultural"
    BIOLOGICAL = "biological"
    CHEMICAL = "chemical"
    GENETIC = "genetic"
    REGULATORY = "regulatory"


class EffectivenessLevel(Enum):
    """Effectiveness of control measure"""
    EXCELLENT = "excellent"  # >80% control
    GOOD = "good"  # 60-80% control
    MODERATE = "moderate"  # 40-60% control
    FAIR = "fair"  # 20-40% control
    POOR = "poor"  # <20% control


class ImplementationDifficulty(Enum):
    """Difficulty to implement"""
    EASY = "easy"
    MODERATE = "moderate"
    DIFFICULT = "difficult"


@dataclass
class ControlMeasure:
    """Individual disease control measure"""
    name: str
    control_type: ControlType
    
    # Effectiveness
    effectiveness: EffectivenessLevel
    effectiveness_percentage: float  # 0-100
    
    # Implementation
    difficulty: ImplementationDifficulty
    cost_per_ha: float
    labor_hours_per_ha: float
    
    # Timing
    timing: str  # When to implement
    frequency: str  # How often
    
    # Applicability
    target_diseases: List[str]
    compatible_crops: List[str]
    
    # Sustainability
    environmental_impact: str  # low, medium, high
    resistance_risk: str  # none, low, medium, high
    
    # Organic
    organic_approved: bool = False
    
    notes: str = ""


@dataclass
class BiocontrolAgent:
    """Biological control organism"""
    name: str
    organism: str
    
    # Activity
    mode_of_action: str
    target_pathogens: List[str]
    
    # Effectiveness
    efficacy: str  # excellent, good, fair
    efficacy_percentage: float
    
    # Application
    application_method: str
    application_timing: str
    cost_per_ha: float
    
    # Environmental requirements
    temperature_range: Tuple[float, float]
    humidity_requirement: str
    
    organic_approved: bool = True
    
    notes: str = ""


@dataclass
class IPMStrategy:
    """Complete IPM program"""
    crop: str
    disease: str
    strategy_name: str
    
    # Control measures by type
    genetic_controls: List[str]
    cultural_controls: List[str]
    biological_controls: List[str]
    chemical_controls: List[str]
    
    # Economics
    total_cost_per_ha: float
    chemical_reduction: float  # % reduction vs conventional
    
    # Expected results
    expected_control: str  # excellent, good, fair
    sustainability_rating: str  # high, medium, low
    
    # Implementation timeline
    preparation_time: str
    
    notes: str = ""


@dataclass
class IPMRecommendation:
    """IPM recommendation for specific situation"""
    crop: str
    disease: str
    
    # Prioritized measures
    priority_1_prevention: List[str]
    priority_2_monitoring: List[str]
    priority_3_cultural: List[str]
    priority_4_biological: List[str]
    priority_5_chemical: List[str]
    
    # Economic analysis
    implementation_cost: float
    expected_savings: float
    roi_ratio: float
    
    # Sustainability
    chemical_reduction_pct: float
    environmental_benefit: str
    
    notes: str = ""


class IPMPlanner:
    """
    Integrated Pest Management planner
    
    FEATURES:
    - Multi-tactic disease control
    - Chemical reduction strategies
    - Biocontrol integration
    - Threshold-based interventions
    """
    
    def __init__(self):
        self.control_measures = self._initialize_control_measures()
        self.biocontrol_agents = self._initialize_biocontrol_agents()
        self.ipm_strategies = self._initialize_ipm_strategies()
    
    def _initialize_control_measures(self) -> Dict[str, ControlMeasure]:
        """Comprehensive control measures database"""
        return {
            'resistant_variety': ControlMeasure(
                name='Resistant Variety Selection',
                control_type=ControlType.GENETIC,
                effectiveness=EffectivenessLevel.EXCELLENT,
                effectiveness_percentage=70.0,
                difficulty=ImplementationDifficulty.EASY,
                cost_per_ha=50.0,  # Slightly higher seed cost
                labor_hours_per_ha=0.0,
                timing='Pre-planting',
                frequency='Once per season',
                target_diseases=['All'],
                compatible_crops=['All'],
                environmental_impact='low',
                resistance_risk='medium',
                organic_approved=True,
                notes='MOST EFFECTIVE: Genetic resistance = foundation of IPM'
            ),
            
            'crop_rotation': ControlMeasure(
                name='Crop Rotation',
                control_type=ControlType.CULTURAL,
                effectiveness=EffectivenessLevel.GOOD,
                effectiveness_percentage=50.0,
                difficulty=ImplementationDifficulty.MODERATE,
                cost_per_ha=0.0,  # No direct cost
                labor_hours_per_ha=0.0,
                timing='Between seasons',
                frequency='Annual',
                target_diseases=[
                    'Fusarium wilt', 'Verticillium wilt', 
                    'Early blight', 'Late blight', 'White rot'
                ],
                compatible_crops=['All annual crops'],
                environmental_impact='low',
                resistance_risk='none',
                organic_approved=True,
                notes='Break disease cycles. 3-4 year rotation optimal for soilborne diseases'
            ),
            
            'sanitation': ControlMeasure(
                name='Field Sanitation',
                control_type=ControlType.CULTURAL,
                effectiveness=EffectivenessLevel.GOOD,
                effectiveness_percentage=50.0,
                difficulty=ImplementationDifficulty.EASY,
                cost_per_ha=30.0,
                labor_hours_per_ha=4.0,
                timing='Post-harvest, during season',
                frequency='Continuous',
                target_diseases=[
                    'Apple scab', 'Brown rot', 'Anthracnose',
                    'Botrytis', 'Fire blight'
                ],
                compatible_crops=['All crops'],
                environmental_impact='low',
                resistance_risk='none',
                organic_approved=True,
                notes='Remove infected tissue = remove inoculum. Apple scab: Fall leaf removal = 50% reduction'
            ),
            
            'drip_irrigation': ControlMeasure(
                name='Drip Irrigation',
                control_type=ControlType.CULTURAL,
                effectiveness=EffectivenessLevel.EXCELLENT,
                effectiveness_percentage=60.0,
                difficulty=ImplementationDifficulty.MODERATE,
                cost_per_ha=800.0,  # Infrastructure investment
                labor_hours_per_ha=2.0,
                timing='Pre-planting installation',
                frequency='Season-long',
                target_diseases=[
                    'Late blight', 'Early blight', 'Downy mildew',
                    'Bacterial spot', 'Anthracnose'
                ],
                compatible_crops=['Tomato', 'Pepper', 'Cucumber', 'Strawberry'],
                environmental_impact='low',
                resistance_risk='none',
                organic_approved=True,
                notes='Avoid leaf wetness = prevent infection. Overhead irrigation = disease promoter'
            ),
            
            'pruning_spacing': ControlMeasure(
                name='Pruning and Spacing',
                control_type=ControlType.CULTURAL,
                effectiveness=EffectivenessLevel.MODERATE,
                effectiveness_percentage=30.0,
                difficulty=ImplementationDifficulty.EASY,
                cost_per_ha=50.0,
                labor_hours_per_ha=8.0,
                timing='During season',
                frequency='Regular',
                target_diseases=[
                    'Botrytis', 'Powdery mildew', 'Downy mildew',
                    'Fire blight', 'Anthracnose'
                ],
                compatible_crops=['All crops'],
                environmental_impact='low',
                resistance_risk='none',
                organic_approved=True,
                notes='Increase air circulation = faster drying = less disease'
            ),
            
            'mulching': ControlMeasure(
                name='Mulching',
                control_type=ControlType.CULTURAL,
                effectiveness=EffectivenessLevel.MODERATE,
                effectiveness_percentage=40.0,
                difficulty=ImplementationDifficulty.EASY,
                cost_per_ha=200.0,
                labor_hours_per_ha=6.0,
                timing='Pre-planting or early season',
                frequency='Once per season',
                target_diseases=[
                    'Early blight', 'Anthracnose', 'Septoria',
                    'Bacterial spot'
                ],
                compatible_crops=['Tomato', 'Pepper', 'Strawberry', 'Cucumber'],
                environmental_impact='low',
                resistance_risk='none',
                organic_approved=True,
                notes='Reduce soil splash = reduce foliar disease. Plastic or organic mulch'
            ),
            
            'balanced_nutrition': ControlMeasure(
                name='Balanced Nutrition',
                control_type=ControlType.CULTURAL,
                effectiveness=EffectivenessLevel.MODERATE,
                effectiveness_percentage=25.0,
                difficulty=ImplementationDifficulty.EASY,
                cost_per_ha=100.0,
                labor_hours_per_ha=1.0,
                timing='Throughout season',
                frequency='Regular',
                target_diseases=['All'],
                compatible_crops=['All crops'],
                environmental_impact='medium',
                resistance_risk='none',
                organic_approved=True,
                notes='Excess N = succulent growth = disease susceptible. Balance N-P-K-Ca'
            )
        }
    
    def _initialize_biocontrol_agents(self) -> Dict[str, BiocontrolAgent]:
        """Biological control agents database"""
        return {
            'trichoderma': BiocontrolAgent(
                name='Trichoderma harzianum',
                organism='Fungus',
                mode_of_action='Competition, mycoparasitism, antibiosis',
                target_pathogens=[
                    'Botrytis', 'Fusarium', 'Pythium',
                    'Rhizoctonia', 'Sclerotinia'
                ],
                efficacy='good',
                efficacy_percentage=40.0,
                application_method='Soil drench, seed treatment',
                application_timing='Pre-planting, transplanting',
                cost_per_ha=60.0,
                temperature_range=(15.0, 35.0),
                humidity_requirement='moderate',
                notes='MOST USED biocontrol. Colonizes roots, antagonizes pathogens'
            ),
            
            'bacillus_subtilis': BiocontrolAgent(
                name='Bacillus subtilis',
                organism='Bacterium',
                mode_of_action='Antibiosis, competition, induced resistance',
                target_pathogens=[
                    'Powdery mildew', 'Botrytis', 'Downy mildew',
                    'Early blight', 'Late blight'
                ],
                efficacy='fair',
                efficacy_percentage=35.0,
                application_method='Foliar spray',
                application_timing='Protectant before infection',
                cost_per_ha=35.0,
                temperature_range=(10.0, 40.0),
                humidity_requirement='any',
                notes='Produces lipopeptides (surfactin, iturin). Systemic resistance induction'
            ),
            
            'streptomyces': BiocontrolAgent(
                name='Streptomyces griseoviridis',
                organism='Actinomycete',
                mode_of_action='Antibiosis, competition',
                target_pathogens=[
                    'Fusarium', 'Alternaria', 'Botrytis',
                    'Phomopsis', 'Pythium'
                ],
                efficacy='good',
                efficacy_percentage=45.0,
                application_method='Soil incorporation, seed treatment',
                application_timing='Pre-planting',
                cost_per_ha=70.0,
                temperature_range=(10.0, 30.0),
                humidity_requirement='moderate',
                notes='Produces antibiotics. Good soil colonizer'
            ),
            
            'pseudomonas': BiocontrolAgent(
                name='Pseudomonas fluorescens',
                organism='Bacterium',
                mode_of_action='Competition, siderophore production, induced resistance',
                target_pathogens=[
                    'Pythium', 'Fusarium', 'Rhizoctonia',
                    'Take-all', 'Damping-off'
                ],
                efficacy='good',
                efficacy_percentage=50.0,
                application_method='Seed treatment, soil drench',
                application_timing='Pre-planting',
                cost_per_ha=55.0,
                temperature_range=(5.0, 35.0),
                humidity_requirement='moderate',
                notes='Produces siderophores (iron chelators). Excellent root colonizer'
            )
        }
    
    def _initialize_ipm_strategies(self) -> Dict[str, IPMStrategy]:
        """Pre-designed IPM strategies"""
        return {
            'tomato_late_blight_ipm': IPMStrategy(
                crop='Tomato',
                disease='Late Blight',
                strategy_name='Late Blight IPM Program',
                genetic_controls=['Mountain Merit or Iron Lady (Ph-2/Ph-3 genes)'],
                cultural_controls=[
                    'Drip irrigation (avoid leaf wetness)',
                    'Wide spacing (air circulation)',
                    'Remove volunteers (destroy inoculum)',
                    'Avoid overhead irrigation'
                ],
                biological_controls=['Bacillus subtilis (protectant)'],
                chemical_controls=[
                    'Mancozeb (FRAC M3) protectant',
                    'Chlorothalonil (FRAC M5) protectant',
                    'Weather-based sprays only'
                ],
                total_cost_per_ha=350.0,
                chemical_reduction=60.0,
                expected_control='excellent',
                sustainability_rating='high',
                preparation_time='1 season',
                notes='Resistant varieties + cultural controls = 60% fungicide reduction'
            ),
            
            'apple_scab_ipm': IPMStrategy(
                crop='Apple',
                disease='Apple Scab',
                strategy_name='Apple Scab IPM Program',
                genetic_controls=['Liberty or Enterprise (Vf gene)'],
                cultural_controls=[
                    'Fall leaf removal (50% inoculum reduction)',
                    'Prune for air circulation',
                    'Avoid overhead irrigation'
                ],
                biological_controls=['Trichoderma (soil application)'],
                chemical_controls=[
                    'Mills table weather-based sprays',
                    'Captan (FRAC M4) protectant',
                    'Myclobutanil (FRAC 3) curative'
                ],
                total_cost_per_ha=280.0,
                chemical_reduction=70.0,
                expected_control='excellent',
                sustainability_rating='high',
                preparation_time='1-2 seasons',
                notes='Vf varieties + sanitation = minimal fungicides. Mills table = precise timing'
            ),
            
            'coffee_rust_ipm': IPMStrategy(
                crop='Coffee',
                disease='Coffee Leaf Rust',
                strategy_name='Coffee Rust IPM Program',
                genetic_controls=['Castillo or Lempira (SH3/SH5 genes)'],
                cultural_controls=[
                    'Shade management (reduce humidity)',
                    'Pruning (air circulation)',
                    'Balanced nutrition (avoid excess N)',
                    'Weed control (reduce humidity)'
                ],
                biological_controls=['Trichoderma (soil drench)'],
                chemical_controls=[
                    'Copper hydroxide (protectant)',
                    'Threshold-based applications only'
                ],
                total_cost_per_ha=200.0,
                chemical_reduction=50.0,
                expected_control='good',
                sustainability_rating='high',
                preparation_time='3-5 years (variety transition)',
                notes='SH gene varieties revolutionized Colombian coffee. Sustainable long-term'
            )
        }
    
    def create_ipm_plan(
        self,
        crop: str,
        disease: str,
        budget_per_ha: float,
        organic: bool = False
    ) -> IPMRecommendation:
        """Create customized IPM plan"""
        
        # Priority 1: Genetic resistance (always recommend if available)
        prevention = ['Select resistant variety (highest priority!)']
        
        # Priority 2: Monitoring
        monitoring = [
            'Weekly scouting (disease detection)',
            'Weather monitoring (infection conditions)',
            'Set thresholds (spray only when needed)'
        ]
        
        # Priority 3: Cultural controls (filter by crop/disease/budget)
        cultural = []
        for name, measure in self.control_measures.items():
            if measure.control_type == ControlType.CULTURAL:
                if disease in measure.target_diseases or 'All' in measure.target_diseases:
                    if crop in measure.compatible_crops or 'All crops' in measure.compatible_crops:
                        if measure.cost_per_ha <= budget_per_ha * 0.3:  # Max 30% of budget
                            if not organic or measure.organic_approved:
                                cultural.append(f"{measure.name} (${measure.cost_per_ha}/ha)")
        
        # Priority 4: Biological controls
        biological = []
        for name, agent in self.biocontrol_agents.items():
            if disease in agent.target_pathogens:
                if agent.cost_per_ha <= budget_per_ha * 0.2:  # Max 20% of budget
                    biological.append(f"{agent.name} ({agent.efficacy}, ${agent.cost_per_ha}/ha)")
        
        # Priority 5: Chemical controls (last resort, threshold-based)
        chemical = [
            'FRAC code rotation (resistance management)',
            'Multi-site protectants (mancozeb, copper)',
            'Weather-based applications only',
            'Tank mix single-site + multi-site'
        ]
        
        if organic:
            chemical = [
                'Copper hydroxide (OMRI approved)',
                'Sulfur (OMRI approved)',
                'Bacillus subtilis (biocontrol)',
                'Potassium bicarbonate (powdery mildew)'
            ]
        
        # Economic analysis
        cultural_cost = sum(
            m.cost_per_ha for m in self.control_measures.values()
            if m.control_type == ControlType.CULTURAL and m.cost_per_ha <= budget_per_ha * 0.3
        ) / 2  # Assume implementing half of measures
        
        biocontrol_cost = sum(
            a.cost_per_ha for a in self.biocontrol_agents.values()
            if disease in a.target_pathogens and a.cost_per_ha <= budget_per_ha * 0.2
        ) / 2
        
        chemical_cost = budget_per_ha * 0.3  # Reduced chemical program
        
        implementation_cost = cultural_cost + biocontrol_cost + chemical_cost
        
        # Expected savings vs conventional (reduced fungicide use)
        conventional_cost = budget_per_ha * 0.8  # Conventional = 80% chemical
        expected_savings = conventional_cost - implementation_cost
        
        roi = (expected_savings + implementation_cost * 0.5) / implementation_cost if implementation_cost > 0 else 0.0
        
        chemical_reduction = ((conventional_cost - chemical_cost) / conventional_cost * 100) if conventional_cost > 0 else 0.0
        
        return IPMRecommendation(
            crop=crop,
            disease=disease,
            priority_1_prevention=prevention,
            priority_2_monitoring=monitoring,
            priority_3_cultural=cultural[:5],  # Top 5
            priority_4_biological=biological[:3],  # Top 3
            priority_5_chemical=chemical,
            implementation_cost=implementation_cost,
            expected_savings=expected_savings,
            roi_ratio=roi,
            chemical_reduction_pct=chemical_reduction,
            environmental_benefit='high' if chemical_reduction > 50 else 'moderate',
            notes=f"Budget: ${budget_per_ha}/ha. Organic: {organic}"
        )


def main():
    """Example usage"""
    planner = IPMPlanner()
    
    print("=== AgroPulse IPM Planner ===")
    print(f"\nControl measures: {len(planner.control_measures)}")
    print(f"Biocontrol agents: {len(planner.biocontrol_agents)}")
    print(f"IPM strategies: {len(planner.ipm_strategies)}")
    
    print("\n🌱 IPM PRINCIPLES:")
    print("1. PREVENTION (resistant varieties, sanitation)")
    print("2. MONITORING (scouting, thresholds)")
    print("3. CULTURAL CONTROLS (irrigation, spacing, nutrition)")
    print("4. BIOLOGICAL CONTROLS (Trichoderma, Bacillus)")
    print("5. CHEMICAL CONTROLS (last resort, threshold-based)")
    
    print("\n🦠 BIOCONTROL AGENTS:")
    for name, agent in planner.biocontrol_agents.items():
        print(f"\n{agent.name}:")
        print(f"   Efficacy: {agent.efficacy} ({agent.efficacy_percentage}%)")
        print(f"   Cost: ${agent.cost_per_ha}/ha")
        print(f"   Mode: {agent.mode_of_action}")
    
    print("\n📋 IPM PLAN EXAMPLE:")
    plan = planner.create_ipm_plan('Tomato', 'Late Blight', 400.0, False)
    
    print(f"\n🍅 Late Blight IPM Plan (${plan.implementation_cost:.0f}/ha)")
    print(f"\n1️⃣ PREVENTION:")
    for item in plan.priority_1_prevention:
        print(f"   ✅ {item}")
    
    print(f"\n2️⃣ MONITORING:")
    for item in plan.priority_2_monitoring:
        print(f"   👁️ {item}")
    
    print(f"\n3️⃣ CULTURAL CONTROLS:")
    for item in plan.priority_3_cultural:
        print(f"   🌿 {item}")
    
    print(f"\n4️⃣ BIOLOGICAL CONTROLS:")
    for item in plan.priority_4_biological:
        print(f"   🦠 {item}")
    
    print(f"\n5️⃣ CHEMICAL CONTROLS:")
    for item in plan.priority_5_chemical:
        print(f"   💊 {item}")
    
    print(f"\n💰 ECONOMICS:")
    print(f"   Implementation cost: ${plan.implementation_cost:.0f}/ha")
    print(f"   Expected savings: ${plan.expected_savings:.0f}/ha")
    print(f"   ROI: {plan.roi_ratio:.1f}x")
    print(f"   Chemical reduction: {plan.chemical_reduction_pct:.0f}%")
    print(f"   Environmental benefit: {plan.environmental_benefit}")
    
    print("\n✅ SYSTEM STATUS: IPM planner operational")


if __name__ == "__main__":
    main()
