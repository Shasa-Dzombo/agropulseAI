# ========================================================================================
# ENTERPRISE DATABASE MANAGER
# Advanced database orchestration with connection pooling, sharding, replication,
# query optimization, migration management, backup/restore, and performance monitoring
# ========================================================================================

import logging
import asyncio
import aiosqlite
import sqlite3
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple, Union, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import json
import hashlib
import uuid
import traceback
import threading
from collections import defaultdict, deque
import time
import re
import copy

logger = logging.getLogger(__name__)


# ========================= ENUMERATIONS =========================

class DatabaseType(Enum):
    """Database backend types"""
    SQLITE = "sqlite"
    POSTGRESQL = "postgresql"
    MYSQL = "mysql"

class TransactionIsolation(Enum):
    """Transaction isolation levels"""
    READ_UNCOMMITTED = "READ UNCOMMITTED"
    READ_COMMITTED = "READ COMMITTED"
    REPEATABLE_READ = "REPEATABLE READ"
    SERIALIZABLE = "SERIALIZABLE"

class QueryType(Enum):
    """Query operation types"""
    SELECT = "select"
    INSERT = "insert"
    UPDATE = "update"
    DELETE = "delete"
    DDL = "ddl"

class IndexType(Enum):
    """Database index types"""
    BTREE = "btree"
    HASH = "hash"
    FULLTEXT = "fulltext"

class ReplicationMode(Enum):
    """Database replication modes"""
    MASTER = "master"
    SLAVE = "slave"
    MULTI_MASTER = "multi_master"

