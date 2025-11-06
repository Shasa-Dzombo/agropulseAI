"""
ML Integration and Training Tests

Comprehensive tests for ML model training, integration, and end-to-end workflows.
"""

import pytest
import numpy as np
from datetime import datetime, timedelta

from app.ml.training_pipeline import TrainingPipeline
from app.ml.weather_integration import WeatherMLIntegration
from app.ml.soil_analysis import SoilAnalysisML
from app.ml.market_intelligence import MarketIntelligenceML
from tests.utils import (
    assert_in_range, assert_probability, calculate_metrics,
    MockWeatherAPI, generate_soil_data, generate_weather_data
)


@pytest.mark.ml
@pytest.mark.integration
class TestTrainingPipeline:
    """Test ML model training pipeline."""
    
    @pytest.fixture
    def pipeline(self):
        """Create training pipeline instance."""
        return TrainingPipeline()
    
    def test_pipeline_initialization(self, pipeline):
        """Test pipeline initializes correctly."""
        assert pipeline is not None
        assert hasattr(pipeline, 'train')
        assert hasattr(pipeline, 'evaluate')
    
    def test_data_loading(self, pipeline):
        """Test training data loading."""
        data = pipeline.load_training_data(
            model_type='crop_recommendation',
            data_path='training_data/crops.csv'
        )
        
        assert data is not None
        assert 'features' in data
        assert 'labels' in data
    
    def test_data_preprocessing(self, pipeline):
        """Test data preprocessing."""
        raw_data = {
            'features': np.random.rand(100, 7),
            'labels': np.random.randint(0, 10, 100)
        }
        
        processed = pipeline.preprocess_data(raw_data)
        
        assert 'X_train' in processed
        assert 'X_test' in processed
        assert 'y_train' in processed
        assert 'y_test' in processed
        
        # Check train/test split
        total_samples = len(raw_data['features'])
        assert len(processed['X_train']) + len(processed['X_test']) == total_samples
    
    def test_feature_scaling(self, pipeline):
        """Test feature scaling."""
        features = np.array([
            [100, 50, 60],
            [80, 40, 55],
            [90, 45, 58]
        ])
        
        scaled = pipeline.scale_features(features)
        
        # Scaled features should have mean ~0 and std ~1
        assert np.abs(scaled.mean()) < 0.1
        assert np.abs(scaled.std() - 1.0) < 0.2
    
    def test_model_training(self, pipeline):
        """Test model training."""
        training_data = {
            'X_train': np.random.rand(100, 7),
            'y_train': np.random.randint(0, 10, 100),
            'X_test': np.random.rand(20, 7),
            'y_test': np.random.randint(0, 10, 20)
        }
        
        model = pipeline.train(
            model_type='crop_recommendation',
            data=training_data,
            epochs=5
        )
        
        assert model is not None
        assert hasattr(model, 'predict')
    
    def test_model_evaluation(self, pipeline):
        """Test model evaluation."""
        training_data = {
            'X_train': np.random.rand(100, 7),
            'y_train': np.random.randint(0, 5, 100),
            'X_test': np.random.rand(20, 7),
            'y_test': np.random.randint(0, 5, 20)
        }
        
        model = pipeline.train(
            model_type='crop_recommendation',
            data=training_data,
            epochs=5
        )
        
        metrics = pipeline.evaluate(model, training_data)
        
        assert 'accuracy' in metrics
        assert 'precision' in metrics
        assert 'recall' in metrics
        assert 'f1_score' in metrics
        
        # Metrics should be between 0 and 1
        for metric_value in metrics.values():
            assert_in_range(metric_value, 0, 1)
    
    def test_hyperparameter_tuning(self, pipeline):
        """Test hyperparameter tuning."""
        training_data = {
            'X_train': np.random.rand(100, 7),
            'y_train': np.random.randint(0, 5, 100),
            'X_test': np.random.rand(20, 7),
            'y_test': np.random.randint(0, 5, 20)
        }
        
        param_grid = {
            'learning_rate': [0.001, 0.01, 0.1],
            'hidden_units': [32, 64, 128]
        }
        
        best_params = pipeline.tune_hyperparameters(
            model_type='crop_recommendation',
            data=training_data,
            param_grid=param_grid
        )
        
        assert 'learning_rate' in best_params
        assert 'hidden_units' in best_params
        assert best_params['learning_rate'] in param_grid['learning_rate']
    
    def test_cross_validation(self, pipeline):
        """Test cross-validation."""
        data = {
            'features': np.random.rand(100, 7),
            'labels': np.random.randint(0, 5, 100)
        }
        
        cv_scores = pipeline.cross_validate(
            model_type='crop_recommendation',
            data=data,
            k_folds=5
        )
        
        assert len(cv_scores) == 5
        assert all(0 <= score <= 1 for score in cv_scores)
    
    def test_model_saving(self, pipeline, temp_directory):
        """Test model saving."""
        import os
        
        training_data = {
            'X_train': np.random.rand(100, 7),
            'y_train': np.random.randint(0, 5, 100),
            'X_test': np.random.rand(20, 7),
            'y_test': np.random.randint(0, 5, 20)
        }
        
        model = pipeline.train(
            model_type='crop_recommendation',
            data=training_data,
            epochs=5
        )
        
        model_path = os.path.join(temp_directory, 'test_model.pkl')
        pipeline.save_model(model, model_path)
        
        assert os.path.exists(model_path)
    
    def test_model_loading(self, pipeline, temp_directory):
        """Test model loading."""
        import os
        
        training_data = {
            'X_train': np.random.rand(100, 7),
            'y_train': np.random.randint(0, 5, 100),
            'X_test': np.random.rand(20, 7),
            'y_test': np.random.randint(0, 5, 20)
        }
        
        # Train and save
        model = pipeline.train(
            model_type='crop_recommendation',
            data=training_data,
            epochs=5
        )
        
        model_path = os.path.join(temp_directory, 'test_model.pkl')
        pipeline.save_model(model, model_path)
        
        # Load
        loaded_model = pipeline.load_model(model_path)
        
        assert loaded_model is not None
        assert hasattr(loaded_model, 'predict')


