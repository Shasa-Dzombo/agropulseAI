"""
Base Service Module

This module provides the foundation for all business logic services in the application.
It implements common patterns and utilities that are shared across service classes.

Design Patterns:
- Service Layer Pattern: Encapsulates business logic
- Transaction Management: Ensures data consistency
- Error Handling: Consistent exception handling
- Logging: Comprehensive activity logging
- Validation: Business rule validation

All service classes should inherit from BaseService to ensure consistency.
"""

from sqlalchemy.orm import Session
from typing import Optional, Dict, Any, List, Type, TypeVar
from datetime import datetime, timedelta
from decimal import Decimal
import logging
from contextlib import contextmanager

from app.models.database import Base
from app.repositories.base import BaseRepository

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Type variable for generic models
T = TypeVar('T', bound=Base)


class ServiceException(Exception):
    """Base exception for service layer errors."""
    def __init__(self, message: str, code: str = "SERVICE_ERROR", details: Optional[Dict] = None):
        self.message = message
        self.code = code
        self.details = details or {}
        super().__init__(self.message)


class ValidationException(ServiceException):
    """Exception raised when business validation fails."""
    def __init__(self, message: str, field: Optional[str] = None, details: Optional[Dict] = None):
        super().__init__(message, code="VALIDATION_ERROR", details=details or {})
        self.field = field


class BusinessRuleException(ServiceException):
    """Exception raised when a business rule is violated."""
    def __init__(self, message: str, rule: str, details: Optional[Dict] = None):
        super().__init__(message, code="BUSINESS_RULE_VIOLATION", details=details or {})
        self.rule = rule


class InsufficientPermissionsException(ServiceException):
    """Exception raised when user lacks required permissions."""
    def __init__(self, message: str = "Insufficient permissions", required_role: Optional[str] = None):
        super().__init__(message, code="INSUFFICIENT_PERMISSIONS")
        self.required_role = required_role


class ResourceNotFoundException(ServiceException):
    """Exception raised when a resource is not found."""
    def __init__(self, resource_type: str, resource_id: Any):
        message = f"{resource_type} with ID {resource_id} not found"
        super().__init__(message, code="RESOURCE_NOT_FOUND")
        self.resource_type = resource_type
        self.resource_id = resource_id