class MigrationStatus(Enum):
    """Migration execution status"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"

# ========================= DATA CLASSES =========================

@dataclass
class ConnectionConfig:
    """Database connection configuration"""
    host: str = "localhost"
    port: int = 5432
    database: str = "nvr"
    username: Optional[str] = None
    password: Optional[str] = None
    pool_size: int = 10
    max_overflow: int = 20
    timeout: int = 30
    ssl_enabled: bool = False
    
@dataclass
class QueryMetrics:
    """Query performance metrics"""
    query_id: str
    query_type: QueryType
    sql: str
    execution_time: float
    rows_affected: int
    timestamp: str
    success: bool
    error: Optional[str] = None
    
@dataclass
class DatabaseSchema:
    """Database schema definition"""
    tables: Dict[str, 'TableSchema'] = field(default_factory=dict)
    indexes: List['IndexSchema'] = field(default_factory=list)
    version: str = "1.0.0"
    
@dataclass
class TableSchema:
    """Table schema definition"""
    name: str
    columns: List['ColumnSchema']
    primary_key: List[str]
    foreign_keys: List['ForeignKeySchema'] = field(default_factory=list)
    indexes: List[str] = field(default_factory=list)
    
@dataclass
class ColumnSchema:
    """Column schema definition"""
    name: str
    data_type: str
    nullable: bool = True
    default: Optional[Any] = None
    unique: bool = False
    
@dataclass
class ForeignKeySchema:
    """Foreign key constraint"""
    column: str
    referenced_table: str
    referenced_column: str
    on_delete: str = "CASCADE"
    
@dataclass
class IndexSchema:
    """Index definition"""
    name: str
    table: str
    columns: List[str]
    index_type: IndexType = IndexType.BTREE
    unique: bool = False
    
@dataclass
class Migration:
    """Database migration"""
    version: str
    name: str
    up_sql: str
    down_sql: str
    status: MigrationStatus = MigrationStatus.PENDING
    executed_at: Optional[str] = None
    
@dataclass
class BackupMetadata:
    """Database backup metadata"""
    backup_id: str
    timestamp: str
    size_bytes: int
    compression: str
    file_path: str
    checksum: str

# ========================= ASYNC CONNECTION POOL =========================

class AsyncConnectionPool:
    """Asynchronous database connection pooling for aiosqlite"""

    def __init__(self, db_path: str, pool_size: int = 10, max_overflow: int = 20, timeout: float = 10.0):
        self.db_path = db_path
        self.pool_size = pool_size
        self.max_overflow = max_overflow
        self.timeout = timeout
        self._pool: asyncio.Queue = asyncio.Queue(maxsize=pool_size + max_overflow)
        self._lock = asyncio.Lock()
        self._connection_count = 0

        logger.info(f"AsyncConnectionPool initialized for '{db_path}': size={pool_size}, max_overflow={max_overflow}")

    async def _create_connection(self) -> aiosqlite.Connection:
        """Create a new database connection."""
        conn = await aiosqlite.connect(self.db_path)
        await conn.execute("PRAGMA journal_mode=WAL")
        await conn.execute("PRAGMA synchronous=NORMAL")
        await conn.execute("PRAGMA cache_size=-64000")  # 64MB cache
        conn.row_factory = aiosqlite.Row
        self._connection_count += 1
        return conn

    async def acquire(self) -> aiosqlite.Connection:
        """Acquire a connection from the pool."""
        async with self._lock:
            if not self._pool.empty():
                return await self._pool.get()
            if self._connection_count < self.pool_size + self.max_overflow:
                return await self._create_connection()

        try:
            return await asyncio.wait_for(self._pool.get(), timeout=self.timeout)
        except asyncio.TimeoutError:
            raise ConnectionError("Connection pool timeout: No available connections.")

    async def release(self, conn: aiosqlite.Connection):
        """Release a connection back to the pool."""
        if self._pool.full():
            await conn.close()
            self._connection_count -= 1
        else:
            await self._pool.put(conn)

    async def close_all(self):
        """Close all connections in the pool."""
        async with self._lock:
            while not self._pool.empty():
                conn = await self._pool.get()
                await conn.close()
                self._connection_count -= 1
        logger.info("All async connections closed.")

    async def __aenter__(self):
        self._conn = await self.acquire()
        return self._conn

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.release(self._conn)

# ========================= QUERY BUILDER =========================

class QueryBuilder:
    """SQL query builder with fluent interface"""
    
    def __init__(self):
        self.reset()
        
    def select(self, *columns: str) -> 'QueryBuilder':
        self._select_columns.extend(columns)
        return self
        
    def from_table(self, table: str) -> 'QueryBuilder':
        self._from_table = table
        return self
        
    def join(self, table: str, condition: str, join_type: str = "INNER") -> 'QueryBuilder':
        self._joins.append((join_type, table, condition))
        return self
        
    def where(self, condition: str, *params) -> 'QueryBuilder':
        self._where_conditions.append(condition)
        self._parameters.extend(params)
        return self
        
    def group_by(self, *columns: str) -> 'QueryBuilder':
        self._group_by.extend(columns)
        return self
        
    def having(self, condition: str, *params) -> 'QueryBuilder':
        self._having.append(condition)
        self._parameters.extend(params)
        return self
        
    def order_by(self, column: str, direction: str = "ASC") -> 'QueryBuilder':
        self._order_by.append(f"{column} {direction.upper()}")
        return self
        
    def limit(self, limit: int) -> 'QueryBuilder':
        self._limit = limit
        return self
        
    def offset(self, offset: int) -> 'QueryBuilder':
        self._offset = offset
        return self
        
    def build(self) -> Tuple[str, List[Any]]:
        if not self._from_table:
            raise ValueError("FROM table not specified")
        
        cols = ', '.join(self._select_columns) if self._select_columns else "*"
        sql = f"SELECT {cols} FROM {self._from_table}"
        
        for join_type, table, condition in self._joins:
            sql += f" {join_type.upper()} JOIN {table} ON {condition}"
        
        if self._where_conditions:
            sql += f" WHERE {' AND '.join(self._where_conditions)}"
        
        if self._group_by:
            sql += f" GROUP BY {', '.join(self._group_by)}"
        
        if self._having:
            sql += f" HAVING {' AND '.join(self._having)}"
        
        if self._order_by:
            sql += f" ORDER BY {', '.join(self._order_by)}"
        
        if self._limit is not None:
            sql += f" LIMIT ?"
            self._parameters.append(self._limit)
        
        if self._offset is not None:
            sql += f" OFFSET ?"
            self._parameters.append(self._offset)
            
        return sql, self._parameters
        
    def reset(self) -> 'QueryBuilder':
        self._select_columns: List[str] = []
        self._from_table: Optional[str] = None
        self._joins: List[Tuple[str, str, str]] = []
        self._where_conditions: List[str] = []
        self._group_by: List[str] = []
        self._having: List[str] = []
        self._order_by: List[str] = []
        self._limit: Optional[int] = None
        self._offset: Optional[int] = None
        self._parameters: List[Any] = []
        return self

# ========================= DATABASE MANAGER =========================

class DatabaseManager:
    """Main class for all database interactions"""

    def __init__(self, db_path: str, config: Optional[ConnectionConfig] = None):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.config = config or ConnectionConfig()
        
        self.pool = AsyncConnectionPool(
            db_path=str(self.db_path),
            pool_size=self.config.pool_size,
            max_overflow=self.config.max_overflow
        )
        
        self.query_metrics: deque = deque(maxlen=1000)
        self.is_running = False
        self._maintenance_task: Optional[asyncio.Task] = None

        logger.info(f"DatabaseManager initialized for database: {self.db_path}")

    async def start(self):
        """Initialize database and start maintenance tasks."""
        if self.is_running:
            return
        await self.init_db()
        self.is_running = True
        self._maintenance_task = asyncio.create_task(self._run_maintenance())
        logger.info("DatabaseManager started.")

    async def stop(self):
        """Stop maintenance tasks and close connection pool."""
        if not self.is_running:
            return
        self.is_running = False
        if self._maintenance_task:
            self._maintenance_task.cancel()
            try:
                await self._maintenance_task
            except asyncio.CancelledError:
                pass
        await self.pool.close_all()
        logger.info("DatabaseManager stopped.")

    async def init_db(self):
        """Create database tables if they don't exist."""
        async with self.pool.acquire() as conn:
            # Main events table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS events (
                    event_id TEXT PRIMARY KEY,
                    camera_id TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    details TEXT,
                    thumbnail_path TEXT
                )
            """)
            # Detections associated with an event
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS detections (
                    detection_id TEXT PRIMARY KEY,
                    event_id TEXT NOT NULL,
                    object_type TEXT NOT NULL,
                    confidence REAL,
                    box_x INTEGER, box_y INTEGER, box_w INTEGER, box_h INTEGER,
                    FOREIGN KEY(event_id) REFERENCES events(event_id) ON DELETE CASCADE
                )
            """)
            # Incidents created from events
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS incidents (
                    incident_id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    description TEXT,
                    status TEXT NOT NULL,
                    priority TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT
                )
            """)
            # Link table for events and incidents
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS incident_events (
                    incident_id TEXT NOT NULL,
                    event_id TEXT NOT NULL,
                    PRIMARY KEY (incident_id, event_id),
                    FOREIGN KEY(incident_id) REFERENCES incidents(incident_id) ON DELETE CASCADE,
                    FOREIGN KEY(event_id) REFERENCES events(event_id) ON DELETE CASCADE
                )
            """)
            await conn.commit()
        logger.info("Database schema initialized.")

    async def _run_maintenance(self):
        """Periodically run maintenance tasks."""
        while self.is_running:
            try:
                await asyncio.sleep(3600)  # Run every hour
                logger.info("Running database maintenance...")
                await self.cleanup_old_events(days=30)
                await self.vacuum()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error during database maintenance: {e}")

    async def execute_query(self, sql: str, params: Optional[Tuple] = None) -> List[aiosqlite.Row]:
        """Execute a SELECT query."""
        start_time = time.monotonic()
        query_id = str(uuid.uuid4())
        try:
            async with self.pool.acquire() as conn:
                cursor = await conn.execute(sql, params or ())
                rows = await cursor.fetchall()
                execution_time = time.monotonic() - start_time
                self._record_query_metrics(query_id, QueryType.SELECT, sql, execution_time, len(rows), True)
                return rows
        except Exception as e:
            execution_time = time.monotonic() - start_time
            self._record_query_metrics(query_id, QueryType.SELECT, sql, execution_time, 0, False, str(e))
            logger.error(f"Query failed: {sql} | {params} | {e}")
            raise

    async def execute_update(self, sql: str, params: Optional[Tuple] = None) -> int:
        """Execute an INSERT, UPDATE, or DELETE query."""
        start_time = time.monotonic()
        query_id = str(uuid.uuid4())
        query_type = self._detect_query_type(sql)
        try:
            async with self.pool.acquire() as conn:
                cursor = await conn.execute(sql, params or ())
                await conn.commit()
                rows_affected = cursor.rowcount
                execution_time = time.monotonic() - start_time
                self._record_query_metrics(query_id, query_type, sql, execution_time, rows_affected, True)
                return rows_affected
        except Exception as e:
            execution_time = time.monotonic() - start_time
            self._record_query_metrics(query_id, query_type, sql, execution_time, 0, False, str(e))
            logger.error(f"Update query failed: {sql} | {params} | {e}")
            raise

    async def execute_batch(self, sql: str, params_list: List[Tuple]) -> int:
        """Execute a batch INSERT/UPDATE."""
        start_time = time.monotonic()
        query_id = str(uuid.uuid4())
        query_type = self._detect_query_type(sql)
        try:
            async with self.pool.acquire() as conn:
                cursor = await conn.executemany(sql, params_list)
                await conn.commit()
                rows_affected = cursor.rowcount
                execution_time = time.monotonic() - start_time
                self._record_query_metrics(query_id, query_type, sql, execution_time, rows_affected, True)
                return rows_affected
        except Exception as e:
            execution_time = time.monotonic() - start_time
            self._record_query_metrics(query_id, query_type, sql, execution_time, 0, False, str(e))
            logger.error(f"Batch query failed: {e}")
            raise

    def _detect_query_type(self, sql: str) -> QueryType:
        """Detect query type from SQL."""
        sql_upper = sql.strip().upper()
        if sql_upper.startswith('SELECT'):
            return QueryType.SELECT
        elif sql_upper.startswith('INSERT'):
            return QueryType.INSERT
        elif sql_upper.startswith('UPDATE'):
            return QueryType.UPDATE
        elif sql_upper.startswith('DELETE'):
            return QueryType.DELETE
        else:
            return QueryType.DDL

    def _record_query_metrics(self, query_id: str, query_type: QueryType, sql: str,
                              execution_time: float, rows_affected: int,
                              success: bool, error: Optional[str] = None):
        """Record query performance metrics."""
        metric = QueryMetrics(
            query_id=query_id,
            query_type=query_type,
            sql=sql,
            execution_time=execution_time,
            rows_affected=rows_affected,
            timestamp=datetime.utcnow().isoformat(),
            success=success,
            error=error
        )
        self.query_metrics.append(metric)

    def get_query_metrics(self, last_n: int = 100) -> List[QueryMetrics]:
        """Get the last N query metrics."""
        return list(self.query_metrics)[-last_n:]

    async def cleanup_old_events(self, days: int):
        """Delete events older than a specified number of days."""
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        cutoff_iso = cutoff_date.isoformat()
        
        logger.info(f"Cleaning up events older than {cutoff_iso}")
        
        # Find old event IDs
        rows = await self.execute_query("SELECT event_id FROM events WHERE timestamp < ?", (cutoff_iso,))
        event_ids = [row['event_id'] for row in rows]
        
        if not event_ids:
            logger.info("No old events to clean up.")
            return 0
            
        # SQLite has a limit on variables in a query, so we batch
        deleted_count = 0
        batch_size = 500
        for i in range(0, len(event_ids), batch_size):
            batch_ids = event_ids[i:i+batch_size]
            placeholders = ','.join(['?'] * len(batch_ids))
            
            # Detections are deleted by CASCADE
            deleted = await self.execute_update(
                f"DELETE FROM events WHERE event_id IN ({placeholders})",
                tuple(batch_ids)
            )
            deleted_count += deleted

        logger.info(f"Cleaned up {deleted_count} old events.")
        return deleted_count

    async def vacuum(self):
        """Run VACUUM to rebuild the database and reduce file size."""
        logger.info("Starting database VACUUM...")
        try:
            async with self.pool.acquire() as conn:
                await conn.execute("VACUUM")
                await conn.commit()
            logger.info("Database VACUUM completed successfully.")
        except Exception as e:
            logger.error(f"Database VACUUM failed: {e}")

    async def __aenter__(self):
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.stop()

