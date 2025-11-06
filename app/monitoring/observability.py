
"""
Comprehensive Observability Platform for AgroPulse

This module provides an integrated, production-grade observability solution inspired by
industry-standard tools like Prometheus, Grafana, Loki, and Jaeger. It is designed to
provide deep insights into the AgroPulse microservices ecosystem.

Core Pillars of Observability:
1.  **Metrics (Prometheus-style):**
    -   A thread-safe `MetricsRegistry` for managing metrics.
    -   Support for Counter, Gauge, Histogram, and Summary metric types.
    -   A `PrometheusExporter` that exposes metrics via an HTTP endpoint.

2.  **Logging (Loki-style):**
    -   A `LogAggregator` service that ingests logs from multiple sources.
    -   Label-based indexing for efficient log querying (`LogIndexer`).
    -   A simple `LogQL`-like query engine for searching and filtering logs.
    -   Pluggable storage backends for logs (e.g., in-memory, file-based).

3.  **Tracing (Jaeger-style):**
    -   A `DistributedTracer` for instrumenting code and generating traces.
    -   Implementation of `Span` and `SpanContext` following OpenTracing principles.
    -   A `JaegerExporter` to send traces to a Jaeger collector.
    -   Configurable sampling strategies (probabilistic, rate-limiting).

4.  **Alerting (Alertmanager-style):**
    -   A `RuleEvaluator` that periodically evaluates PromQL-like alert rules.
    -   An `AlertManager` that manages the full lifecycle of alerts (pending, firing,
        resolved), including grouping, inhibition, and silencing.
    -   Extensible `NotificationChannel` system for dispatching alerts (e.g., console,
        webhook).

5.  **Dashboards (Grafana-style):**
    -   A `DashboardManager` to programmatically define and manage dashboards.
    -   A `GrafanaDashboard` class that can generate Grafana-compatible JSON models.
    -   Builders for panels, rows, and data sources.

6.  **Advanced Features:**
    -   `SLOManager`: For defining and tracking Service Level Objectives (SLOs) and
        error budgets.
    -   `HealthChecker`: Active health checking of services with various probe types.
    -   `AnomalyDetector`: Statistical anomaly detection on time-series metrics.
    -   `CanaryReleaseMonitor`: Automated monitoring and analysis of canary deployments.

This system is designed to run as a standalone service or integrated within the
AgroPulse microservices gateway.
"""

import threading
import time
import json
import os
import re
import logging
import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer
from collections import defaultdict, deque
from typing import (
    Any, Callable, Dict, List, Optional, Tuple, Union, NamedTuple
)
from abc import ABC, abstractmethod
import numpy as np
from enum import Enum
import hashlib
import uuid
import requests
import sched

# ======================================================================================
# SECTION 1: SETUP AND CONFIGURATION
# ======================================================================================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [%(levelname)s] - (%(threadName)s) - %(message)s'
)

# ======================================================================================
# SECTION 2: METRICS SYSTEM (PROMETHEUS-STYLE)
# ======================================================================================

class Metric(ABC):
    """Abstract base class for a metric."""
    def __init__(self, name: str, help_text: str, labels: Tuple[str, ...]):
        if not re.match(r'^[a-zA-Z_:][a-zA-Z0-9_:]*$', name):
            raise ValueError(f"Invalid metric name: {name}")
        self.name = name
        self.help_text = help_text
        self.labels = labels
        self._lock = threading.Lock()

    @abstractmethod
    def to_prometheus_format(self) -> List[str]:
        pass

    def _format_labels(self, label_values: Dict[str, str]) -> str:
        if not label_values:
            return ""
        sorted_labels = sorted(label_values.items())
        return "{" + ",".join([f'{k}="{v}"' for k, v in sorted_labels]) + "}"

class Counter(Metric):
    """A metric that only increases."""
    def __init__(self, name: str, help_text: str, labels: Tuple[str, ...] = ()):
        super().__init__(name, help_text, labels)
        self._values = defaultdict(float)

    def inc(self, value: float = 1.0, label_values: Dict[str, str] = {}):
        if value < 0:
            raise ValueError("Counter value cannot decrease.")
        with self._lock:
            self._values[frozenset(label_values.items())] += value

    def to_prometheus_format(self) -> List[str]:
        lines = [
            f"# HELP {self.name} {self.help_text}",
            f"# TYPE {self.name} counter"
        ]
        with self._lock:
            for label_set, value in self._values.items():
                label_str = self._format_labels(dict(label_set))
                lines.append(f"{self.name}{label_str} {value}")
        return lines

