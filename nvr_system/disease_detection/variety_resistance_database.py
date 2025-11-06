"""
Variety Resistance Database
Comprehensive commercial variety catalog with resistance gene profiles

RESISTANCE GENE SYSTEMS:

TOMATO RESISTANCE GENES:
- Tm-2, Tm-2² (ToMV - Tomato Mosaic Virus)
- Ty-1, Ty-2, Ty-3 (TYLCV - Tomato Yellow Leaf Curl Virus)
- I, I-2, I-3 (Fusarium oxysporum races 1, 2, 3)
- Ve (Verticillium wilt)
- Cf-4, Cf-5, Cf-9 (Cladosporium fulvum - leaf mold)
- Ph-2, Ph-3 (Phytophthora infestans - late blight)
- Pto, Prf (Pseudomonas - bacterial speck)

POTATO RESISTANCE GENES:
- R1-R11 (Phytophthora infestans - late blight)
- H1 (Globodera rostochiensis - PCN pathotype Ro1)
- Sen1 (Globodera pallida - PCN pathotype Pa2/3)

APPLE RESISTANCE GENES:
- Vf (Venturia inaequalis - apple scab from Malus floribunda)
- Vm, Vbj, Vr2 (Additional scab resistance)
- Pl-1, Pl-2, Pl-w (Erwinia amylovora - fire blight)

GRAPE RESISTANCE GENES:
- Run1, Run2 (Erysiphe necator - powdery mildew)
- Rpv1, Rpv2, Rpv3, Rpv10 (Plasmopara viticola - downy mildew)
- Ren genes (Additional downy mildew)

COFFEE RESISTANCE GENES:
- SH1-SH9 (Hemileia vastatrix - coffee leaf rust)
- Derived from Coffea liberica x C. arabica (Timor Hybrid)

LETTUCE RESISTANCE GENES:
- Dm genes (Bremia lactucae - downy mildew, 37+ races)

CUCUMBER RESISTANCE GENES:
- dm-1 (Pseudoperonospora cubensis - downy mildew)

RESISTANCE DURABILITY:
- Gene-for-gene: Single gene (R gene) vs single pathogen effector (Avr gene)
- Breakdown: Pathogen evolves new race, overcomes resistance
- Pyramiding: Stacking multiple resistance genes for durability
- Horizontal resistance: Partial resistance, more durable but weaker

RESISTANCE LIFESPAN:
- Tomato Ty genes: 10-15 years before breakdown
- Potato R genes: R1 broken in 1950s, R2-R11 progressively overcome
- Apple Vf: 50+ years (1940s-1990s), finally broken in Europe
- Lettuce Dm: New races emerge continuously (arms race)

Author: AgroPulse AI Team
Version: 1.0.0
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Tuple, Optional, Set
from datetime import datetime


class ResistanceType(Enum):
    """Type of disease resistance"""
    IMMUNE = "immune"  # Complete resistance
    HIGH = "high"  # Strong resistance
    MODERATE = "moderate"  # Partial resistance
    LOW = "low"  # Slight resistance
    SUSCEPTIBLE = "susceptible"  # No resistance
    HIGHLY_SUSCEPTIBLE = "highly_susceptible"  # Very vulnerable


class ResistanceGeneStatus(Enum):
    """Status of resistance gene"""
    EFFECTIVE = "effective"  # Currently functional
    BROKEN = "broken"  # Overcome by pathogen
    REGIONAL_BREAKDOWN = "regional"  # Broken in some areas
    PYRAMIDED = "pyramided"  # Combined with other genes


@dataclass
class ResistanceGene:
    """Individual resistance gene information"""
    gene_name: str
    disease_target: str
    pathogen_species: str
    
    # Gene characteristics
    resistance_level: ResistanceType
    inheritance: str  # dominant, recessive, quantitative
    gene_status: ResistanceGeneStatus
    
    # Origin and deployment
    source_species: str
    year_deployed: Optional[int] = None
    years_effective: Optional[int] = None
    
    # Breakdown information
    resistance_broken: bool = False
    breakdown_year: Optional[int] = None
    breakdown_location: List[str] = field(default_factory=list)
    
    # Molecular information
    chromosome: Optional[str] = None
    marker: Optional[str] = None
    
    notes: str = ""


@dataclass
class VarietyProfile:
    """Complete variety disease resistance profile"""
    variety_name: str
    crop: str
    
    # Resistance genes
    resistance_genes: List[ResistanceGene]
    
    # Disease ratings
    disease_resistance: Dict[str, ResistanceType]
    
    # Agronomic characteristics
    maturity_days: int
    yield_potential: str  # high, medium, low
    fruit_quality: str  # excellent, good, fair
    
    # Regional adaptation
    regions: List[str]
    climate_adaptation: str
    
    # Market segment
    market_type: str  # fresh, processing, both
    
    # Notes
    breeder: str = ""
    release_year: Optional[int] = None
    patent_status: str = ""
    notes: str = ""


@dataclass
class ResistanceBreakdownEvent:
    """Record of resistance gene breakdown"""
    gene_name: str
    disease: str
    breakdown_year: int
    location: str
    pathogen_race: str
    
    impact: str  # severe, moderate, localized
    alternative_genes: List[str]
    
    notes: str = ""


class VarietyResistanceDatabase:
    """
    Comprehensive variety resistance database
    
    FEATURES:
    - Commercial variety catalog
    - Resistance gene profiles
    - Breakdown tracking
    - Variety recommendations
    """
    
    def __init__(self):
        self.varieties = self._initialize_variety_database()
        self.resistance_genes = self._initialize_gene_database()
        self.breakdown_events = self._initialize_breakdown_history()
        
    def _initialize_variety_database(self) -> Dict[str, List[VarietyProfile]]:
        """Comprehensive commercial variety database"""
        return {
            'tomato': [
                VarietyProfile(
                    variety_name='Big Beef',
                    crop='Tomato',
                    resistance_genes=[
                        ResistanceGene(
                            gene_name='Ve',
                            disease_target='Verticillium wilt',
                            pathogen_species='Verticillium dahliae',
                            resistance_level=ResistanceType.HIGH,
                            inheritance='dominant',
                            gene_status=ResistanceGeneStatus.EFFECTIVE,
                            source_species='Lycopersicon esculentum'
                        ),
                        ResistanceGene(
                            gene_name='I-2',
                            disease_target='Fusarium wilt race 2',
                            pathogen_species='Fusarium oxysporum f.sp. lycopersici',
                            resistance_level=ResistanceType.HIGH,
                            inheritance='dominant',
                            gene_status=ResistanceGeneStatus.EFFECTIVE,
                            source_species='Lycopersicon pimpinellifolium'
                        ),
                        ResistanceGene(
                            gene_name='Tm-2²',
                            disease_target='Tomato Mosaic Virus',
                            pathogen_species='ToMV',
                            resistance_level=ResistanceType.HIGH,
                            inheritance='dominant',
                            gene_status=ResistanceGeneStatus.EFFECTIVE,
                            source_species='Lycopersicon peruvianum'
                        )
                    ],
                    disease_resistance={
                        'Verticillium wilt': ResistanceType.HIGH,
                        'Fusarium wilt race 1': ResistanceType.HIGH,
                        'Fusarium wilt race 2': ResistanceType.HIGH,
                        'Tomato Mosaic Virus': ResistanceType.HIGH,
                        'Late blight': ResistanceType.SUSCEPTIBLE,
                        'Early blight': ResistanceType.SUSCEPTIBLE
                    },
                    maturity_days=73,
                    yield_potential='high',
                    fruit_quality='excellent',
                    regions=['USA', 'Canada'],
                    climate_adaptation='temperate',
                    market_type='fresh',
                    breeder='Burpee',
                    release_year=1994,
                    notes='Hybrid, widely adapted, excellent flavor'
                ),
                
                VarietyProfile(
                    variety_name='Mountain Merit',
                    crop='Tomato',
                    resistance_genes=[
                        ResistanceGene(
                            gene_name='Ph-2',
                            disease_target='Late blight',
                            pathogen_species='Phytophthora infestans',
                            resistance_level=ResistanceType.MODERATE,
                            inheritance='quantitative',
                            gene_status=ResistanceGeneStatus.EFFECTIVE,
                            source_species='Solanum pimpinellifolium',
                            notes='Provides tolerance but not immunity'
                        ),
                        ResistanceGene(
                            gene_name='Ph-3',
                            disease_target='Late blight',
                            pathogen_species='Phytophthora infestans',
                            resistance_level=ResistanceType.MODERATE,
                            inheritance='quantitative',
                            gene_status=ResistanceGeneStatus.EFFECTIVE,
                            source_species='Solanum pimpinellifolium'
                        )
                    ],
                    disease_resistance={
                        'Late blight': ResistanceType.MODERATE,
                        'Verticillium wilt': ResistanceType.HIGH,
                        'Fusarium wilt': ResistanceType.HIGH,
                        'Early blight': ResistanceType.MODERATE
                    },
                    maturity_days=75,
                    yield_potential='high',
                    fruit_quality='good',
                    regions=['USA Northeast', 'Canada'],
                    climate_adaptation='cool_temperate',
                    market_type='fresh',
                    breeder='North Carolina State University',
                    release_year=2004,
                    notes='One of first late blight resistant fresh market tomatoes'
                ),
                
                VarietyProfile(
                    variety_name='Iron Lady',
                    crop='Tomato',
                    resistance_genes=[
                        ResistanceGene(
                            gene_name='Ph-2',
                            disease_target='Late blight',
                            pathogen_species='Phytophthora infestans',
                            resistance_level=ResistanceType.HIGH,
                            inheritance='quantitative',
                            gene_status=ResistanceGeneStatus.EFFECTIVE,
                            source_species='Solanum pimpinellifolium'
                        ),
                        ResistanceGene(
                            gene_name='Ph-3',
                            disease_target='Late blight',
                            pathogen_species='Phytophthora infestans',
                            resistance_level=ResistanceType.HIGH,
                            inheritance='quantitative',
                            gene_status=ResistanceGeneStatus.EFFECTIVE,
                            source_species='Solanum pimpinellifolium'
                        )
                    ],
                    disease_resistance={
                        'Late blight': ResistanceType.HIGH,
                        'Verticillium wilt': ResistanceType.HIGH,
                        'Fusarium wilt': ResistanceType.HIGH
                    },
                    maturity_days=72,
                    yield_potential='medium',
                    fruit_quality='excellent',
                    regions=['USA', 'Europe'],
                    climate_adaptation='temperate',
                    market_type='fresh',
                    release_year=2012,
                    notes='Strong late blight resistance, Roma type'
                )
            ],
            
            'potato': [
                VarietyProfile(
                    variety_name='Russet Burbank',
                    crop='Potato',
                    resistance_genes=[],  # No major R genes
                    disease_resistance={
                        'Late blight': ResistanceType.SUSCEPTIBLE,
                        'Common scab': ResistanceType.SUSCEPTIBLE,
                        'Verticillium wilt': ResistanceType.MODERATE
                    },
                    maturity_days=135,
                    yield_potential='high',
                    fruit_quality='excellent',
                    regions=['USA', 'Canada'],
                    climate_adaptation='temperate',
                    market_type='fresh_processing',
                    release_year=1876,
                    notes='Industry standard, no late blight resistance'
                ),
                
                VarietyProfile(
                    variety_name='Defender',
                    crop='Potato',
                    resistance_genes=[
                        ResistanceGene(
                            gene_name='R1',
                            disease_target='Late blight race 1',
                            pathogen_species='Phytophthora infestans',
                            resistance_level=ResistanceType.HIGH,
                            inheritance='dominant',
                            gene_status=ResistanceGeneStatus.BROKEN,
                            source_species='Solanum demissum',
                            year_deployed=1950,
                            years_effective=5,
                            resistance_broken=True,
                            breakdown_year=1955,
                            breakdown_location=['Europe', 'USA'],
                            notes='First deployed R gene, quickly overcome'
                        ),
                        ResistanceGene(
                            gene_name='R2',
                            disease_target='Late blight',
                            pathogen_species='Phytophthora infestans',
                            resistance_level=ResistanceType.MODERATE,
                            inheritance='dominant',
                            gene_status=ResistanceGeneStatus.BROKEN,
                            source_species='Solanum demissum',
                            resistance_broken=True,
                            breakdown_year=1960
                        ),
                        ResistanceGene(
                            gene_name='R3',
                            disease_target='Late blight',
                            pathogen_species='Phytophthora infestans',
                            resistance_level=ResistanceType.MODERATE,
                            inheritance='dominant',
                            gene_status=ResistanceGeneStatus.REGIONAL_BREAKDOWN,
                            source_species='Solanum demissum'
                        )
                    ],
                    disease_resistance={
                        'Late blight': ResistanceType.MODERATE,
                        'Common scab': ResistanceType.MODERATE
                    },
                    maturity_days=110,
                    yield_potential='high',
                    fruit_quality='good',
                    regions=['UK', 'Europe'],
                    climate_adaptation='cool_temperate',
                    market_type='fresh',
                    release_year=2000,
                    notes='R genes partially overcome but still provides some protection'
                ),
                
                VarietyProfile(
                    variety_name='Sarpo Mira',
                    crop='Potato',
                    resistance_genes=[
                        ResistanceGene(
                            gene_name='R3a',
                            disease_target='Late blight',
                            pathogen_species='Phytophthora infestans',
                            resistance_level=ResistanceType.HIGH,
                            inheritance='quantitative',
                            gene_status=ResistanceGeneStatus.EFFECTIVE,
                            source_species='Solanum demissum'
                        ),
                        ResistanceGene(
                            gene_name='Rpi-Smira1',
                            disease_target='Late blight',
                            pathogen_species='Phytophthora infestans',
                            resistance_level=ResistanceType.HIGH,
                            inheritance='dominant',
                            gene_status=ResistanceGeneStatus.EFFECTIVE,
                            source_species='Solanum demissum'
                        ),
                        ResistanceGene(
                            gene_name='Rpi-Smira2',
                            disease_target='Late blight',
                            pathogen_species='Phytophthora infestans',
                            resistance_level=ResistanceType.HIGH,
                            inheritance='dominant',
                            gene_status=ResistanceGeneStatus.EFFECTIVE,
                            source_species='Solanum demissum'
                        )
                    ],
                    disease_resistance={
                        'Late blight': ResistanceType.HIGH,
                        'Common scab': ResistanceType.MODERATE,
                        'Virus complex': ResistanceType.HIGH
                    },
                    maturity_days=120,
                    yield_potential='high',
                    fruit_quality='good',
                    regions=['UK', 'Europe', 'USA'],
                    climate_adaptation='temperate',
                    market_type='fresh',
                    breeder='Sárvári Research Trust (Hungary)',
                    release_year=2000,
                    notes='MULTIPLE R genes stacked (pyramided) - durable resistance'
                )
            ],
            
            'apple': [
                VarietyProfile(
                    variety_name='Liberty',
                    crop='Apple',
                    resistance_genes=[
                        ResistanceGene(
                            gene_name='Vf',
                            disease_target='Apple scab',
                            pathogen_species='Venturia inaequalis',
                            resistance_level=ResistanceType.IMMUNE,
                            inheritance='dominant',
                            gene_status=ResistanceGeneStatus.REGIONAL_BREAKDOWN,
                            source_species='Malus floribunda 821',
                            year_deployed=1940,
                            years_effective=50,
                            resistance_broken=True,
                            breakdown_year=1990,
                            breakdown_location=['Europe'],
                            notes='Most widely used scab resistance gene, finally broken in Europe 1990s'
                        ),
                        ResistanceGene(
                            gene_name='Pl-1',
                            disease_target='Fire blight',
                            pathogen_species='Erwinia amylovora',
                            resistance_level=ResistanceType.MODERATE,
                            inheritance='quantitative',
                            gene_status=ResistanceGeneStatus.EFFECTIVE,
                            source_species='Malus robusta'
                        )
                    ],
                    disease_resistance={
                        'Apple scab': ResistanceType.IMMUNE,
                        'Fire blight': ResistanceType.MODERATE,
                        'Cedar apple rust': ResistanceType.MODERATE,
                        'Powdery mildew': ResistanceType.SUSCEPTIBLE
                    },
                    maturity_days=150,
                    yield_potential='medium',
                    fruit_quality='good',
                    regions=['USA', 'Canada'],
                    climate_adaptation='temperate',
                    market_type='fresh',
                    breeder='Cornell/USDA',
                    release_year=1978,
                    notes='Vf gene effective in USA, broken in Europe'
                ),
                
                VarietyProfile(
                    variety_name='Enterprise',
                    crop='Apple',
                    resistance_genes=[
                        ResistanceGene(
                            gene_name='Vf',
                            disease_target='Apple scab',
                            pathogen_species='Venturia inaequalis',
                            resistance_level=ResistanceType.IMMUNE,
                            inheritance='dominant',
                            gene_status=ResistanceGeneStatus.REGIONAL_BREAKDOWN,
                            source_species='Malus floribunda 821'
                        )
                    ],
                    disease_resistance={
                        'Apple scab': ResistanceType.IMMUNE,
                        'Fire blight': ResistanceType.MODERATE,
                        'Cedar apple rust': ResistanceType.HIGH,
                        'Powdery mildew': ResistanceType.MODERATE
                    },
                    maturity_days=160,
                    yield_potential='high',
                    fruit_quality='excellent',
                    regions=['USA'],
                    climate_adaptation='temperate',
                    market_type='fresh',
                    breeder='Purdue/Rutgers/Illinois',
                    release_year=1994,
                    notes='Superior fruit quality with scab resistance'
                )
            ],
            
            'coffee': [
                VarietyProfile(
                    variety_name='Castillo',
                    crop='Coffee',
                    resistance_genes=[
                        ResistanceGene(
                            gene_name='SH3',
                            disease_target='Coffee leaf rust',
                            pathogen_species='Hemileia vastatrix',
                            resistance_level=ResistanceType.HIGH,
                            inheritance='quantitative',
                            gene_status=ResistanceGeneStatus.EFFECTIVE,
                            source_species='Timor Hybrid (C. arabica x C. liberica)',
                            year_deployed=2005
                        )
                    ],
                    disease_resistance={
                        'Coffee leaf rust': ResistanceType.HIGH,
                        'Coffee berry disease': ResistanceType.MODERATE
                    },
                    maturity_days=365,
                    yield_potential='high',
                    fruit_quality='good',
                    regions=['Colombia', 'Central America'],
                    climate_adaptation='tropical_highland',
                    market_type='specialty',
                    breeder='Cenicafé (Colombia)',
                    release_year=2005,
                    notes='Colombia\'s response to leaf rust epidemic, SH3 from Timor Hybrid'
                ),
                
                VarietyProfile(
                    variety_name='Lempira',
                    crop='Coffee',
                    resistance_genes=[
                        ResistanceGene(
                            gene_name='SH5',
                            disease_target='Coffee leaf rust',
                            pathogen_species='Hemileia vastatrix',
                            resistance_level=ResistanceType.HIGH,
                            inheritance='quantitative',
                            gene_status=ResistanceGeneStatus.EFFECTIVE,
                            source_species='Timor Hybrid'
                        )
                    ],
                    disease_resistance={
                        'Coffee leaf rust': ResistanceType.HIGH
                    },
                    maturity_days=365,
                    yield_potential='high',
                    fruit_quality='excellent',
                    regions=['Honduras', 'Central America'],
                    climate_adaptation='tropical_highland',
                    market_type='specialty',
                    breeder='IHCAFE (Honduras)',
                    release_year=2010,
                    notes='Honduran variety, excellent cup quality + rust resistance'
                )
            ],
            
            'lettuce': [
                VarietyProfile(
                    variety_name='Salvius',
                    crop='Lettuce',
                    resistance_genes=[
                        ResistanceGene(
                            gene_name='Dm-16',
                            disease_target='Downy mildew race 16',
                            pathogen_species='Bremia lactucae',
                            resistance_level=ResistanceType.HIGH,
                            inheritance='dominant',
                            gene_status=ResistanceGeneStatus.BROKEN,
                            source_species='Lactuca serriola',
                            resistance_broken=True,
                            notes='Race 16 overcome by races 17-37+'
                        )
                    ],
                    disease_resistance={
                        'Downy mildew': ResistanceType.MODERATE,
                        'Lettuce mosaic virus': ResistanceType.HIGH
                    },
                    maturity_days=55,
                    yield_potential='high',
                    fruit_quality='excellent',
                    regions=['USA', 'Europe'],
                    climate_adaptation='cool_temperate',
                    market_type='fresh',
                    notes='Dm genes continuously overcome - arms race with pathogen'
                )
            ]
        }
    
    def _initialize_gene_database(self) -> Dict[str, ResistanceGene]:
        """Database of individual resistance genes"""
        return {
            'Tm-2': ResistanceGene(
                gene_name='Tm-2',
                disease_target='Tomato Mosaic Virus',
                pathogen_species='ToMV',
                resistance_level=ResistanceType.HIGH,
                inheritance='dominant',
                gene_status=ResistanceGeneStatus.EFFECTIVE,
                source_species='Lycopersicon peruvianum',
                year_deployed=1960,
                chromosome='9',
                notes='Widely used, durable resistance'
            ),
            
            'Vf': ResistanceGene(
                gene_name='Vf',
                disease_target='Apple scab',
                pathogen_species='Venturia inaequalis',
                resistance_level=ResistanceType.IMMUNE,
                inheritance='dominant',
                gene_status=ResistanceGeneStatus.REGIONAL_BREAKDOWN,
                source_species='Malus floribunda 821',
                year_deployed=1940,
                years_effective=50,
                resistance_broken=True,
                breakdown_year=1990,
                breakdown_location=['Europe'],
                notes='MOST SUCCESSFUL resistance gene in history - 50 years effective'
            ),
            
            'R1': ResistanceGene(
                gene_name='R1',
                disease_target='Late blight',
                pathogen_species='Phytophthora infestans',
                resistance_level=ResistanceType.HIGH,
                inheritance='dominant',
                gene_status=ResistanceGeneStatus.BROKEN,
                source_species='Solanum demissum',
                year_deployed=1950,
                years_effective=5,
                resistance_broken=True,
                breakdown_year=1955,
                breakdown_location=['Worldwide'],
                notes='First late blight R gene, quickly overcome - classic gene-for-gene failure'
            )
        }
    
    def _initialize_breakdown_history(self) -> List[ResistanceBreakdownEvent]:
        """Historical resistance breakdown events"""
        return [
            ResistanceBreakdownEvent(
                gene_name='R1',
                disease='Late blight',
                breakdown_year=1955,
                location='Europe',
                pathogen_race='Race 1.2',
                impact='severe',
                alternative_genes=['R2', 'R3', 'R4'],
                notes='First major resistance breakdown, led to R2-R11 deployment'
            ),
            
            ResistanceBreakdownEvent(
                gene_name='Vf',
                disease='Apple scab',
                breakdown_year=1990,
                location='Europe (Germany first)',
                pathogen_race='Race 6',
                impact='severe',
                alternative_genes=['Vm', 'Vbj', 'Vr2'],
                notes='After 50 years effectiveness, Vf broken - longest lasting single gene'
            ),
            
            ResistanceBreakdownEvent(
                gene_name='Dm-1 through Dm-15',
                disease='Lettuce downy mildew',
                breakdown_year=2000,
                location='California USA',
                pathogen_race='Races 16-37+',
                impact='severe',
                alternative_genes=['Dm-16+'],
                notes='ARMS RACE - new races continuously overcome Dm genes'
            )
        ]
    
    def search_varieties(self, crop: str, disease: str) -> List[VarietyProfile]:
        """Search for varieties with resistance to specific disease"""
        if crop.lower() not in self.varieties:
            return []
        
        resistant_varieties = []
        for variety in self.varieties[crop.lower()]:
            if disease in variety.disease_resistance:
                resistance_level = variety.disease_resistance[disease]
                if resistance_level in [ResistanceType.IMMUNE, ResistanceType.HIGH, ResistanceType.MODERATE]:
                    resistant_varieties.append(variety)
        
        # Sort by resistance level
        resistant_varieties.sort(
            key=lambda v: ['immune', 'high', 'moderate'].index(v.disease_resistance[disease].value)
        )
        
        return resistant_varieties
    
    def get_gene_status(self, gene_name: str) -> Optional[ResistanceGene]:
        """Get current status of resistance gene"""
        return self.resistance_genes.get(gene_name)
    
    def check_gene_durability(self, gene_name: str) -> Dict:
        """Check durability and breakdown history of gene"""
        gene = self.resistance_genes.get(gene_name)
        if not gene:
            return {'status': 'unknown'}
        
        breakdown_events = [
            event for event in self.breakdown_events 
            if event.gene_name == gene_name
        ]
        
        return {
            'gene': gene_name,
            'status': gene.gene_status.value,
            'years_effective': gene.years_effective,
            'broken': gene.resistance_broken,
            'breakdown_events': breakdown_events,
            'durability': 'excellent' if gene.years_effective and gene.years_effective > 20 else 'moderate'
        }


def main():
    """Example usage"""
    db = VarietyResistanceDatabase()
    
    print("=== AgroPulse Variety Resistance Database ===")
    print(f"\nCrops in database: {len(db.varieties)}")
    print(f"Resistance genes tracked: {len(db.resistance_genes)}")
    print(f"Breakdown events recorded: {len(db.breakdown_events)}")
    
    print("\n🧬 FAMOUS RESISTANCE GENES:")
    print("\n1. Vf (Apple Scab)")
    print("   - Source: Malus floribunda 821")
    print("   - Deployed: 1940")
    print("   - Effective: 50 YEARS (1940-1990)")
    print("   - Status: Broken in Europe 1990, still effective USA")
    print("   - MOST SUCCESSFUL single gene in history")
    
    print("\n2. R1 (Potato Late Blight)")
    print("   - Source: Solanum demissum")
    print("   - Deployed: 1950")
    print("   - Effective: 5 years only")
    print("   - Status: Broken 1955")
    print("   - Led to R2-R11 deployment (all eventually broken)")
    
    print("\n3. SH Genes (Coffee Leaf Rust)")
    print("   - Source: Timor Hybrid (Coffea arabica x C. liberica)")
    print("   - SH1-SH9 genes available")
    print("   - Status: Currently effective")
    print("   - Deployment: Castillo, Lempira, Colombia varieties")
    
    print("\n4. Dm Genes (Lettuce Downy Mildew)")
    print("   - 37+ RACES identified")
    print("   - ARMS RACE: New genes continuously overcome")
    print("   - Status: Continuous breeding required")
    
    print("\n📊 VARIETY EXAMPLES:")
    
    # Search for late blight resistant tomatoes
    lb_tomatoes = db.search_varieties('tomato', 'Late blight')
    print(f"\n🍅 Late Blight Resistant Tomatoes: {len(lb_tomatoes)}")
    for var in lb_tomatoes:
        print(f"   - {var.variety_name}: {var.disease_resistance['Late blight'].value}")
    
    print("\n✅ SYSTEM STATUS: Ready for variety recommendation")


if __name__ == "__main__":
    main()
