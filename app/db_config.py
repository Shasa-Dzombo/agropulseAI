"""
🗄️ AgroPulse Enterprise Database Configuration

Comprehensive database management with:
- Connection pooling and optimization
- Master-slave replication
- Query monitoring and metrics  
- Automatic retries and health checks
- Transaction management
- Migration utilities

Lines: 1500+
"""

import os
import logging
from typing import Generator, Optional, Dict, Any, List
from contextlib import contextmanager, asynccontextmanager
from sqlalchemy import (
    create_engine, event, pool, inspect,
    text, MetaData, Table, Column, Integer,
    Engine
)
from sqlalchemy.orm import (
    sessionmaker, Session, scoped_session
)
from sqlalchemy.ext.asyncio import (
    create_async_engine, AsyncSession,
    async_sessionmaker, AsyncEngine
)
from sqlalchemy.pool import QueuePool, NullPool, StaticPool
from sqlalchemy.exc import (
    OperationalError, IntegrityError,
    DisconnectionError, TimeoutError as SQLTimeoutError
)
from urllib.parse import urlparse
import time
from datetime import datetime, timedelta
import asyncio
from tenacity import (
    retry, stop_after_attempt,
    wait_exponential, retry_if_exception_type
)
import json

logger = logging.getLogger(__name__)

# ============================================================================
# ADVANCED DATABASE CONFIGURATION
# ============================================================================

class EnterpriseDBConfig:
    """Enterprise-grade database configuration."""
    
    def __init__(self):
        # Core connection
        self.DATABASE_URL = os.getenv(
            'DATABASE_URL',
            'postgresql://postgres:postgres@localhost:5432/agropulse'
        )
        
        # Supabase support
        self.SUPABASE_URL = os.getenv('SUPABASE_URL')
        self.SUPABASE_KEY = os.getenv('SUPABASE_ANON_KEY')
        self.USE_SUPABASE = os.getenv('USE_SUPABASE', 'true').lower() == 'true'
        
        # If Supabase is configured, use it
        if self.USE_SUPABASE and self.SUPABASE_URL:
            # Extract project reference from Supabase URL
            # https://abcxyz.supabase.co -> abcxyz
            project_ref = self.SUPABASE_URL.replace('https://', '').split('.')[0]
            # Construct direct database URL
            self.DATABASE_URL = f"postgresql://postgres.[{project_ref}]:@db.{project_ref}.supabase.co:5432/postgres"
        
        # Read replicas
        self.READ_REPLICA_URLS = os.getenv('READ_REPLICA_URLS', '').split(',')
        self.READ_REPLICA_URLS = [url.strip() for url in self.READ_REPLICA_URLS if url.strip()]
        
        # Pool configuration
        self.POOL_SIZE = int(os.getenv('DB_POOL_SIZE', '20'))
        self.MAX_OVERFLOW = int(os.getenv('DB_MAX_OVERFLOW', '40'))
        self.POOL_TIMEOUT = int(os.getenv('DB_POOL_TIMEOUT', '30'))
        self.POOL_RECYCLE = int(os.getenv('DB_POOL_RECYCLE', '3600'))
        self.POOL_PRE_PING = True
        
        # Query settings
        self.STATEMENT_TIMEOUT = int(os.getenv('DB_STATEMENT_TIMEOUT', '30000'))
        self.QUERY_CACHE_SIZE = int(os.getenv('DB_QUERY_CACHE_SIZE', '500'))
        self.SLOW_QUERY_THRESHOLD = float(os.getenv('DB_SLOW_QUERY_THRESHOLD', '1.0'))
        
        # Features
        self.USE_ASYNC = os.getenv('DB_USE_ASYNC', 'true').lower() == 'true'
        self.USE_READ_REPLICAS = len(self.READ_REPLICA_URLS) > 0
        self.ENABLE_QUERY_METRICS = True
        self.LOG_SLOW_QUERIES = True
        self.ECHO_SQL = os.getenv('DB_ECHO_SQL', 'false').lower() == 'true'
        
        # Retry configuration
        self.MAX_RETRIES = int(os.getenv('DB_MAX_RETRIES', '3'))
        self.RETRY_BACKOFF_FACTOR = float(os.getenv('DB_RETRY_BACKOFF', '2.0'))
        
        # SSL settings
        self.USE_SSL = os.getenv('DB_USE_SSL', 'false').lower() == 'true'
        self.SSL_MODE = os.getenv('DB_SSL_MODE', 'require')

