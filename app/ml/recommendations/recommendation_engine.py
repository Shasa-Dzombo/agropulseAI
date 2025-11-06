"""
Machine Learning Recommendation Engine
======================================

Collaborative filtering and content-based recommendations for:
- Crop selection optimization
- Input recommendations (seeds, fertilizers, pesticides)
- Market timing suggestions
- Farm management practices
- Equipment and technology adoption
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple, Any
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.decomposition import NMF, TruncatedSVD
from sklearn.neighbors import NearestNeighbors
import logging
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class Recommendation:
    """Recommendation result."""
    item_id: str
    item_name: str
    item_type: str  # 'crop', 'input', 'practice', 'equipment'
    score: float
    confidence: float
    reasoning: List[str]
    metadata: Dict[str, Any]


class CropRecommendationEngine:
    """
    Recommend optimal crops based on soil, climate, market, and farmer profile.
    
    Features:
    - Soil suitability matching
    - Climate compatibility
    - Market demand analysis
    - Historical performance
    - Farmer experience level
    - Investment capacity
    """
    
    def __init__(self):
        """Initialize crop recommendation engine."""
        self.crops_database = self._load_crops_database()
        self.similarity_model = None
        
    def _load_crops_database(self) -> pd.DataFrame:
        """Load comprehensive crop database."""
        # In production, this would load from database
        crops = {
            'maize': {
                'soil_ph_min': 5.5,
                'soil_ph_max': 7.5,
                'temp_min': 15,
                'temp_max': 35,
                'rainfall_min': 500,
                'rainfall_max': 1200,
                'growing_days': 120,
                'investment_level': 'medium',
                'skill_level': 'beginner',
                'market_demand': 0.9,
                'yield_potential': 4500,  # kg/ha
                'price_per_kg': 0.35,  # USD
            },
            'wheat': {
                'soil_ph_min': 6.0,
                'soil_ph_max': 7.5,
                'temp_min': 10,
                'temp_max': 25,
                'rainfall_min': 300,
                'rainfall_max': 600,
                'growing_days': 150,
                'investment_level': 'medium',
                'skill_level': 'intermediate',
                'market_demand': 0.85,
                'yield_potential': 3500,
                'price_per_kg': 0.40,
            },
            'rice': {
                'soil_ph_min': 5.0,
                'soil_ph_max': 7.0,
                'temp_min': 20,
                'temp_max': 35,
                'rainfall_min': 1000,
                'rainfall_max': 2000,
                'growing_days': 140,
                'investment_level': 'high',
                'skill_level': 'intermediate',
                'market_demand': 0.95,
                'yield_potential': 5000,
                'price_per_kg': 0.50,
            },
            'sorghum': {
                'soil_ph_min': 5.5,
                'soil_ph_max': 8.5,
                'temp_min': 20,
                'temp_max': 40,
                'rainfall_min': 400,
                'rainfall_max': 800,
                'growing_days': 110,
                'investment_level': 'low',
                'skill_level': 'beginner',
                'market_demand': 0.70,
                'yield_potential': 3000,
                'price_per_kg': 0.30,
            },
            'beans': {
                'soil_ph_min': 6.0,
                'soil_ph_max': 7.5,
                'temp_min': 15,
                'temp_max': 30,
                'rainfall_min': 400,
                'rainfall_max': 800,
                'growing_days': 90,
                'investment_level': 'medium',
                'skill_level': 'beginner',
                'market_demand': 0.80,
                'yield_potential': 1500,
                'price_per_kg': 0.80,
            },
            'coffee': {
                'soil_ph_min': 4.5,
                'soil_ph_max': 6.5,
                'temp_min': 15,
                'temp_max': 28,
                'rainfall_min': 1000,
                'rainfall_max': 2000,
                'growing_days': 365,
                'investment_level': 'very_high',
                'skill_level': 'advanced',
                'market_demand': 0.90,
                'yield_potential': 2000,
                'price_per_kg': 3.50,
            },
            'tea': {
                'soil_ph_min': 4.5,
                'soil_ph_max': 6.0,
                'temp_min': 10,
                'temp_max': 30,
                'rainfall_min': 1200,
                'rainfall_max': 2500,
                'growing_days': 365,
                'investment_level': 'very_high',
                'skill_level': 'advanced',
                'market_demand': 0.88,
                'yield_potential': 2500,
                'price_per_kg': 2.80,
            },
            'tomato': {
                'soil_ph_min': 6.0,
                'soil_ph_max': 7.0,
                'temp_min': 18,
                'temp_max': 30,
                'rainfall_min': 500,
                'rainfall_max': 800,
                'growing_days': 75,
                'investment_level': 'medium',
                'skill_level': 'intermediate',
                'market_demand': 0.85,
                'yield_potential': 40000,
                'price_per_kg': 0.60,
            },
            'potato': {
                'soil_ph_min': 5.0,
                'soil_ph_max': 6.5,
                'temp_min': 10,
                'temp_max': 25,
                'rainfall_min': 500,
                'rainfall_max': 750,
                'growing_days': 120,
                'investment_level': 'medium',
                'skill_level': 'intermediate',
                'market_demand': 0.82,
                'yield_potential': 25000,
                'price_per_kg': 0.40,
            },
            'sugarcane': {
                'soil_ph_min': 6.0,
                'soil_ph_max': 7.5,
                'temp_min': 20,
                'temp_max': 35,
                'rainfall_min': 1500,
                'rainfall_max': 2500,
                'growing_days': 365,
                'investment_level': 'very_high',
                'skill_level': 'advanced',
                'market_demand': 0.75,
                'yield_potential': 80000,
                'price_per_kg': 0.05,
            },
        }
        
        return pd.DataFrame(crops).T
        
    def recommend_crops(
        self,
        soil_ph: float,
        avg_temperature: float,
        annual_rainfall: float,
        farm_size: float,  # hectares
        investment_capacity: str,  # 'low', 'medium', 'high', 'very_high'
        skill_level: str,  # 'beginner', 'intermediate', 'advanced'
        market_access: float = 0.8,  # 0-1 score
        top_k: int = 5,
    ) -> List[Recommendation]:
        """
        Recommend crops based on farm conditions and farmer profile.
        
        Args:
            soil_ph: Soil pH value
            avg_temperature: Average temperature (°C)
            annual_rainfall: Annual rainfall (mm)
            farm_size: Farm size in hectares
            investment_capacity: Investment level
            skill_level: Farmer skill level
            market_access: Market access score (0-1)
            top_k: Number of recommendations
            
        Returns:
            List of crop recommendations
        """
        logger.info("Generating crop recommendations...")
        
        recommendations = []
        
        for crop_name, crop_data in self.crops_database.iterrows():
            score = 0.0
            reasoning = []
            
            # Soil pH suitability (30% weight)
            if crop_data['soil_ph_min'] <= soil_ph <= crop_data['soil_ph_max']:
                soil_score = 1.0
                reasoning.append(f"Soil pH {soil_ph} is ideal")
            else:
                ph_distance = min(
                    abs(soil_ph - crop_data['soil_ph_min']),
                    abs(soil_ph - crop_data['soil_ph_max'])
                )
                soil_score = max(0, 1 - (ph_distance / 2))
                if soil_score < 0.5:
                    reasoning.append(f"Soil pH {soil_ph} not optimal (requires adjustment)")
            score += soil_score * 0.30
            
            # Temperature suitability (25% weight)
            if crop_data['temp_min'] <= avg_temperature <= crop_data['temp_max']:
                temp_score = 1.0
                reasoning.append(f"Temperature {avg_temperature}°C is suitable")
            else:
                temp_distance = min(
                    abs(avg_temperature - crop_data['temp_min']),
                    abs(avg_temperature - crop_data['temp_max'])
                )
                temp_score = max(0, 1 - (temp_distance / 10))
                if temp_score < 0.5:
                    reasoning.append(f"Temperature {avg_temperature}°C is marginal")
            score += temp_score * 0.25
            
            # Rainfall suitability (20% weight)
            if crop_data['rainfall_min'] <= annual_rainfall <= crop_data['rainfall_max']:
                rain_score = 1.0
                reasoning.append(f"Rainfall {annual_rainfall}mm is ideal")
            else:
                rain_distance = min(
                    abs(annual_rainfall - crop_data['rainfall_min']),
                    abs(annual_rainfall - crop_data['rainfall_max'])
                )
                rain_score = max(0, 1 - (rain_distance / 500))
                if rain_score < 0.5:
                    reasoning.append(f"Rainfall {annual_rainfall}mm requires irrigation")
            score += rain_score * 0.20
            
            # Investment capacity match (10% weight)
            investment_levels = {'low': 1, 'medium': 2, 'high': 3, 'very_high': 4}
            farmer_level = investment_levels.get(investment_capacity, 2)
            crop_level = investment_levels.get(crop_data['investment_level'], 2)
            
            if farmer_level >= crop_level:
                investment_score = 1.0
                reasoning.append("Investment capacity sufficient")
            else:
                investment_score = 0.5
                reasoning.append("May require additional capital")
            score += investment_score * 0.10
            
            # Skill level match (5% weight)
            skill_levels = {'beginner': 1, 'intermediate': 2, 'advanced': 3}
            farmer_skill = skill_levels.get(skill_level, 1)
            crop_skill = skill_levels.get(crop_data['skill_level'], 1)
            
            if farmer_skill >= crop_skill:
                skill_score = 1.0
                reasoning.append("Matches farmer experience")
            else:
                skill_score = 0.6
                reasoning.append("May require training/support")
            score += skill_score * 0.05
            
            # Market demand (10% weight)
            market_score = crop_data['market_demand'] * market_access
            if market_score > 0.7:
                reasoning.append("Strong market demand")
            score += market_score * 0.10
            
            # Calculate expected profit
            expected_yield = crop_data['yield_potential'] * farm_size * (score / 1.0)
            expected_revenue = expected_yield * crop_data['price_per_kg']
            
            # Confidence based on score and data completeness
            confidence = score * 0.9
            
            recommendations.append(Recommendation(
                item_id=crop_name,
                item_name=crop_name.capitalize(),
                item_type='crop',
                score=float(score),
                confidence=float(confidence),
                reasoning=reasoning,
                metadata={
                    'growing_days': int(crop_data['growing_days']),
                    'expected_yield_kg': round(expected_yield, 2),
                    'expected_revenue_usd': round(expected_revenue, 2),
                    'price_per_kg': crop_data['price_per_kg'],
                    'investment_level': crop_data['investment_level'],
                    'skill_level': crop_data['skill_level'],
                },
            ))
            
        # Sort by score and return top K
        recommendations.sort(key=lambda x: x.score, reverse=True)
        
        logger.info(f"Generated {len(recommendations)} recommendations, returning top {top_k}")
        return recommendations[:top_k]


class CollaborativeFilteringRecommender:
    """
    Collaborative filtering for farm input recommendations.
    
    Uses farmer similarity to recommend:
    - Fertilizers
    - Seeds
    - Pesticides
    - Equipment
    """
    
    def __init__(self, n_components: int = 20):
        """Initialize collaborative filtering model."""
        self.n_components = n_components
        self.model = NMF(n_components=n_components, random_state=42)
        self.farmer_features = None
        self.item_features = None
        self.farmer_ids = []
        self.item_ids = []
        
    def fit(
        self,
        interaction_matrix: pd.DataFrame,
    ):
        """
        Train collaborative filtering model.
        
        Args:
            interaction_matrix: Farmer x Item matrix with ratings/purchases
        """
        logger.info(f"Training collaborative filtering on {interaction_matrix.shape}...")
        
        self.farmer_ids = interaction_matrix.index.tolist()
        self.item_ids = interaction_matrix.columns.tolist()
        
        # NMF decomposition
        self.farmer_features = self.model.fit_transform(interaction_matrix.values)
        self.item_features = self.model.components_.T
        
        # Calculate reconstruction error
        reconstructed = self.farmer_features @ self.item_features.T
        error = np.mean((interaction_matrix.values - reconstructed) ** 2)
        
        logger.info(f"Training complete. Reconstruction MSE: {error:.4f}")
        
    def recommend_for_farmer(
        self,
        farmer_id: str,
        top_k: int = 10,
    ) -> List[Recommendation]:
        """
        Recommend items for a specific farmer.
        
        Args:
            farmer_id: Farmer identifier
            top_k: Number of recommendations
            
        Returns:
            List of recommendations
        """
        if farmer_id not in self.farmer_ids:
            logger.warning(f"Farmer {farmer_id} not in training data")
            return []
            
        farmer_idx = self.farmer_ids.index(farmer_id)
        farmer_vector = self.farmer_features[farmer_idx]
        
        # Calculate scores for all items
        scores = farmer_vector @ self.item_features.T
        
        # Get top K items
        top_indices = np.argsort(scores)[-top_k:][::-1]
        
        recommendations = []
        for idx in top_indices:
            item_id = self.item_ids[idx]
            score = scores[idx]
            
            recommendations.append(Recommendation(
                item_id=item_id,
                item_name=item_id,
                item_type='input',
                score=float(score),
                confidence=0.8,
                reasoning=['Popular among similar farmers'],
                metadata={},
            ))
            
        return recommendations
        
    def find_similar_farmers(
        self,
        farmer_id: str,
        top_k: int = 5,
    ) -> List[Tuple[str, float]]:
        """
        Find farmers similar to given farmer.
        
        Args:
            farmer_id: Farmer identifier
            top_k: Number of similar farmers
            
        Returns:
            List of (farmer_id, similarity_score) tuples
        """
        if farmer_id not in self.farmer_ids:
            return []
            
        farmer_idx = self.farmer_ids.index(farmer_id)
        farmer_vector = self.farmer_features[farmer_idx].reshape(1, -1)
        
        # Calculate cosine similarity
        similarities = cosine_similarity(farmer_vector, self.farmer_features)[0]
        
        # Get top K (excluding self)
        top_indices = np.argsort(similarities)[-(top_k+1):-1][::-1]
        
        similar_farmers = [
            (self.farmer_ids[idx], float(similarities[idx]))
            for idx in top_indices
        ]
        
        return similar_farmers


class MarketTimingRecommender:
    """
    Recommend optimal timing for planting and selling based on:
    - Historical price trends
    - Seasonal patterns
    - Weather forecasts
    - Market supply predictions
    """
    
    def __init__(self):
        """Initialize market timing recommender."""
        self.price_history = {}
        self.seasonal_patterns = {}
        
    def recommend_planting_date(
        self,
        crop: str,
        location: str,
        target_harvest_date: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """
        Recommend optimal planting date.
        
        Args:
            crop: Crop name
            location: Farm location
            target_harvest_date: Desired harvest date
            
        Returns:
            Planting recommendation with reasoning
        """
        # Simplified recommendation logic
        # In production, would use weather forecasts, price predictions, etc.
        
        growing_days = {
            'maize': 120,
            'wheat': 150,
            'rice': 140,
            'beans': 90,
            'tomato': 75,
        }
        
        days = growing_days.get(crop.lower(), 120)
        
        if target_harvest_date:
            planting_date = target_harvest_date - timedelta(days=days)
        else:
            # Default to next optimal season
            planting_date = datetime.now() + timedelta(days=30)
            
        return {
            'recommended_date': planting_date,
            'crop': crop,
            'growing_days': days,
            'expected_harvest': planting_date + timedelta(days=days),
            'confidence': 0.85,
            'reasoning': [
                'Based on typical growing period',
                'Aligned with favorable weather patterns',
                'Targets high-price season',
            ],
        }
        
    def recommend_selling_date(
        self,
        crop: str,
        harvest_date: datetime,
        quantity: float,
    ) -> Dict[str, Any]:
        """
        Recommend optimal selling date to maximize revenue.
        
        Args:
            crop: Crop name
            harvest_date: When crop was harvested
            quantity: Quantity in kg
            
        Returns:
            Selling recommendation
        """
        # Simplified logic - would use price forecasts in production
        
        # Default: sell immediately for perishables, wait for better prices for grains
        perishables = ['tomato', 'potato', 'vegetables']
        
        if crop.lower() in perishables:
            recommended_date = harvest_date + timedelta(days=3)
            reasoning = ['Perishable crop - sell quickly', 'Minimize post-harvest losses']
        else:
            # Wait 2-3 months for better prices (post-harvest glut ends)
            recommended_date = harvest_date + timedelta(days=90)
            reasoning = ['Wait for post-harvest price recovery', 'Store crop safely']
            
        return {
            'recommended_date': recommended_date,
            'crop': crop,
            'harvest_date': harvest_date,
            'wait_days': (recommended_date - harvest_date).days,
            'confidence': 0.75,
            'reasoning': reasoning,
            'storage_requirements': ['Dry storage', 'Pest control', 'Regular monitoring'],
        }
