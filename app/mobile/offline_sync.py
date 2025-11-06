"""
Mobile Offline Sync Manager

Comprehensive offline-first synchronization system for mobile applications:
- Conflict resolution strategies (Last-Write-Wins, Merge, Custom)
- Delta sync for bandwidth efficiency
- Operational Transformation for real-time collaboration
- Background sync queues
- Binary data handling
- Incremental sync
- Sync state management

Supports offline-first architecture with seamless online/offline transitions.
"""

import asyncio
import hashlib
import json
import logging
import os
import pickle
import sqlite3
import time
import uuid
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple, Callable

import redis
from sqlalchemy import create_engine, Column, String, Integer, DateTime, Boolean, JSON, Float, LargeBinary, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

Base = declarative_base()


class SyncStatus(Enum):
    """Synchronization status"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CONFLICTED = "conflicted"


class OperationType(Enum):
    """CRUD operation types"""
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    BATCH = "batch"


class ConflictResolutionStrategy(Enum):
    """Conflict resolution strategies"""
    LAST_WRITE_WINS = "last_write_wins"
    FIRST_WRITE_WINS = "first_write_wins"
    MERGE = "merge"
    MANUAL = "manual"
    SERVER_WINS = "server_wins"
    CLIENT_WINS = "client_wins"


class SyncOperation(Base):
    """Represents a sync operation"""
    __tablename__ = 'sync_operations'
    
    id = Column(String, primary_key=True)
    user_id = Column(String, nullable=False, index=True)
    device_id = Column(String, nullable=False, index=True)
    entity_type = Column(String, nullable=False)
    entity_id = Column(String, nullable=False)
    operation_type = Column(String, nullable=False)
    data = Column(JSON)
    binary_data = Column(LargeBinary, nullable=True)
    version = Column(Integer, default=1)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    status = Column(String, default=SyncStatus.PENDING.value)
    retry_count = Column(Integer, default=0)
    error_message = Column(String, nullable=True)
    hash_value = Column(String, index=True)


class SyncState(Base):
    """Tracks sync state per device"""
    __tablename__ = 'sync_states'
    
    id = Column(String, primary_key=True)
    user_id = Column(String, nullable=False, index=True)
    device_id = Column(String, nullable=False, unique=True)
    last_sync_timestamp = Column(DateTime)
    last_sync_version = Column(Integer, default=0)
    pending_operations_count = Column(Integer, default=0)
    failed_operations_count = Column(Integer, default=0)
    total_synced_bytes = Column(Float, default=0.0)
    is_online = Column(Boolean, default=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ConflictRecord(Base):
    """Records conflicts for manual resolution"""
    __tablename__ = 'conflict_records'
    
    id = Column(String, primary_key=True)
    entity_type = Column(String, nullable=False)
    entity_id = Column(String, nullable=False)
    client_version = Column(JSON)
    server_version = Column(JSON)
    client_timestamp = Column(DateTime)
    server_timestamp = Column(DateTime)
    resolution_strategy = Column(String)
    resolved = Column(Boolean, default=False)
    resolved_version = Column(JSON, nullable=True)
    resolved_at = Column(DateTime, nullable=True)
    resolved_by = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class OperationalTransform:
    """Operational Transformation for concurrent editing"""
    
    @staticmethod
    def transform_operation(op1: Dict[str, Any], op2: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """
        Transform two concurrent operations so they can be applied in any order
        
        Args:
            op1: First operation
            op2: Second operation
        
        Returns:
            Tuple of transformed operations (op1', op2')
        """
        op1_type = op1.get("type")
        op2_type = op2.get("type")
        
        # Text operations
        if op1_type == "insert" and op2_type == "insert":
            return OperationalTransform._transform_insert_insert(op1, op2)
        elif op1_type == "insert" and op2_type == "delete":
            return OperationalTransform._transform_insert_delete(op1, op2)
        elif op1_type == "delete" and op2_type == "insert":
            return OperationalTransform._transform_delete_insert(op1, op2)
        elif op1_type == "delete" and op2_type == "delete":
            return OperationalTransform._transform_delete_delete(op1, op2)
        
        # Default: no transformation needed
        return op1, op2
    
    @staticmethod
    def _transform_insert_insert(op1: Dict[str, Any], op2: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """Transform two concurrent insert operations"""
        pos1 = op1["position"]
        pos2 = op2["position"]
        
        if pos1 < pos2:
            # op1 is before op2, adjust op2's position
            op2_prime = op2.copy()
            op2_prime["position"] = pos2 + len(op1["text"])
            return op1, op2_prime
        elif pos1 > pos2:
            # op2 is before op1, adjust op1's position
            op1_prime = op1.copy()
            op1_prime["position"] = pos1 + len(op2["text"])
            return op1_prime, op2
        else:
            # Same position, use tie-breaker (e.g., operation ID)
            if op1.get("id", "") < op2.get("id", ""):
                op2_prime = op2.copy()
                op2_prime["position"] = pos2 + len(op1["text"])
                return op1, op2_prime
            else:
                op1_prime = op1.copy()
                op1_prime["position"] = pos1 + len(op2["text"])
                return op1_prime, op2
    
    @staticmethod
    def _transform_insert_delete(op1: Dict[str, Any], op2: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """Transform insert and delete operations"""
        insert_pos = op1["position"]
        delete_pos = op2["position"]
        delete_len = op2["length"]
        
        if insert_pos <= delete_pos:
            # Insert is before delete, adjust delete position
            op2_prime = op2.copy()
            op2_prime["position"] = delete_pos + len(op1["text"])
            return op1, op2_prime
        elif insert_pos > delete_pos + delete_len:
            # Insert is after delete, adjust insert position
            op1_prime = op1.copy()
            op1_prime["position"] = insert_pos - delete_len
            return op1_prime, op2
        else:
            # Insert is within delete range, adjust both
            op1_prime = op1.copy()
            op1_prime["position"] = delete_pos
            op2_prime = op2.copy()
            op2_prime["length"] = delete_len + len(op1["text"])
            return op1_prime, op2_prime
    
    @staticmethod
    def _transform_delete_insert(op1: Dict[str, Any], op2: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """Transform delete and insert operations (inverse of insert-delete)"""
        op2_prime, op1_prime = OperationalTransform._transform_insert_delete(op2, op1)
        return op1_prime, op2_prime
    
    @staticmethod
    def _transform_delete_delete(op1: Dict[str, Any], op2: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """Transform two concurrent delete operations"""
        pos1 = op1["position"]
        len1 = op1["length"]
        pos2 = op2["position"]
        len2 = op2["length"]
        
        if pos1 + len1 <= pos2:
            # op1 is completely before op2
            op2_prime = op2.copy()
            op2_prime["position"] = pos2 - len1
            return op1, op2_prime
        elif pos2 + len2 <= pos1:
            # op2 is completely before op1
            op1_prime = op1.copy()
            op1_prime["position"] = pos1 - len2
            return op1_prime, op2
        else:
            # Overlapping deletes
            overlap_start = max(pos1, pos2)
            overlap_end = min(pos1 + len1, pos2 + len2)
            overlap_len = overlap_end - overlap_start
            
            op1_prime = op1.copy()
            op1_prime["length"] = len1 - overlap_len
            
            op2_prime = op2.copy()
            op2_prime["length"] = len2 - overlap_len
            
            if pos1 <= pos2:
                op2_prime["position"] = pos1 + op1_prime["length"]
            else:
                op1_prime["position"] = pos2 + op2_prime["length"]
            
            return op1_prime, op2_prime


class DeltaSyncEngine:
    """Implements delta synchronization for efficient bandwidth usage"""
    
    @staticmethod
    def calculate_delta(old_version: Dict[str, Any], new_version: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate delta between two versions
        
        Returns:
            Delta object containing only changes
        """
        delta = {
            "type": "delta",
            "added": {},
            "modified": {},
            "removed": []
        }
        
        # Find added and modified fields
        for key, new_value in new_version.items():
            if key not in old_version:
                delta["added"][key] = new_value
            elif old_version[key] != new_value:
                delta["modified"][key] = {
                    "old": old_version[key],
                    "new": new_value
                }
        
        # Find removed fields
        for key in old_version.keys():
            if key not in new_version:
                delta["removed"].append(key)
        
        return delta
    
    @staticmethod
    def apply_delta(base_version: Dict[str, Any], delta: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply delta to base version
        
        Returns:
            New version with delta applied
        """
        result = base_version.copy()
        
        # Apply additions
        for key, value in delta.get("added", {}).items():
            result[key] = value
        
        # Apply modifications
        for key, change in delta.get("modified", {}).items():
            result[key] = change["new"]
        
        # Apply removals
        for key in delta.get("removed", []):
            if key in result:
                del result[key]
        
        return result
    
    @staticmethod
    def calculate_binary_delta(old_data: bytes, new_data: bytes) -> bytes:
        """
        Calculate binary delta using simple diff
        (In production, use bsdiff or similar)
        """
        # Simplified binary delta (in production, use proper binary diff)
        if old_data == new_data:
            return b""
        
        # For now, return new data (in production, implement proper binary diff)
        return new_data
    
    @staticmethod
    def apply_binary_delta(base_data: bytes, delta: bytes) -> bytes:
        """Apply binary delta to base data"""
        # Simplified (in production, use bspatch)
        if not delta:
            return base_data
        return delta


class ConflictResolver:
    """Resolves sync conflicts using various strategies"""
    
    def __init__(self, strategy: ConflictResolutionStrategy = ConflictResolutionStrategy.LAST_WRITE_WINS):
        self.strategy = strategy
    
    def resolve_conflict(
        self,
        client_version: Dict[str, Any],
        server_version: Dict[str, Any],
        client_timestamp: datetime,
        server_timestamp: datetime
    ) -> Tuple[Dict[str, Any], bool]:
        """
        Resolve conflict between client and server versions
        
        Returns:
            Tuple of (resolved_version, needs_manual_resolution)
        """
        if self.strategy == ConflictResolutionStrategy.LAST_WRITE_WINS:
            return self._last_write_wins(client_version, server_version, client_timestamp, server_timestamp)
        
        elif self.strategy == ConflictResolutionStrategy.FIRST_WRITE_WINS:
            return self._first_write_wins(client_version, server_version, client_timestamp, server_timestamp)
        
        elif self.strategy == ConflictResolutionStrategy.SERVER_WINS:
            return server_version, False
        
        elif self.strategy == ConflictResolutionStrategy.CLIENT_WINS:
            return client_version, False
        
        elif self.strategy == ConflictResolutionStrategy.MERGE:
            return self._merge_versions(client_version, server_version)
        
        elif self.strategy == ConflictResolutionStrategy.MANUAL:
            return {}, True
        
        else:
            return server_version, False
    
    def _last_write_wins(
        self,
        client_version: Dict[str, Any],
        server_version: Dict[str, Any],
        client_timestamp: datetime,
        server_timestamp: datetime
    ) -> Tuple[Dict[str, Any], bool]:
        """Last write wins strategy"""
        if client_timestamp > server_timestamp:
            return client_version, False
        else:
            return server_version, False
    
    def _first_write_wins(
        self,
        client_version: Dict[str, Any],
        server_version: Dict[str, Any],
        client_timestamp: datetime,
        server_timestamp: datetime
    ) -> Tuple[Dict[str, Any], bool]:
        """First write wins strategy"""
        if client_timestamp < server_timestamp:
            return client_version, False
        else:
            return server_version, False
    
    def _merge_versions(
        self,
        client_version: Dict[str, Any],
        server_version: Dict[str, Any]
    ) -> Tuple[Dict[str, Any], bool]:
        """Attempt to merge versions automatically"""
        merged = server_version.copy()
        conflicts = []
        
        for key, client_value in client_version.items():
            if key not in server_version:
                # New field in client, add it
                merged[key] = client_value
            elif server_version[key] != client_value:
                # Conflicting values
                if self._can_auto_merge(server_version[key], client_value):
                    merged[key] = self._auto_merge_values(server_version[key], client_value)
                else:
                    conflicts.append(key)
        
        if conflicts:
            # Cannot auto-merge, needs manual resolution
            return merged, True
        
        return merged, False
    
    def _can_auto_merge(self, server_value: Any, client_value: Any) -> bool:
        """Check if values can be automatically merged"""
        # Can merge if both are lists
        if isinstance(server_value, list) and isinstance(client_value, list):
            return True
        
        # Can merge if both are dicts
        if isinstance(server_value, dict) and isinstance(client_value, dict):
            return True
        
        # Can merge if both are sets
        if isinstance(server_value, set) and isinstance(client_value, set):
            return True
        
        return False
    
    def _auto_merge_values(self, server_value: Any, client_value: Any) -> Any:
        """Automatically merge compatible values"""
        if isinstance(server_value, list) and isinstance(client_value, list):
            # Merge lists (union)
            return list(set(server_value + client_value))
        
        elif isinstance(server_value, dict) and isinstance(client_value, dict):
            # Merge dicts (client overwrites server for conflicts)
            merged = server_value.copy()
            merged.update(client_value)
            return merged
        
        elif isinstance(server_value, set) and isinstance(client_value, set):
            # Merge sets (union)
            return server_value.union(client_value)
        
        return client_value


class SyncQueue:
    """Manages offline operations queue"""
    
    def __init__(self, db_session: Session):
        self.db = db_session
    
    def enqueue_operation(
        self,
        user_id: str,
        device_id: str,
        entity_type: str,
        entity_id: str,
        operation_type: OperationType,
        data: Dict[str, Any],
        binary_data: Optional[bytes] = None
    ) -> str:
        """Add operation to sync queue"""
        
        operation_id = str(uuid.uuid4())
        
        # Calculate hash for deduplication
        hash_input = f"{entity_type}:{entity_id}:{operation_type.value}:{json.dumps(data, sort_keys=True)}"
        hash_value = hashlib.sha256(hash_input.encode()).hexdigest()
        
        # Check for duplicate
        existing = self.db.query(SyncOperation).filter(
            SyncOperation.user_id == user_id,
            SyncOperation.device_id == device_id,
            SyncOperation.hash_value == hash_value,
            SyncOperation.status == SyncStatus.PENDING.value
        ).first()
        
        if existing:
            logger.info(f"Duplicate operation detected, skipping: {hash_value}")
            return existing.id
        
        operation = SyncOperation(
            id=operation_id,
            user_id=user_id,
            device_id=device_id,
            entity_type=entity_type,
            entity_id=entity_id,
            operation_type=operation_type.value,
            data=data,
            binary_data=binary_data,
            hash_value=hash_value
        )
        
        self.db.add(operation)
        self.db.commit()
        
        # Update sync state
        self._update_sync_state(user_id, device_id)
        
        logger.info(f"Enqueued operation {operation_id} for {entity_type}:{entity_id}")
        return operation_id
    
    def get_pending_operations(
        self,
        user_id: str,
        device_id: str,
        limit: int = 100
    ) -> List[SyncOperation]:
        """Get pending operations for device"""
        
        operations = self.db.query(SyncOperation).filter(
            SyncOperation.user_id == user_id,
            SyncOperation.device_id == device_id,
            SyncOperation.status == SyncStatus.PENDING.value
        ).order_by(
            SyncOperation.timestamp.asc()
        ).limit(limit).all()
        
        return operations
    
    def mark_operation_completed(self, operation_id: str) -> bool:
        """Mark operation as completed"""
        
        operation = self.db.query(SyncOperation).filter(
            SyncOperation.id == operation_id
        ).first()
        
        if not operation:
            return False
        
        operation.status = SyncStatus.COMPLETED.value
        self.db.commit()
        
        # Update sync state
        self._update_sync_state(operation.user_id, operation.device_id)
        
        return True
    
    def mark_operation_failed(self, operation_id: str, error_message: str) -> bool:
        """Mark operation as failed"""
        
        operation = self.db.query(SyncOperation).filter(
            SyncOperation.id == operation_id
        ).first()
        
        if not operation:
            return False
        
        operation.status = SyncStatus.FAILED.value
        operation.error_message = error_message
        operation.retry_count += 1
        self.db.commit()
        
        # Update sync state
        self._update_sync_state(operation.user_id, operation.device_id)
        
        return True
    
    def _update_sync_state(self, user_id: str, device_id: str) -> None:
        """Update sync state statistics"""
        
        # Get counts
        pending_count = self.db.query(SyncOperation).filter(
            SyncOperation.user_id == user_id,
            SyncOperation.device_id == device_id,
            SyncOperation.status == SyncStatus.PENDING.value
        ).count()
        
        failed_count = self.db.query(SyncOperation).filter(
            SyncOperation.user_id == user_id,
            SyncOperation.device_id == device_id,
            SyncOperation.status == SyncStatus.FAILED.value
        ).count()
        
        # Update state
        state = self.db.query(SyncState).filter(
            SyncState.device_id == device_id
        ).first()
        
        if state:
            state.pending_operations_count = pending_count
            state.failed_operations_count = failed_count
            state.updated_at = datetime.utcnow()
        else:
            state = SyncState(
                id=str(uuid.uuid4()),
                user_id=user_id,
                device_id=device_id,
                pending_operations_count=pending_count,
                failed_operations_count=failed_count
            )
            self.db.add(state)
        
        self.db.commit()


class BackgroundSyncManager:
    """Manages background synchronization"""
    
    def __init__(
        self,
        db_session: Session,
        sync_queue: SyncQueue,
        conflict_resolver: ConflictResolver
    ):
        self.db = db_session
        self.sync_queue = sync_queue
        self.conflict_resolver = conflict_resolver
        self.is_syncing: Dict[str, bool] = {}
    
    async def start_sync(
        self,
        user_id: str,
        device_id: str,
        sync_callback: Optional[Callable] = None
    ) -> Dict[str, Any]:
        """Start background sync for device"""
        
        # Check if already syncing
        sync_key = f"{user_id}:{device_id}"
        if self.is_syncing.get(sync_key, False):
            return {"status": "already_syncing"}
        
        self.is_syncing[sync_key] = True
        
        try:
            # Get pending operations
            operations = self.sync_queue.get_pending_operations(user_id, device_id)
            
            logger.info(f"Starting sync for {device_id}: {len(operations)} operations")
            
            results = {
                "total": len(operations),
                "succeeded": 0,
                "failed": 0,
                "conflicted": 0
            }
            
            # Process each operation
            for operation in operations:
                try:
                    # Mark as in progress
                    operation.status = SyncStatus.IN_PROGRESS.value
                    self.db.commit()
                    
                    # Apply operation to server
                    success, conflict = await self._apply_operation(operation)
                    
                    if success:
                        if conflict:
                            results["conflicted"] += 1
                        else:
                            results["succeeded"] += 1
                            self.sync_queue.mark_operation_completed(operation.id)
                    else:
                        results["failed"] += 1
                        self.sync_queue.mark_operation_failed(operation.id, "Application failed")
                    
                    # Call progress callback
                    if sync_callback:
                        progress = (results["succeeded"] + results["failed"] + results["conflicted"]) / results["total"]
                        sync_callback(progress, operation)
                    
                except Exception as e:
                    logger.error(f"Failed to sync operation {operation.id}: {e}")
                    results["failed"] += 1
                    self.sync_queue.mark_operation_failed(operation.id, str(e))
            
            # Update sync state
            state = self.db.query(SyncState).filter(
                SyncState.device_id == device_id
            ).first()
            
            if state:
                state.last_sync_timestamp = datetime.utcnow()
                self.db.commit()
            
            logger.info(f"Sync completed for {device_id}: {results}")
            
            return results
            
        finally:
            self.is_syncing[sync_key] = False
    
    async def _apply_operation(self, operation: SyncOperation) -> Tuple[bool, bool]:
        """
        Apply operation to server
        
        Returns:
            Tuple of (success, is_conflict)
        """
        try:
            # Get current server version
            server_version = self._get_server_version(operation.entity_type, operation.entity_id)
            
            if operation.operation_type == OperationType.CREATE.value:
                # Create new entity
                if server_version:
                    # Entity already exists, conflict
                    return await self._handle_conflict(operation, server_version)
                else:
                    # Create entity
                    self._create_entity(operation.entity_type, operation.entity_id, operation.data)
                    return True, False
            
            elif operation.operation_type == OperationType.UPDATE.value:
                # Update entity
                if not server_version:
                    # Entity doesn't exist, cannot update
                    return False, False
                
                # Check for conflict
                if self._has_conflict(operation, server_version):
                    return await self._handle_conflict(operation, server_version)
                else:
                    # Apply update
                    self._update_entity(operation.entity_type, operation.entity_id, operation.data)
                    return True, False
            
            elif operation.operation_type == OperationType.DELETE.value:
                # Delete entity
                if not server_version:
                    # Entity already deleted, no-op
                    return True, False
                
                self._delete_entity(operation.entity_type, operation.entity_id)
                return True, False
            
            else:
                logger.warning(f"Unknown operation type: {operation.operation_type}")
                return False, False
            
        except Exception as e:
            logger.error(f"Failed to apply operation: {e}")
            return False, False
    
    async def _handle_conflict(
        self,
        operation: SyncOperation,
        server_version: Dict[str, Any]
    ) -> Tuple[bool, bool]:
        """Handle conflict between client and server"""
        
        client_version = operation.data
        client_timestamp = operation.timestamp
        server_timestamp = server_version.get("updated_at", datetime.utcnow())
        
        # Resolve conflict
        resolved_version, needs_manual = self.conflict_resolver.resolve_conflict(
            client_version,
            server_version,
            client_timestamp,
            server_timestamp
        )
        
        if needs_manual:
            # Record conflict for manual resolution
            conflict_id = str(uuid.uuid4())
            conflict = ConflictRecord(
                id=conflict_id,
                entity_type=operation.entity_type,
                entity_id=operation.entity_id,
                client_version=client_version,
                server_version=server_version,
                client_timestamp=client_timestamp,
                server_timestamp=server_timestamp,
                resolution_strategy=self.conflict_resolver.strategy.value
            )
            self.db.add(conflict)
            
            operation.status = SyncStatus.CONFLICTED.value
            self.db.commit()
            
            logger.warning(f"Manual conflict resolution needed for {operation.entity_id}")
            return True, True
        else:
            # Apply resolved version
            self._update_entity(operation.entity_type, operation.entity_id, resolved_version)
            return True, True
    
    def _has_conflict(self, operation: SyncOperation, server_version: Dict[str, Any]) -> bool:
        """Check if operation conflicts with server version"""
        # Compare versions
        client_version = operation.version
        server_version_num = server_version.get("version", 0)
        
        return client_version < server_version_num
    
    def _get_server_version(self, entity_type: str, entity_id: str) -> Optional[Dict[str, Any]]:
        """Get current server version of entity"""
        # In real implementation, query actual database
        # For now, return mock data
        return None
    
    def _create_entity(self, entity_type: str, entity_id: str, data: Dict[str, Any]) -> None:
        """Create entity on server"""
        # In real implementation, insert into database
        logger.info(f"Created {entity_type}:{entity_id}")
    
    def _update_entity(self, entity_type: str, entity_id: str, data: Dict[str, Any]) -> None:
        """Update entity on server"""
        # In real implementation, update database
        logger.info(f"Updated {entity_type}:{entity_id}")
    
    def _delete_entity(self, entity_type: str, entity_id: str) -> None:
        """Delete entity on server"""
        # In real implementation, delete from database
        logger.info(f"Deleted {entity_type}:{entity_id}")


class IncrementalSyncManager:
    """Manages incremental synchronization"""
    
    def __init__(self, db_session: Session):
        self.db = db_session
    
    def get_changes_since(
        self,
        user_id: str,
        since_timestamp: datetime,
        entity_types: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """Get all changes since timestamp"""
        
        query = self.db.query(SyncOperation).filter(
            SyncOperation.user_id == user_id,
            SyncOperation.timestamp > since_timestamp,
            SyncOperation.status == SyncStatus.COMPLETED.value
        )
        
        if entity_types:
            query = query.filter(SyncOperation.entity_type.in_(entity_types))
        
        operations = query.order_by(SyncOperation.timestamp.asc()).all()
        
        changes = []
        for op in operations:
            changes.append({
                "id": op.id,
                "entity_type": op.entity_type,
                "entity_id": op.entity_id,
                "operation_type": op.operation_type,
                "data": op.data,
                "timestamp": op.timestamp.isoformat(),
                "version": op.version
            })
        
        return changes
    
    def apply_incremental_changes(
        self,
        device_id: str,
        changes: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Apply incremental changes to device"""
        
        results = {
            "applied": 0,
            "skipped": 0,
            "failed": 0
        }
        
        for change in changes:
            try:
                # Check if change already applied
                existing = self.db.query(SyncOperation).filter(
                    SyncOperation.device_id == device_id,
                    SyncOperation.entity_id == change["entity_id"],
                    SyncOperation.timestamp >= datetime.fromisoformat(change["timestamp"])
                ).first()
                
                if existing:
                    results["skipped"] += 1
                    continue
                
                # Apply change
                # (In real implementation, update local database)
                results["applied"] += 1
                
            except Exception as e:
                logger.error(f"Failed to apply change: {e}")
                results["failed"] += 1
        
        return results


class MobileOfflineSyncManager:
    """Main coordinator for mobile offline sync"""
    
    def __init__(self, database_url: str):
        self.engine = create_engine(database_url)
        Base.metadata.create_all(self.engine)
        
        Session_maker = sessionmaker(bind=self.engine)
        self.session = Session_maker()
        
        self.sync_queue = SyncQueue(self.session)
        self.conflict_resolver = ConflictResolver()
        self.background_sync = BackgroundSyncManager(
            self.session,
            self.sync_queue,
            self.conflict_resolver
        )
        self.incremental_sync = IncrementalSyncManager(self.session)
        self.delta_engine = DeltaSyncEngine()
        self.ot = OperationalTransform()
    
    def save_offline_change(
        self,
        user_id: str,
        device_id: str,
        entity_type: str,
        entity_id: str,
        operation_type: OperationType,
        data: Dict[str, Any]
    ) -> str:
        """Save change made while offline"""
        
        return self.sync_queue.enqueue_operation(
            user_id,
            device_id,
            entity_type,
            entity_id,
            operation_type,
            data
        )
    
    async def sync_now(
        self,
        user_id: str,
        device_id: str,
        progress_callback: Optional[Callable] = None
    ) -> Dict[str, Any]:
        """Trigger immediate sync"""
        
        return await self.background_sync.start_sync(user_id, device_id, progress_callback)
    
    def get_sync_status(self, device_id: str) -> Dict[str, Any]:
        """Get current sync status"""
        
        state = self.session.query(SyncState).filter(
            SyncState.device_id == device_id
        ).first()
        
        if not state:
            return {
                "pending_operations": 0,
                "failed_operations": 0,
                "last_sync": None,
                "is_online": False
            }
        
        return {
            "pending_operations": state.pending_operations_count,
            "failed_operations": state.failed_operations_count,
            "last_sync": state.last_sync_timestamp.isoformat() if state.last_sync_timestamp else None,
            "is_online": state.is_online
        }


# Example usage
async def example_usage():
    """Demonstrate offline sync system"""
    
    manager = MobileOfflineSyncManager("sqlite:///offline_sync.db")
    
    user_id = "user-123"
    device_id = "device-456"
    
    # Save offline changes
    manager.save_offline_change(
        user_id=user_id,
        device_id=device_id,
        entity_type="farm",
        entity_id="farm-789",
        operation_type=OperationType.UPDATE,
        data={"name": "Green Valley Farm", "size_hectares": 150}
    )
    
    manager.save_offline_change(
        user_id=user_id,
        device_id=device_id,
        entity_type="sensor",
        entity_id="sensor-101",
        operation_type=OperationType.CREATE,
        data={"type": "soil_moisture", "location": {"lat": 42.0, "lng": -93.0}}
    )
    
    # Get sync status
    status = manager.get_sync_status(device_id)
    print(f"Sync status: {status}")
    
    # Trigger sync
    def progress_callback(progress, operation):
        print(f"Sync progress: {progress*100:.1f}%")
    
    results = await manager.sync_now(user_id, device_id, progress_callback)
    print(f"Sync results: {results}")


if __name__ == "__main__":
    asyncio.run(example_usage())
