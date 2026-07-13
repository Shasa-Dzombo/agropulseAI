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

# NOTE: FarmService, ChamaService, IoTService, ProductService, UserService, and
# AnalyticsService are not re-exported here. They depend on app.models.database
# (a second, parallel model/DB stack not used by any currently-registered API
# router) and some reference model classes that don't exist there at all
# (e.g. Harvest, CropType, GrowthStage on Farm/Field). None of the registered
# routers import services at the package level, so this package intentionally
# only eagerly loads what's safe. Import service submodules directly
# (e.g. `from app.services.payment import ...`) as the registered routers do.

__all__ = [
    # Base classes
    "BaseService",
    "ServiceException",
    "ValidationException",
    "BusinessRuleException",
    "InsufficientPermissionsException",
    "ResourceNotFoundException",
]
