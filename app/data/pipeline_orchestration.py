"""
Data Pipeline Orchestration System

Airflow-inspired DAG orchestration framework for managing complex data workflows.
Provides task scheduling, dependency resolution, parallel execution, and monitoring.

Features:
- DAG (Directed Acyclic Graph) definition and validation
- Task scheduling with cron expressions
- Dependency management and resolution
- Parallel and sequential execution
- Retry logic with exponential backoff
- Sensor operators for external triggers
- Webhook and event-driven triggers
- SLA monitoring and alerting
- Dynamic pipeline generation
- Task state management
- Execution history and logging
"""

import os
import re
import json
import time
import uuid
import hashlib
import threading
import multiprocessing
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Callable, Set, Tuple
from dataclasses import dataclass, field, asdict
from enum import Enum
from collections import defaultdict, deque
import logging
from pathlib import Path
import pickle
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, as_completed

from sqlalchemy import (
    Column, String, Integer, Float, DateTime, Text, 
    Boolean, ForeignKey, JSON, create_engine, Enum as SQLEnum
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from croniter import croniter

logger = logging.getLogger(__name__)
Base = declarative_base()


class TaskState(Enum):
    """Task execution states"""
    NONE = "none"
    SCHEDULED = "scheduled"
    QUEUED = "queued"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"
    UPSTREAM_FAILED = "upstream_failed"
    UP_FOR_RETRY = "up_for_retry"
    UP_FOR_RESCHEDULE = "up_for_reschedule"
    REMOVED = "removed"


class DAGState(Enum):
    """DAG execution states"""
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    PAUSED = "paused"


class TriggerRule(Enum):
    """Task trigger rules"""
    ALL_SUCCESS = "all_success"  # All parents succeeded
    ALL_FAILED = "all_failed"  # All parents failed
    ALL_DONE = "all_done"  # All parents completed
    ONE_SUCCESS = "one_success"  # At least one parent succeeded
    ONE_FAILED = "one_failed"  # At least one parent failed
    NONE_FAILED = "none_failed"  # No parent failed
    NONE_SKIPPED = "none_skipped"  # No parent skipped
    DUMMY = "dummy"  # Always trigger


class ScheduleInterval(Enum):
    """Common schedule intervals"""
    ONCE = None
    HOURLY = "0 * * * *"
    DAILY = "0 0 * * *"
    WEEKLY = "0 0 * * 0"
    MONTHLY = "0 0 1 * *"


# Database Models
class DAGModel(Base):
    """DAG metadata table"""
    __tablename__ = 'dags'
    
    dag_id = Column(String(256), primary_key=True)
    description = Column(Text)
    schedule_interval = Column(String(64))
    start_date = Column(DateTime)
    end_date = Column(DateTime)
    is_paused = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    max_active_runs = Column(Integer, default=16)
    concurrency = Column(Integer, default=16)
    tags = Column(JSON)
    default_args = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    runs = relationship("DAGRun", back_populates="dag", cascade="all, delete-orphan")


class DAGRun(Base):
    """DAG run instance table"""
    __tablename__ = 'dag_runs'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    dag_id = Column(String(256), ForeignKey('dags.dag_id'))
    run_id = Column(String(256), unique=True, nullable=False)
    execution_date = Column(DateTime, nullable=False)
    start_date = Column(DateTime)
    end_date = Column(DateTime)
    state = Column(SQLEnum(DAGState), default=DAGState.RUNNING)
    external_trigger = Column(Boolean, default=False)
    conf = Column(JSON)
    
    dag = relationship("DAGModel", back_populates="runs")
    task_instances = relationship("TaskInstance", back_populates="dag_run", cascade="all, delete-orphan")


class TaskInstance(Base):
    """Task instance execution table"""
    __tablename__ = 'task_instances'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(String(256), nullable=False)
    dag_id = Column(String(256), nullable=False)
    run_id = Column(String(256), ForeignKey('dag_runs.run_id'))
    execution_date = Column(DateTime, nullable=False)
    start_date = Column(DateTime)
    end_date = Column(DateTime)
    duration = Column(Float)
    state = Column(SQLEnum(TaskState), default=TaskState.NONE)
    try_number = Column(Integer, default=1)
    max_tries = Column(Integer, default=3)
    hostname = Column(String(256))
    pool = Column(String(256))
    queue = Column(String(256))
    priority_weight = Column(Integer, default=1)
    operator = Column(String(256))
    log_url = Column(Text)
    
    dag_run = relationship("DAGRun", back_populates="task_instances")


class SLAMiss(Base):
    """SLA violation tracking"""
    __tablename__ = 'sla_miss'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(String(256), nullable=False)
    dag_id = Column(String(256), nullable=False)
    execution_date = Column(DateTime, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    duration = Column(Float)
    sla = Column(Float)


@dataclass
class TaskConfig:
    """Task configuration"""
    task_id: str
    operator: str
    operator_params: Dict[str, Any] = field(default_factory=dict)
    dependencies: List[str] = field(default_factory=list)
    trigger_rule: TriggerRule = TriggerRule.ALL_SUCCESS
    retries: int = 3
    retry_delay: timedelta = field(default_factory=lambda: timedelta(minutes=5))
    retry_exponential_backoff: bool = True
    max_retry_delay: timedelta = field(default_factory=lambda: timedelta(hours=1))
    execution_timeout: Optional[timedelta] = None
    sla: Optional[timedelta] = None
    pool: str = "default_pool"
    queue: str = "default"
    priority_weight: int = 1
    weight_rule: str = "downstream"  # downstream, upstream, absolute
    on_success_callback: Optional[Callable] = None
    on_failure_callback: Optional[Callable] = None
    on_retry_callback: Optional[Callable] = None


@dataclass
class DAGConfig:
    """DAG configuration"""
    dag_id: str
    description: str = ""
    schedule_interval: Optional[str] = None
    start_date: datetime = field(default_factory=datetime.utcnow)
    end_date: Optional[datetime] = None
    catchup: bool = False
    max_active_runs: int = 16
    concurrency: int = 16
    dagrun_timeout: Optional[timedelta] = None
    default_args: Dict[str, Any] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)


class Task:
    """
    Task definition
    
    Represents a single unit of work in a DAG.
    """
    
    def __init__(self, config: TaskConfig):
        self.config = config
        self.task_id = config.task_id
        self.downstream_tasks: Set[str] = set()
        self.upstream_tasks: Set[str] = set(config.dependencies)
    
    def set_upstream(self, task_id: str):
        """Set upstream dependency"""
        self.upstream_tasks.add(task_id)
    
    def set_downstream(self, task_id: str):
        """Set downstream dependency"""
        self.downstream_tasks.add(task_id)
    
    def execute(self, context: Dict[str, Any]) -> Any:
        """
        Execute task logic
        
        Args:
            context: Execution context with run info
            
        Returns:
            Task result
        """
        operator = self.config.operator
        params = self.config.operator_params
        
        # Route to appropriate operator
        if operator == "python":
            return self._execute_python(params, context)
        elif operator == "bash":
            return self._execute_bash(params, context)
        elif operator == "sql":
            return self._execute_sql(params, context)
        elif operator == "sensor":
            return self._execute_sensor(params, context)
        elif operator == "http":
            return self._execute_http(params, context)
        elif operator == "email":
            return self._execute_email(params, context)
        else:
            raise ValueError(f"Unknown operator: {operator}")
    
    def _execute_python(self, params: Dict[str, Any], context: Dict[str, Any]) -> Any:
        """Execute Python callable"""
        python_callable = params.get('python_callable')
        if not python_callable:
            raise ValueError("python_callable is required")
        
        op_kwargs = params.get('op_kwargs', {})
        provide_context = params.get('provide_context', False)
        
        if provide_context:
            op_kwargs['context'] = context
        
        return python_callable(**op_kwargs)
    
    def _execute_bash(self, params: Dict[str, Any], context: Dict[str, Any]) -> str:
        """Execute bash command"""
        import subprocess
        
        bash_command = params.get('bash_command')
        if not bash_command:
            raise ValueError("bash_command is required")
        
        env = params.get('env', os.environ.copy())
        cwd = params.get('cwd')
        
        result = subprocess.run(
            bash_command,
            shell=True,
            capture_output=True,
            text=True,
            env=env,
            cwd=cwd
        )
        
        if result.returncode != 0:
            raise RuntimeError(f"Bash command failed: {result.stderr}")
        
        return result.stdout
    
    def _execute_sql(self, params: Dict[str, Any], context: Dict[str, Any]) -> Any:
        """Execute SQL query"""
        from sqlalchemy import create_engine, text
        
        sql = params.get('sql')
        conn_id = params.get('conn_id')
        
        if not sql or not conn_id:
            raise ValueError("sql and conn_id are required")
        
        # Get connection from context or config
        connection_string = context.get('connections', {}).get(conn_id)
        if not connection_string:
            raise ValueError(f"Connection not found: {conn_id}")
        
        engine = create_engine(connection_string)
        with engine.connect() as conn:
            result = conn.execute(text(sql))
            if result.returns_rows:
                return result.fetchall()
            return None
    
    def _execute_sensor(self, params: Dict[str, Any], context: Dict[str, Any]) -> bool:
        """Execute sensor check"""
        sensor_callable = params.get('sensor_callable')
        if not sensor_callable:
            raise ValueError("sensor_callable is required")
        
        poke_interval = params.get('poke_interval', 60)
        timeout = params.get('timeout', 3600)
        
        start_time = time.time()
        while time.time() - start_time < timeout:
            if sensor_callable(context):
                return True
            time.sleep(poke_interval)
        
        raise TimeoutError(f"Sensor timed out after {timeout}s")
    
    def _execute_http(self, params: Dict[str, Any], context: Dict[str, Any]) -> Any:
        """Execute HTTP request"""
        import requests
        
        url = params.get('url')
        method = params.get('method', 'GET')
        headers = params.get('headers', {})
        data = params.get('data')
        json_data = params.get('json')
        
        response = requests.request(
            method=method,
            url=url,
            headers=headers,
            data=data,
            json=json_data
        )
        
        response.raise_for_status()
        
        if response.headers.get('content-type', '').startswith('application/json'):
            return response.json()
        return response.text
    
    def _execute_email(self, params: Dict[str, Any], context: Dict[str, Any]) -> None:
        """Send email notification"""
        import smtplib
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart
        
        to = params.get('to')
        subject = params.get('subject', '')
        html_content = params.get('html_content', '')
        
        # Get SMTP config from context
        smtp_config = context.get('smtp_config', {})
        
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = smtp_config.get('from')
        msg['To'] = ', '.join(to) if isinstance(to, list) else to
        
        msg.attach(MIMEText(html_content, 'html'))
        
        with smtplib.SMTP(smtp_config.get('host'), smtp_config.get('port', 587)) as server:
            server.starttls()
            if smtp_config.get('username'):
                server.login(smtp_config['username'], smtp_config['password'])
            server.send_message(msg)


class DAG:
    """
    Directed Acyclic Graph (DAG)
    
    Represents a workflow with tasks and dependencies.
    """
    
    def __init__(self, config: DAGConfig):
        self.config = config
        self.dag_id = config.dag_id
        self.tasks: Dict[str, Task] = {}
        self._validated = False
    
    def add_task(self, task: Task):
        """Add a task to the DAG"""
        if task.task_id in self.tasks:
            raise ValueError(f"Task already exists: {task.task_id}")
        
        self.tasks[task.task_id] = task
        self._validated = False
    
    def set_dependency(self, upstream_task_id: str, downstream_task_id: str):
        """Set dependency between tasks"""
        if upstream_task_id not in self.tasks:
            raise ValueError(f"Upstream task not found: {upstream_task_id}")
        if downstream_task_id not in self.tasks:
            raise ValueError(f"Downstream task not found: {downstream_task_id}")
        
        upstream = self.tasks[upstream_task_id]
        downstream = self.tasks[downstream_task_id]
        
        upstream.set_downstream(downstream_task_id)
        downstream.set_upstream(upstream_task_id)
        
        self._validated = False
    
    def validate(self) -> bool:
        """
        Validate DAG structure
        
        Checks for:
        - Cycles (must be acyclic)
        - Orphaned tasks
        - Invalid dependencies
        
        Returns:
            True if valid
        
        Raises:
            ValueError if invalid
        """
        # Check for cycles using DFS
        visited = set()
        rec_stack = set()
        
        def has_cycle(task_id: str) -> bool:
            visited.add(task_id)
            rec_stack.add(task_id)
            
            task = self.tasks[task_id]
            for downstream_id in task.downstream_tasks:
                if downstream_id not in visited:
                    if has_cycle(downstream_id):
                        return True
                elif downstream_id in rec_stack:
                    return True
            
            rec_stack.remove(task_id)
            return False
        
        for task_id in self.tasks:
            if task_id not in visited:
                if has_cycle(task_id):
                    raise ValueError(f"Cycle detected in DAG: {self.dag_id}")
        
        # Verify all dependencies exist
        for task_id, task in self.tasks.items():
            for dep_id in task.upstream_tasks:
                if dep_id not in self.tasks:
                    raise ValueError(f"Unknown dependency: {dep_id} for task {task_id}")
        
        self._validated = True
        return True
    
    def get_task_order(self) -> List[str]:
        """
        Get topological sort of tasks
        
        Returns:
            List of task IDs in execution order
        """
        if not self._validated:
            self.validate()
        
        # Kahn's algorithm for topological sort
        in_degree = {task_id: 0 for task_id in self.tasks}
        
        for task in self.tasks.values():
            for downstream_id in task.downstream_tasks:
                in_degree[downstream_id] += 1
        
        queue = deque([task_id for task_id, degree in in_degree.items() if degree == 0])
        order = []
        
        while queue:
            task_id = queue.popleft()
            order.append(task_id)
            
            task = self.tasks[task_id]
            for downstream_id in task.downstream_tasks:
                in_degree[downstream_id] -= 1
                if in_degree[downstream_id] == 0:
                    queue.append(downstream_id)
        
        if len(order) != len(self.tasks):
            raise ValueError("Cannot determine task order (cycle detected)")
        
        return order
    
    def get_root_tasks(self) -> List[str]:
        """Get tasks with no dependencies"""
        return [
            task_id for task_id, task in self.tasks.items()
            if not task.upstream_tasks
        ]
    
    def get_leaf_tasks(self) -> List[str]:
        """Get tasks with no downstream tasks"""
        return [
            task_id for task_id, task in self.tasks.items()
            if not task.downstream_tasks
        ]


class DependencyResolver:
    """
    Dependency resolver
    
    Determines which tasks are ready to run based on dependencies.
    """
    
    def __init__(self):
        self.task_states: Dict[str, TaskState] = {}
    
    def can_run(self, task: Task, upstream_states: Dict[str, TaskState]) -> bool:
        """
        Check if task can run based on trigger rule
        
        Args:
            task: Task to check
            upstream_states: States of upstream tasks
            
        Returns:
            True if task can run
        """
        if not task.upstream_tasks:
            return True
        
        rule = task.config.trigger_rule
        
        if rule == TriggerRule.ALL_SUCCESS:
            return all(
                upstream_states.get(dep_id) == TaskState.SUCCESS
                for dep_id in task.upstream_tasks
            )
        
        elif rule == TriggerRule.ALL_FAILED:
            return all(
                upstream_states.get(dep_id) == TaskState.FAILED
                for dep_id in task.upstream_tasks
            )
        
        elif rule == TriggerRule.ALL_DONE:
            return all(
                upstream_states.get(dep_id) in [TaskState.SUCCESS, TaskState.FAILED, TaskState.SKIPPED]
                for dep_id in task.upstream_tasks
            )
        
        elif rule == TriggerRule.ONE_SUCCESS:
            return any(
                upstream_states.get(dep_id) == TaskState.SUCCESS
                for dep_id in task.upstream_tasks
            )
        
        elif rule == TriggerRule.ONE_FAILED:
            return any(
                upstream_states.get(dep_id) == TaskState.FAILED
                for dep_id in task.upstream_tasks
            )
        
        elif rule == TriggerRule.NONE_FAILED:
            return not any(
                upstream_states.get(dep_id) == TaskState.FAILED
                for dep_id in task.upstream_tasks
            )
        
        elif rule == TriggerRule.NONE_SKIPPED:
            return not any(
                upstream_states.get(dep_id) == TaskState.SKIPPED
                for dep_id in task.upstream_tasks
            )
        
        elif rule == TriggerRule.DUMMY:
            return True
        
        return False
    
    def get_ready_tasks(self, dag: DAG, task_states: Dict[str, TaskState]) -> List[str]:
        """
        Get tasks ready to run
        
        Args:
            dag: DAG instance
            task_states: Current task states
            
        Returns:
            List of task IDs ready to run
        """
        ready = []
        
        for task_id, task in dag.tasks.items():
            current_state = task_states.get(task_id, TaskState.NONE)
            
            # Skip if already processed
            if current_state not in [TaskState.NONE, TaskState.SCHEDULED]:
                continue
            
            # Get upstream states
            upstream_states = {
                dep_id: task_states.get(dep_id, TaskState.NONE)
                for dep_id in task.upstream_tasks
            }
            
            # Check if ready
            if self.can_run(task, upstream_states):
                ready.append(task_id)
        
        return ready


class ExecutionEngine:
    """
    Task execution engine
    
    Executes tasks with retry logic and timeout handling.
    """
    
    def __init__(self, max_workers: int = 4, use_processes: bool = False):
        self.max_workers = max_workers
        self.use_processes = use_processes
        
        if use_processes:
            self.executor = ProcessPoolExecutor(max_workers=max_workers)
        else:
            self.executor = ThreadPoolExecutor(max_workers=max_workers)
    
    def execute_task(self, task: Task, context: Dict[str, Any]) -> Tuple[TaskState, Any]:
        """
        Execute a single task with retry logic
        
        Args:
            task: Task to execute
            context: Execution context
            
        Returns:
            Tuple of (final_state, result)
        """
        max_retries = task.config.retries
        retry_delay = task.config.retry_delay
        max_retry_delay = task.config.max_retry_delay
        exponential_backoff = task.config.retry_exponential_backoff
        execution_timeout = task.config.execution_timeout
        
        for attempt in range(max_retries + 1):
            try:
                # Submit task execution
                future = self.executor.submit(task.execute, context)
                
                # Wait with timeout
                timeout_seconds = execution_timeout.total_seconds() if execution_timeout else None
                result = future.result(timeout=timeout_seconds)
                
                # Success
                if task.config.on_success_callback:
                    task.config.on_success_callback(context)
                
                return (TaskState.SUCCESS, result)
                
            except Exception as e:
                logger.error(f"Task {task.task_id} failed (attempt {attempt + 1}/{max_retries + 1}): {e}")
                
                # Last attempt
                if attempt == max_retries:
                    if task.config.on_failure_callback:
                        task.config.on_failure_callback(context)
                    return (TaskState.FAILED, str(e))
                
                # Retry callback
                if task.config.on_retry_callback:
                    task.config.on_retry_callback(context)
                
                # Calculate retry delay
                delay = retry_delay.total_seconds()
                if exponential_backoff:
                    delay = min(delay * (2 ** attempt), max_retry_delay.total_seconds())
                
                logger.info(f"Retrying task {task.task_id} in {delay}s")
                time.sleep(delay)
        
        return (TaskState.FAILED, None)
    
    def shutdown(self, wait: bool = True):
        """Shutdown executor"""
        self.executor.shutdown(wait=wait)


class TaskScheduler:
    """
    Task scheduler
    
    Schedules DAG runs based on cron expressions.
    """
    
    def __init__(self):
        self.schedules: Dict[str, croniter] = {}
    
    def add_dag(self, dag_id: str, schedule_interval: str, start_date: datetime):
        """Add DAG to scheduler"""
        if schedule_interval:
            self.schedules[dag_id] = croniter(schedule_interval, start_date)
    
    def get_next_execution(self, dag_id: str) -> Optional[datetime]:
        """Get next execution time for DAG"""
        if dag_id not in self.schedules:
            return None
        
        return self.schedules[dag_id].get_next(datetime)
    
    def should_trigger(self, dag_id: str, current_time: datetime) -> bool:
        """Check if DAG should trigger"""
        if dag_id not in self.schedules:
            return False
        
        next_execution = self.get_next_execution(dag_id)
        return next_execution and next_execution <= current_time


class SensorOperator:
    """
    Sensor operator for external triggers
    
    Waits for external conditions before proceeding.
    """
    
    @staticmethod
    def file_sensor(filepath: str) -> Callable:
        """
        Create file existence sensor
        
        Args:
            filepath: Path to check
            
        Returns:
            Sensor callable
        """
        def sensor(context: Dict[str, Any]) -> bool:
            return Path(filepath).exists()
        return sensor
    
    @staticmethod
    def sql_sensor(conn_id: str, sql: str) -> Callable:
        """
        Create SQL sensor
        
        Args:
            conn_id: Connection ID
            sql: SQL query (should return boolean or count)
            
        Returns:
            Sensor callable
        """
        from sqlalchemy import create_engine, text
        
        def sensor(context: Dict[str, Any]) -> bool:
            connection_string = context.get('connections', {}).get(conn_id)
            if not connection_string:
                return False
            
            engine = create_engine(connection_string)
            with engine.connect() as conn:
                result = conn.execute(text(sql))
                row = result.fetchone()
                return bool(row[0]) if row else False
        
        return sensor
    
    @staticmethod
    def http_sensor(url: str, response_check: Callable[[Any], bool] = None) -> Callable:
        """
        Create HTTP sensor
        
        Args:
            url: URL to check
            response_check: Function to validate response
            
        Returns:
            Sensor callable
        """
        import requests
        
        def sensor(context: Dict[str, Any]) -> bool:
            try:
                response = requests.get(url)
                response.raise_for_status()
                
                if response_check:
                    return response_check(response)
                
                return True
            except Exception:
                return False
        
        return sensor
    
    @staticmethod
    def time_sensor(target_time: datetime) -> Callable:
        """
        Create time-based sensor
        
        Args:
            target_time: Time to wait for
            
        Returns:
            Sensor callable
        """
        def sensor(context: Dict[str, Any]) -> bool:
            return datetime.utcnow() >= target_time
        return sensor


class TriggerManager:
    """
    Webhook and event-driven trigger manager
    
    Handles external triggers for DAG execution.
    """
    
    def __init__(self):
        self.triggers: Dict[str, List[Callable]] = defaultdict(list)
        self._lock = threading.Lock()
    
    def register_trigger(self, event_type: str, dag_id: str, callback: Callable):
        """
        Register a trigger for a DAG
        
        Args:
            event_type: Type of event
            dag_id: DAG to trigger
            callback: Callback function
        """
        with self._lock:
            self.triggers[event_type].append({
                'dag_id': dag_id,
                'callback': callback
            })
    
    def fire_trigger(self, event_type: str, payload: Dict[str, Any]) -> List[str]:
        """
        Fire all triggers for an event
        
        Args:
            event_type: Event type
            payload: Event payload
            
        Returns:
            List of triggered DAG IDs
        """
        triggered_dags = []
        
        with self._lock:
            for trigger in self.triggers.get(event_type, []):
                try:
                    if trigger['callback'](payload):
                        triggered_dags.append(trigger['dag_id'])
                except Exception as e:
                    logger.error(f"Trigger callback failed: {e}")
        
        return triggered_dags
    
    def webhook_trigger(self, dag_id: str, payload: Dict[str, Any]) -> str:
        """
        Trigger DAG via webhook
        
        Args:
            dag_id: DAG ID
            payload: Webhook payload
            
        Returns:
            Run ID
        """
        run_id = f"webhook_{uuid.uuid4()}"
        logger.info(f"Webhook triggered DAG {dag_id}: {run_id}")
        return run_id


class DAGOrchestrator:
    """
    Main DAG orchestrator
    
    Manages DAG execution, scheduling, and monitoring.
    """
    
    def __init__(self, db_uri: str = "sqlite:///dag_orchestrator.db",
                 max_workers: int = 4):
        """
        Initialize orchestrator
        
        Args:
            db_uri: Database connection string
            max_workers: Maximum parallel workers
        """
        self.engine = create_engine(db_uri)
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        
        self.dags: Dict[str, DAG] = {}
        self.scheduler = TaskScheduler()
        self.dependency_resolver = DependencyResolver()
        self.execution_engine = ExecutionEngine(max_workers=max_workers)
        self.trigger_manager = TriggerManager()
        
        self._running = False
        self._scheduler_thread = None
    
    def register_dag(self, dag: DAG):
        """
        Register a DAG
        
        Args:
            dag: DAG to register
        """
        # Validate DAG
        dag.validate()
        
        # Store in memory
        self.dags[dag.dag_id] = dag
        
        # Store in database
        session = self.Session()
        try:
            dag_model = DAGModel(
                dag_id=dag.dag_id,
                description=dag.config.description,
                schedule_interval=dag.config.schedule_interval,
                start_date=dag.config.start_date,
                end_date=dag.config.end_date,
                max_active_runs=dag.config.max_active_runs,
                concurrency=dag.config.concurrency,
                tags=dag.config.tags,
                default_args=dag.config.default_args
            )
            
            session.merge(dag_model)
            session.commit()
            
            # Add to scheduler
            if dag.config.schedule_interval:
                self.scheduler.add_dag(
                    dag.dag_id,
                    dag.config.schedule_interval,
                    dag.config.start_date
                )
            
            logger.info(f"Registered DAG: {dag.dag_id}")
            
        finally:
            session.close()
    
    def trigger_dag(self, dag_id: str, execution_date: Optional[datetime] = None,
                   conf: Dict[str, Any] = None, external_trigger: bool = True) -> str:
        """
        Manually trigger a DAG run
        
        Args:
            dag_id: DAG ID
            execution_date: Execution date
            conf: Run configuration
            external_trigger: Whether triggered externally
            
        Returns:
            Run ID
        """
        if dag_id not in self.dags:
            raise ValueError(f"DAG not found: {dag_id}")
        
        execution_date = execution_date or datetime.utcnow()
        run_id = f"{dag_id}_{execution_date.strftime('%Y%m%dT%H%M%S')}"
        
        session = self.Session()
        try:
            dag_run = DAGRun(
                dag_id=dag_id,
                run_id=run_id,
                execution_date=execution_date,
                external_trigger=external_trigger,
                conf=conf or {}
            )
            
            session.add(dag_run)
            session.commit()
            
            logger.info(f"Triggered DAG run: {run_id}")
            
            # Execute DAG
            self._execute_dag_run(run_id)
            
            return run_id
            
        finally:
            session.close()
    
    def _execute_dag_run(self, run_id: str):
        """Execute a DAG run"""
        session = self.Session()
        try:
            # Get run
            dag_run = session.query(DAGRun).filter_by(run_id=run_id).first()
            if not dag_run:
                raise ValueError(f"DAG run not found: {run_id}")
            
            dag = self.dags.get(dag_run.dag_id)
            if not dag:
                raise ValueError(f"DAG not found: {dag_run.dag_id}")
            
            # Update run state
            dag_run.start_date = datetime.utcnow()
            dag_run.state = DAGState.RUNNING
            session.commit()
            
            # Track task states
            task_states: Dict[str, TaskState] = {
                task_id: TaskState.NONE for task_id in dag.tasks
            }
            
            # Create context
            context = {
                'dag_id': dag.dag_id,
                'run_id': run_id,
                'execution_date': dag_run.execution_date,
                'conf': dag_run.conf,
                'connections': {},  # Add connection info
                'smtp_config': {}  # Add SMTP config
            }
            
            # Execute tasks
            completed = set()
            failed = set()
            
            while len(completed) + len(failed) < len(dag.tasks):
                # Get ready tasks
                ready_tasks = self.dependency_resolver.get_ready_tasks(dag, task_states)
                
                if not ready_tasks:
                    # No tasks ready, check if stuck
                    if not any(state == TaskState.RUNNING for state in task_states.values()):
                        # Stuck - mark remaining as upstream failed
                        for task_id, state in task_states.items():
                            if state == TaskState.NONE:
                                task_states[task_id] = TaskState.UPSTREAM_FAILED
                        break
                    
                    # Wait for running tasks
                    time.sleep(1)
                    continue
                
                # Execute ready tasks in parallel
                futures = {}
                for task_id in ready_tasks:
                    if task_states[task_id] != TaskState.RUNNING:
                        task = dag.tasks[task_id]
                        task_states[task_id] = TaskState.RUNNING
                        
                        # Create task instance
                        task_instance = TaskInstance(
                            task_id=task_id,
                            dag_id=dag.dag_id,
                            run_id=run_id,
                            execution_date=dag_run.execution_date,
                            start_date=datetime.utcnow(),
                            state=TaskState.RUNNING,
                            operator=task.config.operator
                        )
                        session.add(task_instance)
                        session.commit()
                        
                        # Submit execution
                        future = self.execution_engine.executor.submit(
                            self.execution_engine.execute_task,
                            task,
                            context
                        )
                        futures[future] = (task_id, task_instance.id)
                
                # Wait for completions
                for future in as_completed(futures):
                    task_id, instance_id = futures[future]
                    
                    try:
                        state, result = future.result()
                        task_states[task_id] = state
                        
                        # Update task instance
                        task_instance = session.query(TaskInstance).filter_by(
                            id=instance_id
                        ).first()
                        
                        if task_instance:
                            task_instance.end_date = datetime.utcnow()
                            task_instance.state = state
                            if task_instance.start_date:
                                duration = (task_instance.end_date - task_instance.start_date).total_seconds()
                                task_instance.duration = duration
                            session.commit()
                        
                        if state == TaskState.SUCCESS:
                            completed.add(task_id)
                            logger.info(f"Task {task_id} completed successfully")
                        else:
                            failed.add(task_id)
                            logger.error(f"Task {task_id} failed")
                        
                    except Exception as e:
                        logger.error(f"Task {task_id} execution error: {e}")
                        task_states[task_id] = TaskState.FAILED
                        failed.add(task_id)
            
            # Update run state
            dag_run.end_date = datetime.utcnow()
            if failed:
                dag_run.state = DAGState.FAILED
            else:
                dag_run.state = DAGState.SUCCESS
            
            session.commit()
            
            logger.info(f"DAG run {run_id} completed: {dag_run.state.value}")
            
        except Exception as e:
            logger.error(f"DAG run {run_id} failed: {e}")
            if dag_run:
                dag_run.state = DAGState.FAILED
                dag_run.end_date = datetime.utcnow()
                session.commit()
        finally:
            session.close()
    
    def start_scheduler(self):
        """Start background scheduler"""
        if self._running:
            return
        
        self._running = True
        self._scheduler_thread = threading.Thread(target=self._scheduler_loop, daemon=True)
        self._scheduler_thread.start()
        logger.info("Scheduler started")
    
    def _scheduler_loop(self):
        """Scheduler main loop"""
        while self._running:
            current_time = datetime.utcnow()
            
            # Check each DAG
            for dag_id in self.dags:
                if self.scheduler.should_trigger(dag_id, current_time):
                    try:
                        self.trigger_dag(dag_id, execution_date=current_time, external_trigger=False)
                    except Exception as e:
                        logger.error(f"Failed to trigger DAG {dag_id}: {e}")
            
            # Sleep
            time.sleep(60)  # Check every minute
    
    def stop_scheduler(self):
        """Stop scheduler"""
        self._running = False
        if self._scheduler_thread:
            self._scheduler_thread.join(timeout=5)
        logger.info("Scheduler stopped")
    
    def pause_dag(self, dag_id: str):
        """Pause a DAG"""
        session = self.Session()
        try:
            dag_model = session.query(DAGModel).filter_by(dag_id=dag_id).first()
            if dag_model:
                dag_model.is_paused = True
                session.commit()
                logger.info(f"Paused DAG: {dag_id}")
        finally:
            session.close()
    
    def unpause_dag(self, dag_id: str):
        """Unpause a DAG"""
        session = self.Session()
        try:
            dag_model = session.query(DAGModel).filter_by(dag_id=dag_id).first()
            if dag_model:
                dag_model.is_paused = False
                session.commit()
                logger.info(f"Unpaused DAG: {dag_id}")
        finally:
            session.close()
    
    def get_dag_runs(self, dag_id: str, limit: int = 10) -> List[DAGRun]:
        """Get recent DAG runs"""
        session = self.Session()
        try:
            return session.query(DAGRun).filter_by(
                dag_id=dag_id
            ).order_by(DAGRun.execution_date.desc()).limit(limit).all()
        finally:
            session.close()
    
    def get_task_instances(self, run_id: str) -> List[TaskInstance]:
        """Get task instances for a run"""
        session = self.Session()
        try:
            return session.query(TaskInstance).filter_by(run_id=run_id).all()
        finally:
            session.close()
    
    def shutdown(self):
        """Shutdown orchestrator"""
        self.stop_scheduler()
        self.execution_engine.shutdown()
        logger.info("Orchestrator shutdown complete")


# Example usage
def example_usage():
    """Demonstrate pipeline orchestration"""
    
    # Initialize orchestrator
    orchestrator = DAGOrchestrator(
        db_uri="sqlite:///pipelines.db",
        max_workers=4
    )
    
    # Define tasks
    def extract_data(**kwargs):
        print("Extracting data...")
        return {"records": 1000}
    
    def transform_data(**kwargs):
        print("Transforming data...")
        return {"transformed": 950}
    
    def load_data(**kwargs):
        print("Loading data...")
        return {"loaded": 950}
    
    # Create tasks
    extract_task = Task(TaskConfig(
        task_id="extract",
        operator="python",
        operator_params={'python_callable': extract_data, 'provide_context': True}
    ))
    
    transform_task = Task(TaskConfig(
        task_id="transform",
        operator="python",
        operator_params={'python_callable': transform_data},
        dependencies=["extract"]
    ))
    
    load_task = Task(TaskConfig(
        task_id="load",
        operator="python",
        operator_params={'python_callable': load_data},
        dependencies=["transform"]
    ))
    
    # Create DAG
    dag_config = DAGConfig(
        dag_id="etl_pipeline",
        description="ETL pipeline for agricultural data",
        schedule_interval=ScheduleInterval.DAILY.value,
        start_date=datetime(2024, 1, 1),
        tags=["etl", "agriculture"]
    )
    
    dag = DAG(dag_config)
    dag.add_task(extract_task)
    dag.add_task(transform_task)
    dag.add_task(load_task)
    
    # Register DAG
    orchestrator.register_dag(dag)
    
    # Trigger DAG
    run_id = orchestrator.trigger_dag("etl_pipeline")
    print(f"Triggered run: {run_id}")
    
    # Start scheduler
    orchestrator.start_scheduler()
    
    # Keep running
    try:
        time.sleep(10)
    finally:
        orchestrator.shutdown()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    example_usage()
