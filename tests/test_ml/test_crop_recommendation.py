"""
Crop Recommendation ML Model Tests

Comprehensive tests for crop recommendation models including basic and advanced recommendations.
"""

import pytest
import numpy as np
from datetime import datetime

from app.ml.crop_recommendation import CropRecommendationModel
from app.ml.crop_advanced import AdvancedCropRecommendation
from tests.factories import CropRecommendationInputFactory
from tests.utils import (
    calculate_metrics, assert_in_range, assert_probability,
    MockMLModel, assert_model_performance
)


@pytest.mark.ml
@pytest.mark.unit
class TestCropRecommendationModel:
    """Test basic crop recommendation model."""
    
    @pytest.fixture
    def model(self):
        """Create crop recommendation model instance."""
        return CropRecommendationModel()
    
    def test_model_initialization(self, model):
        """Test model initializes correctly."""
        assert model is not None
        assert hasattr(model, 'predict')
        assert hasattr(model, 'train')
    
    def test_predict_with_valid_input(self, model):
        """Test prediction with valid input."""
        input_data = {
            'nitrogen': 80,
            'phosphorus': 50,
            'potassium': 60,
            'temperature': 25.0,
            'humidity': 70.0,
            'ph': 6.5,
            'rainfall': 800
        }
        
        prediction = model.predict(input_data)
        
        assert 'crop' in prediction
        assert 'confidence' in prediction
        assert_probability(prediction['confidence'])
    
    def test_predict_maize_conditions(self, model):
        """Test prediction for maize-favorable conditions."""
        input_data = {
            'nitrogen': 90,
            'phosphorus': 60,
            'potassium': 50,
            'temperature': 23.0,
            'humidity': 65.0,
            'ph': 6.0,
            'rainfall': 900
        }
        
        prediction = model.predict(input_data)
        
        # Maize should be recommended or among alternatives
        assert prediction['crop'] in ['maize', 'beans', 'wheat']
        assert prediction['confidence'] > 0.5
    
    def test_predict_beans_conditions(self, model):
        """Test prediction for beans-favorable conditions."""
        input_data = {
            'nitrogen': 60,
            'phosphorus': 70,
            'potassium': 55,
            'temperature': 22.0,
            'humidity': 70.0,
            'ph': 6.5,
            'rainfall': 750
        }
        
        prediction = model.predict(input_data)
        
        assert prediction['crop'] in ['beans', 'maize', 'potatoes']
        assert_probability(prediction['confidence'])
    
    def test_predict_with_extreme_values(self, model):
        """Test prediction with extreme but valid values."""
        input_data = {
            'nitrogen': 150,
            'phosphorus': 100,
            'potassium': 100,
            'temperature': 35.0,
            'humidity': 90.0,
            'ph': 8.0,
            'rainfall': 1500
        }
        
        prediction = model.predict(input_data)
        
        # Should still return a prediction
        assert 'crop' in prediction
        assert 'confidence' in prediction
    
    def test_predict_with_low_nutrients(self, model):
        """Test prediction with low nutrient levels."""
        input_data = {
            'nitrogen': 20,
            'phosphorus': 15,
            'potassium': 10,
            'temperature': 25.0,
            'humidity': 60.0,
            'ph': 6.0,
            'rainfall': 600
        }
        
        prediction = model.predict(input_data)
        
        # Should recommend crops suitable for low nutrients
        assert 'crop' in prediction
        assert prediction.get('nutrient_warning', False) or prediction['confidence'] < 0.7
    
    def test_predict_batch(self, model):
        """Test batch prediction."""
        batch_input = [
            CropRecommendationInputFactory.build() for _ in range(10)
        ]
        
        predictions = model.predict_batch(batch_input)
        
        assert len(predictions) == 10
        assert all('crop' in p for p in predictions)
        assert all('confidence' in p for p in predictions)
    
    def test_get_alternatives(self, model):
        """Test getting alternative crop recommendations."""
        input_data = {
            'nitrogen': 80,
            'phosphorus': 50,
            'potassium': 60,
            'temperature': 25.0,
            'humidity': 70.0,
            'ph': 6.5,
            'rainfall': 800
        }
        
        prediction = model.predict(input_data, include_alternatives=True)
        
        assert 'alternatives' in prediction
        assert isinstance(prediction['alternatives'], list)
        assert len(prediction['alternatives']) >= 2
        
        # Each alternative should have crop and confidence
        for alt in prediction['alternatives']:
            assert 'crop' in alt
            assert 'confidence' in alt
            assert_probability(alt['confidence'])
    
    def test_explain_prediction(self, model):
        """Test prediction explanation."""
        input_data = {
            'nitrogen': 80,
            'phosphorus': 50,
            'potassium': 60,
            'temperature': 25.0,
            'humidity': 70.0,
            'ph': 6.5,
            'rainfall': 800
        }
        
        prediction = model.predict(input_data, explain=True)
        
        assert 'explanation' in prediction
        assert 'factors' in prediction['explanation']
        
        factors = prediction['explanation']['factors']
        assert 'soil_nutrients' in factors
        assert 'climate' in factors
    
    def test_feature_importance(self, model):
        """Test feature importance extraction."""
        importance = model.get_feature_importance()
        
        assert isinstance(importance, dict)
        assert 'nitrogen' in importance
        assert 'temperature' in importance
        
        # Importances should sum to ~1.0
        total = sum(importance.values())
        assert_in_range(total, 0.95, 1.05)
    
    def test_model_confidence_calibration(self, model):
        """Test confidence scores are well-calibrated."""
        # Generate diverse test cases
        test_cases = [
            CropRecommendationInputFactory.build() for _ in range(100)
        ]
        
        predictions = model.predict_batch(test_cases)
        confidences = [p['confidence'] for p in predictions]
        
        # Check confidence distribution
        assert min(confidences) >= 0.0
        assert max(confidences) <= 1.0
        assert np.mean(confidences) > 0.5  # Reasonable average confidence
    
    def test_invalid_input_handling(self, model):
        """Test handling of invalid input."""
        invalid_input = {
            'nitrogen': -10,  # Invalid negative
            'temperature': 25.0
        }
        
        with pytest.raises((ValueError, KeyError)):
            model.predict(invalid_input)
    
    def test_missing_feature_handling(self, model):
        """Test handling of missing features."""
        incomplete_input = {
            'nitrogen': 80,
            'phosphorus': 50
            # Missing other features
        }
        
        with pytest.raises(KeyError):
            model.predict(incomplete_input)


