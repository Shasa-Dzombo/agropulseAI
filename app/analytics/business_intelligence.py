"""
Advanced Analytics and Business Intelligence

Data warehousing, OLAP, reporting, dashboards, predictive analytics.

Features:
- Data warehouse design
- Star schema implementation
- OLAP cube operations
- Report generation
- Dashboard metrics
- Time series forecasting
- Cohort analysis
- Funnel analytics
"""

import logging
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import json

try:
    import numpy as np
    import pandas as pd
    from scipy import stats
    from sklearn.preprocessing import StandardScaler
    from sklearn.ensemble import RandomForestRegressor
    ANALYTICS_AVAILABLE = True
except ImportError:
    ANALYTICS_AVAILABLE = False
    logging.warning("Analytics libraries not available")


logger = logging.getLogger(__name__)


class DimensionLevel(Enum):
    """OLAP dimension levels"""
    YEAR = "year"
    QUARTER = "quarter"
    MONTH = "month"
    WEEK = "week"
    DAY = "day"
    HOUR = "hour"


@dataclass
class Dimension:
    """OLAP dimension"""
    name: str
    hierarchy: List[str]
    attributes: Dict[str, List[str]] = field(default_factory=dict)


@dataclass
class Measure:
    """OLAP measure"""
    name: str
    aggregation_func: str  # sum, avg, count, min, max
    data_type: str = "float"


@dataclass
class DashboardMetric:
    """Dashboard metric definition"""
    metric_id: str
    name: str
    description: str
    query: str
    visualization_type: str  # line, bar, pie, table, gauge
    refresh_interval: int = 300  # seconds
    thresholds: Dict[str, float] = field(default_factory=dict)
    