class BaseService:
    """
    Base service class providing common functionality for all services.
    
    Features:
    - Transaction management
    - Error handling and logging
    - Common validation methods
    - Audit logging
    - Permission checking
    
    Usage:
        class UserService(BaseService):
            def __init__(self, db: Session):
                super().__init__(db)
                self.user_repo = UserRepository(db)
    """
    
    def __init__(self, db: Session):
        """
        Initialize the base service.
        
        Args:
            db: SQLAlchemy database session
        """
        self.db = db
        self.logger = logging.getLogger(self.__class__.__name__)
    
    @contextmanager
    def transaction(self):
        """
        Context manager for database transactions.
        Automatically commits on success and rolls back on error.
        
        Usage:
            with self.transaction():
                # Perform database operations
                user = self.create_user(data)
                self.send_welcome_email(user)
        """
        try:
            yield self.db
            self.db.commit()
            self.logger.info("Transaction committed successfully")
        except Exception as e:
            self.db.rollback()
            self.logger.error(f"Transaction rolled back due to error: {e}")
            raise
    
    def validate_not_none(self, value: Any, field_name: str):
        """
        Validate that a value is not None.
        
        Args:
            value: Value to validate
            field_name: Name of the field for error message
            
        Raises:
            ValidationException: If value is None
        """
        if value is None:
            raise ValidationException(
                f"{field_name} is required",
                field=field_name
            )
    
    def validate_positive(self, value: float, field_name: str):
        """
        Validate that a numeric value is positive.
        
        Args:
            value: Value to validate
            field_name: Name of the field for error message
            
        Raises:
            ValidationException: If value is not positive
        """
        if value <= 0:
            raise ValidationException(
                f"{field_name} must be positive",
                field=field_name,
                details={"value": value}
            )
    
    def validate_min_value(self, value: float, min_value: float, field_name: str):
        """
        Validate that a value meets minimum requirement.
        
        Args:
            value: Value to validate
            min_value: Minimum allowed value
            field_name: Name of the field for error message
            
        Raises:
            ValidationException: If value is below minimum
        """
        if value < min_value:
            raise ValidationException(
                f"{field_name} must be at least {min_value}",
                field=field_name,
                details={"value": value, "min_value": min_value}
            )
    
    def validate_max_value(self, value: float, max_value: float, field_name: str):
        """
        Validate that a value does not exceed maximum.
        
        Args:
            value: Value to validate
            max_value: Maximum allowed value
            field_name: Name of the field for error message
            
        Raises:
            ValidationException: If value exceeds maximum
        """
        if value > max_value:
            raise ValidationException(
                f"{field_name} must not exceed {max_value}",
                field=field_name,
                details={"value": value, "max_value": max_value}
            )
    
    def validate_string_length(self, value: str, min_length: int, max_length: int, field_name: str):
        """
        Validate string length.
        
        Args:
            value: String to validate
            min_length: Minimum length
            max_length: Maximum length
            field_name: Name of the field for error message
            
        Raises:
            ValidationException: If length is invalid
        """
        if len(value) < min_length:
            raise ValidationException(
                f"{field_name} must be at least {min_length} characters",
                field=field_name,
                details={"length": len(value), "min_length": min_length}
            )
        if len(value) > max_length:
            raise ValidationException(
                f"{field_name} must not exceed {max_length} characters",
                field=field_name,
                details={"length": len(value), "max_length": max_length}
            )
    
    def validate_email_format(self, email: str, field_name: str = "email"):
        """
        Validate email format.
        
        Args:
            email: Email address to validate
            field_name: Name of the field for error message
            
        Raises:
            ValidationException: If email format is invalid
        """
        import re
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, email):
            raise ValidationException(
                f"Invalid {field_name} format",
                field=field_name,
                details={"email": email}
            )
    
    def validate_phone_format(self, phone: str, field_name: str = "phone"):
        """
        Validate phone number format (Kenyan format).
        
        Args:
            phone: Phone number to validate
            field_name: Name of the field for error message
            
        Raises:
            ValidationException: If phone format is invalid
        """
        import re
        # Kenyan phone format: +254XXXXXXXXX or 07XXXXXXXX
        phone_pattern = r'^(\+254|0)[17]\d{8}$'
        if not re.match(phone_pattern, phone):
            raise ValidationException(
                f"Invalid {field_name} format. Expected: +254XXXXXXXXX or 07XXXXXXXX",
                field=field_name,
                details={"phone": phone}
            )
    
    def validate_date_range(self, start_date: datetime, end_date: datetime, field_name: str = "date range"):
        """
        Validate that end date is after start date.
        
        Args:
            start_date: Start date
            end_date: End date
            field_name: Name of the field for error message
            
        Raises:
            ValidationException: If date range is invalid
        """
        if end_date <= start_date:
            raise ValidationException(
                f"End date must be after start date for {field_name}",
                field=field_name,
                details={
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat()
                }
            )
    
    def check_resource_exists(self, resource: Optional[T], resource_type: str, resource_id: Any) -> T:
        """
        Check if a resource exists and raise exception if not.
        
        Args:
            resource: Resource to check
            resource_type: Type of resource for error message
            resource_id: ID of resource for error message
            
        Returns:
            The resource if it exists
            
        Raises:
            ResourceNotFoundException: If resource is None
        """
        if resource is None:
            raise ResourceNotFoundException(resource_type, resource_id)
        return resource
    
    def check_permission(self, user_role: str, required_role: str):
        """
        Check if user has required permission.
        
        Args:
            user_role: User's current role
            required_role: Required role for the operation
            
        Raises:
            InsufficientPermissionsException: If user lacks permission
        """
        role_hierarchy = {
            "admin": 3,
            "agronomist": 2,
            "user": 1
        }
        
        user_level = role_hierarchy.get(user_role, 0)
        required_level = role_hierarchy.get(required_role, 0)
        
        if user_level < required_level:
            raise InsufficientPermissionsException(
                f"Operation requires {required_role} role",
                required_role=required_role
            )
    
    def check_ownership(self, resource_owner_id: int, user_id: int, resource_type: str):
        """
        Check if user owns a resource.
        
        Args:
            resource_owner_id: ID of resource owner
            user_id: ID of current user
            resource_type: Type of resource for error message
            
        Raises:
            InsufficientPermissionsException: If user doesn't own resource
        """
        if resource_owner_id != user_id:
            raise InsufficientPermissionsException(
                f"You don't have permission to access this {resource_type}"
            )
    
    def log_activity(self, action: str, user_id: int, details: Optional[Dict] = None):
        """
        Log user activity for audit trail.
        
        Args:
            action: Action performed
            user_id: ID of user performing action
            details: Additional details about the action
        """
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "action": action,
            "user_id": user_id,
            "details": details or {}
        }
        self.logger.info(f"Activity: {log_entry}")
    
    def calculate_percentage(self, part: float, total: float) -> float:
        """
        Calculate percentage safely (handles division by zero).
        
        Args:
            part: Part value
            total: Total value
            
        Returns:
            Percentage value (0-100)
        """
        if total == 0:
            return 0.0
        return round((part / total) * 100, 2)
    
    def calculate_days_between(self, start_date: datetime, end_date: datetime) -> int:
        """
        Calculate number of days between two dates.
        
        Args:
            start_date: Start date
            end_date: End date
            
        Returns:
            Number of days
        """
        delta = end_date - start_date
        return delta.days
    
    def add_days_to_date(self, date: datetime, days: int) -> datetime:
        """
        Add days to a date.
        
        Args:
            date: Starting date
            days: Number of days to add
            
        Returns:
            New date
        """
        return date + timedelta(days=days)
    
    def format_currency(self, amount: float, currency: str = "KES") -> str:
        """
        Format amount as currency string.
        
        Args:
            amount: Amount to format
            currency: Currency code (default: KES)
            
        Returns:
            Formatted currency string
        """
        return f"{currency} {amount:,.2f}"
    
    def calculate_interest(self, principal: Decimal, rate: Decimal, days: int) -> Decimal:
        """
        Calculate simple interest.
        
        Args:
            principal: Principal amount
            rate: Annual interest rate (e.g., 0.12 for 12%)
            days: Number of days
            
        Returns:
            Interest amount
        """
        return principal * rate * Decimal(days) / Decimal(365)
    
    def paginate_results(self, items: List[T], page: int, page_size: int) -> Dict[str, Any]:
        """
        Paginate a list of items.
        
        Args:
            items: List of items to paginate
            page: Page number (1-indexed)
            page_size: Number of items per page
            
        Returns:
            Dictionary with pagination info and items
        """
        total_items = len(items)
        total_pages = (total_items + page_size - 1) // page_size
        
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        
        return {
            "items": items[start_idx:end_idx],
            "total_items": total_items,
            "total_pages": total_pages,
            "current_page": page,
            "page_size": page_size,
            "has_next": page < total_pages,
            "has_previous": page > 1
        }
    
    def sanitize_string(self, value: str) -> str:
        """
        Sanitize string input (remove extra whitespace, strip).
        
        Args:
            value: String to sanitize
            
        Returns:
            Sanitized string
        """
        import re
        # Remove extra whitespace
        value = re.sub(r'\s+', ' ', value)
        return value.strip()
    
    def generate_reference_number(self, prefix: str, id_value: int) -> str:
        """
        Generate a reference number.
        
        Args:
            prefix: Prefix for the reference (e.g., "INV", "LN")
            id_value: Numeric ID
            
        Returns:
            Reference number (e.g., "INV-000123")
        """
        return f"{prefix}-{id_value:06d}"
    
    def is_business_day(self, date: datetime) -> bool:
        """
        Check if a date is a business day (Monday-Friday).
        
        Args:
            date: Date to check
            
        Returns:
            True if business day, False otherwise
        """
        return date.weekday() < 5  # Monday = 0, Friday = 4
    
    def get_next_business_day(self, date: datetime) -> datetime:
        """
        Get the next business day from a given date.
        
        Args:
            date: Starting date
            
        Returns:
            Next business day
        """
        next_day = date + timedelta(days=1)
        while not self.is_business_day(next_day):
            next_day += timedelta(days=1)
        return next_day
    
    def merge_dicts(self, *dicts: Dict) -> Dict:
        """
        Merge multiple dictionaries.
        
        Args:
            *dicts: Dictionaries to merge
            
        Returns:
            Merged dictionary
        """
        result = {}
        for d in dicts:
            result.update(d)
        return result
    
    def chunk_list(self, items: List[T], chunk_size: int) -> List[List[T]]:
        """
        Split a list into chunks.
        
        Args:
            items: List to split
            chunk_size: Size of each chunk
            
        Returns:
            List of chunks
        """
        return [items[i:i + chunk_size] for i in range(0, len(items), chunk_size)]