@pytest.mark.ml
@pytest.mark.integration
class TestAdvancedCropRecommendation:
    """Test advanced crop recommendation features."""
    
    @pytest.fixture
    def advanced_model(self):
        """Create advanced crop recommendation model."""
        return AdvancedCropRecommendation()
    
    def test_crop_rotation_recommendation(self, advanced_model):
        """Test crop rotation recommendations."""
        previous_crops = ['maize', 'maize', 'beans']
        current_conditions = {
            'nitrogen': 60,
            'phosphorus': 50,
            'potassium': 60,
            'temperature': 25.0,
            'humidity': 70.0,
            'ph': 6.5,
            'rainfall': 800
        }
        
        recommendation = advanced_model.recommend_rotation(
            previous_crops, current_conditions
        )
        
        assert 'recommended_crop' in recommendation
        assert 'rotation_benefit' in recommendation
        assert 'reason' in recommendation
        
        # Should not recommend maize after two maize seasons
        assert recommendation['recommended_crop'] != 'maize'
    
    def test_intercropping_recommendation(self, advanced_model):
        """Test intercropping recommendations."""
        main_crop = 'maize'
        field_conditions = {
            'nitrogen': 80,
            'phosphorus': 50,
            'potassium': 60,
            'temperature': 25.0,
            'humidity': 70.0,
            'ph': 6.5,
            'rainfall': 800,
            'field_size': 10.0
        }
        
        recommendation = advanced_model.recommend_intercrop(
            main_crop, field_conditions
        )
        
        assert 'intercrop' in recommendation
        assert 'benefits' in recommendation
        assert 'planting_ratio' in recommendation
        
        # Common intercrop for maize is beans
        assert recommendation['intercrop'] in ['beans', 'cowpeas', 'pumpkin']
    
    def test_succession_planting(self, advanced_model):
        """Test succession planting recommendations."""
        field_conditions = {
            'nitrogen': 70,
            'phosphorus': 50,
            'potassium': 60,
            'temperature': 24.0,
            'humidity': 65.0,
            'ph': 6.5,
            'rainfall': 850,
            'growing_season_length': 180  # days
        }
        
        plan = advanced_model.recommend_succession_planting(field_conditions)
        
        assert 'planting_schedule' in plan
        assert len(plan['planting_schedule']) >= 2
        
        # Verify sequential planting
        for planting in plan['planting_schedule']:
            assert 'crop' in planting
            assert 'start_day' in planting
            assert 'end_day' in planting
    
    def test_seasonal_recommendations(self, advanced_model):
        """Test seasonal crop recommendations."""
        location = {'latitude': -1.286389, 'longitude': 36.817223}  # Nairobi
        season = 'long_rains'  # March-May
        
        recommendations = advanced_model.recommend_by_season(
            location, season
        )
        
        assert isinstance(recommendations, list)
        assert len(recommendations) > 0
        
        for rec in recommendations:
            assert 'crop' in rec
            assert 'suitability' in rec
            assert_probability(rec['suitability'])
    
    def test_climate_zone_adaptation(self, advanced_model):
        """Test recommendations adapt to climate zones."""
        # Highland conditions
        highland_conditions = {
            'nitrogen': 80,
            'phosphorus': 50,
            'potassium': 60,
            'temperature': 18.0,  # Cooler
            'humidity': 75.0,
            'ph': 6.0,
            'rainfall': 1200,
            'elevation': 2000
        }
        
        highland_rec = advanced_model.predict(highland_conditions)
        
        # Lowland conditions
        lowland_conditions = highland_conditions.copy()
        lowland_conditions['temperature'] = 28.0  # Warmer
        lowland_conditions['elevation'] = 500
        
        lowland_rec = advanced_model.predict(lowland_conditions)
        
        # Recommendations should differ based on climate
        assert highland_rec['crop'] != lowland_rec['crop'] or \
               abs(highland_rec['confidence'] - lowland_rec['confidence']) > 0.1
    
    def test_multi_criteria_optimization(self, advanced_model):
        """Test optimization for multiple criteria."""
        conditions = {
            'nitrogen': 80,
            'phosphorus': 50,
            'potassium': 60,
            'temperature': 25.0,
            'humidity': 70.0,
            'ph': 6.5,
            'rainfall': 800
        }
        
        criteria = {
            'maximize_yield': 0.4,
            'maximize_profit': 0.3,
            'minimize_water': 0.2,
            'minimize_inputs': 0.1
        }
        
        recommendation = advanced_model.optimize_multi_criteria(
            conditions, criteria
        )
        
        assert 'crop' in recommendation
        assert 'optimization_score' in recommendation
        assert 'tradeoffs' in recommendation
    
    def test_soil_health_consideration(self, advanced_model):
        """Test recommendations consider soil health."""
        degraded_soil = {
            'nitrogen': 30,  # Low
            'phosphorus': 20,  # Low
            'potassium': 25,  # Low
            'organic_matter': 1.5,  # Low
            'temperature': 25.0,
            'humidity': 70.0,
            'ph': 5.5,  # Acidic
            'rainfall': 800
        }
        
        recommendation = advanced_model.predict(
            degraded_soil, consider_soil_health=True
        )
        
        assert 'soil_improvement_needed' in recommendation
        assert 'amendments_suggested' in recommendation
        
        # Should recommend soil-improving crops
        assert recommendation.get('nitrogen_fixing', False) or \
               'legume' in recommendation.get('crop_family', '').lower()


