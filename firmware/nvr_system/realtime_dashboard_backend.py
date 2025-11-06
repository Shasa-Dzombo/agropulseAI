# ======================================================================================================================
# AgroPulse NVR - Real-time Analytics Dashboard Backend
# WebSocket streaming, live metrics, chart data aggregation, dashboard state management
# ======================================================================================================================

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, field
from enum import Enum
from collections import deque, defaultdict
import json

logger = logging.getLogger(__name__)

# ======================================================================================================================
# DASHBOARD MODELS
# ======================================================================================================================

class WidgetType(Enum):
    """Dashboard widget types"""
    LINE_CHART = "line_chart"
    BAR_CHART = "bar_chart"
    PIE_CHART = "pie_chart"
    GAUGE = "gauge"
    COUNTER = "counter"
    TABLE = "table"
    MAP = "map"
    HEATMAP = "heatmap"
    TIMELINE = "timeline"

class MetricAggregation(Enum):
    """Metric aggregation types"""
    SUM = "sum"
    AVG = "average"
    MIN = "min"
    MAX = "max"
    COUNT = "count"
    LAST = "last"

class TimeRange(Enum):
    """Time range presets"""
    LAST_5_MIN = "5m"
    LAST_15_MIN = "15m"
    LAST_1_HOUR = "1h"
    LAST_6_HOURS = "6h"
    LAST_24_HOURS = "24h"
    LAST_7_DAYS = "7d"
    LAST_30_DAYS = "30d"
    CUSTOM = "custom"

@dataclass
class DataPoint:
    """Time-series data point"""
    timestamp: datetime
    value: float
    label: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class MetricSeries:
    """Metric time series"""
    metric_name: str
    series_id: str
    data_points: deque = field(default_factory=lambda: deque(maxlen=1000))
    last_updated: datetime = field(default_factory=datetime.now)

@dataclass
class Widget:
    """Dashboard widget"""
    widget_id: str
    widget_type: WidgetType
    title: str
    metric_name: str
    aggregation: MetricAggregation
    time_range: TimeRange
    refresh_interval: int = 5  # seconds
    position: Dict[str, int] = field(default_factory=dict)
    config: Dict[str, Any] = field(default_factory=dict)

@dataclass
class Dashboard:
    """Dashboard definition"""
    dashboard_id: str
    name: str
    description: str
    widgets: List[Widget]
    created_by: str
    is_public: bool = False
    created_at: datetime = field(default_factory=datetime.now)
    last_modified: datetime = field(default_factory=datetime.now)

@dataclass
class DashboardSession:
    """Dashboard WebSocket session"""
    session_id: str
    dashboard_id: str
    user_id: str
    connected_at: datetime = field(default_factory=datetime.now)
    subscribed_metrics: Set[str] = field(default_factory=set)

# ======================================================================================================================
# METRICS COLLECTOR
# ======================================================================================================================

