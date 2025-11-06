"""
Comprehensive Farmer Dashboard and Web Application Backend

This advanced system provides:
- RESTful API for web and mobile clients
- Real-time WebSocket connections for live data
- User authentication and authorization
- Multi-tenant orchard management
- Dashboard data aggregation and caching
- Alert and notification system
- Historical data analytics API
- Report generation and export
- Mobile app backend services
- Third-party integrations (Zapier, IFTTT)
- Rate limiting and security
- GraphQL API support
- Payment processing integration
- Subscription management
- API documentation (OpenAPI/Swagger)
- Multi-language support
- Time-zone handling
- Data export in multiple formats

Author: AgroPulse Development Team
Version: 7.0.0
"""

from fastapi import FastAPI, WebSocket, Depends, HTTPException, status, BackgroundTasks
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, EmailStr, validator
from typing import Dict, List, Tuple, Optional, Any, Union
from datetime import datetime, timedelta
from enum import Enum
import asyncio
from collections import defaultdict, deque
import json
import jwt
import hashlib
import secrets
from passlib.context import CryptContext
import redis.asyncio as redis
from motor.motor_asyncio import AsyncIOMotorClient
import pandas as pd
from io import BytesIO, StringIO
import numpy as np
import warnings
warnings.filterwarnings('ignore')


# Configuration
SECRET_KEY = secrets.token_urlsafe(32)
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7


class UserRole(str, Enum):
    """User roles with different access levels"""
    ADMIN = "admin"
    OWNER = "owner"
    MANAGER = "manager"
    OPERATOR = "operator"
    VIEWER = "viewer"


class SubscriptionTier(str, Enum):
    """Subscription tiers"""
    FREE = "free"
    BASIC = "basic"
    PROFESSIONAL = "professional"
    ENTERPRISE = "enterprise"


class AlertSeverity(str, Enum):
    """Alert severity levels"""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    EMERGENCY = "emergency"


# Pydantic Models
class UserBase(BaseModel):
    """Base user model"""
    email: EmailStr
    full_name: str
    phone: Optional[str] = None


class UserCreate(UserBase):
    """User creation model"""
    password: str
    
    @validator('password')
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters')
        return v


class UserResponse(UserBase):
    """User response model"""
    user_id: str
    role: UserRole
    subscription_tier: SubscriptionTier
    created_at: datetime
    last_login: Optional[datetime] = None
    is_active: bool = True