class DataWarehouse:
    """
    Agricultural data warehouse
    
    Star schema with fact and dimension tables.
    """
    
    def __init__(self):
        """Initialize data warehouse"""
        if not ANALYTICS_AVAILABLE:
            raise RuntimeError("Analytics libraries not available")
        
        # Fact tables
        self.fact_harvest = pd.DataFrame()
        self.fact_irrigation = pd.DataFrame()
        self.fact_sensors = pd.DataFrame()
        self.fact_sales = pd.DataFrame()
        
        # Dimension tables
        self.dim_time = pd.DataFrame()
        self.dim_farm = pd.DataFrame()
        self.dim_crop = pd.DataFrame()
        self.dim_weather = pd.DataFrame()
        
        self._initialize_dimensions()
        
        logger.info("DataWarehouse initialized")
    
    def _initialize_dimensions(self):
        """Initialize dimension tables"""
        # Time dimension
        date_range = pd.date_range(start='2020-01-01', end='2025-12-31', freq='D')
        
        self.dim_time = pd.DataFrame({
            'time_key': range(len(date_range)),
            'date': date_range,
            'year': date_range.year,
            'quarter': date_range.quarter,
            'month': date_range.month,
            'week': date_range.isocalendar().week,
            'day_of_week': date_range.dayofweek,
            'day_of_month': date_range.day,
            'day_of_year': date_range.dayofyear,
            'is_weekend': date_range.dayofweek.isin([5, 6]).astype(int)
        })
        
        # Farm dimension
        self.dim_farm = pd.DataFrame({
            'farm_key': range(1000),
            'farm_id': [f'FARM_{i:04d}' for i in range(1000)],
            'region': np.random.choice(['North', 'South', 'East', 'West'], 1000),
            'size_hectares': np.random.uniform(10, 500, 1000),
            'soil_type': np.random.choice(['Clay', 'Loam', 'Sandy', 'Silt'], 1000)
        })
        
        # Crop dimension
        crops = ['Tomato', 'Potato', 'Corn', 'Wheat', 'Rice', 'Soybean']
        varieties = ['Var_A', 'Var_B', 'Var_C']
        
        crop_data = []
        for i, crop in enumerate(crops):
            for j, variety in enumerate(varieties):
                crop_data.append({
                    'crop_key': i * len(varieties) + j,
                    'crop_name': crop,
                    'crop_variety': variety,
                    'crop_family': 'Family_' + crop[0],
                    'growth_season': np.random.choice(['Spring', 'Summer', 'Fall'], 1)
                })
        
        self.dim_crop = pd.DataFrame(crop_data)
        
        logger.info("Dimension tables initialized")
    
    def load_harvest_facts(
        self,
        harvest_data: List[Dict]
    ):
        """
        Load harvest fact data
        
        Args:
            harvest_data: List of harvest records
        """
        df = pd.DataFrame(harvest_data)
        
        # Add surrogate keys
        df = df.merge(
            self.dim_time[['date', 'time_key']],
            left_on='harvest_date',
            right_on='date',
            how='left'
        )
        
        df = df.merge(
            self.dim_farm[['farm_id', 'farm_key']],
            on='farm_id',
            how='left'
        )
        
        df = df.merge(
            self.dim_crop[['crop_name', 'crop_variety', 'crop_key']],
            on=['crop_name', 'crop_variety'],
            how='left'
        )
        
        self.fact_harvest = pd.concat([self.fact_harvest, df], ignore_index=True)
        
        logger.info(f"Loaded {len(df)} harvest facts")
    
    def query_facts(
        self,
        fact_table: str,
        dimensions: List[str],
        measures: List[str],
        filters: Optional[Dict] = None,
        time_range: Optional[Tuple[datetime, datetime]] = None
    ) -> pd.DataFrame:
        """
        Query fact table with dimensions
        
        Args:
            fact_table: Fact table name
            dimensions: Dimension columns to group by
            measures: Measure columns to aggregate
            filters: Filter conditions
            time_range: Time range filter
            
        Returns:
            Query result DataFrame
        """
        # Get fact table
        if fact_table == 'harvest':
            facts = self.fact_harvest
        elif fact_table == 'irrigation':
            facts = self.fact_irrigation
        elif fact_table == 'sensors':
            facts = self.fact_sensors
        elif fact_table == 'sales':
            facts = self.fact_sales
        else:
            raise ValueError(f"Unknown fact table: {fact_table}")
        
        if facts.empty:
            return pd.DataFrame()
        
        # Apply filters
        filtered = facts.copy()
        
        if filters:
            for col, value in filters.items():
                if col in filtered.columns:
                    filtered = filtered[filtered[col] == value]
        
        if time_range:
            start_date, end_date = time_range
            if 'harvest_date' in filtered.columns:
                filtered = filtered[
                    (filtered['harvest_date'] >= start_date) &
                    (filtered['harvest_date'] <= end_date)
                ]
        
        # Group and aggregate
        if dimensions and measures:
            result = filtered.groupby(dimensions)[measures].agg(['sum', 'mean', 'count'])
            return result
        
        return filtered


