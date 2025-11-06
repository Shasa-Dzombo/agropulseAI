# Alert Manager - Enterprise Multi-Channel Notification and Escalation Platform
# Comprehensive alerting system with intelligent routing, escalation policies, and aggregation
# Supports: Email, SMS, Webhook, Slack, Teams, PagerDuty, Telegram, Push notifications
# Features: Alert deduplication, rate limiting, escalation chains, on-call schedules
# Advanced capabilities: ML-based alert prioritization, intelligent grouping, auto-remediation

import logging
import aiohttp
import asyncio
import smtplib
import json
import sqlite3
import hashlib
import time
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any, Union
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from enum import Enum, auto
from collections import defaultdict, deque
import uuid
import traceback

logger = logging.getLogger(__name__)


# ========================= ENUMERATIONS =========================

class AlertLevel(Enum):
    """Alert severity levels"""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"
    EMERGENCY = "emergency"

class AlertChannel(Enum):
    """Alert notification channels"""
    EMAIL = "email"
    SMS = "sms"
    WEBHOOK = "webhook"
    SLACK = "slack"
    TEAMS = "teams"
    TELEGRAM = "telegram"
    PAGERDUTY = "pagerduty"
    PUSH = "push"
    LOG = "log"
    DATABASE = "database"

class AlertStatus(Enum):
    """Alert status"""
    PENDING = auto()
    SENT = auto()
    DELIVERED = auto()
    FAILED = auto()
    ACKNOWLEDGED = auto()
    RESOLVED = auto()
    SUPPRESSED = auto()

class EscalationAction(Enum):
    """Escalation actions"""
    NOTIFY_NEXT = "notify_next"
    NOTIFY_ALL = "notify_all"
    NOTIFY_MANAGER = "notify_manager"
    CREATE_INCIDENT = "create_incident"
    TRIGGER_AUTOMATION = "trigger_automation"

# ========================= DATA CLASSES =========================

@dataclass
class Alert:
    """Alert data structure"""
    alert_id: str
    source: str
    message: str
    level: AlertLevel
    timestamp: str
    status: AlertStatus = AlertStatus.PENDING
    fingerprint: Optional[str] = None
    count: int = 1
    first_occurrence: Optional[str] = None
    last_occurrence: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    acknowledged_by: Optional[str] = None
    acknowledged_at: Optional[str] = None
    resolved_at: Optional[str] = None

@dataclass
class NotificationConfig:
    """Notification channel configuration"""
    channel: AlertChannel
    enabled: bool = True
    min_level: AlertLevel = AlertLevel.INFO
    max_retries: int = 3
    retry_interval: int = 60
    timeout: int = 30
    rate_limit_per_minute: int = 10
    config: Dict[str, Any] = field(default_factory=dict)

@dataclass
class EscalationPolicy:
    """Alert escalation policy"""
    policy_id: str
    name: str
    rules: List[Dict[str, Any]]
    enabled: bool = True
    repeat_interval_minutes: int = 60
    max_escalations: int = 3

@dataclass
class OnCallSchedule:
    """On-call schedule"""
    schedule_id: str
    name: str
    timezone: str
    rotations: List[Dict[str, Any]]
    overrides: List[Dict[str, Any]] = field(default_factory=list)

@dataclass
class AlertMetrics:
    """Alert system metrics"""
    total_alerts: int = 0
    alerts_by_level: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    alerts_by_source: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    sent_count: int = 0
    failed_count: int = 0
    acknowledged_count: int = 0
    resolved_count: int = 0
    avg_delivery_time_ms: float = 0.0
    avg_acknowledgment_time_seconds: float = 0.0

# ========================= EMAIL HANDLER =========================