class MetricsCollector:
    """Collect and store real-time metrics"""
    
    def __init__(self, max_history: int = 1000):
        self.metrics: Dict[str, MetricSeries] = {}
        self.max_history = max_history
        
        logger.info("[METRICS] Metrics collector initialized")
    
    def record_metric(self, metric_name: str, value: float,
                     timestamp: Optional[datetime] = None,
                     metadata: Optional[Dict[str, Any]] = None):
        """Record metric value"""
        if metric_name not in self.metrics:
            self.metrics[metric_name] = MetricSeries(
                metric_name=metric_name,
                series_id=f"series_{metric_name}"
            )
        
        series = self.metrics[metric_name]
        
        data_point = DataPoint(
            timestamp=timestamp or datetime.now(),
            value=value,
            metadata=metadata or {}
        )
        
        series.data_points.append(data_point)
        series.last_updated = datetime.now()
        
        logger.debug(f"[METRICS] Recorded: {metric_name} = {value}")
    
    def get_metric(self, metric_name: str,
                  time_range: Optional[TimeRange] = None) -> Optional[MetricSeries]:
        """Get metric series"""
        series = self.metrics.get(metric_name)
        
        if not series or not time_range:
            return series
        
        # Filter by time range
        cutoff = self._get_time_cutoff(time_range)
        filtered_points = deque(
            [dp for dp in series.data_points if dp.timestamp >= cutoff],
            maxlen=self.max_history
        )
        
        return MetricSeries(
            metric_name=series.metric_name,
            series_id=series.series_id,
            data_points=filtered_points,
            last_updated=series.last_updated
        )
    
    def _get_time_cutoff(self, time_range: TimeRange) -> datetime:
        """Get time cutoff for range"""
        now = datetime.now()
        
        if time_range == TimeRange.LAST_5_MIN:
            return now - timedelta(minutes=5)
        elif time_range == TimeRange.LAST_15_MIN:
            return now - timedelta(minutes=15)
        elif time_range == TimeRange.LAST_1_HOUR:
            return now - timedelta(hours=1)
        elif time_range == TimeRange.LAST_6_HOURS:
            return now - timedelta(hours=6)
        elif time_range == TimeRange.LAST_24_HOURS:
            return now - timedelta(hours=24)
        elif time_range == TimeRange.LAST_7_DAYS:
            return now - timedelta(days=7)
        elif time_range == TimeRange.LAST_30_DAYS:
            return now - timedelta(days=30)
        
        return now - timedelta(hours=1)
    
    def aggregate_metric(self, metric_name: str,
                        aggregation: MetricAggregation,
                        time_range: Optional[TimeRange] = None) -> float:
        """Aggregate metric"""
        series = self.get_metric(metric_name, time_range)
        
        if not series or not series.data_points:
            return 0.0
        
        values = [dp.value for dp in series.data_points]
        
        if aggregation == MetricAggregation.SUM:
            return sum(values)
        elif aggregation == MetricAggregation.AVG:
            return sum(values) / len(values)
        elif aggregation == MetricAggregation.MIN:
            return min(values)
        elif aggregation == MetricAggregation.MAX:
            return max(values)
        elif aggregation == MetricAggregation.COUNT:
            return len(values)
        elif aggregation == MetricAggregation.LAST:
            return values[-1]
        
        return 0.0
    
    def get_available_metrics(self) -> List[str]:
        """Get list of available metrics"""
        return list(self.metrics.keys())

# ======================================================================================================================
# DATA AGGREGATOR
# ======================================================================================================================

