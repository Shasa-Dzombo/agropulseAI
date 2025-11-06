# System Health Manager
# Advanced comprehensive monitoring and diagnostics system for Jetson Nano/Xavier platforms

import logging
import asyncio
import psutil
import subprocess
import json
import time
import threading
import queue
import numpy as np
import pickle
from datetime import datetime, timedelta
from pathlib import Path
from collections import deque, defaultdict
import aiofiles
import aiohttp
import sqlite3
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Tuple, Any
import warnings

logger = logging.getLogger(__name__)

@dataclass
class SystemMetrics:
    timestamp: float
    cpu_percent: float
    memory_percent: float
    memory_available: int
    memory_used: int
    memory_total: int
    cpu_temp_c: Optional[float]
    gpu_temp_c: Optional[float]
    disk_percent: float
    disk_free: int
    disk_total: int
    network_bytes_sent: int
    network_bytes_recv: int
    gpu_utilization: Optional[float]
    gpu_memory_used: Optional[int]
    gpu_memory_total: Optional[int]
    power_consumption: Optional[float]
    fan_speed: Optional[int]
    load_average_1m: float
    load_average_5m: float
    load_average_15m: float
    process_count: int
    thread_count: int
    file_descriptors: int

@dataclass
class AlertRule:
    metric_name: str
    threshold_type: str
    threshold_value: float
    duration_seconds: int
    severity: str
    enabled: bool
    cooldown_seconds: int

class MetricsDatabase:
    def __init__(self, db_path: str):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = None
        self._setup_database()

    def _setup_database(self):
        self.connection = sqlite3.connect(str(self.db_path), check_same_thread=False)
        cursor = self.connection.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS system_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp REAL,
                cpu_percent REAL,
                memory_percent REAL,
                memory_available INTEGER,
                memory_used INTEGER,
                memory_total INTEGER,
                cpu_temp_c REAL,
                gpu_temp_c REAL,
                disk_percent REAL,
                disk_free INTEGER,
                disk_total INTEGER,
                network_bytes_sent INTEGER,
                network_bytes_recv INTEGER,
                gpu_utilization REAL,
                gpu_memory_used INTEGER,
                gpu_memory_total INTEGER,
                power_consumption REAL,
                fan_speed INTEGER,
                load_average_1m REAL,
                load_average_5m REAL,
                load_average_15m REAL,
                process_count INTEGER,
                thread_count INTEGER,
                file_descriptors INTEGER
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS alert_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp REAL,
                metric_name TEXT,
                severity TEXT,
                message TEXT,
                value REAL,
                threshold REAL
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS performance_baselines (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                metric_name TEXT,
                baseline_value REAL,
                confidence_interval REAL,
                sample_size INTEGER,
                last_updated REAL
            )
        """)
        self.connection.commit()

    def insert_metrics(self, metrics: SystemMetrics):
        cursor = self.connection.cursor()
        cursor.execute("""
            INSERT INTO system_metrics (
                timestamp, cpu_percent, memory_percent, memory_available, memory_used, memory_total,
                cpu_temp_c, gpu_temp_c, disk_percent, disk_free, disk_total, network_bytes_sent,
                network_bytes_recv, gpu_utilization, gpu_memory_used, gpu_memory_total,
                power_consumption, fan_speed, load_average_1m, load_average_5m, load_average_15m,
                process_count, thread_count, file_descriptors
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            metrics.timestamp, metrics.cpu_percent, metrics.memory_percent,
            metrics.memory_available, metrics.memory_used, metrics.memory_total,
            metrics.cpu_temp_c, metrics.gpu_temp_c, metrics.disk_percent,
            metrics.disk_free, metrics.disk_total, metrics.network_bytes_sent,
            metrics.network_bytes_recv, metrics.gpu_utilization, metrics.gpu_memory_used,
            metrics.gpu_memory_total, metrics.power_consumption, metrics.fan_speed,
            metrics.load_average_1m, metrics.load_average_5m, metrics.load_average_15m,
            metrics.process_count, metrics.thread_count, metrics.file_descriptors
        ))
        self.connection.commit()

    def get_metrics_range(self, start_time: float, end_time: float) -> List[SystemMetrics]:
        cursor = self.connection.cursor()
        cursor.execute("""
            SELECT * FROM system_metrics WHERE timestamp BETWEEN ? AND ? ORDER BY timestamp
        """, (start_time, end_time))
        
        metrics_list = []
        for row in cursor.fetchall():
            metrics = SystemMetrics(
                timestamp=row[1], cpu_percent=row[2], memory_percent=row[3],
                memory_available=row[4], memory_used=row[5], memory_total=row[6],
                cpu_temp_c=row[7], gpu_temp_c=row[8], disk_percent=row[9],
                disk_free=row[10], disk_total=row[11], network_bytes_sent=row[12],
                network_bytes_recv=row[13], gpu_utilization=row[14], gpu_memory_used=row[15],
                gpu_memory_total=row[16], power_consumption=row[17], fan_speed=row[18],
                load_average_1m=row[19], load_average_5m=row[20], load_average_15m=row[21],
                process_count=row[22], thread_count=row[23], file_descriptors=row[24]
            )
            metrics_list.append(metrics)
        return metrics_list

    def cleanup_old_data(self, retention_days: int):
        cutoff_time = time.time() - (retention_days * 24 * 3600)
        cursor = self.connection.cursor()
        cursor.execute("DELETE FROM system_metrics WHERE timestamp < ?", (cutoff_time,))
        cursor.execute("DELETE FROM alert_history WHERE timestamp < ?", (cutoff_time,))
        self.connection.commit()

