"""
Farm Service Module

This service handles all business logic related to farm management, including:
- Farm registration and verification
- Field management and crop planning
- Planting workflows and tracking
- Harvest tracking and yield calculations
- Farm analytics and reporting
- Geographic queries and proximity searches
- Weather integration
- Crop recommendations

The service implements complex agricultural business rules and coordinates
with multiple repositories.
"""

from sqlalchemy.orm import Session
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime, timedelta
from decimal import Decimal
from geoalchemy2.elements import WKTElement

from app.services.base import (
    BaseService,
    ValidationException,
    BusinessRuleException,
    ResourceNotFoundException,
    InsufficientPermissionsException
)
from app.repositories.farm import FarmRepository
from app.repositories.user import UserRepository
from app.models.database import Farm, Field, CropPlanting, Harvest, CropType, GrowthStage


class FarmService(BaseService):
    """
    Service class for farm-related business logic.
    
    This service provides high-level operations for farm management,
    implementing agricultural business rules and best practices.
    """
    
    def __init__(self, db: Session):
        """
        Initialize the farm service.
        
        Args:
            db: SQLAlchemy database session
        """
        super().__init__(db)
        self.farm_repo = FarmRepository(db)
        self.user_repo = UserRepository(db)
    
    # ========================================================================
    # Farm Registration and Management
    # ========================================================================
    
    def register_farm(
        self,
        owner_id: int,
        name: str,
        size: float,
        latitude: float,
        longitude: float,
        county: Optional[str] = None,
        description: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Register a new farm with complete validation.
        
        Business Rules:
        - Size must be positive and realistic (0.1 - 10000 acres)
        - Coordinates must be valid (within Kenya bounds)
        - Name must be unique for the owner
        - Owner must exist and be active
        
        Args:
            owner_id: ID of farm owner
            name: Farm name
            size: Farm size in acres
            latitude: Farm latitude
            longitude: Farm longitude
            county: County location (optional)
            description: Farm description (optional)
            
        Returns:
            Dictionary with farm information
            
        Raises:
            ValidationException: If validation fails
            ResourceNotFoundException: If owner not found
        """
        with self.transaction():
            # Validate owner exists
            owner = self.check_resource_exists(
                self.user_repo.get_by_id(owner_id),
                "User",
                owner_id
            )
            
            if not owner.is_active:
                raise BusinessRuleException(
                    "Cannot register farm for inactive user",
                    rule="active_user_required"
                )
            
            # Validate farm details
            self.validate_farm_size(size)
            self.validate_coordinates(latitude, longitude)
            self.validate_string_length(name, 2, 100, "name")
            
            # Check name uniqueness for owner
            existing_farms = self.farm_repo.get_by_owner(owner_id)
            if any(f.name.lower() == name.lower() for f in existing_farms):
                raise ValidationException(
                    "Farm name already exists for this owner",
                    field="name"
                )
            
            # Create farm
            farm_data = {
                "owner_id": owner_id,
                "name": name,
                "size": size,
                "latitude": latitude,
                "longitude": longitude,
                "county": county,
                "description": description,
                "verified": False
            }
            
            farm = self.farm_repo.create(farm_data)
            
            self.log_activity("farm_registered", owner_id, {
                "farm_id": farm.id,
                "name": name,
                "size": size
            })
            
            return self._format_farm_response(farm)
    
    def validate_farm_size(self, size: float):
        """
        Validate farm size is realistic.
        
        Args:
            size: Farm size in acres
            
        Raises:
            ValidationException: If size is invalid
        """
        self.validate_positive(size, "size")
        
        if size < 0.1:
            raise ValidationException(
                "Farm size must be at least 0.1 acres",
                field="size"
            )
        
        if size > 10000:
            raise ValidationException(
                "Farm size exceeds maximum (10,000 acres). Please contact support for large farms.",
                field="size"
            )
    
    def validate_coordinates(self, latitude: float, longitude: float):
        """
        Validate coordinates are within Kenya bounds.
        
        Kenya bounds approximately:
        Latitude: -4.68 to 5.03
        Longitude: 33.91 to 41.91
        
        Args:
            latitude: Latitude coordinate
            longitude: Longitude coordinate
            
        Raises:
            ValidationException: If coordinates are invalid
        """
        if not (-4.68 <= latitude <= 5.03):
            raise ValidationException(
                "Latitude must be within Kenya bounds (-4.68 to 5.03)",
                field="latitude"
            )
        
        if not (33.91 <= longitude <= 41.91):
            raise ValidationException(
                "Longitude must be within Kenya bounds (33.91 to 41.91)",
                field="longitude"
            )
    
    def update_farm(
        self,
        farm_id: int,
        user_id: int,
        name: Optional[str] = None,
        size: Optional[float] = None,
        county: Optional[str] = None,
        description: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Update farm details.
        
        Args:
            farm_id: ID of farm to update
            user_id: ID of user performing update
            name: New farm name (optional)
            size: New farm size (optional)
            county: New county (optional)
            description: New description (optional)
            
        Returns:
            Updated farm information
            
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
        
        update_data = {}
        
        if name is not None:
            self.validate_string_length(name, 2, 100, "name")
            update_data["name"] = name
        
        if size is not None:
            self.validate_farm_size(size)
            update_data["size"] = size
        
        if county is not None:
            update_data["county"] = county
        
        if description is not None:
            update_data["description"] = description
        
        updated_farm = self.farm_repo.update(farm, **update_data)
        
        self.log_activity("farm_updated", user_id, {
            "farm_id": farm_id,
            "updates": update_data
        })
        
        return self._format_farm_response(updated_farm)
    
    def verify_farm(self, farm_id: int, verifier_id: int) -> Dict[str, Any]:
        """
        Verify a farm (admin/agronomist only).
        
        Business Rules:
        - Only admin or agronomist can verify
        - Farm must have complete information
        - Verification is permanent
        
        Args:
            farm_id: ID of farm to verify
            verifier_id: ID of user performing verification
            
        Returns:
            Updated farm information
            
        Raises:
            ResourceNotFoundException: If farm not found
            InsufficientPermissionsException: If user lacks permission
        """
        verifier = self.user_repo.get_by_id(verifier_id)
        if verifier.role not in ["admin", "agronomist"]:
            raise InsufficientPermissionsException(
                "Only admins and agronomists can verify farms"
            )
        
        farm = self.check_resource_exists(
            self.farm_repo.get_by_id(farm_id),
            "Farm",
            farm_id
        )
        
        if farm.verified:
            return {
                "message": "Farm already verified",
                "farm": self._format_farm_response(farm)
            }
        
        # Validate farm has minimum required information
        if not farm.size or not farm.latitude or not farm.longitude:
            raise BusinessRuleException(
                "Farm must have size and location to be verified",
                rule="complete_farm_info_required"
            )
        
        updated_farm = self.farm_repo.update(farm, verified=True)
        
        self.log_activity("farm_verified", verifier_id, {
            "farm_id": farm_id,
            "farm_name": farm.name,
            "owner_id": farm.owner_id
        })
        
        return {
            "message": "Farm verified successfully",
            "farm": self._format_farm_response(updated_farm)
        }
    
    # ========================================================================
    # Field Management
    # ========================================================================
    
    def add_field(
        self,
        farm_id: int,
        user_id: int,
        name: str,
        size: float,
        soil_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Add a field to a farm.
        
        Business Rules:
        - Total field size cannot exceed farm size
        - Field name must be unique within farm
        - Field size must be positive
        
        Args:
            farm_id: ID of farm
            user_id: ID of user adding field
            name: Field name
            size: Field size in acres
            soil_type: Soil type (optional)
            
        Returns:
            Field information
            
        Raises:
            ResourceNotFoundException: If farm not found
            InsufficientPermissionsException: If user doesn't own farm
            BusinessRuleException: If business rules violated
        """
        farm = self.check_resource_exists(
            self.farm_repo.get_by_id(farm_id),
            "Farm",
            farm_id
        )
        
        self.check_ownership(farm.owner_id, user_id, "farm")
        
        # Validate field size
        self.validate_positive(size, "size")
        
        # Check total field size doesn't exceed farm size
        fields = self.farm_repo.get_fields_by_farm(farm_id)
        total_field_size = sum(f.size for f in fields) + size
        
        if total_field_size > farm.size:
            raise BusinessRuleException(
                f"Total field size ({total_field_size} acres) would exceed farm size ({farm.size} acres)",
                rule="field_size_limit",
                details={
                    "farm_size": farm.size,
                    "current_fields_size": total_field_size - size,
                    "new_field_size": size,
                    "total_would_be": total_field_size
                }
            )
        
        # Check field name uniqueness
        if any(f.name.lower() == name.lower() for f in fields):
            raise ValidationException(
                "Field name already exists in this farm",
                field="name"
            )
        
        # Create field
        field_data = {
            "farm_id": farm_id,
            "name": name,
            "size": size,
            "soil_type": soil_type
        }
        
        field = self.farm_repo.create_field(field_data)
        
        self.log_activity("field_added", user_id, {
            "farm_id": farm_id,
            "field_id": field.id,
            "name": name,
            "size": size
        })
        
        return {
            "id": field.id,
            "farm_id": field.farm_id,
            "name": field.name,
            "size": field.size,
            "soil_type": field.soil_type,
            "created_at": field.created_at.isoformat()
        }
    
    def get_field_utilization(self, farm_id: int) -> Dict[str, Any]:
        """
        Calculate field utilization statistics for a farm.
        
        Args:
            farm_id: ID of farm
            
        Returns:
            Utilization statistics
            
        Raises:
            ResourceNotFoundException: If farm not found
        """
        farm = self.check_resource_exists(
            self.farm_repo.get_by_id(farm_id),
            "Farm",
            farm_id
        )
        
        fields = self.farm_repo.get_fields_by_farm(farm_id)
        
        total_field_size = sum(f.size for f in fields)
        unallocated_size = farm.size - total_field_size
        utilization_percentage = self.calculate_percentage(total_field_size, farm.size)
        
        return {
            "farm_id": farm_id,
            "farm_size": farm.size,
            "total_fields": len(fields),
            "allocated_size": total_field_size,
            "unallocated_size": unallocated_size,
            "utilization_percentage": utilization_percentage,
            "fields": [
                {
                    "id": f.id,
                    "name": f.name,
                    "size": f.size,
                    "percentage_of_farm": self.calculate_percentage(f.size, farm.size)
                }
                for f in fields
            ]
        }
    
    # ========================================================================
    # Crop Planting and Management
    # ========================================================================
    
    def plant_crop(
        self,
        field_id: int,
        user_id: int,
        crop_type: str,
        variety: str,
        planting_date: datetime,
        expected_harvest_date: datetime,
        quantity: float,
        unit: str = "acres"
    ) -> Dict[str, Any]:
        """
        Record crop planting in a field.
        
        Business Rules:
        - Field must exist and belong to user's farm
        - Planting date must be in the past or today
        - Expected harvest date must be after planting date
        - Quantity must be positive and not exceed field size
        - Cannot have overlapping active plantings in same field
        
        Args:
            field_id: ID of field
            user_id: ID of user
            crop_type: Type of crop
            variety: Crop variety
            planting_date: Date of planting
            expected_harvest_date: Expected harvest date
            quantity: Quantity planted
            unit: Unit of measurement (default: acres)
            
        Returns:
            Planting information
            
        Raises:
            ResourceNotFoundException: If field not found
            ValidationException: If validation fails
            BusinessRuleException: If business rules violated
        """
        field = self.check_resource_exists(
            self.farm_repo.get_field_by_id(field_id),
            "Field",
            field_id
        )
        
        farm = self.farm_repo.get_by_id(field.farm_id)
        self.check_ownership(farm.owner_id, user_id, "farm")
        
        # Validate dates
        if planting_date > datetime.utcnow():
            raise ValidationException(
                "Planting date cannot be in the future",
                field="planting_date"
            )
        
        self.validate_date_range(planting_date, expected_harvest_date, "planting period")
        
        # Validate quantity
        self.validate_positive(quantity, "quantity")
        
        if quantity > field.size:
            raise BusinessRuleException(
                f"Planting quantity ({quantity} acres) exceeds field size ({field.size} acres)",
                rule="quantity_exceeds_field_size"
            )
        
        # Check for overlapping plantings
        active_plantings = self.farm_repo.get_active_plantings_by_field(field_id)
        if active_plantings:
            raise BusinessRuleException(
                "Field already has an active planting. Harvest existing crop first.",
                rule="no_overlapping_plantings",
                details={
                    "active_planting_id": active_plantings[0].id,
                    "active_crop": active_plantings[0].crop_type
                }
            )
        
        # Create planting record
        planting_data = {
            "field_id": field_id,
            "crop_type": crop_type,
            "variety": variety,
            "planting_date": planting_date,
            "expected_harvest_date": expected_harvest_date,
            "quantity": quantity,
            "unit": unit,
            "growth_stage": GrowthStage.GERMINATION
        }
        
        planting = self.farm_repo.create_planting(planting_data)
        
        self.log_activity("crop_planted", user_id, {
            "field_id": field_id,
            "planting_id": planting.id,
            "crop_type": crop_type,
            "quantity": quantity
        })
        
        return {
            "id": planting.id,
            "field_id": planting.field_id,
            "crop_type": planting.crop_type,
            "variety": planting.variety,
            "planting_date": planting.planting_date.isoformat(),
            "expected_harvest_date": planting.expected_harvest_date.isoformat(),
            "quantity": planting.quantity,
            "unit": planting.unit,
            "growth_stage": planting.growth_stage.value,
            "message": "Crop planted successfully"
        }
    
    def update_growth_stage(
        self,
        planting_id: int,
        user_id: int,
        new_stage: str,
        notes: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Update the growth stage of a planting.
        
        Growth Stages: germination → vegetative → flowering → fruiting → maturity
        
        Args:
            planting_id: ID of planting
            user_id: ID of user
            new_stage: New growth stage
            notes: Optional notes about the update
            
        Returns:
            Updated planting information
            
        Raises:
            ResourceNotFoundException: If planting not found
            ValidationException: If stage is invalid
        """
        planting = self.check_resource_exists(
            self.farm_repo.get_planting_by_id(planting_id),
            "CropPlanting",
            planting_id
        )
        
        field = self.farm_repo.get_field_by_id(planting.field_id)
        farm = self.farm_repo.get_by_id(field.farm_id)
        self.check_ownership(farm.owner_id, user_id, "farm")
        
        # Validate growth stage
        try:
            new_stage_enum = GrowthStage(new_stage)
        except ValueError:
            valid_stages = [stage.value for stage in GrowthStage]
            raise ValidationException(
                f"Invalid growth stage. Must be one of: {', '.join(valid_stages)}",
                field="new_stage"
            )
        
        # Update planting
        updated_planting = self.farm_repo.update_planting(
            planting,
            growth_stage=new_stage_enum,
            notes=notes
        )
        
        self.log_activity("growth_stage_updated", user_id, {
            "planting_id": planting_id,
            "from_stage": planting.growth_stage.value,
            "to_stage": new_stage,
            "notes": notes
        })
        
        return {
            "id": updated_planting.id,
            "crop_type": updated_planting.crop_type,
            "growth_stage": updated_planting.growth_stage.value,
            "planting_date": updated_planting.planting_date.isoformat(),
            "days_since_planting": self.calculate_days_between(
                updated_planting.planting_date,
                datetime.utcnow()
            ),
            "message": f"Growth stage updated to {new_stage}"
        }
    
    # ========================================================================
    # Harvest Management
    # ========================================================================
    
    def record_harvest(
        self,
        planting_id: int,
        user_id: int,
        harvest_date: datetime,
        quantity: float,
        unit: str,
        quality_grade: Optional[str] = None,
        notes: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Record a harvest for a planting.
        
        Business Rules:
        - Planting must exist and be active
        - Harvest date must be after planting date
        - Quantity must be positive
        - Harvest marks planting as complete
        
        Args:
            planting_id: ID of planting
            user_id: ID of user
            harvest_date: Date of harvest
            quantity: Quantity harvested
            unit: Unit of measurement
            quality_grade: Quality grade (A, B, C) (optional)
            notes: Harvest notes (optional)
            
        Returns:
            Harvest information with yield calculations
            
        Raises:
            ResourceNotFoundException: If planting not found
            ValidationException: If validation fails
            BusinessRuleException: If business rules violated
        """
        planting = self.check_resource_exists(
            self.farm_repo.get_planting_by_id(planting_id),
            "CropPlanting",
            planting_id
        )
        
        field = self.farm_repo.get_field_by_id(planting.field_id)
        farm = self.farm_repo.get_by_id(field.farm_id)
        self.check_ownership(farm.owner_id, user_id, "farm")
        
        # Validate harvest date
        if harvest_date < planting.planting_date:
            raise ValidationException(
                "Harvest date cannot be before planting date",
                field="harvest_date"
            )
        
        if harvest_date > datetime.utcnow():
            raise ValidationException(
                "Harvest date cannot be in the future",
                field="harvest_date"
            )
        
        # Validate quantity
        self.validate_positive(quantity, "quantity")
        
        # Check if already harvested
        existing_harvests = self.farm_repo.get_harvests_by_planting(planting_id)
        if existing_harvests:
            raise BusinessRuleException(
                "This planting has already been harvested",
                rule="single_harvest_per_planting",
                details={"existing_harvest_id": existing_harvests[0].id}
            )
        
        # Create harvest record
        harvest_data = {
            "planting_id": planting_id,
            "harvest_date": harvest_date,
            "quantity": quantity,
            "unit": unit,
            "quality_grade": quality_grade,
            "notes": notes
        }
        
        harvest = self.farm_repo.create_harvest(harvest_data)
        
        # Calculate yield statistics
        days_to_harvest = self.calculate_days_between(
            planting.planting_date,
            harvest_date
        )
        
        yield_per_acre = quantity / planting.quantity if planting.quantity > 0 else 0
        
        # Mark planting as harvested
        self.farm_repo.update_planting(planting, growth_stage=GrowthStage.MATURITY)
        
        self.log_activity("harvest_recorded", user_id, {
            "planting_id": planting_id,
            "harvest_id": harvest.id,
            "quantity": quantity,
            "yield_per_acre": yield_per_acre
        })
        
        return {
            "id": harvest.id,
            "planting_id": harvest.planting_id,
            "crop_type": planting.crop_type,
            "harvest_date": harvest.harvest_date.isoformat(),
            "quantity": harvest.quantity,
            "unit": harvest.unit,
            "quality_grade": harvest.quality_grade,
            "yield_statistics": {
                "days_to_harvest": days_to_harvest,
                "yield_per_acre": round(yield_per_acre, 2),
                "total_quantity": quantity,
                "planted_area": planting.quantity
            },
            "message": "Harvest recorded successfully"
        }
    
    def calculate_average_yield(
        self,
        farm_id: int,
        crop_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Calculate average yield for a farm's crops.
        
        Args:
            farm_id: ID of farm
            crop_type: Specific crop type (optional, defaults to all crops)
            
        Returns:
            Average yield statistics
            
        Raises:
            ResourceNotFoundException: If farm not found
        """
        farm = self.check_resource_exists(
            self.farm_repo.get_by_id(farm_id),
            "Farm",
            farm_id
        )
        
        # Get all harvests for this farm
        fields = self.farm_repo.get_fields_by_farm(farm_id)
        all_harvests = []
        
        for field in fields:
            plantings = self.farm_repo.get_plantings_by_field(field.id)
            for planting in plantings:
                if crop_type and planting.crop_type != crop_type:
                    continue
                harvests = self.farm_repo.get_harvests_by_planting(planting.id)
                for harvest in harvests:
                    all_harvests.append({
                        "planting": planting,
                        "harvest": harvest
                    })
        
        if not all_harvests:
            return {
                "farm_id": farm_id,
                "crop_type": crop_type,
                "total_harvests": 0,
                "average_yield_per_acre": 0,
                "message": "No harvest data available"
            }
        
        # Calculate statistics
        total_yield = sum(h["harvest"].quantity for h in all_harvests)
        total_area = sum(h["planting"].quantity for h in all_harvests)
        average_yield_per_acre = total_yield / total_area if total_area > 0 else 0
        
        # Calculate average days to harvest
        days_to_harvest_list = [
            self.calculate_days_between(
                h["planting"].planting_date,
                h["harvest"].harvest_date
            )
            for h in all_harvests
        ]
        average_days_to_harvest = sum(days_to_harvest_list) / len(days_to_harvest_list)
        
        return {
            "farm_id": farm_id,
            "crop_type": crop_type or "all_crops",
            "total_harvests": len(all_harvests),
            "total_yield": total_yield,
            "total_area_harvested": total_area,
            "average_yield_per_acre": round(average_yield_per_acre, 2),
            "average_days_to_harvest": round(average_days_to_harvest, 1),
            "harvests_by_quality": self._group_harvests_by_quality(all_harvests)
        }
    
    def _group_harvests_by_quality(self, harvests: List[Dict]) -> Dict[str, int]:
        """Group harvests by quality grade."""
        quality_counts = {}
        for h in harvests:
            grade = h["harvest"].quality_grade or "ungraded"
            quality_counts[grade] = quality_counts.get(grade, 0) + 1
        return quality_counts
    
    # ========================================================================
    # Geographic Queries
    # ========================================================================
    
    def find_nearby_farms(
        self,
        latitude: float,
        longitude: float,
        radius_km: float = 10,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Find farms near a specific location.
        
        Args:
            latitude: Center latitude
            longitude: Center longitude
            radius_km: Search radius in kilometers (default: 10)
            limit: Maximum number of results (default: 10)
            
        Returns:
            List of nearby farms with distances
            
        Raises:
            ValidationException: If coordinates are invalid
        """
        self.validate_coordinates(latitude, longitude)
        self.validate_positive(radius_km, "radius_km")
        
        farms = self.farm_repo.get_nearby_farms(latitude, longitude, radius_km, limit)
        
        return [
            {
                "id": farm.id,
                "name": farm.name,
                "owner_id": farm.owner_id,
                "size": farm.size,
                "county": farm.county,
                "verified": farm.verified,
                "latitude": farm.latitude,
                "longitude": farm.longitude,
                "distance_km": round(farm.distance / 1000, 2) if hasattr(farm, 'distance') else None
            }
            for farm in farms
        ]
    
    def get_farms_in_county(self, county: str, page: int = 1, page_size: int = 20) -> Dict[str, Any]:
        """
        Get all farms in a specific county with pagination.
        
        Args:
            county: County name
            page: Page number (default: 1)
            page_size: Items per page (default: 20)
            
        Returns:
            Paginated list of farms
        """
        farms = self.farm_repo.get_by_county(county)
        
        return self.paginate_results(
            [self._format_farm_response(f) for f in farms],
            page,
            page_size
        )
    
    # ========================================================================
    # Farm Analytics and Reporting
    # ========================================================================
    
    def get_farm_dashboard(self, farm_id: int, user_id: int) -> Dict[str, Any]:
        """
        Get comprehensive dashboard data for a farm.
        
        Args:
            farm_id: ID of farm
            user_id: ID of requesting user
            
        Returns:
            Dashboard data with statistics
            
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
        
        # Get fields and plantings
        fields = self.farm_repo.get_fields_by_farm(farm_id)
        all_plantings = []
        active_plantings = []
        
        for field in fields:
            plantings = self.farm_repo.get_plantings_by_field(field.id)
            all_plantings.extend(plantings)
            active_plantings.extend([p for p in plantings if p.growth_stage != GrowthStage.MATURITY])
        
        # Get field utilization
        utilization = self.get_field_utilization(farm_id)
        
        # Get yield statistics
        yield_stats = self.calculate_average_yield(farm_id)
        
        # Get upcoming harvests (expected within 30 days)
        upcoming_harvests = [
            {
                "planting_id": p.id,
                "crop_type": p.crop_type,
                "field_name": next((f.name for f in fields if f.id == p.field_id), "Unknown"),
                "expected_date": p.expected_harvest_date.isoformat(),
                "days_until_harvest": self.calculate_days_between(
                    datetime.utcnow(),
                    p.expected_harvest_date
                )
            }
            for p in active_plantings
            if p.expected_harvest_date and
            0 <= self.calculate_days_between(datetime.utcnow(), p.expected_harvest_date) <= 30
        ]
        
        return {
            "farm": self._format_farm_response(farm),
            "statistics": {
                "total_fields": len(fields),
                "total_plantings": len(all_plantings),
                "active_plantings": len(active_plantings),
                "utilization_percentage": utilization["utilization_percentage"],
                "average_yield_per_acre": yield_stats["average_yield_per_acre"],
                "total_harvests": yield_stats["total_harvests"]
            },
            "upcoming_harvests": upcoming_harvests,
            "field_breakdown": [
                {
                    "id": f.id,
                    "name": f.name,
                    "size": f.size,
                    "active_crop": next(
                        (p.crop_type for p in active_plantings if p.field_id == f.id),
                        None
                    )
                }
                for f in fields
            ]
        }
    
    def generate_farm_report(
        self,
        farm_id: int,
        user_id: int,
        start_date: datetime,
        end_date: datetime
    ) -> Dict[str, Any]:
        """
        Generate a comprehensive report for a farm over a date range.
        
        Args:
            farm_id: ID of farm
            user_id: ID of requesting user
            start_date: Report start date
            end_date: Report end date
            
        Returns:
            Comprehensive farm report
            
        Raises:
            ResourceNotFoundException: If farm not found
            InsufficientPermissionsException: If user doesn't own farm
            ValidationException: If date range is invalid
        """
        farm = self.check_resource_exists(
            self.farm_repo.get_by_id(farm_id),
            "Farm",
            farm_id
        )
        
        self.check_ownership(farm.owner_id, user_id, "farm")
        self.validate_date_range(start_date, end_date, "report period")
        
        # Get fields
        fields = self.farm_repo.get_fields_by_farm(farm_id)
        
        # Get plantings in date range
        plantings_in_range = []
        harvests_in_range = []
        
        for field in fields:
            plantings = self.farm_repo.get_plantings_by_field(field.id)
            for planting in plantings:
                if start_date <= planting.planting_date <= end_date:
                    plantings_in_range.append(planting)
                
                harvests = self.farm_repo.get_harvests_by_planting(planting.id)
                for harvest in harvests:
                    if start_date <= harvest.harvest_date <= end_date:
                        harvests_in_range.append((planting, harvest))
        
        # Calculate statistics
        total_planted_area = sum(p.quantity for p in plantings_in_range)
        total_harvested_quantity = sum(h[1].quantity for h in harvests_in_range)
        
        # Crop diversity
        crops_planted = {}
        for p in plantings_in_range:
            crops_planted[p.crop_type] = crops_planted.get(p.crop_type, 0) + 1
        
        return {
            "farm_id": farm_id,
            "farm_name": farm.name,
            "report_period": {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "days": self.calculate_days_between(start_date, end_date)
            },
            "planting_summary": {
                "total_plantings": len(plantings_in_range),
                "total_area_planted": total_planted_area,
                "crops_diversity": len(crops_planted),
                "crops_planted": crops_planted
            },
            "harvest_summary": {
                "total_harvests": len(harvests_in_range),
                "total_quantity_harvested": total_harvested_quantity,
                "average_yield_per_acre": (
                    total_harvested_quantity / total_planted_area
                    if total_planted_area > 0 else 0
                )
            },
            "field_utilization": self.get_field_utilization(farm_id),
            "generated_at": datetime.utcnow().isoformat()
        }
    
    # ========================================================================
    # Helper Methods
    # ========================================================================
    
    def _format_farm_response(self, farm: Farm) -> Dict[str, Any]:
        """Format farm object as API response dictionary."""
        return {
            "id": farm.id,
            "owner_id": farm.owner_id,
            "name": farm.name,
            "size": farm.size,
            "county": farm.county,
            "description": farm.description,
            "verified": farm.verified,
            "location": {
                "latitude": farm.latitude,
                "longitude": farm.longitude
            },
            "created_at": farm.created_at.isoformat(),
            "updated_at": farm.updated_at.isoformat() if farm.updated_at else None
        }
