# 🗄️ AgroPulse Database Layer - Complete Guide

## Overview

Enterprise-grade database layer for AgroPulse agricultural platform with 25+ models, comprehensive relationships, and production-ready features.

**Total Lines:** 4,656  
**Models:** 25+  
**Features:** Soft delete, audit trails, geographic support, versioning, full-text search

---

## 📁 File Structure

```
AgroPulse/
├── app/
│   ├── models/
│   │   ├── __init__.py          # Model exports
│   │   └── database.py          # All SQLAlchemy models (2,116 lines)
│   ├── repositories/
│   │   └── base.py              # Repository pattern (595 lines)
│   ├── database.py              # Legacy async setup
│   └── db_config.py             # Production DB config (842 lines)
├── scripts/
│   └── seed_database.py         # Seed data (449 lines)
├── alembic/
│   ├── env.py                   # Alembic environment (150 lines)
│   └── versions/
│       └── 001_initial_schema.py # Initial migration (292 lines)
└── alembic.ini                  # Alembic configuration
```

---

## 🏗️ Database Models

### User Management
- **User** - Complete user profiles with authentication, subscriptions, referrals
- **UserSession** - Session tracking with security monitoring
- **APIKey** - API access management with rate limiting

### Farm Management
- **Farm** - Farms with geographic boundaries (PostGIS), certifications
- **Field** - Individual plots within farms
- **CropPlanting** - Crop lifecycle tracking from planting to harvest

### Diagnosis System
- **Diagnosis** - AI diagnosis records with treatment tracking
- **Disease** - Disease knowledge base with symptoms, treatments
- **Treatment** - Treatment recommendations with compliance data
- **TreatmentApplication** - Application tracking with effectiveness

### Products & Suppliers
- **Product** - Agricultural products (pesticides, fertilizers, seeds)
- **Supplier** - Supplier management with availability

### Digital Chama (Cooperatives)
- **Chama** - Cooperative management
- **Transaction** - Financial transactions (M-Pesa, bank, cash)
- **Loan** - Loan management with guarantors
- **LoanRepayment** - Repayment tracking
- **ChamaMeeting** - Meeting records with attendance

### IoT & Sensors
- **IoTDevice** - Device management (weather stations, sensors, cameras)
- **SensorReading** - Time-series sensor data
- **WeatherRecord** - Weather data from devices/APIs
- **SoilTest** - Soil testing results

### Alerts & Notifications
- **Alert** - Farm alert system (disease, pest, weather, device)
- **Notification** - User notifications (push, email, SMS, in-app)

### Audit
- **AuditLog** - Comprehensive audit trail for compliance

---

## 🚀 Quick Start

### 1. Install Dependencies

```bash
pip install sqlalchemy alembic asyncpg psycopg2-binary geoalchemy2 shapely sqlalchemy-utils passlib tenacity
```

### 2. Configure Database

Create `.env` file:

```bash
# Supabase (recommended)
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your-anon-key
USE_SUPABASE=true

# OR Local PostgreSQL
DATABASE_URL=postgresql://postgres:password@localhost:5432/agropulse

# Connection Pool
DB_POOL_SIZE=20
DB_MAX_OVERFLOW=40
DB_POOL_TIMEOUT=30

# Features
DB_USE_ASYNC=true
DB_ENABLE_QUERY_METRICS=true
DB_LOG_SLOW_QUERIES=true
```

### 3. Initialize Database

```bash
# Create migration
alembic upgrade head

# Seed with sample data
python scripts/seed_database.py
```

### 4. Use in Application

```python
from app.db_config import get_production_db
from app.models import User, Farm, Diagnosis

# Sync database session
with get_production_db() as db:
    users = db.query(User).filter(User.role == 'farmer').all()
    print(f"Found {len(users)} farmers")

# Async database session
from app.db_config import get_production_async_db
import asyncio

async def get_farms():
    async with get_production_async_db() as db:
        result = await db.execute(select(Farm).limit(10))
        farms = result.scalars().all()
        return farms

# FastAPI dependency injection
from fastapi import Depends, FastAPI
from sqlalchemy.orm import Session
from app.db_config import get_production_db_dependency

app = FastAPI()

@app.get("/users")
def get_users(db: Session = Depends(get_production_db_dependency)):
    return db.query(User).limit(10).all()
```