class ThermalManager:
    def __init__(self):
        self.thermal_zones = []
        self._discover_thermal_zones()
        self.thermal_history = deque(maxlen=100)
        
    def _discover_thermal_zones(self):
        thermal_path = Path('/sys/class/thermal')
        if thermal_path.exists():
            for zone_dir in thermal_path.glob('thermal_zone*'):
                try:
                    with open(zone_dir / 'type') as f:
                        zone_type = f.read().strip()
                    self.thermal_zones.append({
                        'path': zone_dir / 'temp',
                        'type': zone_type,
                        'name': zone_dir.name
                    })
                except:
                    continue

    def get_temperatures(self) -> Dict[str, float]:
        temperatures = {}
        for zone in self.thermal_zones:
            try:
                with open(zone['path']) as f:
                    temp_millicelsius = int(f.read().strip())
                    temp_celsius = temp_millicelsius / 1000.0
                    temperatures[zone['type']] = temp_celsius
            except:
                continue
        return temperatures

    def get_thermal_throttling_status(self) -> Dict[str, bool]:
        throttling_status = {}
        for zone in self.thermal_zones:
            throttle_path = zone['path'].parent / 'throttle'
            try:
                with open(throttle_path) as f:
                    throttle_value = int(f.read().strip())
                    throttling_status[zone['type']] = throttle_value > 0
            except:
                throttling_status[zone['type']] = False
        return throttling_status

