# ========================================================================================
# ENTERPRISE AUTOMATION ENGINE
# Advanced rule-based automation with complex conditions, actions, workflows,
# scheduling, state machines, MQTT/Webhook/API integrations, and scripting support
# ========================================================================================

import logging
import asyncio
import aiohttp
import json
import re
import smtplib
import hashlib
import hmac
from typing import Dict, List, Optional, Any, Callable, Union, Set, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field, asdict
from enum import Enum
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from collections import defaultdict, deque
import uuid
import ast
import operator
from abc import ABC, abstractmethod
import threading
import time
import importlib.util
import sys
import os

logger = logging.getLogger(__name__)

# ========================== ENUMERATIONS ==========================

class TriggerType(Enum):
    """Automation trigger types"""
    EVENT_DETECTED = "event_detected"
    MOTION_DETECTED = "motion_detected"
    FACE_RECOGNIZED = "face_recognized"
    LPR_MATCH = "lpr_match"
    LINE_CROSSED = "line_crossed"
    INTRUSION = "intrusion"
    CAMERA_OFFLINE = "camera_offline"
    CAMERA_ONLINE = "camera_online"
    STORAGE_THRESHOLD = "storage_threshold"
    SCHEDULED = "scheduled"
    WEBHOOK = "webhook"
    MANUAL = "manual"
    STATE_CHANGE = "state_change"
    TIME_BASED = "time_based"
    TEMPERATURE = "temperature"
    SENSOR = "sensor"
    DEVICE_ALARM = "device_alarm"
    AUDIO_DETECTED = "audio_detected"
    LOITERING = "loitering"
    ABANDONED_OBJECT = "abandoned_object"
    CROWD_DETECTED = "crowd_detected"
    TAILGATING = "tailgating"


class ActionType(Enum):
    """Automation action types"""
    SEND_WEBHOOK = "send_webhook"
    SEND_MQTT = "send_mqtt"
    SEND_EMAIL = "send_email"
    SEND_SMS = "send_sms"
    SEND_NOTIFICATION = "send_notification"
    START_RECORDING = "start_recording"
    STOP_RECORDING = "stop_recording"
    SNAPSHOT = "snapshot"
    PTZ_PRESET = "ptz_preset"
    PTZ_PATROL = "ptz_patrol"
    CREATE_INCIDENT = "create_incident"
    EXECUTE_SCRIPT = "execute_script"
    CALL_API = "call_api"
    TRIGGER_ALARM = "trigger_alarm"
    LOCK_DOOR = "lock_door"
    UNLOCK_DOOR = "unlock_door"
    TURN_ON_LIGHT = "turn_on_light"
    TURN_OFF_LIGHT = "turn_off_light"
    PLAY_AUDIO = "play_audio"
    EXECUTE_WORKFLOW = "execute_workflow"
    SET_VARIABLE = "set_variable"
    INCREMENT_COUNTER = "increment_counter"
    LOG_EVENT = "log_event"
    FORWARD_TO_SIEM = "forward_to_siem"


class ConditionOperator(Enum):
    """Condition operators"""
    EQUALS = "=="
    NOT_EQUALS = "!="
    GREATER_THAN = ">"
    LESS_THAN = "<"
    GREATER_EQUAL = ">="
    LESS_EQUAL = "<="
    CONTAINS = "contains"
    NOT_CONTAINS = "not_contains"
    MATCHES = "matches"
    IN = "in"
    NOT_IN = "not_in"
    STARTS_WITH = "starts_with"
    ENDS_WITH = "ends_with"
    IS_NULL = "is_null"
    IS_NOT_NULL = "is_not_null"


class RuleState(Enum):
    """Rule execution state"""
    IDLE = "idle"
    TRIGGERED = "triggered"
    EVALUATING = "evaluating"
    EXECUTING = "executing"
    COOLDOWN = "cooldown"
    DISABLED = "disabled"
    ERROR = "error"


class WorkflowState(Enum):
    """Workflow execution state"""
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ScheduleType(Enum):
    """Schedule types"""
    ONCE = "once"
    RECURRING = "recurring"
    CRON = "cron"
    INTERVAL = "interval"
    SUNRISE = "sunrise"
    SUNSET = "sunset"


class LogicOperator(Enum):
    """Logic operators for condition groups"""
    AND = "and"
    OR = "or"
    NOT = "not"
    XOR = "xor"


class Priority(Enum):
    """Rule priority levels"""
    CRITICAL = 1
    HIGH = 2
    MEDIUM = 3
    LOW = 4
    INFO = 5


# ========================== DATA CLASSES ==========================

@dataclass
class Condition:
    """Rule condition"""
    field: str
    operator: ConditionOperator
    value: Any
    logic_operator: LogicOperator = LogicOperator.AND
    negate: bool = False


@dataclass
class ConditionGroup:
    """Group of conditions with logic"""
    conditions: List[Union[Condition, 'ConditionGroup']]
    logic_operator: LogicOperator = LogicOperator.AND


@dataclass
class Action:
    """Automation action"""
    action_id: str
    action_type: ActionType
    parameters: Dict[str, Any]
    delay_seconds: float = 0.0
    timeout_seconds: float = 30.0
    retry_count: int = 0
    retry_delay: float = 5.0
    continue_on_error: bool = False


@dataclass
class Schedule:
    """Schedule configuration"""
    schedule_type: ScheduleType
    cron_expression: Optional[str] = None
    interval_seconds: Optional[int] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    days_of_week: Optional[List[int]] = None
    timezone: str = "UTC"