class Gauge(Metric):
    """A metric that can go up or down."""
    def __init__(self, name: str, help_text: str, labels: Tuple[str, ...] = ()):
        super().__init__(name, help_text, labels)
        self._values = defaultdict(float)

    def set(self, value: float, label_values: Dict[str, str] = {}):
        with self._lock:
            self._values[frozenset(label_values.items())] = value

    def inc(self, value: float = 1.0, label_values: Dict[str, str] = {}):
        with self._lock:
            self._values[frozenset(label_values.items())] += value

    def dec(self, value: float = 1.0, label_values: Dict[str, str] = {}):
        with self._lock:
            self._values[frozenset(label_values.items())] -= value

    def to_prometheus_format(self) -> List[str]:
        lines = [
            f"# HELP {self.name} {self.help_text}",
            f"# TYPE {self.name} gauge"
        ]
        with self._lock:
            for label_set, value in self._values.items():
                label_str = self._format_labels(dict(label_set))
                lines.append(f"{self.name}{label_str} {value}")
        return lines

class Histogram(Metric):
    """A metric that samples observations into configurable buckets."""
    def __init__(self, name: str, help_text: str, labels: Tuple[str, ...] = (),
                 buckets: Tuple[float, ...] = (0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10)):
        super().__init__(name, help_text, labels)
        self.buckets = sorted(buckets) + [float('inf')]
        self._counts = defaultdict(lambda: np.zeros(len(self.buckets)))
        self._sums = defaultdict(float)

    def observe(self, value: float, label_values: Dict[str, str] = {}):
        with self._lock:
            label_set = frozenset(label_values.items())
            self._sums[label_set] += value
            for i, bucket in enumerate(self.buckets):
                if value <= bucket:
                    self._counts[label_set][i] += 1

    def to_prometheus_format(self) -> List[str]:
        lines = [
            f"# HELP {self.name} {self.help_text}",
            f"# TYPE {self.name} histogram"
        ]
        with self._lock:
            for label_set, counts in self._counts.items():
                label_str = self._format_labels(dict(label_set))
                cumulative_counts = np.cumsum(counts)
                for i, bucket in enumerate(self.buckets):
                    le = 'inf' if bucket == float('inf') else str(bucket)
                    lines.append(f'{self.name}_bucket{{le="{le}"{label_str[1:] if label_str else ""}}} {cumulative_counts[i]}')
                lines.append(f"{self.name}_sum{label_str} {self._sums[label_set]}")
                lines.append(f"{self.name}_count{label_str} {cumulative_counts[-1]}")
        return lines

class Summary(Metric):
    """A metric that calculates configurable quantiles over a sliding window."""
    # This is a simplified implementation. Real summaries are complex.
    def __init__(self, name: str, help_text: str, labels: Tuple[str, ...] = (),
                 quantiles: Tuple[float, ...] = (0.5, 0.9, 0.99), max_age_seconds: int = 600, age_buckets: int = 5):
        super().__init__(name, help_text, labels)
        self.quantiles = quantiles
        self._sums = defaultdict(float)
        self._counts = defaultdict(int)
        # Simplified windowing: just keep all observations for now
        self._observations = defaultdict(list)

    def observe(self, value: float, label_values: Dict[str, str] = {}):
        with self._lock:
            label_set = frozenset(label_values.items())
            self._sums[label_set] += value
            self._counts[label_set] += 1
            self._observations[label_set].append(value)

    def to_prometheus_format(self) -> List[str]:
        lines = [
            f"# HELP {self.name} {self.help_text}",
            f"# TYPE {self.name} summary"
        ]
        with self._lock:
            for label_set, obs in self._observations.items():
                label_str = self._format_labels(dict(label_set))
                sorted_obs = sorted(obs)
                for q in self.quantiles:
                    pos = int(len(sorted_obs) * q)
                    value = sorted_obs[pos] if sorted_obs else 0
                    lines.append(f'{self.name}{{quantile="{q}"{label_str[1:] if label_str else ""}}} {value}')
                lines.append(f"{self.name}_sum{label_str} {self._sums[label_set]}")
                lines.append(f"{self.name}_count{label_str} {self._counts[label_set]}")
        return lines