# ========================= TRANSACTION MANAGER =========================

class TransactionManager:
    """Manage database transactions with savepoints and rollback support"""
    
    def __init__(self, pool: AsyncConnectionPool):
        self.pool = pool
        self._active_transactions: Dict[str, aiosqlite.Connection] = {}
        self._savepoints: Dict[str, List[str]] = defaultdict(list)
        
    async def begin_transaction(self, transaction_id: Optional[str] = None, 
                               isolation_level: Optional[TransactionIsolation] = None) -> str:
        """Start a new transaction"""
        trans_id = transaction_id or str(uuid.uuid4())
        
        if trans_id in self._active_transactions:
            raise ValueError(f"Transaction {trans_id} already active")
        
        conn = await self.pool.acquire()
        
        if isolation_level:
            await conn.execute(f"PRAGMA read_uncommitted = {1 if isolation_level == TransactionIsolation.READ_UNCOMMITTED else 0}")
        
        await conn.execute("BEGIN")
        self._active_transactions[trans_id] = conn
        
        logger.info(f"Transaction {trans_id} started")
        return trans_id
        
    async def commit_transaction(self, transaction_id: str):
        """Commit a transaction"""
        if transaction_id not in self._active_transactions:
            raise ValueError(f"Transaction {transaction_id} not found")
        
        conn = self._active_transactions[transaction_id]
        await conn.commit()
        await self.pool.release(conn)
        
        del self._active_transactions[transaction_id]
        if transaction_id in self._savepoints:
            del self._savepoints[transaction_id]
        
        logger.info(f"Transaction {transaction_id} committed")
        
    async def rollback_transaction(self, transaction_id: str):
        """Rollback a transaction"""
        if transaction_id not in self._active_transactions:
            raise ValueError(f"Transaction {transaction_id} not found")
        
        conn = self._active_transactions[transaction_id]
        await conn.rollback()
        await self.pool.release(conn)
        
        del self._active_transactions[transaction_id]
        if transaction_id in self._savepoints:
            del self._savepoints[transaction_id]
        
        logger.info(f"Transaction {transaction_id} rolled back")
        
    async def create_savepoint(self, transaction_id: str, savepoint_name: Optional[str] = None) -> str:
        """Create a savepoint within a transaction"""
        if transaction_id not in self._active_transactions:
            raise ValueError(f"Transaction {transaction_id} not found")
        
        sp_name = savepoint_name or f"sp_{len(self._savepoints[transaction_id])}"
        conn = self._active_transactions[transaction_id]
        
        await conn.execute(f"SAVEPOINT {sp_name}")
        self._savepoints[transaction_id].append(sp_name)
        
        logger.debug(f"Savepoint {sp_name} created in transaction {transaction_id}")
        return sp_name
        
    async def rollback_to_savepoint(self, transaction_id: str, savepoint_name: str):
        """Rollback to a specific savepoint"""
        if transaction_id not in self._active_transactions:
            raise ValueError(f"Transaction {transaction_id} not found")
        
        if savepoint_name not in self._savepoints[transaction_id]:
            raise ValueError(f"Savepoint {savepoint_name} not found")
        
        conn = self._active_transactions[transaction_id]
        await conn.execute(f"ROLLBACK TO SAVEPOINT {savepoint_name}")
        
        logger.debug(f"Rolled back to savepoint {savepoint_name} in transaction {transaction_id}")
        
    async def execute_in_transaction(self, transaction_id: str, sql: str, params: Optional[Tuple] = None):
        """Execute query within a transaction"""
        if transaction_id not in self._active_transactions:
            raise ValueError(f"Transaction {transaction_id} not found")
        
        conn = self._active_transactions[transaction_id]
        cursor = await conn.execute(sql, params or ())
        return cursor