@dataclass
class AutomationRule:
    """Automation rule"""
    rule_id: str
    name: str
    description: str
    trigger_type: TriggerType
    trigger_source: Optional[str] = None
    condition_groups: List[ConditionGroup] = field(default_factory=list)
    actions: List[Action] = field(default_factory=list)
    enabled: bool = True
    priority: Priority = Priority.MEDIUM
    cooldown_seconds: int = 60
    max_executions_per_hour: int = 100
    max_executions_per_day: int = 1000
    schedule: Optional[Schedule] = None
    state: RuleState = RuleState.IDLE
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())


@dataclass
class RuleExecution:
    """Rule execution record"""
    execution_id: str
    rule_id: str
    timestamp: str
    trigger_data: Dict[str, Any]
    conditions_met: bool
    actions_executed: List[str]
    success: bool
    duration_ms: float
    error: Optional[str] = None


@dataclass
class WorkflowStep:
    """Workflow step"""
    step_id: str
    name: str
    action: Action
    conditions: List[Condition] = field(default_factory=list)
    on_success: Optional[str] = None  # Next step ID
    on_failure: Optional[str] = None  # Next step ID on failure
    parallel: bool = False


@dataclass
class Workflow:
    """Multi-step workflow"""
    workflow_id: str
    name: str
    description: str
    steps: List[WorkflowStep]
    enabled: bool = True
    state: WorkflowState = WorkflowState.PENDING
    current_step: Optional[str] = None
    variables: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ExecutionContext:
    """Execution context for rules and workflows"""
    context_id: str
    trigger_type: TriggerType
    trigger_data: Dict[str, Any]
    timestamp: str
    variables: Dict[str, Any] = field(default_factory=dict)
    counters: Dict[str, int] = field(default_factory=dict)


# ========================== CONDITION EVALUATOR ==========================

class ConditionEvaluator:
    """Evaluate rule conditions"""
    
    def __init__(self):
        self.operators = {
            ConditionOperator.EQUALS: operator.eq,
            ConditionOperator.NOT_EQUALS: operator.ne,
            ConditionOperator.GREATER_THAN: operator.gt,
            ConditionOperator.LESS_THAN: operator.lt,
            ConditionOperator.GREATER_EQUAL: operator.ge,
            ConditionOperator.LESS_EQUAL: operator.le,
        }
    
    def evaluate(self, condition: Condition, data: Dict[str, Any]) -> bool:
        """Evaluate single condition"""
        try:
            # Get field value from data
            field_value = self._get_nested_value(data, condition.field)
            
            # Handle null checks
            if condition.operator == ConditionOperator.IS_NULL:
                result = field_value is None
            elif condition.operator == ConditionOperator.IS_NOT_NULL:
                result = field_value is not None
            elif field_value is None:
                return False
            # Apply operator
            elif condition.operator in self.operators:
                result = self.operators[condition.operator](field_value, condition.value)
            elif condition.operator == ConditionOperator.CONTAINS:
                result = condition.value in str(field_value)
            elif condition.operator == ConditionOperator.NOT_CONTAINS:
                result = condition.value not in str(field_value)
            elif condition.operator == ConditionOperator.MATCHES:
                result = bool(re.match(condition.value, str(field_value)))
            elif condition.operator == ConditionOperator.IN:
                result = field_value in condition.value
            elif condition.operator == ConditionOperator.NOT_IN:
                result = field_value not in condition.value
            elif condition.operator == ConditionOperator.STARTS_WITH:
                result = str(field_value).startswith(condition.value)
            elif condition.operator == ConditionOperator.ENDS_WITH:
                result = str(field_value).endswith(condition.value)
            else:
                logger.warning(f"Unknown operator: {condition.operator}")
                result = False
            
            # Apply negation if needed
            return not result if condition.negate else result
            
        except Exception as e:
            logger.error(f"Condition evaluation error: {e}")
            return False
    
    def evaluate_group(self, group: ConditionGroup, data: Dict[str, Any]) -> bool:
        """Evaluate condition group"""
        if not group.conditions:
            return True
        
        results = []
        for item in group.conditions:
            if isinstance(item, Condition):
                results.append(self.evaluate(item, data))
            elif isinstance(item, ConditionGroup):
                results.append(self.evaluate_group(item, data))
        
        if group.logic_operator == LogicOperator.AND:
            return all(results)
        elif group.logic_operator == LogicOperator.OR:
            return any(results)
        elif group.logic_operator == LogicOperator.NOT:
            return not all(results)
        elif group.logic_operator == LogicOperator.XOR:
            return sum(results) == 1
        
        return all(results)
    
    def evaluate_all(self, condition_groups: List[ConditionGroup], data: Dict[str, Any]) -> bool:
        """Evaluate all condition groups"""
        if not condition_groups:
            return True
        
        # All groups must pass (AND logic between groups)
        return all(self.evaluate_group(group, data) for group in condition_groups)
    
    def _get_nested_value(self, data: Dict, field_path: str) -> Any:
        """Get nested dictionary value using dot notation"""
        keys = field_path.split('.')
        value = data
        
        for key in keys:
            if isinstance(value, dict):
                value = value.get(key)
            elif isinstance(value, (list, tuple)) and key.isdigit():
                idx = int(key)
                value = value[idx] if idx < len(value) else None
            else:
                return None
        
        return value


# ========================== ACTION EXECUTOR ==========================