@pytest.mark.ml
@pytest.mark.performance
class TestCropRecommendationPerformance:
    """Test crop recommendation model performance."""
    
    @pytest.fixture
    def model(self):
        """Create model instance."""
        return CropRecommendationModel()
    
    def test_prediction_speed(self, model, performance_timer):
        """Test single prediction speed."""
        input_data = CropRecommendationInputFactory.build()
        
        with performance_timer('crop_prediction'):
            for _ in range(100):
                model.predict(input_data)
        
        avg_time = performance_timer.get_average_time('crop_prediction')
        assert avg_time < 0.01  # Less than 10ms per prediction
    
    def test_batch_prediction_speed(self, model, performance_timer):
        """Test batch prediction speed."""
        batch_input = [
            CropRecommendationInputFactory.build() for _ in range(1000)
        ]
        
        with performance_timer('batch_prediction'):
            model.predict_batch(batch_input)
        
        total_time = performance_timer.get_average_time('batch_prediction')
        assert total_time < 1.0  # Less than 1 second for 1000 predictions
    
    def test_model_memory_usage(self, model):
        """Test model memory footprint."""
        import sys
        
        model_size = sys.getsizeof(model)
        
        # Model should be reasonably sized (< 100MB)
        assert model_size < 100 * 1024 * 1024
    
    def test_concurrent_predictions(self, model):
        """Test concurrent prediction handling."""
        import concurrent.futures
        
        def make_prediction():
            input_data = CropRecommendationInputFactory.build()
            return model.predict(input_data)
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(make_prediction) for _ in range(50)]
            results = [f.result() for f in futures]
        
        # All predictions should succeed
        assert len(results) == 50
        assert all('crop' in r for r in results)