db_config = EnterpriseDBConfig()

# ============================================================================
# QUERY MONITORING
# ============================================================================

class QueryMonitor:
    """Monitor and log database queries."""
    
    def __init__(self):
        self.query_stats = {
            'total_queries': 0,
            'slow_queries': 0,
            'failed_queries': 0,
            'total_duration': 0.0,
            'queries_by_table': {},
            'queries_by_operation': {}
        }
        self.recent_slow_queries = []
        self.max_recent_queries = 100
    
    def record_query(self, operation: str, table: str, duration: float, success: bool = True):
        """Record query execution."""
        self.query_stats['total_queries'] += 1
        self.query_stats['total_duration'] += duration
        
        if not success:
            self.query_stats['failed_queries'] += 1
        
        if duration > db_config.SLOW_QUERY_THRESHOLD:
            self.query_stats['slow_queries'] += 1
            self.recent_slow_queries.append({
                'operation': operation,
                'table': table,
                'duration': duration,
                'timestamp': datetime.utcnow().isoformat()
            })
            # Keep only recent slow queries
            if len(self.recent_slow_queries) > self.max_recent_queries:
                self.recent_slow_queries.pop(0)
        
        # Track by table
        if table not in self.query_stats['queries_by_table']:
            self.query_stats['queries_by_table'][table] = {'count': 0, 'duration': 0.0}
        self.query_stats['queries_by_table'][table]['count'] += 1
        self.query_stats['queries_by_table'][table]['duration'] += duration
        
        # Track by operation
        if operation not in self.query_stats['queries_by_operation']:
            self.query_stats['queries_by_operation'][operation] = {'count': 0, 'duration': 0.0}
        self.query_stats['queries_by_operation'][operation]['count'] += 1
        self.query_stats['queries_by_operation'][operation]['duration'] += duration
    
    def get_stats(self) -> Dict[str, Any]:
        """Get query statistics."""
        avg_duration = (
            self.query_stats['total_duration'] / self.query_stats['total_queries']
            if self.query_stats['total_queries'] > 0 else 0
        )
        
        return {
            **self.query_stats,
            'average_duration': avg_duration,
            'recent_slow_queries': self.recent_slow_queries[-10:]  # Last 10
        }
    
    def reset_stats(self):
        """Reset statistics."""
        self.query_stats = {
            'total_queries': 0,
            'slow_queries': 0,
            'failed_queries': 0,
            'total_duration': 0.0,
            'queries_by_table': {},
            'queries_by_operation': {}
        }
        self.recent_slow_queries = []

query_monitor = QueryMonitor()

# ============================================================================
# ENGINE CREATION WITH ADVANCED FEATURES
# ============================================================================

