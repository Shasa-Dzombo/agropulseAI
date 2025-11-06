"""
Reports and Analytics API Tests

Tests for reporting, analytics, dashboards, and data export endpoints.
"""

import pytest
from datetime import datetime, timedelta
from fastapi import status

from tests.utils import (
    assert_status_code, get_json_response, assert_dict_structure
)


@pytest.mark.api
@pytest.mark.integration
class TestReportsAPI:
    """Test report generation endpoints."""
    
    def test_get_farm_report(self, authenticated_client, test_farm):
        """Test getting farm report."""
        response = authenticated_client.get(
            f"/api/v1/reports/farm/{test_farm.id}"
        )
        
        assert_status_code(response, status.HTTP_200_OK)
        data = get_json_response(response)
        assert_dict_structure(data, [
            "farm_id", "summary", "fields", "crops"
        ])
    
    def test_get_crop_performance_report(self, authenticated_client, test_crop):
        """Test crop performance report."""
        response = authenticated_client.get(
            f"/api/v1/reports/crop/{test_crop.id}/performance"
        )
        
        assert_status_code(response, status.HTTP_200_OK)
        data = get_json_response(response)
        assert "growth_metrics" in data
    
    def test_get_yield_report(self, authenticated_client, test_farm):
        """Test yield report."""
        start_date = (datetime.utcnow() - timedelta(days=90)).isoformat()
        end_date = datetime.utcnow().isoformat()
        
        response = authenticated_client.get(
            f"/api/v1/reports/farm/{test_farm.id}/yield",
            params={"start_date": start_date, "end_date": end_date}
        )
        
        assert_status_code(response, status.HTTP_200_OK)
        data = get_json_response(response)
        assert isinstance(data, dict)
    
    def test_get_financial_report(self, authenticated_client, test_farm):
        """Test financial report."""
        response = authenticated_client.get(
            f"/api/v1/reports/farm/{test_farm.id}/financial"
        )
        
        assert_status_code(response, status.HTTP_200_OK)
        data = get_json_response(response)
        assert_dict_structure(data, [
            "total_revenue", "total_expenses", "profit"
        ])
    
    def test_get_expense_breakdown(self, authenticated_client, test_farm):
        """Test expense breakdown report."""
        response = authenticated_client.get(
            f"/api/v1/reports/farm/{test_farm.id}/expenses"
        )
        
        assert_status_code(response, status.HTTP_200_OK)
        data = get_json_response(response)
        assert isinstance(data, dict)
    
    def test_get_soil_health_report(self, authenticated_client, test_field):
        """Test soil health report."""
        response = authenticated_client.get(
            f"/api/v1/reports/field/{test_field.id}/soil-health"
        )
        
        assert_status_code(response, status.HTTP_200_OK)
        data = get_json_response(response)
        assert "soil_metrics" in data
    
    def test_get_water_usage_report(self, authenticated_client, test_farm):
        """Test water usage report."""
        response = authenticated_client.get(
            f"/api/v1/reports/farm/{test_farm.id}/water-usage"
        )
        
        assert_status_code(response, status.HTTP_200_OK)
    
    def test_get_pest_disease_report(self, authenticated_client, test_farm):
        """Test pest and disease report."""
        response = authenticated_client.get(
            f"/api/v1/reports/farm/{test_farm.id}/pests-diseases"
        )
        
        assert_status_code(response, status.HTTP_200_OK)
        data = get_json_response(response)
        assert isinstance(data, dict)
    
    def test_export_report_pdf(self, authenticated_client, test_farm):
        """Test exporting report as PDF."""
        response = authenticated_client.get(
            f"/api/v1/reports/farm/{test_farm.id}/export",
            params={"format": "pdf"}
        )
        
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_501_NOT_IMPLEMENTED
        ]
        
        if response.status_code == status.HTTP_200_OK:
            assert response.headers["content-type"] == "application/pdf"
    
    def test_export_report_csv(self, authenticated_client, test_farm):
        """Test exporting report as CSV."""
        response = authenticated_client.get(
            f"/api/v1/reports/farm/{test_farm.id}/export",
            params={"format": "csv"}
        )
        
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_501_NOT_IMPLEMENTED
        ]
    
    def test_export_report_excel(self, authenticated_client, test_farm):
        """Test exporting report as Excel."""
        response = authenticated_client.get(
            f"/api/v1/reports/farm/{test_farm.id}/export",
            params={"format": "xlsx"}
        )
        
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_501_NOT_IMPLEMENTED
        ]
    
    def test_schedule_report(self, authenticated_client, test_farm):
        """Test scheduling recurring report."""
        schedule_data = {
            "report_type": "financial",
            "frequency": "weekly",
            "recipients": ["user@example.com"]
        }
        
        response = authenticated_client.post(
            f"/api/v1/reports/farm/{test_farm.id}/schedule",
            json=schedule_data
        )
        
        assert response.status_code in [
            status.HTTP_201_CREATED,
            status.HTTP_501_NOT_IMPLEMENTED
        ]