@pytest.mark.ml
@pytest.mark.integration
class TestWeatherMLIntegration:
    """Test weather and ML integration."""
    
    @pytest.fixture
    def weather_ml(self):
        """Create weather ML integration instance."""
        return WeatherMLIntegration()
    
    @pytest.fixture
    def mock_weather_api(self):
        """Create mock weather API."""
        return MockWeatherAPI()
    
    def test_fetch_weather_data(self, weather_ml, mock_weather_api):
        """Test fetching weather data."""
        location = {'latitude': -1.286389, 'longitude': 36.817223}
        
        weather_data = weather_ml.fetch_weather_data(
            location,
            api=mock_weather_api
        )
        
        assert 'temperature' in weather_data
        assert 'humidity' in weather_data
        assert 'rainfall' in weather_data
    
    def test_growing_degree_days(self, weather_ml):
        """Test GDD calculation."""
        weather_data = [
            {'date': datetime.now() - timedelta(days=i), 'temp_max': 28, 'temp_min': 18}
            for i in range(30)
        ]
        
        gdd = weather_ml.calculate_growing_degree_days(
            weather_data,
            base_temp=10,
            ceiling_temp=30
        )
        
        assert gdd > 0
        assert gdd < 1000  # Reasonable range for 30 days
    
    def test_frost_risk_prediction(self, weather_ml):
        """Test frost risk prediction."""
        forecast = [
            {'date': datetime.now() + timedelta(days=i), 'temp_min': 5.0 - i}
            for i in range(7)
        ]
        
        risk = weather_ml.predict_frost_risk(forecast)
        
        assert 'risk_level' in risk
        assert risk['risk_level'] in ['none', 'low', 'medium', 'high']
        assert 'frost_dates' in risk
    
    def test_drought_stress_index(self, weather_ml):
        """Test drought stress index calculation."""
        weather_history = [
            {
                'date': datetime.now() - timedelta(days=i),
                'rainfall': 2.0 if i % 10 == 0 else 0.0,
                'evapotranspiration': 5.0
            }
            for i in range(60)
        ]
        
        stress_index = weather_ml.calculate_drought_stress(weather_history)
        
        assert_in_range(stress_index, 0, 1)
    
    def test_optimal_planting_window(self, weather_ml):
        """Test optimal planting window prediction."""
        location = {'latitude': -1.286389, 'longitude': 36.817223}
        crop = 'maize'
        
        window = weather_ml.predict_planting_window(location, crop)
        
        assert 'start_date' in window
        assert 'end_date' in window
        assert 'confidence' in window
        assert_probability(window['confidence'])
    
    def test_harvest_timing_prediction(self, weather_ml):
        """Test harvest timing prediction."""
        planting_date = datetime.now() - timedelta(days=90)
        crop = 'maize'
        weather_forecast = generate_weather_data(days=30)
        
        harvest_prediction = weather_ml.predict_harvest_timing(
            crop,
            planting_date,
            weather_forecast
        )
        
        assert 'recommended_date' in harvest_prediction
        assert 'maturity_status' in harvest_prediction


