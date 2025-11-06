"""
Analytics Service Module

This service handles all analytics and reporting business logic, including:
- User analytics and engagement metrics
- Farm performance analytics
- Financial reporting and insights
- Trend analysis and forecasting
- Dashboard data aggregation
- KPI calculations
- Export functionality (CSV, PDF)
- Custom report generation
- Comparative analytics

Provides comprehensive business intelligence for decision-making.
"""

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, case, extract
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime, timedelta
from decimal import Decimal
from statistics import mean, median, stdev
import csv
from io import StringIO

from app.services.base import (
    BaseService,
    ValidationException,
    BusinessRuleException,
    ResourceNotFoundException,
    InsufficientPermissionsException
)
from app.repositories.user import UserRepository
from app.repositories.farm import FarmRepository
from app.repositories.base import BaseRepository
from app.models.database import (
    User, Farm, Field, Planting, Harvest,
    Chama, ChamaMember, Loan, LoanRepayment,
    Product, Order, OrderItem, SensorData,
    IoTDevice, Transaction
)


class AnalyticsService(BaseService):
    """
    Service class for analytics and reporting business logic.
    
    This service provides comprehensive analytics across all domains
    for business intelligence and decision-making.
    """
    
    def __init__(self, db: Session):
        """
        Initialize the analytics service.
        
        Args:
            db: SQLAlchemy database session
        """
        super().__init__(db)
        self.user_repo = UserRepository(db)
        self.farm_repo = FarmRepository(db)
    
    # ========================================================================
    # User Analytics
    # ========================================================================
    
    def get_user_analytics(
        self,
        user_id: int,
        period_days: int = 30
    ) -> Dict[str, Any]:
        """
        Get comprehensive analytics for a user.
        
        Args:
            user_id: ID of user
            period_days: Analysis period in days (default: 30)
            
        Returns:
            Dictionary with user analytics
            
        Raises:
            ResourceNotFoundException: If user not found
        """
        user = self.check_resource_exists(
            self.user_repo.get_by_id(user_id),
            "User",
            user_id
        )
        
        start_date = datetime.utcnow() - timedelta(days=period_days)
        
        # Account metrics
        account_age_days = self.calculate_days_between(user.created_at, datetime.utcnow())
        
        # Farm metrics
        farms = self.db.query(Farm).filter(Farm.owner_id == user_id).all()
        total_farms = len(farms)
        verified_farms = sum(1 for f in farms if f.is_verified)
        total_farm_size = sum(f.size_acres for f in farms)
        
        # Planting metrics
        planting_count = self.db.query(Planting).join(Field).join(Farm).filter(
            Farm.owner_id == user_id,
            Planting.planting_date >= start_date
        ).count()
        
        # Harvest metrics
        harvests = self.db.query(Harvest).join(Planting).join(Field).join(Farm).filter(
            Farm.owner_id == user_id,
            Harvest.harvest_date >= start_date
        ).all()
        
        total_harvest_quantity = sum(h.quantity for h in harvests)
        
        # Financial metrics
        chama_memberships = self.db.query(ChamaMember).filter(
            ChamaMember.user_id == user_id,
            ChamaMember.is_active == True
        ).count()
        
        # Product orders
        orders = self.db.query(Order).filter(
            Order.user_id == user_id,
            Order.created_at >= start_date
        ).all()
        
        total_orders = len(orders)
        total_order_value = sum(o.total_amount for o in orders)
        
        return {
            "user_id": user_id,
            "period_days": period_days,
            "account": {
                "account_age_days": account_age_days,
                "subscription_type": user.subscription_type,
                "is_verified": user.is_email_verified and user.is_phone_verified,
                "role": user.role
            },
            "farms": {
                "total_farms": total_farms,
                "verified_farms": verified_farms,
                "total_size_acres": float(total_farm_size),
                "average_size_acres": float(total_farm_size / total_farms) if total_farms > 0 else 0
            },
            "activity": {
                "plantings_period": planting_count,
                "harvests_period": len(harvests),
                "total_harvest_quantity": float(total_harvest_quantity)
            },
            "financial": {
                "chama_memberships": chama_memberships,
                "orders_period": total_orders,
                "order_value_period": float(total_order_value)
            }
        }
    
    def get_platform_metrics(
        self,
        admin_id: int,
        period_days: int = 30
    ) -> Dict[str, Any]:
        """
        Get platform-wide analytics (admin only).
        
        Args:
            admin_id: ID of admin user
            period_days: Analysis period in days
            
        Returns:
            Platform-wide metrics
            
        Raises:
            InsufficientPermissionsException: If not admin
        """
        admin = self.user_repo.get_by_id(admin_id)
        self.check_permission(admin.role, "admin")
        
        start_date = datetime.utcnow() - timedelta(days=period_days)
        
        # User metrics
        total_users = self.db.query(User).count()
        active_users = self.db.query(User).filter(User.is_active == True).count()
        new_users = self.db.query(User).filter(User.created_at >= start_date).count()
        
        # Subscription breakdown
        subscription_counts = self.db.query(
            User.subscription_type,
            func.count(User.id)
        ).group_by(User.subscription_type).all()
        
        # Farm metrics
        total_farms = self.db.query(Farm).count()
        verified_farms = self.db.query(Farm).filter(Farm.is_verified == True).count()
        total_farm_size = self.db.query(func.sum(Farm.size_acres)).scalar() or 0
        
        # Activity metrics
        plantings_period = self.db.query(Planting).filter(
            Planting.planting_date >= start_date
        ).count()
        
        harvests_period = self.db.query(Harvest).filter(
            Harvest.harvest_date >= start_date
        ).count()
        
        # Financial metrics
        total_chamas = self.db.query(Chama).count()
        active_loans = self.db.query(Loan).filter(
            Loan.status.in_(["approved", "active"])
        ).count()
        
        total_loan_amount = self.db.query(func.sum(Loan.principal_amount)).filter(
            Loan.status != "rejected"
        ).scalar() or 0
        
        # Marketplace metrics
        total_products = self.db.query(Product).count()
        active_products = self.db.query(Product).filter(Product.is_active == True).count()
        
        orders_period = self.db.query(Order).filter(
            Order.created_at >= start_date
        ).count()
        
        order_value_period = self.db.query(func.sum(Order.total_amount)).filter(
            Order.created_at >= start_date
        ).scalar() or 0
        
        # IoT metrics
        total_devices = self.db.query(IoTDevice).count()
        active_devices = self.db.query(IoTDevice).filter(
            IoTDevice.is_active == True
        ).count()
        
        sensor_readings_period = self.db.query(SensorData).filter(
            SensorData.timestamp >= start_date
        ).count()
        
        return {
            "period_days": period_days,
            "users": {
                "total": total_users,
                "active": active_users,
                "new_period": new_users,
                "subscriptions": {s[0]: s[1] for s in subscription_counts}
            },
            "farms": {
                "total": total_farms,
                "verified": verified_farms,
                "total_size_acres": float(total_farm_size),
                "verification_rate": self.calculate_percentage(verified_farms, total_farms)
            },
            "activity": {
                "plantings_period": plantings_period,
                "harvests_period": harvests_period
            },
            "financial": {
                "total_chamas": total_chamas,
                "active_loans": active_loans,
                "total_loan_amount": float(total_loan_amount)
            },
            "marketplace": {
                "total_products": total_products,
                "active_products": active_products,
                "orders_period": orders_period,
                "order_value_period": float(order_value_period)
            },
            "iot": {
                "total_devices": total_devices,
                "active_devices": active_devices,
                "sensor_readings_period": sensor_readings_period
            }
        }
    
    # ========================================================================
    # Farm Analytics
    # ========================================================================
    
    def get_farm_performance_analytics(
        self,
        farm_id: int,
        user_id: int,
        period_days: int = 90
    ) -> Dict[str, Any]:
        """
        Get comprehensive farm performance analytics.
        
        Args:
            farm_id: ID of farm
            user_id: ID of requesting user
            period_days: Analysis period in days
            
        Returns:
            Farm performance metrics
            
        Raises:
            ResourceNotFoundException: If farm not found
            InsufficientPermissionsException: If user doesn't own farm
        """
        farm = self.check_resource_exists(
            self.farm_repo.get_by_id(farm_id),
            "Farm",
            farm_id
        )
        
        self.check_ownership(farm.owner_id, user_id, "farm")
        
        start_date = datetime.utcnow() - timedelta(days=period_days)
        
        # Field utilization
        fields = self.db.query(Field).filter(Field.farm_id == farm_id).all()
        total_field_size = sum(f.size_acres for f in fields)
        field_utilization = self.calculate_percentage(total_field_size, farm.size_acres)
        
        # Planting analytics
        plantings = self.db.query(Planting).join(Field).filter(
            Field.farm_id == farm_id,
            Planting.planting_date >= start_date
        ).all()
        
        crop_diversity = len(set(p.crop_type for p in plantings))
        total_planted_area = sum(p.quantity for p in plantings)
        
        # Harvest analytics
        harvests = self.db.query(Harvest).join(Planting).join(Field).filter(
            Field.farm_id == farm_id,
            Harvest.harvest_date >= start_date
        ).all()
        
        if harvests:
            total_harvest = sum(h.quantity for h in harvests)
            avg_yield = mean([h.quantity / h.planting.quantity for h in harvests if h.planting.quantity > 0])
            avg_days_to_harvest = mean([
                self.calculate_days_between(h.planting.planting_date, h.harvest_date)
                for h in harvests
            ])
        else:
            total_harvest = 0
            avg_yield = 0
            avg_days_to_harvest = 0
        
        # Quality distribution
        quality_distribution = {}
        for harvest in harvests:
            quality = harvest.quality_grade or "ungraded"
            quality_distribution[quality] = quality_distribution.get(quality, 0) + 1
        
        # Growth stage tracking
        active_plantings = self.db.query(Planting).join(Field).filter(
            Field.farm_id == farm_id,
            Planting.status != "harvested"
        ).all()
        
        growth_stages = {}
        for planting in active_plantings:
            stage = planting.growth_stage
            growth_stages[stage] = growth_stages.get(stage, 0) + 1
        
        # IoT integration
        devices = self.db.query(IoTDevice).filter(IoTDevice.farm_id == farm_id).all()
        device_count = len(devices)
        active_device_count = sum(1 for d in devices if d.is_active)
        
        return {
            "farm_id": farm_id,
            "period_days": period_days,
            "utilization": {
                "total_farm_size": float(farm.size_acres),
                "total_field_size": float(total_field_size),
                "utilization_percentage": field_utilization,
                "total_fields": len(fields)
            },
            "planting": {
                "total_plantings": len(plantings),
                "crop_diversity": crop_diversity,
                "total_planted_area": float(total_planted_area),
                "active_plantings": len(active_plantings),
                "growth_stages": growth_stages
            },
            "harvest": {
                "total_harvests": len(harvests),
                "total_quantity": float(total_harvest),
                "average_yield_per_acre": float(avg_yield),
                "average_days_to_harvest": float(avg_days_to_harvest),
                "quality_distribution": quality_distribution
            },
            "technology": {
                "iot_devices": device_count,
                "active_devices": active_device_count
            }
        }
    
    def compare_farm_performance(
        self,
        farm_id: int,
        user_id: int,
        county: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Compare farm performance against averages.
        
        Args:
            farm_id: ID of farm
            user_id: ID of requesting user
            county: Compare within county (optional)
            
        Returns:
            Comparative analytics
        """
        farm = self.check_resource_exists(
            self.farm_repo.get_by_id(farm_id),
            "Farm",
            farm_id
        )
        
        self.check_ownership(farm.owner_id, user_id, "farm")
        
        # Get farm metrics
        farm_metrics = self.get_farm_performance_analytics(farm_id, user_id, 90)
        
        # Build comparison query
        comparison_query = self.db.query(Farm)
        if county:
            comparison_query = comparison_query.filter(Farm.county == county)
        else:
            comparison_query = comparison_query.filter(Farm.county == farm.county)
        
        comparison_farms = comparison_query.all()
        
        # Calculate averages
        if len(comparison_farms) > 1:
            avg_farm_size = mean([f.size_acres for f in comparison_farms])
            
            # Get harvest data for comparison
            comparison_harvests = []
            for comp_farm in comparison_farms:
                harvests = self.db.query(Harvest).join(Planting).join(Field).filter(
                    Field.farm_id == comp_farm.id
                ).all()
                comparison_harvests.extend(harvests)
            
            if comparison_harvests:
                avg_yield = mean([
                    h.quantity / h.planting.quantity 
                    for h in comparison_harvests 
                    if h.planting.quantity > 0
                ])
            else:
                avg_yield = 0
        else:
            avg_farm_size = farm.size_acres
            avg_yield = 0
        
        return {
            "farm_id": farm_id,
            "comparison_scope": county or farm.county,
            "total_farms_compared": len(comparison_farms),
            "farm_metrics": {
                "size_acres": float(farm.size_acres),
                "yield_per_acre": farm_metrics["harvest"]["average_yield_per_acre"]
            },
            "average_metrics": {
                "size_acres": float(avg_farm_size),
                "yield_per_acre": float(avg_yield)
            },
            "performance": {
                "size_vs_average": self.calculate_percentage(
                    farm.size_acres - avg_farm_size,
                    avg_farm_size
                ) if avg_farm_size > 0 else 0,
                "yield_vs_average": self.calculate_percentage(
                    farm_metrics["harvest"]["average_yield_per_acre"] - avg_yield,
                    avg_yield
                ) if avg_yield > 0 else 0
            }
        }
    
    # ========================================================================
    # Financial Analytics
    # ========================================================================
    
    def get_chama_financial_analytics(
        self,
        chama_id: int,
        user_id: int,
        period_days: int = 90
    ) -> Dict[str, Any]:
        """
        Get comprehensive chama financial analytics.
        
        Args:
            chama_id: ID of chama
            user_id: ID of requesting user
            period_days: Analysis period in days
            
        Returns:
            Financial analytics
        """
        chama = self.check_resource_exists(
            self.db.query(Chama).filter(Chama.id == chama_id).first(),
            "Chama",
            chama_id
        )
        
        # Verify user is member
        member = self.db.query(ChamaMember).filter(
            ChamaMember.chama_id == chama_id,
            ChamaMember.user_id == user_id,
            ChamaMember.is_active == True
        ).first()
        
        if not member:
            raise InsufficientPermissionsException("You are not a member of this chama")
        
        start_date = datetime.utcnow() - timedelta(days=period_days)
        
        # Member analytics
        total_members = self.db.query(ChamaMember).filter(
            ChamaMember.chama_id == chama_id,
            ChamaMember.is_active == True
        ).count()
        
        # Loan analytics
        all_loans = self.db.query(Loan).filter(Loan.chama_id == chama_id).all()
        active_loans = [l for l in all_loans if l.status in ["approved", "active"]]
        paid_loans = [l for l in all_loans if l.status == "paid"]
        defaulted_loans = [l for l in all_loans if l.status == "defaulted"]
        
        total_disbursed = sum(l.principal_amount for l in all_loans if l.status != "rejected")
        total_repaid = sum(l.amount_repaid for l in all_loans)
        outstanding_principal = sum(l.principal_amount - l.amount_repaid for l in active_loans)
        
        # Interest calculations
        total_interest_expected = sum(l.interest_amount for l in all_loans if l.status != "rejected")
        total_interest_paid = sum(
            (l.amount_repaid - l.principal_amount) for l in all_loans 
            if l.amount_repaid > l.principal_amount
        )
        
        # Repayment rate
        if paid_loans:
            repayment_rate = self.calculate_percentage(len(paid_loans), len(all_loans))
        else:
            repayment_rate = 0
        
        # Default rate
        default_rate = self.calculate_percentage(len(defaulted_loans), len(all_loans))
        
        # Transaction analytics
        transactions = self.db.query(Transaction).filter(
            Transaction.chama_id == chama_id,
            Transaction.created_at >= start_date
        ).all()
        
        transaction_count = len(transactions)
        transaction_volume = sum(t.amount for t in transactions)
        
        return {
            "chama_id": chama_id,
            "period_days": period_days,
            "membership": {
                "total_members": total_members,
                "max_members": chama.max_members,
                "capacity_utilization": self.calculate_percentage(
                    total_members,
                    chama.max_members
                ) if chama.max_members else 100
            },
            "financial_position": {
                "current_balance": float(chama.balance),
                "total_disbursed": float(total_disbursed),
                "total_repaid": float(total_repaid),
                "outstanding_principal": float(outstanding_principal)
            },
            "loan_portfolio": {
                "total_loans": len(all_loans),
                "active_loans": len(active_loans),
                "paid_loans": len(paid_loans),
                "defaulted_loans": len(defaulted_loans),
                "repayment_rate": repayment_rate,
                "default_rate": default_rate
            },
            "interest": {
                "total_expected": float(total_interest_expected),
                "total_paid": float(total_interest_paid),
                "interest_earned_rate": self.calculate_percentage(
                    total_interest_paid,
                    total_interest_expected
                ) if total_interest_expected > 0 else 0
            },
            "transactions": {
                "count_period": transaction_count,
                "volume_period": float(transaction_volume)
            }
        }
    
    def get_marketplace_analytics(
        self,
        user_id: int,
        supplier_id: Optional[int] = None,
        period_days: int = 30
    ) -> Dict[str, Any]:
        """
        Get marketplace analytics.
        
        Args:
            user_id: ID of requesting user
            supplier_id: Filter by supplier (optional)
            period_days: Analysis period in days
            
        Returns:
            Marketplace analytics
        """
        start_date = datetime.utcnow() - timedelta(days=period_days)
        
        # Product analytics
        product_query = self.db.query(Product)
        if supplier_id:
            product_query = product_query.filter(Product.supplier_id == supplier_id)
        
        products = product_query.all()
        active_products = [p for p in products if p.is_active]
        
        total_stock_value = sum(p.price * p.stock_quantity for p in active_products)
        low_stock_products = [p for p in active_products if p.stock_quantity < p.min_order_quantity]
        
        # Order analytics
        order_query = self.db.query(Order).filter(Order.created_at >= start_date)
        if supplier_id:
            order_query = order_query.join(OrderItem).join(Product).filter(
                Product.supplier_id == supplier_id
            )
        
        orders = order_query.all()
        total_orders = len(orders)
        total_revenue = sum(o.total_amount for o in orders)
        
        # Order status distribution
        status_distribution = {}
        for order in orders:
            status = order.status
            status_distribution[status] = status_distribution.get(status, 0) + 1
        
        # Top products
        top_products_query = self.db.query(
            Product.name,
            func.sum(OrderItem.quantity).label('total_sold'),
            func.sum(OrderItem.total_price).label('total_revenue')
        ).join(OrderItem).filter(
            Order.created_at >= start_date
        ).group_by(Product.name).order_by(
            func.sum(OrderItem.quantity).desc()
        ).limit(10)
        
        if supplier_id:
            top_products_query = top_products_query.filter(Product.supplier_id == supplier_id)
        
        top_products = top_products_query.all()
        
        return {
            "period_days": period_days,
            "supplier_id": supplier_id,
            "products": {
                "total_products": len(products),
                "active_products": len(active_products),
                "total_stock_value": float(total_stock_value),
                "low_stock_count": len(low_stock_products)
            },
            "orders": {
                "total_orders": total_orders,
                "total_revenue": float(total_revenue),
                "average_order_value": float(total_revenue / total_orders) if total_orders > 0 else 0,
                "status_distribution": status_distribution
            },
            "top_products": [
                {
                    "name": p[0],
                    "total_sold": p[1],
                    "revenue": float(p[2])
                }
                for p in top_products
            ]
        }
    
    # ========================================================================
    # Trend Analysis
    # ========================================================================
    
    def get_trend_analysis(
        self,
        metric_type: str,
        entity_id: Optional[int] = None,
        period_days: int = 90,
        interval: str = "daily"
    ) -> Dict[str, Any]:
        """
        Get trend analysis for various metrics.
        
        Args:
            metric_type: Type of metric (users, orders, harvests, loans)
            entity_id: Optional entity ID for filtering
            period_days: Analysis period in days
            interval: Aggregation interval (daily, weekly, monthly)
            
        Returns:
            Trend data with time series
        """
        start_date = datetime.utcnow() - timedelta(days=period_days)
        
        if metric_type == "users":
            data = self._get_user_trends(start_date, interval)
        elif metric_type == "orders":
            data = self._get_order_trends(start_date, interval, entity_id)
        elif metric_type == "harvests":
            data = self._get_harvest_trends(start_date, interval, entity_id)
        elif metric_type == "loans":
            data = self._get_loan_trends(start_date, interval, entity_id)
        else:
            raise ValidationException(f"Invalid metric type: {metric_type}")
        
        return {
            "metric_type": metric_type,
            "period_days": period_days,
            "interval": interval,
            "data": data
        }
    
    def _get_user_trends(self, start_date: datetime, interval: str) -> List[Dict]:
        """Get user registration trends."""
        query = self.db.query(
            func.date(User.created_at).label('date'),
            func.count(User.id).label('count')
        ).filter(
            User.created_at >= start_date
        ).group_by(func.date(User.created_at)).order_by('date')
        
        results = query.all()
        return [{"date": r[0].isoformat(), "count": r[1]} for r in results]
    
    def _get_order_trends(
        self,
        start_date: datetime,
        interval: str,
        supplier_id: Optional[int]
    ) -> List[Dict]:
        """Get order trends."""
        query = self.db.query(
            func.date(Order.created_at).label('date'),
            func.count(Order.id).label('count'),
            func.sum(Order.total_amount).label('revenue')
        ).filter(
            Order.created_at >= start_date
        )
        
        if supplier_id:
            query = query.join(OrderItem).join(Product).filter(
                Product.supplier_id == supplier_id
            )
        
        query = query.group_by(func.date(Order.created_at)).order_by('date')
        
        results = query.all()
        return [
            {
                "date": r[0].isoformat(),
                "count": r[1],
                "revenue": float(r[2] or 0)
            }
            for r in results
        ]
    
    def _get_harvest_trends(
        self,
        start_date: datetime,
        interval: str,
        farm_id: Optional[int]
    ) -> List[Dict]:
        """Get harvest trends."""
        query = self.db.query(
            func.date(Harvest.harvest_date).label('date'),
            func.count(Harvest.id).label('count'),
            func.sum(Harvest.quantity).label('quantity')
        ).filter(
            Harvest.harvest_date >= start_date
        )
        
        if farm_id:
            query = query.join(Planting).join(Field).filter(Field.farm_id == farm_id)
        
        query = query.group_by(func.date(Harvest.harvest_date)).order_by('date')
        
        results = query.all()
        return [
            {
                "date": r[0].isoformat(),
                "count": r[1],
                "quantity": float(r[2] or 0)
            }
            for r in results
        ]
    
    def _get_loan_trends(
        self,
        start_date: datetime,
        interval: str,
        chama_id: Optional[int]
    ) -> List[Dict]:
        """Get loan disbursement trends."""
        query = self.db.query(
            func.date(Loan.created_at).label('date'),
            func.count(Loan.id).label('count'),
            func.sum(Loan.principal_amount).label('amount')
        ).filter(
            Loan.created_at >= start_date,
            Loan.status != "rejected"
        )
        
        if chama_id:
            query = query.filter(Loan.chama_id == chama_id)
        
        query = query.group_by(func.date(Loan.created_at)).order_by('date')
        
        results = query.all()
        return [
            {
                "date": r[0].isoformat(),
                "count": r[1],
                "amount": float(r[2] or 0)
            }
            for r in results
        ]
    
    # ========================================================================
    # Export Functionality
    # ========================================================================
    
    def export_analytics_csv(
        self,
        analytics_type: str,
        data: Dict[str, Any]
    ) -> str:
        """
        Export analytics data to CSV format.
        
        Args:
            analytics_type: Type of analytics
            data: Analytics data dictionary
            
        Returns:
            CSV string
        """
        output = StringIO()
        writer = csv.writer(output)
        
        # Write header
        writer.writerow([f"{analytics_type.upper()} Analytics Report"])
        writer.writerow(["Generated:", datetime.utcnow().isoformat()])
        writer.writerow([])
        
        # Write data based on type
        if analytics_type == "farm_performance":
            self._write_farm_csv(writer, data)
        elif analytics_type == "financial":
            self._write_financial_csv(writer, data)
        elif analytics_type == "marketplace":
            self._write_marketplace_csv(writer, data)
        
        return output.getvalue()
    
    def _write_farm_csv(self, writer, data: Dict):
        """Write farm analytics to CSV."""
        writer.writerow(["Utilization Metrics"])
        writer.writerow(["Total Farm Size", data["utilization"]["total_farm_size"]])
        writer.writerow(["Field Utilization %", data["utilization"]["utilization_percentage"]])
        writer.writerow([])
        
        writer.writerow(["Harvest Metrics"])
        writer.writerow(["Total Harvests", data["harvest"]["total_harvests"]])
        writer.writerow(["Total Quantity", data["harvest"]["total_quantity"]])
        writer.writerow(["Avg Yield/Acre", data["harvest"]["average_yield_per_acre"]])
    
    def _write_financial_csv(self, writer, data: Dict):
        """Write financial analytics to CSV."""
        writer.writerow(["Financial Position"])
        writer.writerow(["Current Balance", data["financial_position"]["current_balance"]])
        writer.writerow(["Total Disbursed", data["financial_position"]["total_disbursed"]])
        writer.writerow(["Total Repaid", data["financial_position"]["total_repaid"]])
        writer.writerow([])
        
        writer.writerow(["Loan Portfolio"])
        writer.writerow(["Total Loans", data["loan_portfolio"]["total_loans"]])
        writer.writerow(["Repayment Rate %", data["loan_portfolio"]["repayment_rate"]])
        writer.writerow(["Default Rate %", data["loan_portfolio"]["default_rate"]])
    
    def _write_marketplace_csv(self, writer, data: Dict):
        """Write marketplace analytics to CSV."""
        writer.writerow(["Products"])
        writer.writerow(["Total Products", data["products"]["total_products"]])
        writer.writerow(["Active Products", data["products"]["active_products"]])
        writer.writerow([])
        
        writer.writerow(["Orders"])
        writer.writerow(["Total Orders", data["orders"]["total_orders"]])
        writer.writerow(["Total Revenue", data["orders"]["total_revenue"]])
        writer.writerow(["Avg Order Value", data["orders"]["average_order_value"]])