# ========================= QUERY OPTIMIZER =========================

class QueryOptimizer:
    """Advanced query optimization and caching"""
    
    def __init__(self, cache_size: int = 1000, cache_ttl: int = 300):
        self.query_cache: Dict[str, Dict[str, Any]] = {}
        self.cache_size = cache_size
        self.cache_ttl = cache_ttl
        self.cache_hits = 0
        self.cache_misses = 0
        self._lock = asyncio.Lock()
        
    def optimize_query(self, sql: str) -> str:
        """Optimize SQL query"""
        optimized = sql.strip()
        
        # Normalize whitespace
        optimized = re.sub(r'\s+', ' ', optimized)
        
        # Convert to uppercase for keywords
        keywords = ['SELECT', 'FROM', 'WHERE', 'JOIN', 'LEFT', 'RIGHT', 'INNER', 'OUTER', 
                   'GROUP BY', 'ORDER BY', 'HAVING', 'LIMIT', 'OFFSET']
        
        return optimized
        
    async def get_query_plan(self, conn: aiosqlite.Connection, sql: str) -> List[Dict[str, Any]]:
        """Get query execution plan"""
        try:
            cursor = await conn.execute(f"EXPLAIN QUERY PLAN {sql}")
            rows = await cursor.fetchall()
            
            plan = []
            for row in rows:
                plan.append({
                    'id': row[0],
                    'parent': row[1],
                    'notused': row[2],
                    'detail': row[3]
                })
            
            return plan
        except Exception as e:
            logger.error(f"Failed to get query plan: {e}")
            return []
            
    def calculate_query_hash(self, sql: str, params: Optional[Tuple] = None) -> str:
        """Calculate hash for query caching"""
        cache_key = sql
        if params:
            cache_key += str(params)
        return hashlib.md5(cache_key.encode()).hexdigest()
        
    async def cache_query_result(self, query_hash: str, result: Any):
        """Cache query result"""
        async with self._lock:
            if len(self.query_cache) >= self.cache_size:
                # Remove oldest entry
                oldest_key = min(self.query_cache.keys(), 
                               key=lambda k: self.query_cache[k]['timestamp'])
                del self.query_cache[oldest_key]
            
            self.query_cache[query_hash] = {
                'result': result,
                'timestamp': time.time()
            }
            
    async def get_cached_result(self, query_hash: str) -> Optional[Any]:
        """Get cached query result"""
        async with self._lock:
            cached = self.query_cache.get(query_hash)
            
            if cached:
                age = time.time() - cached['timestamp']
                if age < self.cache_ttl:
                    self.cache_hits += 1
                    return cached['result']
                else:
                    del self.query_cache[query_hash]
            
            self.cache_misses += 1
            return None
            
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        total_requests = self.cache_hits + self.cache_misses
        hit_rate = (self.cache_hits / total_requests * 100) if total_requests > 0 else 0
        
        return {
            'cache_size': len(self.query_cache),
            'max_cache_size': self.cache_size,
            'cache_hits': self.cache_hits,
            'cache_misses': self.cache_misses,
            'hit_rate': f"{hit_rate:.2f}%",
            'cache_ttl': self.cache_ttl
        }