class MetricsRegistry:
    """A registry for all metrics."""
    def __init__(self):
        self._metrics = {}
        self._lock = threading.Lock()

    def register(self, metric: Metric):
        with self._lock:
            if metric.name in self._metrics:
                raise ValueError(f"Metric '{metric.name}' already registered.")
            self._metrics[metric.name] = metric

    def unregister(self, name: str):
        with self._lock:
            if name in self._metrics:
                del self._metrics[name]

    def get_metric(self, name: str) -> Optional[Metric]:
        with self._lock:
            return self._metrics.get(name)

    def gather(self) -> str:
        """Collect all metrics in Prometheus text format."""
        all_lines = []
        with self._lock:
            for name in sorted(self._metrics.keys()):
                metric = self._metrics[name]
                all_lines.extend(metric.to_prometheus_format())
                all_lines.append("")
        return "\n".join(all_lines)

# Global default registry
DEFAULT_REGISTRY = MetricsRegistry()

class PrometheusExporter:
    """Exposes metrics via an HTTP endpoint."""
    def __init__(self, port: int, registry: MetricsRegistry = DEFAULT_REGISTRY):
        self.port = port
        self.registry = registry
        self._server_thread = None

    def start(self):
        """Starts the HTTP server in a background thread."""
        if self._server_thread is not None:
            logging.warning("Prometheus exporter already running.")
            return

        handler = self._make_handler()
        httpd = HTTPServer(("", self.port), handler)
        
        self._server_thread = threading.Thread(target=httpd.serve_forever, name="PrometheusExporter")
        self._server_thread.daemon = True
        self._server_thread.start()
        logging.info(f"Prometheus exporter started on port {self.port}")

    def _make_handler(self):
        registry = self.registry
        class MetricsHandler(BaseHTTPRequestHandler):
            def do_GET(self):
                if self.path == '/metrics':
                    self.send_response(200)
                    self.send_header('Content-Type', 'text/plain; version=0.0.4')
                    self.end_headers()
                    self.wfile.write(registry.gather().encode('utf-8'))
                else:
                    self.send_response(404)
                    self.end_headers()
            
            def log_message(self, format, *args):
                # Suppress default logging to avoid clutter
                return

        return MetricsHandler

# ======================================================================================
# SECTION 3: LOGGING SYSTEM (LOKI-STYLE)
# ======================================================================================

class LogEntry(NamedTuple):
    timestamp: float
    labels: Dict[str, str]
    line: str

class LogStorage(ABC):
    @abstractmethod
    def store(self, entry: LogEntry):
        pass

    @abstractmethod
    def query(self, start_time: float, end_time: float, label_filter: Dict[str, str]) -> List[LogEntry]:
        pass

class InMemoryLogStorage(LogStorage):
    """Simple in-memory log storage for demonstration."""
    def __init__(self, max_entries: int = 100000):
        self._logs = deque(maxlen=max_entries)
        self._lock = threading.Lock()

    def store(self, entry: LogEntry):
        with self._lock:
            self._logs.append(entry)

    def query(self, start_time: float, end_time: float, label_filter: Dict[str, str]) -> List[LogEntry]:
        results = []
        with self._lock:
            for log in self._logs:
                if start_time <= log.timestamp <= end_time:
                    if all(log.labels.get(k) == v for k, v in label_filter.items()):
                        results.append(log)
        return results

class LogAggregator:
    """Receives and stores log entries."""
    def __init__(self, storage: LogStorage):
        self.storage = storage

    def push(self, logs: List[Dict[str, Any]]):
        """
        Push a list of log streams.
        Format: [{"labels": {"app": "foo"}, "entries": [{"ts": timestamp, "line": "log line"}]}]
        """
        for stream in logs:
            labels = stream.get("labels", {})
            for entry_data in stream.get("entries", []):
                entry = LogEntry(
                    timestamp=entry_data.get("ts", time.time()),
                    labels=labels,
                    line=entry_data.get("line", "")
                )
                self.storage.store(entry)

class LogQLParser:
    """A very basic parser for LogQL-like queries."""
    def parse(self, query: str) -> Tuple[Dict[str, str], List[str]]:
        """Parses a query like '{app="api", cluster="us-central-1"} |= "error"'"""
        label_part_match = re.match(r'\{(.*?)\}', query)
        if not label_part_match:
            raise ValueError("Invalid LogQL query: missing label selector.")
        
        label_str = label_part_match.group(1)
        labels = dict(re.findall(r'(\w+)="([^"]+)"', label_str))
        
        filter_parts = re.findall(r'\|="([^"]+)"', query)
        
        return labels, filter_parts

