# 🚀 Repository Quick Reference Guide

## Overview

This guide provides quick examples for using the UserRepository and FarmRepository in your application.

---

## Setup

```python
from app.db_config import get_production_db
from app.repositories.user import UserRepository
from app.repositories.farm import FarmRepository

# Get database session
with get_production_db() as db:
    user_repo = UserRepository(db)
    farm_repo = FarmRepository(db)
    
    # Your code here
```

---

## User Repository Examples

### Authentication

```python
# Register new user
user = user_repo.create(
    email='farmer@example.com',
    phone_number='+254712345678',
    password_hash='hashed_password',  # Use bcrypt.hashpw()
    first_name='John',
    last_name='Doe',
    role='farmer',
    county='Nakuru'
)

# Authenticate user
user = user_repo.authenticate(
    email='farmer@example.com',
    password_hash='hashed_password'
)

if user:
    print(f"Welcome {user.first_name}!")
else:
    print("Invalid credentials")

# Verify email
user_repo.verify_email(user.id)

# Enable 2FA
user_repo.enable_2fa(user.id, totp_secret='SECRET123')
```

### Profile Management

```python
# Update profile
user = user_repo.update_profile(
    user_id=1,
    date_of_birth='1990-01-01',
    gender='Male',
    county='Nakuru',
    avatar_url='https://example.com/avatar.jpg'
)

# Complete onboarding
user = user_repo.complete_onboarding(user.id)

# Profile completion is calculated automatically
print(f"Profile {user.profile_completion_percentage}% complete")
```

### Subscription Management

```python
from datetime import datetime, timedelta

# Upgrade to premium
user = user_repo.update_subscription(
    user_id=1,
    tier='premium',
    expires_at=datetime.utcnow() + timedelta(days=365),
    diagnoses_remaining=100
)

# Decrement diagnosis count
user = user_repo.decrement_diagnoses(user.id)
print(f"{user.diagnoses_remaining} diagnoses remaining")

# Find expiring subscriptions
expiring = user_repo.get_expiring_subscriptions(days=7)
for user in expiring:
    print(f"{user.email} expires in 7 days")
```

### Referral System

```python
# Get user by referral code
referrer = user_repo.get_by_referral_code('FARM2024')

# Register referred user
new_user = user_repo.create(
    email='referred@example.com',
    referred_by_id=referrer.id,
    # ... other fields
)

# Track referral
user_repo.increment_referral_count(referrer.id)
user_repo.add_referral_earnings(referrer.id, 100.0)  # 100 KSH bonus

# Get all referrals
referrals = user_repo.get_referrals(referrer.id)
print(f"{len(referrals)} users referred")
```

### User Queries

```python
# Get farmers in a county
farmers = user_repo.get_by_county('Nakuru', skip=0, limit=50)

# Get active farmers
active_farmers = user_repo.get_active_farmers(skip=0, limit=100)

# Get verified users
verified = user_repo.get_verified_users()

# Get premium users
premium = user_repo.get_premium_users()

# Search users
results = user_repo.search_users('John', skip=0, limit=10)

# Get by role
agronomists = user_repo.get_by_role('agronomist')
```

### Statistics

```python
# Overall user statistics
stats = user_repo.get_user_statistics()
print(f"Total users: {stats['total_users']}")
print(f"Active users: {stats['active_users']}")
print(f"Farmers: {stats['farmers']}")

# Subscription breakdown
breakdown = user_repo.get_subscription_breakdown()
print(f"Free: {breakdown.get('free', 0)}")
print(f"Premium: {breakdown.get('premium', 0)}")

# Top referrers
top = user_repo.get_top_referrers(limit=10)
for user in top:
    print(f"{user.email}: {user.referral_count} referrals")
```

---

## Farm Repository Examples

### Geographic Queries

