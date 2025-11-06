"""
GraphQL API Server
==================

Comprehensive GraphQL API for AgroPulse platform with queries, mutations,
subscriptions, and real-time capabilities.
"""

import graphene
from graphene import relay, ObjectType, String, Float, Int, Boolean, List, Field, DateTime, ID
from graphene_sqlalchemy import SQLAlchemyObjectType, SQLAlchemyConnectionField
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)


# GraphQL Types
class FarmerType(ObjectType):
    """Farmer GraphQL type."""
    class Meta:
        interfaces = (relay.Node,)
        
    id = ID(required=True)
    name = String(required=True)
    email = String()
    phone = String()
    location = String()
    farm_size = Float()
    crops = List(lambda: CropType)
    sensors = List(lambda: SensorType)
    payments = List(lambda: PaymentType)
    created_at = DateTime()


class CropType(ObjectType):
    """Crop GraphQL type."""
    class Meta:
        interfaces = (relay.Node,)
        
    id = ID(required=True)
    name = String(required=True)
    variety = String()
    planting_date = DateTime()
    expected_harvest_date = DateTime()
    actual_harvest_date = DateTime()
    area_hectares = Float()
    expected_yield = Float()
    actual_yield = Float()
    status = String()
    farmer = Field(FarmerType)


class SensorType(ObjectType):
    """Sensor GraphQL type."""
    class Meta:
        interfaces = (relay.Node,)
        
    id = ID(required=True)
    device_id = String(required=True)
    sensor_type = String()
    location_lat = Float()
    location_lon = Float()
    status = String()
    battery_level = Float()
    last_reading = DateTime()
    readings = List(lambda: SensorReadingType)


class SensorReadingType(ObjectType):
    """Sensor reading GraphQL type."""
    class Meta:
        interfaces = (relay.Node,)
        
    id = ID(required=True)
    sensor_id = ID(required=True)
    timestamp = DateTime(required=True)
    temperature = Float()
    humidity = Float()
    soil_moisture = Float()
    light_intensity = Float()
    rainfall = Float()


class WeatherForecastType(ObjectType):
    """Weather forecast GraphQL type."""
    timestamp = DateTime(required=True)
    temperature = Float()
    rainfall = Float()
    humidity = Float()
    wind_speed = Float()
    description = String()


class PaymentType(ObjectType):
    """Payment GraphQL type."""
    class Meta:
        interfaces = (relay.Node,)
        
    id = ID(required=True)
    transaction_id = String(required=True)
    farmer_id = ID(required=True)
    amount_local = Float(required=True)
    amount_usd = Float(required=True)
    currency = String(required=True)
    payment_method = String()
    status = String(required=True)
    created_at = DateTime()


class CropRecommendationType(ObjectType):
    """Crop recommendation GraphQL type."""
    crop_name = String(required=True)
    score = Float(required=True)
    confidence = Float(required=True)
    reasoning = List(String)
    expected_yield = Float()
    expected_revenue = Float()
    growing_days = Int()


class MarketPriceType(ObjectType):
    """Market price GraphQL type."""
    commodity = String(required=True)
    price = Float(required=True)
    currency = String(required=True)
    market_name = String()
    timestamp = DateTime(required=True)
    trend = String()  # 'rising', 'falling', 'stable'


