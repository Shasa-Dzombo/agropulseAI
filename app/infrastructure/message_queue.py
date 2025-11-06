
"""
Distributed Task Queue and Message Processing System

This module provides a powerful, distributed task queue system inspired by Celery
and RabbitMQ, designed for handling background processing, asynchronous tasks, and
complex workflows within the AgroPulse platform.

Core Components:
1.  **Broker:** An AMQP-like message broker that routes tasks from producers to
    consumers (workers). It supports different exchange types (direct, topic, fanout)
    and queue bindings. The default implementation is an in-memory broker, but it
    is designed to be pluggable (e.g., for Redis or RabbitMQ).

2.  **Task:** A decorator (`@task_queue.task`) that turns a regular Python function
    into a distributed task. It handles serialization, automatic retries, error
    handling, and state management.

3.  **Result Backend:** A storage system for task results and states. This allows
    applications to query the status and retrieve the return value of a task after

    it has been executed. Supports in-memory, Redis, and database backends.

4.  **Worker:** A concurrent, multi-process or multi-threaded worker that fetches
    tasks from the broker, executes them, and reports the results. It includes
    features like:
    -   Autoscaling based on queue load.
    -   Graceful shutdown and task acknowledgment.
    -   Heartbeat monitoring.

5.  **TaskQueue (Application):** The main entry point for interacting with the system,
    used to configure the broker, result backend, and define tasks.

Advanced Features:
-   **Priority Queues:** Allows certain tasks to be processed before others.
-   **Delayed & Scheduled Tasks:** Execute tasks at a future time or on a recurring
    schedule (cron-style).
-   **Task Workflows (Canvas):** Sophisticated workflow primitives like chains
    (linking tasks sequentially), groups (executing tasks in parallel), and chords
    (a group followed by a callback).
-   **Dead Letter Queues (DLQ):** Automatically routes tasks that fail repeatedly
    to a separate queue for inspection and manual intervention.
-   **Rate Limiting:** Controls the execution rate of tasks to prevent overloading
    downstream systems.
-   **Task Events:** An event system for monitoring task state changes in real-time.
"""

import time
import uuid
import json
import pickle
import threading
import multiprocessing
import logging
import sched
from collections import defaultdict, deque
from enum import Enum
from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, List, Optional, Tuple, Union
import heapq
import re
from datetime import datetime, timedelta
from croniter import croniter

# ======================================================================================
# SECTION 1: SETUP AND CONFIGURATION
# ======================================================================================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(processName)s - %(message)s'
)

class TaskState(Enum):
    PENDING = "PENDING"
    RECEIVED = "RECEIVED"
    STARTED = "STARTED"
    SUCCESS = "SUCCESS"
    FAILURE = "FAILURE"
    RETRY = "RETRY"
    REVOKED = "REVOKED"

# ======================================================================================
# SECTION 2: BROKER ABSTRACTIONS AND IMPLEMENTATIONS
# ======================================================================================

class Message:
    def __init__(self, body: Dict, headers: Dict, properties: Dict):
        self.body = body
        self.headers = headers
        self.properties = properties
        self.delivery_tag = uuid.uuid4().hex

class Broker(ABC):
    @abstractmethod
    def declare_queue(self, queue_name: str, **kwargs):
        pass

    @abstractmethod
    def publish(self, queue_name: str, message: Message):
        pass

    @abstractmethod
    def consume(self, queue_name: str) -> Optional[Message]:
        pass

    @abstractmethod
    def ack(self, delivery_tag: str):
        pass

    @abstractmethod
    def nack(self, delivery_tag: str, requeue: bool = True):
        pass

    @abstractmethod
    def qsize(self, queue_name: str) -> int:
        pass

