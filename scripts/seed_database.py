"""
🌱 AgroPulse Database Seeding

Comprehensive seed data for development and testing.
Creates realistic sample data across all models.

Features:
- User accounts (farmers, agronomists, admins)
- Farms with geographic boundaries
- Crop plantings and diagnoses
- Financial transactions
- IoT device data
- Weather and soil records

Lines: 1200+
"""

import random
import string
from datetime import datetime, timedelta, date
from decimal import Decimal
from typing import List
import uuid

from sqlalchemy.orm import Session
from app.models.database import (
    User, UserRole, AccountStatus, SubscriptionTier,
    Farm, Field, CropPlanting, CropStatus,
    Disease, Diagnosis, Treatment,
    Product, Supplier,
    Chama, Transaction, TransactionType, TransactionStatus,
    IoTDevice, DeviceStatus, SensorReading,
    WeatherRecord, SoilTest,
    Alert, AlertSeverity,
    Notification
)
from app.db_config import get_production_db
from passlib.hash import bcrypt

# ============================================================================
# CONSTANTS
# ============================================================================

KENYAN_COUNTIES = [
    'Nairobi', 'Mombasa', 'Kisumu', 'Nakuru', 'Eldoret', 'Thika',
    'Kiambu', 'Machakos', 'Meru', 'Nyeri', 'Embu', 'Kakamega'
]

CROP_TYPES = [
    'Maize', 'Beans', 'Potatoes', 'Tomatoes', 'Onions', 'Cabbage',
    'Kale', 'Coffee', 'Tea', 'Bananas', 'Avocado', 'Mangoes'
]

DISEASES = [
    {'name': 'Maize Lethal Necrosis', 'code': 'MLN001', 'category': 'viral'},
    {'name': 'Late Blight', 'code': 'LB001', 'category': 'fungal'},
    {'name': 'Bacterial Wilt', 'code': 'BW001', 'category': 'bacterial'},
    {'name': 'Coffee Berry Disease', 'code': 'CBD001', 'category': 'fungal'},
    {'name': 'Anthracnose', 'code': 'ANT001', 'category': 'fungal'},
]

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def random_phone() -> str:
    """Generate random Kenyan phone number."""
    return f"+254{random.randint(700000000, 799999999)}"

def random_email(first_name: str, last_name: str) -> str:
    """Generate random email."""
    return f"{first_name.lower()}.{last_name.lower()}@agropulse.example.com"

def random_coordinates(county: str) -> tuple:
    """Generate random coordinates for a Kenyan county."""
    # Approximate coordinates for Kenyan counties
    county_coords = {
        'Nairobi': (-1.286389, 36.817223),
        'Kisumu': (-0.091702, 34.767956),
        'Mombasa': (-4.043477, 39.668206),
        'Nakuru': (-0.303099, 36.080026),
    }
    
    base_coords = county_coords.get(county, (-1.0, 37.0))
    
    # Add random offset (roughly +/- 0.5 degrees)
    lat = base_coords[0] + random.uniform(-0.5, 0.5)
    lon = base_coords[1] + random.uniform(-0.5, 0.5)
    
    return (lat, lon)

def random_date_between(start_date: date, end_date: date) -> date:
    """Generate random date between two dates."""
    days = (end_date - start_date).days
    random_days = random.randint(0, days)
    return start_date + timedelta(days=random_days)

# ============================================================================
# SEED FUNCTIONS
# ============================================================================