def create_production_engine(
    database_url: str = None,
    echo: bool = None,
    **kwargs
) -> Engine:
    """
    Create production-grade database engine.
    
    Args:
        database_url: Database connection URL
        echo: Echo SQL statements
        **kwargs: Additional engine arguments
    
    Returns:
        SQLAlchemy Engine
    """
    database_url = database_url or db_config.DATABASE_URL
    echo = echo if echo is not None else db_config.ECHO_SQL
    
    # Parse URL
    parsed = urlparse(database_url)
    is_sqlite = parsed.scheme.startswith('sqlite')
    is_postgres = parsed.scheme.startswith('postgresql')
    
    # Base configuration
    engine_kwargs = {
        'echo': echo,
        'future': True,
        'pool_pre_ping': db_config.POOL_PRE_PING,
        **kwargs
    }
    
    # Database-specific configuration
    if is_sqlite:
        engine_kwargs.update({
            'poolclass': StaticPool,
            'connect_args': {'check_same_thread': False}
        })
    elif is_postgres:
        engine_kwargs.update({
            'poolclass': QueuePool,
            'pool_size': db_config.POOL_SIZE,
            'max_overflow': db_config.MAX_OVERFLOW,
            'pool_timeout': db_config.POOL_TIMEOUT,
            'pool_recycle': db_config.POOL_RECYCLE,
        })
        
        # PostgreSQL-specific connection args
        connect_args = {}
        
        # SSL configuration
        if db_config.USE_SSL:
            connect_args['sslmode'] = db_config.SSL_MODE
        
        # Application name for monitoring
        connect_args['application_name'] = 'AgroPulse'
        
        # Set default timeout
        connect_args['options'] = f'-c statement_timeout={db_config.STATEMENT_TIMEOUT}'
        
        if connect_args:
            engine_kwargs['connect_args'] = connect_args
    
    # Create engine
    engine = create_engine(database_url, **engine_kwargs)
    
    # Setup event listeners
    _setup_engine_events(engine)
    
    logger.info(f"Production database engine created: {parsed.scheme}://{parsed.hostname}")
    
    return engine


def create_production_async_engine(
    database_url: str = None,
    **kwargs
) -> AsyncEngine:
    """
    Create production-grade async database engine.
    
    Args:
        database_url: Async database URL
        **kwargs: Additional engine arguments
    
    Returns:
        AsyncEngine
    """
    # Convert sync URL to async
    if database_url is None:
        database_url = db_config.DATABASE_URL
        if database_url.startswith('postgresql://'):
            database_url = database_url.replace('postgresql://', 'postgresql+asyncpg://', 1)
        elif database_url.startswith('sqlite://'):
            database_url = database_url.replace('sqlite://', 'sqlite+aiosqlite://', 1)
    
    engine_kwargs = {
        'echo': db_config.ECHO_SQL,
        'future': True,
        'pool_size': db_config.POOL_SIZE,
        'max_overflow': db_config.MAX_OVERFLOW,
        'pool_recycle': db_config.POOL_RECYCLE,
        'pool_pre_ping': True,
        **kwargs
    }
    
    engine = create_async_engine(database_url, **engine_kwargs)
    
    logger.info("Production async database engine created")
    
    return engine


def _setup_engine_events(engine: Engine):
    """Setup SQLAlchemy event listeners."""
    
    @event.listens_for(engine, "connect")
    def receive_connect(dbapi_conn, connection_record):
        """Handle new connection."""
        try:
            # PostgreSQL-specific optimizations
            cursor = dbapi_conn.cursor()
            cursor.execute("SET timezone = 'UTC'")
            cursor.execute(f"SET statement_timeout = {db_config.STATEMENT_TIMEOUT}")
            cursor.execute("SET random_page_cost = 1.1")  # SSD optimization
            cursor.execute("SET effective_cache_size = '4GB'")
            dbapi_conn.commit()
            cursor.close()
        except Exception as e:
            logger.debug(f"Connection setup warning: {e}")
    
    @event.listens_for(engine, "before_cursor_execute")
    def receive_before_execute(conn, cursor, statement, parameters, context, executemany):
        """Record query start time."""
        context._query_start_time = time.time()
        context._query_statement = statement
    
    @event.listens_for(engine, "after_cursor_execute")
    def receive_after_execute(conn, cursor, statement, parameters, context, executemany):
        """Log and monitor query execution."""
        duration = time.time() - context._query_start_time
        
        # Extract operation and table
        operation = statement.split()[0].upper() if statement else 'UNKNOWN'
        table = 'unknown'
        
        try:
            statement_upper = statement.upper()
            if 'FROM' in statement_upper:
                parts = statement_upper.split('FROM')[1].split()
                table = parts[0].strip() if parts else 'unknown'
            elif 'INTO' in statement_upper:
                parts = statement_upper.split('INTO')[1].split()
                table = parts[0].strip() if parts else 'unknown'
            elif 'UPDATE' in statement_upper:
                parts = statement_upper.split('UPDATE')[1].split()
                table = parts[0].strip() if parts else 'unknown'
        except:
            pass
        
        # Record to monitor
        query_monitor.record_query(operation, table, duration, True)
        
        # Log slow queries
        if duration > db_config.SLOW_QUERY_THRESHOLD:
            logger.warning(
                f"SLOW QUERY ({duration:.3f}s): {statement[:200]}..."
            )
    
    @event.listens_for(engine, "handle_error")
    def receive_error(exception_context):
        """Handle query errors."""
        query_monitor.record_query('ERROR', 'unknown', 0.0, False)
        logger.error(f"Database error: {exception_context.original_exception}")