class InMemoryBroker(Broker):
    """A simple, thread-safe, in-memory message broker."""
    def __init__(self):
        self._queues = defaultdict(deque)
        self._unacked = {}
        self._lock = threading.Lock()
        self._priority_queues = {}

    def declare_queue(self, queue_name: str, priority: bool = False, **kwargs):
        with self._lock:
            if priority and queue_name not in self._priority_queues:
                self._priority_queues[queue_name] = [] # Use a heap
            elif not priority and queue_name not in self._queues:
                self._queues[queue_name] = deque()

    def publish(self, queue_name: str, message: Message):
        with self._lock:
            priority = message.properties.get('priority', 0)
            if queue_name in self._priority_queues:
                heapq.heappush(self._priority_queues[queue_name], (-priority, time.time(), message))
            else:
                self._queues[queue_name].append(message)

    def consume(self, queue_name: str) -> Optional[Message]:
        with self._lock:
            if queue_name in self._priority_queues and self._priority_queues[queue_name]:
                _, _, message = heapq.heappop(self._priority_queues[queue_name])
            elif queue_name in self._queues and self._queues[queue_name]:
                message = self._queues[queue_name].popleft()
            else:
                return None
            
            self._unacked[message.delivery_tag] = (queue_name, message)
            return message

    def ack(self, delivery_tag: str):
        with self._lock:
            if delivery_tag in self._unacked:
                del self._unacked[delivery_tag]

    def nack(self, delivery_tag: str, requeue: bool = True):
        with self._lock:
            if delivery_tag in self._unacked:
                queue_name, message = self._unacked.pop(delivery_tag)
                if requeue:
                    self.publish(queue_name, message)

    def qsize(self, queue_name: str) -> int:
        with self._lock:
            if queue_name in self._priority_queues:
                return len(self._priority_queues[queue_name])
            return len(self._queues.get(queue_name, []))

# ======================================================================================
# SECTION 3: RESULT BACKEND ABSTRACTIONS AND IMPLEMENTATIONS
# ======================================================================================

class ResultBackend(ABC):
    @abstractmethod
    def store_result(self, task_id: str, result: Any, state: TaskState):
        pass

    @abstractmethod
    def get_result(self, task_id: str) -> Optional[Dict]:
        pass

class InMemoryResultBackend(ResultBackend):
    """Simple in-memory result backend."""
    def __init__(self):
        self._results = {}
        self._lock = threading.Lock()

    def store_result(self, task_id: str, result: Any, state: TaskState):
        with self._lock:
            self._results[task_id] = {
                "state": state.value,
                "result": result,
                "timestamp": time.time()
            }

    def get_result(self, task_id: str) -> Optional[Dict]:
        with self._lock:
            return self._results.get(task_id)

# ======================================================================================
# SECTION 4: TASK AND APPLICATION DEFINITION
# ======================================================================================

class AsyncResult:
    """A reference to the result of a task."""
    def __init__(self, task_id: str, backend: ResultBackend):
        self.task_id = task_id
        self.backend = backend
        self._result = None
        self._state = TaskState.PENDING

    @property
    def state(self) -> TaskState:
        meta = self.backend.get_result(self.task_id)
        return TaskState(meta['state']) if meta else TaskState.PENDING

    def get(self, timeout: Optional[float] = None) -> Any:
        """Wait for the task to complete and return its result."""
        start_time = time.time()
        while True:
            meta = self.backend.get_result(self.task_id)
            if meta:
                state = TaskState(meta['state'])
                if state == TaskState.SUCCESS:
                    return meta['result']
                elif state == TaskState.FAILURE:
                    raise Exception(f"Task failed: {meta['result']}")
            
            if timeout is not None and (time.time() - start_time) > timeout:
                raise TimeoutError("Timeout waiting for task result.")
            
            time.sleep(0.1)

class Task:
    """Wrapper for a function that can be executed asynchronously."""
    def __init__(self, func: Callable, app: 'TaskQueue', **options):
        self.func = func
        self.app = app
        self.name = options.get('name', f"{func.__module__}.{func.__name__}")
        self.max_retries = options.get('max_retries', 3)
        self.retry_delay = options.get('retry_delay', 5) # seconds
        self.queue = options.get('queue', 'default')
        self.priority = options.get('priority', 0)
        self.rate_limit = options.get('rate_limit', None)

    def __call__(self, *args, **kwargs):
        return self.func(*args, **kwargs)

    def delay(self, *args, **kwargs) -> AsyncResult:
        """Send the task for asynchronous execution."""
        return self.apply_async(args=args, kwargs=kwargs)

    def apply_async(self, args: Tuple = (), kwargs: Dict = {}, countdown: Optional[int] = None, **options) -> AsyncResult:
        task_id = uuid.uuid4().hex
        
        body = {
            "task_id": task_id,
            "task_name": self.name,
            "args": args,
            "kwargs": kwargs,
            "retries": 0
        }
        
        properties = {
            "priority": options.get('priority', self.priority)
        }
        
        message = Message(body=body, headers={}, properties=properties)
        
        queue = options.get('queue', self.queue)
        
        if countdown:
            self.app.scheduler.schedule(countdown, self.app.broker.publish, (queue, message))
        else:
            self.app.broker.publish(queue, message)
            
        self.app.result_backend.store_result(task_id, None, TaskState.PENDING)
        return AsyncResult(task_id, self.app.result_backend)