@pytest.mark.api
@pytest.mark.integration
class TestAnalyticsAPI:
    """Test analytics and insights endpoints."""
    
    def test_get_dashboard_summary(self, authenticated_client, test_user):
        """Test getting dashboard summary."""
        response = authenticated_client.get("/api/v1/analytics/dashboard")
        
        assert_status_code(response, status.HTTP_200_OK)
        data = get_json_response(response)
        assert_dict_structure(data, [
            "farms_count", "fields_count", "crops_count"
        ])
    
    def test_get_farm_analytics(self, authenticated_client, test_farm):
        """Test farm analytics."""
        response = authenticated_client.get(
            f"/api/v1/analytics/farm/{test_farm.id}"
        )
        
        assert_status_code(response, status.HTTP_200_OK)
        data = get_json_response(response)
        assert isinstance(data, dict)
    
    def test_get_crop_trends(self, authenticated_client, test_farm):
        """Test crop trends analysis."""
        response = authenticated_client.get(
            f"/api/v1/analytics/farm/{test_farm.id}/crop-trends"
        )
        
        assert_status_code(response, status.HTTP_200_OK)
        data = get_json_response(response)
        assert isinstance(data, list) or isinstance(data, dict)
    
    def test_get_yield_trends(self, authenticated_client, test_farm):
        """Test yield trends over time."""
        response = authenticated_client.get(
            f"/api/v1/analytics/farm/{test_farm.id}/yield-trends"
        )
        
        assert_status_code(response, status.HTTP_200_OK)
    
    def test_get_financial_trends(self, authenticated_client, test_farm):
        """Test financial trends."""
        response = authenticated_client.get(
            f"/api/v1/analytics/farm/{test_farm.id}/financial-trends"
        )
        
        assert_status_code(response, status.HTTP_200_OK)
        data = get_json_response(response)
        assert isinstance(data, dict)
    
    def test_get_weather_patterns(self, authenticated_client, test_farm):
        """Test weather patterns analysis."""
        response = authenticated_client.get(
            f"/api/v1/analytics/farm/{test_farm.id}/weather-patterns"
        )
        
        assert_status_code(response, status.HTTP_200_OK)
    
    def test_get_sensor_analytics(self, authenticated_client, test_sensor):
        """Test sensor data analytics."""
        response = authenticated_client.get(
            f"/api/v1/analytics/sensor/{test_sensor.id}"
        )
        
        assert_status_code(response, status.HTTP_200_OK)
        data = get_json_response(response)
        assert_dict_structure(data, ["min", "max", "average"])
    
    def test_get_performance_metrics(self, authenticated_client, test_farm):
        """Test farm performance metrics."""
        response = authenticated_client.get(
            f"/api/v1/analytics/farm/{test_farm.id}/performance"
        )
        
        assert_status_code(response, status.HTTP_200_OK)
        data = get_json_response(response)
        assert isinstance(data, dict)
    
    def test_compare_farms(self, authenticated_client, test_farm, test_user, db_session):
        """Test comparing multiple farms."""
        # Create another farm
        from app.database.models.farm import Farm
        farm2 = Farm(
            name="Farm 2",
            owner_id=test_user.id,
            location="Test"
        )
        db_session.add(farm2)
        db_session.commit()
        
        response = authenticated_client.get(
            "/api/v1/analytics/compare",
            params={"farm_ids": f"{test_farm.id},{farm2.id}"}
        )
        
        assert_status_code(response, status.HTTP_200_OK)
    
    def test_get_recommendations(self, authenticated_client, test_farm):
        """Test getting AI recommendations."""
        response = authenticated_client.get(
            f"/api/v1/analytics/farm/{test_farm.id}/recommendations"
        )
        
        assert_status_code(response, status.HTTP_200_OK)
        data = get_json_response(response)
        assert isinstance(data, list) or isinstance(data, dict)


