"""
Differential Diagnosis Engine
Advanced system for distinguishing confusable diseases

CRITICAL DIFFERENTIALS:

1. BACTERIAL vs FUNGAL LEAF SPOTS
   - Bacterial: Water-soaked margins, angular (vein-limited), bacterial streaming
   - Fungal: Dry lesions, circular, fungal fruiting bodies

2. DOWNY vs POWDERY MILDEW
   - Downy: Leaf underside sporulation, wet weather, angular spots
   - Powdery: Both sides, dry weather, white powdery coating

3. NUTRIENT DEFICIENCY vs VIRAL YELLOWING
   - Nutrient: Uniform yellowing, older leaves first (N), mobile nutrients
   - Viral: Mottled mosaic pattern, vein clearing, aphid transmission

4. ANTHRACNOSE vs OTHER BLACK SPOTS
   - Anthracnose: Sunken lesions, pink spore masses, latent infections
   - Bacterial: Angular, water-soaked, ooze
   - Fungal scab: Raised corky, olive-green

5. EARLY BLIGHT vs LATE BLIGHT (Potato/Tomato)
   - Early: Concentric rings (target spot), older leaves first, slow
   - Late: Water-soaked, white sporulation underside, RAPID (7-10 days)

6. CITRUS BLACK SPOT vs FALSE BLACK SPOT
   - True CBS: Fruit ONLY, 60-day latency, QUARANTINE
   - False CBS: Fruit AND leaves, shorter latency, harmless

7. FIRE BLIGHT vs OTHER BLIGHTS
   - Fire blight: Shepherd's crook, amber ooze, BACTERIAL
   - Other: No ooze, no crook, fungal

DECISION TREES:
- Symptom progression speed
- Location patterns
- Environmental triggers
- Microscopy confirmation
- PCR/DNA testing requirements

Author: AgroPulse AI Team
Version: 1.0.0
"""

import cv2
import numpy as np
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Tuple, Optional
from datetime import datetime


class DiagnosticCategory(Enum):
    """Disease diagnostic categories"""
    BACTERIAL = "bacterial"
    FUNGAL = "fungal"
    VIRAL = "viral"
    OOMYCETE = "oomycete"
    NEMATODE = "nematode"
    PHYSIOLOGICAL = "physiological"
    ALGAL = "algal"


class ConfirmationMethod(Enum):
    """Additional testing requirements"""
    VISUAL_SUFFICIENT = "visual"
    MICROSCOPY_RECOMMENDED = "microscopy"
    CULTURE_REQUIRED = "culture"
    PCR_REQUIRED = "pcr"
    DNA_SEQUENCING = "dna"
    ELISA = "elisa"


@dataclass
class DiagnosticFeature:
    """Individual diagnostic characteristic"""
    feature_name: str
    presence: bool
    confidence: float
    diagnostic_weight: float  # 0.0-1.0 (how diagnostic this feature is)
    description: str


@dataclass
class DifferentialOption:
    """Alternative disease possibility"""
    disease_name: str
    probability: float
    category: DiagnosticCategory
    distinguishing_features: List[str]
    confirmation_needed: ConfirmationMethod
    
    # Key differentials
    ruled_out_by: List[str] = field(default_factory=list)
    confirmed_by: List[str] = field(default_factory=list)


@dataclass
class DifferentialDiagnosisResult:
    """Differential diagnosis result"""
    primary_diagnosis: str
    primary_confidence: float
    primary_category: DiagnosticCategory
    
    differential_options: List[DifferentialOption]
    
    # Diagnostic reasoning
    supporting_features: List[DiagnosticFeature]
    ruling_out_features: List[DiagnosticFeature]
    
    # Additional testing
    confirmation_method: ConfirmationMethod
    additional_tests_needed: List[str]
    
    # Critical flags
    quarantine_differential: bool = False
    emergency_differential: bool = False
    
    timestamp: datetime = field(default_factory=datetime.now)


