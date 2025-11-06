"""
Services Package

This package contains all business logic services for the AgroPulse application.

Services implement the Service Layer pattern, encapsulating business logic and
coordinating between repositories, external services, and API endpoints.

Available Services:
- BaseService: Foundation class with common utilities
- UserService: User management and authentication business logic
- FarmService: Farm operations and management
- ChamaService: Digital cooperative and microfinance services
- IoTService: IoT device and sensor data management
- ProductService: Marketplace and product catalog services
- NotificationService: Multi-channel notification delivery
- AnalyticsService: Data analytics and reporting

Design Principles:
1. Single Responsibility: Each service focuses on one domain
2. Transaction Management: Services handle database transactions
3. Business Rules: All business logic is encapsulated in services
4. Validation: Comprehensive input validation
5. Error Handling: Consistent exception handling
6. Logging: Activity and audit logging
"""

from app.services.base import (
    BaseService,
    ServiceException,
    ValidationException,
    BusinessRuleException,
    InsufficientPermissionsException,
    ResourceNotFoundException
)
from app.services.user_service import UserService
from app.services.farm_service import FarmService
from app.services.chama_service import ChamaService
from app.services.iot_service import IoTService
from app.services.product_service import ProductService
from app.services.notification_service import NotificationService, notification_service
from app.services.analytics_service import AnalyticsService

__all__ = [
    # Base classes
    "BaseService",
    "ServiceException",
    "ValidationException",
    "BusinessRuleException",
    "InsufficientPermissionsException",
    "ResourceNotFoundException",
    
    # Services
    "UserService",
    "FarmService",
    "ChamaService",
    "IoTService",
    "ProductService",
    "NotificationService",
    "notification_service",
    "AnalyticsService",
]