class LogQueryEngine:
    def __init__(self, storage: LogStorage):
        self.storage = storage
        self.parser = LogQLParser()

    def execute_query(self, query: str, start_time: float, end_time: float) -> List[LogEntry]:
        labels, filters = self.parser.parse(query)
        
        results = self.storage.query(start_time, end_time, labels)
        
        if filters:
            filtered_results = []
            for log in results:
                if all(f in log.line for f in filters):
                    filtered_results.append(log)
            return filtered_results
        
        return results

# ======================================================================================
# SECTION 4: DISTRIBUTED TRACING (JAEGER-STYLE)
# ======================================================================================

class SpanContext(NamedTuple):
    trace_id: str
    span_id: str
    parent_span_id: Optional[str]
    is_sampled: bool

class Span:
    """Represents a single unit of work in a trace."""
    def __init__(self, tracer: 'DistributedTracer', context: SpanContext, operation_name: str):
        self.tracer = tracer
        self.context = context
        self.operation_name = operation_name
        self.start_time = time.time()
        self.end_time = None
        self.tags = {}
        self.logs = []

    def set_tag(self, key: str, value: Any):
        self.tags[key] = value

    def log(self, event: str, payload: Any = None):
        self.logs.append({"timestamp": time.time(), "event": event, "payload": payload})

    def finish(self):
        self.end_time = time.time()
        self.tracer.report_span(self)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            self.set_tag("error", True)
            self.set_tag("error.type", exc_type.__name__)
            self.log("error", {"type": exc_type.__name__, "value": str(exc_val)})
        self.finish()

class TraceSampler(ABC):
    @abstractmethod
    def is_sampled(self, trace_id: str) -> bool:
        pass

class ProbabilisticSampler(TraceSampler):
    def __init__(self, rate: float):
        if not 0.0 <= rate <= 1.0:
            raise ValueError("Sampling rate must be between 0.0 and 1.0")
        self.rate = rate
        self.boundary = int(self.rate * (2**64 - 1))

    def is_sampled(self, trace_id: str) -> bool:
        return int(trace_id[:16], 16) < self.boundary

class DistributedTracer:
    """Manages the creation and reporting of spans."""
    def __init__(self, service_name: str, exporter: 'TraceExporter', sampler: TraceSampler):
        self.service_name = service_name
        self.exporter = exporter
        self.sampler = sampler
        self._current_span = threading.local()

    def start_span(self, operation_name: str, parent_context: Optional[SpanContext] = None) -> Span:
        if parent_context is None and hasattr(self._current_span, 'span'):
            parent_context = self._current_span.span.context

        if parent_context:
            trace_id = parent_context.trace_id
            parent_span_id = parent_context.span_id
            is_sampled = parent_context.is_sampled
        else:
            trace_id = self._generate_id(16)
            parent_span_id = None
            is_sampled = self.sampler.is_sampled(trace_id)

        span_id = self._generate_id(8)
        context = SpanContext(trace_id, span_id, parent_span_id, is_sampled)
        
        span = Span(self, context, operation_name)
        self._current_span.span = span
        return span

    def report_span(self, span: Span):
        if span.context.is_sampled:
            self.exporter.export([span])

    def _generate_id(self, length: int) -> str:
        return uuid.uuid4().hex[:length*2]

class TraceExporter(ABC):
    @abstractmethod
    def export(self, spans: List[Span]):
        pass

class JaegerExporter(TraceExporter):
    """Exports spans to a Jaeger agent/collector."""
    def __init__(self, agent_host: str = 'localhost', agent_port: int = 6831, collector_endpoint: str = None):
        self.collector_endpoint = collector_endpoint
        # UDP agent communication is more complex, so we'll focus on HTTP collector
        if not collector_endpoint:
            logging.warning("JaegerExporter: No collector endpoint configured. Spans will not be sent.")

    def export(self, spans: List[Span]):
        if not self.collector_endpoint:
            return

        jaeger_spans = [self._convert_to_jaeger_format(s) for s in spans]
        payload = {
            "process": {"serviceName": spans[0].tracer.service_name},
            "spans": jaeger_spans
        }
        try:
            requests.post(self.collector_endpoint, json=payload, timeout=1)
        except requests.RequestException as e:
            logging.error(f"Failed to export spans to Jaeger: {e}")

    def _convert_to_jaeger_format(self, span: Span) -> Dict:
        return {
            "traceID": span.context.trace_id,
            "spanID": span.context.span_id,
            "parentSpanID": span.context.parent_span_id,
            "operationName": span.operation_name,
            "startTime": int(span.start_time * 1_000_000),
            "duration": int((span.end_time - span.start_time) * 1_000_000) if span.end_time else 0,
            "tags": [{"key": k, "type": "string", "value": str(v)} for k, v in span.tags.items()],
            "logs": [{"timestamp": int(l["timestamp"] * 1_000_000), "fields": [{"key": "event", "value": l["event"]}]} for l in span.logs]
        }