@pytest.mark.api
@pytest.mark.integration
class TestDataExportAPI:
    """Test data export endpoints."""
    
    def test_export_farm_data(self, authenticated_client, test_farm):
        """Test exporting all farm data."""
        response = authenticated_client.get(
            f"/api/v1/export/farm/{test_farm.id}",
            params={"format": "json"}
        )
        
        assert_status_code(response, status.HTTP_200_OK)
    
    def test_export_sensor_data(self, authenticated_client, test_sensor):
        """Test exporting sensor data."""
        response = authenticated_client.get(
            f"/api/v1/export/sensor/{test_sensor.id}",
            params={
                "start_date": (datetime.utcnow() - timedelta(days=7)).isoformat(),
                "end_date": datetime.utcnow().isoformat(),
                "format": "csv"
            }
        )
        
        assert_status_code(response, status.HTTP_200_OK)
    
    def test_export_crop_history(self, authenticated_client, test_field):
        """Test exporting crop history."""
        response = authenticated_client.get(
            f"/api/v1/export/field/{test_field.id}/crop-history",
            params={"format": "csv"}
        )
        
        assert_status_code(response, status.HTTP_200_OK)
    
    def test_bulk_export(self, authenticated_client):
        """Test bulk data export."""
        response = authenticated_client.post(
            "/api/v1/export/bulk",
            json={
                "include": ["farms", "fields", "crops", "sensors"],
                "format": "zip"
            }
        )
        
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_202_ACCEPTED
        ]
    
    def test_export_with_date_range(self, authenticated_client, test_farm):
        """Test export with specific date range."""
        start = (datetime.utcnow() - timedelta(days=30)).isoformat()
        end = datetime.utcnow().isoformat()
        
        response = authenticated_client.get(
            f"/api/v1/export/farm/{test_farm.id}",
            params={
                "start_date": start,
                "end_date": end,
                "format": "json"
            }
        )
        
        assert_status_code(response, status.HTTP_200_OK)


@pytest.mark.api
@pytest.mark.integration
class TestStatisticsAPI:
    """Test statistics endpoints."""
    
    def test_get_user_statistics(self, authenticated_client):
        """Test user statistics."""
        response = authenticated_client.get("/api/v1/statistics/user")
        
        assert_status_code(response, status.HTTP_200_OK)
        data = get_json_response(response)
        assert_dict_structure(data, [
            "total_farms", "total_fields", "total_crops"
        ])
    
    def test_get_farm_statistics(self, authenticated_client, test_farm):
        """Test farm statistics."""
        response = authenticated_client.get(
            f"/api/v1/statistics/farm/{test_farm.id}"
        )
        
        assert_status_code(response, status.HTTP_200_OK)
        data = get_json_response(response)
        assert isinstance(data, dict)
    
    def test_get_crop_statistics(self, authenticated_client, test_farm):
        """Test crop statistics."""
        response = authenticated_client.get(
            f"/api/v1/statistics/farm/{test_farm.id}/crops"
        )
        
        assert_status_code(response, status.HTTP_200_OK)
    
    def test_get_sensor_statistics(self, authenticated_client, test_farm):
        """Test sensor statistics."""
        response = authenticated_client.get(
            f"/api/v1/statistics/farm/{test_farm.id}/sensors"
        )
        
        assert_status_code(response, status.HTTP_200_OK)
    
    def test_get_alert_statistics(self, authenticated_client):
        """Test alert statistics."""
        response = authenticated_client.get("/api/v1/statistics/alerts")
        
        assert_status_code(response, status.HTTP_200_OK)
        data = get_json_response(response)
        assert isinstance(data, dict)
    
    def test_get_system_statistics(self, authenticated_client):
        """Test system-wide statistics (admin only)."""
        response = authenticated_client.get("/api/v1/statistics/system")
        
        # May require admin privileges
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_403_FORBIDDEN
        ]


@pytest.mark.api
@pytest.mark.integration
class TestVisualizationAPI:
    """Test data visualization endpoints."""
    
    def test_get_growth_chart_data(self, authenticated_client, test_crop):
        """Test crop growth chart data."""
        response = authenticated_client.get(
            f"/api/v1/visualizations/crop/{test_crop.id}/growth-chart"
        )
        
        assert_status_code(response, status.HTTP_200_OK)
        data = get_json_response(response)
        assert "labels" in data
        assert "datasets" in data
    
    def test_get_yield_chart_data(self, authenticated_client, test_farm):
        """Test yield chart data."""
        response = authenticated_client.get(
            f"/api/v1/visualizations/farm/{test_farm.id}/yield-chart"
        )
        
        assert_status_code(response, status.HTTP_200_OK)
    
    def test_get_financial_chart_data(self, authenticated_client, test_farm):
        """Test financial chart data."""
        response = authenticated_client.get(
            f"/api/v1/visualizations/farm/{test_farm.id}/financial-chart"
        )
        
        assert_status_code(response, status.HTTP_200_OK)
    
    def test_get_sensor_heatmap_data(self, authenticated_client, test_farm):
        """Test sensor heatmap data."""
        response = authenticated_client.get(
            f"/api/v1/visualizations/farm/{test_farm.id}/sensor-heatmap"
        )
        
        assert_status_code(response, status.HTTP_200_OK)
    
    def test_get_weather_chart_data(self, authenticated_client, test_farm):
        """Test weather chart data."""
        response = authenticated_client.get(
            f"/api/v1/visualizations/farm/{test_farm.id}/weather-chart"
        )
        
        assert_status_code(response, status.HTTP_200_OK)
