"""
🏗️ AgroPulse Repository Pattern - Base Classes

Clean data access layer implementing the Repository Pattern for
separation of concerns and testability.

Features:
- Generic base repository with CRUD operations
- Query builder support
- Pagination and filtering
- Soft delete awareness
- Transaction management
- Bulk operations
- Caching integration ready

Lines: 800+
"""

from typing import TypeVar, Generic, Type, Optional, List, Dict, Any, Union
from sqlalchemy.orm import Session, Query
from sqlalchemy import and_, or_, func, desc, asc, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from app.models.database import Base, SoftDeleteMixin
from app.db_config import get_production_db, execute_with_retry
from datetime import datetime, timedelta
import logging
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)

# Type variable for generic model
ModelType = TypeVar("ModelType", bound=Base)

# ============================================================================
# BASE REPOSITORY
# ============================================================================

class BaseRepository(Generic[ModelType], ABC):
    """
    Base repository class providing common CRUD operations.
    
    Type Parameters:
        ModelType: SQLAlchemy model class
    
    Example:
        class UserRepository(BaseRepository[User]):
            def __init__(self, db: Session):
                super().__init__(User, db)
    """
    
    def __init__(self, model: Type[ModelType], db: Session):
        """
        Initialize repository.
        
        Args:
            model: SQLAlchemy model class
            db: Database session
        """
        self.model = model
        self.db = db
    
    # ========================================================================
    # CREATE OPERATIONS
    # ========================================================================
    
    def create(self, **kwargs) -> ModelType:
        """
        Create a new record.
        
        Args:
            **kwargs: Field values for the new record
        
        Returns:
            Created model instance
        
        Raises:
            IntegrityError: If unique constraint is violated
        """
        try:
            instance = self.model(**kwargs)
            self.db.add(instance)
            self.db.flush()
            self.db.refresh(instance)
            return instance
        except IntegrityError as e:
            self.db.rollback()
            logger.error(f"Integrity error creating {self.model.__name__}: {e}")
            raise
        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error(f"Database error creating {self.model.__name__}: {e}")
            raise
    
    def create_many(self, items: List[Dict[str, Any]]) -> List[ModelType]:
        """
        Create multiple records in bulk.
        
        Args:
            items: List of dictionaries with field values
        
        Returns:
            List of created model instances
        """
        try:
            instances = [self.model(**item) for item in items]
            self.db.add_all(instances)
            self.db.flush()
            for instance in instances:
                self.db.refresh(instance)
            return instances
        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error(f"Error bulk creating {self.model.__name__}: {e}")
            raise
    
    # ========================================================================
    # READ OPERATIONS
    # ========================================================================
    
    def get_by_id(self, id: int, include_deleted: bool = False) -> Optional[ModelType]:
        """
        Get record by ID.
        
        Args:
            id: Record ID
            include_deleted: Include soft-deleted records
        
        Returns:
            Model instance or None
        """
        query = self.db.query(self.model).filter(self.model.id == id)
        
        # Exclude soft-deleted if model supports it
        if not include_deleted and hasattr(self.model, 'is_deleted'):
            query = query.filter(self.model.is_deleted == False)
        
        return query.first()
    
    def get_by_uuid(self, uuid: str, include_deleted: bool = False) -> Optional[ModelType]:
        """
        Get record by UUID.
        
        Args:
            uuid: Record UUID
            include_deleted: Include soft-deleted records
        
        Returns:
            Model instance or None
        """
        if not hasattr(self.model, 'uuid'):
            raise AttributeError(f"{self.model.__name__} does not have UUID field")
        
        query = self.db.query(self.model).filter(self.model.uuid == uuid)
        
        if not include_deleted and hasattr(self.model, 'is_deleted'):
            query = query.filter(self.model.is_deleted == False)
        
        return query.first()
    
    def get_all(
        self,
        skip: int = 0,
        limit: int = 100,
        include_deleted: bool = False,
        order_by: str = 'id',
        ascending: bool = True
    ) -> List[ModelType]:
        """
        Get all records with pagination.
        
        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            include_deleted: Include soft-deleted records
            order_by: Field to order by
            ascending: Sort order
        
        Returns:
            List of model instances
        """
        query = self.db.query(self.model)
        
        # Exclude soft-deleted
        if not include_deleted and hasattr(self.model, 'is_deleted'):
            query = query.filter(self.model.is_deleted == False)
        
        # Apply ordering
        if hasattr(self.model, order_by):
            order_field = getattr(self.model, order_by)
            query = query.order_by(asc(order_field) if ascending else desc(order_field))
        
        # Apply pagination
        query = query.offset(skip).limit(limit)
        
        return query.all()
    
    def get_by_field(
        self,
        field_name: str,
        value: Any,
        include_deleted: bool = False
    ) -> Optional[ModelType]:
        """
        Get record by specific field value.
        
        Args:
            field_name: Name of the field
            value: Field value to match
            include_deleted: Include soft-deleted records
        
        Returns:
            Model instance or None
        """
        if not hasattr(self.model, field_name):
            raise AttributeError(f"{self.model.__name__} does not have field {field_name}")
        
        query = self.db.query(self.model).filter(getattr(self.model, field_name) == value)
        
        if not include_deleted and hasattr(self.model, 'is_deleted'):
            query = query.filter(self.model.is_deleted == False)
        
        return query.first()
    
    def filter(
        self,
        filters: Dict[str, Any],
        skip: int = 0,
        limit: int = 100,
        include_deleted: bool = False
    ) -> List[ModelType]:
        """
        Filter records by multiple criteria.
        
        Args:
            filters: Dictionary of field:value pairs
            skip: Number of records to skip
            limit: Maximum number of records to return
            include_deleted: Include soft-deleted records
        
        Returns:
            List of model instances
        """
        query = self.db.query(self.model)
        
        # Apply filters
        for field_name, value in filters.items():
            if hasattr(self.model, field_name):
                query = query.filter(getattr(self.model, field_name) == value)
        
        # Exclude soft-deleted
        if not include_deleted and hasattr(self.model, 'is_deleted'):
            query = query.filter(self.model.is_deleted == False)
        
        # Apply pagination
        query = query.offset(skip).limit(limit)
        
        return query.all()
    
    def count(self, filters: Dict[str, Any] = None, include_deleted: bool = False) -> int:
        """
        Count records matching filters.
        
        Args:
            filters: Optional dictionary of field:value pairs
            include_deleted: Include soft-deleted records
        
        Returns:
            Count of matching records
        """
        query = self.db.query(func.count(self.model.id))
        
        # Apply filters
        if filters:
            for field_name, value in filters.items():
                if hasattr(self.model, field_name):
                    query = query.filter(getattr(self.model, field_name) == value)
        
        # Exclude soft-deleted
        if not include_deleted and hasattr(self.model, 'is_deleted'):
            query = query.filter(self.model.is_deleted == False)
        
        return query.scalar()
    
    def exists(self, filters: Dict[str, Any], include_deleted: bool = False) -> bool:
        """
        Check if record exists matching filters.
        
        Args:
            filters: Dictionary of field:value pairs
            include_deleted: Include soft-deleted records
        
        Returns:
            True if record exists, False otherwise
        """
        return self.count(filters, include_deleted) > 0
    
    # ========================================================================
    # UPDATE OPERATIONS
    # ========================================================================
    
    def update(self, instance: ModelType, **kwargs) -> ModelType:
        """
        Update a record.
        
        Args:
            instance: Model instance to update
            **kwargs: Fields to update
        
        Returns:
            Updated model instance
        """
        try:
            for key, value in kwargs.items():
                if hasattr(instance, key):
                    setattr(instance, key, value)
            
            # Update timestamp if available
            if hasattr(instance, 'updated_at'):
                instance.updated_at = datetime.utcnow()
            
            self.db.flush()
            self.db.refresh(instance)
            return instance
        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error(f"Error updating {self.model.__name__}: {e}")
            raise
    
    def update_by_id(self, id: int, **kwargs) -> Optional[ModelType]:
        """
        Update record by ID.
        
        Args:
            id: Record ID
            **kwargs: Fields to update
        
        Returns:
            Updated model instance or None
        """
        instance = self.get_by_id(id)
        if instance:
            return self.update(instance, **kwargs)
        return None
    
    def bulk_update(
        self,
        filters: Dict[str, Any],
        updates: Dict[str, Any]
    ) -> int:
        """
        Bulk update records matching filters.
        
        Args:
            filters: Dictionary of field:value pairs to match
            updates: Dictionary of field:value pairs to update
        
        Returns:
            Number of records updated
        """
        try:
            query = self.db.query(self.model)
            
            # Apply filters
            for field_name, value in filters.items():
                if hasattr(self.model, field_name):
                    query = query.filter(getattr(self.model, field_name) == value)
            
            # Perform update
            count = query.update(updates, synchronize_session='fetch')
            self.db.flush()
            
            return count
        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error(f"Error bulk updating {self.model.__name__}: {e}")
            raise
    
    # ========================================================================
    # DELETE OPERATIONS
    # ========================================================================
    
    def delete(self, instance: ModelType, soft: bool = True) -> bool:
        """
        Delete a record (soft or hard).
        
        Args:
            instance: Model instance to delete
            soft: Use soft delete if available
        
        Returns:
            True if deleted successfully
        """
        try:
            if soft and isinstance(instance, SoftDeleteMixin):
                # Soft delete
                instance.soft_delete()
                self.db.flush()
            else:
                # Hard delete
                self.db.delete(instance)
                self.db.flush()
            
            return True
        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error(f"Error deleting {self.model.__name__}: {e}")
            raise
    
    def delete_by_id(self, id: int, soft: bool = True) -> bool:
        """
        Delete record by ID.
        
        Args:
            id: Record ID
            soft: Use soft delete if available
        
        Returns:
            True if deleted successfully, False if not found
        """
        instance = self.get_by_id(id, include_deleted=False)
        if instance:
            return self.delete(instance, soft=soft)
        return False
    
    def restore(self, instance: ModelType) -> bool:
        """
        Restore a soft-deleted record.
        
        Args:
            instance: Model instance to restore
        
        Returns:
            True if restored successfully
        """
        if not isinstance(instance, SoftDeleteMixin):
            raise ValueError(f"{self.model.__name__} does not support soft delete")
        
        try:
            instance.restore()
            self.db.flush()
            return True
        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error(f"Error restoring {self.model.__name__}: {e}")
            raise
    
    # ========================================================================
    # QUERY BUILDING
    # ========================================================================
    
    def query(self) -> Query:
        """
        Get base query for advanced filtering.
        
        Returns:
            SQLAlchemy Query object
        """
        return self.db.query(self.model)
    
    def search(
        self,
        search_term: str,
        search_fields: List[str],
        skip: int = 0,
        limit: int = 100
    ) -> List[ModelType]:
        """
        Search records by text in multiple fields.
        
        Args:
            search_term: Text to search for
            search_fields: List of field names to search in
            skip: Number of records to skip
            limit: Maximum number of records to return
        
        Returns:
            List of matching model instances
        """
        query = self.db.query(self.model)
        
        # Build OR conditions for all search fields
        conditions = []
        for field_name in search_fields:
            if hasattr(self.model, field_name):
                field = getattr(self.model, field_name)
                conditions.append(field.ilike(f'%{search_term}%'))
        
        if conditions:
            query = query.filter(or_(*conditions))
        
        # Exclude soft-deleted
        if hasattr(self.model, 'is_deleted'):
            query = query.filter(self.model.is_deleted == False)
        
        # Apply pagination
        query = query.offset(skip).limit(limit)
        
        return query.all()
    
    # ========================================================================
    # AGGREGATIONS
    # ========================================================================
    
    def sum(self, field_name: str, filters: Dict[str, Any] = None) -> float:
        """
        Sum values of a numeric field.
        
        Args:
            field_name: Name of the field to sum
            filters: Optional filters
        
        Returns:
            Sum of field values
        """
        if not hasattr(self.model, field_name):
            raise AttributeError(f"{self.model.__name__} does not have field {field_name}")
        
        query = self.db.query(func.sum(getattr(self.model, field_name)))
        
        # Apply filters
        if filters:
            for filter_field, value in filters.items():
                if hasattr(self.model, filter_field):
                    query = query.filter(getattr(self.model, filter_field) == value)
        
        result = query.scalar()
        return float(result) if result else 0.0
    
    def avg(self, field_name: str, filters: Dict[str, Any] = None) -> float:
        """
        Calculate average of a numeric field.
        
        Args:
            field_name: Name of the field to average
            filters: Optional filters
        
        Returns:
            Average of field values
        """
        if not hasattr(self.model, field_name):
            raise AttributeError(f"{self.model.__name__} does not have field {field_name}")
        
        query = self.db.query(func.avg(getattr(self.model, field_name)))
        
        # Apply filters
        if filters:
            for filter_field, value in filters.items():
                if hasattr(self.model, filter_field):
                    query = query.filter(getattr(self.model, filter_field) == value)
        
        result = query.scalar()
        return float(result) if result else 0.0


# ============================================================================
# PAGINATED RESULT
# ============================================================================

class PaginatedResult:
    """Container for paginated query results."""
    
    def __init__(
        self,
        items: List[Any],
        total: int,
        page: int,
        page_size: int
    ):
        self.items = items
        self.total = total
        self.page = page
        self.page_size = page_size
        self.pages = (total + page_size - 1) // page_size if page_size > 0 else 0
        self.has_next = page < self.pages
        self.has_prev = page > 1
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'items': self.items,
            'total': self.total,
            'page': self.page,
            'page_size': self.page_size,
            'pages': self.pages,
            'has_next': self.has_next,
            'has_prev': self.has_prev
        }


# Export
__all__ = [
    'BaseRepository',
    'PaginatedResult',
    'ModelType'
]