class ActionExecutor:
    """Execute automation actions"""
    
    def __init__(self, nvr_system):
        self.nvr = nvr_system
        self.smtp_config = nvr_system.config.get('smtp', {}) if hasattr(nvr_system, 'config') else {}
        self.mqtt_client = None
        self.action_handlers: Dict[ActionType, Callable] = {}
        self._register_handlers()
    
    def _register_handlers(self):
        """Register action handlers"""
        self.action_handlers = {
            ActionType.SEND_WEBHOOK: self._execute_webhook,
            ActionType.SEND_MQTT: self._execute_mqtt,
            ActionType.SEND_EMAIL: self._execute_email,
            ActionType.SEND_SMS: self._execute_sms,
            ActionType.SEND_NOTIFICATION: self._execute_notification,
            ActionType.START_RECORDING: self._execute_start_recording,
            ActionType.STOP_RECORDING: self._execute_stop_recording,
            ActionType.SNAPSHOT: self._execute_snapshot,
            ActionType.PTZ_PRESET: self._execute_ptz_preset,
            ActionType.CREATE_INCIDENT: self._execute_create_incident,
            ActionType.EXECUTE_SCRIPT: self._execute_script,
            ActionType.CALL_API: self._execute_api_call,
            ActionType.TRIGGER_ALARM: self._execute_trigger_alarm,
            ActionType.LOCK_DOOR: self._execute_lock_door,
            ActionType.UNLOCK_DOOR: self._execute_unlock_door,
            ActionType.PLAY_AUDIO: self._execute_play_audio,
            ActionType.SET_VARIABLE: self._execute_set_variable,
            ActionType.LOG_EVENT: self._execute_log_event,
        }
    
    async def execute(self, action: Action, context: ExecutionContext) -> bool:
        """Execute single action with retry logic"""
        attempt = 0
        max_attempts = action.retry_count + 1
        
        while attempt < max_attempts:
            try:
                # Apply delay
                if action.delay_seconds > 0:
                    await asyncio.sleep(action.delay_seconds)
                
                # Get handler
                handler = self.action_handlers.get(action.action_type)
                if not handler:
                    logger.warning(f"Unknown action type: {action.action_type}")
                    return False
                
                # Execute with timeout
                result = await asyncio.wait_for(
                    handler(action.parameters, context),
                    timeout=action.timeout_seconds
                )
                
                if result:
                    return True
                
                # Retry logic
                attempt += 1
                if attempt < max_attempts:
                    logger.warning(f"Action {action.action_id} failed, retrying ({attempt}/{max_attempts})")
                    await asyncio.sleep(action.retry_delay)
                
            except asyncio.TimeoutError:
                logger.error(f"Action {action.action_id} timed out after {action.timeout_seconds}s")
                attempt += 1
                if attempt < max_attempts:
                    await asyncio.sleep(action.retry_delay)
                    
            except Exception as e:
                logger.error(f"Action execution error: {e}", exc_info=True)
                if action.continue_on_error:
                    return True
                attempt += 1
                if attempt < max_attempts:
                    await asyncio.sleep(action.retry_delay)
        
        return False
    
    async def execute_all(self, actions: List[Action], context: ExecutionContext) -> List[str]:
        """Execute all actions and return executed action IDs"""
        executed = []
        
        for action in actions:
            success = await self.execute(action, context)
            if success:
                executed.append(action.action_id)
            elif not action.continue_on_error:
                logger.error(f"Action {action.action_id} failed, stopping execution chain")
                break
        
        return executed
    
    async def _execute_webhook(self, params: Dict, context: ExecutionContext) -> bool:
        """Send webhook"""
        url = params.get('url')
        method = params.get('method', 'POST').upper()
        headers = params.get('headers', {})
        payload = self._template_replace(params.get('payload', {}), context)
        verify_ssl = params.get('verify_ssl', True)
        
        if not url:
            logger.error("Webhook URL not specified")
            return False
        
        try:
            async with aiohttp.ClientSession() as session:
                kwargs = {
                    'headers': headers,
                    'ssl': verify_ssl
                }
                
                if method == 'POST':
                    kwargs['json'] = payload
                    async with session.post(url, **kwargs) as response:
                        return response.status < 400
                elif method == 'GET':
                    kwargs['params'] = payload
                    async with session.get(url, **kwargs) as response:
                        return response.status < 400
                elif method == 'PUT':
                    kwargs['json'] = payload
                    async with session.put(url, **kwargs) as response:
                        return response.status < 400
                else:
                    logger.error(f"Unsupported HTTP method: {method}")
                    return False
                    
        except Exception as e:
            logger.error(f"Webhook execution error: {e}")
            return False
    
    async def _execute_mqtt(self, params: Dict, context: ExecutionContext) -> bool:
        """Send MQTT message"""
        topic = params.get('topic')
        payload = self._template_replace(params.get('payload', {}), context)
        qos = params.get('qos', 0)
        retain = params.get('retain', False)
        
        if not topic:
            logger.error("MQTT topic not specified")
            return False
        
        if not self.mqtt_client:
            logger.error("MQTT client not initialized")
            return False
        
        try:
            message = json.dumps(payload) if isinstance(payload, dict) else str(payload)
            self.mqtt_client.publish(topic, message, qos=qos, retain=retain)
            return True
        except Exception as e:
            logger.error(f"MQTT execution error: {e}")
            return False
    
    async def _execute_email(self, params: Dict, context: ExecutionContext) -> bool:
        """Send email"""
        to_addresses = params.get('to', [])
        subject = self._template_replace(params.get('subject', 'Automation Alert'), context)
        body = self._template_replace(params.get('body', ''), context)
        html = params.get('html', False)
        attachments = params.get('attachments', [])
        
        if not to_addresses:
            logger.error("Email recipients not specified")
            return False
        
        if not self.smtp_config:
            logger.error("SMTP not configured")
            return False
        
        try:
            msg = MIMEMultipart()
            msg['From'] = self.smtp_config.get('from')
            msg['To'] = ', '.join(to_addresses)
            msg['Subject'] = subject
            
            if html:
                msg.attach(MIMEText(body, 'html'))
            else:
                msg.attach(MIMEText(body, 'plain'))
            
            # Send email
            with smtplib.SMTP(self.smtp_config['host'], self.smtp_config.get('port', 587)) as server:
                if self.smtp_config.get('tls', True):
                    server.starttls()
                if self.smtp_config.get('username'):
                    server.login(self.smtp_config['username'], self.smtp_config['password'])
                server.send_message(msg)
            
            return True
            
        except Exception as e:
            logger.error(f"Email execution error: {e}")
            return False
    
    async def _execute_sms(self, params: Dict, context: ExecutionContext) -> bool:
        """Send SMS (via Twilio or similar)"""
        to_numbers = params.get('to', [])
        message = self._template_replace(params.get('message', ''), context)
        
        # Implementation would depend on SMS provider
        logger.info(f"SMS action: {message} to {to_numbers}")
        return True
    
    async def _execute_notification(self, params: Dict, context: ExecutionContext) -> bool:
        """Send push notification"""
        users = params.get('users', [])
        title = self._template_replace(params.get('title', ''), context)
        message = self._template_replace(params.get('message', ''), context)
        priority = params.get('priority', 'normal')
        
        try:
            # Send to notification service
            if hasattr(self.nvr, 'notification_manager'):
                await self.nvr.notification_manager.send_notification(
                    users=users,
                    title=title,
                    message=message,
                    priority=priority
                )
            return True
        except Exception as e:
            logger.error(f"Notification error: {e}")
            return False
    
    async def _execute_start_recording(self, params: Dict, context: ExecutionContext) -> bool:
        """Start recording on camera"""
        camera_id = params.get('camera_id')
        duration = params.get('duration')
        
        if not camera_id:
            logger.error("Camera ID not specified")
            return False
        
        try:
            if hasattr(self.nvr, 'cameras'):
                camera = self.nvr.cameras.get(camera_id)
                if camera:
                    await camera.start_recording(duration=duration)
                    return True
            return False
        except Exception as e:
            logger.error(f"Start recording error: {e}")
            return False
    
    async def _execute_stop_recording(self, params: Dict, context: ExecutionContext) -> bool:
        """Stop recording on camera"""
        camera_id = params.get('camera_id')
        
        if not camera_id:
            logger.error("Camera ID not specified")
            return False
        
        try:
            if hasattr(self.nvr, 'cameras'):
                camera = self.nvr.cameras.get(camera_id)
                if camera:
                    await camera.stop_recording()
                    return True
            return False
        except Exception as e:
            logger.error(f"Stop recording error: {e}")
            return False
    
    async def _execute_snapshot(self, params: Dict, context: ExecutionContext) -> bool:
        """Capture snapshot from camera"""
        camera_id = params.get('camera_id')
        save_path = params.get('save_path')
        
        if not camera_id:
            logger.error("Camera ID not specified")
            return False
        
        try:
            if hasattr(self.nvr, 'cameras'):
                camera = self.nvr.cameras.get(camera_id)
                if camera:
                    snapshot = await camera.capture_snapshot()
                    if save_path:
                        with open(save_path, 'wb') as f:
                            f.write(snapshot)
                    return True
            return False
        except Exception as e:
            logger.error(f"Snapshot error: {e}")
            return False
    
    async def _execute_ptz_preset(self, params: Dict, context: ExecutionContext) -> bool:
        """Move PTZ camera to preset"""
        camera_id = params.get('camera_id')
        preset = params.get('preset')
        
        if not camera_id or preset is None:
            logger.error("Camera ID or preset not specified")
            return False
        
        try:
            if hasattr(self.nvr, 'cameras'):
                camera = self.nvr.cameras.get(camera_id)
                if camera and hasattr(camera, 'goto_preset'):
                    await camera.goto_preset(preset)
                    return True
            return False
        except Exception as e:
            logger.error(f"PTZ preset error: {e}")
            return False
    
    async def _execute_create_incident(self, params: Dict, context: ExecutionContext) -> bool:
        """Create incident"""
        title = self._template_replace(params.get('title', ''), context)
        description = self._template_replace(params.get('description', ''), context)
        severity = params.get('severity', 'medium')
        
        try:
            if hasattr(self.nvr, 'incident_manager'):
                incident = await self.nvr.incident_manager.create_incident(
                    title=title,
                    description=description,
                    severity=severity,
                    trigger_data=context.trigger_data
                )
                return incident is not None
            return False
        except Exception as e:
            logger.error(f"Create incident error: {e}")
            return False
    
    async def _execute_script(self, params: Dict, context: ExecutionContext) -> bool:
        """Execute Python script"""
        script_path = params.get('script_path')
        script_code = params.get('script_code')
        args = params.get('args', [])
        
        try:
            if script_path and os.path.exists(script_path):
                # Load and execute external script
                spec = importlib.util.spec_from_file_location("automation_script", script_path)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                
                if hasattr(module, 'execute'):
                    result = await module.execute(context, *args)
                    return bool(result)
            
            elif script_code:
                # Execute inline code (use with caution!)
                exec_globals = {
                    'context': context,
                    'nvr': self.nvr,
                    'logger': logger
                }
                exec(script_code, exec_globals)
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Script execution error: {e}")
            return False
    
    async def _execute_api_call(self, params: Dict, context: ExecutionContext) -> bool:
        """Call external API"""
        url = params.get('url')
        method = params.get('method', 'GET').upper()
        headers = params.get('headers', {})
        data = self._template_replace(params.get('data', {}), context)
        auth = params.get('auth')
        
        if not url:
            logger.error("API URL not specified")
            return False
        
        try:
            async with aiohttp.ClientSession() as session:
                kwargs = {'headers': headers}
                
                if auth:
                    kwargs['auth'] = aiohttp.BasicAuth(auth.get('username'), auth.get('password'))
                
                if method == 'GET':
                    async with session.get(url, params=data, **kwargs) as response:
                        return response.status < 400
                elif method == 'POST':
                    async with session.post(url, json=data, **kwargs) as response:
                        return response.status < 400
                elif method == 'PUT':
                    async with session.put(url, json=data, **kwargs) as response:
                        return response.status < 400
                elif method == 'DELETE':
                    async with session.delete(url, **kwargs) as response:
                        return response.status < 400
                        
        except Exception as e:
            logger.error(f"API call error: {e}")
            return False
    
    async def _execute_trigger_alarm(self, params: Dict, context: ExecutionContext) -> bool:
        """Trigger alarm system"""
        alarm_id = params.get('alarm_id')
        duration = params.get('duration', 10)
        
        try:
            if hasattr(self.nvr, 'alarm_manager'):
                await self.nvr.alarm_manager.trigger_alarm(alarm_id, duration)
            return True
        except Exception as e:
            logger.error(f"Trigger alarm error: {e}")
            return False
    
    async def _execute_lock_door(self, params: Dict, context: ExecutionContext) -> bool:
        """Lock door"""
        door_id = params.get('door_id')
        
        try:
            if hasattr(self.nvr, 'access_control'):
                await self.nvr.access_control.lock_door(door_id)
            return True
        except Exception as e:
            logger.error(f"Lock door error: {e}")
            return False
    
    async def _execute_unlock_door(self, params: Dict, context: ExecutionContext) -> bool:
        """Unlock door"""
        door_id = params.get('door_id')
        duration = params.get('duration', 5)
        
        try:
            if hasattr(self.nvr, 'access_control'):
                await self.nvr.access_control.unlock_door(door_id, duration)
            return True
        except Exception as e:
            logger.error(f"Unlock door error: {e}")
            return False
    
    async def _execute_play_audio(self, params: Dict, context: ExecutionContext) -> bool:
        """Play audio message"""
        camera_id = params.get('camera_id')
        audio_file = params.get('audio_file')
        message = params.get('message')
        
        try:
            if hasattr(self.nvr, 'cameras'):
                camera = self.nvr.cameras.get(camera_id)
                if camera and hasattr(camera, 'play_audio'):
                    if audio_file:
                        await camera.play_audio(audio_file)
                    elif message:
                        # Text-to-speech
                        await camera.speak(message)
            return True
        except Exception as e:
            logger.error(f"Play audio error: {e}")
            return False
    
    async def _execute_set_variable(self, params: Dict, context: ExecutionContext) -> bool:
        """Set context variable"""
        variable_name = params.get('name')
        value = params.get('value')
        
        if variable_name:
            context.variables[variable_name] = value
            return True
        return False
    
    async def _execute_log_event(self, params: Dict, context: ExecutionContext) -> bool:
        """Log event"""
        message = self._template_replace(params.get('message', ''), context)
        level = params.get('level', 'info').lower()
        
        if level == 'debug':
            logger.debug(message)
        elif level == 'info':
            logger.info(message)
        elif level == 'warning':
            logger.warning(message)
        elif level == 'error':
            logger.error(message)
        
        return True
    
    def _template_replace(self, template: Any, context: ExecutionContext) -> Any:
        """Replace template variables with context values"""
        if isinstance(template, str):
            # Replace {{variable}} with actual values
            result = template
            for key, value in context.trigger_data.items():
                result = result.replace(f"{{{{{key}}}}}", str(value))
            for key, value in context.variables.items():
                result = result.replace(f"{{{{{key}}}}}", str(value))
            return result
        elif isinstance(template, dict):
            return {k: self._template_replace(v, context) for k, v in template.items()}
        elif isinstance(template, list):
            return [self._template_replace(item, context) for item in template]
        return template