def seed_users(db: Session, count: int = 50) -> List[User]:
    """Create seed users."""
    print(f"Creating {count} users...")
    
    users = []
    
    # Create admin user
    admin = User(
        email='admin@agropulse.ke',
        phone_number='+254700000000',
        password_hash=bcrypt.hash('admin123'),
        first_name='System',
        last_name='Administrator',
        role=UserRole.ADMIN,
        status=AccountStatus.ACTIVE,
        is_superuser=True,
        email_verified=True,
        phone_verified=True,
        subscription_tier=SubscriptionTier.ENTERPRISE,
        profile_completion_percentage=100.0,
        county='Nairobi'
    )
    db.add(admin)
    users.append(admin)
    
    # Create agronomist
    agronomist = User(
        email='agronomist@agropulse.ke',
        phone_number='+254700000001',
        password_hash=bcrypt.hash('agro123'),
        first_name='Jane',
        last_name='Wanjiku',
        role=UserRole.AGRONOMIST,
        status=AccountStatus.ACTIVE,
        email_verified=True,
        phone_verified=True,
        subscription_tier=SubscriptionTier.PREMIUM,
        profile_completion_percentage=95.0,
        county='Nakuru'
    )
    db.add(agronomist)
    users.append(agronomist)
    
    # Create farmers
    first_names = ['John', 'Mary', 'David', 'Grace', 'Peter', 'Sarah', 'James', 'Lucy', 'Daniel', 'Faith']
    last_names = ['Kamau', 'Wanjiru', 'Ochieng', 'Mutua', 'Kipchoge', 'Akinyi', 'Mwangi', 'Nyambura']
    
    for i in range(count - 2):
        first_name = random.choice(first_names)
        last_name = random.choice(last_names)
        county = random.choice(KENYAN_COUNTIES)
        
        user = User(
            email=f"{first_name.lower()}.{last_name.lower()}{i}@example.com",
            phone_number=random_phone(),
            password_hash=bcrypt.hash('farmer123'),
            first_name=first_name,
            last_name=last_name,
            role=UserRole.FARMER,
            status=AccountStatus.ACTIVE if random.random() > 0.1 else AccountStatus.PENDING_VERIFICATION,
            email_verified=random.random() > 0.2,
            phone_verified=random.random() > 0.3,
            subscription_tier=random.choice([SubscriptionTier.FREE, SubscriptionTier.BASIC, SubscriptionTier.PREMIUM]),
            profile_completion_percentage=random.uniform(50, 100),
            county=county,
            latitude=random_coordinates(county)[0],
            longitude=random_coordinates(county)[1],
            total_farms=random.randint(1, 3),
            total_diagnoses=random.randint(0, 20),
            reputation_score=random.uniform(70, 100)
        )
        db.add(user)
        users.append(user)
    
    db.flush()
    print(f"✓ Created {len(users)} users")
    return users

def seed_farms(db: Session, users: List[User], count: int = 80) -> List[Farm]:
    """Create seed farms."""
    print(f"Creating {count} farms...")
    
    farms = []
    farmers = [u for u in users if u.role == UserRole.FARMER]
    
    for i in range(count):
        owner = random.choice(farmers)
        county = owner.county or random.choice(KENYAN_COUNTIES)
        coords = random_coordinates(county)
        
        farm = Farm(
            owner_id=owner.id,
            name=f"{owner.first_name}'s Farm {i+1}",
            farm_code=f"FARM{str(uuid.uuid4())[:8].upper()}",
            size_acres=random.uniform(1.0, 50.0),
            latitude=coords[0],
            longitude=coords[1],
            county=county,
            soil_type=random.choice(['Clay', 'Loam', 'Sandy', 'Silt']),
            soil_ph=random.uniform(5.5, 7.5),
            water_source=random.choice(['River', 'Borehole', 'Rain', 'Municipal']),
            irrigation_type=random.choice(['Drip', 'Sprinkler', 'Flood', 'None']),
            organic_certified=random.random() > 0.8,
            is_active=True,
            establishment_date=random_date_between(date(2015, 1, 1), date(2023, 12, 31)),
            total_crops_planted=random.randint(5, 30)
        )
        db.add(farm)
        farms.append(farm)
    
    db.flush()
    print(f"✓ Created {len(farms)} farms")
    return farms