class DataAggregator:
    """Aggregate data for charts"""
    
    def __init__(self, metrics_collector: MetricsCollector):
        self.metrics_collector = metrics_collector
        
        logger.info("[AGGREGATOR] Data aggregator initialized")
    
    def get_chart_data(self, widget: Widget) -> Dict[str, Any]:
        """Get chart data for widget"""
        series = self.metrics_collector.get_metric(
            widget.metric_name,
            widget.time_range
        )
        
        if not series:
            return {'labels': [], 'values': []}
        
        if widget.widget_type == WidgetType.LINE_CHART:
            return self._prepare_line_chart(series)
        elif widget.widget_type == WidgetType.BAR_CHART:
            return self._prepare_bar_chart(series)
        elif widget.widget_type == WidgetType.PIE_CHART:
            return self._prepare_pie_chart(series)
        elif widget.widget_type == WidgetType.GAUGE:
            return self._prepare_gauge(series, widget.aggregation)
        elif widget.widget_type == WidgetType.COUNTER:
            return self._prepare_counter(series, widget.aggregation)
        
        return {}
    
    def _prepare_line_chart(self, series: MetricSeries) -> Dict[str, Any]:
        """Prepare line chart data"""
        labels = [dp.timestamp.strftime('%H:%M:%S') for dp in series.data_points]
        values = [dp.value for dp in series.data_points]
        
        return {
            'labels': labels,
            'datasets': [{
                'label': series.metric_name,
                'data': values
            }]
        }
    
    def _prepare_bar_chart(self, series: MetricSeries) -> Dict[str, Any]:
        """Prepare bar chart data"""
        # Group by label if available
        grouped = defaultdict(list)
        
        for dp in series.data_points:
            label = dp.label or 'default'
            grouped[label].append(dp.value)
        
        labels = list(grouped.keys())
        values = [sum(vals) / len(vals) for vals in grouped.values()]
        
        return {
            'labels': labels,
            'datasets': [{
                'label': series.metric_name,
                'data': values
            }]
        }
    
    def _prepare_pie_chart(self, series: MetricSeries) -> Dict[str, Any]:
        """Prepare pie chart data"""
        # Group by label
        grouped = defaultdict(float)
        
        for dp in series.data_points:
            label = dp.label or 'Unknown'
            grouped[label] += dp.value
        
        return {
            'labels': list(grouped.keys()),
            'values': list(grouped.values())
        }
    
    def _prepare_gauge(self, series: MetricSeries,
                      aggregation: MetricAggregation) -> Dict[str, Any]:
        """Prepare gauge data"""
        if not series.data_points:
            return {'value': 0, 'min': 0, 'max': 100}
        
        values = [dp.value for dp in series.data_points]
        
        if aggregation == MetricAggregation.LAST:
            value = values[-1]
        elif aggregation == MetricAggregation.AVG:
            value = sum(values) / len(values)
        else:
            value = values[-1]
        
        return {
            'value': value,
            'min': min(values),
            'max': max(values)
        }
    
    def _prepare_counter(self, series: MetricSeries,
                        aggregation: MetricAggregation) -> Dict[str, Any]:
        """Prepare counter data"""
        if not series.data_points:
            return {'value': 0}
        
        values = [dp.value for dp in series.data_points]
        
        if aggregation == MetricAggregation.SUM:
            value = sum(values)
        elif aggregation == MetricAggregation.COUNT:
            value = len(values)
        elif aggregation == MetricAggregation.LAST:
            value = values[-1]
        else:
            value = sum(values)
        
        return {'value': value}

# ======================================================================================================================
# DASHBOARD MANAGER
# ======================================================================================================================

class DashboardManager:
    """Manage dashboards"""
    
    def __init__(self):
        self.dashboards: Dict[str, Dashboard] = {}
        
        logger.info("[DASH-MGR] Dashboard manager initialized")
    
    def create_dashboard(self, name: str, description: str,
                        created_by: str) -> Dashboard:
        """Create dashboard"""
        dashboard_id = f"dash_{datetime.now().timestamp()}"
        
        dashboard = Dashboard(
            dashboard_id=dashboard_id,
            name=name,
            description=description,
            widgets=[],
            created_by=created_by
        )
        
        self.dashboards[dashboard_id] = dashboard
        
        logger.info(f"[DASH-MGR] Created dashboard: {dashboard_id}")
        return dashboard
    
    def add_widget(self, dashboard_id: str, widget: Widget):
        """Add widget to dashboard"""
        dashboard = self.dashboards.get(dashboard_id)
        if dashboard:
            dashboard.widgets.append(widget)
            dashboard.last_modified = datetime.now()
            logger.info(f"[DASH-MGR] Added widget: {widget.widget_id}")
    
    def remove_widget(self, dashboard_id: str, widget_id: str):
        """Remove widget from dashboard"""
        dashboard = self.dashboards.get(dashboard_id)
        if dashboard:
            dashboard.widgets = [
                w for w in dashboard.widgets if w.widget_id != widget_id
            ]
            dashboard.last_modified = datetime.now()
            logger.info(f"[DASH-MGR] Removed widget: {widget_id}")
    
    def get_dashboard(self, dashboard_id: str) -> Optional[Dashboard]:
        """Get dashboard"""
        return self.dashboards.get(dashboard_id)
    
    def get_user_dashboards(self, user_id: str) -> List[Dashboard]:
        """Get user's dashboards"""
        return [
            dash for dash in self.dashboards.values()
            if dash.created_by == user_id or dash.is_public
        ]