class GPUMonitor:
    def __init__(self):
        self.nvidia_smi_available = self._check_nvidia_smi()
        self.tegrastats_available = self._check_tegrastats()

    def _check_nvidia_smi(self) -> bool:
        try:
            subprocess.check_output(['nvidia-smi', '-L'], stderr=subprocess.DEVNULL)
            return True
        except:
            return False

    def _check_tegrastats(self) -> bool:
        try:
            subprocess.check_output(['which', 'tegrastats'], stderr=subprocess.DEVNULL)
            return True
        except:
            return False

    def get_gpu_metrics(self) -> Dict[str, Any]:
        if self.nvidia_smi_available:
            return self._get_nvidia_smi_metrics()
        elif self.tegrastats_available:
            return self._get_tegrastats_metrics()
        else:
            return {}

    def _get_nvidia_smi_metrics(self) -> Dict[str, Any]:
        try:
            cmd = ['nvidia-smi', '--query-gpu=utilization.gpu,memory.used,memory.total,temperature.gpu,power.draw', '--format=csv,noheader,nounits']
            output = subprocess.check_output(cmd, stderr=subprocess.DEVNULL).decode().strip()
            
            if output:
                values = output.split(', ')
                return {
                    'utilization': float(values[0]) if values[0] != 'N/A' else None,
                    'memory_used': int(values[1]) * 1024 * 1024 if values[1] != 'N/A' else None,
                    'memory_total': int(values[2]) * 1024 * 1024 if values[2] != 'N/A' else None,
                    'temperature': float(values[3]) if values[3] != 'N/A' else None,
                    'power_draw': float(values[4]) if values[4] != 'N/A' else None
                }
        except:
            pass
        return {}

    def _get_tegrastats_metrics(self) -> Dict[str, Any]:
        try:
            proc = subprocess.Popen(['tegrastats', '--interval', '1000'], 
                                  stdout=subprocess.PIPE, 
                                  stderr=subprocess.DEVNULL)
            output, _ = proc.communicate(timeout=2)
            proc.kill()
            
            lines = output.decode().strip().split('\n')
            if lines:
                last_line = lines[-1]
                return self._parse_tegrastats_line(last_line)
        except:
            pass
        return {}

    def _parse_tegrastats_line(self, line: str) -> Dict[str, Any]:
        metrics = {}
        try:
            if 'GPU@' in line:
                gpu_temp_match = line.split('GPU@')[1].split('C')[0]
                metrics['temperature'] = float(gpu_temp_match)
            
            if 'GR3D_FREQ' in line:
                freq_match = line.split('GR3D_FREQ ')[1].split('%')[0]
                metrics['utilization'] = float(freq_match)
                
            if 'VDD_IN' in line:
                power_match = line.split('VDD_IN ')[1].split('mW')[0]
                metrics['power_draw'] = float(power_match) / 1000.0
        except:
            pass
        return metrics

class NetworkMonitor:
    def __init__(self):
        self.last_network_stats = psutil.net_io_counters()
        self.last_measurement_time = time.time()
        self.network_history = deque(maxlen=60)

    def get_network_metrics(self) -> Dict[str, Any]:
        current_stats = psutil.net_io_counters()
        current_time = time.time()
        
        time_delta = current_time - self.last_measurement_time
        
        if time_delta > 0:
            bytes_sent_per_sec = (current_stats.bytes_sent - self.last_network_stats.bytes_sent) / time_delta
            bytes_recv_per_sec = (current_stats.bytes_recv - self.last_network_stats.bytes_recv) / time_delta
            
            self.network_history.append({
                'timestamp': current_time,
                'bytes_sent_per_sec': bytes_sent_per_sec,
                'bytes_recv_per_sec': bytes_recv_per_sec
            })
        else:
            bytes_sent_per_sec = 0
            bytes_recv_per_sec = 0

        self.last_network_stats = current_stats
        self.last_measurement_time = current_time

        return {
            'bytes_sent_total': current_stats.bytes_sent,
            'bytes_recv_total': current_stats.bytes_recv,
            'bytes_sent_per_sec': bytes_sent_per_sec,
            'bytes_recv_per_sec': bytes_recv_per_sec,
            'packets_sent': current_stats.packets_sent,
            'packets_recv': current_stats.packets_recv,
            'errin': current_stats.errin,
            'errout': current_stats.errout,
            'dropin': current_stats.dropin,
            'dropout': current_stats.dropout
        }