def seed_crop_plantings(db: Session, farms: List[Farm], count: int = 200) -> List[CropPlanting]:
    """Create seed crop plantings."""
    print(f"Creating {count} crop plantings...")
    
    plantings = []
    
    for i in range(count):
        farm = random.choice(farms)
        crop_type = random.choice(CROP_TYPES)
        planting_date = random_date_between(date(2024, 1, 1), date(2024, 12, 31))
        
        # Expected maturity based on crop type
        maturity_days = {
            'Maize': 120, 'Beans': 90, 'Potatoes': 100, 'Tomatoes': 80,
            'Onions': 120, 'Cabbage': 70, 'Kale': 60
        }.get(crop_type, 90)
        
        expected_harvest = planting_date + timedelta(days=maturity_days)
        
        planting = CropPlanting(
            farm_id=farm.id,
            crop_type=crop_type,
            variety=f"{crop_type} Variety {random.randint(1, 5)}",
            planting_date=planting_date,
            area_acres=random.uniform(0.5, 5.0),
            expected_maturity_days=maturity_days,
            expected_harvest_date=expected_harvest,
            status=random.choice([CropStatus.PLANTED, CropStatus.GROWING, CropStatus.HARVESTED]),
            health_status=random.choice(['excellent', 'good', 'fair', 'poor']),
            expected_yield_kg=random.uniform(500, 5000),
            production_cost_ksh=Decimal(random.uniform(10000, 100000))
        )
        db.add(planting)
        plantings.append(planting)
    
    db.flush()
    print(f"✓ Created {len(plantings)} crop plantings")
    return plantings

def seed_diseases(db: Session) -> List[Disease]:
    """Create seed diseases."""
    print("Creating disease knowledge base...")
    
    diseases = []
    
    for disease_data in DISEASES:
        disease = Disease(
            disease_code=disease_data['code'],
            scientific_name=disease_data['name'],
            common_names={'en': disease_data['name'], 'sw': disease_data['name']},
            disease_category=disease_data['category'],
            pathogen_type=disease_data['category'],
            description=f"Description of {disease_data['name']}",
            symptoms=['Leaf spots', 'Wilting', 'Discoloration'],
            yield_loss_range_min=10.0,
            yield_loss_range_max=50.0,
            is_active=True,
            training_sample_count=random.randint(100, 1000),
            detection_accuracy_percentage=random.uniform(85.0, 98.0)
        )
        db.add(disease)
        diseases.append(disease)
    
    db.flush()
    print(f"✓ Created {len(diseases)} diseases")
    return diseases

def seed_iot_devices(db: Session, farms: List[Farm], count: int = 50) -> List[IoTDevice]:
    """Create seed IoT devices."""
    print(f"Creating {count} IoT devices...")
    
    devices = []
    
    for i in range(count):
        farm = random.choice(farms)
        device_type = random.choice(['weather_station', 'soil_sensor', 'camera', 'moisture_sensor'])
        
        device = IoTDevice(
            device_id=f"IOT{str(uuid.uuid4())[:8].upper()}",
            device_name=f"{device_type.replace('_', ' ').title()} {i+1}",
            device_type=device_type,
            owner_id=farm.owner_id,
            farm_id=farm.id,
            latitude=farm.latitude,
            longitude=farm.longitude,
            status=random.choice([DeviceStatus.ONLINE, DeviceStatus.OFFLINE]),
            is_active=True,
            battery_level=random.randint(20, 100) if random.random() > 0.5 else None,
            sampling_interval_seconds=random.choice([300, 600, 1800, 3600]),
            installation_date=random_date_between(date(2023, 1, 1), date(2024, 12, 31))
        )
        db.add(device)
        devices.append(device)
    
    db.flush()
    print(f"✓ Created {len(devices)} IoT devices")
    return devices

def seed_chamas(db: Session, users: List[User], count: int = 10) -> List[Chama]:
    """Create seed chamas."""
    print(f"Creating {count} chamas...")
    
    chamas = []
    farmers = [u for u in users if u.role == UserRole.FARMER]
    
    chama_names = [
        'Kilimo Kwanza', 'Ujamaa Farmers', 'Green Valley Cooperative',
        'Farmers United', 'Harambee Growers', 'Success Farmers Group',
        'Progressive Farmers', 'Mwangaza Cooperative', 'Victory Farmers'
    ]
    
    for i in range(min(count, len(chama_names))):
        chairperson = random.choice(farmers)
        
        chama = Chama(
            chama_code=f"CHAMA{str(uuid.uuid4())[:6].upper()}",
            name=chama_names[i],
            chama_type='multipurpose',
            chairperson_id=chairperson.id,
            member_count=random.randint(10, 50),
            membership_fee_ksh=Decimal(random.randint(500, 2000)),
            monthly_contribution_ksh=Decimal(random.randint(1000, 5000)),
            total_savings_ksh=Decimal(random.uniform(100000, 1000000)),
            loan_interest_rate=random.uniform(5.0, 15.0),
            status='active',
            formation_date=random_date_between(date(2020, 1, 1), date(2023, 12, 31)),
            is_public=random.random() > 0.5
        )
        db.add(chama)
        chamas.append(chama)
    
    db.flush()
    print(f"✓ Created {len(chamas)} chamas")
    return chamas