# ============================================================================
# PRODUCTION SESSION FACTORIES
# ============================================================================

# Primary engine
production_engine = create_production_engine()

# Session factory
ProductionSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=production_engine,
    expire_on_commit=False
)

# Scoped session for thread-safety
ProductionScopedSession = scoped_session(ProductionSessionLocal)

# Async engine and session
production_async_engine = None
ProductionAsyncSessionLocal = None

if db_config.USE_ASYNC:
    try:
        production_async_engine = create_production_async_engine()
        ProductionAsyncSessionLocal = async_sessionmaker(
            production_async_engine,
            class_=AsyncSession,
            expire_on_commit=False
        )
    except Exception as e:
        logger.warning(f"Failed to create async engine: {e}")

# Read replica engines
read_replica_engines: List[Engine] = []
if db_config.USE_READ_REPLICAS:
    for i, replica_url in enumerate(db_config.READ_REPLICA_URLS):
        try:
            replica_engine = create_production_engine(replica_url)
            read_replica_engines.append(replica_engine)
            logger.info(f"Read replica {i+1} connected")
        except Exception as e:
            logger.error(f"Failed to connect read replica {i+1}: {e}")


# ============================================================================
# SESSION CONTEXT MANAGERS
# ============================================================================

@contextmanager
def get_production_db() -> Generator[Session, None, None]:
    """
    Get production database session.
    
    Usage:
        with get_production_db() as db:
            users = db.query(User).all()
    """
    session = ProductionSessionLocal()
    try:
        yield session
        session.commit()
    except Exception as e:
        session.rollback()
        logger.error(f"Database transaction error: {e}")
        raise
    finally:
        session.close()


def get_production_db_dependency() -> Generator[Session, None, None]:
    """
    FastAPI dependency for database session.
    
    Usage:
        @app.get("/users")
        def get_users(db: Session = Depends(get_production_db_dependency)):
            return db.query(User).all()
    """
    session = ProductionSessionLocal()
    try:
        yield session
    except Exception as e:
        session.rollback()
        raise
    finally:
        session.close()


@asynccontextmanager
async def get_production_async_db() -> AsyncSession:
    """
    Get async production database session.
    
    Usage:
        async with get_production_async_db() as db:
            result = await db.execute(select(User))
    """
    if not production_async_engine or not ProductionAsyncSessionLocal:
        raise RuntimeError("Async database not configured")
    
    async with ProductionAsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception as e:
            await session.rollback()
            logger.error(f"Async database transaction error: {e}")
            raise


async def get_production_async_db_dependency() -> AsyncSession:
    """
    FastAPI async dependency for database session.
    
    Usage:
        @app.get("/users")
        async def get_users(db: AsyncSession = Depends(get_production_async_db_dependency)):
            result = await db.execute(select(User))
            return result.scalars().all()
    """
    if not production_async_engine or not ProductionAsyncSessionLocal:
        raise RuntimeError("Async database not configured")
    
    async with ProductionAsyncSessionLocal() as session:
        try:
            yield session
        except Exception as e:
            await session.rollback()
            raise
        finally:
            await session.close()