# GraphQL Queries
class Query(ObjectType):
    """Root query type."""
    node = relay.Node.Field()
    
    # Farmer queries
    farmer = Field(FarmerType, id=ID(required=True))
    all_farmers = List(FarmerType, limit=Int(), offset=Int())
    search_farmers = List(FarmerType, query=String(required=True))
    
    # Crop queries
    crop = Field(CropType, id=ID(required=True))
    crops_by_farmer = List(CropType, farmer_id=ID(required=True))
    crops_by_status = List(CropType, status=String(required=True))
    
    # Sensor queries
    sensor = Field(SensorType, id=ID(required=True))
    sensors_by_farmer = List(SensorType, farmer_id=ID(required=True))
    sensor_readings = List(
        SensorReadingType,
        sensor_id=ID(required=True),
        start_date=DateTime(),
        end_date=DateTime(),
        limit=Int()
    )
    
    # Weather queries
    current_weather = Field(
        lambda: WeatherDataType,
        latitude=Float(required=True),
        longitude=Float(required=True)
    )
    weather_forecast = List(
        WeatherForecastType,
        latitude=Float(required=True),
        longitude=Float(required=True),
        days=Int()
    )
    
    # Payment queries
    payment = Field(PaymentType, id=ID(required=True))
    payments_by_farmer = List(PaymentType, farmer_id=ID(required=True))
    payment_statistics = Field(
        lambda: PaymentStatisticsType,
        farmer_id=ID(),
        start_date=DateTime(),
        end_date=DateTime()
    )
    
    # Recommendation queries
    crop_recommendations = List(
        CropRecommendationType,
        soil_ph=Float(required=True),
        temperature=Float(required=True),
        rainfall=Float(required=True),
        farm_size=Float(required=True),
        investment_level=String(),
        skill_level=String(),
        top_k=Int()
    )
    
    # Market queries
    market_prices = List(
        MarketPriceType,
        commodity=String(),
        market=String(),
        start_date=DateTime(),
        end_date=DateTime()
    )
    price_forecast = List(
        MarketPriceType,
        commodity=String(required=True),
        days=Int(required=True)
    )
    
    # Analytics queries
    farm_analytics = Field(
        lambda: FarmAnalyticsType,
        farmer_id=ID(required=True),
        start_date=DateTime(),
        end_date=DateTime()
    )
    
    # Resolvers
    def resolve_farmer(self, info, id):
        """Resolve single farmer."""
        # In production, query database
        return FarmerType(
            id=id,
            name="John Doe",
            email="john@example.com",
            phone="+254712345678",
            location="Nairobi, Kenya",
            farm_size=5.0,
        )
        
    def resolve_all_farmers(self, info, limit=100, offset=0):
        """Resolve all farmers with pagination."""
        # In production, query database with pagination
        return []
        
    def resolve_crop_recommendations(
        self,
        info,
        soil_ph,
        temperature,
        rainfall,
        farm_size,
        investment_level='medium',
        skill_level='beginner',
        top_k=5
    ):
        """Resolve crop recommendations."""
        from app.ml.recommendations.recommendation_engine import CropRecommendationEngine
        
        engine = CropRecommendationEngine()
        recommendations = engine.recommend_crops(
            soil_ph=soil_ph,
            avg_temperature=temperature,
            annual_rainfall=rainfall,
            farm_size=farm_size,
            investment_capacity=investment_level,
            skill_level=skill_level,
            top_k=top_k,
        )
        
        return [
            CropRecommendationType(
                crop_name=rec.item_name,
                score=rec.score,
                confidence=rec.confidence,
                reasoning=rec.reasoning,
                expected_yield=rec.metadata.get('expected_yield_kg'),
                expected_revenue=rec.metadata.get('expected_revenue_usd'),
                growing_days=rec.metadata.get('growing_days'),
            )
            for rec in recommendations
        ]
        
    def resolve_weather_forecast(self, info, latitude, longitude, days=7):
        """Resolve weather forecast."""
        from app.integrations.weather.openweather import OpenWeatherMapClient
        import os
        
        api_key = os.getenv('OPENWEATHER_API_KEY', '')
        if not api_key:
            return []
            
        client = OpenWeatherMapClient(api_key=api_key)
        forecasts = client.get_5day_forecast(latitude, longitude)
        
        return [
            WeatherForecastType(
                timestamp=f.timestamp,
                temperature=f.temperature,
                rainfall=f.rainfall,
                humidity=f.humidity,
                wind_speed=f.wind_speed,
                description=f.description,
            )
            for f in forecasts[:days*8]  # 8 readings per day (3-hour intervals)
        ]


# GraphQL Mutations
class CreateFarmerMutation(graphene.Mutation):
    """Create new farmer."""
    class Arguments:
        name = String(required=True)
        email = String()
        phone = String(required=True)
        location = String()
        farm_size = Float()
        
    farmer = Field(lambda: FarmerType)
    success = Boolean()
    message = String()
    
    def mutate(self, info, name, phone, email=None, location=None, farm_size=None):
        """Execute farmer creation."""
        logger.info(f"Creating farmer: {name}")
        
        # In production, save to database
        farmer = FarmerType(
            id="new_farmer_id",
            name=name,
            email=email,
            phone=phone,
            location=location,
            farm_size=farm_size,
        )
        
        return CreateFarmerMutation(
            farmer=farmer,
            success=True,
            message="Farmer created successfully"
        )


class UpdateCropMutation(graphene.Mutation):
    """Update crop information."""
    class Arguments:
        crop_id = ID(required=True)
        status = String()
        actual_yield = Float()
        actual_harvest_date = DateTime()
        
    crop = Field(lambda: CropType)
    success = Boolean()
    message = String()
    
    def mutate(self, info, crop_id, status=None, actual_yield=None, actual_harvest_date=None):
        """Execute crop update."""
        logger.info(f"Updating crop: {crop_id}")
        
        # In production, update database
        crop = CropType(
            id=crop_id,
            name="Maize",
            status=status or "growing",
            actual_yield=actual_yield,
            actual_harvest_date=actual_harvest_date,
        )
        
        return UpdateCropMutation(
            crop=crop,
            success=True,
            message="Crop updated successfully"
        )