```python
# Find farms near a location
nearby_farms = farm_repo.get_by_location(
    latitude=-0.3031,  # Nakuru
    longitude=36.0800,
    radius_km=10.0,
    skip=0,
    limit=50
)

for farm in nearby_farms:
    print(f"{farm.name} - {farm.size_acres} acres")

# Calculate distance between farms
distance_km = farm_repo.calculate_distance(farm1_id=1, farm2_id=2)
print(f"Distance: {distance_km:.2f} km")

# Find farms in a polygon
polygon = {
    "type": "Polygon",
    "coordinates": [[
        [36.0, -0.5],
        [36.5, -0.5],
        [36.5, 0.0],
        [36.0, 0.0],
        [36.0, -0.5]
    ]]
}
farms_in_area = farm_repo.get_farms_in_polygon(polygon)
```

### Farm Management

```python
# Create new farm
farm = farm_repo.create(
    user_id=1,
    name='Green Valley Farm',
    latitude=-0.3031,
    longitude=36.0800,
    size_acres=15.5,
    county='Nakuru',
    primary_crop='Maize',
    farm_type='mixed',
    has_irrigation=True
)

# Get user's farms
my_farms = farm_repo.get_by_user(user_id=1)

# Get farms by type
organic_farms = farm_repo.get_by_farm_type('organic')

# Get farms by crop
maize_farms = farm_repo.get_by_primary_crop('Maize')

# Search farms
results = farm_repo.search_farms('Valley')
```

### Certification

```python
# Get certified farms
organic = farm_repo.get_organic_certified()
global_gap = farm_repo.get_global_gap_certified()

# Verify a farm
farm = farm_repo.verify_farm(farm_id=1)
print(f"Farm verified: {farm.verification_status}")
```

### Size Queries

```python
# Get farms in size range
medium_farms = farm_repo.get_by_size_range(
    min_acres=5.0,
    max_acres=20.0
)

# Get large farms
large_farms = farm_repo.get_large_farms(min_acres=10.0)

# Get small-holder farms
small_farms = farm_repo.get_small_holder_farms(max_acres=5.0)
```

### Irrigation & Water

```python
# Get irrigated farms
irrigated = farm_repo.get_irrigated_farms()

# Get farms by irrigation type
drip_farms = farm_repo.get_by_irrigation_type('drip')
sprinkler_farms = farm_repo.get_by_irrigation_type('sprinkler')

# Get farms by water source
borehole_farms = farm_repo.get_by_water_source('borehole')
river_farms = farm_repo.get_by_water_source('river')
```

### Soil & Climate

```python
# Get farms by soil type
loam_farms = farm_repo.get_by_soil_type('loam')
clay_farms = farm_repo.get_by_soil_type('clay')

# Get farms by climate zone
tropical_farms = farm_repo.get_by_climate_zone('tropical')
```

### Statistics

```python
# Overall farm statistics
stats = farm_repo.get_farm_statistics()
print(f"Total farms: {stats['total_farms']}")
print(f"Active farms: {stats['active_farms']}")
print(f"Total area: {stats['total_area_acres']} acres")
print(f"Average size: {stats['average_size_acres']:.2f} acres")

# County breakdown
counties = farm_repo.get_county_breakdown()
for county, count in counties.items():
    print(f"{county}: {count} farms")

# Crop distribution
crops = farm_repo.get_crop_distribution()
for crop, count in crops.items():
    print(f"{crop}: {count} farms")

# Largest farms
largest = farm_repo.get_largest_farms(limit=10)
for farm in largest:
    print(f"{farm.name}: {farm.size_acres} acres")
```

### Field Management

```python
# Get farm's fields
fields = farm_repo.get_fields(farm_id=1)
print(f"Farm has {len(fields)} fields")

# Count fields
field_count = farm_repo.get_field_count(farm_id=1)

# Get total field area
total_area = farm_repo.get_total_field_area(farm_id=1)
print(f"Total field area: {total_area} acres")
```

### Crop Integration

```python
# Get active plantings
plantings = farm_repo.get_active_plantings(farm_id=1)
for planting in plantings:
    print(f"{planting.crop_name}: {planting.area_planted_acres} acres")

# Count plantings
planting_count = farm_repo.get_planting_count(farm_id=1)
```

---

## FastAPI Integration

### Basic Endpoint