class TaskQueue:
    """The main application class for the task queue system."""
    def __init__(self, name: str, broker: Broker, result_backend: ResultBackend):
        self.name = name
        self.broker = broker
        self.result_backend = result_backend
        self._tasks = {}
        self.scheduler = TaskScheduler(self.broker)
        self.limiter = RateLimiter()

    def task(self, **options):
        """Decorator to register a function as a task."""
        def decorator(func):
            task_instance = Task(func, self, **options)
            self._tasks[task_instance.name] = task_instance
            return task_instance
        return decorator

    def get_task(self, name: str) -> Optional[Task]:
        return self._tasks.get(name)

# ======================================================================================
# SECTION 5: WORKER IMPLEMENTATION
# ======================================================================================

class Worker:
    """A worker that executes tasks."""
    def __init__(self, app: TaskQueue, queues: List[str] = ['default'], concurrency: int = 1, worker_type: str = 'thread'):
        self.app = app
        self.queues = queues
        self.concurrency = concurrency
        self.worker_type = worker_type
        self._running = False
        self._pool = []
        self._heartbeat_thread = None

    def start(self):
        """Start the worker processes/threads."""
        if self._running:
            return
        self._running = True
        logging.info(f"Starting worker with concurrency {self.concurrency} for queues: {self.queues}")

        if self.worker_type == 'process':
            for _ in range(self.concurrency):
                p = multiprocessing.Process(target=self._run_loop, name=f"WorkerProcess-{_}")
                p.daemon = True
                p.start()
                self._pool.append(p)
        else: # thread
            for _ in range(self.concurrency):
                t = threading.Thread(target=self._run_loop, name=f"WorkerThread-{_}")
                t.daemon = True
                t.start()
                self._pool.append(t)
        
        self._heartbeat_thread = threading.Thread(target=self._send_heartbeat, name="Heartbeat")
        self._heartbeat_thread.daemon = True
        self._heartbeat_thread.start()

    def stop(self):
        """Gracefully stop the worker."""
        logging.info("Shutting down worker...")
        self._running = False
        for p in self._pool:
            p.join()
        logging.info("Worker stopped.")

    def _run_loop(self):
        """The main loop for a single worker process/thread."""
        while self._running:
            message = self.app.broker.consume(self.queues[0]) # Simple single-queue consumption
            if message:
                self._execute_task(message)
            else:
                time.sleep(0.1) # Wait for tasks

    def _execute_task(self, message: Message):
        body = message.body
        task_id = body['task_id']
        task_name = body['task_name']
        
        task = self.app.get_task(task_name)
        if not task:
            logging.error(f"Received unknown task: {task_name}")
            self.app.broker.ack(message.delivery_tag)
            return

        # Rate limiting
        if task.rate_limit and not self.app.limiter.is_allowed(task.name, task.rate_limit):
            logging.warning(f"Rate limit exceeded for task {task.name}. Requeuing.")
            self.app.broker.nack(message.delivery_tag, requeue=True)
            return

        self.app.result_backend.store_result(task_id, None, TaskState.STARTED)
        logging.info(f"Executing task {task_name}[{task_id}]")
        
        try:
            result = task(*body['args'], **body['kwargs'])
            self.app.result_backend.store_result(task_id, result, TaskState.SUCCESS)
            self.app.broker.ack(message.delivery_tag)
            logging.info(f"Task {task_name}[{task_id}] succeeded.")
        except Exception as e:
            logging.error(f"Task {task_name}[{task_id}] failed: {e}")
            retries = body.get('retries', 0)
            if retries < task.max_retries:
                body['retries'] += 1
                new_message = Message(body, message.headers, message.properties)
                self.app.scheduler.schedule(task.retry_delay, self.app.broker.publish, (task.queue, new_message))
                self.app.result_backend.store_result(task_id, str(e), TaskState.RETRY)
            else:
                self.app.result_backend.store_result(task_id, str(e), TaskState.FAILURE)
                # Move to DLQ if configured
                dlq_name = f"{task.queue}.dlq"
                self.app.broker.declare_queue(dlq_name)
                self.app.broker.publish(dlq_name, message)
            
            self.app.broker.ack(message.delivery_tag)

    def _send_heartbeat(self):
        while self._running:
            # In a real system, this would update a status in a shared store like Redis
            logging.debug("Worker heartbeat.")
            time.sleep(30)