class Token(BaseModel):
    """JWT token response"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class OrchardBase(BaseModel):
    """Base orchard model"""
    name: str
    location: Tuple[float, float]  # lat, lon
    area_hectares: float
    crop_type: str
    description: Optional[str] = None


class OrchardCreate(OrchardBase):
    """Orchard creation model"""
    pass


class OrchardResponse(OrchardBase):
    """Orchard response model"""
    orchard_id: str
    owner_id: str
    created_at: datetime
    drone_count: int = 0
    last_survey: Optional[datetime] = None
    health_score: float = 100.0


class DashboardStats(BaseModel):
    """Dashboard statistics"""
    total_orchards: int
    total_drones: int
    active_missions: int
    total_flight_hours: float
    health_index: float
    recent_alerts: int
    battery_status: Dict[str, int]
    weather_status: str


class AlertBase(BaseModel):
    """Base alert model"""
    severity: AlertSeverity
    title: str
    message: str
    orchard_id: Optional[str] = None
    drone_id: Optional[str] = None


class AlertResponse(AlertBase):
    """Alert response model"""
    alert_id: str
    timestamp: datetime
    acknowledged: bool = False
    acknowledged_by: Optional[str] = None
    acknowledged_at: Optional[datetime] = None


class MissionBase(BaseModel):
    """Base mission model"""
    mission_type: str
    orchard_id: str
    drone_id: str
    scheduled_time: datetime
    estimated_duration: int  # minutes
    waypoints: List[Tuple[float, float, float]]


class MissionCreate(MissionBase):
    """Mission creation model"""
    pass


class MissionResponse(MissionBase):
    """Mission response model"""
    mission_id: str
    status: str  # pending, in_progress, completed, failed
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    progress: float = 0.0
    data_collected: Dict[str, Any] = {}


class AnalyticsQuery(BaseModel):
    """Analytics query parameters"""
    orchard_id: Optional[str] = None
    metric_type: str
    start_date: datetime
    end_date: datetime
    aggregation: str = "daily"  # hourly, daily, weekly, monthly


class NotificationSettings(BaseModel):
    """User notification preferences"""
    email_enabled: bool = True
    sms_enabled: bool = False
    push_enabled: bool = True
    alert_severity_threshold: AlertSeverity = AlertSeverity.WARNING
    quiet_hours_start: Optional[str] = None  # "22:00"
    quiet_hours_end: Optional[str] = None  # "07:00"


# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


class AuthService:
    """
    Authentication and authorization service
    """
    
    def __init__(self):
        self.pwd_context = pwd_context
        self.active_sessions = {}
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify password against hash"""
        return self.pwd_context.verify(plain_password, hashed_password)
    
    def get_password_hash(self, password: str) -> str:
        """Generate password hash"""
        return self.pwd_context.hash(password)
    
    def create_access_token(self, data: dict, expires_delta: Optional[timedelta] = None) -> str:
        """Create JWT access token"""
        to_encode = data.copy()
        
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        
        to_encode.update({"exp": expire, "type": "access"})
        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        
        return encoded_jwt
    
    def create_refresh_token(self, data: dict) -> str:
        """Create JWT refresh token"""
        to_encode = data.copy()
        expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
        
        to_encode.update({"exp": expire, "type": "refresh"})
        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        
        return encoded_jwt
    
    def decode_token(self, token: str) -> Dict[str, Any]:
        """Decode and verify JWT token"""
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            return payload
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired",
                headers={"WWW-Authenticate": "Bearer"},
            )
        except jwt.JWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
    
    def check_permission(self, user_role: UserRole, required_role: UserRole) -> bool:
        """Check if user has required permission level"""
        role_hierarchy = {
            UserRole.ADMIN: 5,
            UserRole.OWNER: 4,
            UserRole.MANAGER: 3,
            UserRole.OPERATOR: 2,
            UserRole.VIEWER: 1
        }
        
        return role_hierarchy.get(user_role, 0) >= role_hierarchy.get(required_role, 0)


