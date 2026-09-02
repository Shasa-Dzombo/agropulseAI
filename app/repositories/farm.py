"""
🚜 Farm Repository

Specialized repository for Farm model with geographic queries, crop tracking,
and farm management features.

Features:
- Geographic queries (nearby farms, boundary searches)
- Certification filtering
- Farm statistics and analytics
- Crop tracking integration
- Farm health monitoring

Author: AgroPulse Engineering Team
"""

from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
from geoalchemy2 import functions as geo_func

from app.models.database import Farm, Field, CropPlanting
from app.repositories.base import BaseRepository


class FarmRepository(BaseRepository[Farm]):
    """Repository for Farm model with geographic and agricultural features."""
    
    def __init__(self, db: Session):
        """
        Initialize farm repository.
        
        Args:
            db: Database session
        """
        super().__init__(Farm, db)
    
    # ========================================================================
    # GEOGRAPHIC QUERIES
    # ========================================================================
    
    def get_by_location(
        self,
        latitude: float,
        longitude: float,
        radius_km: float = 10.0,
        skip: int = 0,
        limit: int = 50
    ) -> List[Farm]:
        """
        Get farms within radius of a location.
        
        Args:
            latitude: Center point latitude
            longitude: Center point longitude
            radius_km: Search radius in kilometers
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List of farms within radius
        """
        # Convert km to meters for PostGIS
        radius_meters = radius_km * 1000
        
        # Create point from coordinates
        point = func.ST_SetSRID(func.ST_MakePoint(longitude, latitude), 4326)
        
        return self.db.query(Farm).filter(
            and_(
                geo_func.ST_DWithin(
                    Farm.location,
                    point,
                    radius_meters
                ),
                Farm.is_deleted == False
            )
        ).offset(skip).limit(limit).all()
    
    def get_by_county(
        self,
        county: str,
        skip: int = 0,
        limit: int = 100
    ) -> List[Farm]:
        """
        Get farms in a specific county.
        
        Args:
            county: County name
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List of farms in county
        """
        return self.filter({'county': county}, skip=skip, limit=limit)
    
    def get_by_sub_county(
        self,
        sub_county: str,
        skip: int = 0,
        limit: int = 100
    ) -> List[Farm]:
        """
        Get farms in a specific sub-county.
        
        Args:
            sub_county: Sub-county name
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List of farms in sub-county
        """
        return self.filter({'sub_county': sub_county}, skip=skip, limit=limit)
    
    def calculate_distance(
        self,
        farm1_id: int,
        farm2_id: int
    ) -> Optional[float]:
        """
        Calculate distance between two farms in kilometers.
        
        Args:
            farm1_id: First farm ID
            farm2_id: Second farm ID
            
        Returns:
            Distance in kilometers, None if farms not found
        """
        farm1 = self.get_by_id(farm1_id)
        farm2 = self.get_by_id(farm2_id)
        
        if not farm1 or not farm2:
            return None
        
        distance_meters = self.db.query(
            geo_func.ST_Distance(farm1.location, farm2.location)
        ).scalar()
        
        return distance_meters / 1000.0 if distance_meters else None
    
    def get_farms_in_polygon(
        self,
        polygon_geojson: Dict[str, Any],
        skip: int = 0,
        limit: int = 100
    ) -> List[Farm]:
        """
        Get farms within a polygon boundary.
        
        Args:
            polygon_geojson: GeoJSON polygon
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List of farms within polygon
        """
        # Convert GeoJSON to PostGIS geometry
        polygon = func.ST_GeomFromGeoJSON(str(polygon_geojson))
        
        return self.db.query(Farm).filter(
            and_(
                geo_func.ST_Within(Farm.location, polygon),
                Farm.is_deleted == False
            )
        ).offset(skip).limit(limit).all()
    
    # ========================================================================
    # FARM MANAGEMENT
    # ========================================================================
    
    def get_by_user(
        self,
        user_id: int,
        skip: int = 0,
        limit: int = 100
    ) -> List[Farm]:
        """
        Get all farms owned by a user.
        
        Args:
            user_id: User ID
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List of user's farms
        """
        return self.filter({'user_id': user_id}, skip=skip, limit=limit)
    
    def get_active_farms(
        self,
        skip: int = 0,
        limit: int = 100
    ) -> List[Farm]:
        """
        Get all active farms.
        
        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List of active farms
        """
        return self.filter({'is_active': True}, skip=skip, limit=limit)
    
    def get_by_farm_type(
        self,
        farm_type: str,
        skip: int = 0,
        limit: int = 100
    ) -> List[Farm]:
        """
        Get farms by type.
        
        Args:
            farm_type: Farm type (e.g., 'mixed', 'organic', 'commercial')
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List of farms of specified type
        """
        return self.filter({'farm_type': farm_type}, skip=skip, limit=limit)
    
    def get_by_primary_crop(
        self,
        crop_name: str,
        skip: int = 0,
        limit: int = 100
    ) -> List[Farm]:
        """
        Get farms by primary crop.
        
        Args:
            crop_name: Crop name
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List of farms growing specified crop
        """
        return self.filter({'primary_crop': crop_name}, skip=skip, limit=limit)
    
    # ========================================================================
    # CERTIFICATION & VERIFICATION
    # ========================================================================
    
    def get_organic_certified(
        self,
        skip: int = 0,
        limit: int = 100
    ) -> List[Farm]:
        """
        Get organic certified farms.
        
        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List of organic certified farms
        """
        return self.filter({'organic_certified': True}, skip=skip, limit=limit)
    
    def get_global_gap_certified(
        self,
        skip: int = 0,
        limit: int = 100
    ) -> List[Farm]:
        """
        Get GlobalGAP certified farms.
        
        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List of GlobalGAP certified farms
        """
        return self.filter({'global_gap_certified': True}, skip=skip, limit=limit)
    
    def get_verified_farms(
        self,
        skip: int = 0,
        limit: int = 100
    ) -> List[Farm]:
        """
        Get verified farms.
        
        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List of verified farms
        """
        return self.filter({'verification_status': 'verified'}, skip=skip, limit=limit)
    
    def verify_farm(
        self,
        farm_id: int
    ) -> Optional[Farm]:
        """
        Verify a farm.
        
        Args:
            farm_id: Farm ID
            
        Returns:
            Updated farm if successful, None otherwise
        """
        farm = self.get_by_id(farm_id)
        if not farm:
            return None
        
        farm.verification_status = 'verified'
        self.db.commit()
        self.db.refresh(farm)
        return farm
    
    # ========================================================================
    # SIZE & AREA QUERIES
    # ========================================================================
    
    def get_by_size_range(
        self,
        min_acres: float,
        max_acres: float,
        skip: int = 0,
        limit: int = 100,
        owner_id: Optional[int] = None
    ) -> List[Farm]:
        """
        Get farms within size range.

        Args:
            min_acres: Minimum size in acres
            max_acres: Maximum size in acres
            skip: Number of records to skip
            limit: Maximum number of records to return
            owner_id: Restrict to this owner's farms only (None = all owners)

        Returns:
            List of farms within size range
        """
        conditions = [
            Farm.size_acres >= min_acres,
            Farm.size_acres <= max_acres,
            Farm.is_deleted == False
        ]
        if owner_id is not None:
            conditions.append(Farm.owner_id == owner_id)
        return self.db.query(Farm).filter(and_(*conditions)).offset(skip).limit(limit).all()
    
    def get_large_farms(
        self,
        min_acres: float = 10.0,
        skip: int = 0,
        limit: int = 100
    ) -> List[Farm]:
        """
        Get large farms (above minimum size).
        
        Args:
            min_acres: Minimum size threshold
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List of large farms
        """
        return self.db.query(Farm).filter(
            and_(
                Farm.size_acres >= min_acres,
                Farm.is_deleted == False
            )
        ).order_by(Farm.size_acres.desc()).offset(skip).limit(limit).all()
    
    def get_small_holder_farms(
        self,
        max_acres: float = 5.0,
        skip: int = 0,
        limit: int = 100
    ) -> List[Farm]:
        """
        Get small-holder farms (below maximum size).
        
        Args:
            max_acres: Maximum size threshold
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List of small-holder farms
        """
        return self.db.query(Farm).filter(
            and_(
                Farm.size_acres <= max_acres,
                Farm.is_deleted == False
            )
        ).order_by(Farm.size_acres.asc()).offset(skip).limit(limit).all()
    
    # ========================================================================
    # IRRIGATION & WATER
    # ========================================================================
    
    def get_irrigated_farms(
        self,
        skip: int = 0,
        limit: int = 100
    ) -> List[Farm]:
        """
        Get farms with irrigation.
        
        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List of irrigated farms
        """
        return self.filter({'has_irrigation': True}, skip=skip, limit=limit)
    
    def get_by_irrigation_type(
        self,
        irrigation_type: str,
        skip: int = 0,
        limit: int = 100
    ) -> List[Farm]:
        """
        Get farms by irrigation type.
        
        Args:
            irrigation_type: Irrigation type (drip, sprinkler, flood, etc.)
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List of farms with specified irrigation type
        """
        return self.filter({'irrigation_type': irrigation_type}, skip=skip, limit=limit)
    
    def get_by_water_source(
        self,
        water_source: str,
        skip: int = 0,
        limit: int = 100
    ) -> List[Farm]:
        """
        Get farms by water source.
        
        Args:
            water_source: Water source (river, borehole, dam, etc.)
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List of farms with specified water source
        """
        return self.filter({'water_source': water_source}, skip=skip, limit=limit)
    
    # ========================================================================
    # SOIL & CLIMATE
    # ========================================================================
    
    def get_by_soil_type(
        self,
        soil_type: str,
        skip: int = 0,
        limit: int = 100
    ) -> List[Farm]:
        """
        Get farms by soil type.
        
        Args:
            soil_type: Soil type (clay, loam, sandy, etc.)
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List of farms with specified soil type
        """
        return self.filter({'soil_type': soil_type}, skip=skip, limit=limit)
    
    def get_by_climate_zone(
        self,
        climate_zone: str,
        skip: int = 0,
        limit: int = 100
    ) -> List[Farm]:
        """
        Get farms by climate zone.
        
        Args:
            climate_zone: Climate zone
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List of farms in specified climate zone
        """
        return self.filter({'climate_zone': climate_zone}, skip=skip, limit=limit)
    
    # ========================================================================
    # SEARCH
    # ========================================================================
    
    def search_farms(
        self,
        search_term: str,
        skip: int = 0,
        limit: int = 50
    ) -> List[Farm]:
        """
        Search farms by name or description.
        
        Args:
            search_term: Search term
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List of matching farms
        """
        return self.search(
            search_term,
            ['name', 'description'],
            skip=skip,
            limit=limit
        )
    
    # ========================================================================
    # STATISTICS & ANALYTICS
    # ========================================================================
    
    def get_farm_statistics(self) -> Dict[str, Any]:
        """
        Get farm statistics.
        
        Returns:
            Dictionary with farm statistics
        """
        total = self.count()
        active = self.count({'is_active': True})
        verified = self.count({'verification_status': 'verified'})
        organic = self.count({'organic_certified': True})
        irrigated = self.count({'has_irrigation': True})
        
        # Calculate total area
        total_area = self.db.query(
            func.sum(Farm.size_acres)
        ).filter(Farm.is_deleted == False).scalar() or 0
        
        # Calculate average farm size
        avg_size = self.db.query(
            func.avg(Farm.size_acres)
        ).filter(Farm.is_deleted == False).scalar() or 0
        
        return {
            'total_farms': total,
            'active_farms': active,
            'verified_farms': verified,
            'organic_certified': organic,
            'irrigated_farms': irrigated,
            'total_area_acres': float(total_area),
            'average_size_acres': float(avg_size)
        }
    
    def get_county_breakdown(self) -> Dict[str, int]:
        """
        Get farm count by county.
        
        Returns:
            Dictionary with county counts
        """
        result = self.db.query(
            Farm.county,
            func.count(Farm.id)
        ).filter(
            Farm.is_deleted == False
        ).group_by(Farm.county).all()
        
        return {county: count for county, count in result if county}
    
    def get_crop_distribution(self) -> Dict[str, int]:
        """
        Get farm count by primary crop.
        
        Returns:
            Dictionary with crop counts
        """
        result = self.db.query(
            Farm.primary_crop,
            func.count(Farm.id)
        ).filter(
            Farm.is_deleted == False
        ).group_by(Farm.primary_crop).all()
        
        return {crop: count for crop, count in result if crop}
    
    def get_soil_type_distribution(self) -> Dict[str, int]:
        """
        Get farm count by soil type.
        
        Returns:
            Dictionary with soil type counts
        """
        result = self.db.query(
            Farm.soil_type,
            func.count(Farm.id)
        ).filter(
            Farm.is_deleted == False
        ).group_by(Farm.soil_type).all()
        
        return {soil: count for soil, count in result if soil}
    
    def get_largest_farms(
        self,
        limit: int = 10
    ) -> List[Farm]:
        """
        Get largest farms by area.
        
        Args:
            limit: Number of farms to return
            
        Returns:
            List of largest farms
        """
        return self.db.query(Farm).filter(
            Farm.is_deleted == False
        ).order_by(Farm.size_acres.desc()).limit(limit).all()
    
    # ========================================================================
    # FIELD MANAGEMENT
    # ========================================================================
    
    def get_fields(
        self,
        farm_id: int
    ) -> List[Field]:
        """
        Get all fields for a farm.
        
        Args:
            farm_id: Farm ID
            
        Returns:
            List of fields
        """
        return self.db.query(Field).filter(
            and_(
                Field.farm_id == farm_id,
                Field.is_deleted == False
            )
        ).all()
    
    def get_field_count(
        self,
        farm_id: int
    ) -> int:
        """
        Get count of fields for a farm.
        
        Args:
            farm_id: Farm ID
            
        Returns:
            Number of fields
        """
        return self.db.query(Field).filter(
            and_(
                Field.farm_id == farm_id,
                Field.is_deleted == False
            )
        ).count()
    
    def get_total_field_area(
        self,
        farm_id: int
    ) -> float:
        """
        Get total area of all fields in a farm.
        
        Args:
            farm_id: Farm ID
            
        Returns:
            Total field area in acres
        """
        total = self.db.query(
            func.sum(Field.size_acres)
        ).filter(
            and_(
                Field.farm_id == farm_id,
                Field.is_deleted == False
            )
        ).scalar()
        
        return float(total) if total else 0.0
    
    # ========================================================================
    # CROP PLANTING INTEGRATION
    # ========================================================================
    
    def get_active_plantings(
        self,
        farm_id: int
    ) -> List[CropPlanting]:
        """
        Get active crop plantings for a farm.
        
        Args:
            farm_id: Farm ID
            
        Returns:
            List of active crop plantings
        """
        return self.db.query(CropPlanting).filter(
            and_(
                CropPlanting.farm_id == farm_id,
                CropPlanting.status == 'active',
                CropPlanting.is_deleted == False
            )
        ).all()
    
    def get_planting_count(
        self,
        farm_id: int
    ) -> int:
        """
        Get count of crop plantings for a farm.
        
        Args:
            farm_id: Farm ID
            
        Returns:
            Number of crop plantings
        """
        return self.db.query(CropPlanting).filter(
            and_(
                CropPlanting.farm_id == farm_id,
                CropPlanting.is_deleted == False
            )
        ).count()