@pytest.mark.ml
@pytest.mark.integration
class TestSoilAnalysisML:
    """Test soil analysis ML models."""
    
    @pytest.fixture
    def soil_ml(self):
        """Create soil analysis ML instance."""
        return SoilAnalysisML()
    
    def test_soil_type_classification(self, soil_ml):
        """Test soil type classification."""
        soil_properties = {
            'sand_percent': 40,
            'silt_percent': 35,
            'clay_percent': 25,
            'organic_matter': 3.5,
            'ph': 6.5
        }
        
        classification = soil_ml.classify_soil_type(soil_properties)
        
        assert 'soil_type' in classification
        assert classification['soil_type'] in [
            'clay', 'sandy', 'loam', 'sandy_loam', 'clay_loam',
            'silt_loam', 'sandy_clay', 'silty_clay', 'silt',
            'clay_loam', 'sandy_clay_loam', 'silty_clay_loam'
        ]
    
    def test_nutrient_deficiency_detection(self, soil_ml):
        """Test nutrient deficiency detection."""
        soil_test = {
            'nitrogen': 25,  # Low
            'phosphorus': 15,  # Low
            'potassium': 80,  # Good
            'ph': 5.5,
            'organic_matter': 2.0
        }
        
        deficiencies = soil_ml.detect_deficiencies(soil_test)
        
        assert 'deficient_nutrients' in deficiencies
        assert 'nitrogen' in deficiencies['deficient_nutrients']
        assert 'phosphorus' in deficiencies['deficient_nutrients']
    
    def test_fertilizer_recommendation(self, soil_ml):
        """Test fertilizer recommendations."""
        soil_test = {
            'nitrogen': 40,
            'phosphorus': 30,
            'potassium': 50,
            'ph': 6.0
        }
        crop = 'maize'
        target_yield = 9000  # kg/ha
        
        recommendation = soil_ml.recommend_fertilizer(
            soil_test,
            crop,
            target_yield
        )
        
        assert 'npk_ratio' in recommendation
        assert 'application_rate' in recommendation
        assert 'estimated_cost' in recommendation
    
    def test_soil_health_score(self, soil_ml):
        """Test soil health scoring."""
        soil_data = {
            'organic_matter': 3.5,
            'ph': 6.5,
            'nitrogen': 80,
            'phosphorus': 50,
            'potassium': 60,
            'bulk_density': 1.3,
            'water_holding_capacity': 0.35
        }
        
        health_score = soil_ml.calculate_health_score(soil_data)
        
        assert 'overall_score' in health_score
        assert_in_range(health_score['overall_score'], 0, 100)
        assert 'component_scores' in health_score
    
    def test_soil_amendment_plan(self, soil_ml):
        """Test soil amendment planning."""
        current_soil = generate_soil_data('sandy')
        target_improvements = {
            'increase_organic_matter': 1.0,
            'adjust_ph': 6.5,
            'boost_nitrogen': 80
        }
        
        amendment_plan = soil_ml.create_amendment_plan(
            current_soil,
            target_improvements
        )
        
        assert 'amendments' in amendment_plan
        assert 'timeline' in amendment_plan
        assert 'estimated_cost' in amendment_plan


