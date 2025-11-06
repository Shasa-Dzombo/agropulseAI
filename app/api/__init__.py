"""
🌐 AgroPulse API Package

FastAPI routers and endpoints for the AgroPulse platform.

Routers:
- auth: Authentication and authorization
- users: User management
- farms: Farm management
- diagnoses: Crop diagnosis system
- chamas: Digital cooperatives
- iot: IoT device management
- products: Product catalog
- notifications: Notification system

Author: AgroPulse Engineering Team
"""

from fastapi import APIRouter

# API version
API_VERSION = "v1"
API_PREFIX = f"/api/{API_VERSION}"

# Main API router
api_router = APIRouter()

__all__ = [
    'api_router',
    'API_VERSION',
    'API_PREFIX'
]
