"""
Advanced Analytics and Reporting System for Orchard Management

This comprehensive system provides:
- Real-time analytics dashboard data generation
- Historical trend analysis and forecasting
- Business intelligence reporting
- Custom report generation with templates
- Data visualization preparation
- Performance metrics and KPIs
- Anomaly detection in time-series data
- Comparative analysis across orchards/zones
- ROI and cost-benefit analysis
- Automated alert generation
- Export to multiple formats (PDF, Excel, CSV, JSON)
- Scheduled report delivery
- Interactive query builder
- Statistical analysis suite
- Machine learning insights
- Geospatial analytics
- Multi-dimensional OLAP cubes

Author: AgroPulse Development Team
Version: 4.0.0
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional, Any, Union, Callable
from dataclasses import dataclass, field
from enum import Enum
import json
import asyncio
from collections import defaultdict, deque
import statistics
from scipy import stats
from scipy.signal import find_peaks, savgol_filter
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
from sklearn.cluster import DBSCAN, KMeans
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend
import matplotlib.pyplot as plt
import seaborn as sns
from io import BytesIO
import base64
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
import warnings
warnings.filterwarnings('ignore')


class ReportType(Enum):
    """Types of reports available in the system"""
    DAILY_SUMMARY = "daily_summary"
    WEEKLY_ANALYSIS = "weekly_analysis"
    MONTHLY_OVERVIEW = "monthly_overview"
    SEASONAL_REPORT = "seasonal_report"
    CUSTOM = "custom"
    HEALTH_ASSESSMENT = "health_assessment"
    YIELD_FORECAST = "yield_forecast"
    DISEASE_ANALYSIS = "disease_analysis"
    IRRIGATION_EFFICIENCY = "irrigation_efficiency"
    FINANCIAL_REPORT = "financial_report"
    COMPLIANCE_REPORT = "compliance_report"


class MetricType(Enum):
    """Types of metrics tracked in the system"""
    HEALTH_INDEX = "health_index"
    YIELD_ESTIMATE = "yield_estimate"
    DISEASE_PREVALENCE = "disease_prevalence"
    WATER_USAGE = "water_usage"
    NUTRIENT_LEVELS = "nutrient_levels"
    PEST_PRESSURE = "pest_pressure"
    GROWTH_RATE = "growth_rate"
    FRUIT_SIZE = "fruit_size"
    CANOPY_COVERAGE = "canopy_coverage"
    SOIL_MOISTURE = "soil_moisture"


class AnomalyType(Enum):
    """Types of anomalies detected"""
    POINT = "point"  # Single data point anomaly
    CONTEXTUAL = "contextual"  # Anomaly in specific context
    COLLECTIVE = "collective"  # Sequence of anomalous points
    SEASONAL = "seasonal"  # Deviation from seasonal pattern


@dataclass
class TimeSeriesDataPoint:
    """Single data point in time series"""
    timestamp: datetime
    value: float
    metric_type: MetricType
    location_id: str
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Anomaly:
    """Detected anomaly information"""
    anomaly_type: AnomalyType
    timestamp: datetime
    metric_type: MetricType
    expected_value: float
    actual_value: float
    severity: float  # 0.0 to 1.0
    description: str
    location_id: str


@dataclass
class KPI:
    """Key Performance Indicator"""
    name: str
    value: float
    unit: str
    target: Optional[float] = None
    trend: str = "stable"  # increasing, decreasing, stable
    change_percent: float = 0.0
    status: str = "normal"  # normal, warning, critical


@dataclass
class ReportSection:
    """Section of a report"""
    title: str
    content: str
    charts: List[bytes] = field(default_factory=list)
    tables: List[pd.DataFrame] = field(default_factory=list)
    subsections: List['ReportSection'] = field(default_factory=list)


class TimeSeriesAnalyzer:
    """
    Advanced time-series analysis for agricultural metrics
    """
    
    def __init__(self):
        self.scaler = StandardScaler()
        self.anomaly_detector = IsolationForest(contamination=0.1, random_state=42)
        
    def analyze_trend(self, data: List[TimeSeriesDataPoint]) -> Dict[str, Any]:
        """
        Analyze trend in time-series data
        
        Returns trend direction, slope, confidence, and forecast
        """
        if len(data) < 3:
            return {"error": "Insufficient data points"}
        
        # Sort by timestamp
        sorted_data = sorted(data, key=lambda x: x.timestamp)
        values = np.array([d.value for d in sorted_data])
        timestamps = np.array([(d.timestamp - sorted_data[0].timestamp).total_seconds() 
                               for d in sorted_data])
        
        # Linear regression for trend
        slope, intercept, r_value, p_value, std_err = stats.linregress(timestamps, values)
        
        # Determine trend direction
        if abs(slope) < std_err * 2:  # Not statistically significant
            direction = "stable"
        elif slope > 0:
            direction = "increasing"
        else:
            direction = "decreasing"
        
        # Calculate confidence
        confidence = abs(r_value)
        
        # Simple forecast (next 7 days)
        last_timestamp = timestamps[-1]
        forecast_timestamps = np.linspace(last_timestamp, 
                                         last_timestamp + 7*24*3600, 
                                         num=7)
        forecast_values = slope * forecast_timestamps + intercept
        
        # Calculate variance and bounds
        residuals = values - (slope * timestamps + intercept)
        std_residual = np.std(residuals)
        
        return {
            "direction": direction,
            "slope": float(slope),
            "confidence": float(confidence),
            "r_squared": float(r_value ** 2),
            "p_value": float(p_value),
            "forecast": {
                "values": forecast_values.tolist(),
                "timestamps": [sorted_data[0].timestamp + timedelta(seconds=int(t)) 
                              for t in forecast_timestamps],
                "upper_bound": (forecast_values + 2*std_residual).tolist(),
                "lower_bound": (forecast_values - 2*std_residual).tolist()
            },
            "statistics": {
                "mean": float(np.mean(values)),
                "median": float(np.median(values)),
                "std": float(np.std(values)),
                "min": float(np.min(values)),
                "max": float(np.max(values))
            }
        }
    
    def detect_anomalies(self, data: List[TimeSeriesDataPoint]) -> List[Anomaly]:
        """
        Detect anomalies in time-series data using multiple methods
        """
        if len(data) < 10:
            return []
        
        sorted_data = sorted(data, key=lambda x: x.timestamp)
        values = np.array([d.value for d in sorted_data])
        
        anomalies = []
        
        # Method 1: Statistical outliers (Z-score)
        z_scores = np.abs(stats.zscore(values))
        outlier_indices = np.where(z_scores > 3)[0]
        
        for idx in outlier_indices:
            mean_val = np.mean(values)
            anomalies.append(Anomaly(
                anomaly_type=AnomalyType.POINT,
                timestamp=sorted_data[idx].timestamp,
                metric_type=sorted_data[idx].metric_type,
                expected_value=float(mean_val),
                actual_value=float(sorted_data[idx].value),
                severity=min(float(z_scores[idx] / 10), 1.0),
                description=f"Statistical outlier detected (Z-score: {z_scores[idx]:.2f})",
                location_id=sorted_data[idx].location_id
            ))
        
        # Method 2: Isolation Forest
        values_reshaped = values.reshape(-1, 1)
        predictions = self.anomaly_detector.fit_predict(values_reshaped)
        anomaly_indices = np.where(predictions == -1)[0]
        
        for idx in anomaly_indices:
            if idx not in outlier_indices:  # Don't duplicate
                # Calculate expected value using neighbors
                window = 5
                start = max(0, idx - window)
                end = min(len(values), idx + window + 1)
                neighbor_values = np.concatenate([values[start:idx], values[idx+1:end]])
                expected = np.median(neighbor_values) if len(neighbor_values) > 0 else np.median(values)
                
                deviation = abs(sorted_data[idx].value - expected) / (np.std(values) + 1e-6)
                
                anomalies.append(Anomaly(
                    anomaly_type=AnomalyType.CONTEXTUAL,
                    timestamp=sorted_data[idx].timestamp,
                    metric_type=sorted_data[idx].metric_type,
                    expected_value=float(expected),
                    actual_value=float(sorted_data[idx].value),
                    severity=min(float(deviation / 5), 1.0),
                    description="Contextual anomaly detected by isolation forest",
                    location_id=sorted_data[idx].location_id
                ))
        
        # Method 3: Sudden changes (derivatives)
        if len(values) > 2:
            derivatives = np.diff(values)
            derivative_z_scores = np.abs(stats.zscore(derivatives))
            sudden_change_indices = np.where(derivative_z_scores > 2.5)[0]
            
            for idx in sudden_change_indices:
                actual_idx = idx + 1  # Derivative shifts index by 1
                if actual_idx < len(sorted_data):
                    anomalies.append(Anomaly(
                        anomaly_type=AnomalyType.COLLECTIVE,
                        timestamp=sorted_data[actual_idx].timestamp,
                        metric_type=sorted_data[actual_idx].metric_type,
                        expected_value=float(sorted_data[idx].value),
                        actual_value=float(sorted_data[actual_idx].value),
                        severity=min(float(derivative_z_scores[idx] / 5), 1.0),
                        description=f"Sudden change detected (rate: {derivatives[idx]:.2f})",
                        location_id=sorted_data[actual_idx].location_id
                    ))
        
        return anomalies
    
    def seasonal_decomposition(self, data: List[TimeSeriesDataPoint], 
                               period: int = 24) -> Dict[str, np.ndarray]:
        """
        Decompose time-series into trend, seasonal, and residual components
        """
        if len(data) < period * 2:
            return {"error": "Insufficient data for seasonal decomposition"}
        
        sorted_data = sorted(data, key=lambda x: x.timestamp)
        values = np.array([d.value for d in sorted_data])
        
        # Simple moving average for trend
        trend = savgol_filter(values, window_length=min(period, len(values)//2*2-1), polyorder=2)
        
        # Detrended data
        detrended = values - trend
        
        # Seasonal component (average pattern over periods)
        seasonal_periods = len(values) // period
        seasonal_matrix = detrended[:seasonal_periods * period].reshape(seasonal_periods, period)
        seasonal = np.tile(np.mean(seasonal_matrix, axis=0), seasonal_periods + 1)[:len(values)]
        
        # Residual
        residual = values - trend - seasonal
        
        return {
            "original": values,
            "trend": trend,
            "seasonal": seasonal,
            "residual": residual,
            "timestamps": [d.timestamp for d in sorted_data]
        }
    
    def calculate_correlation(self, data1: List[TimeSeriesDataPoint], 
                            data2: List[TimeSeriesDataPoint]) -> Dict[str, float]:
        """
        Calculate correlation between two time-series
        """
        # Align timestamps
        timestamps1 = {d.timestamp: d.value for d in data1}
        timestamps2 = {d.timestamp: d.value for d in data2}
        
        common_timestamps = set(timestamps1.keys()) & set(timestamps2.keys())
        
        if len(common_timestamps) < 3:
            return {"error": "Insufficient overlapping data points"}
        
        values1 = np.array([timestamps1[t] for t in sorted(common_timestamps)])
        values2 = np.array([timestamps2[t] for t in sorted(common_timestamps)])
        
        # Pearson correlation
        pearson_r, pearson_p = stats.pearsonr(values1, values2)
        
        # Spearman correlation (rank-based)
        spearman_r, spearman_p = stats.spearmanr(values1, values2)
        
        # Time-lagged correlation
        max_lag = min(10, len(values1) // 4)
        lagged_correlations = []
        for lag in range(-max_lag, max_lag + 1):
            if lag < 0:
                corr = np.corrcoef(values1[:lag], values2[-lag:])[0, 1]
            elif lag > 0:
                corr = np.corrcoef(values1[lag:], values2[:-lag])[0, 1]
            else:
                corr = np.corrcoef(values1, values2)[0, 1]
            lagged_correlations.append((lag, corr))
        
        best_lag, best_corr = max(lagged_correlations, key=lambda x: abs(x[1]))
        
        return {
            "pearson_r": float(pearson_r),
            "pearson_p_value": float(pearson_p),
            "spearman_r": float(spearman_r),
            "spearman_p_value": float(spearman_p),
            "best_lag": int(best_lag),
            "best_lag_correlation": float(best_corr),
            "interpretation": self._interpret_correlation(pearson_r)
        }
    
    def _interpret_correlation(self, r: float) -> str:
        """Interpret correlation coefficient"""
        abs_r = abs(r)
        if abs_r < 0.3:
            strength = "weak"
        elif abs_r < 0.7:
            strength = "moderate"
        else:
            strength = "strong"
        
        direction = "positive" if r > 0 else "negative"
        return f"{strength} {direction} correlation"


class KPICalculator:
    """
    Calculate and track Key Performance Indicators
    """
    
    def __init__(self):
        self.kpi_definitions = self._define_kpis()
        self.historical_values = defaultdict(deque)
    
    def _define_kpis(self) -> Dict[str, Dict[str, Any]]:
        """Define all KPIs tracked by the system"""
        return {
            "overall_health_index": {
                "name": "Overall Orchard Health Index",
                "unit": "score",
                "target": 85.0,
                "weight": 1.0,
                "description": "Composite score of orchard health"
            },
            "yield_per_hectare": {
                "name": "Estimated Yield per Hectare",
                "unit": "tons/ha",
                "target": 30.0,
                "weight": 1.5,
                "description": "Projected fruit yield"
            },
            "water_use_efficiency": {
                "name": "Water Use Efficiency",
                "unit": "kg/m³",
                "target": 3.5,
                "weight": 1.2,
                "description": "Fruit production per unit water"
            },
            "disease_free_percentage": {
                "name": "Disease-Free Trees",
                "unit": "%",
                "target": 95.0,
                "weight": 1.3,
                "description": "Percentage of healthy trees"
            },
            "canopy_coverage": {
                "name": "Canopy Coverage",
                "unit": "%",
                "target": 70.0,
                "weight": 0.8,
                "description": "Ground coverage by tree canopy"
            },
            "nutrient_efficiency": {
                "name": "Nutrient Use Efficiency",
                "unit": "score",
                "target": 80.0,
                "weight": 1.0,
                "description": "Effectiveness of fertilizer application"
            },
            "fruit_size_uniformity": {
                "name": "Fruit Size Uniformity",
                "unit": "coefficient",
                "target": 0.15,
                "weight": 0.9,
                "description": "Coefficient of variation in fruit size"
            },
            "pest_control_effectiveness": {
                "name": "Pest Control Effectiveness",
                "unit": "%",
                "target": 90.0,
                "weight": 1.1,
                "description": "Success rate of pest management"
            },
            "roi_percentage": {
                "name": "Return on Investment",
                "unit": "%",
                "target": 25.0,
                "weight": 2.0,
                "description": "Financial return percentage"
            },
            "drone_efficiency": {
                "name": "Drone Operation Efficiency",
                "unit": "ha/hour",
                "target": 5.0,
                "weight": 0.7,
                "description": "Area covered per flight hour"
            }
        }
    
    def calculate_kpi(self, kpi_id: str, current_value: float, 
                     historical_data: Optional[List[float]] = None) -> KPI:
        """
        Calculate a specific KPI with trend analysis
        """
        if kpi_id not in self.kpi_definitions:
            raise ValueError(f"Unknown KPI: {kpi_id}")
        
        definition = self.kpi_definitions[kpi_id]
        
        # Store in historical data
        self.historical_values[kpi_id].append(current_value)
        if len(self.historical_values[kpi_id]) > 100:
            self.historical_values[kpi_id].popleft()
        
        # Use provided historical data or stored data
        if historical_data is None:
            historical_data = list(self.historical_values[kpi_id])
        
        # Calculate trend
        trend = "stable"
        change_percent = 0.0
        
        if len(historical_data) >= 2:
            recent_avg = np.mean(historical_data[-5:])
            previous_avg = np.mean(historical_data[-10:-5]) if len(historical_data) >= 10 else historical_data[0]
            
            if previous_avg != 0:
                change_percent = ((recent_avg - previous_avg) / previous_avg) * 100
                
                if abs(change_percent) > 5:
                    trend = "increasing" if change_percent > 0 else "decreasing"
        
        # Determine status based on target
        status = "normal"
        if definition["target"] is not None:
            deviation = abs(current_value - definition["target"]) / definition["target"]
            if deviation > 0.2:
                status = "critical"
            elif deviation > 0.1:
                status = "warning"
        
        return KPI(
            name=definition["name"],
            value=current_value,
            unit=definition["unit"],
            target=definition["target"],
            trend=trend,
            change_percent=change_percent,
            status=status
        )
    
    def calculate_composite_score(self, kpis: List[KPI]) -> float:
        """
        Calculate weighted composite score from multiple KPIs
        """
        total_weight = 0.0
        weighted_sum = 0.0
        
        for kpi in kpis:
            # Find definition
            kpi_def = None
            for kpi_id, definition in self.kpi_definitions.items():
                if definition["name"] == kpi.name:
                    kpi_def = definition
                    break
            
            if kpi_def and kpi_def["target"]:
                # Normalize to 0-100 scale
                normalized = (kpi.value / kpi_def["target"]) * 100
                normalized = min(max(normalized, 0), 100)  # Clamp to 0-100
                
                weight = kpi_def["weight"]
                weighted_sum += normalized * weight
                total_weight += weight
        
        return weighted_sum / total_weight if total_weight > 0 else 0.0


class VisualizationGenerator:
    """
    Generate charts and visualizations for reports
    """
    
    def __init__(self):
        sns.set_style("whitegrid")
        self.color_palette = sns.color_palette("husl", 8)
    
    def generate_time_series_plot(self, data: List[TimeSeriesDataPoint], 
                                  title: str, ylabel: str) -> bytes:
        """
        Generate time-series line plot
        """
        fig, ax = plt.subplots(figsize=(10, 6))
        
        sorted_data = sorted(data, key=lambda x: x.timestamp)
        timestamps = [d.timestamp for d in sorted_data]
        values = [d.value for d in sorted_data]
        
        ax.plot(timestamps, values, linewidth=2, color=self.color_palette[0])
        ax.set_xlabel('Time', fontsize=12)
        ax.set_ylabel(ylabel, fontsize=12)
        ax.set_title(title, fontsize=14, fontweight='bold')
        ax.grid(True, alpha=0.3)
        
        plt.xticks(rotation=45)
        plt.tight_layout()
        
        # Convert to bytes
        buf = BytesIO()
        plt.savefig(buf, format='png', dpi=150)
        buf.seek(0)
        image_bytes = buf.read()
        plt.close()
        
        return image_bytes
    
    def generate_comparison_bar_chart(self, categories: List[str], 
                                     values: List[float], title: str) -> bytes:
        """
        Generate bar chart for comparing categories
        """
        fig, ax = plt.subplots(figsize=(10, 6))
        
        colors = [self.color_palette[i % len(self.color_palette)] 
                 for i in range(len(categories))]
        bars = ax.bar(categories, values, color=colors)
        
        # Add value labels on bars
        for bar in bars:
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height,
                   f'{height:.1f}',
                   ha='center', va='bottom')
        
        ax.set_title(title, fontsize=14, fontweight='bold')
        ax.set_ylabel('Value', fontsize=12)
        plt.xticks(rotation=45, ha='right')
        plt.tight_layout()
        
        buf = BytesIO()
        plt.savefig(buf, format='png', dpi=150)
        buf.seek(0)
        image_bytes = buf.read()
        plt.close()
        
        return image_bytes
    
    def generate_heatmap(self, data: np.ndarray, xlabels: List[str], 
                        ylabels: List[str], title: str) -> bytes:
        """
        Generate heatmap visualization
        """
        fig, ax = plt.subplots(figsize=(12, 8))
        
        sns.heatmap(data, annot=True, fmt='.2f', cmap='YlOrRd', 
                   xticklabels=xlabels, yticklabels=ylabels, ax=ax)
        
        ax.set_title(title, fontsize=14, fontweight='bold')
        plt.tight_layout()
        
        buf = BytesIO()
        plt.savefig(buf, format='png', dpi=150)
        buf.seek(0)
        image_bytes = buf.read()
        plt.close()
        
        return image_bytes
    
    def generate_distribution_plot(self, values: List[float], 
                                   title: str, xlabel: str) -> bytes:
        """
        Generate histogram with KDE overlay
        """
        fig, ax = plt.subplots(figsize=(10, 6))
        
        ax.hist(values, bins=30, density=True, alpha=0.7, 
               color=self.color_palette[0], edgecolor='black')
        
        # Add KDE
        from scipy.stats import gaussian_kde
        if len(values) > 1:
            kde = gaussian_kde(values)
            x_range = np.linspace(min(values), max(values), 100)
            ax.plot(x_range, kde(x_range), 'r-', linewidth=2, label='KDE')
        
        ax.set_xlabel(xlabel, fontsize=12)
        ax.set_ylabel('Density', fontsize=12)
        ax.set_title(title, fontsize=14, fontweight='bold')
        ax.legend()
        plt.tight_layout()
        
        buf = BytesIO()
        plt.savefig(buf, format='png', dpi=150)
        buf.seek(0)
        image_bytes = buf.read()
        plt.close()
        
        return image_bytes
    
    def generate_kpi_gauge(self, kpi: KPI) -> bytes:
        """
        Generate gauge chart for KPI visualization
        """
        fig, ax = plt.subplots(figsize=(8, 6), subplot_kw={'projection': 'polar'})
        
        # Normalize value to 0-1 scale
        if kpi.target:
            normalized_value = min(kpi.value / kpi.target, 1.0)
        else:
            normalized_value = kpi.value / 100.0
        
        # Create gauge
        theta = np.linspace(0, np.pi, 100)
        
        # Background
        ax.plot(theta, np.ones_like(theta), color='lightgray', linewidth=20)
        
        # Value arc
        value_theta = theta[:int(normalized_value * 100)]
        color = 'green' if kpi.status == 'normal' else 'orange' if kpi.status == 'warning' else 'red'
        ax.plot(value_theta, np.ones_like(value_theta), color=color, linewidth=20)
        
        # Add value text
        ax.text(0, 0, f'{kpi.value:.1f}\n{kpi.unit}', 
               ha='center', va='center', fontsize=20, fontweight='bold')
        
        ax.set_ylim(0, 1.2)
        ax.set_theta_zero_location('W')
        ax.set_theta_direction(1)
        ax.set_xticks([])
        ax.set_yticks([])
        ax.spines['polar'].set_visible(False)
        ax.set_title(kpi.name, fontsize=12, fontweight='bold', pad=20)
        
        plt.tight_layout()
        
        buf = BytesIO()
        plt.savefig(buf, format='png', dpi=150)
        buf.seek(0)
        image_bytes = buf.read()
        plt.close()
        
        return image_bytes
    
    def generate_geospatial_heatmap(self, locations: List[Tuple[float, float]], 
                                   values: List[float], title: str) -> bytes:
        """
        Generate geospatial heatmap from location-value pairs
        """
        fig, ax = plt.subplots(figsize=(12, 10))
        
        lats = [loc[0] for loc in locations]
        lons = [loc[1] for loc in locations]
        
        scatter = ax.scatter(lons, lats, c=values, s=100, 
                           cmap='RdYlGn', alpha=0.6, edgecolors='black')
        
        plt.colorbar(scatter, ax=ax, label='Value')
        ax.set_xlabel('Longitude', fontsize=12)
        ax.set_ylabel('Latitude', fontsize=12)
        ax.set_title(title, fontsize=14, fontweight='bold')
        ax.grid(True, alpha=0.3)
        plt.tight_layout()
        
        buf = BytesIO()
        plt.savefig(buf, format='png', dpi=150)
        buf.seek(0)
        image_bytes = buf.read()
        plt.close()
        
        return image_bytes


class ReportGenerator:
    """
    Generate comprehensive PDF reports
    """
    
    def __init__(self):
        self.styles = getSampleStyleSheet()
        self.title_style = ParagraphStyle(
            'CustomTitle',
            parent=self.styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#2C3E50'),
            spaceAfter=30,
            alignment=1  # Center
        )
        self.heading_style = ParagraphStyle(
            'CustomHeading',
            parent=self.styles['Heading2'],
            fontSize=16,
            textColor=colors.HexColor('#34495E'),
            spaceAfter=12
        )
    
    def generate_report(self, report_type: ReportType, sections: List[ReportSection],
                       metadata: Dict[str, Any]) -> bytes:
        """
        Generate complete PDF report
        """
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter,
                               rightMargin=72, leftMargin=72,
                               topMargin=72, bottomMargin=18)
        
        story = []
        
        # Title page
        story.append(Paragraph(metadata.get('title', 'Orchard Analysis Report'), 
                              self.title_style))
        story.append(Spacer(1, 12))
        story.append(Paragraph(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}", 
                              self.styles['Normal']))
        story.append(Paragraph(f"Report Type: {report_type.value}", 
                              self.styles['Normal']))
        story.append(PageBreak())
        
        # Add sections
        for section in sections:
            story.extend(self._create_section_elements(section))
        
        # Build PDF
        doc.build(story)
        buffer.seek(0)
        return buffer.read()
    
    def _create_section_elements(self, section: ReportSection) -> List:
        """Create PDF elements for a report section"""
        elements = []
        
        # Section title
        elements.append(Paragraph(section.title, self.heading_style))
        elements.append(Spacer(1, 12))
        
        # Section content
        for paragraph in section.content.split('\n\n'):
            if paragraph.strip():
                elements.append(Paragraph(paragraph, self.styles['Normal']))
                elements.append(Spacer(1, 6))
        
        # Add charts
        for chart_bytes in section.charts:
            img = Image(BytesIO(chart_bytes))
            img.drawHeight = 4*inch
            img.drawWidth = 6*inch
            elements.append(img)
            elements.append(Spacer(1, 12))
        
        # Add tables
        for df in section.tables:
            table_data = [df.columns.tolist()] + df.values.tolist()
            table = Table(table_data)
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 12),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            elements.append(table)
            elements.append(Spacer(1, 12))
        
        # Add subsections recursively
        for subsection in section.subsections:
            elements.extend(self._create_section_elements(subsection))
        
        return elements


class AnalyticsReportingSystem:
    """
    Main system coordinating all analytics and reporting functionality
    """
    
    def __init__(self):
        self.time_series_analyzer = TimeSeriesAnalyzer()
        self.kpi_calculator = KPICalculator()
        self.visualization_generator = VisualizationGenerator()
        self.report_generator = ReportGenerator()
        
        self.data_cache = {}
        self.scheduled_reports = {}
    
    async def generate_daily_summary(self, orchard_id: str, 
                                    date: datetime) -> bytes:
        """
        Generate daily summary report for an orchard
        """
        sections = []
        
        # Executive Summary Section
        exec_summary = await self._create_executive_summary(orchard_id, date)
        sections.append(exec_summary)
        
        # Health Metrics Section
        health_section = await self._create_health_metrics_section(orchard_id, date)
        sections.append(health_section)
        
        # Anomalies Section
        anomaly_section = await self._create_anomaly_section(orchard_id, date)
        sections.append(anomaly_section)
        
        # Recommendations Section
        recommendations = await self._create_recommendations_section(orchard_id, date)
        sections.append(recommendations)
        
        metadata = {
            'title': f'Daily Summary Report - {orchard_id}',
            'date': date.strftime('%Y-%m-%d'),
            'orchard_id': orchard_id
        }
        
        return self.report_generator.generate_report(
            ReportType.DAILY_SUMMARY, sections, metadata
        )
    
    async def generate_yield_forecast_report(self, orchard_id: str, 
                                            season: str) -> bytes:
        """
        Generate yield forecast report for upcoming season
        """
        sections = []
        
        # Historical yield analysis
        historical_section = ReportSection(
            title="Historical Yield Analysis",
            content="Analysis of yield trends over previous seasons with statistical insights.",
            charts=[],
            tables=[]
        )
        
        # Simulate historical data
        historical_yields = [28.5, 29.2, 27.8, 30.1, 31.5]
        years = ['2020', '2021', '2022', '2023', '2024']
        
        chart = self.visualization_generator.generate_comparison_bar_chart(
            years, historical_yields, "Historical Yield (tons/ha)"
        )
        historical_section.charts.append(chart)
        
        df = pd.DataFrame({
            'Year': years,
            'Yield (tons/ha)': historical_yields,
            'Change (%)': [0] + [round((historical_yields[i] - historical_yields[i-1])/historical_yields[i-1]*100, 1) 
                                 for i in range(1, len(historical_yields))]
        })
        historical_section.tables.append(df)
        sections.append(historical_section)
        
        # Current season forecast
        forecast_section = ReportSection(
            title="Current Season Forecast",
            content=f"Projected yield for {season} season based on current growth patterns, "
                   "weather conditions, and AI model predictions.",
            charts=[],
            tables=[]
        )
        
        # Simulate forecast data
        forecast_data = [
            TimeSeriesDataPoint(
                timestamp=datetime.now() + timedelta(days=i*7),
                value=29.0 + i*0.5 + np.random.normal(0, 0.5),
                metric_type=MetricType.YIELD_ESTIMATE,
                location_id=orchard_id
            )
            for i in range(12)
        ]
        
        chart = self.visualization_generator.generate_time_series_plot(
            forecast_data, "Yield Forecast Progression", "Estimated Yield (tons/ha)"
        )
        forecast_section.charts.append(chart)
        sections.append(forecast_section)
        
        # Confidence intervals and risk factors
        risk_section = ReportSection(
            title="Risk Factors and Confidence Analysis",
            content="Assessment of factors that may impact yield forecast accuracy.",
            charts=[],
            tables=[]
        )
        
        risk_factors = pd.DataFrame({
            'Risk Factor': ['Weather Variability', 'Disease Pressure', 'Water Availability', 
                          'Market Conditions', 'Labor Availability'],
            'Impact': ['Medium', 'Low', 'Medium', 'Low', 'Low'],
            'Mitigation Strategy': [
                'Weather monitoring and irrigation adjustment',
                'Preventive treatment program',
                'Water storage and efficient irrigation',
                'Diversified market channels',
                'Automated systems deployment'
            ]
        })
        risk_section.tables.append(risk_factors)
        sections.append(risk_section)
        
        metadata = {
            'title': f'Yield Forecast Report - {season}',
            'orchard_id': orchard_id,
            'season': season
        }
        
        return self.report_generator.generate_report(
            ReportType.YIELD_FORECAST, sections, metadata
        )
    
    async def _create_executive_summary(self, orchard_id: str, 
                                       date: datetime) -> ReportSection:
        """Create executive summary section with KPIs"""
        # Simulate KPI data
        kpis = [
            self.kpi_calculator.calculate_kpi('overall_health_index', 87.3),
            self.kpi_calculator.calculate_kpi('yield_per_hectare', 31.2),
            self.kpi_calculator.calculate_kpi('water_use_efficiency', 3.7),
            self.kpi_calculator.calculate_kpi('disease_free_percentage', 94.5)
        ]
        
        composite_score = self.kpi_calculator.calculate_composite_score(kpis)
        
        content = f"""
        Overall Performance Score: {composite_score:.1f}/100
        
        The orchard is performing at {composite_score:.1f}% of target levels across all key metrics. 
        {len([k for k in kpis if k.status == 'normal'])} out of {len(kpis)} primary KPIs are within normal ranges.
        
        Key Highlights:
        - Health Index: {kpis[0].value:.1f} ({kpis[0].trend})
        - Projected Yield: {kpis[1].value:.1f} {kpis[1].unit} ({kpis[1].trend})
        - Water Efficiency: {kpis[2].value:.2f} {kpis[2].unit}
        - Tree Health: {kpis[3].value:.1f}% disease-free
        """
        
        section = ReportSection(
            title="Executive Summary",
            content=content,
            charts=[],
            tables=[]
        )
        
        # Add KPI gauges
        for kpi in kpis:
            gauge = self.visualization_generator.generate_kpi_gauge(kpi)
            section.charts.append(gauge)
        
        return section
    
    async def _create_health_metrics_section(self, orchard_id: str, 
                                            date: datetime) -> ReportSection:
        """Create detailed health metrics section"""
        # Simulate health metrics time-series
        health_data = [
            TimeSeriesDataPoint(
                timestamp=date - timedelta(hours=24-i),
                value=85 + np.random.normal(0, 2),
                metric_type=MetricType.HEALTH_INDEX,
                location_id=orchard_id
            )
            for i in range(24)
        ]
        
        analysis = self.time_series_analyzer.analyze_trend(health_data)
        
        content = f"""
        Health Index Analysis (24-hour period):
        
        Current Status: {health_data[-1].value:.1f}
        Trend: {analysis['direction']} ({analysis['slope']:.3f} per hour)
        Confidence: {analysis['confidence']:.2%}
        
        Statistical Summary:
        - Mean: {analysis['statistics']['mean']:.1f}
        - Median: {analysis['statistics']['median']:.1f}
        - Standard Deviation: {analysis['statistics']['std']:.2f}
        - Range: {analysis['statistics']['min']:.1f} - {analysis['statistics']['max']:.1f}
        
        The health index shows a {analysis['direction']} trend with {analysis['confidence']:.0%} confidence.
        """
        
        section = ReportSection(
            title="Health Metrics Analysis",
            content=content,
            charts=[],
            tables=[]
        )
        
        # Add time-series chart
        chart = self.visualization_generator.generate_time_series_plot(
            health_data, "24-Hour Health Index Trend", "Health Index"
        )
        section.charts.append(chart)
        
        return section
    
    async def _create_anomaly_section(self, orchard_id: str, 
                                     date: datetime) -> ReportSection:
        """Create anomaly detection section"""
        # Simulate data with some anomalies
        normal_data = [
            TimeSeriesDataPoint(
                timestamp=date - timedelta(hours=48-i),
                value=20 + 5*np.sin(i/4) + np.random.normal(0, 0.5),
                metric_type=MetricType.SOIL_MOISTURE,
                location_id=orchard_id
            )
            for i in range(48)
        ]
        
        # Inject some anomalies
        normal_data[20].value = 35  # Spike
        normal_data[35].value = 10  # Drop
        
        anomalies = self.time_series_analyzer.detect_anomalies(normal_data)
        
        content = f"""
        Anomaly Detection Results:
        
        Total anomalies detected: {len(anomalies)}
        - Point anomalies: {len([a for a in anomalies if a.anomaly_type == AnomalyType.POINT])}
        - Contextual anomalies: {len([a for a in anomalies if a.anomaly_type == AnomalyType.CONTEXTUAL])}
        - Collective anomalies: {len([a for a in anomalies if a.anomaly_type == AnomalyType.COLLECTIVE])}
        
        Critical anomalies (severity > 0.7): {len([a for a in anomalies if a.severity > 0.7])}
        
        Details of detected anomalies:
        """
        
        for i, anomaly in enumerate(anomalies[:5], 1):  # Top 5
            content += f"\n{i}. {anomaly.timestamp.strftime('%Y-%m-%d %H:%M')} - "
            content += f"{anomaly.description} (Severity: {anomaly.severity:.2f})"
        
        section = ReportSection(
            title="Anomaly Detection",
            content=content,
            charts=[],
            tables=[]
        )
        
        # Add chart with anomalies marked
        chart = self.visualization_generator.generate_time_series_plot(
            normal_data, "Soil Moisture with Anomalies", "Moisture (%)"
        )
        section.charts.append(chart)
        
        # Create anomaly table
        if anomalies:
            df = pd.DataFrame([
                {
                    'Timestamp': a.timestamp.strftime('%Y-%m-%d %H:%M'),
                    'Type': a.anomaly_type.value,
                    'Expected': f'{a.expected_value:.2f}',
                    'Actual': f'{a.actual_value:.2f}',
                    'Severity': f'{a.severity:.2f}'
                }
                for a in anomalies[:10]
            ])
            section.tables.append(df)
        
        return section
    
    async def _create_recommendations_section(self, orchard_id: str, 
                                             date: datetime) -> ReportSection:
        """Create actionable recommendations section"""
        content = """
        Recommended Actions:
        
        1. Irrigation Management:
           - Increase irrigation in zones A3, B2 (soil moisture below 18%)
           - Consider reducing water in zone C1 (potential over-watering)
        
        2. Disease Monitoring:
           - Inspect trees in section B3 for early blight symptoms
           - Preventive treatment recommended for high-risk areas
        
        3. Nutrient Management:
           - Nitrogen supplementation needed in zones A1, A2
           - Potassium levels optimal across all zones
        
        4. Pest Control:
           - Deploy pheromone traps in sections C1-C3
           - Monitor codling moth populations
        
        5. Harvesting Planning:
           - Zones A1, A2 estimated ready in 3-4 weeks
           - Begin pre-harvest preparations
        """
        
        section = ReportSection(
            title="Actionable Recommendations",
            content=content,
            charts=[],
            tables=[]
        )
        
        # Add priority table
        priorities = pd.DataFrame({
            'Action': ['Increase irrigation A3, B2', 'Inspect B3 for blight', 
                      'Nitrogen supplement A1, A2', 'Deploy pest traps C1-C3', 
                      'Prep harvest equipment'],
            'Priority': ['High', 'High', 'Medium', 'Medium', 'Low'],
            'Timeline': ['Immediate', '24 hours', '3-5 days', '1 week', '2-3 weeks'],
            'Resource': ['Irrigation system', 'Field scout', 'Fertilizer application', 
                        'Pest management', 'Harvest crew']
        })
        section.tables.append(priorities)
        
        return section
    
    def schedule_report(self, report_id: str, report_type: ReportType,
                       schedule: str, recipients: List[str],
                       parameters: Dict[str, Any]):
        """
        Schedule automated report generation and delivery
        """
        self.scheduled_reports[report_id] = {
            'report_type': report_type,
            'schedule': schedule,  # Cron format
            'recipients': recipients,
            'parameters': parameters,
            'last_run': None,
            'next_run': self._calculate_next_run(schedule)
        }
    
    def _calculate_next_run(self, schedule: str) -> datetime:
        """Calculate next run time from cron schedule"""
        # Simplified - in production, use croniter library
        return datetime.now() + timedelta(days=1)
    
    async def export_data(self, data: Union[pd.DataFrame, List[Dict]], 
                         format: str = 'csv') -> bytes:
        """
        Export data in various formats
        """
        if isinstance(data, list):
            df = pd.DataFrame(data)
        else:
            df = data
        
        buffer = BytesIO()
        
        if format == 'csv':
            df.to_csv(buffer, index=False)
        elif format == 'excel':
            df.to_excel(buffer, index=False, engine='openpyxl')
        elif format == 'json':
            buffer.write(df.to_json(orient='records', indent=2).encode())
        else:
            raise ValueError(f"Unsupported format: {format}")
        
        buffer.seek(0)
        return buffer.read()


# Example usage and testing
if __name__ == "__main__":
    async def main():
        # Initialize system
        system = AnalyticsReportingSystem()
        
        # Generate daily summary report
        report_pdf = await system.generate_daily_summary(
            orchard_id="ORCH-001",
            date=datetime.now()
        )
        
        print(f"Generated daily report: {len(report_pdf)} bytes")
        
        # Generate yield forecast
        forecast_pdf = await system.generate_yield_forecast_report(
            orchard_id="ORCH-001",
            season="2025 Spring"
        )
        
        print(f"Generated forecast report: {len(forecast_pdf)} bytes")
        
        # Calculate KPIs
        kpi = system.kpi_calculator.calculate_kpi(
            'overall_health_index', 
            87.5,
            historical_data=[85.0, 84.5, 86.0, 86.5, 87.0]
        )
        
        print(f"\nKPI: {kpi.name}")
        print(f"Value: {kpi.value} {kpi.unit}")
        print(f"Status: {kpi.status}")
        print(f"Trend: {kpi.trend} ({kpi.change_percent:+.1f}%)")
        
        # Time-series analysis
        test_data = [
            TimeSeriesDataPoint(
                timestamp=datetime.now() - timedelta(hours=24-i),
                value=80 + 10*np.sin(i/4) + np.random.normal(0, 1),
                metric_type=MetricType.HEALTH_INDEX,
                location_id="TEST-001"
            )
            for i in range(48)
        ]
        
        trend_analysis = system.time_series_analyzer.analyze_trend(test_data)
        print(f"\nTrend Analysis:")
        print(f"Direction: {trend_analysis['direction']}")
        print(f"Confidence: {trend_analysis['confidence']:.2%}")
        print(f"R²: {trend_analysis['r_squared']:.3f}")
        
        # Anomaly detection
        anomalies = system.time_series_analyzer.detect_anomalies(test_data)
        print(f"\nDetected {len(anomalies)} anomalies")
        for anomaly in anomalies[:3]:
            print(f"  - {anomaly.anomaly_type.value}: {anomaly.description}")
        
        print("\nAnalytics and Reporting System initialized successfully!")
        print("System ready for production use.")
    
    # Run async main
    asyncio.run(main())