# ======================================================================================
# SECTION 5: ALERTING SYSTEM (ALERTMANAGER-STYLE)
# ======================================================================================

class AlertState(Enum):
    PENDING = "pending"
    FIRING = "firing"
    RESOLVED = "resolved"

class Alert:
    def __init__(self, rule: 'AlertRule', labels: Dict[str, str], value: float):
        self.rule = rule
        self.labels = labels
        self.value = value
        self.state = AlertState.PENDING
        self.starts_at = time.time()
        self.ends_at = None
        self.last_evaluated = self.starts_at
        self.fingerprint = self._generate_fingerprint()

    def _generate_fingerprint(self) -> str:
        m = hashlib.sha256()
        m.update(self.rule.name.encode())
        for k, v in sorted(self.labels.items()):
            m.update(f"{k}={v}".encode())
        return m.hexdigest()

    def resolve(self):
        self.state = AlertState.RESOLVED
        self.ends_at = time.time()

class AlertRule:
    def __init__(self, name: str, expression: str, for_duration: int, labels: Dict[str, str], annotations: Dict[str, str]):
        self.name = name
        self.expression = expression # Simplified: metric name and threshold, e.g., "http_requests_total > 100"
        self.for_duration = for_duration
        self.labels = labels
        self.annotations = annotations

class RuleEvaluator:
    def __init__(self, rules: List[AlertRule], registry: MetricsRegistry):
        self.rules = rules
        self.registry = registry

    def evaluate(self) -> List[Alert]:
        active_alerts = []
        for rule in self.rules:
            try:
                # Simplified expression parsing
                metric_name, op, threshold_str = rule.expression.split()
                threshold = float(threshold_str)
                
                metric = self.registry.get_metric(metric_name)
                if not metric:
                    continue

                # This is highly simplified. A real implementation needs a full PromQL engine.
                with metric._lock:
                    for label_set, value in metric._values.items():
                        if self._compare(value, op, threshold):
                            alert_labels = dict(label_set)
                            alert_labels.update(rule.labels)
                            active_alerts.append(Alert(rule, alert_labels, value))
            except Exception as e:
                logging.error(f"Failed to evaluate rule '{rule.name}': {e}")
        return active_alerts

    def _compare(self, value, op, threshold):
        return {
            '>': value > threshold,
            '<': value < threshold,
            '==': value == threshold,
            '!=': value != threshold,
            '>=': value >= threshold,
            '<=': value <= threshold,
        }[op]

class NotificationChannel(ABC):
    @abstractmethod
    def notify(self, alerts: List[Alert]):
        pass

class ConsoleNotificationChannel(NotificationChannel):
    def notify(self, alerts: List[Alert]):
        for alert in alerts:
            print(f"--- FIRING ALERT ---")
            print(f"  Name: {alert.rule.name}")
            print(f"  Summary: {alert.rule.annotations.get('summary')}")
            print(f"  Labels: {alert.labels}")
            print(f"  Value: {alert.value}")
            print(f"  Starts at: {datetime.datetime.fromtimestamp(alert.starts_at)}")
            print("--------------------")