# ========================== RULE ENGINE ==========================

class RuleEngine:
    """Automation rule engine"""
    
    def __init__(self, nvr_system):
        self.nvr = nvr_system
        self.rules: Dict[str, AutomationRule] = {}
        self.condition_evaluator = ConditionEvaluator()
        self.action_executor = ActionExecutor(nvr_system)
        self.execution_history: deque = deque(maxlen=1000)
        self.rule_stats: Dict[str, Dict] = defaultdict(lambda: {
            'executions': 0,
            'successes': 0,
            'failures': 0,
            'last_execution': None,
            'last_cooldown': None
        })
        self._lock = asyncio.Lock()
    
    async def add_rule(self, rule: AutomationRule):
        """Add automation rule"""
        async with self._lock:
            self.rules[rule.rule_id] = rule
            logger.info(f"Added automation rule: {rule.name} ({rule.rule_id})")
    
    async def remove_rule(self, rule_id: str):
        """Remove automation rule"""
        async with self._lock:
            if rule_id in self.rules:
                del self.rules[rule_id]
                logger.info(f"Removed automation rule: {rule_id}")
    
    async def update_rule(self, rule: AutomationRule):
        """Update automation rule"""
        async with self._lock:
            rule.updated_at = datetime.utcnow().isoformat()
            self.rules[rule.rule_id] = rule
            logger.info(f"Updated automation rule: {rule.name} ({rule.rule_id})")
    
    async def enable_rule(self, rule_id: str):
        """Enable rule"""
        async with self._lock:
            if rule_id in self.rules:
                self.rules[rule_id].enabled = True
                self.rules[rule_id].state = RuleState.IDLE
    
    async def disable_rule(self, rule_id: str):
        """Disable rule"""
        async with self._lock:
            if rule_id in self.rules:
                self.rules[rule_id].enabled = False
                self.rules[rule_id].state = RuleState.DISABLED
    
    async def trigger_rule(self, trigger_type: TriggerType, trigger_source: Optional[str], 
                          trigger_data: Dict[str, Any]):
        """Process trigger and execute matching rules"""
        execution_id = str(uuid.uuid4())
        context = ExecutionContext(
            context_id=execution_id,
            trigger_type=trigger_type,
            trigger_data=trigger_data,
            timestamp=datetime.utcnow().isoformat()
        )
        
        # Find matching rules
        matching_rules = []
        for rule in self.rules.values():
            if not rule.enabled or rule.state == RuleState.DISABLED:
                continue
            
            # Check trigger match
            if rule.trigger_type != trigger_type:
                continue
            
            if rule.trigger_source and rule.trigger_source != trigger_source:
                continue
            
            # Check cooldown
            stats = self.rule_stats[rule.rule_id]
            if stats['last_cooldown']:
                cooldown_end = datetime.fromisoformat(stats['last_cooldown']) + timedelta(seconds=rule.cooldown_seconds)
                if datetime.utcnow() < cooldown_end:
                    continue
            
            # Check execution limits
            if stats['executions'] >= rule.max_executions_per_hour:
                logger.warning(f"Rule {rule.rule_id} exceeded hourly execution limit")
                continue
            
            matching_rules.append(rule)
        
        # Sort by priority
        matching_rules.sort(key=lambda r: r.priority.value)
        
        # Execute rules
        for rule in matching_rules:
            await self._execute_rule(rule, context)
    
    async def _execute_rule(self, rule: AutomationRule, context: ExecutionContext):
        """Execute single rule"""
        start_time = time.time()
        execution_id = context.context_id
        
        try:
            # Update state
            rule.state = RuleState.EVALUATING
            
            # Evaluate conditions
            conditions_met = self.condition_evaluator.evaluate_all(rule.condition_groups, context.trigger_data)
            
            if not conditions_met:
                logger.debug(f"Rule {rule.name} conditions not met")
                rule.state = RuleState.IDLE
                return
            
            # Execute actions
            rule.state = RuleState.EXECUTING
            logger.info(f"Executing rule: {rule.name}")
            
            actions_executed = await self.action_executor.execute_all(rule.actions, context)
            
            # Record execution
            duration_ms = (time.time() - start_time) * 1000
            execution = RuleExecution(
                execution_id=execution_id,
                rule_id=rule.rule_id,
                timestamp=context.timestamp,
                trigger_data=context.trigger_data,
                conditions_met=True,
                actions_executed=actions_executed,
                success=len(actions_executed) == len(rule.actions),
                duration_ms=duration_ms
            )
            
            self.execution_history.append(execution)
            
            # Update stats
            stats = self.rule_stats[rule.rule_id]
            stats['executions'] += 1
            if execution.success:
                stats['successes'] += 1
            else:
                stats['failures'] += 1
            stats['last_execution'] = context.timestamp
            stats['last_cooldown'] = context.timestamp
            
            # Update state
            rule.state = RuleState.COOLDOWN if rule.cooldown_seconds > 0 else RuleState.IDLE
            
            logger.info(f"Rule {rule.name} executed successfully in {duration_ms:.2f}ms")
            
        except Exception as e:
            logger.error(f"Rule execution error: {e}", exc_info=True)
            rule.state = RuleState.ERROR
            
            execution = RuleExecution(
                execution_id=execution_id,
                rule_id=rule.rule_id,
                timestamp=context.timestamp,
                trigger_data=context.trigger_data,
                conditions_met=True,
                actions_executed=[],
                success=False,
                duration_ms=(time.time() - start_time) * 1000,
                error=str(e)
            )
            self.execution_history.append(execution)
            
            stats = self.rule_stats[rule.rule_id]
            stats['failures'] += 1
    
    def get_rule(self, rule_id: str) -> Optional[AutomationRule]:
        """Get rule by ID"""
        return self.rules.get(rule_id)
    
    def get_all_rules(self) -> List[AutomationRule]:
        """Get all rules"""
        return list(self.rules.values())
    
    def get_execution_history(self, rule_id: Optional[str] = None, limit: int = 100) -> List[RuleExecution]:
        """Get execution history"""
        if rule_id:
            return [e for e in list(self.execution_history)[-limit:] if e.rule_id == rule_id]
        return list(self.execution_history)[-limit:]
    
    def get_rule_stats(self, rule_id: str) -> Dict:
        """Get rule statistics"""
        return self.rule_stats.get(rule_id, {})