class OLAPCube:
    """
    OLAP cube for multidimensional analysis
    
    Enables slice, dice, drill-down, roll-up operations.
    """
    
    def __init__(
        self,
        name: str,
        dimensions: List[Dimension],
        measures: List[Measure]
    ):
        """
        Initialize OLAP cube
        
        Args:
            name: Cube name
            dimensions: List of dimensions
            measures: List of measures
        """
        if not ANALYTICS_AVAILABLE:
            raise RuntimeError("Analytics libraries not available")
        
        self.name = name
        self.dimensions = {d.name: d for d in dimensions}
        self.measures = {m.name: m for m in measures}
        
        self.data: Optional[pd.DataFrame] = None
        
        logger.info(f"OLAPCube '{name}' initialized")
    
    def load_data(self, data: pd.DataFrame):
        """Load data into cube"""
        self.data = data.copy()
        logger.info(f"Loaded {len(data)} rows into cube '{self.name}'")
    
    def slice(
        self,
        dimension: str,
        value: Any
    ) -> 'OLAPCube':
        """
        Slice operation: select a single value for a dimension
        
        Args:
            dimension: Dimension name
            value: Dimension value
            
        Returns:
            New cube with sliced data
        """
        if dimension not in self.dimensions:
            raise ValueError(f"Unknown dimension: {dimension}")
        
        sliced_cube = OLAPCube(
            f"{self.name}_sliced",
            list(self.dimensions.values()),
            list(self.measures.values())
        )
        
        if self.data is not None:
            sliced_data = self.data[self.data[dimension] == value].copy()
            sliced_cube.load_data(sliced_data)
        
        return sliced_cube
    
    def dice(
        self,
        filters: Dict[str, List[Any]]
    ) -> 'OLAPCube':
        """
        Dice operation: select multiple values for multiple dimensions
        
        Args:
            filters: Dictionary of dimension -> values
            
        Returns:
            New cube with diced data
        """
        diced_cube = OLAPCube(
            f"{self.name}_diced",
            list(self.dimensions.values()),
            list(self.measures.values())
        )
        
        if self.data is not None:
            diced_data = self.data.copy()
            
            for dimension, values in filters.items():
                if dimension in self.dimensions:
                    diced_data = diced_data[diced_data[dimension].isin(values)]
            
            diced_cube.load_data(diced_data)
        
        return diced_cube
    
    def drill_down(
        self,
        dimension: str,
        from_level: str,
        to_level: str
    ) -> pd.DataFrame:
        """
        Drill-down operation: navigate to more detailed level
        
        Args:
            dimension: Dimension name
            from_level: Current level
            to_level: Target (more detailed) level
            
        Returns:
            Aggregated data at target level
        """
        if dimension not in self.dimensions:
            raise ValueError(f"Unknown dimension: {dimension}")
        
        dim = self.dimensions[dimension]
        
        if to_level not in dim.hierarchy:
            raise ValueError(f"Unknown level: {to_level}")
        
        if self.data is None:
            return pd.DataFrame()
        
        # Group by target level
        measure_cols = list(self.measures.keys())
        result = self.data.groupby(to_level)[measure_cols].agg('sum')
        
        return result
    
    def roll_up(
        self,
        dimension: str,
        from_level: str,
        to_level: str
    ) -> pd.DataFrame:
        """
        Roll-up operation: navigate to less detailed level
        
        Args:
            dimension: Dimension name
            from_level: Current level
            to_level: Target (less detailed) level
            
        Returns:
            Aggregated data at target level
        """
        return self.drill_down(dimension, to_level, from_level)
    
    def pivot(
        self,
        rows: List[str],
        columns: List[str],
        values: str,
        aggfunc: str = 'sum'
    ) -> pd.DataFrame:
        """
        Create pivot table
        
        Args:
            rows: Row dimensions
            columns: Column dimensions
            values: Value measure
            aggfunc: Aggregation function
            
        Returns:
            Pivot table
        """
        if self.data is None:
            return pd.DataFrame()
        
        return pd.pivot_table(
            self.data,
            values=values,
            index=rows,
            columns=columns,
            aggfunc=aggfunc,
            fill_value=0
        )