class ProcessMonitor:
    def __init__(self):
        self.process_history = deque(maxlen=50)
        self.suspicious_processes = set()

    def get_process_metrics(self) -> Dict[str, Any]:
        processes = []
        total_cpu = 0
        total_memory = 0
        
        for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent', 'memory_info']):
            try:
                pinfo = proc.info
                if pinfo['cpu_percent'] is not None:
                    total_cpu += pinfo['cpu_percent']
                if pinfo['memory_percent'] is not None:
                    total_memory += pinfo['memory_percent']
                
                processes.append({
                    'pid': pinfo['pid'],
                    'name': pinfo['name'],
                    'cpu_percent': pinfo['cpu_percent'],
                    'memory_percent': pinfo['memory_percent'],
                    'memory_rss': pinfo['memory_info'].rss if pinfo['memory_info'] else 0
                })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        top_cpu_processes = sorted(processes, key=lambda x: x['cpu_percent'] or 0, reverse=True)[:10]
        top_memory_processes = sorted(processes, key=lambda x: x['memory_percent'] or 0, reverse=True)[:10]

        return {
            'process_count': len(processes),
            'total_cpu_percent': total_cpu,
            'total_memory_percent': total_memory,
            'top_cpu_processes': top_cpu_processes,
            'top_memory_processes': top_memory_processes
        }

    def detect_anomalous_processes(self, current_processes: List[Dict]) -> List[Dict]:
        anomalies = []
        for proc in current_processes:
            if proc['cpu_percent'] and proc['cpu_percent'] > 90:
                anomalies.append({
                    'type': 'high_cpu',
                    'process': proc,
                    'severity': 'high' if proc['cpu_percent'] > 95 else 'medium'
                })
            
            if proc['memory_percent'] and proc['memory_percent'] > 50:
                anomalies.append({
                    'type': 'high_memory',
                    'process': proc,
                    'severity': 'high' if proc['memory_percent'] > 80 else 'medium'
                })
        
        return anomalies

class PerformanceAnalyzer:
    def __init__(self):
        self.baseline_metrics = {}
        self.performance_trends = {}
        self.anomaly_detector = AnomalyDetector()

    def update_baseline(self, metrics_history: List[SystemMetrics]):
        if len(metrics_history) < 10:
            return

        metric_arrays = defaultdict(list)
        for metric in metrics_history:
            for field_name, value in asdict(metric).items():
                if isinstance(value, (int, float)) and value is not None:
                    metric_arrays[field_name].append(value)

        for metric_name, values in metric_arrays.items():
            if len(values) > 5:
                mean_val = np.mean(values)
                std_val = np.std(values)
                self.baseline_metrics[metric_name] = {
                    'mean': mean_val,
                    'std': std_val,
                    'confidence_interval': 1.96 * std_val,
                    'sample_size': len(values),
                    'last_updated': time.time()
                }

    def analyze_performance_trend(self, metrics_history: List[SystemMetrics]) -> Dict[str, Any]:
        if len(metrics_history) < 20:
            return {}

        trends = {}
        timestamps = [m.timestamp for m in metrics_history]
        
        for field_name in ['cpu_percent', 'memory_percent', 'cpu_temp_c', 'disk_percent']:
            values = []
            for metric in metrics_history:
                value = getattr(metric, field_name)
                if value is not None:
                    values.append(value)
            
            if len(values) >= len(timestamps) * 0.8:
                trend_coefficient = np.polyfit(range(len(values)), values, 1)[0]
                trends[field_name] = {
                    'slope': trend_coefficient,
                    'direction': 'increasing' if trend_coefficient > 0 else 'decreasing',
                    'magnitude': abs(trend_coefficient)
                }

        return trends

    def detect_performance_degradation(self, current_metrics: SystemMetrics) -> List[Dict]:
        degradations = []
        
        for metric_name, baseline in self.baseline_metrics.items():
            current_value = getattr(current_metrics, metric_name, None)
            if current_value is None:
                continue
                
            deviation = abs(current_value - baseline['mean'])
            if deviation > baseline['confidence_interval']:
                severity = 'high' if deviation > 2 * baseline['confidence_interval'] else 'medium'
                degradations.append({
                    'metric': metric_name,
                    'current_value': current_value,
                    'baseline_mean': baseline['mean'],
                    'deviation': deviation,
                    'severity': severity,
                    'threshold': baseline['confidence_interval']
                })

        return degradations