@pytest.mark.ml
@pytest.mark.integration
class TestMarketIntelligenceML:
    """Test market intelligence ML models."""
    
    @pytest.fixture
    def market_ml(self):
        """Create market intelligence ML instance."""
        return MarketIntelligenceML()
    
    def test_price_prediction(self, market_ml):
        """Test crop price prediction."""
        crop = 'maize'
        location = 'nairobi'
        forecast_days = 30
        
        price_forecast = market_ml.predict_prices(
            crop,
            location,
            forecast_days
        )
        
        assert 'forecast' in price_forecast
        assert len(price_forecast['forecast']) == forecast_days
        
        for daily_forecast in price_forecast['forecast']:
            assert 'date' in daily_forecast
            assert 'predicted_price' in daily_forecast
            assert daily_forecast['predicted_price'] > 0
    
    def test_price_trend_analysis(self, market_ml):
        """Test price trend analysis."""
        historical_prices = [
            {'date': datetime.now() - timedelta(days=i), 'price': 30 + i * 0.1}
            for i in range(90)
        ]
        
        trend = market_ml.analyze_price_trend(historical_prices)
        
        assert 'trend_direction' in trend
        assert trend['trend_direction'] in ['upward', 'downward', 'stable']
        assert 'volatility' in trend
    
    def test_profitability_analysis(self, market_ml):
        """Test profitability analysis."""
        crop_data = {
            'crop': 'maize',
            'expected_yield': 9000,  # kg
            'field_size': 10.0,  # hectares
            'input_costs': 150000,  # KES
            'labor_costs': 50000,
            'other_costs': 30000
        }
        
        current_price = 35  # KES per kg
        
        analysis = market_ml.analyze_profitability(crop_data, current_price)
        
        assert 'total_revenue' in analysis
        assert 'total_costs' in analysis
        assert 'profit' in analysis
        assert 'roi' in analysis
    
    def test_market_demand_prediction(self, market_ml):
        """Test market demand prediction."""
        crop = 'beans'
        region = 'central'
        
        demand = market_ml.predict_demand(crop, region)
        
        assert 'demand_level' in demand
        assert demand['demand_level'] in ['low', 'medium', 'high']
        assert 'confidence' in demand
        assert_probability(demand['confidence'])
    
    def test_optimal_selling_time(self, market_ml):
        """Test optimal selling time prediction."""
        crop = 'maize'
        harvest_date = datetime.now()
        storage_capacity_months = 6
        
        optimal_time = market_ml.predict_optimal_selling_time(
            crop,
            harvest_date,
            storage_capacity_months
        )
        
        assert 'recommended_date' in optimal_time
        assert 'expected_price' in optimal_time
        assert 'storage_cost' in optimal_time
    
    def test_supply_demand_balance(self, market_ml):
        """Test supply-demand balance analysis."""
        crop = 'potatoes'
        region = 'rift_valley'
        
        balance = market_ml.analyze_supply_demand(crop, region)
        
        assert 'balance_indicator' in balance
        assert 'surplus_deficit' in balance
        assert 'market_recommendation' in balance