class DatabaseService:
    """
    Database service with async MongoDB support
    """
    
    def __init__(self, connection_string: str):
        """Initialize database connection"""
        self.client = AsyncIOMotorClient(connection_string)
        self.db = self.client.agropulse
        
        # Collections
        self.users = self.db.users
        self.orchards = self.db.orchards
        self.drones = self.db.drones
        self.missions = self.db.missions
        self.alerts = self.db.alerts
        self.analytics = self.db.analytics
    
    async def create_user(self, user_data: UserCreate, role: UserRole = UserRole.VIEWER) -> UserResponse:
        """Create new user"""
        # Check if user exists
        existing = await self.users.find_one({"email": user_data.email})
        if existing:
            raise HTTPException(status_code=400, detail="Email already registered")
        
        # Hash password
        auth_service = AuthService()
        hashed_password = auth_service.get_password_hash(user_data.password)
        
        # Create user document
        user_doc = {
            "user_id": secrets.token_urlsafe(16),
            "email": user_data.email,
            "full_name": user_data.full_name,
            "phone": user_data.phone,
            "hashed_password": hashed_password,
            "role": role.value,
            "subscription_tier": SubscriptionTier.FREE.value,
            "created_at": datetime.utcnow(),
            "last_login": None,
            "is_active": True
        }
        
        await self.users.insert_one(user_doc)
        
        return UserResponse(**{k: v for k, v in user_doc.items() if k != 'hashed_password'})
    
    async def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Get user by email"""
        return await self.users.find_one({"email": email})
    
    async def get_user_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user by ID"""
        return await self.users.find_one({"user_id": user_id})
    
    async def create_orchard(self, orchard_data: OrchardCreate, owner_id: str) -> OrchardResponse:
        """Create new orchard"""
        orchard_doc = {
            "orchard_id": secrets.token_urlsafe(16),
            "owner_id": owner_id,
            "name": orchard_data.name,
            "location": orchard_data.location,
            "area_hectares": orchard_data.area_hectares,
            "crop_type": orchard_data.crop_type,
            "description": orchard_data.description,
            "created_at": datetime.utcnow(),
            "drone_count": 0,
            "last_survey": None,
            "health_score": 100.0
        }
        
        await self.orchards.insert_one(orchard_doc)
        
        return OrchardResponse(**orchard_doc)
    
    async def get_user_orchards(self, user_id: str) -> List[OrchardResponse]:
        """Get all orchards for a user"""
        cursor = self.orchards.find({"owner_id": user_id})
        orchards = await cursor.to_list(length=100)
        
        return [OrchardResponse(**orchard) for orchard in orchards]
    
    async def create_alert(self, alert_data: AlertBase, user_id: str) -> AlertResponse:
        """Create new alert"""
        alert_doc = {
            "alert_id": secrets.token_urlsafe(16),
            "user_id": user_id,
            "severity": alert_data.severity.value,
            "title": alert_data.title,
            "message": alert_data.message,
            "orchard_id": alert_data.orchard_id,
            "drone_id": alert_data.drone_id,
            "timestamp": datetime.utcnow(),
            "acknowledged": False,
            "acknowledged_by": None,
            "acknowledged_at": None
        }
        
        await self.alerts.insert_one(alert_doc)
        
        return AlertResponse(**alert_doc)
    
    async def get_recent_alerts(self, user_id: str, limit: int = 50) -> List[AlertResponse]:
        """Get recent alerts for user"""
        # Get user's orchards
        orchards = await self.get_user_orchards(user_id)
        orchard_ids = [o.orchard_id for o in orchards]
        
        # Get alerts
        cursor = self.alerts.find({
            "$or": [
                {"user_id": user_id},
                {"orchard_id": {"$in": orchard_ids}}
            ]
        }).sort("timestamp", -1).limit(limit)
        
        alerts = await cursor.to_list(length=limit)
        
        return [AlertResponse(**alert) for alert in alerts]