# ======================================================================================================================
# WEBSOCKET MANAGER
# ======================================================================================================================

class WebSocketManager:
    """Manage WebSocket connections"""
    
    def __init__(self):
        self.sessions: Dict[str, DashboardSession] = {}
        self.connections: Dict[str, Any] = {}  # session_id -> websocket
        
        logger.info("[WS-MGR] WebSocket manager initialized")
    
    def create_session(self, dashboard_id: str, user_id: str) -> str:
        """Create dashboard session"""
        session_id = f"sess_{datetime.now().timestamp()}"
        
        session = DashboardSession(
            session_id=session_id,
            dashboard_id=dashboard_id,
            user_id=user_id
        )
        
        self.sessions[session_id] = session
        
        logger.info(f"[WS-MGR] Created session: {session_id}")
        return session_id
    
    def subscribe_metric(self, session_id: str, metric_name: str):
        """Subscribe to metric"""
        session = self.sessions.get(session_id)
        if session:
            session.subscribed_metrics.add(metric_name)
            logger.debug(f"[WS-MGR] Subscribed: {session_id} -> {metric_name}")
    
    def unsubscribe_metric(self, session_id: str, metric_name: str):
        """Unsubscribe from metric"""
        session = self.sessions.get(session_id)
        if session:
            session.subscribed_metrics.discard(metric_name)
            logger.debug(f"[WS-MGR] Unsubscribed: {session_id} -> {metric_name}")
    
    def get_sessions_for_metric(self, metric_name: str) -> List[str]:
        """Get sessions subscribed to metric"""
        return [
            session_id for session_id, session in self.sessions.items()
            if metric_name in session.subscribed_metrics
        ]
    
    def close_session(self, session_id: str):
        """Close session"""
        if session_id in self.sessions:
            del self.sessions[session_id]
            logger.info(f"[WS-MGR] Closed session: {session_id}")

# ======================================================================================================================
# REAL-TIME BROADCASTER
# ======================================================================================================================

class RealTimeBroadcaster:
    """Broadcast real-time updates"""
    
    def __init__(self, websocket_manager: WebSocketManager,
                 data_aggregator: DataAggregator):
        self.websocket_manager = websocket_manager
        self.data_aggregator = data_aggregator
        self.running = False
        self.broadcast_task: Optional[asyncio.Task] = None
        
        logger.info("[BROADCASTER] Real-time broadcaster initialized")
    
    async def start(self):
        """Start broadcasting"""
        self.running = True
        self.broadcast_task = asyncio.create_task(self._broadcast_loop())
        logger.info("[BROADCASTER] Broadcasting started")
    
    async def stop(self):
        """Stop broadcasting"""
        self.running = False
        if self.broadcast_task:
            self.broadcast_task.cancel()
            try:
                await self.broadcast_task
            except asyncio.CancelledError:
                pass
        logger.info("[BROADCASTER] Broadcasting stopped")
    
    async def _broadcast_loop(self):
        """Broadcast loop"""
        while self.running:
            try:
                await asyncio.sleep(1)  # Broadcast every second
                
                # Would broadcast to WebSocket connections here
                # For each session, send updated data
                
            except Exception as e:
                logger.error(f"[BROADCASTER] Broadcast error: {e}")
    
    async def broadcast_metric_update(self, metric_name: str, value: float):
        """Broadcast metric update"""
        # Get sessions subscribed to this metric
        session_ids = self.websocket_manager.get_sessions_for_metric(metric_name)
        
        if not session_ids:
            return
        
        # Prepare update message
        message = {
            'type': 'metric_update',
            'metric_name': metric_name,
            'value': value,
            'timestamp': datetime.now().isoformat()
        }
        
        logger.debug(f"[BROADCASTER] Broadcasting to {len(session_ids)} sessions")