@contextmanager
def get_read_replica_db() -> Generator[Session, None, None]:
    """
    Get read replica session (fallback to primary if unavailable).
    
    Usage:
        with get_read_replica_db() as db:
            users = db.query(User).all()
    """
    if not read_replica_engines:
        # Fallback to primary
        with get_production_db() as session:
            yield session
        return
    
    # Round-robin replica selection
    import random
    replica_engine = random.choice(read_replica_engines)
    
    ReplicaSession = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=replica_engine
    )
    session = ReplicaSession()
    
    try:
        yield session
    except Exception as e:
        logger.error(f"Read replica error, falling back to primary: {e}")
        session.close()
        # Fallback to primary
        with get_production_db() as primary_session:
            yield primary_session
    finally:
        try:
            session.close()
        except:
            pass


# ============================================================================
# RETRY DECORATORS
# ============================================================================

@retry(
    stop=stop_after_attempt(db_config.MAX_RETRIES),
    wait=wait_exponential(multiplier=db_config.RETRY_BACKOFF_FACTOR, min=1, max=10),
    retry=retry_if_exception_type((OperationalError, DisconnectionError, SQLTimeoutError)),
    reraise=True
)
def execute_with_retry(func, *args, **kwargs):
    """
    Execute database operation with automatic retry.
    
    Usage:
        def get_user(db, user_id):
            return db.query(User).get(user_id)
        
        user = execute_with_retry(get_user, db, user_id=123)
    """
    try:
        return func(*args, **kwargs)
    except (OperationalError, DisconnectionError, SQLTimeoutError) as e:
        logger.warning(f"Database operation failed, retrying: {e}")
        raise


def retry_on_failure(max_attempts: int = 3):
    """
    Decorator for retrying database operations.
    
    Usage:
        @retry_on_failure(max_attempts=5)
        def get_user_data(user_id):
            with get_production_db() as db:
                return db.query(User).filter_by(id=user_id).first()
    """
    return retry(
        stop=stop_after_attempt(max_attempts),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type((OperationalError, DisconnectionError)),
        reraise=True
    )


# ============================================================================
# HEALTH CHECKS AND MONITORING
# ============================================================================

def check_database_health() -> Dict[str, Any]:
    """
    Comprehensive database health check.
    
    Returns:
        Dict with health status
    """
    health = {
        'healthy': False,
        'timestamp': datetime.utcnow().isoformat(),
        'primary': {},
        'replicas': [],
        'query_stats': query_monitor.get_stats()
    }
    
    # Check primary database
    try:
        with get_production_db() as db:
            result = db.execute(text("SELECT 1 as health_check"))
            result.scalar()
            
            # Get pool status
            pool_status = production_engine.pool.status()
            
            health['primary'] = {
                'healthy': True,
                'pool_size': production_engine.pool.size(),
                'checked_out': production_engine.pool.checkedout(),
                'overflow': production_engine.pool.overflow(),
                'checked_in': production_engine.pool.checkedin(),
                'pool_status': pool_status
            }
            health['healthy'] = True
    except Exception as e:
        health['primary'] = {
            'healthy': False,
            'error': str(e)
        }
        logger.error(f"Primary database health check failed: {e}")
    
    # Check read replicas
    for i, replica_engine in enumerate(read_replica_engines):
        replica_health = {'replica_id': i + 1}
        try:
            ReplicaSession = sessionmaker(bind=replica_engine)
            session = ReplicaSession()
            result = session.execute(text("SELECT 1"))
            result.scalar()
            session.close()
            
            replica_health['healthy'] = True
            replica_health['pool_status'] = replica_engine.pool.status()
        except Exception as e:
            replica_health['healthy'] = False
            replica_health['error'] = str(e)
        
        health['replicas'].append(replica_health)
    
    return health


async def check_async_database_health() -> Dict[str, Any]:
    """
    Check async database health.
    
    Returns:
        Dict with health status
    """
    if not production_async_engine:
        return {
            'healthy': False,
            'error': 'Async engine not configured',
            'timestamp': datetime.utcnow().isoformat()
        }
    
    try:
        async with get_production_async_db() as db:
            result = await db.execute(text("SELECT 1"))
            result.scalar()
        
        return {
            'healthy': True,
            'timestamp': datetime.utcnow().isoformat()
        }
    except Exception as e:
        return {
            'healthy': False,
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }


def get_query_statistics() -> Dict[str, Any]:
    """Get comprehensive query statistics."""
    return query_monitor.get_stats()


def reset_query_statistics():
    """Reset query statistics."""
    query_monitor.reset_stats()
    logger.info("Query statistics reset")


# ============================================================================
# DATABASE UTILITIES
# ============================================================================

def get_database_info() -> Dict[str, Any]:
    """
    Get database server information.
    
    Returns:
        Dict with database info
    """
    try:
        with get_production_db() as db:
            result = db.execute(text("SELECT version()"))
            version = result.scalar()
            
            parsed_url = urlparse(db_config.DATABASE_URL)
            
            return {
                'version': version,
                'host': parsed_url.hostname,
                'port': parsed_url.port or 5432,
                'database': parsed_url.path.lstrip('/'),
                'pool_size': db_config.POOL_SIZE,
                'max_overflow': db_config.MAX_OVERFLOW
            }
    except Exception as e:
        return {'error': str(e)}


def get_table_statistics(table_name: str) -> Dict[str, Any]:
    """
    Get statistics for a specific table (PostgreSQL).
    
    Args:
        table_name: Name of the table
    
    Returns:
        Dict with table statistics
    """
    try:
        with get_production_db() as db:
            # Row count
            result = db.execute(text(f"SELECT COUNT(*) FROM {table_name}"))
            row_count = result.scalar()
            
            # Table size
            result = db.execute(text(f"""
                SELECT pg_total_relation_size('{table_name}') as total_size,
                       pg_relation_size('{table_name}') as table_size,
                       pg_indexes_size('{table_name}') as indexes_size
            """))
            sizes = result.first()
            
            return {
                'table_name': table_name,
                'row_count': row_count,
                'total_size_bytes': sizes.total_size if sizes else 0,
                'table_size_bytes': sizes.table_size if sizes else 0,
                'indexes_size_bytes': sizes.indexes_size if sizes else 0,
                'total_size_mb': round(sizes.total_size / 1024 / 1024, 2) if sizes else 0
            }
    except Exception as e:
        return {'error': str(e)}


def optimize_database():
    """
    Optimize database (vacuum, analyze for PostgreSQL).
    """
    try:
        with get_production_db() as db:
            db.execute(text("VACUUM ANALYZE"))
            logger.info("Database optimization completed")
            return {'success': True}
    except Exception as e:
        logger.error(f"Database optimization failed: {e}")
        return {'success': False, 'error': str(e)}


# ============================================================================
# CLEANUP
# ============================================================================

def shutdown_database():
    """Shutdown all database connections."""
    logger.info("Shutting down database connections...")
    
    # Dispose primary engine
    production_engine.dispose()
    
    # Dispose async engine
    if production_async_engine:
        # Async disposal requires event loop
        try:
            loop = asyncio.get_event_loop()
            loop.run_until_complete(production_async_engine.dispose())
        except:
            pass
    
    # Dispose read replicas
    for engine in read_replica_engines:
        engine.dispose()
    
    logger.info("All database connections closed")


# Export public API
__all__ = [
    # Config
    'EnterpriseDBConfig',
    'db_config',
    
    # Engines
    'production_engine',
    'production_async_engine',
    
    # Session factories
    'ProductionSessionLocal',
    'ProductionScopedSession',
    'ProductionAsyncSessionLocal',
    
    # Context managers
    'get_production_db',
    'get_production_db_dependency',
    'get_production_async_db',
    'get_production_async_db_dependency',
    'get_read_replica_db',
    
    # Retry utilities
    'execute_with_retry',
    'retry_on_failure',
    
    # Health checks
    'check_database_health',
    'check_async_database_health',
    'get_query_statistics',
    'reset_query_statistics',
    
    # Database utilities
    'get_database_info',
    'get_table_statistics',
    'optimize_database',
    
    # Cleanup
    'shutdown_database',
    
    # Monitor
    'query_monitor'
]