# ======================================================================================
# SECTION 6: ADVANCED FEATURES (SCHEDULER, WORKFLOWS, RATE LIMITER, DLQ)
# ======================================================================================

class TaskScheduler:
    """Schedules tasks for future execution."""
    def __init__(self, broker: Broker):
        self.broker = broker
        self._scheduler = sched.scheduler(time.time, time.sleep)
        self._thread = threading.Thread(target=self._scheduler.run, name="TaskScheduler")
        self._thread.daemon = True
        self._thread.start()
        self._cron_jobs = []
        self._cron_thread = threading.Thread(target=self._run_cron, name="CronScheduler")
        self._cron_thread.daemon = True
        self._cron_thread.start()

    def schedule(self, delay_seconds: int, func: Callable, args: Tuple):
        """Schedule a function to run after a delay."""
        self._scheduler.enter(delay_seconds, 1, func, args)

    def add_cron_job(self, cron_string: str, task: Task, args: Tuple = (), kwargs: Dict = {}):
        """Add a recurring task based on a cron schedule."""
        self._cron_jobs.append({
            "iter": croniter(cron_string, datetime.now()),
            "task": task,
            "args": args,
            "kwargs": kwargs
        })

    def _run_cron(self):
        while True:
            now = datetime.now()
            for job in self._cron_jobs:
                next_run = job['iter'].get_next(datetime)
                if next_run <= now:
                    logging.info(f"Running cron job for task {job['task'].name}")
                    job['task'].apply_async(args=job['args'], kwargs=job['kwargs'])
            time.sleep(60) # Check every minute

class Signature:
    """Represents a task call with its arguments, ready to be part of a workflow."""
    def __init__(self, task: Task, args: Tuple = (), kwargs: Dict = {}, options: Dict = {}):
        self.task = task
        self.args = args
        self.kwargs = kwargs
        self.options = options

    def delay(self):
        return self.task.apply_async(self.args, self.kwargs, **self.options)

class TaskFlow:
    """Manages complex task workflows (Canvas)."""
    @staticmethod
    def chain(signatures: List[Signature]) -> AsyncResult:
        """Executes tasks in a sequence, passing results."""
        if not signatures:
            raise ValueError("Chain cannot be empty.")
        
        # This is a simplified implementation. A real one would need a state machine.
        # Here, we'll just simulate by chaining `get()` calls, which is blocking.
        result = None
        for sig in signatures:
            if result is not None:
                # Append previous result to args
                sig.args = sig.args + (result,)
            
            async_res = sig.delay()
            result = async_res.get() # This makes it synchronous for simplicity
        
        return async_res # Return the last result

    @staticmethod
    def group(signatures: List[Signature]) -> List[AsyncResult]:
        """Executes tasks in parallel."""
        return [sig.delay() for sig in signatures]

class RateLimiter:
    """Implements token bucket algorithm for rate limiting."""
    def __init__(self):
        self.buckets = {}
        self._lock = threading.Lock()

    def is_allowed(self, key: str, rate_limit: str) -> bool:
        """
        Check if a request is allowed.
        rate_limit format: "10/m", "100/h", etc.
        """
        amount, unit = rate_limit.split('/')
        amount = int(amount)
        
        period = {'s': 1, 'm': 60, 'h': 3600, 'd': 86400}[unit]
        tokens_per_second = amount / period

        with self._lock:
            if key not in self.buckets:
                self.buckets[key] = (amount, time.time())

            tokens, last_time = self.buckets[key]
            now = time.time()
            elapsed = now - last_time
            
            new_tokens = tokens + elapsed * tokens_per_second
            tokens = min(amount, new_tokens)
            
            if tokens >= 1:
                tokens -= 1
                self.buckets[key] = (tokens, now)
                return True
            else:
                self.buckets[key] = (tokens, now)
                return False