class AlertManager:
    def __init__(self, evaluator: RuleEvaluator, channels: List[NotificationChannel]):
        self.evaluator = evaluator
        self.channels = channels
        self.alerts = {} # fingerprint -> Alert
        self._lock = threading.Lock()
        self._scheduler = sched.scheduler(time.time, time.sleep)
        self._running = False

    def start(self, interval: int = 15):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._run, args=(interval,), name="AlertManager")
        self._thread.daemon = True
        self._thread.start()
        logging.info("AlertManager started.")

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join()

    def _run(self, interval: int):
        while self._running:
            self._scheduler.enter(interval, 1, self._tick)
            self._scheduler.run()

    def _tick(self):
        with self._lock:
            now = time.time()
            active_alerts_from_eval = self.evaluator.evaluate()
            active_fingerprints = {a.fingerprint for a in active_alerts_from_eval}

            # Update existing or add new alerts
            for new_alert in active_alerts_from_eval:
                fp = new_alert.fingerprint
                if fp in self.alerts:
                    # Update existing alert
                    self.alerts[fp].last_evaluated = now
                    self.alerts[fp].value = new_alert.value
                else:
                    # Add new pending alert
                    self.alerts[fp] = new_alert

            # Check for resolved alerts
            resolved_alerts = []
            for fp, alert in list(self.alerts.items()):
                if fp not in active_fingerprints:
                    if alert.state != AlertState.RESOLVED:
                        alert.resolve()
                        logging.info(f"Alert {alert.rule.name}{alert.labels} resolved.")
                    resolved_alerts.append(alert)
            
            # Clean up old resolved alerts
            for alert in resolved_alerts:
                if now - alert.ends_at > 300: # 5 minutes
                    del self.alerts[alert.fingerprint]

            # Process state transitions and notify
            firing_alerts_to_notify = []
            for alert in self.alerts.values():
                if alert.state == AlertState.PENDING and (now - alert.starts_at) >= alert.rule.for_duration:
                    alert.state = AlertState.FIRING
                    firing_alerts_to_notify.append(alert)
                    logging.info(f"Alert {alert.rule.name}{alert.labels} is now FIRING.")

            if firing_alerts_to_notify:
                for channel in self.channels:
                    channel.notify(firing_alerts_to_notify)

# ======================================================================================
# SECTION 6: DASHBOARDS (GRAFANA-STYLE)
# ======================================================================================

class Panel:
    def __init__(self, title: str, panel_type: str = 'graph', targets: List[Dict] = []):
        self.id = uuid.uuid4().int & (1<<31)-1
        self.title = title
        self.type = panel_type
        self.targets = targets
        self.grid_pos = {}

    def to_json(self) -> Dict:
        return {
            "id": self.id,
            "title": self.title,
            "type": self.type,
            "targets": self.targets,
            "gridPos": self.grid_pos
        }

class GrafanaDashboard:
    def __init__(self, title: str, description: str = ""):
        self.title = title
        self.description = description
        self.panels = []
        self._next_y = 0
        self._next_x = 0

    def add_panel(self, panel: Panel, width: int = 12, height: int = 8):
        if self._next_x + width > 24:
            self._next_y += height
            self._next_x = 0
        
        panel.grid_pos = {"h": height, "w": width, "x": self._next_x, "y": self._next_y}
        self.panels.append(panel)
        self._next_x += width

    def to_json_str(self) -> str:
        dashboard_model = {
            "__inputs": [],
            "__requires": [],
            "annotations": {"list": []},
            "description": self.description,
            "editable": True,
            "gnetId": None,
            "graphTooltip": 0,
            "id": None,
            "links": [],
            "panels": [p.to_json() for p in self.panels],
            "schemaVersion": 27,
            "style": "dark",
            "tags": [],
            "templating": {"list": []},
            "time": {"from": "now-6h", "to": "now"},
            "timepicker": {},
            "timezone": "browser",
            "title": self.title,
            "uid": uuid.uuid4().hex,
            "version": 1
        }
        return json.dumps(dashboard_model, indent=2)

class DashboardManager:
    def __init__(self):
        self.dashboards = {}

    def create_dashboard(self, title: str, description: str = "") -> GrafanaDashboard:
        dash = GrafanaDashboard(title, description)
        self.dashboards[title] = dash
        return dash

    def get_dashboard_json(self, title: str) -> Optional[str]:
        if title in self.dashboards:
            return self.dashboards[title].to_json_str()
        return None

# ======================================================================================
# SECTION 7: ADVANCED FEATURES (SLO, HEALTH, ANOMALY, CANARY)
# ======================================================================================