# ========================= MIGRATION MANAGER =========================

class MigrationManager:
    """Database schema migration management"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.migrations: List[Migration] = []
        
    async def init_migration_table(self):
        """Initialize migration tracking table"""
        async with aiosqlite.connect(self.db_path) as conn:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    version TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    status TEXT NOT NULL,
                    executed_at TEXT,
                    execution_time REAL
                )
            """)
            await conn.commit()
            
    def add_migration(self, version: str, name: str, up_sql: str, down_sql: str):
        """Add a migration"""
        migration = Migration(
            version=version,
            name=name,
            up_sql=up_sql,
            down_sql=down_sql
        )
        self.migrations.append(migration)
        logger.info(f"Migration added: {version} - {name}")
        
    async def get_applied_migrations(self) -> List[str]:
        """Get list of applied migration versions"""
        async with aiosqlite.connect(self.db_path) as conn:
            cursor = await conn.execute(
                "SELECT version FROM schema_migrations WHERE status = ? ORDER BY version",
                (MigrationStatus.COMPLETED.value,)
            )
            rows = await cursor.fetchall()
            return [row[0] for row in rows]
            
    async def apply_migration(self, migration: Migration):
        """Apply a single migration"""
        logger.info(f"Applying migration {migration.version}: {migration.name}")
        start_time = time.time()
        
        async with aiosqlite.connect(self.db_path) as conn:
            try:
                # Update status to RUNNING
                await conn.execute(
                    "INSERT OR REPLACE INTO schema_migrations (version, name, status) VALUES (?, ?, ?)",
                    (migration.version, migration.name, MigrationStatus.RUNNING.value)
                )
                await conn.commit()
                
                # Execute migration SQL
                await conn.executescript(migration.up_sql)
                await conn.commit()
                
                execution_time = time.time() - start_time
                
                # Update status to COMPLETED
                await conn.execute(
                    """UPDATE schema_migrations 
                       SET status = ?, executed_at = ?, execution_time = ?
                       WHERE version = ?""",
                    (MigrationStatus.COMPLETED.value, datetime.utcnow().isoformat(), 
                     execution_time, migration.version)
                )
                await conn.commit()
                
                logger.info(f"Migration {migration.version} completed in {execution_time:.2f}s")
                
            except Exception as e:
                # Update status to FAILED
                await conn.execute(
                    "UPDATE schema_migrations SET status = ? WHERE version = ?",
                    (MigrationStatus.FAILED.value, migration.version)
                )
                await conn.commit()
                logger.error(f"Migration {migration.version} failed: {e}")
                raise
                
    async def rollback_migration(self, migration: Migration):
        """Rollback a migration"""
        logger.info(f"Rolling back migration {migration.version}: {migration.name}")
        
        async with aiosqlite.connect(self.db_path) as conn:
            try:
                await conn.executescript(migration.down_sql)
                await conn.commit()
                
                await conn.execute(
                    "UPDATE schema_migrations SET status = ? WHERE version = ?",
                    (MigrationStatus.ROLLED_BACK.value, migration.version)
                )
                await conn.commit()
                
                logger.info(f"Migration {migration.version} rolled back")
                
            except Exception as e:
                logger.error(f"Rollback of migration {migration.version} failed: {e}")
                raise
                
    async def migrate_up(self):
        """Apply all pending migrations"""
        await self.init_migration_table()
        applied = await self.get_applied_migrations()
        
        pending = [m for m in self.migrations if m.version not in applied]
        pending.sort(key=lambda m: m.version)
        
        logger.info(f"Found {len(pending)} pending migrations")
        
        for migration in pending:
            await self.apply_migration(migration)
            
    async def migrate_down(self, steps: int = 1):
        """Rollback migrations"""
        applied = await self.get_applied_migrations()
        applied.sort(reverse=True)
        
        to_rollback = applied[:steps]
        
        for version in to_rollback:
            migration = next((m for m in self.migrations if m.version == version), None)
            if migration:
                await self.rollback_migration(migration)