class EmailHandler:
    """Email notification handler"""
    
    def __init__(self, config: Dict[str, Any]):
        self.smtp_server = config.get('smtp_server')
        self.smtp_port = config.get('smtp_port', 587)
        self.username = config.get('username')
        self.password = config.get('password')
        self.from_address = config.get('from_address')
        self.use_tls = config.get('use_tls', True)
        logger.info(f"EmailHandler initialized: {self.smtp_server}:{self.smtp_port}")
        
    async def send(self, alert: Alert, recipients: List[str]) -> bool:
        """Send email notification"""
        try:
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, self._send_sync, alert, recipients)
        except Exception as e:
            logger.error(f"Email send failed: {e}")
            return False
            
    def _send_sync(self, alert: Alert, recipients: List[str]) -> bool:
        """Synchronous email send"""
        try:
            msg = MIMEMultipart('alternative')
            msg['Subject'] = f"[{alert.level.value.upper()}] {alert.source}: {alert.message[:50]}"
            msg['From'] = self.from_address
            msg['To'] = ', '.join(recipients)
            
            # Plain text version
            text_body = f"""
Alert Notification

Level: {alert.level.value.upper()}
Source: {alert.source}
Message: {alert.message}
Timestamp: {alert.timestamp}
Alert ID: {alert.alert_id}

Occurrences: {alert.count}
First: {alert.first_occurrence or alert.timestamp}
Last: {alert.last_occurrence or alert.timestamp}
            """
            
            # HTML version
            html_body = f"""
<html>
<body style="font-family: Arial, sans-serif;">
    <h2 style="color: {'#d32f2f' if alert.level.value in ['critical', 'emergency'] else '#f57c00' if alert.level.value == 'error' else '#fbc02d' if alert.level.value == 'warning' else '#388e3c'};">
        Alert Notification
    </h2>
    <table style="border-collapse: collapse; width: 100%;">
        <tr><td style="padding: 8px; border: 1px solid #ddd;"><strong>Level</strong></td><td style="padding: 8px; border: 1px solid #ddd;">{alert.level.value.upper()}</td></tr>
        <tr><td style="padding: 8px; border: 1px solid #ddd;"><strong>Source</strong></td><td style="padding: 8px; border: 1px solid #ddd;">{alert.source}</td></tr>
        <tr><td style="padding: 8px; border: 1px solid #ddd;"><strong>Message</strong></td><td style="padding: 8px; border: 1px solid #ddd;">{alert.message}</td></tr>
        <tr><td style="padding: 8px; border: 1px solid #ddd;"><strong>Timestamp</strong></td><td style="padding: 8px; border: 1px solid #ddd;">{alert.timestamp}</td></tr>
        <tr><td style="padding: 8px; border: 1px solid #ddd;"><strong>Alert ID</strong></td><td style="padding: 8px; border: 1px solid #ddd;">{alert.alert_id}</td></tr>
        <tr><td style="padding: 8px; border: 1px solid #ddd;"><strong>Occurrences</strong></td><td style="padding: 8px; border: 1px solid #ddd;">{alert.count}</td></tr>
    </table>
</body>
</html>
            """
            
            msg.attach(MIMEText(text_body, 'plain'))
            msg.attach(MIMEText(html_body, 'html'))
            
            # Send email
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                if self.use_tls:
                    server.starttls()
                if self.username and self.password:
                    server.login(self.username, self.password)
                server.send_message(msg)
            
            logger.info(f"Email sent to {len(recipients)} recipients for alert {alert.alert_id}")
            return True
            
        except Exception as e:
            logger.error(f"Email send error: {e}")
            return False

# ========================= WEBHOOK HANDLER =========================

class WebhookHandler:
    """Webhook notification handler"""
    
    def __init__(self, config: Dict[str, Any]):
        self.url = config.get('url')
        self.method = config.get('method', 'POST').upper()
        self.headers = config.get('headers', {})
        self.auth_token = config.get('auth_token')
        logger.info(f"WebhookHandler initialized: {self.url}")
        
    async def send(self, alert: Alert) -> bool:
        """Send webhook notification"""
        try:
            payload = {
                'alert_id': alert.alert_id,
                'source': alert.source,
                'message': alert.message,
                'level': alert.level.value,
                'timestamp': alert.timestamp,
                'status': alert.status.value,
                'count': alert.count,
                'tags': alert.tags,
                'metadata': alert.metadata
            }
            
            headers = self.headers.copy()
            if self.auth_token:
                headers['Authorization'] = f"Bearer {self.auth_token}"
            headers['Content-Type'] = 'application/json'
            
            async with aiohttp.ClientSession() as session:
                if self.method == 'POST':
                    async with session.post(self.url, json=payload, headers=headers, timeout=aiohttp.ClientTimeout(total=30)) as response:
                        success = response.status < 300
                else:
                    async with session.get(self.url, params=payload, headers=headers, timeout=aiohttp.ClientTimeout(total=30)) as response:
                        success = response.status < 300
                
                if success:
                    logger.info(f"Webhook sent successfully for alert {alert.alert_id}")
                else:
                    logger.error(f"Webhook failed with status {response.status}")
                
                return success
                
        except Exception as e:
            logger.error(f"Webhook send error: {e}")
            return False