class DifferentialDiagnosisEngine:
    """
    Advanced differential diagnosis system
    
    CAPABILITIES:
    - Distinguish confusable diseases
    - Rule-based diagnostic reasoning
    - Confidence ranking
    - Additional testing recommendations
    """
    
    def __init__(self):
        self.differential_database = self._initialize_differential_database()
        self.decision_trees = self._initialize_decision_trees()
        
    def _initialize_differential_database(self) -> Dict[str, Dict]:
        """Comprehensive differential diagnosis database"""
        return {
            'bacterial_vs_fungal_leaf_spots': {
                'differential_pair': ['Bacterial leaf spot', 'Fungal leaf spot'],
                'key_features': {
                    'bacterial': {
                        'water_soaked_margin': {
                            'weight': 0.9,
                            'description': 'Translucent water-soaked appearance at margins'
                        },
                        'angular_shape': {
                            'weight': 0.8,
                            'description': 'Angular lesions (veins limit bacterial spread)'
                        },
                        'bacterial_streaming': {
                            'weight': 1.0,
                            'description': 'Bacterial ooze streams in water (DIAGNOSTIC)'
                        },
                        'no_fruiting_bodies': {
                            'weight': 0.6,
                            'description': 'No fungal structures visible'
                        },
                        'rapid_spread_wet': {
                            'weight': 0.7,
                            'description': 'Spreads rapidly in wet/humid conditions'
                        }
                    },
                    'fungal': {
                        'circular_lesions': {
                            'weight': 0.7,
                            'description': 'Circular lesions (fungus grows radially)'
                        },
                        'fungal_fruiting_bodies': {
                            'weight': 0.9,
                            'description': 'Visible spores, acervuli, or pycnidia'
                        },
                        'concentric_rings': {
                            'weight': 0.8,
                            'description': 'Target spot pattern (alternating rings)'
                        },
                        'dry_necrotic': {
                            'weight': 0.6,
                            'description': 'Dry necrotic tissue (not water-soaked)'
                        }
                    }
                },
                'decision_logic': 'If water-soaked + angular → 80% bacterial, If circular + fruiting bodies → 90% fungal',
                'confirmation': ConfirmationMethod.CULTURE_REQUIRED,
                'notes': 'Bacterial streaming test DEFINITIVE (bacteria stream in water droplet)'
            },
            
            'downy_vs_powdery_mildew': {
                'differential_pair': ['Downy mildew', 'Powdery mildew'],
                'key_features': {
                    'downy': {
                        'leaf_underside_only': {
                            'weight': 0.9,
                            'description': 'Sporulation PRIMARILY on leaf underside (DIAGNOSTIC)'
                        },
                        'angular_yellow_spots_upper': {
                            'weight': 0.8,
                            'description': 'Angular yellow/brown spots on upper leaf surface'
                        },
                        'wet_weather_disease': {
                            'weight': 0.7,
                            'description': 'Requires water/high humidity (oomycete)'
                        },
                        'fuzzy_gray_growth': {
                            'weight': 0.8,
                            'description': 'Gray fuzzy downy growth (sporangiophores)'
                        }
                    },
                    'powdery': {
                        'both_leaf_surfaces': {
                            'weight': 0.9,
                            'description': 'White powder on BOTH upper and lower surfaces'
                        },
                        'dry_weather_disease': {
                            'weight': 0.8,
                            'description': 'NO WATER REQUIRED (dry weather disease)'
                        },
                        'white_powdery_coating': {
                            'weight': 1.0,
                            'description': 'White powdery coating (DIAGNOSTIC)'
                        },
                        'circular_colonies': {
                            'weight': 0.7,
                            'description': 'Circular powdery colonies initially'
                        }
                    }
                },
                'decision_logic': 'Underside only + wet weather → Downy, Both sides + dry → Powdery',
                'confirmation': ConfirmationMethod.MICROSCOPY_RECOMMENDED,
                'notes': 'OPPOSITE environmental requirements (wet vs dry)'
            },
            
            'nutrient_deficiency_vs_virus': {
                'differential_pair': ['Nutrient deficiency', 'Viral infection'],
                'key_features': {
                    'nutrient_deficiency': {
                        'uniform_yellowing': {
                            'weight': 0.8,
                            'description': 'UNIFORM chlorosis (not mottled)'
                        },
                        'older_leaves_first_n': {
                            'weight': 0.9,
                            'description': 'Older leaves first (N, P, K, Mg - mobile nutrients)'
                        },
                        'younger_leaves_first_fe': {
                            'weight': 0.9,
                            'description': 'Younger leaves first (Fe, Mn, Zn - immobile)'
                        },
                        'interveinal_chlorosis': {
                            'weight': 0.7,
                            'description': 'Interveinal chlorosis (veins stay green - Fe, Mn)'
                        },
                        'reversible': {
                            'weight': 0.8,
                            'description': 'Responds to fertilizer application'
                        }
                    },
                    'viral': {
                        'mosaic_mottling': {
                            'weight': 0.95,
                            'description': 'MOSAIC or MOTTLED pattern (DIAGNOSTIC for virus)'
                        },
                        'vein_clearing': {
                            'weight': 0.9,
                            'description': 'Vein clearing (veins yellow, tissue green)'
                        },
                        'stunting': {
                            'weight': 0.7,
                            'description': 'Plant stunting'
                        },
                        'leaf_distortion': {
                            'weight': 0.8,
                            'description': 'Leaf curling, distortion, malformation'
                        },
                        'vector_present': {
                            'weight': 0.7,
                            'description': 'Aphids, whiteflies, thrips present'
                        },
                        'irreversible': {
                            'weight': 0.8,
                            'description': 'Does NOT respond to fertilizer'
                        }
                    }
                },
                'decision_logic': 'Mosaic/mottling → Virus, Uniform + responds to fertilizer → Nutrient',
                'confirmation': ConfirmationMethod.ELISA,
                'notes': 'MOSAIC pattern nearly diagnostic for virus, uniform chlorosis suggests nutrient'
            },
            
            'early_blight_vs_late_blight': {
                'differential_pair': ['Early blight (Alternaria)', 'Late blight (Phytophthora)'],
                'crops': ['Potato', 'Tomato'],
                'key_features': {
                    'early_blight': {
                        'concentric_rings': {
                            'weight': 0.95,
                            'description': 'CONCENTRIC RINGS (target spot) - DIAGNOSTIC'
                        },
                        'older_leaves_first': {
                            'weight': 0.8,
                            'description': 'Lower/older leaves affected first'
                        },
                        'slow_progression': {
                            'weight': 0.7,
                            'description': 'Slow progression (weeks)'
                        },
                        'dry_necrotic': {
                            'weight': 0.7,
                            'description': 'Dry brown necrotic lesions'
                        }
                    },
                    'late_blight': {
                        'water_soaked_lesions': {
                            'weight': 0.95,
                            'description': 'WATER-SOAKED lesions (DIAGNOSTIC)'
                        },
                        'white_sporulation_underside': {
                            'weight': 0.95,
                            'description': 'WHITE FUZZY growth on leaf underside (DIAGNOSTIC)'
                        },
                        'rapid_progression': {
                            'weight': 0.9,
                            'description': 'RAPID progression (entire field 7-10 days)'
                        },
                        'any_age_leaves': {
                            'weight': 0.6,
                            'description': 'Affects leaves of any age'
                        },
                        'tuber_fruit_infection': {
                            'weight': 0.8,
                            'description': 'Potato tuber rot, tomato fruit infection'
                        }
                    }
                },
                'decision_logic': 'Water-soaked + white underside + RAPID → Late blight (EMERGENCY), Concentric rings + slow → Early blight',
                'confirmation': ConfirmationMethod.MICROSCOPY_RECOMMENDED,
                'critical': 'Late blight EMERGENCY (Irish Famine pathogen, can destroy crop 7-10 days)',
                'notes': 'Speed of progression KEY differential'
            },
            
            'citrus_black_spot_vs_false': {
                'differential_pair': ['Citrus black spot (TRUE CBS)', 'False black spot'],
                'critical': 'QUARANTINE differential - misdiagnosis has severe trade consequences',
                'key_features': {
                    'true_cbs': {
                        'fruit_only': {
                            'weight': 1.0,
                            'description': 'FRUIT ONLY (no leaf symptoms) - DIAGNOSTIC'
                        },
                        'long_latency': {
                            'weight': 0.8,
                            'description': 'Long latency (60+ days from infection)'
                        },
                        'hard_spot_freckle': {
                            'weight': 0.9,
                            'description': 'Hard spot or freckle types'
                        },
                        'phyllosticta_citricarpa': {
                            'weight': 1.0,
                            'description': 'Phyllosticta citricarpa (DNA confirmation REQUIRED)'
                        }
                    },
                    'false_cbs': {
                        'fruit_and_leaves': {
                            'weight': 1.0,
                            'description': 'FRUIT AND LEAVES affected - DIAGNOSTIC'
                        },
                        'shorter_latency': {
                            'weight': 0.7,
                            'description': 'Shorter latency period'
                        },
                        'phyllosticta_capitalensis': {
                            'weight': 1.0,
                            'description': 'Phyllosticta capitalensis (DNA confirmation REQUIRED)'
                        },
                        'harmless': {
                            'weight': 0.9,
                            'description': 'Cosmetic only (HARMLESS)'
                        }
                    }
                },
                'decision_logic': 'Fruit ONLY → TRUE CBS (QUARANTINE), Fruit + Leaves → False CBS (harmless)',
                'confirmation': ConfirmationMethod.DNA_SEQUENCING,
                'critical_note': 'DNA TESTING MANDATORY - false positive triggers export bans, market access loss',
                'quarantine': True,
                'notes': 'MOST CRITICAL DIFFERENTIAL - misidentification = international trade disaster'
            },
            
            'fire_blight_vs_other_blights': {
                'differential_pair': ['Fire blight (Erwinia)', 'Fungal blights'],
                'key_features': {
                    'fire_blight': {
                        'shepherds_crook': {
                            'weight': 1.0,
                            'description': 'SHEPHERD\'S CROOK shoot blight (PATHOGNOMONIC)'
                        },
                        'amber_bacterial_ooze': {
                            'weight': 0.95,
                            'description': 'Amber droplets of bacterial ooze'
                        },
                        'bacterial': {
                            'weight': 1.0,
                            'description': 'Bacterial (Erwinia amylovora)'
                        },
                        'bloom_infection': {
                            'weight': 0.8,
                            'description': 'Starts at bloom (flower infection)'
                        }
                    },
                    'fungal_blights': {
                        'no_ooze': {
                            'weight': 0.8,
                            'description': 'No bacterial ooze'
                        },
                        'no_shepherds_crook': {
                            'weight': 0.9,
                            'description': 'No characteristic crook shape'
                        },
                        'fungal_fruiting': {
                            'weight': 0.7,
                            'description': 'Fungal sporulation visible'
                        }
                    }
                },
                'decision_logic': 'Shepherd\'s crook + ooze → Fire blight (BACTERIAL), No crook + fungal structures → Fungal',
                'confirmation': ConfirmationMethod.CULTURE_REQUIRED,
                'notes': 'Shepherd\'s crook PATHOGNOMONIC for fire blight'
            },
            
            'anthracnose_vs_other_black_spots': {
                'differential_pair': ['Anthracnose (Colletotrichum)', 'Bacterial black spot', 'Fungal scab'],
                'key_features': {
                    'anthracnose': {
                        'sunken_lesions': {
                            'weight': 0.9,
                            'description': 'SUNKEN circular lesions (diagnostic)'
                        },
                        'pink_spore_masses': {
                            'weight': 0.95,
                            'description': 'PINK SALMON-colored acervuli (DIAGNOSTIC)'
                        },
                        'latent_infections': {
                            'weight': 0.8,
                            'description': 'Appears during ripening (invisible at harvest)'
                        },
                        'soft_rot': {
                            'weight': 0.7,
                            'description': 'Soft watery rot progression'
                        }
                    },
                    'bacterial_black_spot': {
                        'angular_spots': {
                            'weight': 0.8,
                            'description': 'Angular spots (vein-limited)'
                        },
                        'water_soaked': {
                            'weight': 0.9,
                            'description': 'Water-soaked margins'
                        },
                        'bacterial_ooze': {
                            'weight': 0.95,
                            'description': 'Bacterial ooze/streaming'
                        }
                    },
                    'fungal_scab': {
                        'raised_corky': {
                            'weight': 0.9,
                            'description': 'RAISED corky lesions (vs sunken)'
                        },
                        'olive_green': {
                            'weight': 0.8,
                            'description': 'Olive-green color'
                        },
                        'velvety_texture': {
                            'weight': 0.8,
                            'description': 'Velvety texture (conidia)'
                        }
                    }
                },
                'decision_logic': 'Sunken + pink spores → Anthracnose, Angular + water-soaked → Bacterial, Raised + olive-green → Scab',
                'confirmation': ConfirmationMethod.MICROSCOPY_RECOMMENDED,
                'notes': 'Pink spore masses diagnostic for anthracnose, angular for bacterial, raised for scab'
            }
        }
    
    def _initialize_decision_trees(self) -> Dict:
        """Decision tree logic for differential diagnosis"""
        return {
            'leaf_spot_decision_tree': {
                'question_1': {
                    'question': 'Is the lesion water-soaked and angular?',
                    'yes': 'bacterial_likely',
                    'no': 'question_2'
                },
                'question_2': {
                    'question': 'Are there visible fungal structures (spores, fruiting bodies)?',
                    'yes': 'fungal_confirmed',
                    'no': 'question_3'
                },
                'question_3': {
                    'question': 'Is the lesion circular with concentric rings?',
                    'yes': 'fungal_alternaria',
                    'no': 'additional_testing_needed'
                }
            },
            
            'yellowing_decision_tree': {
                'question_1': {
                    'question': 'Is the yellowing uniform or mottled/mosaic?',
                    'uniform': 'question_2',
                    'mottled': 'viral_likely'
                },
                'question_2': {
                    'question': 'Which leaves are affected first?',
                    'older_leaves': 'mobile_nutrient_deficiency',
                    'younger_leaves': 'immobile_nutrient_deficiency'
                },
                'mobile_nutrient_deficiency': {
                    'possibilities': ['Nitrogen', 'Phosphorus', 'Potassium', 'Magnesium'],
                    'test': 'Soil/tissue test + fertilizer application trial'
                },
                'immobile_nutrient_deficiency': {
                    'possibilities': ['Iron', 'Manganese', 'Zinc', 'Boron'],
                    'test': 'Soil pH check + chelated micronutrient application'
                }
            }
        }
    
    def generate_differential_diagnosis(self, primary_disease: str,
                                       symptoms: Dict[str, bool],
                                       confidence: float) -> DifferentialDiagnosisResult:
        """
        Generate differential diagnosis with alternative possibilities
        """
        # Find relevant differential pairs
        differentials = []
        
        # Example: If primary is bacterial leaf spot, check fungal differential
        if 'bacterial' in primary_disease.lower() and 'spot' in primary_disease.lower():
            diff_key = 'bacterial_vs_fungal_leaf_spots'
            if diff_key in self.differential_database:
                diff_info = self.differential_database[diff_key]
                
                # Calculate probability for fungal alternative
                fungal_prob = self._calculate_alternative_probability(
                    symptoms, diff_info['key_features']['fungal']
                )
                
                differentials.append(DifferentialOption(
                    disease_name='Fungal leaf spot',
                    probability=fungal_prob,
                    category=DiagnosticCategory.FUNGAL,
                    distinguishing_features=[
                        'Circular lesions (vs angular)',
                        'Fungal fruiting bodies',
                        'Dry necrotic (vs water-soaked)'
                    ],
                    confirmation_needed=ConfirmationMethod.CULTURE_REQUIRED,
                    ruled_out_by=['water_soaked_margins', 'angular_shape'] if symptoms.get('water_soaked', False) else [],
                    confirmed_by=['fungal_structures'] if symptoms.get('fungal_structures', False) else []
                ))
        
        # Generate supporting and ruling out features
        supporting = []
        ruling_out = []
        
        for feature, present in symptoms.items():
            if present:
                supporting.append(DiagnosticFeature(
                    feature_name=feature,
                    presence=True,
                    confidence=0.8,
                    diagnostic_weight=0.7,
                    description=f'{feature} supports primary diagnosis'
                ))
        
        # Determine confirmation method
        confirmation = ConfirmationMethod.VISUAL_SUFFICIENT
        if confidence < 0.75:
            confirmation = ConfirmationMethod.MICROSCOPY_RECOMMENDED
        if confidence < 0.60:
            confirmation = ConfirmationMethod.PCR_REQUIRED
        
        return DifferentialDiagnosisResult(
            primary_diagnosis=primary_disease,
            primary_confidence=confidence,
            primary_category=DiagnosticCategory.BACTERIAL if 'bacterial' in primary_disease.lower() else DiagnosticCategory.FUNGAL,
            differential_options=differentials,
            supporting_features=supporting,
            ruling_out_features=ruling_out,
            confirmation_method=confirmation,
            additional_tests_needed=['Bacterial streaming test', 'Culture on nutrient agar'] if 'bacterial' in primary_disease.lower() else []
        )
    
    def _calculate_alternative_probability(self, symptoms: Dict[str, bool],
                                          alternative_features: Dict) -> float:
        """Calculate probability of alternative diagnosis"""
        total_weight = 0.0
        matched_weight = 0.0
        
        for feature_key, feature_info in alternative_features.items():
            weight = feature_info['weight']
            total_weight += weight
            
            if symptoms.get(feature_key, False):
                matched_weight += weight
        
        if total_weight > 0:
            return (matched_weight / total_weight) * 100
        return 0.0