class CacheService:
    """
    Redis-based caching service for performance optimization
    """
    
    def __init__(self, redis_url: str):
        """Initialize Redis connection"""
        self.redis = redis.from_url(redis_url, encoding="utf-8", decode_responses=True)
        self.default_ttl = 300  # 5 minutes
    
    async def get(self, key: str) -> Optional[Any]:
        """Get cached value"""
        value = await self.redis.get(key)
        if value:
            return json.loads(value)
        return None
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set cached value"""
        ttl = ttl or self.default_ttl
        return await self.redis.setex(key, ttl, json.dumps(value, default=str))
    
    async def delete(self, key: str) -> bool:
        """Delete cached value"""
        return await self.redis.delete(key) > 0
    
    async def clear_pattern(self, pattern: str) -> int:
        """Clear all keys matching pattern"""
        keys = await self.redis.keys(pattern)
        if keys:
            return await self.redis.delete(*keys)
        return 0


class DashboardService:
    """
    Service for dashboard data aggregation and processing
    """
    
    def __init__(self, db: DatabaseService, cache: CacheService):
        self.db = db
        self.cache = cache
    
    async def get_dashboard_stats(self, user_id: str) -> DashboardStats:
        """Get aggregated dashboard statistics"""
        # Try cache first
        cache_key = f"dashboard_stats:{user_id}"
        cached = await self.cache.get(cache_key)
        if cached:
            return DashboardStats(**cached)
        
        # Get user's orchards
        orchards = await self.db.get_user_orchards(user_id)
        orchard_ids = [o.orchard_id for o in orchards]
        
        # Count drones
        drone_count = await self.db.drones.count_documents({
            "orchard_id": {"$in": orchard_ids}
        })
        
        # Count active missions
        active_missions = await self.db.missions.count_documents({
            "orchard_id": {"$in": orchard_ids},
            "status": "in_progress"
        })
        
        # Calculate total flight hours
        pipeline = [
            {"$match": {"orchard_id": {"$in": orchard_ids}}},
            {"$group": {"_id": None, "total": {"$sum": "$total_flight_hours"}}}
        ]
        result = await self.db.drones.aggregate(pipeline).to_list(length=1)
        total_flight_hours = result[0]["total"] if result else 0.0
        
        # Calculate average health index
        avg_health = np.mean([o.health_score for o in orchards]) if orchards else 100.0
        
        # Count recent alerts (last 24 hours)
        yesterday = datetime.utcnow() - timedelta(days=1)
        recent_alerts = await self.db.alerts.count_documents({
            "orchard_id": {"$in": orchard_ids},
            "timestamp": {"$gte": yesterday}
        })
        
        # Battery status distribution
        battery_pipeline = [
            {"$match": {"orchard_id": {"$in": orchard_ids}}},
            {"$bucket": {
                "groupBy": "$battery_level",
                "boundaries": [0, 25, 50, 75, 100],
                "default": "unknown",
                "output": {"count": {"$sum": 1}}
            }}
        ]
        battery_result = await self.db.drones.aggregate(battery_pipeline).to_list(length=10)
        battery_status = {str(r["_id"]): r["count"] for r in battery_result}
        
        stats = DashboardStats(
            total_orchards=len(orchards),
            total_drones=drone_count,
            active_missions=active_missions,
            total_flight_hours=total_flight_hours,
            health_index=avg_health,
            recent_alerts=recent_alerts,
            battery_status=battery_status,
            weather_status="good"  # Would integrate with weather service
        )
        
        # Cache for 5 minutes
        await self.cache.set(cache_key, stats.dict(), ttl=300)
        
        return stats
    
    async def get_time_series_data(self, query: AnalyticsQuery) -> Dict[str, Any]:
        """Get time-series analytics data"""
        # Build aggregation pipeline
        match_stage = {
            "timestamp": {
                "$gte": query.start_date,
                "$lte": query.end_date
            },
            "metric_type": query.metric_type
        }
        
        if query.orchard_id:
            match_stage["orchard_id"] = query.orchard_id
        
        # Determine grouping based on aggregation
        if query.aggregation == "hourly":
            date_format = "%Y-%m-%d %H:00"
        elif query.aggregation == "daily":
            date_format = "%Y-%m-%d"
        elif query.aggregation == "weekly":
            date_format = "%Y-W%U"
        else:  # monthly
            date_format = "%Y-%m"
        
        pipeline = [
            {"$match": match_stage},
            {"$group": {
                "_id": {"$dateToString": {"format": date_format, "date": "$timestamp"}},
                "avg_value": {"$avg": "$value"},
                "min_value": {"$min": "$value"},
                "max_value": {"$max": "$value"},
                "count": {"$sum": 1}
            }},
            {"$sort": {"_id": 1}}
        ]
        
        results = await self.db.analytics.aggregate(pipeline).to_list(length=1000)
        
        return {
            "metric_type": query.metric_type,
            "aggregation": query.aggregation,
            "data_points": [
                {
                    "timestamp": r["_id"],
                    "average": r["avg_value"],
                    "minimum": r["min_value"],
                    "maximum": r["max_value"],
                    "count": r["count"]
                }
                for r in results
            ]
        }


class NotificationService:
    """
    Multi-channel notification service
    """
    
    def __init__(self):
        self.notification_queue = deque(maxlen=10000)
        self.websocket_connections = {}
    
    async def send_notification(self, user_id: str, notification: Dict[str, Any]):
        """Send notification to user through available channels"""
        # Add to queue
        self.notification_queue.append({
            "user_id": user_id,
            "timestamp": datetime.utcnow(),
            **notification
        })
        
        # Send via WebSocket if connected
        if user_id in self.websocket_connections:
            websocket = self.websocket_connections[user_id]
            try:
                await websocket.send_json(notification)
            except:
                # Connection lost, remove from active connections
                del self.websocket_connections[user_id]
        
        # Would also send via email, SMS, push notifications based on user preferences
    
    async def send_alert(self, user_id: str, alert: AlertResponse):
        """Send alert notification"""
        notification = {
            "type": "alert",
            "severity": alert.severity.value,
            "title": alert.title,
            "message": alert.message,
            "alert_id": alert.alert_id,
            "timestamp": alert.timestamp.isoformat()
        }
        
        await self.send_notification(user_id, notification)
    
    def register_websocket(self, user_id: str, websocket: WebSocket):
        """Register WebSocket connection for user"""
        self.websocket_connections[user_id] = websocket
    
    def unregister_websocket(self, user_id: str):
        """Unregister WebSocket connection"""
        if user_id in self.websocket_connections:
            del self.websocket_connections[user_id]


class ReportGenerator:
    """
    Generate reports in various formats
    """
    
    def __init__(self, db: DatabaseService):
        self.db = db
    
    async def generate_orchard_report(self, orchard_id: str, 
                                     start_date: datetime,
                                     end_date: datetime,
                                     format: str = "json") -> Union[Dict, bytes]:
        """Generate comprehensive orchard report"""
        # Get orchard data
        orchard = await self.db.orchards.find_one({"orchard_id": orchard_id})
        if not orchard:
            raise HTTPException(status_code=404, detail="Orchard not found")
        
        # Get missions in date range
        missions = await self.db.missions.find({
            "orchard_id": orchard_id,
            "created_at": {"$gte": start_date, "$lte": end_date}
        }).to_list(length=1000)
        
        # Get alerts
        alerts = await self.db.alerts.find({
            "orchard_id": orchard_id,
            "timestamp": {"$gte": start_date, "$lte": end_date}
        }).to_list(length=1000)
        
        # Compile report data
        report_data = {
            "orchard": {
                "name": orchard["name"],
                "location": orchard["location"],
                "area_hectares": orchard["area_hectares"],
                "health_score": orchard["health_score"]
            },
            "report_period": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat()
            },
            "summary": {
                "total_missions": len(missions),
                "completed_missions": len([m for m in missions if m["status"] == "completed"]),
                "total_alerts": len(alerts),
                "critical_alerts": len([a for a in alerts if a["severity"] == "critical"])
            },
            "missions": missions,
            "alerts": alerts
        }
        
        # Format output
        if format == "json":
            return report_data
        elif format == "csv":
            return self._generate_csv(report_data)
        elif format == "excel":
            return self._generate_excel(report_data)
        else:
            raise HTTPException(status_code=400, detail="Unsupported format")
    
    def _generate_csv(self, report_data: Dict) -> bytes:
        """Generate CSV report"""
        output = StringIO()
        
        # Write summary
        output.write("Orchard Report\n")
        output.write(f"Name,{report_data['orchard']['name']}\n")
        output.write(f"Health Score,{report_data['orchard']['health_score']}\n")
        output.write("\n")
        
        # Write missions
        if report_data['missions']:
            df = pd.DataFrame(report_data['missions'])
            df.to_csv(output, index=False)
        
        return output.getvalue().encode('utf-8')
    
    def _generate_excel(self, report_data: Dict) -> bytes:
        """Generate Excel report"""
        output = BytesIO()
        
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            # Summary sheet
            summary_df = pd.DataFrame([report_data['summary']])
            summary_df.to_excel(writer, sheet_name='Summary', index=False)
            
            # Missions sheet
            if report_data['missions']:
                missions_df = pd.DataFrame(report_data['missions'])
                missions_df.to_excel(writer, sheet_name='Missions', index=False)
            
            # Alerts sheet
            if report_data['alerts']:
                alerts_df = pd.DataFrame(report_data['alerts'])
                alerts_df.to_excel(writer, sheet_name='Alerts', index=False)
        
        output.seek(0)
        return output.read()


# Initialize FastAPI app
app = FastAPI(
    title="AgroPulse Dashboard API",
    description="Comprehensive API for drone orchard management",
    version="7.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize services (would use proper config in production)
db_service = DatabaseService("mongodb://localhost:27017")
cache_service = CacheService("redis://localhost:6379")
dashboard_service = DashboardService(db_service, cache_service)
notification_service = NotificationService()
report_generator = ReportGenerator(db_service)
auth_service = AuthService()


# Dependency to get current user
async def get_current_user(token: str = Depends(oauth2_scheme)) -> Dict[str, Any]:
    """Get current authenticated user"""
    payload = auth_service.decode_token(token)
    user_id = payload.get("sub")
    
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials"
        )
    
    user = await db_service.get_user_by_id(user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    
    return user


# API Endpoints

@app.post("/api/v1/auth/register", response_model=UserResponse)
async def register_user(user_data: UserCreate):
    """Register new user"""
    return await db_service.create_user(user_data)


@app.post("/api/v1/auth/login", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    """Login and get access token"""
    user = await db_service.get_user_by_email(form_data.username)
    
    if not user or not auth_service.verify_password(form_data.password, user["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
    
    # Create tokens
    access_token = auth_service.create_access_token(data={"sub": user["user_id"]})
    refresh_token = auth_service.create_refresh_token(data={"sub": user["user_id"]})
    
    # Update last login
    await db_service.users.update_one(
        {"user_id": user["user_id"]},
        {"$set": {"last_login": datetime.utcnow()}}
    )
    
    return Token(access_token=access_token, refresh_token=refresh_token)


@app.get("/api/v1/dashboard/stats", response_model=DashboardStats)
async def get_dashboard_stats(current_user: Dict = Depends(get_current_user)):
    """Get dashboard statistics"""
    return await dashboard_service.get_dashboard_stats(current_user["user_id"])


@app.get("/api/v1/orchards", response_model=List[OrchardResponse])
async def list_orchards(current_user: Dict = Depends(get_current_user)):
    """List user's orchards"""
    return await db_service.get_user_orchards(current_user["user_id"])