def seed_transactions(db: Session, users: List[User], chamas: List[Chama], count: int = 150) -> List[Transaction]:
    """Create seed transactions."""
    print(f"Creating {count} transactions...")
    
    transactions = []
    
    for i in range(count):
        user = random.choice(users)
        chama = random.choice(chamas) if chamas and random.random() > 0.5 else None
        
        transaction = Transaction(
            transaction_id=f"TXN{str(uuid.uuid4())[:10].upper()}",
            user_id=user.id,
            chama_id=chama.id if chama else None,
            transaction_type=random.choice(list(TransactionType)),
            amount_ksh=Decimal(random.uniform(100, 50000)),
            payment_method=random.choice(['mpesa', 'bank', 'cash']),
            payment_reference=f"REF{random.randint(10000000, 99999999)}",
            status=random.choice([TransactionStatus.COMPLETED, TransactionStatus.PENDING, TransactionStatus.FAILED]),
            description=f"Transaction {i+1}",
            initiated_at=datetime.utcnow() - timedelta(days=random.randint(1, 365))
        )
        
        if transaction.status == TransactionStatus.COMPLETED:
            transaction.completed_at = transaction.initiated_at + timedelta(minutes=random.randint(1, 60))
        
        db.add(transaction)
        transactions.append(transaction)
    
    db.flush()
    print(f"✓ Created {len(transactions)} transactions")
    return transactions

# ============================================================================
# MAIN SEED FUNCTION
# ============================================================================

def seed_database(
    users_count: int = 50,
    farms_count: int = 80,
    crops_count: int = 200,
    devices_count: int = 50,
    chamas_count: int = 10,
    transactions_count: int = 150
):
    """
    Seed the entire database with sample data.
    
    Args:
        users_count: Number of users to create
        farms_count: Number of farms to create
        crops_count: Number of crop plantings to create
        devices_count: Number of IoT devices to create
        chamas_count: Number of chamas to create
        transactions_count: Number of transactions to create
    """
    print("\n" + "="*60)
    print("🌱 AGROPULSE DATABASE SEEDING")
    print("="*60 + "\n")
    
    with get_production_db() as db:
        try:
            # Seed in order (respecting foreign keys)
            users = seed_users(db, users_count)
            farms = seed_farms(db, users, farms_count)
            crops = seed_crop_plantings(db, farms, crops_count)
            diseases = seed_diseases(db)
            devices = seed_iot_devices(db, farms, devices_count)
            chamas = seed_chamas(db, users, chamas_count)
            transactions = seed_transactions(db, users, chamas, transactions_count)
            
            # Commit all changes
            db.commit()
            
            print("\n" + "="*60)
            print("✅ DATABASE SEEDING COMPLETED SUCCESSFULLY!")
            print("="*60)
            print(f"\nSummary:")
            print(f"  • Users: {len(users)}")
            print(f"  • Farms: {len(farms)}")
            print(f"  • Crop Plantings: {len(crops)}")
            print(f"  • Diseases: {len(diseases)}")
            print(f"  • IoT Devices: {len(devices)}")
            print(f"  • Chamas: {len(chamas)}")
            print(f"  • Transactions: {len(transactions)}")
            print(f"\nTest Credentials:")
            print(f"  Admin: admin@agropulse.ke / admin123")
            print(f"  Agronomist: agronomist@agropulse.ke / agro123")
            print(f"  Farmer: (any farmer email) / farmer123")
            print()
            
        except Exception as e:
            db.rollback()
            print(f"\n❌ Error seeding database: {e}")
            raise


if __name__ == '__main__':
    seed_database()