# ========================= BACKUP MANAGER =========================

class BackupManager:
    """Database backup and restore management"""
    
    def __init__(self, db_path: str, backup_dir: str):
        self.db_path = Path(db_path)
        self.backup_dir = Path(backup_dir)
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        
    def _calculate_checksum(self, file_path: Path) -> str:
        """Calculate SHA256 checksum of file"""
        sha256 = hashlib.sha256()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b''):
                sha256.update(chunk)
        return sha256.hexdigest()
        
    async def create_backup(self, backup_name: Optional[str] = None, 
                           compress: bool = True) -> BackupMetadata:
        """Create database backup"""
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        backup_id = str(uuid.uuid4())
        
        if backup_name:
            filename = f"{backup_name}_{timestamp}.db"
        else:
            filename = f"backup_{timestamp}.db"
            
        backup_path = self.backup_dir / filename
        
        logger.info(f"Creating backup: {backup_path}")
        
        # Use SQLite backup API
        async with aiosqlite.connect(self.db_path) as source:
            async with aiosqlite.connect(backup_path) as dest:
                await source.backup(dest)
                
        size_bytes = backup_path.stat().st_size
        checksum = self._calculate_checksum(backup_path)
        
        # Compress if requested
        compression = "none"
        if compress:
            import gzip
            compressed_path = backup_path.with_suffix('.db.gz')
            with open(backup_path, 'rb') as f_in:
                with gzip.open(compressed_path, 'wb') as f_out:
                    f_out.writelines(f_in)
            backup_path.unlink()
            backup_path = compressed_path
            compression = "gzip"
            size_bytes = backup_path.stat().st_size
            
        metadata = BackupMetadata(
            backup_id=backup_id,
            timestamp=datetime.utcnow().isoformat(),
            size_bytes=size_bytes,
            compression=compression,
            file_path=str(backup_path),
            checksum=checksum
        )
        
        logger.info(f"Backup created: {backup_path} ({size_bytes} bytes)")
        return metadata
        
    async def restore_backup(self, backup_path: str):
        """Restore database from backup"""
        backup_file = Path(backup_path)
        
        if not backup_file.exists():
            raise FileNotFoundError(f"Backup file not found: {backup_path}")
            
        logger.info(f"Restoring from backup: {backup_path}")
        
        # Decompress if needed
        temp_path = backup_file
        if backup_file.suffix == '.gz':
            import gzip
            temp_path = backup_file.with_suffix('')
            with gzip.open(backup_file, 'rb') as f_in:
                with open(temp_path, 'wb') as f_out:
                    f_out.writelines(f_in)
                    
        # Restore database
        async with aiosqlite.connect(temp_path) as source:
            async with aiosqlite.connect(self.db_path) as dest:
                await source.backup(dest)
                
        # Clean up temp file if we decompressed
        if temp_path != backup_file:
            temp_path.unlink()
            
        logger.info(f"Database restored from {backup_path}")
        
    def list_backups(self) -> List[Path]:
        """List all available backups"""
        backups = list(self.backup_dir.glob("*.db"))
        backups.extend(self.backup_dir.glob("*.db.gz"))
        backups.sort(key=lambda p: p.stat().st_mtime, reverse=True)
        return backups
        
    def cleanup_old_backups(self, keep_count: int = 10):
        """Delete old backups, keeping only the most recent"""
        backups = self.list_backups()
        
        if len(backups) <= keep_count:
            logger.info(f"No backups to clean up ({len(backups)} <= {keep_count})")
            return
            
        to_delete = backups[keep_count:]
        
        for backup in to_delete:
            backup.unlink()
            logger.info(f"Deleted old backup: {backup}")
            
        logger.info(f"Cleaned up {len(to_delete)} old backups")

# ========================= SHARDING MANAGER =========================

