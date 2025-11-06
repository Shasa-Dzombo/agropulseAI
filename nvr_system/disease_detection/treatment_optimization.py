"""
Treatment Optimization System
FRAC code rotation and fungicide resistance management

FRAC CODES (Fungicide Resistance Action Committee):

SINGLE-SITE MODES OF ACTION (HIGH RESISTANCE RISK):
- FRAC 1 (MBC): Thiophanate-methyl, benomyl - WIDESPREAD RESISTANCE
- FRAC 3 (DMI): Propiconazole, tebuconazole - RESISTANCE DOCUMENTED
- FRAC 7 (SDHI): Boscalid, fluxapyroxad - RESISTANCE EMERGING
- FRAC 11 (QoI): Azoxystrobin, pyraclostrobin - SEVERE RESISTANCE
- FRAC 21 (QiI): Cyazofamid - RESISTANCE REPORTED

MULTI-SITE MODES OF ACTION (LOW RESISTANCE RISK):
- FRAC M1 (Inorganic): Copper, sulfur - DURABLE
- FRAC M2 (Inorganic): Sulfur - VERY DURABLE
- FRAC M3 (Dithiocarbamates): Mancozeb, chlorothalonil - DURABLE
- FRAC M4 (Phthalimides): Captan, folpet - DURABLE

RESISTANCE HISTORY:
- Benomyl (FRAC 1): Deployed 1968, resistance 1972 (4 years!)
- QoI strobilurins (FRAC 11): Deployed 1996, resistance 2000s (widespread)
- DMI triazoles (FRAC 3): Resistance documented but slower
- Copper: Used since 1882 (Bordeaux mixture), resistance rare but documented

ROTATION STRATEGY:
- NEVER use same FRAC group consecutively
- Mix high-risk with low-risk modes of action
- Tank mix single-site + multi-site
- Limit single-site applications per season
- Alternate FRAC groups each spray

RESISTANCE MANAGEMENT:
- Labeled rates (don't under-dose)
- Spray coverage critical
- Protectant before infection
- Limit FRAC 11 to 2-3 applications/season
- Monitor efficacy (resistance early warning)

BACTERICIDES:
- Copper compounds (durable, some resistance)
- Streptomycin (WIDESPREAD RESISTANCE - Erwinia, Xanthomonas)
- Kasugamycin (alternative to streptomycin)
- Oxytetracycline (limited use, resistance risk)

ORGANIC OPTIONS:
- Copper (Bordeaux mixture, copper hydroxide)
- Sulfur (powdery mildew only)
- Bacillus subtilis (biocontrol)
- Trichoderma (biocontrol)
- Potassium bicarbonate (powdery mildew)

Author: AgroPulse AI Team
Version: 1.0.0
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Tuple, Optional, Set
from datetime import datetime, timedelta


class FRACGroup(Enum):
    """FRAC fungicide groups"""
    # Single-site (HIGH RESISTANCE RISK)
    FRAC_1_MBC = "1_MBC"  # Benzimidazoles
    FRAC_3_DMI = "3_DMI"  # Demethylation Inhibitors (triazoles)
    FRAC_7_SDHI = "7_SDHI"  # Succinate Dehydrogenase Inhibitors
    FRAC_11_QOI = "11_QoI"  # Quinone outside Inhibitors (strobilurins)
    FRAC_21_QII = "21_QiI"  # Quinone inside Inhibitors
    
    # Multi-site (LOW RESISTANCE RISK)
    FRAC_M1 = "M1"  # Inorganic (copper)
    FRAC_M2 = "M2"  # Inorganic (sulfur)
    FRAC_M3 = "M3"  # Dithiocarbamates (mancozeb)
    FRAC_M4 = "M4"  # Phthalimides (captan)
    
    # Biocontrol
    FRAC_BM = "BM"  # Biological/microbial


class ResistanceRisk(Enum):
    """Resistance development risk"""
    EXTREME = "extreme"  # Widespread resistance documented
    HIGH = "high"  # Single-site, resistance prone
    MEDIUM = "medium"  # Some resistance documented
    LOW = "low"  # Multi-site, durable
    NONE = "none"  # Biocontrol, no resistance


class ApplicationTiming(Enum):
    """When to apply treatment"""
    PROTECTANT = "protectant"  # Before infection
    EARLY_INFECTION = "early_infection"  # First symptoms
    CURATIVE = "curative"  # Active infection
    ERADICANT = "eradicant"  # Severe infection


@dataclass
class Fungicide:
    """Fungicide information"""
    name: str
    active_ingredient: str
    frac_group: FRACGroup
    
    # Resistance
    resistance_risk: ResistanceRisk
    resistance_documented: bool
    
    # Activity
    mode_of_action: str
    protectant: bool
    curative: bool
    eradicant: bool
    
    # Spectrum
    target_diseases: List[str]
    
    # Application
    max_applications_per_season: Optional[int] = None
    phi_days: int = 0  # Pre-harvest interval
    rei_hours: int = 12  # Re-entry interval
    
    # Efficacy
    efficacy_rating: str = "good"  # excellent, good, fair, poor
    
    # Cost
    cost_per_hectare_usd: Optional[float] = None
    
    # Organic
    organic_approved: bool = False
    
    notes: str = ""


@dataclass
class BacterialTreatment:
    """Bactericide information"""
    name: str
    active_ingredient: str
    
    # Resistance
    resistance_risk: ResistanceRisk
    resistance_documented: bool
    
    # Spectrum
    target_pathogens: List[str]
    
    # Application
    phi_days: int = 0
    rei_hours: int = 12
    
    # Efficacy
    efficacy_rating: str = "good"
    
    organic_approved: bool = False
    
    notes: str = ""


@dataclass
class SprayProgram:
    """Complete spray schedule"""
    crop: str
    disease: str
    program_name: str
    
    applications: List[Tuple[str, str, int]]  # (fungicide, timing, days_from_start)
    
    # Cost analysis
    total_cost_usd_per_ha: float
    total_applications: int
    
    # Resistance management
    frac_rotation_compliant: bool
    single_site_applications: int
    
    # Expected results
    expected_control: str  # excellent, good, fair
    
    notes: str = ""


@dataclass
class TreatmentRecommendation:
    """Treatment recommendation"""
    disease: str
    crop: str
    
    # Primary recommendation
    primary_treatment: str
    frac_code: str
    
    # Alternative options
    alternatives: List[str]
    
    # Rotation partners
    rotation_options: List[str]
    
    # Timing
    application_timing: ApplicationTiming
    
    # Resistance management
    max_uses_per_season: int
    tank_mix_partner: Optional[str] = None
    
    # Economic
    cost_per_hectare: float
    expected_yield_protection: float  # percentage
    roi_ratio: float  # benefit/cost
    
    # Action required
    spray_urgency: str  # critical, high, moderate, low
    
    notes: str = ""


class TreatmentOptimizer:
    """
    Treatment optimization system
    
    FEATURES:
    - FRAC code rotation
    - Resistance management
    - Cost optimization
    - ROI analysis
    """
    
    def __init__(self):
        self.fungicides = self._initialize_fungicide_database()
        self.bactericides = self._initialize_bactericide_database()
        self.spray_programs = self._initialize_spray_programs()
    
    def _initialize_fungicide_database(self) -> Dict[str, Fungicide]:
        """Comprehensive fungicide database"""
        return {
            'azoxystrobin': Fungicide(
                name='Azoxystrobin',
                active_ingredient='Azoxystrobin',
                frac_group=FRACGroup.FRAC_11_QOI,
                resistance_risk=ResistanceRisk.EXTREME,
                resistance_documented=True,
                mode_of_action='Mitochondrial respiration inhibitor (Complex III)',
                protectant=True,
                curative=True,
                eradicant=False,
                target_diseases=[
                    'Late blight', 'Downy mildew', 'Powdery mildew',
                    'Anthracnose', 'Leaf spots', 'Rusts'
                ],
                max_applications_per_season=2,  # CRITICAL: Limit to 2-3 max
                phi_days=0,
                cost_per_hectare_usd=45.0,
                efficacy_rating='excellent',
                notes='FRAC 11 - SEVERE RESISTANCE worldwide. Limit use, rotate with other FRAC groups'
            ),
            
            'propiconazole': Fungicide(
                name='Propiconazole',
                active_ingredient='Propiconazole',
                frac_group=FRACGroup.FRAC_3_DMI,
                resistance_risk=ResistanceRisk.HIGH,
                resistance_documented=True,
                mode_of_action='C14-demethylase inhibitor (sterol biosynthesis)',
                protectant=True,
                curative=True,
                eradicant=True,
                target_diseases=[
                    'Powdery mildew', 'Rusts', 'Leaf spots',
                    'Scab', 'Brown rot'
                ],
                max_applications_per_season=4,
                phi_days=14,
                cost_per_hectare_usd=30.0,
                efficacy_rating='good',
                notes='FRAC 3 DMI - Resistance documented but manageable. Good curative activity'
            ),
            
            'mancozeb': Fungicide(
                name='Mancozeb',
                active_ingredient='Mancozeb',
                frac_group=FRACGroup.FRAC_M3,
                resistance_risk=ResistanceRisk.LOW,
                resistance_documented=False,
                mode_of_action='Multi-site contact fungicide',
                protectant=True,
                curative=False,
                eradicant=False,
                target_diseases=[
                    'Late blight', 'Early blight', 'Downy mildew',
                    'Anthracnose', 'Leaf spots'
                ],
                max_applications_per_season=None,  # No limit (multi-site)
                phi_days=7,
                cost_per_hectare_usd=15.0,
                efficacy_rating='good',
                notes='FRAC M3 - DURABLE. Multi-site, no resistance. Protectant only (apply before infection)'
            ),
            
            'copper_hydroxide': Fungicide(
                name='Copper Hydroxide',
                active_ingredient='Copper hydroxide',
                frac_group=FRACGroup.FRAC_M1,
                resistance_risk=ResistanceRisk.LOW,
                resistance_documented=False,
                mode_of_action='Multi-site contact (protein inactivation)',
                protectant=True,
                curative=False,
                eradicant=False,
                target_diseases=[
                    'Bacterial spot', 'Bacterial canker', 'Downy mildew',
                    'Late blight', 'Anthracnose', 'Peacock spot'
                ],
                phi_days=0,
                cost_per_hectare_usd=20.0,
                efficacy_rating='good',
                organic_approved=True,
                notes='FRAC M1 - HISTORIC (1882 Bordeaux). Bactericide + fungicide. Phytotoxicity risk in hot weather'
            ),
            
            'sulfur': Fungicide(
                name='Sulfur',
                active_ingredient='Sulfur',
                frac_group=FRACGroup.FRAC_M2,
                resistance_risk=ResistanceRisk.NONE,
                resistance_documented=False,
                mode_of_action='Multi-site contact',
                protectant=True,
                curative=False,
                eradicant=False,
                target_diseases=['Powdery mildew', 'Rusts', 'Scab'],
                phi_days=0,
                cost_per_hectare_usd=10.0,
                efficacy_rating='excellent',
                organic_approved=True,
                notes='FRAC M2 - ANCIENT (known to Greeks/Romans). Powdery mildew only. Phytotoxic >32°C'
            ),
            
            'captan': Fungicide(
                name='Captan',
                active_ingredient='Captan',
                frac_group=FRACGroup.FRAC_M4,
                resistance_risk=ResistanceRisk.LOW,
                resistance_documented=False,
                mode_of_action='Multi-site contact',
                protectant=True,
                curative=False,
                eradicant=False,
                target_diseases=[
                    'Apple scab', 'Brown rot', 'Anthracnose',
                    'Botrytis', 'Downy mildew'
                ],
                phi_days=0,
                cost_per_hectare_usd=18.0,
                efficacy_rating='good',
                notes='FRAC M4 - DURABLE multi-site. Excellent for stone fruits'
            ),
            
            'bacillus_subtilis': Fungicide(
                name='Bacillus subtilis',
                active_ingredient='Bacillus subtilis strain QST 713',
                frac_group=FRACGroup.FRAC_BM,
                resistance_risk=ResistanceRisk.NONE,
                resistance_documented=False,
                mode_of_action='Biocontrol (competition, antibiosis)',
                protectant=True,
                curative=False,
                eradicant=False,
                target_diseases=[
                    'Powdery mildew', 'Botrytis', 'Downy mildew',
                    'Early blight', 'Late blight'
                ],
                phi_days=0,
                cost_per_hectare_usd=35.0,
                efficacy_rating='fair',
                organic_approved=True,
                notes='FRAC BM - BIOCONTROL. No resistance risk. Lower efficacy than synthetic'
            )
        }
    
    def _initialize_bactericide_database(self) -> Dict[str, BacterialTreatment]:
        """Bactericide database"""
        return {
            'copper_hydroxide': BacterialTreatment(
                name='Copper Hydroxide',
                active_ingredient='Copper hydroxide',
                resistance_risk=ResistanceRisk.LOW,
                resistance_documented=True,
                target_pathogens=[
                    'Xanthomonas', 'Pseudomonas', 'Erwinia',
                    'Ralstonia', 'Clavibacter'
                ],
                phi_days=0,
                efficacy_rating='good',
                organic_approved=True,
                notes='Standard bactericide. Resistance documented but rare. Phytotoxic >32°C'
            ),
            
            'streptomycin': BacterialTreatment(
                name='Streptomycin',
                active_ingredient='Streptomycin sulfate',
                resistance_risk=ResistanceRisk.EXTREME,
                resistance_documented=True,
                target_pathogens=['Erwinia', 'Xanthomonas', 'Pseudomonas'],
                phi_days=21,
                efficacy_rating='poor',
                notes='WIDESPREAD RESISTANCE. Limited effectiveness. Avoid if possible'
            ),
            
            'kasugamycin': BacterialTreatment(
                name='Kasugamycin',
                active_ingredient='Kasugamycin',
                resistance_risk=ResistanceRisk.MEDIUM,
                resistance_documented=False,
                target_pathogens=['Pseudomonas', 'Xanthomonas'],
                phi_days=0,
                efficacy_rating='good',
                notes='Alternative to streptomycin. Better resistance profile'
            )
        }
    
    def _initialize_spray_programs(self) -> Dict[str, SprayProgram]:
        """Pre-designed spray programs"""
        return {
            'potato_late_blight_intensive': SprayProgram(
                crop='Potato',
                disease='Late blight',
                program_name='Intensive Late Blight Program',
                applications=[
                    ('mancozeb', 'protectant', 0),
                    ('mancozeb', 'protectant', 7),
                    ('azoxystrobin', 'protectant', 14),
                    ('mancozeb', 'protectant', 21),
                    ('propiconazole', 'curative', 28),
                    ('mancozeb', 'protectant', 35),
                    ('mancozeb', 'protectant', 42)
                ],
                total_cost_usd_per_ha=180.0,
                total_applications=7,
                frac_rotation_compliant=True,
                single_site_applications=2,
                expected_control='excellent',
                notes='FRAC rotation: M3 → M3 → 11 → M3 → 3 → M3 → M3. Limited single-site to 2 applications'
            ),
            
            'apple_scab_organic': SprayProgram(
                crop='Apple',
                disease='Apple scab',
                program_name='Organic Apple Scab Program',
                applications=[
                    ('copper_hydroxide', 'protectant', 0),
                    ('sulfur', 'protectant', 7),
                    ('copper_hydroxide', 'protectant', 14),
                    ('captan', 'protectant', 21),
                    ('sulfur', 'protectant', 28)
                ],
                total_cost_usd_per_ha=90.0,
                total_applications=5,
                frac_rotation_compliant=True,
                single_site_applications=0,
                expected_control='good',
                notes='All multi-site FRAC codes. Organic approved. No resistance risk'
            )
        }
    
    def recommend_treatment(
        self, 
        disease: str, 
        crop: str, 
        infection_stage: ApplicationTiming,
        previous_applications: List[str] = None
    ) -> TreatmentRecommendation:
        """
        Recommend optimal treatment with FRAC rotation
        """
        if previous_applications is None:
            previous_applications = []
        
        # Get previous FRAC codes used
        previous_frac_codes = set()
        for app in previous_applications:
            if app in self.fungicides:
                previous_frac_codes.add(self.fungicides[app].frac_group)
        
        # Find suitable fungicides
        candidates = []
        for name, fungicide in self.fungicides.items():
            # Check if appropriate for timing
            if infection_stage == ApplicationTiming.PROTECTANT and not fungicide.protectant:
                continue
            if infection_stage == ApplicationTiming.CURATIVE and not fungicide.curative:
                continue
            if infection_stage == ApplicationTiming.ERADICANT and not fungicide.eradicant:
                continue
            
            # Check if targets disease
            if disease not in fungicide.target_diseases:
                continue
            
            # Score based on resistance and rotation
            score = 0.0
            
            # Prefer not recently used FRAC code
            if fungicide.frac_group not in previous_frac_codes:
                score += 10.0
            
            # Prefer low resistance risk
            if fungicide.resistance_risk == ResistanceRisk.LOW:
                score += 5.0
            elif fungicide.resistance_risk == ResistanceRisk.EXTREME:
                score -= 5.0
            
            # Prefer high efficacy
            if fungicide.efficacy_rating == 'excellent':
                score += 3.0
            
            # Prefer lower cost
            if fungicide.cost_per_hectare_usd:
                score += (50.0 - fungicide.cost_per_hectare_usd) / 10.0
            
            candidates.append((score, name, fungicide))
        
        # Sort by score
        candidates.sort(reverse=True, key=lambda x: x[0])
        
        if not candidates:
            return None
        
        # Primary recommendation
        _, primary_name, primary = candidates[0]
        
        # Alternatives
        alternatives = [name for _, name, _ in candidates[1:4]]
        
        # Rotation partners (different FRAC codes)
        rotation_options = [
            name for _, name, f in candidates 
            if f.frac_group != primary.frac_group
        ][:3]
        
        # Tank mix partner (multi-site)
        tank_mix = None
        for name, fungicide in self.fungicides.items():
            if fungicide.frac_group.value.startswith('M') and name != primary_name:
                tank_mix = name
                break
        
        # Economic analysis
        yield_protection = 0.7  # 70% yield protection estimate
        crop_value_per_ha = 5000.0  # $5000/ha estimate
        benefit = crop_value_per_ha * yield_protection
        cost = primary.cost_per_hectare_usd or 30.0
        roi = benefit / cost if cost > 0 else 0.0
        
        return TreatmentRecommendation(
            disease=disease,
            crop=crop,
            primary_treatment=primary_name,
            frac_code=primary.frac_group.value,
            alternatives=alternatives,
            rotation_options=rotation_options,
            application_timing=infection_stage,
            max_uses_per_season=primary.max_applications_per_season or 999,
            tank_mix_partner=tank_mix,
            cost_per_hectare=cost,
            expected_yield_protection=yield_protection * 100,
            roi_ratio=roi,
            spray_urgency='critical' if infection_stage == ApplicationTiming.CURATIVE else 'moderate',
            notes=primary.notes
        )
    
    def validate_frac_rotation(self, spray_sequence: List[str]) -> Dict:
        """Validate FRAC code rotation compliance"""
        issues = []
        frac_sequence = []
        
        for i, spray in enumerate(spray_sequence):
            if spray not in self.fungicides:
                continue
            
            frac_code = self.fungicides[spray].frac_group
            frac_sequence.append(frac_code)
            
            # Check consecutive same FRAC code
            if i > 0 and frac_code == frac_sequence[i-1]:
                if not frac_code.value.startswith('M'):  # Multi-site OK
                    issues.append(f"⚠️ Consecutive {frac_code.value} at positions {i} and {i+1}")
        
        # Count single-site applications
        single_site_count = {}
        for spray in spray_sequence:
            if spray in self.fungicides:
                f = self.fungicides[spray]
                if not f.frac_group.value.startswith('M'):
                    single_site_count[f.frac_group] = single_site_count.get(f.frac_group, 0) + 1
        
        # Check application limits
        for spray in spray_sequence:
            if spray in self.fungicides:
                f = self.fungicides[spray]
                if f.max_applications_per_season:
                    count = spray_sequence.count(spray)
                    if count > f.max_applications_per_season:
                        issues.append(f"⚠️ {spray}: {count} applications exceeds limit of {f.max_applications_per_season}")
        
        compliant = len(issues) == 0
        
        return {
            'compliant': compliant,
            'issues': issues,
            'frac_sequence': [f.value for f in frac_sequence],
            'single_site_counts': {k.value: v for k, v in single_site_count.items()},
            'total_applications': len(spray_sequence)
        }


def main():
    """Example usage"""
    optimizer = TreatmentOptimizer()
    
    print("=== AgroPulse Treatment Optimization System ===")
    print(f"\nFungicides in database: {len(optimizer.fungicides)}")
    print(f"Bactericides in database: {len(optimizer.bactericides)}")
    print(f"Spray programs: {len(optimizer.spray_programs)}")
    
    print("\n💊 FRAC GROUPS:")
    print("\n⚠️ HIGH RESISTANCE RISK (Single-site):")
    print("   FRAC 11 (QoI Strobilurins): SEVERE resistance worldwide")
    print("   FRAC 3 (DMI Triazoles): Resistance documented")
    print("   FRAC 1 (MBC Benzimidazoles): WIDESPREAD resistance")
    
    print("\n✅ LOW RESISTANCE RISK (Multi-site):")
    print("   FRAC M1 (Copper): DURABLE since 1882")
    print("   FRAC M2 (Sulfur): ANCIENT, no resistance")
    print("   FRAC M3 (Mancozeb): DURABLE multi-site")
    print("   FRAC M4 (Captan): DURABLE multi-site")
    
    print("\n📋 TREATMENT RECOMMENDATION:")
    rec = optimizer.recommend_treatment('Late blight', 'Potato', ApplicationTiming.PROTECTANT)
    
    if rec:
        print(f"\n🎯 Primary: {rec.primary_treatment} (FRAC {rec.frac_code})")
        print(f"   Cost: ${rec.cost_per_hectare:.2f}/ha")
        print(f"   Expected protection: {rec.expected_yield_protection:.0f}%")
        print(f"   ROI: {rec.roi_ratio:.1f}x")
        print(f"   Max uses/season: {rec.max_uses_per_season}")
        print(f"   Tank mix with: {rec.tank_mix_partner}")
        print(f"\n🔄 Rotation options: {', '.join(rec.rotation_options[:3])}")
    
    print("\n🔍 FRAC ROTATION VALIDATION:")
    test_sequence = ['mancozeb', 'mancozeb', 'azoxystrobin', 'mancozeb', 'propiconazole']
    validation = optimizer.validate_frac_rotation(test_sequence)
    
    print(f"\nTest sequence: {' → '.join(test_sequence)}")
    print(f"FRAC sequence: {' → '.join(validation['frac_sequence'])}")
    print(f"Compliant: {'✅ YES' if validation['compliant'] else '❌ NO'}")
    if validation['issues']:
        for issue in validation['issues']:
            print(f"   {issue}")
    
    print("\n✅ SYSTEM STATUS: Treatment optimization operational")


if __name__ == "__main__":
    main()