---

## 🎯 Repository Pattern

Clean data access layer with CRUD operations:

```python
from app.repositories.base import BaseRepository
from app.models import User
from app.db_config import get_production_db

class UserRepository(BaseRepository[User]):
    def __init__(self, db: Session):
        super().__init__(User, db)
    
    def get_by_email(self, email: str):
        return self.get_by_field('email', email)
    
    def get_active_farmers(self):
        return self.filter({
            'role': 'farmer',
            'status': 'active'
        })

# Usage
with get_production_db() as db:
    user_repo = UserRepository(db)
    
    # Create
    user = user_repo.create(
        email='farmer@example.com',
        first_name='John',
        last_name='Doe',
        role='farmer'
    )
    
    # Read
    user = user_repo.get_by_email('farmer@example.com')
    all_users = user_repo.get_all(skip=0, limit=100)
    
    # Update
    user_repo.update(user, status='active')
    
    # Delete (soft)
    user_repo.delete(user, soft=True)
    
    # Search
    results = user_repo.search('John', ['first_name', 'last_name'])
    
    # Count
    count = user_repo.count({'role': 'farmer'})
```

---

## 📊 Database Schema Highlights

### Geographic Support (PostGIS)
```python
# Store farm boundaries
farm = Farm(
    name="Green Valley Farm",
    latitude=-1.286389,
    longitude=36.817223,
    boundary_geojson={
        "type": "Polygon",
        "coordinates": [[...]]
    }
)

# Query nearby farms
from sqlalchemy import func
nearby_farms = db.query(Farm).filter(
    func.ST_DWithin(
        Farm.location,
        func.ST_SetSRID(func.ST_MakePoint(lon, lat), 4326),
        10000  # 10km radius
    )
).all()
```

### Soft Delete
```python
# Soft delete (default)
user_repo.delete(user, soft=True)

# Hard delete
user_repo.delete(user, soft=False)

# Restore soft-deleted
user_repo.restore(user)

# Include deleted in queries
users = user_repo.get_all(include_deleted=True)
```

### Audit Trail
```python
# Automatic audit logging
audit_log = AuditLog(
    user_id=user.id,
    action='UPDATE',
    entity_type='User',
    entity_id=str(user.id),
    old_values={'email': 'old@example.com'},
    new_values={'email': 'new@example.com'}
)
```

### Optimistic Locking
```python
# Version-based concurrency control
user = db.query(User).get(1)
user.email = 'new@example.com'
# version automatically incremented on update
```

---

## 🔒 Security Features

1. **Password Hashing** - bcrypt with salt
2. **Two-Factor Authentication** - TOTP secret storage
3. **Session Management** - Secure token-based sessions
4. **API Key Management** - Scoped access with rate limiting
5. **Audit Logging** - Complete action trail
6. **Role-Based Access** - User roles and permissions
7. **Account Locking** - Failed login protection
8. **IP Tracking** - Session IP monitoring

---

## ⚡ Performance Optimizations

### Indexes
```sql
-- Composite indexes
CREATE INDEX idx_user_email_status ON users(email, status);
CREATE INDEX idx_diagnosis_user_created ON diagnoses(user_id, created_at);

-- Geographic indexes
CREATE INDEX idx_farm_location ON farms USING GIST(location);

-- Full-text search
CREATE INDEX idx_farm_name_trgm ON farms USING GIN(name gin_trgm_ops);
```

### Connection Pooling
- Pool size: 20 connections
- Max overflow: 40 connections
- Pool recycle: 1 hour
- Pre-ping: Enabled
- Statement timeout: 30 seconds

### Query Monitoring
```python
from app.db_config import get_query_statistics

stats = get_query_statistics()
print(f"Total queries: {stats['total_queries']}")
print(f"Slow queries: {stats['slow_queries']}")
print(f"Average duration: {stats['average_duration']}")
```

---

## 🧪 Testing

### Seed Development Data
```bash
python scripts/seed_database.py
```

Creates:
- 50 users (farmers, agronomists, admin)
- 80 farms across Kenya
- 200 crop plantings
- 5 diseases
- 50 IoT devices
- 10 chamas
- 150 transactions

### Test Credentials
```
Admin:      admin@agropulse.ke / admin123
Agronomist: agronomist@agropulse.ke / agro123
Farmers:    (any farmer email) / farmer123
```