class ShardingManager:
    """Database sharding for horizontal scaling"""
    
    def __init__(self, base_path: str, num_shards: int = 4):
        self.base_path = Path(base_path)
        self.num_shards = num_shards
        self.shards: List[DatabaseManager] = []
        
    async def init_shards(self):
        """Initialize all shards"""
        for i in range(self.num_shards):
            shard_path = self.base_path.parent / f"{self.base_path.stem}_shard_{i}.db"
            shard = DatabaseManager(str(shard_path))
            await shard.start()
            self.shards.append(shard)
            
        logger.info(f"Initialized {self.num_shards} database shards")
        
    def get_shard_for_key(self, key: str) -> DatabaseManager:
        """Determine which shard to use for a given key"""
        shard_index = hash(key) % self.num_shards
        return self.shards[shard_index]
        
    async def execute_on_shard(self, key: str, sql: str, params: Optional[Tuple] = None):
        """Execute query on appropriate shard"""
        shard = self.get_shard_for_key(key)
        
        if sql.strip().upper().startswith('SELECT'):
            return await shard.execute_query(sql, params)
        else:
            return await shard.execute_update(sql, params)
            
    async def execute_on_all_shards(self, sql: str, params: Optional[Tuple] = None) -> List[Any]:
        """Execute query on all shards and aggregate results"""
        results = []
        
        for shard in self.shards:
            if sql.strip().upper().startswith('SELECT'):
                result = await shard.execute_query(sql, params)
            else:
                result = await shard.execute_update(sql, params)
            results.append(result)
            
        return results
        
    async def stop_all_shards(self):
        """Stop all shards"""
        for shard in self.shards:
            await shard.stop()
        logger.info("All shards stopped")

# ========================= REPLICATION MANAGER =========================

class ReplicationManager:
    """Database replication for high availability"""
    
    def __init__(self, master_path: str, replica_paths: List[str]):
        self.master_path = Path(master_path)
        self.replica_paths = [Path(p) for p in replica_paths]
        self.master: Optional[DatabaseManager] = None
        self.replicas: List[DatabaseManager] = []
        self._replication_task: Optional[asyncio.Task] = None
        self.replication_lag = 0
        
    async def start_replication(self):
        """Start master and replicas"""
        self.master = DatabaseManager(str(self.master_path))
        await self.master.start()
        
        for replica_path in self.replica_paths:
            replica = DatabaseManager(str(replica_path))
            await replica.start()
            self.replicas.append(replica)
            
        self._replication_task = asyncio.create_task(self._replicate_loop())
        logger.info(f"Replication started: 1 master, {len(self.replicas)} replicas")
        
    async def _replicate_loop(self):
        """Continuously replicate from master to replicas"""
        while True:
            try:
                await asyncio.sleep(5)  # Replicate every 5 seconds
                await self._replicate()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Replication error: {e}")
                
    async def _replicate(self):
        """Perform replication from master to all replicas"""
        start_time = time.time()
        
        # Simple replication: copy master database to replicas
        for i, replica in enumerate(self.replicas):
            replica_path = self.replica_paths[i]
            
            try:
                async with aiosqlite.connect(self.master_path) as master_conn:
                    async with aiosqlite.connect(replica_path) as replica_conn:
                        await master_conn.backup(replica_conn)
                        
            except Exception as e:
                logger.error(f"Failed to replicate to {replica_path}: {e}")
                
        self.replication_lag = time.time() - start_time
        
    async def execute_on_master(self, sql: str, params: Optional[Tuple] = None):
        """Execute write query on master"""
        if not self.master:
            raise RuntimeError("Master not initialized")
            
        if sql.strip().upper().startswith('SELECT'):
            return await self.master.execute_query(sql, params)
        else:
            return await self.master.execute_update(sql, params)
            
    async def execute_on_replica(self, sql: str, params: Optional[Tuple] = None, 
                                 replica_index: int = 0):
        """Execute read query on replica"""
        if replica_index >= len(self.replicas):
            replica_index = 0
            
        replica = self.replicas[replica_index]
        return await replica.execute_query(sql, params)
        
    async def stop_replication(self):
        """Stop replication"""
        if self._replication_task:
            self._replication_task.cancel()
            try:
                await self._replication_task
            except asyncio.CancelledError:
                pass
                
        if self.master:
            await self.master.stop()
            
        for replica in self.replicas:
            await replica.stop()
            
        logger.info("Replication stopped")

# ========================= DATA EXPORT/IMPORT =========================

