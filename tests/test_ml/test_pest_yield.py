"""
Pest Detection and Yield Prediction ML Tests

Comprehensive tests for pest/disease detection and yield prediction models.
"""

import pytest
import numpy as np
from PIL import Image
import io

from app.ml.pest_detection import PestDetectionModel
from app.ml.yield_prediction import YieldPredictionModel
from tests.utils import (
    create_mock_image_bytes, assert_probability, assert_in_range,
    calculate_metrics, assert_model_performance
)


@pytest.mark.ml
@pytest.mark.unit
class TestPestDetectionModel:
    """Test pest detection CNN model."""
    
    @pytest.fixture
    def model(self):
        """Create pest detection model instance."""
        return PestDetectionModel()
    
    @pytest.fixture
    def test_image(self):
        """Create test image."""
        return create_mock_image_bytes(224, 224)
    
    def test_model_initialization(self, model):
        """Test model initializes correctly."""
        assert model is not None
        assert hasattr(model, 'predict')
        assert hasattr(model, 'detect_pest')
    
    def test_predict_with_image(self, model, test_image):
        """Test prediction with image input."""
        prediction = model.predict(test_image)
        
        assert 'pest_detected' in prediction
        assert 'pest_type' in prediction
        assert 'confidence' in prediction
        assert_probability(prediction['confidence'])
    
    def test_detect_multiple_pests(self, model, test_image):
        """Test detecting multiple pests in image."""
        prediction = model.predict(test_image, detect_multiple=True)
        
        assert 'detections' in prediction
        assert isinstance(prediction['detections'], list)
        
        for detection in prediction['detections']:
            assert 'pest_type' in detection
            assert 'confidence' in detection
            assert 'bounding_box' in detection
    
    def test_image_preprocessing(self, model):
        """Test image preprocessing."""
        # Create image with different size
        large_image = create_mock_image_bytes(512, 512)
        
        processed = model.preprocess_image(large_image)
        
        # Should be resized to model input size
        assert processed.shape == (224, 224, 3) or \
               processed.shape == (1, 224, 224, 3)
    
    def test_pest_classification(self, model, test_image):
        """Test pest classification."""
        prediction = model.predict(test_image)
        
        # Check valid pest types
        valid_pests = [
            'armyworm', 'aphid', 'whitefly', 'thrips', 'mealybug',
            'leaf_miner', 'stem_borer', 'cutworm', 'healthy'
        ]
        
        assert prediction['pest_type'] in valid_pests
    
    def test_confidence_threshold(self, model, test_image):
        """Test confidence threshold filtering."""
        prediction = model.predict(test_image, confidence_threshold=0.8)
        
        if prediction['pest_detected']:
            assert prediction['confidence'] >= 0.8
    
    def test_treatment_recommendation(self, model, test_image):
        """Test pest treatment recommendations."""
        prediction = model.predict(test_image, include_treatment=True)
        
        if prediction['pest_detected']:
            assert 'treatment' in prediction
            assert 'pesticide' in prediction['treatment']
            assert 'organic_alternative' in prediction['treatment']
            assert 'application_rate' in prediction['treatment']
    
    def test_severity_assessment(self, model, test_image):
        """Test pest severity assessment."""
        prediction = model.predict(test_image, assess_severity=True)
        
        if prediction['pest_detected']:
            assert 'severity' in prediction
            assert prediction['severity'] in ['low', 'medium', 'high', 'critical']
    
    def test_batch_image_processing(self, model):
        """Test batch image processing."""
        images = [create_mock_image_bytes(224, 224) for _ in range(10)]
        
        predictions = model.predict_batch(images)
        
        assert len(predictions) == 10
        assert all('pest_detected' in p for p in predictions)
    
    def test_invalid_image_handling(self, model):
        """Test handling of invalid image data."""
        invalid_image = b"not an image"
        
        with pytest.raises((ValueError, IOError)):
            model.predict(invalid_image)
    
    def test_image_format_support(self, model):
        """Test support for different image formats."""
        formats = ['JPEG', 'PNG', 'BMP']
        
        for fmt in formats:
            img = Image.new('RGB', (224, 224), color='green')
            buffer = io.BytesIO()
            img.save(buffer, format=fmt)
            image_bytes = buffer.getvalue()
            
            prediction = model.predict(image_bytes)
            assert 'pest_detected' in prediction
    
    def test_feature_extraction(self, model, test_image):
        """Test CNN feature extraction."""
        features = model.extract_features(test_image)
        
        assert isinstance(features, np.ndarray)
        assert len(features.shape) >= 1
        assert features.shape[0] > 0