```python
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db_config import get_production_db_dependency
from app.repositories.user import UserRepository

router = APIRouter()

@router.get("/users/{user_id}")
def get_user(
    user_id: int,
    db: Session = Depends(get_production_db_dependency)
):
    user_repo = UserRepository(db)
    user = user_repo.get_by_id(user_id)
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return user
```

### Authentication Endpoint

```python
from fastapi import HTTPException
from pydantic import BaseModel
import bcrypt

class LoginRequest(BaseModel):
    email: str
    password: str

@router.post("/auth/login")
def login(
    request: LoginRequest,
    db: Session = Depends(get_production_db_dependency)
):
    user_repo = UserRepository(db)
    
    # Hash password
    password_hash = bcrypt.hashpw(
        request.password.encode('utf-8'),
        bcrypt.gensalt()
    ).decode('utf-8')
    
    # Authenticate
    user = user_repo.authenticate(request.email, password_hash)
    
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    return {
        "user_id": user.id,
        "email": user.email,
        "name": f"{user.first_name} {user.last_name}"
    }
```

### Geographic Search Endpoint

```python
@router.get("/farms/nearby")
def get_nearby_farms(
    latitude: float,
    longitude: float,
    radius_km: float = 10.0,
    db: Session = Depends(get_production_db_dependency)
):
    farm_repo = FarmRepository(db)
    farms = farm_repo.get_by_location(
        latitude=latitude,
        longitude=longitude,
        radius_km=radius_km
    )
    
    return {
        "count": len(farms),
        "farms": farms
    }
```

---

## Common Patterns

### Pagination

```python
# All repository methods support skip and limit
page = 1
page_size = 20
skip = (page - 1) * page_size

users = user_repo.get_active_farmers(skip=skip, limit=page_size)
total = user_repo.count({'role': 'farmer', 'status': 'active'})

return {
    "items": users,
    "page": page,
    "page_size": page_size,
    "total": total,
    "pages": (total + page_size - 1) // page_size
}
```

### Error Handling

```python
try:
    user = user_repo.create(**user_data)
except Exception as e:
    db.rollback()
    raise HTTPException(status_code=400, detail=str(e))
```

### Transaction Management

```python
from app.db_config import get_production_db

try:
    with get_production_db() as db:
        user_repo = UserRepository(db)
        
        # Multiple operations in transaction
        user = user_repo.create(**user_data)
        user_repo.increment_referral_count(referrer_id)
        
        # Commit happens automatically on context exit
        
except Exception as e:
    # Rollback happens automatically on exception
    print(f"Transaction failed: {e}")
```

---

## Performance Tips

1. **Use Pagination** - Always use skip/limit for large result sets
2. **Index Usage** - Queries on indexed fields are much faster
3. **Eager Loading** - Use joinedload for relationships if needed
4. **Connection Pooling** - Reuse database connections via session factory
5. **Geographic Queries** - PostGIS indexes make location queries fast
6. **Full-Text Search** - Trigram indexes enable fast text search

---

## Testing Examples

```python
import pytest
from app.db_config import get_test_db
from app.repositories.user import UserRepository

@pytest.fixture
def user_repo():
    with get_test_db() as db:
        yield UserRepository(db)

def test_create_user(user_repo):
    user = user_repo.create(
        email='test@example.com',
        first_name='Test',
        last_name='User',
        role='farmer'
    )
    
    assert user.id is not None
    assert user.email == 'test@example.com'

def test_authenticate(user_repo):
    # Create user
    user = user_repo.create(
        email='auth@example.com',
        password_hash='hashed_password',
        first_name='Auth',
        last_name='User'
    )
    
    # Authenticate
    auth_user = user_repo.authenticate(
        'auth@example.com',
        'hashed_password'
    )
    
    assert auth_user is not None
    assert auth_user.id == user.id
```

---

## Additional Resources

- **Database Guide:** See `DATABASE_GUIDE.md` for comprehensive database documentation
- **Phase 1 Summary:** See `PHASE1_COMPLETION_SUMMARY.md` for achievement details
- **Progress Tracking:** See `PHASE1_PROGRESS.md` for current status

---

**Happy Coding! 🚀**

*AgroPulse Engineering Team*