@pytest.mark.ml
@pytest.mark.integration
class TestMLModelIntegration:
    """Test integration between multiple ML models."""
    
    def test_crop_to_yield_pipeline(self):
        """Test crop recommendation to yield prediction pipeline."""
        from app.ml.crop_recommendation import CropRecommendationModel
        from app.ml.yield_prediction import YieldPredictionModel
        
        crop_model = CropRecommendationModel()
        yield_model = YieldPredictionModel()
        
        # Get crop recommendation
        soil_conditions = {
            'nitrogen': 80,
            'phosphorus': 50,
            'potassium': 60,
            'temperature': 25.0,
            'humidity': 70.0,
            'ph': 6.5,
            'rainfall': 800
        }
        
        crop_rec = crop_model.predict(soil_conditions)
        
        # Predict yield for recommended crop
        yield_input = soil_conditions.copy()
        yield_input.update({
            'crop_type': crop_rec['crop'],
            'field_size': 10.0,
            'growth_days': 90
        })
        
        yield_pred = yield_model.predict(yield_input)
        
        assert yield_pred['predicted_yield'] > 0
    
    def test_weather_to_planting_pipeline(self):
        """Test weather integration to crop recommendation."""
        weather_ml = WeatherMLIntegration()
        crop_model = CropRecommendationModel()
        
        # Get weather-adjusted conditions
        location = {'latitude': -1.286389, 'longitude': 36.817223}
        weather_data = generate_weather_data(days=30)
        
        adjusted_conditions = weather_ml.adjust_for_weather(
            weather_data,
            base_conditions={
                'nitrogen': 80,
                'phosphorus': 50,
                'potassium': 60,
                'ph': 6.5
            }
        )
        
        # Get crop recommendation
        crop_rec = crop_model.predict(adjusted_conditions)
        
        assert 'crop' in crop_rec
        assert 'confidence' in crop_rec
    
    def test_soil_to_fertilizer_to_yield(self):
        """Test soil analysis to fertilizer to yield prediction."""
        soil_ml = SoilAnalysisML()
        yield_model = YieldPredictionModel()
        
        # Analyze soil
        soil_test = {
            'nitrogen': 40,
            'phosphorus': 30,
            'potassium': 50,
            'ph': 6.0
        }
        
        fertilizer_rec = soil_ml.recommend_fertilizer(
            soil_test,
            crop='maize',
            target_yield=9000
        )
        
        # Predict yield with fertilizer applied
        adjusted_soil = soil_test.copy()
        adjusted_soil['nitrogen'] += fertilizer_rec['npk_ratio']['n']
        adjusted_soil['phosphorus'] += fertilizer_rec['npk_ratio']['p']
        adjusted_soil['potassium'] += fertilizer_rec['npk_ratio']['k']
        
        yield_input = {
            'crop_type': 'maize',
            'field_size': 10.0,
            'soil_nitrogen': adjusted_soil['nitrogen'],
            'soil_phosphorus': adjusted_soil['phosphorus'],
            'soil_potassium': adjusted_soil['potassium'],
            'temperature': 25.0,
            'rainfall': 800,
            'growth_days': 90
        }
        
        yield_pred = yield_model.predict(yield_input)
        
        assert yield_pred['predicted_yield'] >= 8500  # Should be close to target


@pytest.mark.ml
@pytest.mark.slow
class TestMLModelRetraining:
    """Test model retraining and updates."""
    
    def test_incremental_training(self):
        """Test incremental model training."""
        pipeline = TrainingPipeline()
        
        # Initial training
        initial_data = {
            'X_train': np.random.rand(100, 7),
            'y_train': np.random.randint(0, 5, 100),
            'X_test': np.random.rand(20, 7),
            'y_test': np.random.randint(0, 5, 20)
        }
        
        model = pipeline.train(
            model_type='crop_recommendation',
            data=initial_data,
            epochs=5
        )
        
        # Incremental training
        new_data = {
            'X_train': np.random.rand(50, 7),
            'y_train': np.random.randint(0, 5, 50)
        }
        
        updated_model = pipeline.incremental_train(
            model,
            new_data,
            epochs=2
        )
        
        assert updated_model is not None
    
    def test_model_versioning(self, temp_directory):
        """Test model version management."""
        import os
        
        pipeline = TrainingPipeline()
        
        training_data = {
            'X_train': np.random.rand(100, 7),
            'y_train': np.random.randint(0, 5, 100),
            'X_test': np.random.rand(20, 7),
            'y_test': np.random.randint(0, 5, 20)
        }
        
        # Train multiple versions
        for version in range(1, 4):
            model = pipeline.train(
                model_type='crop_recommendation',
                data=training_data,
                epochs=5
            )
            
            model_path = os.path.join(
                temp_directory,
                f'model_v{version}.pkl'
            )
            pipeline.save_model(model, model_path, version=version)
        
        # Check all versions exist
        for version in range(1, 4):
            model_path = os.path.join(
                temp_directory,
                f'model_v{version}.pkl'
            )
            assert os.path.exists(model_path)