class TimeSeriesForecaster:
    """
    Time series forecasting for agricultural metrics
    
    Uses various forecasting techniques.
    """
    
    def __init__(self):
        """Initialize forecaster"""
        if not ANALYTICS_AVAILABLE:
            raise RuntimeError("Analytics libraries not available")
        
        self.models: Dict[str, Any] = {}
        
        logger.info("TimeSeriesForecaster initialized")
    
    def forecast_yield(
        self,
        historical_data: pd.DataFrame,
        horizon: int = 30
    ) -> pd.DataFrame:
        """
        Forecast crop yield
        
        Args:
            historical_data: Historical yield data
            horizon: Forecast horizon (days)
            
        Returns:
            Forecast DataFrame
        """
        # Simple moving average forecast
        if len(historical_data) < 7:
            return pd.DataFrame()
        
        # Calculate moving average
        window = min(7, len(historical_data))
        ma = historical_data['yield'].rolling(window=window).mean()
        
        # Generate forecast
        last_value = ma.iloc[-1]
        
        forecast_dates = pd.date_range(
            start=historical_data['date'].max() + timedelta(days=1),
            periods=horizon,
            freq='D'
        )
        
        forecast_df = pd.DataFrame({
            'date': forecast_dates,
            'forecast': last_value,
            'lower_bound': last_value * 0.9,
            'upper_bound': last_value * 1.1
        })
        
        return forecast_df
    
    def forecast_demand(
        self,
        historical_sales: pd.DataFrame,
        features: Optional[pd.DataFrame] = None,
        horizon: int = 7
    ) -> pd.DataFrame:
        """
        Forecast crop demand using ML
        
        Args:
            historical_sales: Historical sales data
            features: Optional feature matrix
            horizon: Forecast horizon (days)
            
        Returns:
            Demand forecast
        """
        if len(historical_sales) < 30:
            return pd.DataFrame()
        
        # Prepare features
        historical_sales = historical_sales.sort_values('date')
        historical_sales['day_of_week'] = pd.to_datetime(historical_sales['date']).dt.dayofweek
        historical_sales['month'] = pd.to_datetime(historical_sales['date']).dt.month
        
        # Create lagged features
        for lag in [1, 7, 14]:
            historical_sales[f'lag_{lag}'] = historical_sales['sales'].shift(lag)
        
        # Drop NaN rows
        historical_sales = historical_sales.dropna()
        
        if len(historical_sales) < 20:
            return pd.DataFrame()
        
        # Train model
        feature_cols = ['day_of_week', 'month', 'lag_1', 'lag_7', 'lag_14']
        X = historical_sales[feature_cols]
        y = historical_sales['sales']
        
        model = RandomForestRegressor(n_estimators=100, random_state=42)
        model.fit(X, y)
        
        # Generate forecast
        last_date = historical_sales['date'].max()
        forecast_dates = pd.date_range(
            start=last_date + timedelta(days=1),
            periods=horizon,
            freq='D'
        )
        
        forecasts = []
        
        for date in forecast_dates:
            # Create features for forecast date
            features_dict = {
                'day_of_week': date.dayofweek,
                'month': date.month,
                'lag_1': historical_sales['sales'].iloc[-1],
                'lag_7': historical_sales['sales'].iloc[-7] if len(historical_sales) >= 7 else historical_sales['sales'].iloc[-1],
                'lag_14': historical_sales['sales'].iloc[-14] if len(historical_sales) >= 14 else historical_sales['sales'].iloc[-1]
            }
            
            X_forecast = pd.DataFrame([features_dict])
            prediction = model.predict(X_forecast)[0]
            
            forecasts.append({
                'date': date,
                'forecast': prediction
            })
        
        return pd.DataFrame(forecasts)


class CohortAnalyzer:
    """
    Cohort analysis for farmer engagement and retention
    """
    
    def __init__(self):
        """Initialize cohort analyzer"""
        if not ANALYTICS_AVAILABLE:
            raise RuntimeError("Analytics libraries not available")
        
        logger.info("CohortAnalyzer initialized")
    
    def analyze_retention(
        self,
        user_activity: pd.DataFrame,
        cohort_column: str = 'signup_month',
        activity_column: str = 'active_month'
    ) -> pd.DataFrame:
        """
        Analyze user retention by cohort
        
        Args:
            user_activity: User activity data
            cohort_column: Column defining cohort
            activity_column: Column defining activity period
            
        Returns:
            Retention matrix
        """
        # Group by cohort and activity period
        cohort_data = user_activity.groupby([cohort_column, activity_column])['user_id'].nunique().reset_index()
        
        # Pivot to create retention matrix
        retention_matrix = cohort_data.pivot(
            index=cohort_column,
            columns=activity_column,
            values='user_id'
        )
        
        # Calculate retention percentages
        cohort_sizes = retention_matrix.iloc[:, 0]
        retention_pct = retention_matrix.divide(cohort_sizes, axis=0) * 100
        
        return retention_pct
    
    def calculate_lifetime_value(
        self,
        user_revenue: pd.DataFrame,
        cohort_column: str = 'signup_month'
    ) -> pd.DataFrame:
        """
        Calculate customer lifetime value by cohort
        
        Args:
            user_revenue: User revenue data
            cohort_column: Column defining cohort
            
        Returns:
            LTV by cohort
        """
        ltv = user_revenue.groupby(cohort_column).agg({
            'revenue': 'sum',
            'user_id': 'nunique'
        })
        
        ltv['avg_ltv'] = ltv['revenue'] / ltv['user_id']
        
        return ltv