---

## 📈 Monitoring & Health Checks

```python
from app.db_config import check_database_health

# Sync health check
health = check_database_health()
print(f"Database healthy: {health['healthy']}")
print(f"Pool status: {health['primary']['pool_status']}")

# Async health check
health = await check_async_database_health()

# Query statistics
from app.db_config import get_query_statistics
stats = get_query_statistics()
```

---

## 🔧 Maintenance

### Run Migrations
```bash
# Create new migration
alembic revision --autogenerate -m "Add new feature"

# Apply migrations
alembic upgrade head

# Rollback
alembic downgrade -1
```

### Database Optimization
```python
from app.db_config import optimize_database

# Run VACUUM ANALYZE
optimize_database()
```

### Table Statistics
```python
from app.db_config import get_table_statistics

stats = get_table_statistics('users')
print(f"Row count: {stats['row_count']}")
print(f"Table size: {stats['total_size_mb']} MB")
```

---

## 🌍 Geographic Queries

```python
from geoalchemy2 import func

# Find farms within radius
farms = db.query(Farm).filter(
    func.ST_DWithin(
        Farm.location,
        func.ST_SetSRID(func.ST_MakePoint(longitude, latitude), 4326),
        distance_meters
    )
).all()

# Calculate distance
distance = db.query(
    func.ST_Distance(farm1.location, farm2.location)
).scalar()

# Check if point in polygon
is_inside = db.query(
    func.ST_Contains(farm.boundary_geometry, point_geometry)
).scalar()
```

---

## 📝 Common Queries

### Users
```python
# Active farmers in a county
farmers = db.query(User).filter(
    User.role == 'farmer',
    User.status == 'active',
    User.county == 'Nakuru'
).all()

# Users with expiring subscriptions
expiring = db.query(User).filter(
    User.subscription_expires_at < datetime.utcnow() + timedelta(days=7)
).all()
```

### Farms
```python
# Organic certified farms
organic_farms = db.query(Farm).filter(
    Farm.organic_certified == True,
    Farm.is_active == True
).all()

# Farms by size
large_farms = db.query(Farm).filter(
    Farm.size_acres >= 10.0
).order_by(Farm.size_acres.desc()).all()
```

### Diagnoses
```python
# Pending diagnoses
pending = db.query(Diagnosis).filter(
    Diagnosis.status == 'pending'
).order_by(Diagnosis.priority.desc()).all()

# High severity diagnoses
critical = db.query(Diagnosis).filter(
    Diagnosis.severity_level == 'critical',
    Diagnosis.completed_at.is_(None)
).all()
```

---

## 🎓 Best Practices

1. **Use Context Managers** - Always use `with get_production_db()` for automatic cleanup
2. **Repository Pattern** - Separate data access logic from business logic
3. **Soft Delete** - Preserve data for audit and analytics
4. **Pagination** - Always paginate large result sets
5. **Indexes** - Add indexes for frequently queried fields
6. **Transactions** - Group related operations in transactions
7. **Error Handling** - Catch and log SQLAlchemy exceptions
8. **Query Optimization** - Use `.filter()` before `.all()` to reduce data transfer

---

## 🐛 Troubleshooting

### Connection Pool Exhausted
```python
# Increase pool size in .env
DB_POOL_SIZE=30
DB_MAX_OVERFLOW=60
```

### Slow Queries
```python
# Enable query logging
DB_LOG_SLOW_QUERIES=true
DB_SLOW_QUERY_THRESHOLD=0.5

# Check slow queries
from app.db_config import query_monitor
slow_queries = query_monitor.recent_slow_queries
```

### Migration Conflicts
```bash
# Merge migration heads
alembic merge heads -m "merge migrations"

# Force migration
alembic stamp head
```

---

## 📚 Additional Resources

- [SQLAlchemy Documentation](https://docs.sqlalchemy.org/)
- [Alembic Documentation](https://alembic.sqlalchemy.org/)
- [PostGIS Documentation](https://postgis.net/documentation/)
- [FastAPI Database Guide](https://fastapi.tiangolo.com/tutorial/sql-databases/)

---

**Built with ❤️ by the AgroPulse Engineering Team**

*Last Updated: November 1, 2025*