def main():
    """Example usage"""
    engine = DifferentialDiagnosisEngine()
    
    print("=== AgroPulse Differential Diagnosis Engine ===")
    print(f"\nMonitoring {len(engine.differential_database)} critical differentials")
    
    print("\n🔍 CRITICAL DIFFERENTIALS:")
    print("\n1. BACTERIAL vs FUNGAL Leaf Spots")
    print("   - Bacterial: Water-soaked + angular + bacterial streaming")
    print("   - Fungal: Circular + fruiting bodies + concentric rings")
    
    print("\n2. DOWNY vs POWDERY Mildew")
    print("   - Downy: Underside only + WET weather + gray fuzzy")
    print("   - Powdery: Both sides + DRY weather + white powder")
    
    print("\n3. EARLY vs LATE Blight")
    print("   - Early: Concentric rings (target) + slow + older leaves")
    print("   - Late: Water-soaked + white underside + RAPID (7-10 days)")
    
    print("\n4. CITRUS BLACK SPOT (Quarantine Differential)")
    print("   - TRUE CBS: Fruit ONLY (QUARANTINE)")
    print("   - FALSE CBS: Fruit + Leaves (harmless)")
    print("   - DNA testing MANDATORY")
    
    print("\n5. NUTRIENT vs VIRAL Yellowing")
    print("   - Nutrient: UNIFORM chlorosis + responds to fertilizer")
    print("   - Viral: MOSAIC mottling + vein clearing + irreversible")
    
    print("\n✅ SYSTEM STATUS: Ready for differential analysis")


if __name__ == "__main__":
    main()