class FunnelAnalyzer:
    """
    Funnel analysis for conversion tracking
    """
    
    def __init__(self):
        """Initialize funnel analyzer"""
        if not ANALYTICS_AVAILABLE:
            raise RuntimeError("Analytics libraries not available")
        
        logger.info("FunnelAnalyzer initialized")
    
    def analyze_funnel(
        self,
        events: pd.DataFrame,
        funnel_steps: List[str]
    ) -> Dict[str, Any]:
        """
        Analyze conversion funnel
        
        Args:
            events: Event data
            funnel_steps: Ordered list of funnel steps
            
        Returns:
            Funnel analysis results
        """
        funnel_data = []
        
        for i, step in enumerate(funnel_steps):
            step_users = events[events['event_type'] == step]['user_id'].nunique()
            
            if i == 0:
                conversion_rate = 100.0
                drop_off_rate = 0.0
            else:
                prev_users = funnel_data[i-1]['users']
                conversion_rate = (step_users / prev_users * 100) if prev_users > 0 else 0
                drop_off_rate = 100 - conversion_rate
            
            funnel_data.append({
                'step': step,
                'users': step_users,
                'conversion_rate': conversion_rate,
                'drop_off_rate': drop_off_rate
            })
        
        return {
            'funnel_steps': funnel_data,
            'overall_conversion': (funnel_data[-1]['users'] / funnel_data[0]['users'] * 100) if funnel_data else 0
        }


class DashboardEngine:
    """
    Dashboard engine for real-time metrics
    """
    
    def __init__(self, data_warehouse: DataWarehouse):
        """
        Initialize dashboard engine
        
        Args:
            data_warehouse: Data warehouse instance
        """
        self.data_warehouse = data_warehouse
        self.metrics: Dict[str, DashboardMetric] = {}
        self.cached_results: Dict[str, Any] = {}
        
        logger.info("DashboardEngine initialized")
    
    def register_metric(self, metric: DashboardMetric):
        """Register dashboard metric"""
        self.metrics[metric.metric_id] = metric
        logger.info(f"Registered metric: {metric.metric_id}")
    
    def compute_metric(self, metric_id: str) -> Any:
        """
        Compute metric value
        
        Args:
            metric_id: Metric identifier
            
        Returns:
            Metric value
        """
        if metric_id not in self.metrics:
            raise ValueError(f"Unknown metric: {metric_id}")
        
        metric = self.metrics[metric_id]
        
        # Check cache
        if metric_id in self.cached_results:
            cached_time, cached_value = self.cached_results[metric_id]
            if (datetime.now() - cached_time).total_seconds() < metric.refresh_interval:
                return cached_value
        
        # Compute metric (simplified)
        result = self._execute_metric_query(metric)
        
        # Cache result
        self.cached_results[metric_id] = (datetime.now(), result)
        
        return result
    
    def _execute_metric_query(self, metric: DashboardMetric) -> Any:
        """Execute metric query"""
        # Simplified query execution
        return {
            'value': 0,
            'trend': 'stable',
            'timestamp': datetime.now().isoformat()
        }
    
    def get_dashboard_snapshot(self, metric_ids: List[str]) -> Dict:
        """
        Get snapshot of multiple metrics
        
        Args:
            metric_ids: List of metric IDs
            
        Returns:
            Dashboard snapshot
        """
        snapshot = {}
        
        for metric_id in metric_ids:
            try:
                snapshot[metric_id] = self.compute_metric(metric_id)
            except Exception as e:
                logger.error(f"Error computing metric {metric_id}: {e}")
                snapshot[metric_id] = None
        
        return snapshot