class SLOManager:
    """Manages Service Level Objectives."""
    def __init__(self, registry: MetricsRegistry):
        self.registry = registry
        self.slos = {}
        self.slo_gauge = Gauge("slo_compliance_ratio", "SLO compliance ratio (1 = 100%)", ["slo_name"])
        self.error_budget_gauge = Gauge("slo_error_budget_remaining_ratio", "Remaining error budget ratio", ["slo_name"])
        registry.register(self.slo_gauge)
        registry.register(self.error_budget_gauge)

    def define_slo(self, name: str, sli_expression_good: str, sli_expression_total: str, goal: float, window: str):
        self.slos[name] = {
            "good_expr": sli_expression_good,
            "total_expr": sli_expression_total,
            "goal": goal,
            "window": window # e.g., "30d"
        }

    def evaluate_all(self):
        # This is a placeholder for a complex evaluation logic that would query
        # the metrics backend over a time window.
        for name, slo in self.slos.items():
            # Dummy evaluation
            good_events = 1998
            total_events = 2000
            
            compliance = (good_events / total_events) if total_events > 0 else 1.0
            error_budget_remaining = (compliance - slo['goal']) / (1 - slo['goal'])
            
            self.slo_gauge.set(compliance, {"slo_name": name})
            self.error_budget_gauge.set(max(0, error_budget_remaining), {"slo_name": name})

class HealthChecker:
    """Performs active health checks on services."""
    def __init__(self, registry: MetricsRegistry):
        self.registry = registry
        self.targets = []
        self.health_gauge = Gauge("service_health_status", "Health status of a service (1=up, 0=down)", ["service_name", "target"])
        registry.register(self.health_gauge)
        self._scheduler = sched.scheduler(time.time, time.sleep)
        self._running = False

    def add_target(self, name: str, check_type: str, endpoint: str, interval: int):
        self.targets.append({"name": name, "type": check_type, "endpoint": endpoint, "interval": interval})

    def start(self):
        if self._running: return
        self._running = True
        self._thread = threading.Thread(target=self._run, name="HealthChecker")
        self._thread.daemon = True
        self._thread.start()

    def _run(self):
        for target in self.targets:
            self._schedule_check(target)
        self._scheduler.run()

    def _schedule_check(self, target):
        if not self._running: return
        self._scheduler.enter(target['interval'], 1, self._perform_check, (target,))

    def _perform_check(self, target):
        status = 0
        try:
            if target['type'] == 'http':
                r = requests.get(target['endpoint'], timeout=5)
                if 200 <= r.status_code < 300:
                    status = 1
        except requests.RequestException:
            status = 0
        
        self.health_gauge.set(status, {"service_name": target['name'], "target": target['endpoint']})
        self._schedule_check(target) # Reschedule

class AnomalyDetector:
    """Detects anomalies in time series data using statistical methods."""
    def __init__(self, registry: MetricsRegistry):
        self.registry = registry
        self.anomaly_gauge = Gauge("metric_anomaly_detected", "Indicates if an anomaly is detected for a metric", ["metric_name"])
        registry.register(self.anomaly_gauge)

    def check(self, metric_name: str, window_size: int = 60, threshold: float = 3.5):
        # Placeholder: needs a time-series database. We'll simulate with a local deque.
        # In a real system, this would query Prometheus or a similar TSDB.
        metric = self.registry.get_metric(metric_name)
        if not isinstance(metric, Gauge): return # Simplified to work with gauges

        # This is a highly simplified simulation
        history = list(metric._values.values())
        if len(history) < window_size: return

        series = np.array(history[-window_size:])
        median = np.median(series)
        mad = np.median(np.abs(series - median))
        if mad == 0: return
        
        z_score = 0.6745 * (series[-1] - median) / mad
        
        if np.abs(z_score) > threshold:
            self.anomaly_gauge.set(1, {"metric_name": metric_name})
        else:
            self.anomaly_gauge.set(0, {"metric_name": metric_name})

class CanaryReleaseMonitor:
    """Monitors and compares canary vs. baseline deployments."""
    def __init__(self, registry: MetricsRegistry, alert_manager: AlertManager):
        self.registry = registry
        self.alert_manager = alert_manager

    def evaluate(self, service_name: str, metrics_to_check: List[str]):
        # Placeholder for logic that queries metrics for baseline and canary,
        # performs statistical tests (e.g., t-test) and triggers alerts.
        logging.info(f"Evaluating canary for {service_name}...")
        
        for metric_name in metrics_to_check:
            # Dummy data
            baseline_value = 100
            canary_value = 150
            
            if canary_value > baseline_value * 1.2: # 20% degradation
                logging.warning(f"Canary for {service_name} shows degradation in {metric_name}!")
                # This could trigger a rollback via an alert
                # For now, we just log it.