@pytest.mark.ml
@pytest.mark.integration
class TestCropRecommendationAccuracy:
    """Test model accuracy and reliability."""
    
    @pytest.fixture
    def model(self):
        """Create model instance."""
        return CropRecommendationModel()
    
    def test_accuracy_on_known_cases(self, model):
        """Test accuracy on known good cases."""
        test_cases = [
            # (input, expected_crop)
            ({
                'nitrogen': 90, 'phosphorus': 60, 'potassium': 50,
                'temperature': 23.0, 'humidity': 65.0,
                'ph': 6.0, 'rainfall': 900
            }, 'maize'),
            ({
                'nitrogen': 60, 'phosphorus': 70, 'potassium': 55,
                'temperature': 22.0, 'humidity': 70.0,
                'ph': 6.5, 'rainfall': 750
            }, 'beans'),
            ({
                'nitrogen': 70, 'phosphorus': 50, 'potassium': 60,
                'temperature': 20.0, 'humidity': 75.0,
                'ph': 5.8, 'rainfall': 850
            }, 'potatoes'),
        ]
        
        correct = 0
        for input_data, expected in test_cases:
            prediction = model.predict(input_data, include_alternatives=True)
            
            # Check if expected is in top 3 recommendations
            all_crops = [prediction['crop']] + [
                alt['crop'] for alt in prediction.get('alternatives', [])[:2]
            ]
            
            if expected in all_crops:
                correct += 1
        
        accuracy = correct / len(test_cases)
        assert accuracy >= 0.7  # At least 70% accuracy
    
    def test_consistency_across_similar_inputs(self, model):
        """Test model gives consistent results for similar inputs."""
        base_input = {
            'nitrogen': 80,
            'phosphorus': 50,
            'potassium': 60,
            'temperature': 25.0,
            'humidity': 70.0,
            'ph': 6.5,
            'rainfall': 800
        }
        
        # Make slight variations
        predictions = []
        for i in range(5):
            varied_input = base_input.copy()
            varied_input['nitrogen'] += i * 2  # Small variation
            predictions.append(model.predict(varied_input))
        
        # All should recommend same crop
        crops = [p['crop'] for p in predictions]
        assert len(set(crops)) <= 2  # At most 2 different recommendations
    
    def test_robustness_to_noise(self, model):
        """Test model is robust to input noise."""
        clean_input = {
            'nitrogen': 80,
            'phosphorus': 50,
            'potassium': 60,
            'temperature': 25.0,
            'humidity': 70.0,
            'ph': 6.5,
            'rainfall': 800
        }
        
        clean_prediction = model.predict(clean_input)
        
        # Add 5% noise
        noisy_input = {
            k: v * (1 + np.random.uniform(-0.05, 0.05))
            for k, v in clean_input.items()
        }
        
        noisy_prediction = model.predict(noisy_input)
        
        # Should give similar results
        assert clean_prediction['crop'] == noisy_prediction['crop'] or \
               abs(clean_prediction['confidence'] - noisy_prediction['confidence']) < 0.15