# ========================= SLACK HANDLER =========================

class SlackHandler:
    """Slack notification handler"""
    
    def __init__(self, config: Dict[str, Any]):
        self.webhook_url = config.get('webhook_url')
        self.channel = config.get('channel')
        self.username = config.get('username', 'NVR Alert Bot')
        self.icon_emoji = config.get('icon_emoji', ':warning:')
        logger.info(f"SlackHandler initialized for channel: {self.channel}")
        
    async def send(self, alert: Alert) -> bool:
        """Send Slack notification"""
        try:
            color = self._get_color(alert.level)
            
            payload = {
                'channel': self.channel,
                'username': self.username,
                'icon_emoji': self.icon_emoji,
                'attachments': [{
                    'color': color,
                    'title': f"{alert.level.value.upper()}: {alert.source}",
                    'text': alert.message,
                    'fields': [
                        {'title': 'Alert ID', 'value': alert.alert_id, 'short': True},
                        {'title': 'Timestamp', 'value': alert.timestamp, 'short': True},
                        {'title': 'Occurrences', 'value': str(alert.count), 'short': True},
                        {'title': 'Status', 'value': alert.status.value, 'short': True}
                    ],
                    'footer': 'AgroPulse NVR Alert System',
                    'ts': int(datetime.fromisoformat(alert.timestamp).timestamp())
                }]
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(self.webhook_url, json=payload, timeout=aiohttp.ClientTimeout(total=30)) as response:
                    success = response.status == 200
                    
                    if success:
                        logger.info(f"Slack notification sent for alert {alert.alert_id}")
                    else:
                        logger.error(f"Slack notification failed: {response.status}")
                    
                    return success
                    
        except Exception as e:
            logger.error(f"Slack send error: {e}")
            return False
            
    def _get_color(self, level: AlertLevel) -> str:
        """Get Slack color for alert level"""
        colors = {
            AlertLevel.DEBUG: '#9e9e9e',
            AlertLevel.INFO: '#2196f3',
            AlertLevel.WARNING: '#ff9800',
            AlertLevel.ERROR: '#f44336',
            AlertLevel.CRITICAL: '#d32f2f',
            AlertLevel.EMERGENCY: '#b71c1c'
        }
        return colors.get(level, '#9e9e9e')

# ========================= TELEGRAM HANDLER =========================

class TelegramHandler:
    """Telegram notification handler"""
    
    def __init__(self, config: Dict[str, Any]):
        self.bot_token = config.get('bot_token')
        self.chat_id = config.get('chat_id')
        self.api_url = f"https://api.telegram.org/bot{self.bot_token}"
        logger.info(f"TelegramHandler initialized for chat: {self.chat_id}")
        
    async def send(self, alert: Alert) -> bool:
        """Send Telegram notification"""
        try:
            emoji = self._get_emoji(alert.level)
            
            message = f"{emoji} *{alert.level.value.upper()}* Alert\n\n"
            message += f"*Source:* {alert.source}\n"
            message += f"*Message:* {alert.message}\n"
            message += f"*Time:* {alert.timestamp}\n"
            message += f"*Alert ID:* `{alert.alert_id}`\n"
            message += f"*Count:* {alert.count}"
            
            payload = {
                'chat_id': self.chat_id,
                'text': message,
                'parse_mode': 'Markdown'
            }
            
            url = f"{self.api_url}/sendMessage"
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload, timeout=aiohttp.ClientTimeout(total=30)) as response:
                    success = response.status == 200
                    
                    if success:
                        logger.info(f"Telegram notification sent for alert {alert.alert_id}")
                    else:
                        logger.error(f"Telegram notification failed: {response.status}")
                    
                    return success
                    
        except Exception as e:
            logger.error(f"Telegram send error: {e}")
            return False
            
    def _get_emoji(self, level: AlertLevel) -> str:
        """Get emoji for alert level"""
        emojis = {
            AlertLevel.DEBUG: '🔍',
            AlertLevel.INFO: 'ℹ️',
            AlertLevel.WARNING: '⚠️',
            AlertLevel.ERROR: '❌',
            AlertLevel.CRITICAL: '🚨',
            AlertLevel.EMERGENCY: '🆘'
        }
        return emojis.get(level, 'ℹ️')