class AnomalyDetector:
    def __init__(self):
        self.isolation_forest_models = {}
        self.training_data = defaultdict(list)
        self.model_update_threshold = 100

    def add_training_data(self, metrics: SystemMetrics):
        metric_dict = asdict(metrics)
        for key, value in metric_dict.items():
            if isinstance(value, (int, float)) and value is not None:
                self.training_data[key].append(value)
                
                if len(self.training_data[key]) >= self.model_update_threshold:
                    self._update_model(key)

    def _update_model(self, metric_name: str):
        try:
            from sklearn.ensemble import IsolationForest
            data = np.array(self.training_data[metric_name]).reshape(-1, 1)
            model = IsolationForest(contamination=0.1, random_state=42)
            model.fit(data)
            self.isolation_forest_models[metric_name] = model
            
            self.training_data[metric_name] = self.training_data[metric_name][-50:]
        except ImportError:
            logger.warning("sklearn not available for anomaly detection")

    def detect_anomalies(self, metrics: SystemMetrics) -> List[Dict]:
        anomalies = []
        metric_dict = asdict(metrics)
        
        for metric_name, value in metric_dict.items():
            if metric_name in self.isolation_forest_models and value is not None:
                model = self.isolation_forest_models[metric_name]
                prediction = model.predict([[value]])
                
                if prediction[0] == -1:
                    anomaly_score = model.decision_function([[value]])[0]
                    anomalies.append({
                        'metric': metric_name,
                        'value': value,
                        'anomaly_score': anomaly_score,
                        'type': 'statistical_outlier'
                    })

        return anomalies

class AlertManager:
    def __init__(self, alert_config: Dict):
        self.rules = []
        self.alert_history = deque(maxlen=1000)
        self.cooldown_cache = {}
        self._load_alert_rules(alert_config)

    def _load_alert_rules(self, config: Dict):
        for rule_config in config.get('rules', []):
            rule = AlertRule(
                metric_name=rule_config['metric'],
                threshold_type=rule_config.get('type', 'greater_than'),
                threshold_value=rule_config['threshold'],
                duration_seconds=rule_config.get('duration', 60),
                severity=rule_config.get('severity', 'medium'),
                enabled=rule_config.get('enabled', True),
                cooldown_seconds=rule_config.get('cooldown', 300)
            )
            self.rules.append(rule)

    def evaluate_alerts(self, metrics: SystemMetrics, metrics_history: List[SystemMetrics]) -> List[Dict]:
        alerts = []
        current_time = time.time()
        
        for rule in self.rules:
            if not rule.enabled:
                continue
                
            rule_key = f"{rule.metric_name}_{rule.threshold_type}_{rule.threshold_value}"
            
            if rule_key in self.cooldown_cache:
                if current_time - self.cooldown_cache[rule_key] < rule.cooldown_seconds:
                    continue

            current_value = getattr(metrics, rule.metric_name, None)
            if current_value is None:
                continue

            triggered = False
            if rule.threshold_type == 'greater_than':
                triggered = current_value > rule.threshold_value
            elif rule.threshold_type == 'less_than':
                triggered = current_value < rule.threshold_value
            elif rule.threshold_type == 'equals':
                triggered = abs(current_value - rule.threshold_value) < 0.001

            if triggered:
                duration_check = self._check_duration_condition(rule, metrics_history)
                if duration_check:
                    alert = {
                        'rule': rule,
                        'current_value': current_value,
                        'threshold': rule.threshold_value,
                        'severity': rule.severity,
                        'timestamp': current_time,
                        'message': f"Alert: {rule.metric_name} = {current_value} {rule.threshold_type} {rule.threshold_value}"
                    }
                    alerts.append(alert)
                    self.cooldown_cache[rule_key] = current_time
                    self.alert_history.append(alert)

        return alerts

    def _check_duration_condition(self, rule: AlertRule, history: List[SystemMetrics]) -> bool:
        if rule.duration_seconds <= 0:
            return True
            
        cutoff_time = time.time() - rule.duration_seconds
        relevant_metrics = [m for m in history if m.timestamp >= cutoff_time]
        
        violation_count = 0
        for metric in relevant_metrics:
            value = getattr(metric, rule.metric_name, None)
            if value is None:
                continue
                
            if rule.threshold_type == 'greater_than' and value > rule.threshold_value:
                violation_count += 1
            elif rule.threshold_type == 'less_than' and value < rule.threshold_value:
                violation_count += 1

        violation_rate = violation_count / len(relevant_metrics) if relevant_metrics else 0
        return violation_rate > 0.8