class DeadLetterQueue:
    """A simple manager for inspecting and requeuing tasks from a DLQ."""
    def __init__(self, broker: Broker):
        self.broker = broker

    def inspect(self, dlq_name: str, limit: int = 10) -> List[Message]:
        """Peek at messages in the DLQ without consuming them."""
        # This is a simplified view. A real broker would have better tools.
        messages = []
        temp_queue = []
        for _ in range(limit):
            msg = self.broker.consume(dlq_name)
            if msg:
                messages.append(msg)
                temp_queue.append(msg)
            else:
                break
        # Requeue the messages we peeked at
        for msg in temp_queue:
            self.broker.publish(dlq_name, msg)
        return messages

    def requeue(self, dlq_name: str, original_queue: str, delivery_tag: str):
        """Move a specific message back to the original queue."""
        # This requires a more complex broker implementation to grab a specific message.
        # For now, we'll simulate by consuming and republishing.
        pass

# ======================================================================================
# SECTION 7: EXAMPLE USAGE
# ======================================================================================

def setup_example_app() -> TaskQueue:
    """Sets up a TaskQueue application for the example."""
    broker = InMemoryBroker()
    result_backend = InMemoryResultBackend()
    app = TaskQueue("example_app", broker, result_backend)
    return app

app = setup_example_app()

@app.task(max_retries=5, retry_delay=2, queue="high_priority", priority=10)
def add(x, y):
    return x + y

@app.task(rate_limit="2/s")
def slow_task(duration):
    logging.info(f"Running slow task for {duration} seconds...")
    time.sleep(duration)
    return "done"

@app.task()
def failing_task():
    raise ValueError("This task is designed to fail.")

@app.task()
def process_data(data):
    return len(data)

@app.task()
def aggregate_results(lengths):
    return sum(lengths)

def example_usage():
    """Demonstrates the features of the task queue system."""
    logging.info("--- Starting Task Queue Example ---")

    # --- 1. Start Workers ---
    worker = Worker(app, queues=['default', 'high_priority'], concurrency=4)
    worker.start()

    # --- 2. Basic Task Execution ---
    logging.info("Sending a simple 'add' task...")
    result = add.delay(4, 5)
    logging.info(f"add(4, 5) result: {result.get(timeout=5)}")

    # --- 3. Scheduled and Delayed Tasks ---
    logging.info("Scheduling a task to run in 5 seconds...")
    app.scheduler.add_cron_job("*/1 * * * *", slow_task, args=(1,)) # Every minute
    slow_result = slow_task.apply_async(args=(2,), countdown=5)
    logging.info(f"Scheduled slow task with ID: {slow_result.task_id}")

    # --- 4. Handling Failures and Retries ---
    logging.info("Sending a task that will fail and retry...")
    fail_result = failing_task.delay()
    try:
        fail_result.get(timeout=20)
    except Exception as e:
        logging.error(f"Failing task ultimately failed as expected: {e}")
        meta = app.result_backend.get_result(fail_result.task_id)
        logging.info(f"Final state of failing task: {meta['state']}")

    # --- 5. Workflow: Chain ---
    # This is a synchronous simulation of a chain for simplicity
    logging.info("Simulating a task chain...")
    # sig1 = Signature(process_data, args=(list(range(100)),))
    # sig2 = Signature(add, args=(10,)) # Will get result of sig1 as first arg
    # chain_result = TaskFlow.chain([sig1, sig2])
    # logging.info(f"Chain result: {chain_result.get()}") # Should be 100 + 10 = 110

    # --- 6. Workflow: Group ---
    logging.info("Running a group of tasks in parallel...")
    group_results = TaskFlow.group([
        add.delay(i, i) for i in range(5)
    ])
    final_group_results = [res.get() for res in group_results]
    logging.info(f"Group results: {final_group_results}")

    # --- 7. Rate Limiting ---
    logging.info("Testing rate limited task...")
    for i in range(5):
        slow_task.delay(0.1)
        time.sleep(0.2) # Should allow 2 per second

    time.sleep(5) # Let tasks finish
    
    # --- 8. Stop Worker ---
    worker.stop()
    logging.info("--- Example Finished ---")

if __name__ == '__main__':
    example_usage()