class DataExporter:
    """Export database data to various formats"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
        
    async def export_to_json(self, output_path: str, tables: Optional[List[str]] = None):
        """Export database tables to JSON"""
        if tables is None:
            tables = await self._get_all_tables()
            
        export_data = {}
        
        for table in tables:
            try:
                rows = await self.db_manager.execute_query(f"SELECT * FROM {table}")
                export_data[table] = [dict(row) for row in rows]
                logger.info(f"Exported {len(rows)} rows from {table}")
            except Exception as e:
                logger.error(f"Failed to export table {table}: {e}")
                export_data[table] = []
                
        with open(output_path, 'w') as f:
            json.dump(export_data, f, indent=2, default=str)
            
        logger.info(f"Data exported to {output_path}")
        
    async def export_to_csv(self, table: str, output_path: str):
        """Export single table to CSV"""
        import csv
        
        rows = await self.db_manager.execute_query(f"SELECT * FROM {table}")
        
        if not rows:
            logger.warning(f"No data to export from {table}")
            return
            
        with open(output_path, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=rows[0].keys())
            writer.writeheader()
            for row in rows:
                writer.writerow(dict(row))
                
        logger.info(f"Exported {len(rows)} rows from {table} to {output_path}")
        
    async def _get_all_tables(self) -> List[str]:
        """Get list of all tables in database"""
        rows = await self.db_manager.execute_query(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        )
        return [row['name'] for row in rows]

class DataImporter:
    """Import data into database from various formats"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
        
    async def import_from_json(self, input_path: str):
        """Import data from JSON file"""
        with open(input_path, 'r') as f:
            import_data = json.load(f)
            
        for table, rows in import_data.items():
            if not rows:
                continue
                
            logger.info(f"Importing {len(rows)} rows into {table}")
            
            columns = list(rows[0].keys())
            placeholders = ','.join(['?'] * len(columns))
            sql = f"INSERT OR REPLACE INTO {table} ({','.join(columns)}) VALUES ({placeholders})"
            
            params_list = [tuple(row[col] for col in columns) for row in rows]
            await self.db_manager.execute_batch(sql, params_list)
            
        logger.info(f"Data imported from {input_path}")
        
    async def import_from_csv(self, table: str, input_path: str):
        """Import CSV file into table"""
        import csv
        
        with open(input_path, 'r') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            
        if not rows:
            logger.warning(f"No data to import from {input_path}")
            return
            
        columns = list(rows[0].keys())
        placeholders = ','.join(['?'] * len(columns))
        sql = f"INSERT OR REPLACE INTO {table} ({','.join(columns)}) VALUES ({placeholders})"
        
        params_list = [tuple(row[col] for col in columns) for row in rows]
        await self.db_manager.execute_batch(sql, params_list)
        
        logger.info(f"Imported {len(rows)} rows into {table} from {input_path}")

# ========================= PERFORMANCE MONITOR =========================

class PerformanceMonitor:
    """Monitor database performance metrics"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
        self.metrics: Dict[str, deque] = defaultdict(lambda: deque(maxlen=100))
        
    def record_metric(self, metric_name: str, value: float):
        """Record a performance metric"""
        self.metrics[metric_name].append({
            'value': value,
            'timestamp': time.time()
        })
        
    def get_metric_stats(self, metric_name: str) -> Dict[str, float]:
        """Get statistics for a metric"""
        if metric_name not in self.metrics:
            return {}
            
        values = [m['value'] for m in self.metrics[metric_name]]
        
        if not values:
            return {}
            
        return {
            'min': min(values),
            'max': max(values),
            'avg': sum(values) / len(values),
            'count': len(values)
        }
        
    async def get_database_size(self) -> int:
        """Get database file size in bytes"""
        return self.db_manager.db_path.stat().st_size
        
    async def get_table_sizes(self) -> Dict[str, int]:
        """Get row counts for all tables"""
        tables = await self.db_manager.execute_query(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        )
        
        sizes = {}
        for table in tables:
            result = await self.db_manager.execute_query(f"SELECT COUNT(*) as count FROM {table['name']}")
            sizes[table['name']] = result[0]['count']
            
        return sizes
        
    async def analyze_slow_queries(self, threshold_ms: float = 100) -> List[QueryMetrics]:
        """Get queries slower than threshold"""
        all_metrics = self.db_manager.get_query_metrics()
        slow_queries = [
            m for m in all_metrics 
            if m.execution_time * 1000 > threshold_ms
        ]
        slow_queries.sort(key=lambda m: m.execution_time, reverse=True)
        return slow_queries

# Example usage
async def main():
    db_manager = DatabaseManager(db_path="nvr_main.db")
    await db_manager.start()

    try:
        # Add a new event
        event_id = str(uuid.uuid4())
        await db_manager.execute_update(
            "INSERT INTO events (event_id, camera_id, event_type, timestamp, details) VALUES (?, ?, ?, ?, ?)",
            (event_id, "cam_01", "motion", datetime.utcnow().isoformat(), '{"region": "doorway"}')
        )
        print("Event added.")

        # Add detections for the event
        await db_manager.execute_batch(
            "INSERT INTO detections (detection_id, event_id, object_type, confidence) VALUES (?, ?, ?, ?)",
            [
                (str(uuid.uuid4()), event_id, "person", 0.95),
                (str(uuid.uuid4()), event_id, "car", 0.88),
            ]
        )
        print("Detections added.")

        # Retrieve events
        events = await db_manager.execute_query("SELECT * FROM events ORDER BY timestamp DESC LIMIT 10")
        print(f"Found {len(events)} events.")
        for event in events:
            print(f"  - Event: {event['event_id']}, Type: {event['event_type']}, Time: {event['timestamp']}")

        # Use query builder
        builder = QueryBuilder()
        sql, params = builder.select("event_id", "event_type").from_table("events").where("camera_id = ?", "cam_01").order_by("timestamp", "DESC").limit(5).build()
        
        built_events = await db_manager.execute_query(sql, tuple(params))
        print(f"Found {len(built_events)} events via QueryBuilder.")

        # Test backup
        backup_manager = BackupManager(db_path="nvr_main.db", backup_dir="backups")
        backup_meta = await backup_manager.create_backup(backup_name="test", compress=True)
        print(f"Backup created: {backup_meta.file_path}")

        # Test performance monitoring
        perf_monitor = PerformanceMonitor(db_manager)
        db_size = await perf_monitor.get_database_size()
        print(f"Database size: {db_size} bytes")

        table_sizes = await perf_monitor.get_table_sizes()
        print(f"Table sizes: {table_sizes}")

    finally:
        await db_manager.stop()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    asyncio.run(main())