# ========================== WORKFLOW ENGINE ==========================

class WorkflowEngine:
    """Workflow execution engine"""
    
    def __init__(self, nvr_system):
        self.nvr = nvr_system
        self.workflows: Dict[str, Workflow] = {}
        self.action_executor = ActionExecutor(nvr_system)
        self.condition_evaluator = ConditionEvaluator()
        self.active_workflows: Dict[str, Workflow] = {}
        self._lock = asyncio.Lock()
    
    async def add_workflow(self, workflow: Workflow):
        """Add workflow"""
        async with self._lock:
            self.workflows[workflow.workflow_id] = workflow
            logger.info(f"Added workflow: {workflow.name}")
    
    async def remove_workflow(self, workflow_id: str):
        """Remove workflow"""
        async with self._lock:
            if workflow_id in self.workflows:
                del self.workflows[workflow_id]
    
    async def execute_workflow(self, workflow_id: str, trigger_data: Dict[str, Any]) -> bool:
        """Execute workflow"""
        workflow = self.workflows.get(workflow_id)
        if not workflow or not workflow.enabled:
            return False
        
        # Create execution context
        context = ExecutionContext(
            context_id=str(uuid.uuid4()),
            trigger_type=TriggerType.MANUAL,
            trigger_data=trigger_data,
            timestamp=datetime.utcnow().isoformat(),
            variables=workflow.variables.copy()
        )
        
        try:
            workflow.state = WorkflowState.RUNNING
            self.active_workflows[workflow_id] = workflow
            
            # Execute workflow steps
            current_step_id = workflow.steps[0].step_id if workflow.steps else None
            
            while current_step_id:
                step = self._get_step(workflow, current_step_id)
                if not step:
                    break
                
                workflow.current_step = current_step_id
                
                # Evaluate step conditions
                conditions_met = True
                if step.conditions:
                    conditions_met = all(
                        self.condition_evaluator.evaluate(cond, context.trigger_data)
                        for cond in step.conditions
                    )
                
                if conditions_met:
                    # Execute step action
                    success = await self.action_executor.execute(step.action, context)
                    
                    if success:
                        current_step_id = step.on_success
                    else:
                        current_step_id = step.on_failure
                else:
                    current_step_id = step.on_failure
            
            workflow.state = WorkflowState.COMPLETED
            return True
            
        except Exception as e:
            logger.error(f"Workflow execution error: {e}")
            workflow.state = WorkflowState.FAILED
            return False
        finally:
            if workflow_id in self.active_workflows:
                del self.active_workflows[workflow_id]
    
    def _get_step(self, workflow: Workflow, step_id: str) -> Optional[WorkflowStep]:
        """Get workflow step by ID"""
        for step in workflow.steps:
            if step.step_id == step_id:
                return step
        return None
    
    async def pause_workflow(self, workflow_id: str):
        """Pause running workflow"""
        if workflow_id in self.active_workflows:
            self.active_workflows[workflow_id].state = WorkflowState.PAUSED
    
    async def resume_workflow(self, workflow_id: str):
        """Resume paused workflow"""
        if workflow_id in self.active_workflows:
            workflow = self.active_workflows[workflow_id]
            if workflow.state == WorkflowState.PAUSED:
                workflow.state = WorkflowState.RUNNING
    
    async def cancel_workflow(self, workflow_id: str):
        """Cancel running workflow"""
        if workflow_id in self.active_workflows:
            self.active_workflows[workflow_id].state = WorkflowState.CANCELLED
            del self.active_workflows[workflow_id]