class SystemHealthManager:
    def __init__(self, config, alert_manager):
        self.config = config
        self.external_alert_manager = alert_manager
        self.interval = config.get('check_interval_seconds', 30)
        self.is_monitoring = False
        self.current_metrics = None
        self.metrics_history = deque(maxlen=1000)
        self.thresholds = config.get('thresholds', {})
        
        self.db = MetricsDatabase(config.get('database_path', '/var/lib/agropulse/health.db'))
        self.thermal_manager = ThermalManager()
        self.gpu_monitor = GPUMonitor()
        self.network_monitor = NetworkMonitor()
        self.process_monitor = ProcessMonitor()
        self.performance_analyzer = PerformanceAnalyzer()
        self.alert_manager = AlertManager(config.get('alerting', {}))
        
        self.monitoring_thread = None
        self.metrics_queue = queue.Queue()
        
        logger.info("Advanced System Health Manager initialized with comprehensive monitoring capabilities.")

    async def start(self):
        self.is_monitoring = True
        self.monitoring_thread = threading.Thread(target=self._monitoring_thread_worker, daemon=True)
        self.monitoring_thread.start()
        
        asyncio.create_task(self._async_monitor_loop())
        asyncio.create_task(self._maintenance_loop())
        logger.info(f"System health monitoring started. Check interval: {self.interval}s.")

    async def stop(self):
        self.is_monitoring = False
        if self.monitoring_thread and self.monitoring_thread.is_alive():
            self.monitoring_thread.join(timeout=5)
        logger.info("System health monitoring stopped.")

    def _monitoring_thread_worker(self):
        while self.is_monitoring:
            try:
                metrics = self._collect_comprehensive_metrics()
                self.metrics_queue.put(metrics)
                time.sleep(self.interval)
            except Exception as e:
                logger.error(f"Error in monitoring thread: {e}")
                time.sleep(self.interval)

    async def _async_monitor_loop(self):
        while self.is_monitoring:
            try:
                if not self.metrics_queue.empty():
                    metrics = self.metrics_queue.get_nowait()
                    await self._process_metrics(metrics)
                await asyncio.sleep(1)
            except Exception as e:
                logger.error(f"Error in async monitoring loop: {e}")
                await asyncio.sleep(self.interval)

    async def _process_metrics(self, metrics: SystemMetrics):
        self.current_metrics = metrics
        self.metrics_history.append(metrics)
        
        self.db.insert_metrics(metrics)
        
        self.performance_analyzer.anomaly_detector.add_training_data(metrics)
        
        if len(self.metrics_history) > 50:
            self.performance_analyzer.update_baseline(list(self.metrics_history)[-50:])
        
        await self._evaluate_health_status(metrics)
        
        process_anomalies = self.process_monitor.detect_anomalous_processes(
            self.process_monitor.get_process_metrics()['top_cpu_processes']
        )
        
        for anomaly in process_anomalies:
            await self._send_alert(f"Process Anomaly: {anomaly['type']}", anomaly, 'warning')

    async def _maintenance_loop(self):
        while self.is_monitoring:
            try:
                await asyncio.sleep(3600)
                
                retention_days = self.config.get('data_retention_days', 30)
                self.db.cleanup_old_data(retention_days)
                
                if len(self.metrics_history) > 100:
                    trends = self.performance_analyzer.analyze_performance_trend(list(self.metrics_history))
                    for metric_name, trend in trends.items():
                        if trend['magnitude'] > 0.1:
                            message = f"Performance trend detected in {metric_name}: {trend['direction']} at rate {trend['slope']:.4f}/sample"
                            await self._send_alert("Performance Trend Alert", {'metric': metric_name, 'trend': trend}, 'info')
                
            except Exception as e:
                logger.error(f"Error in maintenance loop: {e}")

    def _collect_comprehensive_metrics(self) -> SystemMetrics:
        timestamp = time.time()
        
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        load_avg = psutil.getloadavg()
        
        cpu_percent = psutil.cpu_percent(interval=None)
        
        temperatures = self.thermal_manager.get_temperatures()
        cpu_temp = temperatures.get('thermal', temperatures.get('cpu-thermal'))
        gpu_temp = temperatures.get('gpu', temperatures.get('gpu-thermal'))
        
        network_metrics = self.network_monitor.get_network_metrics()
        gpu_metrics = self.gpu_monitor.get_gpu_metrics()
        
        process_count = len(psutil.pids())
        
        try:
            with open('/proc/sys/fs/file-nr') as f:
                file_descriptors = int(f.read().split()[0])
        except:
            file_descriptors = 0
        
        thread_count = 0
        for proc in psutil.process_iter(['num_threads']):
            try:
                thread_count += proc.info['num_threads'] or 0
            except:
                continue

        return SystemMetrics(
            timestamp=timestamp,
            cpu_percent=cpu_percent,
            memory_percent=memory.percent,
            memory_available=memory.available,
            memory_used=memory.used,
            memory_total=memory.total,
            cpu_temp_c=cpu_temp,
            gpu_temp_c=gpu_temp or gpu_metrics.get('temperature'),
            disk_percent=disk.percent,
            disk_free=disk.free,
            disk_total=disk.total,
            network_bytes_sent=network_metrics.get('bytes_sent_total', 0),
            network_bytes_recv=network_metrics.get('bytes_recv_total', 0),
            gpu_utilization=gpu_metrics.get('utilization'),
            gpu_memory_used=gpu_metrics.get('memory_used'),
            gpu_memory_total=gpu_metrics.get('memory_total'),
            power_consumption=gpu_metrics.get('power_draw'),
            fan_speed=None,
            load_average_1m=load_avg[0],
            load_average_5m=load_avg[1],
            load_average_15m=load_avg[2],
            process_count=process_count,
            thread_count=thread_count,
            file_descriptors=file_descriptors
        )

    async def _evaluate_health_status(self, metrics: SystemMetrics):
        alerts = self.alert_manager.evaluate_alerts(metrics, list(self.metrics_history))
        
        for alert in alerts:
            await self._send_alert(alert['message'], alert, alert['severity'])
        
        degradations = self.performance_analyzer.detect_performance_degradation(metrics)
        for degradation in degradations:
            message = f"Performance degradation in {degradation['metric']}: current={degradation['current_value']:.2f}, baseline={degradation['baseline_mean']:.2f}"
            await self._send_alert(message, degradation, degradation['severity'])
        
        anomalies = self.performance_analyzer.anomaly_detector.detect_anomalies(metrics)
        for anomaly in anomalies:
            message = f"Statistical anomaly detected in {anomaly['metric']}: value={anomaly['value']:.2f}, score={anomaly['anomaly_score']:.3f}"
            await self._send_alert(message, anomaly, 'warning')
        
        thermal_throttling = self.thermal_manager.get_thermal_throttling_status()
        for zone, is_throttling in thermal_throttling.items():
            if is_throttling:
                message = f"Thermal throttling detected in {zone}"
                await self._send_alert(message, {'zone': zone, 'throttling': True}, 'critical')

    async def _send_alert(self, message: str, data: Dict, severity: str):
        try:
            await self.external_alert_manager.send_alert('system_health', message, level=severity)
            logger.warning(f"Health Alert [{severity.upper()}]: {message}")
        except Exception as e:
            logger.error(f"Failed to send health alert: {e}")

    def get_current_metrics(self) -> Optional[SystemMetrics]:
        return self.current_metrics

    def get_metrics_history(self, hours: int = 24) -> List[SystemMetrics]:
        end_time = time.time()
        start_time = end_time - (hours * 3600)
        return self.db.get_metrics_range(start_time, end_time)

    def get_system_status_summary(self) -> Dict[str, Any]:
        if not self.current_metrics:
            return {"status": "no_data"}
        
        m = self.current_metrics
        status = {
            "overall_status": "healthy",
            "timestamp": m.timestamp,
            "cpu": {
                "usage_percent": m.cpu_percent,
                "temperature_c": m.cpu_temp_c,
                "load_average": {
                    "1m": m.load_average_1m,
                    "5m": m.load_average_5m,
                    "15m": m.load_average_15m
                }
            },
            "memory": {
                "usage_percent": m.memory_percent,
                "used_gb": m.memory_used / (1024**3),
                "total_gb": m.memory_total / (1024**3),
                "available_gb": m.memory_available / (1024**3)
            },
            "disk": {
                "usage_percent": m.disk_percent,
                "free_gb": m.disk_free / (1024**3),
                "total_gb": m.disk_total / (1024**3)
            },
            "processes": {
                "count": m.process_count,
                "threads": m.thread_count,
                "file_descriptors": m.file_descriptors
            }
        }
        
        if m.gpu_utilization is not None:
            status["gpu"] = {
                "utilization_percent": m.gpu_utilization,
                "temperature_c": m.gpu_temp_c,
                "memory_used_mb": m.gpu_memory_used / (1024**2) if m.gpu_memory_used else None,
                "memory_total_mb": m.gpu_memory_total / (1024**2) if m.gpu_memory_total else None,
                "power_draw_w": m.power_consumption
            }
        
        critical_thresholds = {
            "cpu_percent": 90,
            "memory_percent": 85,
            "disk_percent": 90,
            "cpu_temp_c": 80
        }
        
        warnings = []
        for metric, threshold in critical_thresholds.items():
            value = getattr(m, metric)
            if value is not None and value > threshold:
                warnings.append(f"{metric} is high: {value:.1f}")
                status["overall_status"] = "warning"
        
        if warnings:
            status["warnings"] = warnings
            
        if any(getattr(m, metric) > critical_thresholds[metric] * 1.1 for metric in critical_thresholds if getattr(m, metric) is not None):
            status["overall_status"] = "critical"
        
        return status

    def generate_health_report(self, hours: int = 24) -> Dict[str, Any]:
        history = self.get_metrics_history(hours)
        if not history:
            return {"error": "No historical data available"}
        
        report = {
            "report_period_hours": hours,
            "sample_count": len(history),
            "generated_at": datetime.now().isoformat(),
            "metrics_summary": {},
            "performance_trends": {},
            "alert_summary": {},
            "recommendations": []
        }
        
        metric_fields = ['cpu_percent', 'memory_percent', 'disk_percent', 'cpu_temp_c', 'gpu_temp_c', 'gpu_utilization']
        
        for field in metric_fields:
            values = [getattr(m, field) for m in history if getattr(m, field) is not None]
            if values:
                report["metrics_summary"][field] = {
                    "min": min(values),
                    "max": max(values),
                    "mean": sum(values) / len(values),
                    "median": sorted(values)[len(values) // 2],
                    "std_dev": np.std(values) if len(values) > 1 else 0
                }
        
        trends = self.performance_analyzer.analyze_performance_trend(history)
        report["performance_trends"] = trends
        
        recent_alerts = [alert for alert in self.alert_manager.alert_history if alert['timestamp'] > time.time() - (hours * 3600)]
        report["alert_summary"] = {
            "total_alerts": len(recent_alerts),
            "by_severity": {}
        }
        
        for alert in recent_alerts:
            severity = alert.get('severity', 'unknown')
            report["alert_summary"]["by_severity"][severity] = report["alert_summary"]["by_severity"].get(severity, 0) + 1
        
        if self.current_metrics:
            m = self.current_metrics
            if m.cpu_percent > 80:
                report["recommendations"].append("Consider reducing CPU-intensive processes or upgrading hardware")
            if m.memory_percent > 80:
                report["recommendations"].append("Memory usage is high - consider increasing RAM or optimizing applications")
            if m.disk_percent > 80:
                report["recommendations"].append("Disk space is low - consider cleanup or adding storage")
            if m.cpu_temp_c and m.cpu_temp_c > 70:
                report["recommendations"].append("CPU temperature is elevated - check cooling system")
        
        return report