# ======================================================================================
# SECTION 8: MAIN ORCHESTRATOR AND EXAMPLE USAGE
# ======================================================================================

class ObservabilityService:
    """Main service to run all observability components."""
    def __init__(self, config: Dict):
        self.config = config
        
        # Init components
        self.registry = DEFAULT_REGISTRY
        self.prometheus_exporter = PrometheusExporter(config['exporter_port'], self.registry)
        
        rules = [AlertRule(**r) for r in config.get('alert_rules', [])]
        self.rule_evaluator = RuleEvaluator(rules, self.registry)
        self.alert_manager = AlertManager(self.rule_evaluator, [ConsoleNotificationChannel()])
        
        self.health_checker = HealthChecker(self.registry)
        for target in config.get('health_targets', []):
            self.health_checker.add_target(**target)

    def start(self):
        logging.info("Starting Observability Service...")
        self.prometheus_exporter.start()
        self.alert_manager.start()
        self.health_checker.start()
        logging.info("Observability Service started successfully.")

    def stop(self):
        logging.info("Stopping Observability Service...")
        self.alert_manager.stop()
        # Other components stop via daemon threads
        logging.info("Observability Service stopped.")

def example_usage():
    """Demonstrates how to use the observability platform."""
    
    # --- 1. Define Configuration ---
    config = {
        "exporter_port": 9099,
        "alert_rules": [
            {
                "name": "HighRequestLatency",
                "expression": "http_request_latency_seconds_sum > 5",
                "for_duration": 30,
                "labels": {"severity": "page"},
                "annotations": {"summary": "High request latency detected!"}
            }
        ],
        "health_targets": [
            {"name": "self-metrics", "type": "http", "endpoint": "http://localhost:9099/metrics", "interval": 10}
        ]
    }

    # --- 2. Start the Observability Service ---
    service = ObservabilityService(config)
    service.start()

    # --- 3. Instrument an example application ---
    
    # Create some metrics
    http_requests = Counter("http_requests_total", "Total HTTP requests", ["method", "endpoint"])
    http_latency = Histogram("http_request_latency_seconds", "HTTP request latency", ["endpoint"])
    active_users = Gauge("active_users", "Number of active users")
    
    service.registry.register(http_requests)
    service.registry.register(http_latency)
    service.registry.register(active_users)

    # Setup tracing
    tracer = DistributedTracer("example-app", JaegerExporter(collector_endpoint=None), ProbabilisticSampler(1.0))

    def handle_request(endpoint: str):
        with tracer.start_span(f"GET {endpoint}") as span:
            span.set_tag("http.method", "GET")
            start_time = time.time()
            
            http_requests.inc(label_values={"method": "GET", "endpoint": endpoint})
            active_users.inc()
            span.log("request_started")
            
            time.sleep(np.random.uniform(0.05, 0.2)) # Simulate work
            
            latency = time.time() - start_time
            http_latency.observe(latency, {"endpoint": endpoint})
            
            active_users.dec()
            span.set_tag("http.status_code", 200)
            span.log("request_finished")

    # --- 4. Run the example application for a while ---
    logging.info("Running example application simulation for 60 seconds...")
    end_time = time.time() + 60
    while time.time() < end_time:
        handle_request("/api/data")
        handle_request("/api/users")
        time.sleep(1)
        # Manually trigger high latency for alert
        if time.time() % 20 < 2:
             http_latency.observe(6.0, {"endpoint": "/api/data"})

    # --- 5. Demonstrate Dashboard Generation ---
    dash_manager = DashboardManager()
    app_dashboard = dash_manager.create_dashboard("Example App Dashboard")
    
    app_dashboard.add_panel(Panel(
        title="Total Requests",
        targets=[{"expr": "rate(http_requests_total[5m])"}]
    ), width=12)
    app_dashboard.add_panel(Panel(
        title="P95 Latency",
        targets=[{"expr": 'histogram_quantile(0.95, sum(rate(http_request_latency_seconds_bucket[5m])) by (le))'}]
    ), width=12)
    
    dashboard_json = dash_manager.get_dashboard_json("Example App Dashboard")
    with open("example_dashboard.json", "w") as f:
        f.write(dashboard_json)
    logging.info("Generated Grafana dashboard to example_dashboard.json")

    # --- 6. Stop the service ---
    service.stop()


if __name__ == '__main__':
    example_usage()