# ========================== SCHEDULER ==========================

class Scheduler:
    """Task scheduler for time-based automation"""
    
    def __init__(self, rule_engine: RuleEngine):
        self.rule_engine = rule_engine
        self.scheduled_tasks: Dict[str, asyncio.Task] = {}
        self.running = False
    
    async def start(self):
        """Start scheduler"""
        self.running = True
        asyncio.create_task(self._scheduler_loop())
    
    async def stop(self):
        """Stop scheduler"""
        self.running = False
        for task in self.scheduled_tasks.values():
            task.cancel()
    
    async def _scheduler_loop(self):
        """Main scheduler loop"""
        while self.running:
            try:
                # Check scheduled rules
                for rule in self.rule_engine.get_all_rules():
                    if not rule.enabled or not rule.schedule:
                        continue
                    
                    if self._should_execute(rule):
                        await self.rule_engine.trigger_rule(
                            TriggerType.SCHEDULED,
                            rule.rule_id,
                            {'scheduled': True, 'timestamp': datetime.utcnow().isoformat()}
                        )
                
                await asyncio.sleep(60)  # Check every minute
                
            except Exception as e:
                logger.error(f"Scheduler error: {e}")
    
    def _should_execute(self, rule: AutomationRule) -> bool:
        """Check if scheduled rule should execute"""
        if not rule.schedule:
            return False
        
        schedule = rule.schedule
        now = datetime.utcnow()
        
        if schedule.schedule_type == ScheduleType.INTERVAL:
            stats = self.rule_engine.rule_stats[rule.rule_id]
            if stats['last_execution']:
                last_exec = datetime.fromisoformat(stats['last_execution'])
                elapsed = (now - last_exec).total_seconds()
                return elapsed >= schedule.interval_seconds
            return True
        
        elif schedule.schedule_type == ScheduleType.ONCE:
            if schedule.start_time:
                start = datetime.fromisoformat(schedule.start_time)
                stats = self.rule_engine.rule_stats[rule.rule_id]
                # Execute once at specified time if not already executed
                return abs((start - now).total_seconds()) < 60 and not stats['last_execution']
        
        return False