# ======================================================================================================================
# DASHBOARD ORCHESTRATOR
# ======================================================================================================================

class DashboardOrchestrator:
    """Main dashboard orchestrator"""
    
    def __init__(self):
        self.metrics_collector = MetricsCollector()
        self.data_aggregator = DataAggregator(self.metrics_collector)
        self.dashboard_manager = DashboardManager()
        self.websocket_manager = WebSocketManager()
        self.broadcaster = RealTimeBroadcaster(
            self.websocket_manager,
            self.data_aggregator
        )
        
        logger.info("[DASH-ORCH] Dashboard orchestrator initialized")
        
        self._create_default_dashboards()
    
    def _create_default_dashboards(self):
        """Create default dashboards"""
        # System overview dashboard
        dashboard = self.dashboard_manager.create_dashboard(
            "System Overview",
            "Overall system metrics and health",
            "system"
        )
        
        # Add widgets
        self.dashboard_manager.add_widget(dashboard.dashboard_id, Widget(
            widget_id="widget_1",
            widget_type=WidgetType.COUNTER,
            title="Total Detections",
            metric_name="detections_count",
            aggregation=MetricAggregation.SUM,
            time_range=TimeRange.LAST_24_HOURS
        ))
        
        self.dashboard_manager.add_widget(dashboard.dashboard_id, Widget(
            widget_id="widget_2",
            widget_type=WidgetType.LINE_CHART,
            title="Detection Trend",
            metric_name="detections_rate",
            aggregation=MetricAggregation.COUNT,
            time_range=TimeRange.LAST_1_HOUR
        ))
        
        self.dashboard_manager.add_widget(dashboard.dashboard_id, Widget(
            widget_id="widget_3",
            widget_type=WidgetType.GAUGE,
            title="System Health",
            metric_name="system_health_score",
            aggregation=MetricAggregation.LAST,
            time_range=TimeRange.LAST_5_MIN
        ))
    
    async def start(self):
        """Start dashboard system"""
        await self.broadcaster.start()
    
    async def stop(self):
        """Stop dashboard system"""
        await self.broadcaster.stop()
    
    def record_metric(self, metric_name: str, value: float):
        """Record metric"""
        self.metrics_collector.record_metric(metric_name, value)
    
    def create_dashboard(self, name: str, description: str,
                        user_id: str) -> str:
        """Create dashboard"""
        dashboard = self.dashboard_manager.create_dashboard(
            name, description, user_id
        )
        return dashboard.dashboard_id
    
    def get_dashboard_data(self, dashboard_id: str) -> Optional[Dict[str, Any]]:
        """Get dashboard data"""
        dashboard = self.dashboard_manager.get_dashboard(dashboard_id)
        
        if not dashboard:
            return None
        
        widgets_data = []
        for widget in dashboard.widgets:
            chart_data = self.data_aggregator.get_chart_data(widget)
            widgets_data.append({
                'widget_id': widget.widget_id,
                'title': widget.title,
                'type': widget.widget_type.value,
                'data': chart_data
            })
        
        return {
            'dashboard_id': dashboard.dashboard_id,
            'name': dashboard.name,
            'description': dashboard.description,
            'widgets': widgets_data
        }
    
    def create_session(self, dashboard_id: str, user_id: str) -> str:
        """Create WebSocket session"""
        return self.websocket_manager.create_session(dashboard_id, user_id)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get dashboard statistics"""
        return {
            'total_dashboards': len(self.dashboard_manager.dashboards),
            'total_metrics': len(self.metrics_collector.metrics),
            'active_sessions': len(self.websocket_manager.sessions),
            'available_metrics': self.metrics_collector.get_available_metrics()
        }

# ======================================================================================================================
# END OF REAL-TIME ANALYTICS DASHBOARD MODULE
# Lines in this file: ~700+
# Combined total: ~35,450+
# Remaining for 50k: ~14,550 lines
# ======================================================================================================================