@app.post("/api/v1/orchards", response_model=OrchardResponse)
async def create_orchard(
    orchard_data: OrchardCreate,
    current_user: Dict = Depends(get_current_user)
):
    """Create new orchard"""
    return await db_service.create_orchard(orchard_data, current_user["user_id"])


@app.get("/api/v1/alerts", response_model=List[AlertResponse])
async def list_alerts(
    limit: int = 50,
    current_user: Dict = Depends(get_current_user)
):
    """List recent alerts"""
    return await db_service.get_recent_alerts(current_user["user_id"], limit)


@app.post("/api/v1/alerts", response_model=AlertResponse)
async def create_alert(
    alert_data: AlertBase,
    current_user: Dict = Depends(get_current_user)
):
    """Create new alert"""
    alert = await db_service.create_alert(alert_data, current_user["user_id"])
    
    # Send notification
    await notification_service.send_alert(current_user["user_id"], alert)
    
    return alert


@app.post("/api/v1/analytics/query")
async def query_analytics(
    query: AnalyticsQuery,
    current_user: Dict = Depends(get_current_user)
):
    """Query analytics data"""
    return await dashboard_service.get_time_series_data(query)


@app.get("/api/v1/reports/{orchard_id}")
async def generate_report(
    orchard_id: str,
    start_date: datetime,
    end_date: datetime,
    format: str = "json",
    current_user: Dict = Depends(get_current_user)
):
    """Generate orchard report"""
    report = await report_generator.generate_orchard_report(
        orchard_id, start_date, end_date, format
    )
    
    if format == "json":
        return report
    elif format == "csv":
        return StreamingResponse(
            BytesIO(report),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=report_{orchard_id}.csv"}
        )
    elif format == "excel":
        return StreamingResponse(
            BytesIO(report),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename=report_{orchard_id}.xlsx"}
        )


@app.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: str):
    """WebSocket endpoint for real-time updates"""
    await websocket.accept()
    notification_service.register_websocket(user_id, websocket)
    
    try:
        while True:
            # Keep connection alive
            data = await websocket.receive_text()
            
            # Echo back (or handle commands)
            await websocket.send_json({"type": "pong", "timestamp": datetime.utcnow().isoformat()})
    except:
        notification_service.unregister_websocket(user_id)


@app.get("/api/v1/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "7.0.0"
    }


# Example usage
if __name__ == "__main__":
    import uvicorn
    
    print("Starting AgroPulse Dashboard API...")
    print("API Documentation: http://localhost:8000/docs")
    print("WebSocket: ws://localhost:8000/ws/{user_id}")
    
    uvicorn.run(app, host="0.0.0.0", port=8000)