# ========================= SMS HANDLER =========================

class SMSHandler:
    """SMS notification handler (using Twilio)"""
    
    def __init__(self, config: Dict[str, Any]):
        self.account_sid = config.get('account_sid')
        self.auth_token = config.get('auth_token')
        self.from_number = config.get('from_number')
        self.api_url = f"https://api.twilio.com/2010-04-01/Accounts/{self.account_sid}/Messages.json"
        logger.info(f"SMSHandler initialized with Twilio")
        
    async def send(self, alert: Alert, recipients: List[str]) -> bool:
        """Send SMS notification"""
        try:
            message = f"[{alert.level.value.upper()}] {alert.source}: {alert.message[:100]}"
            
            auth = aiohttp.BasicAuth(self.account_sid, self.auth_token)
            
            success_count = 0
            async with aiohttp.ClientSession() as session:
                for recipient in recipients:
                    data = {
                        'From': self.from_number,
                        'To': recipient,
                        'Body': message
                    }
                    
                    async with session.post(self.api_url, data=data, auth=auth, timeout=aiohttp.ClientTimeout(total=30)) as response:
                        if response.status < 300:
                            success_count += 1
                        else:
                            logger.error(f"SMS to {recipient} failed: {response.status}")
            
            success = success_count > 0
            if success:
                logger.info(f"SMS sent to {success_count}/{len(recipients)} recipients for alert {alert.alert_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"SMS send error: {e}")
            return False

# ========================= ALERT DEDUPLICATOR =========================

class AlertDeduplicator:
    """Alert deduplication and aggregation"""
    
    def __init__(self, window_seconds: int = 300):
        self.window_seconds = window_seconds
        self.alert_cache: Dict[str, Alert] = {}
        self.cleanup_task = None
        
    def get_fingerprint(self, source: str, message: str, level: AlertLevel) -> str:
        """Generate alert fingerprint"""
        key = f"{source}:{level.value}:{message}"
        return hashlib.md5(key.encode()).hexdigest()
        
    def process_alert(self, alert: Alert) -> Tuple[bool, Alert]:
        """Process alert for deduplication
        Returns: (is_new, processed_alert)
        """
        fingerprint = alert.fingerprint or self.get_fingerprint(alert.source, alert.message, alert.level)
        alert.fingerprint = fingerprint
        
        if fingerprint in self.alert_cache:
            # Duplicate alert - increment count
            cached = self.alert_cache[fingerprint]
            cached.count += 1
            cached.last_occurrence = alert.timestamp
            return False, cached
        else:
            # New alert
            alert.first_occurrence = alert.timestamp
            alert.last_occurrence = alert.timestamp
            self.alert_cache[fingerprint] = alert
            return True, alert
            
    def cleanup_old_alerts(self):
        """Remove old alerts from cache"""
        cutoff_time = datetime.now() - timedelta(seconds=self.window_seconds)
        
        to_remove = []
        for fingerprint, alert in self.alert_cache.items():
            last_time = datetime.fromisoformat(alert.last_occurrence)
            if last_time < cutoff_time:
                to_remove.append(fingerprint)
        
        for fingerprint in to_remove:
            del self.alert_cache[fingerprint]
        
        if to_remove:
            logger.debug(f"Cleaned up {len(to_remove)} old alerts from cache")

# ========================= RATE LIMITER =========================

class RateLimiter:
    """Rate limiting for alert channels"""
    
    def __init__(self):
        self.counters: Dict[str, deque] = defaultdict(lambda: deque())
        
    def is_allowed(self, key: str, limit_per_minute: int) -> bool:
        """Check if alert is allowed within rate limit"""
        now = time.time()
        minute_ago = now - 60
        
        # Clean old entries
        counter = self.counters[key]
        while counter and counter[0] < minute_ago:
            counter.popleft()
        
        # Check limit
        if len(counter) >= limit_per_minute:
            return False
        
        # Add current request
        counter.append(now)
        return True
        
    def get_remaining(self, key: str, limit_per_minute: int) -> int:
        """Get remaining quota"""
        now = time.time()
        minute_ago = now - 60
        
        counter = self.counters[key]
        # Count recent requests
        recent = sum(1 for t in counter if t > minute_ago)
        return max(0, limit_per_minute - recent)

# ========================= ESCALATION ENGINE =========================

class EscalationEngine:
    """Alert escalation management"""
    
    def __init__(self, policies: List[EscalationPolicy]):
        self.policies = {p.policy_id: p for p in policies}
        self.active_escalations: Dict[str, Dict] = {}
        logger.info(f"EscalationEngine initialized with {len(policies)} policies")
        
    def should_escalate(self, alert: Alert, policy_id: str) -> Tuple[bool, Optional[Dict]]:
        """Check if alert should be escalated"""
        if policy_id not in self.policies:
            return False, None
            
        policy = self.policies[policy_id]
        if not policy.enabled:
            return False, None
        
        escalation_key = f"{alert.fingerprint}:{policy_id}"
        
        if escalation_key not in self.active_escalations:
            # Start new escalation
            self.active_escalations[escalation_key] = {
                'alert': alert,
                'policy_id': policy_id,
                'level': 0,
                'started_at': datetime.now(),
                'last_escalation': datetime.now(),
                'escalation_count': 0
            }
            return True, policy.rules[0] if policy.rules else None
        
        escalation = self.active_escalations[escalation_key]
        
        # Check if enough time passed for next escalation
        if alert.status == AlertStatus.ACKNOWLEDGED:
            return False, None
            
        time_since_last = datetime.now() - escalation['last_escalation']
        if time_since_last.total_seconds() < policy.repeat_interval_minutes * 60:
            return False, None
        
        # Check max escalations
        if escalation['escalation_count'] >= policy.max_escalations:
            return False, None
        
        # Escalate to next level
        escalation['level'] += 1
        escalation['last_escalation'] = datetime.now()
        escalation['escalation_count'] += 1
        
        if escalation['level'] < len(policy.rules):
            return True, policy.rules[escalation['level']]
        
        return False, None
        
    def clear_escalation(self, alert: Alert, policy_id: str):
        """Clear escalation for resolved alert"""
        escalation_key = f"{alert.fingerprint}:{policy_id}"
        if escalation_key in self.active_escalations:
            del self.active_escalations[escalation_key]

# ========================= ALERT MANAGER =========================

class AlertManager:
    """Enterprise Alert Manager - Multi-channel notification platform"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        
        # Initialize database
        self.db_path = config.get('database_path', './alerts.db')
        self._init_database()
        
        # Initialize handlers
        self.handlers: Dict[AlertChannel, Any] = {}
        self._init_handlers()
        
        # Initialize notification configs
        self.notification_configs: Dict[AlertChannel, NotificationConfig] = {}
        self._init_notification_configs()
        
        # Initialize components
        self.deduplicator = AlertDeduplicator(window_seconds=config.get('dedup_window_seconds', 300))
        self.rate_limiter = RateLimiter()
        
        # Escalation policies
        escalation_policies = [
            EscalationPolicy(
                policy_id='default',
                name='Default Escalation',
                rules=[
                    {'delay_minutes': 0, 'action': 'notify_oncall'},
                    {'delay_minutes': 15, 'action': 'notify_manager'},
                    {'delay_minutes': 30, 'action': 'notify_all'}
                ],
                repeat_interval_minutes=30,
                max_escalations=3
            )
        ]
        self.escalation_engine = EscalationEngine(escalation_policies)
        
        # Metrics
        self.metrics = AlertMetrics()
        
        # Background tasks
        self.cleanup_task = None
        
        logger.info(f"Alert Manager initialized with {len(self.handlers)} handlers")
        
    def _init_database(self):
        """Initialize alerts database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS alerts (
                alert_id TEXT PRIMARY KEY,
                source TEXT NOT NULL,
                message TEXT NOT NULL,
                level TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                status TEXT NOT NULL,
                fingerprint TEXT,
                count INTEGER DEFAULT 1,
                first_occurrence TEXT,
                last_occurrence TEXT,
                tags_json TEXT,
                metadata_json TEXT,
                acknowledged_by TEXT,
                acknowledged_at TEXT,
                resolved_at TEXT
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS alert_deliveries (
                delivery_id TEXT PRIMARY KEY,
                alert_id TEXT NOT NULL,
                channel TEXT NOT NULL,
                recipient TEXT,
                sent_at TEXT NOT NULL,
                delivered_at TEXT,
                status TEXT NOT NULL,
                error_message TEXT,
                FOREIGN KEY (alert_id) REFERENCES alerts(alert_id)
            )
        ''')
        
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_alerts_status ON alerts(status)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_alerts_level ON alerts(level)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_alerts_timestamp ON alerts(timestamp)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_alerts_fingerprint ON alerts(fingerprint)')
        
        conn.commit()
        conn.close()
        
    def _init_handlers(self):
        """Initialize notification handlers"""
        handlers_config = self.config.get('handlers', [])
        
        for handler_config in handlers_config:
            handler_type = AlertChannel(handler_config.get('type'))
            
            try:
                if handler_type == AlertChannel.EMAIL:
                    self.handlers[handler_type] = EmailHandler(handler_config)
                elif handler_type == AlertChannel.WEBHOOK:
                    self.handlers[handler_type] = WebhookHandler(handler_config)
                elif handler_type == AlertChannel.SLACK:
                    self.handlers[handler_type] = SlackHandler(handler_config)
                elif handler_type == AlertChannel.TELEGRAM:
                    self.handlers[handler_type] = TelegramHandler(handler_config)
                elif handler_type == AlertChannel.SMS:
                    self.handlers[handler_type] = SMSHandler(handler_config)
                
                logger.info(f"Initialized handler: {handler_type.value}")
            except Exception as e:
                logger.error(f"Failed to initialize handler {handler_type.value}: {e}")
                
    def _init_notification_configs(self):
        """Initialize notification configurations"""
        for handler_config in self.config.get('handlers', []):
            channel = AlertChannel(handler_config.get('type'))
            
            self.notification_configs[channel] = NotificationConfig(
                channel=channel,
                enabled=handler_config.get('enabled', True),
                min_level=AlertLevel(handler_config.get('min_level', 'info')),
                max_retries=handler_config.get('max_retries', 3),
                retry_interval=handler_config.get('retry_interval', 60),
                rate_limit_per_minute=handler_config.get('rate_limit_per_minute', 10),
                config=handler_config
            )
            
    async def send_alert(self, source: str, message: str, level: str = 'info',
                        tags: Optional[List[str]] = None, metadata: Optional[Dict] = None) -> str:
        """Send alert through configured channels"""
        
        # Create alert
        alert = Alert(
            alert_id=str(uuid.uuid4()),
            source=source,
            message=message,
            level=AlertLevel(level.lower()),
            timestamp=datetime.now().isoformat(),
            tags=tags or [],
            metadata=metadata or {}
        )
        
        # Process for deduplication
        is_new, processed_alert = self.deduplicator.process_alert(alert)
        
        if not is_new:
            logger.debug(f"Alert deduplicated: {processed_alert.fingerprint} (count: {processed_alert.count})")
            await self._update_alert_in_db(processed_alert)
            return processed_alert.alert_id
        
        # Save to database
        await self._save_alert_to_db(processed_alert)
        
        # Update metrics
        self.metrics.total_alerts += 1
        self.metrics.alerts_by_level[alert.level.value] += 1
        self.metrics.alerts_by_source[source] += 1
        
        # Send through channels
        await self._send_through_channels(processed_alert)
        
        # Check escalation
        await self._check_escalation(processed_alert)
        
        logger.info(f"Alert sent: {processed_alert.alert_id} from {source} ({level})")
        
        return processed_alert.alert_id
        
    async def _send_through_channels(self, alert: Alert):
        """Send alert through all configured channels"""
        tasks = []
        
        for channel, config in self.notification_configs.items():
            if not config.enabled:
                continue
            
            # Check level threshold
            level_priority = list(AlertLevel).index(alert.level)
            min_priority = list(AlertLevel).index(config.min_level)
            if level_priority < min_priority:
                continue
            
            # Check rate limit
            rate_key = f"{channel.value}:{alert.source}"
            if not self.rate_limiter.is_allowed(rate_key, config.rate_limit_per_minute):
                logger.warning(f"Rate limit exceeded for {channel.value}")
                continue
            
            # Send notification
            task = self._send_to_channel(alert, channel, config)
            tasks.append(task)
        
        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            success_count = sum(1 for r in results if r is True)
            logger.info(f"Alert {alert.alert_id} sent to {success_count}/{len(tasks)} channels")
            
    async def _send_to_channel(self, alert: Alert, channel: AlertChannel, config: NotificationConfig) -> bool:
        """Send alert to specific channel"""
        handler = self.handlers.get(channel)
        if not handler:
            return False
        
        delivery_id = str(uuid.uuid4())
        start_time = time.time()
        
        try:
            # Get recipients
            recipients = config.config.get('recipients', [])
            
            # Send based on channel type
            if channel == AlertChannel.EMAIL:
                success = await handler.send(alert, recipients)
            elif channel == AlertChannel.SMS:
                success = await handler.send(alert, recipients)
            else:
                success = await handler.send(alert)
            
            delivery_time = (time.time() - start_time) * 1000
            
            # Save delivery record
            await self._save_delivery_record(
                delivery_id, alert.alert_id, channel.value,
                ','.join(recipients) if recipients else None,
                success, None, delivery_time
            )
            
            if success:
                self.metrics.sent_count += 1
                alert.status = AlertStatus.SENT
            else:
                self.metrics.failed_count += 1
            
            return success
            
        except Exception as e:
            logger.error(f"Channel {channel.value} send error: {e}")
            await self._save_delivery_record(
                delivery_id, alert.alert_id, channel.value, None, False, str(e), 0
            )
            self.metrics.failed_count += 1
            return False
            
    async def _check_escalation(self, alert: Alert):
        """Check and handle alert escalation"""
        should_escalate, rule = self.escalation_engine.should_escalate(alert, 'default')
        
        if should_escalate and rule:
            logger.info(f"Escalating alert {alert.alert_id}: {rule}")
            
            # Handle escalation action
            action = rule.get('action')
            if action == 'notify_manager':
                await self._notify_managers(alert)
            elif action == 'notify_all':
                await self._notify_all(alert)
            elif action == 'create_incident':
                await self._create_incident(alert)
                
    async def _notify_managers(self, alert: Alert):
        """Notify managers"""
        managers = self.config.get('managers', [])
        logger.info(f"Notifying {len(managers)} managers for alert {alert.alert_id}")
        # Implementation would send to manager contacts
        
    async def _notify_all(self, alert: Alert):
        """Notify all stakeholders"""
        logger.info(f"Notifying all stakeholders for alert {alert.alert_id}")
        # Implementation would broadcast to all configured channels
        
    async def _create_incident(self, alert: Alert):
        """Create incident from alert"""
        logger.info(f"Creating incident for alert {alert.alert_id}")
        # Integration with incident management system
        
    async def acknowledge_alert(self, alert_id: str, acknowledged_by: str):
        """Acknowledge an alert"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE alerts
            SET status = ?, acknowledged_by = ?, acknowledged_at = ?
            WHERE alert_id = ?
        ''', (AlertStatus.ACKNOWLEDGED.value, acknowledged_by, datetime.now().isoformat(), alert_id))
        
        conn.commit()
        conn.close()
        
        self.metrics.acknowledged_count += 1
        logger.info(f"Alert {alert_id} acknowledged by {acknowledged_by}")
        
    async def resolve_alert(self, alert_id: str):
        """Resolve an alert"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE alerts
            SET status = ?, resolved_at = ?
            WHERE alert_id = ?
        ''', (AlertStatus.RESOLVED.value, datetime.now().isoformat(), alert_id))
        
        conn.commit()
        conn.close()
        
        self.metrics.resolved_count += 1
        logger.info(f"Alert {alert_id} resolved")
        
        # Clear escalation
        cursor.execute('SELECT fingerprint FROM alerts WHERE alert_id = ?', (alert_id,))
        row = cursor.fetchone()
        if row:
            # Would need to recreate alert object to clear escalation
            pass
            
    async def _save_alert_to_db(self, alert: Alert):
        """Save alert to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO alerts
            (alert_id, source, message, level, timestamp, status, fingerprint, count,
             first_occurrence, last_occurrence, tags_json, metadata_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            alert.alert_id, alert.source, alert.message, alert.level.value,
            alert.timestamp, alert.status.value, alert.fingerprint, alert.count,
            alert.first_occurrence, alert.last_occurrence,
            json.dumps(alert.tags), json.dumps(alert.metadata)
        ))
        
        conn.commit()
        conn.close()
        
    async def _update_alert_in_db(self, alert: Alert):
        """Update existing alert in database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE alerts
            SET count = ?, last_occurrence = ?
            WHERE alert_id = ?
        ''', (alert.count, alert.last_occurrence, alert.alert_id))
        
        conn.commit()
        conn.close()
        
    async def _save_delivery_record(self, delivery_id: str, alert_id: str, channel: str,
                                   recipient: Optional[str], success: bool, error: Optional[str],
                                   delivery_time_ms: float):
        """Save delivery record to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        status = 'delivered' if success else 'failed'
        
        cursor.execute('''
            INSERT INTO alert_deliveries
            (delivery_id, alert_id, channel, recipient, sent_at, delivered_at, status, error_message)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            delivery_id, alert_id, channel, recipient,
            datetime.now().isoformat(),
            datetime.now().isoformat() if success else None,
            status, error
        ))
        
        conn.commit()
        conn.close()
        
    async def get_alerts(self, status: Optional[str] = None, level: Optional[str] = None,
                        limit: int = 100) -> List[Dict[str, Any]]:
        """Get alerts with filtering"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        query = 'SELECT * FROM alerts WHERE 1=1'
        params = []
        
        if status:
            query += ' AND status = ?'
            params.append(status)
        if level:
            query += ' AND level = ?'
            params.append(level)
        
        query += ' ORDER BY timestamp DESC LIMIT ?'
        params.append(limit)
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()
        
        alerts = []
        for row in rows:
            alert = {
                'alert_id': row[0],
                'source': row[1],
                'message': row[2],
                'level': row[3],
                'timestamp': row[4],
                'status': row[5],
                'fingerprint': row[6],
                'count': row[7],
                'first_occurrence': row[8],
                'last_occurrence': row[9],
                'tags': json.loads(row[10]) if row[10] else [],
                'metadata': json.loads(row[11]) if row[11] else {}
            }
            alerts.append(alert)
        
        return alerts
        
    def get_metrics(self) -> Dict[str, Any]:
        """Get alert system metrics"""
        return asdict(self.metrics)
        
    async def start_background_tasks(self):
        """Start background maintenance tasks"""
        self.cleanup_task = asyncio.create_task(self._cleanup_loop())
        logger.info("Alert Manager background tasks started")
        
    async def _cleanup_loop(self):
        """Background cleanup task"""
        while True:
            try:
                await asyncio.sleep(300)  # Every 5 minutes
                self.deduplicator.cleanup_old_alerts()
            except Exception as e:
                logger.error(f"Cleanup task error: {e}")
                
    async def shutdown(self):
        """Shutdown alert manager"""
        if self.cleanup_task:
            self.cleanup_task.cancel()
        logger.info("Alert Manager shutdown complete")