class ProcessPaymentMutation(graphene.Mutation):
    """Process payment."""
    class Arguments:
        farmer_id = ID(required=True)
        amount = Float(required=True)
        currency = String(required=True)
        payment_method = String(required=True)
        
    payment = Field(lambda: PaymentType)
    success = Boolean()
    message = String()
    
    def mutate(self, info, farmer_id, amount, currency, payment_method):
        """Execute payment processing."""
        from app.integrations.payments.payment_router import PaymentRouter
        from decimal import Decimal
        
        logger.info(f"Processing payment: {amount} {currency} for farmer {farmer_id}")
        
        # In production, process payment through gateway
        payment = PaymentType(
            id="new_payment_id",
            transaction_id="TXN123456",
            farmer_id=farmer_id,
            amount_local=amount,
            amount_usd=amount,  # Would convert
            currency=currency,
            payment_method=payment_method,
            status="pending",
        )
        
        return ProcessPaymentMutation(
            payment=payment,
            success=True,
            message="Payment processing initiated"
        )


class Mutation(ObjectType):
    """Root mutation type."""
    create_farmer = CreateFarmerMutation.Field()
    update_crop = UpdateCropMutation.Field()
    process_payment = ProcessPaymentMutation.Field()


# GraphQL Subscriptions
class Subscription(ObjectType):
    """Root subscription type for real-time updates."""
    
    sensor_reading_updated = Field(
        SensorReadingType,
        sensor_id=ID(required=True)
    )
    
    payment_status_changed = Field(
        PaymentType,
        payment_id=ID(required=True)
    )
    
    weather_alert = Field(
        lambda: WeatherAlertType,
        location_lat=Float(required=True),
        location_lon=Float(required=True)
    )
    
    def resolve_sensor_reading_updated(self, info, sensor_id):
        """Subscribe to sensor reading updates."""
        # In production, use WebSocket or Server-Sent Events
        return None
        
    def resolve_payment_status_changed(self, info, payment_id):
        """Subscribe to payment status changes."""
        return None
        
    def resolve_weather_alert(self, info, location_lat, location_lon):
        """Subscribe to weather alerts."""
        return None


# Additional GraphQL Types
class WeatherDataType(ObjectType):
    """Current weather data."""
    temperature = Float()
    humidity = Int()
    rainfall = Float()
    wind_speed = Float()
    description = String()
    location = String()


class WeatherAlertType(ObjectType):
    """Weather alert."""
    alert_type = String(required=True)
    severity = String(required=True)
    description = String()
    recommendations = List(String)


class PaymentStatisticsType(ObjectType):
    """Payment statistics."""
    total_payments = Int()
    total_amount_usd = Float()
    successful_payments = Int()
    failed_payments = Int()
    average_transaction_size = Float()


class FarmAnalyticsType(ObjectType):
    """Farm analytics."""
    total_area = Float()
    active_crops = Int()
    total_yield = Float()
    total_revenue = Float()
    average_yield_per_hectare = Float()
    sensor_count = Int()
    average_soil_moisture = Float()
    irrigation_efficiency = Float()


# GraphQL Schema
schema = graphene.Schema(
    query=Query,
    mutation=Mutation,
    subscription=Subscription
)


# FastAPI integration
from fastapi import FastAPI
from starlette.graphql import GraphQLApp

app = FastAPI(
    title="AgroPulse GraphQL API",
    description="Comprehensive GraphQL API for agricultural platform",
    version="1.0.0",
)

app.add_route("/graphql", GraphQLApp(schema=schema))


# Example GraphQL queries
EXAMPLE_QUERIES = """
# Get farmer information
query GetFarmer {
  farmer(id: "farmer_123") {
    name
    email
    phone
    farmSize
    crops {
      name
      status
      expectedYield
    }
  }
}

# Get crop recommendations
query GetCropRecommendations {
  cropRecommendations(
    soilPh: 6.5
    temperature: 25
    rainfall: 800
    farmSize: 10
    investmentLevel: "medium"
    skillLevel: "beginner"
    topK: 5
  ) {
    cropName
    score
    confidence
    reasoning
    expectedYield
    expectedRevenue
  }
}

# Get weather forecast
query GetWeatherForecast {
  weatherForecast(
    latitude: -1.286389
    longitude: 36.817223
    days: 7
  ) {
    timestamp
    temperature
    rainfall
    humidity
    description
  }
}

# Create farmer
mutation CreateFarmer {
  createFarmer(
    name: "Jane Farmer"
    email: "jane@example.com"
    phone: "+254712345678"
    location: "Nairobi"
    farmSize: 15.5
  ) {
    farmer {
      id
      name
      email
    }
    success
    message
  }
}

# Process payment
mutation ProcessPayment {
  processPayment(
    farmerId: "farmer_123"
    amount: 1500.00
    currency: "KES"
    paymentMethod: "mpesa"
  ) {
    payment {
      id
      transactionId
      status
      amountLocal
      amountUsd
    }
    success
    message
  }
}

# Subscribe to sensor updates
subscription SensorUpdates {
  sensorReadingUpdated(sensorId: "sensor_123") {
    timestamp
    temperature
    soilMoisture
    humidity
  }
}

# Subscribe to weather alerts
subscription WeatherAlerts {
  weatherAlert(
    locationLat: -1.286389
    locationLon: 36.817223
  ) {
    alertType
    severity
    description
    recommendations
  }
}
"""