# ========================== AUTOMATION MANAGER ==========================

class AutomationManager:
    """Main automation manager"""
    
    def __init__(self, config: Dict, nvr_system):
        self.config = config.get('automation', {}) if isinstance(config, dict) else {}
        self.nvr = nvr_system
        self.enabled = self.config.get('enabled', True)
        
        # Components
        self.rule_engine = RuleEngine(nvr_system)
        self.workflow_engine = WorkflowEngine(nvr_system)
        self.scheduler = Scheduler(self.rule_engine)
        
        # State
        self.running = False
        
        logger.info(f"Automation Manager initialized. Enabled: {self.enabled}")
    
    async def start(self):
        """Start automation manager"""
        if not self.enabled:
            logger.info("Automation manager is disabled")
            return
        
        self.running = True
        
        # Load rules from database
        await self._load_rules()
        
        # Start scheduler
        await self.scheduler.start()
        
        logger.info("Automation Manager started")
    
    async def stop(self):
        """Stop automation manager"""
        self.running = False
        await self.scheduler.stop()
        logger.info("Automation Manager stopped")
    
    async def _load_rules(self):
        """Load automation rules from database"""
        try:
            # Load from database if available
            if hasattr(self.nvr, 'db_manager'):
                pass  # Load rules from DB
            
            logger.info(f"Loaded {len(self.rule_engine.rules)} automation rules")
        except Exception as e:
            logger.error(f"Failed to load rules: {e}")
    
    # ===== Rule Management =====
    
    async def create_rule(self, rule: AutomationRule) -> str:
        """Create new automation rule"""
        await self.rule_engine.add_rule(rule)
        return rule.rule_id
    
    async def update_rule(self, rule: AutomationRule):
        """Update automation rule"""
        await self.rule_engine.update_rule(rule)
    
    async def delete_rule(self, rule_id: str):
        """Delete automation rule"""
        await self.rule_engine.remove_rule(rule_id)
    
    async def get_rule(self, rule_id: str) -> Optional[AutomationRule]:
        """Get rule by ID"""
        return self.rule_engine.get_rule(rule_id)
    
    async def list_rules(self, enabled_only: bool = False) -> List[AutomationRule]:
        """List all rules"""
        rules = self.rule_engine.get_all_rules()
        if enabled_only:
            rules = [r for r in rules if r.enabled]
        return rules
    
    async def enable_rule(self, rule_id: str):
        """Enable rule"""
        await self.rule_engine.enable_rule(rule_id)
    
    async def disable_rule(self, rule_id: str):
        """Disable rule"""
        await self.rule_engine.disable_rule(rule_id)
    
    # ===== Trigger Handling =====
    
    async def trigger(self, trigger_type: TriggerType, source_id: Optional[str] = None, 
                     data: Optional[Dict[str, Any]] = None):
        """Trigger automation rules"""
        if not self.enabled or not self.running:
            return
        
        data = data or {}
        await self.rule_engine.trigger_rule(trigger_type, source_id, data)
    
    async def manual_trigger(self, rule_id: str, data: Optional[Dict[str, Any]] = None):
        """Manually trigger specific rule"""
        rule = self.rule_engine.get_rule(rule_id)
        if not rule:
            logger.error(f"Rule not found: {rule_id}")
            return
        
        data = data or {}
        context = ExecutionContext(
            context_id=str(uuid.uuid4()),
            trigger_type=TriggerType.MANUAL,
            trigger_data=data,
            timestamp=datetime.utcnow().isoformat()
        )
        
        await self.rule_engine._execute_rule(rule, context)
    
    # ===== Workflow Management =====
    
    async def create_workflow(self, workflow: Workflow) -> str:
        """Create workflow"""
        await self.workflow_engine.add_workflow(workflow)
        return workflow.workflow_id
    
    async def execute_workflow(self, workflow_id: str, data: Optional[Dict[str, Any]] = None) -> bool:
        """Execute workflow"""
        data = data or {}
        return await self.workflow_engine.execute_workflow(workflow_id, data)
    
    async def pause_workflow(self, workflow_id: str):
        """Pause workflow"""
        await self.workflow_engine.pause_workflow(workflow_id)
    
    async def resume_workflow(self, workflow_id: str):
        """Resume workflow"""
        await self.workflow_engine.resume_workflow(workflow_id)
    
    async def cancel_workflow(self, workflow_id: str):
        """Cancel workflow"""
        await self.workflow_engine.cancel_workflow(workflow_id)
    
    # ===== Statistics =====
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get automation statistics"""
        if not self.enabled:
            return {}
        
        total_rules = len(self.rule_engine.rules)
        enabled_rules = len([r for r in self.rule_engine.rules.values() if r.enabled])
        
        executions = list(self.rule_engine.execution_history)
        total_executions = len(executions)
        successful = len([e for e in executions if e.success])
        failed = total_executions - successful
        
        # By rule
        by_rule = {}
        for rule_id, stats in self.rule_engine.rule_stats.items():
            rule = self.rule_engine.get_rule(rule_id)
            if rule:
                by_rule[rule.name] = {
                    'executions': stats['executions'],
                    'successes': stats['successes'],
                    'failures': stats['failures'],
                    'last_execution': stats['last_execution']
                }
        
        # By trigger type
        by_trigger = defaultdict(int)
        for execution in executions:
            rule = self.rule_engine.get_rule(execution.rule_id)
            if rule:
                by_trigger[rule.trigger_type.value] += 1
        
        return {
            'total_rules': total_rules,
            'enabled_rules': enabled_rules,
            'disabled_rules': total_rules - enabled_rules,
            'total_executions': total_executions,
            'successful_executions': successful,
            'failed_executions': failed,
            'success_rate': f"{(successful / total_executions * 100):.2f}%" if total_executions > 0 else "0%",
            'by_rule': by_rule,
            'by_trigger_type': dict(by_trigger),
            'total_workflows': len(self.workflow_engine.workflows),
            'active_workflows': len(self.workflow_engine.active_workflows)
        }
    
    def get_execution_history(self, rule_id: Optional[str] = None, limit: int = 100) -> List[Dict]:
        """Get execution history"""
        executions = self.rule_engine.get_execution_history(rule_id, limit)
        return [asdict(e) for e in executions]
    
    def get_rule_stats(self, rule_id: str) -> Dict:
        """Get statistics for specific rule"""
        return self.rule_engine.get_rule_stats(rule_id)


# ========================== UTILITY FUNCTIONS ==========================

def create_simple_rule(name: str, trigger_type: TriggerType, action_type: ActionType,
                      action_params: Dict, conditions: Optional[List[Condition]] = None) -> AutomationRule:
    """Helper to create simple automation rule"""
    rule_id = str(uuid.uuid4())
    action_id = str(uuid.uuid4())
    
    condition_groups = []
    if conditions:
        condition_groups = [ConditionGroup(conditions=conditions)]
    
    return AutomationRule(
        rule_id=rule_id,
        name=name,
        description=f"Simple rule: {name}",
        trigger_type=trigger_type,
        condition_groups=condition_groups,
        actions=[Action(
            action_id=action_id,
            action_type=action_type,
            parameters=action_params
        )]
    )