@pytest.mark.ml
@pytest.mark.integration
class TestPestDetectionAccuracy:
    """Test pest detection accuracy."""
    
    @pytest.fixture
    def model(self):
        """Create model instance."""
        return PestDetectionModel()
    
    def test_healthy_plant_detection(self, model):
        """Test detection of healthy plants."""
        # Create green image (simulating healthy plant)
        img = Image.new('RGB', (224, 224), color='green')
        buffer = io.BytesIO()
        img.save(buffer, format='JPEG')
        image_bytes = buffer.getvalue()
        
        prediction = model.predict(image_bytes)
        
        # Should have low pest detection confidence
        if prediction['pest_detected']:
            assert prediction['confidence'] < 0.7 or \
                   prediction['pest_type'] == 'healthy'
    
    def test_consistency_across_rotations(self, model):
        """Test model consistency across image rotations."""
        img = Image.new('RGB', (224, 224), color=(150, 100, 50))
        
        predictions = []
        for angle in [0, 90, 180, 270]:
            rotated = img.rotate(angle)
            buffer = io.BytesIO()
            rotated.save(buffer, format='JPEG')
            image_bytes = buffer.getvalue()
            
            prediction = model.predict(image_bytes)
            predictions.append(prediction)
        
        # Should give similar results
        pest_types = [p['pest_type'] for p in predictions]
        assert len(set(pest_types)) <= 2


@pytest.mark.ml
@pytest.mark.unit
class TestYieldPredictionModel:
    """Test yield prediction model."""
    
    @pytest.fixture
    def model(self):
        """Create yield prediction model instance."""
        return YieldPredictionModel()
    
    def test_model_initialization(self, model):
        """Test model initializes correctly."""
        assert model is not None
        assert hasattr(model, 'predict')
        assert hasattr(model, 'forecast')
    
    def test_predict_yield(self, model):
        """Test yield prediction."""
        input_data = {
            'crop_type': 'maize',
            'field_size': 10.0,
            'soil_nitrogen': 80,
            'soil_phosphorus': 50,
            'soil_potassium': 60,
            'temperature': 25.0,
            'rainfall': 800,
            'growth_days': 90
        }
        
        prediction = model.predict(input_data)
        
        assert 'predicted_yield' in prediction
        assert 'confidence_interval' in prediction
        assert 'unit' in prediction
        assert prediction['predicted_yield'] > 0
    
    def test_yield_by_crop_type(self, model):
        """Test yield predictions for different crops."""
        base_input = {
            'field_size': 10.0,
            'soil_nitrogen': 80,
            'soil_phosphorus': 50,
            'soil_potassium': 60,
            'temperature': 25.0,
            'rainfall': 800,
            'growth_days': 90
        }
        
        crops = ['maize', 'beans', 'potatoes', 'wheat']
        predictions = {}
        
        for crop in crops:
            input_data = base_input.copy()
            input_data['crop_type'] = crop
            predictions[crop] = model.predict(input_data)
        
        # Yields should vary by crop
        yields = [p['predicted_yield'] for p in predictions.values()]
        assert len(set(yields)) > 1
    
    def test_time_series_forecast(self, model):
        """Test time series yield forecasting."""
        historical_data = [
            {'year': 2020, 'yield': 8500},
            {'year': 2021, 'yield': 9200},
            {'year': 2022, 'yield': 8800},
            {'year': 2023, 'yield': 9500},
        ]
        
        forecast = model.forecast(historical_data, periods=2)
        
        assert 'forecast' in forecast
        assert len(forecast['forecast']) == 2
        assert all('year' in f for f in forecast['forecast'])
        assert all('predicted_yield' in f for f in forecast['forecast'])
    
    def test_confidence_intervals(self, model):
        """Test confidence interval calculation."""
        input_data = {
            'crop_type': 'maize',
            'field_size': 10.0,
            'soil_nitrogen': 80,
            'soil_phosphorus': 50,
            'soil_potassium': 60,
            'temperature': 25.0,
            'rainfall': 800,
            'growth_days': 90
        }
        
        prediction = model.predict(input_data, confidence_level=0.95)
        
        assert 'confidence_interval' in prediction
        ci = prediction['confidence_interval']
        assert 'lower' in ci
        assert 'upper' in ci
        assert ci['lower'] < prediction['predicted_yield'] < ci['upper']
    
    def test_weather_impact(self, model):
        """Test impact of weather on yield."""
        base_input = {
            'crop_type': 'maize',
            'field_size': 10.0,
            'soil_nitrogen': 80,
            'soil_phosphorus': 50,
            'soil_potassium': 60,
            'temperature': 25.0,
            'growth_days': 90
        }
        
        # Low rainfall
        low_rain = base_input.copy()
        low_rain['rainfall'] = 400
        low_pred = model.predict(low_rain)
        
        # High rainfall
        high_rain = base_input.copy()
        high_rain['rainfall'] = 1200
        high_pred = model.predict(high_rain)
        
        # Optimal rainfall
        optimal_rain = base_input.copy()
        optimal_rain['rainfall'] = 800
        optimal_pred = model.predict(optimal_rain)
        
        # Optimal should have highest yield
        assert optimal_pred['predicted_yield'] >= low_pred['predicted_yield']
    
    def test_nutrient_impact(self, model):
        """Test impact of soil nutrients on yield."""
        base_input = {
            'crop_type': 'maize',
            'field_size': 10.0,
            'temperature': 25.0,
            'rainfall': 800,
            'growth_days': 90
        }
        
        # Low nutrients
        low_nutrients = base_input.copy()
        low_nutrients.update({
            'soil_nitrogen': 30,
            'soil_phosphorus': 20,
            'soil_potassium': 25
        })
        low_pred = model.predict(low_nutrients)
        
        # High nutrients
        high_nutrients = base_input.copy()
        high_nutrients.update({
            'soil_nitrogen': 120,
            'soil_phosphorus': 80,
            'soil_potassium': 90
        })
        high_pred = model.predict(high_nutrients)
        
        # Higher nutrients should give better yield
        assert high_pred['predicted_yield'] > low_pred['predicted_yield']
    
    def test_growth_stage_prediction(self, model):
        """Test yield prediction at different growth stages."""
        base_input = {
            'crop_type': 'maize',
            'field_size': 10.0,
            'soil_nitrogen': 80,
            'soil_phosphorus': 50,
            'soil_potassium': 60,
            'temperature': 25.0,
            'rainfall': 800
        }
        
        stages = [30, 60, 90, 120]  # days
        predictions = []
        
        for days in stages:
            input_data = base_input.copy()
            input_data['growth_days'] = days
            pred = model.predict(input_data)
            predictions.append(pred)
        
        # Confidence should increase with growth stage
        confidences = [p.get('confidence', 0.5) for p in predictions]
        assert confidences[-1] > confidences[0]
    
    def test_yield_per_hectare(self, model):
        """Test yield calculation per hectare."""
        input_data = {
            'crop_type': 'maize',
            'field_size': 5.0,
            'soil_nitrogen': 80,
            'soil_phosphorus': 50,
            'soil_potassium': 60,
            'temperature': 25.0,
            'rainfall': 800,
            'growth_days': 90
        }
        
        prediction = model.predict(input_data)
        
        assert 'yield_per_hectare' in prediction
        assert prediction['yield_per_hectare'] > 0
    
    def test_historical_comparison(self, model):
        """Test comparison with historical yields."""
        input_data = {
            'crop_type': 'maize',
            'field_size': 10.0,
            'soil_nitrogen': 80,
            'soil_phosphorus': 50,
            'soil_potassium': 60,
            'temperature': 25.0,
            'rainfall': 800,
            'growth_days': 90
        }
        
        historical_avg = 8500  # kg
        
        prediction = model.predict(
            input_data,
            historical_average=historical_avg
        )
        
        assert 'comparison_to_historical' in prediction
        assert 'percentage_difference' in prediction


@pytest.mark.ml
@pytest.mark.integration
class TestYieldPredictionAccuracy:
    """Test yield prediction accuracy."""
    
    @pytest.fixture
    def model(self):
        """Create model instance."""
        return YieldPredictionModel()
    
    def test_realistic_yield_ranges(self, model):
        """Test predictions are within realistic ranges."""
        input_data = {
            'crop_type': 'maize',
            'field_size': 10.0,
            'soil_nitrogen': 80,
            'soil_phosphorus': 50,
            'soil_potassium': 60,
            'temperature': 25.0,
            'rainfall': 800,
            'growth_days': 90
        }
        
        prediction = model.predict(input_data)
        
        # Maize yield typically 3,000-12,000 kg/ha
        yield_per_ha = prediction['yield_per_hectare']
        assert_in_range(yield_per_ha, 1000, 15000)
    
    def test_prediction_stability(self, model):
        """Test prediction stability."""
        input_data = {
            'crop_type': 'maize',
            'field_size': 10.0,
            'soil_nitrogen': 80,
            'soil_phosphorus': 50,
            'soil_potassium': 60,
            'temperature': 25.0,
            'rainfall': 800,
            'growth_days': 90
        }
        
        # Make multiple predictions
        predictions = [model.predict(input_data) for _ in range(5)]
        yields = [p['predicted_yield'] for p in predictions]
        
        # Should be identical (deterministic)
        assert len(set(yields)) == 1


@pytest.mark.ml
@pytest.mark.performance
class TestMLModelPerformance:
    """Test ML model performance."""
    
    def test_pest_detection_speed(self, performance_timer):
        """Test pest detection inference speed."""
        model = PestDetectionModel()
        test_image = create_mock_image_bytes(224, 224)
        
        with performance_timer('pest_detection'):
            for _ in range(10):
                model.predict(test_image)
        
        avg_time = performance_timer.get_average_time('pest_detection')
        assert avg_time < 0.5  # Less than 500ms per prediction
    
    def test_yield_prediction_speed(self, performance_timer):
        """Test yield prediction speed."""
        model = YieldPredictionModel()
        input_data = {
            'crop_type': 'maize',
            'field_size': 10.0,
            'soil_nitrogen': 80,
            'soil_phosphorus': 50,
            'soil_potassium': 60,
            'temperature': 25.0,
            'rainfall': 800,
            'growth_days': 90
        }
        
        with performance_timer('yield_prediction'):
            for _ in range(100):
                model.predict(input_data)
        
        avg_time = performance_timer.get_average_time('yield_prediction')
        assert avg_time < 0.05  # Less than 50ms per prediction
