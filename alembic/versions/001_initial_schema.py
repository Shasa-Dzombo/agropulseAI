"""
🗄️ AgroPulse Database Migrations

Initial migration creating all core tables for the AgroPulse platform.

This migration creates:
- User management tables (users, user_sessions, api_keys)
- Farm management tables (farms, fields, crop_plantings)
- Diagnosis system tables (diagnoses, diseases, treatments, treatment_applications)
- Product catalog (products, suppliers, product_supplier_association)
- Digital Chama tables (chamas, transactions, loans, loan_repayments, chama_meetings)
- IoT tables (iot_devices, sensor_readings, weather_records, soil_tests)
- Alert & notification tables (alerts, notifications)
- Audit tables (audit_logs)
- Association tables for many-to-many relationships

Revision ID: 001_initial_schema
Revises: None
Create Date: 2025-11-01 10:00:00

Lines: 1800+
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import geoalchemy2

# revision identifiers
revision = '001_initial_schema'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create all initial tables."""
    
    # ========================================================================
    # ENABLE EXTENSIONS
    # ========================================================================
    
    op.execute('CREATE EXTENSION IF NOT EXISTS postgis')
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')
    op.execute('CREATE EXTENSION IF NOT EXISTS pg_trgm')  # For text search
    op.execute('CREATE EXTENSION IF NOT EXISTS btree_gin')  # For composite indexes
    
    # ========================================================================
    # USER MANAGEMENT TABLES
    # ========================================================================
    
    # Users table
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('uuid', postgresql.UUID(as_uuid=True), server_default=sa.text('uuid_generate_v4()'), nullable=False),
        
        # Authentication
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('phone_number', sa.String(length=20), nullable=True),
        sa.Column('password_hash', sa.String(length=255), nullable=False),
        sa.Column('two_factor_secret', sa.String(length=100), nullable=True),
        sa.Column('two_factor_enabled', sa.Boolean(), default=False),
        
        # Profile
        sa.Column('first_name', sa.String(length=100), nullable=False),
        sa.Column('last_name', sa.String(length=100), nullable=False),
        sa.Column('middle_name', sa.String(length=100), nullable=True),
        sa.Column('display_name', sa.String(length=200), nullable=True),
        sa.Column('date_of_birth', sa.Date(), nullable=True),
        sa.Column('gender', sa.String(length=20), nullable=True),
        sa.Column('national_id', sa.String(length=50), nullable=True),
        
        # Contact
        sa.Column('alternate_phone', sa.String(length=20), nullable=True),
        sa.Column('whatsapp_number', sa.String(length=20), nullable=True),
        sa.Column('address_line1', sa.String(length=255), nullable=True),
        sa.Column('address_line2', sa.String(length=255), nullable=True),
        sa.Column('city', sa.String(length=100), nullable=True),
        sa.Column('county', sa.String(length=100), nullable=True),
        sa.Column('postal_code', sa.String(length=20), nullable=True),
        sa.Column('country', sa.String(length=100), default='Kenya'),
        
        # Location
        sa.Column('latitude', sa.Float(), nullable=True),
        sa.Column('longitude', sa.Float(), nullable=True),
        sa.Column('altitude', sa.Float(), nullable=True),
        sa.Column('location', geoalchemy2.types.Geography(geometry_type='POINT', srid=4326), nullable=True),
        sa.Column('location_accuracy', sa.Float(), nullable=True),
        
        # Role and permissions
        sa.Column('role', sa.String(length=50), nullable=False, default='farmer'),
        sa.Column('permissions', postgresql.JSONB(), default=dict),
        sa.Column('is_superuser', sa.Boolean(), default=False),
        sa.Column('is_staff', sa.Boolean(), default=False),
        sa.Column('is_verified', sa.Boolean(), default=False),
        
        # Account status
        sa.Column('status', sa.String(length=50), nullable=False, default='pending_verification'),
        sa.Column('email_verified', sa.Boolean(), default=False),
        sa.Column('phone_verified', sa.Boolean(), default=False),
        sa.Column('kyc_verified', sa.Boolean(), default=False),
        
        # Subscription
        sa.Column('subscription_tier', sa.String(length=50), default='free'),
        sa.Column('subscription_expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('diagnoses_remaining', sa.Integer(), default=3),
        
        # Preferences
        sa.Column('language_preference', sa.String(length=10), default='en'),
        sa.Column('timezone', sa.String(length=50), default='Africa/Nairobi'),
        sa.Column('notification_preferences', postgresql.JSONB(), default=dict),
        sa.Column('theme_preference', sa.String(length=20), default='light'),
        
        # Profile completion
        sa.Column('profile_completion_percentage', sa.Float(), default=0.0),
        sa.Column('onboarding_completed', sa.Boolean(), default=False),
        sa.Column('onboarding_step', sa.Integer(), default=0),
        
        # Activity tracking
        sa.Column('last_login_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_login_ip', postgresql.INET(), nullable=True),
        sa.Column('login_count', sa.Integer(), default=0),
        sa.Column('failed_login_attempts', sa.Integer(), default=0),
        sa.Column('last_failed_login_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('account_locked_until', sa.DateTime(timezone=True), nullable=True),
        
        # Profile images
        sa.Column('avatar_url', sa.String(length=500), nullable=True),
        sa.Column('cover_photo_url', sa.String(length=500), nullable=True),
        
        # Social
        sa.Column('social_links', postgresql.JSONB(), default=dict),
        
        # Metrics
        sa.Column('total_diagnoses', sa.Integer(), default=0),
        sa.Column('total_farms', sa.Integer(), default=0),
        sa.Column('total_spent_ksh', sa.DECIMAL(12, 2), default=0),
        sa.Column('reputation_score', sa.Float(), default=0.0),
        
        # Referral
        sa.Column('referral_code', sa.String(length=20), nullable=True),
        sa.Column('referred_by_id', sa.Integer(), nullable=True),
        sa.Column('referral_count', sa.Integer(), default=0),
        sa.Column('referral_earnings_ksh', sa.DECIMAL(10, 2), default=0),
        
        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_deleted', sa.Boolean(), default=False),
        
        # Versioning
        sa.Column('version', sa.Integer(), default=1),
        
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['referred_by_id'], ['users.id'], ondelete='SET NULL'),
        sa.UniqueConstraint('uuid'),
        sa.UniqueConstraint('email'),
        sa.UniqueConstraint('phone_number'),
        sa.UniqueConstraint('national_id'),
        sa.UniqueConstraint('referral_code'),
        sa.CheckConstraint('profile_completion_percentage >= 0 AND profile_completion_percentage <= 100'),
        sa.CheckConstraint('reputation_score >= 0 AND reputation_score <= 100')
    )
    
    # Indexes for users table
    op.create_index('idx_user_email_status', 'users', ['email', 'status'])
    op.create_index('idx_user_phone_status', 'users', ['phone_number', 'status'])
    op.create_index('idx_user_role_status', 'users', ['role', 'status'])
    op.create_index('idx_user_created_at', 'users', ['created_at'])
    op.create_index('idx_user_subscription', 'users', ['subscription_tier', 'subscription_expires_at'])
    op.create_index('idx_user_uuid', 'users', ['uuid'])
    op.create_index('idx_user_deleted', 'users', ['is_deleted'])
    
    # User Sessions table
    op.create_table(
        'user_sessions',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('uuid', postgresql.UUID(as_uuid=True), server_default=sa.text('uuid_generate_v4()'), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        
        # Session details
        sa.Column('session_token', sa.String(length=255), nullable=False),
        sa.Column('refresh_token', sa.String(length=255), nullable=True),
        sa.Column('device_id', sa.String(length=255), nullable=True),
        
        # Device info
        sa.Column('user_agent', sa.Text(), nullable=True),
        sa.Column('device_type', sa.String(length=50), nullable=True),
        sa.Column('os', sa.String(length=50), nullable=True),
        sa.Column('os_version', sa.String(length=50), nullable=True),
        sa.Column('browser', sa.String(length=50), nullable=True),
        sa.Column('browser_version', sa.String(length=50), nullable=True),
        
        # Network info
        sa.Column('ip_address', postgresql.INET(), nullable=True),
        sa.Column('country', sa.String(length=100), nullable=True),
        sa.Column('city', sa.String(length=100), nullable=True),
        sa.Column('isp', sa.String(length=255), nullable=True),
        
        # Lifecycle
        sa.Column('started_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('last_activity_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('ended_at', sa.DateTime(timezone=True), nullable=True),
        
        # Status
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('logout_reason', sa.String(length=100), nullable=True),
        
        # Security
        sa.Column('risk_score', sa.Float(), default=0.0),
        sa.Column('is_suspicious', sa.Boolean(), default=False),
        sa.Column('security_events', postgresql.JSONB(), default=list),
        
        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
        
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('uuid'),
        sa.UniqueConstraint('session_token'),
        sa.UniqueConstraint('refresh_token')
    )
    
    op.create_index('idx_session_user_active', 'user_sessions', ['user_id', 'is_active'])
    op.create_index('idx_session_expires', 'user_sessions', ['expires_at'])
    op.create_index('idx_session_token', 'user_sessions', ['session_token'])
    
    # API Keys table
    op.create_table(
        'api_keys',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('uuid', postgresql.UUID(as_uuid=True), server_default=sa.text('uuid_generate_v4()'), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        
        # Key details
        sa.Column('key_name', sa.String(length=100), nullable=False),
        sa.Column('key_hash', sa.String(length=255), nullable=False),
        sa.Column('key_prefix', sa.String(length=20), nullable=False),
        
        # Permissions
        sa.Column('scopes', postgresql.ARRAY(sa.String()), default=list),
        sa.Column('rate_limit_per_hour', sa.Integer(), default=100),
        sa.Column('rate_limit_per_day', sa.Integer(), default=1000),
        
        # Usage
        sa.Column('last_used_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('total_requests', sa.BigInteger(), default=0),
        sa.Column('failed_requests', sa.BigInteger(), default=0),
        
        # Status
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        
        # Security
        sa.Column('allowed_ip_addresses', postgresql.ARRAY(sa.String()), default=list),
        sa.Column('allowed_domains', postgresql.ARRAY(sa.String()), default=list),
        
        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_deleted', sa.Boolean(), default=False),
        
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('uuid'),
        sa.UniqueConstraint('key_hash')
    )
    
    op.create_index('idx_apikey_user_active', 'api_keys', ['user_id', 'is_active'])
    op.create_index('idx_apikey_hash', 'api_keys', ['key_hash'])
    
    # ========================================================================
    # FARM MANAGEMENT TABLES
    # ========================================================================
    
    # Farms table
    op.create_table(
        'farms',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('uuid', postgresql.UUID(as_uuid=True), server_default=sa.text('uuid_generate_v4()'), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        
        # Basic details
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('farm_code', sa.String(length=50), nullable=True),
        
        # Location
        sa.Column('latitude', sa.Float(), nullable=False),
        sa.Column('longitude', sa.Float(), nullable=False),
        sa.Column('altitude', sa.Float(), nullable=True),
        sa.Column('location', geoalchemy2.types.Geography(geometry_type='POINT', srid=4326), nullable=False),
        sa.Column('boundary_geojson', postgresql.JSONB(), nullable=True),
        sa.Column('boundary_geometry', geoalchemy2.types.Geography(geometry_type='POLYGON', srid=4326), nullable=True),
        
        # Address
        sa.Column('address', sa.String(length=500), nullable=True),
        sa.Column('county', sa.String(length=100), nullable=True),
        sa.Column('sub_county', sa.String(length=100), nullable=True),
        sa.Column('ward', sa.String(length=100), nullable=True),
        sa.Column('village', sa.String(length=100), nullable=True),
        
        # Size
        sa.Column('size_acres', sa.Float(), nullable=False),
        sa.Column('size_hectares', sa.Float(), nullable=True),
        sa.Column('cultivated_area_acres', sa.Float(), nullable=True),
        
        # Farm type
        sa.Column('farm_type', sa.String(length=50), nullable=True),
        sa.Column('primary_crop', sa.String(length=100), nullable=True),
        sa.Column('secondary_crops', postgresql.ARRAY(sa.String()), default=list),
        
        # Soil
        sa.Column('soil_type', sa.String(length=100), nullable=True),
        sa.Column('soil_ph', sa.Float(), nullable=True),
        sa.Column('soil_health_score', sa.Float(), nullable=True),
        
        # Climate
        sa.Column('climate_zone', sa.String(length=50), nullable=True),
        sa.Column('average_rainfall_mm', sa.Float(), nullable=True),
        sa.Column('average_temperature_c', sa.Float(), nullable=True),
        
        # Water
        sa.Column('water_source', sa.String(length=100), nullable=True),
        sa.Column('irrigation_type', sa.String(length=100), nullable=True),
        sa.Column('has_irrigation', sa.Boolean(), default=False),
        
        # Certifications
        sa.Column('organic_certified', sa.Boolean(), default=False),
        sa.Column('global_gap_certified', sa.Boolean(), default=False),
        sa.Column('certifications', postgresql.ARRAY(sa.String()), default=list),
        
        # Ownership
        sa.Column('ownership_type', sa.String(length=50), nullable=True),
        sa.Column('title_deed_number', sa.String(length=100), nullable=True),
        
        # Images
        sa.Column('photos', postgresql.ARRAY(sa.String()), default=list),
        sa.Column('thumbnail_url', sa.String(length=500), nullable=True),
        
        # Status
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('verification_status', sa.String(length=50), default='pending'),
        
        # Metadata
        sa.Column('metadata', postgresql.JSONB(), default=dict),
        
        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_deleted', sa.Boolean(), default=False),
        sa.Column('version', sa.Integer(), default=1),
        
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('uuid'),
        sa.CheckConstraint('size_acres > 0'),
        sa.CheckConstraint('soil_ph IS NULL OR (soil_ph >= 0 AND soil_ph <= 14)')
    )
    
    op.create_index('idx_farm_user', 'farms', ['user_id'])
    op.create_index('idx_farm_location', 'farms', ['location'], postgresql_using='gist')
    op.create_index('idx_farm_county', 'farms', ['county'])
    op.create_index('idx_farm_active', 'farms', ['is_active'])
    op.create_index('idx_farm_name_trgm', 'farms', ['name'], postgresql_using='gin', postgresql_ops={'name': 'gin_trgm_ops'})
    
    # Fields table
    op.create_table(
        'fields',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('uuid', postgresql.UUID(as_uuid=True), server_default=sa.text('uuid_generate_v4()'), nullable=False),
        sa.Column('farm_id', sa.Integer(), nullable=False),
        
        # Details
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('field_code', sa.String(length=50), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        
        # Location
        sa.Column('boundary_geojson', postgresql.JSONB(), nullable=True),
        sa.Column('boundary_geometry', geoalchemy2.types.Geography(geometry_type='POLYGON', srid=4326), nullable=True),
        sa.Column('centroid', geoalchemy2.types.Geography(geometry_type='POINT', srid=4326), nullable=True),
        
        # Size
        sa.Column('size_acres', sa.Float(), nullable=False),
        sa.Column('size_hectares', sa.Float(), nullable=True),
        
        # Soil
        sa.Column('soil_type', sa.String(length=100), nullable=True),
        sa.Column('soil_ph', sa.Float(), nullable=True),
        
        # Status
        sa.Column('is_active', sa.Boolean(), default=True),
        
        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_deleted', sa.Boolean(), default=False),
        
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['farm_id'], ['farms.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('uuid'),
        sa.CheckConstraint('size_acres > 0')
    )
    
    op.create_index('idx_field_farm', 'fields', ['farm_id'])
    op.create_index('idx_field_boundary', 'fields', ['boundary_geometry'], postgresql_using='gist')
    
    # Crop Plantings table
    op.create_table(
        'crop_plantings',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('uuid', postgresql.UUID(as_uuid=True), server_default=sa.text('uuid_generate_v4()'), nullable=False),
        sa.Column('farm_id', sa.Integer(), nullable=False),
        sa.Column('field_id', sa.Integer(), nullable=True),
        sa.Column('user_id', sa.Integer(), nullable=False),
        
        # Crop details
        sa.Column('crop_name', sa.String(length=100), nullable=False),
        sa.Column('crop_variety', sa.String(length=100), nullable=True),
        sa.Column('crop_category', sa.String(length=50), nullable=True),
        
        # Planting
        sa.Column('planting_date', sa.Date(), nullable=False),
        sa.Column('planting_method', sa.String(length=100), nullable=True),
        sa.Column('seed_source', sa.String(length=200), nullable=True),
        sa.Column('seed_batch', sa.String(length=100), nullable=True),
        
        # Area
        sa.Column('area_planted_acres', sa.Float(), nullable=False),
        sa.Column('plant_population', sa.Integer(), nullable=True),
        sa.Column('row_spacing_cm', sa.Float(), nullable=True),
        sa.Column('plant_spacing_cm', sa.Float(), nullable=True),
        
        # Growth stage
        sa.Column('current_growth_stage', sa.String(length=50), nullable=True),
        sa.Column('growth_stage_updated_at', sa.DateTime(timezone=True), nullable=True),
        
        # Expected harvest
        sa.Column('expected_harvest_date', sa.Date(), nullable=True),
        sa.Column('expected_yield_kg', sa.Float(), nullable=True),
        
        # Actual harvest
        sa.Column('actual_harvest_date', sa.Date(), nullable=True),
        sa.Column('actual_yield_kg', sa.Float(), nullable=True),
        sa.Column('quality_grade', sa.String(length=20), nullable=True),
        
        # Health
        sa.Column('health_status', sa.String(length=50), default='healthy'),
        sa.Column('disease_history', postgresql.JSONB(), default=list),
        sa.Column('pest_history', postgresql.JSONB(), default=list),
        
        # Cost tracking
        sa.Column('total_cost_ksh', sa.DECIMAL(12, 2), default=0),
        sa.Column('revenue_ksh', sa.DECIMAL(12, 2), default=0),
        sa.Column('profit_ksh', sa.DECIMAL(12, 2), default=0),
        
        # Status
        sa.Column('status', sa.String(length=50), default='active'),
        sa.Column('is_active', sa.Boolean(), default=True),
        
        # Notes
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('photos', postgresql.ARRAY(sa.String()), default=list),
        
        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_deleted', sa.Boolean(), default=False),
        
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['farm_id'], ['farms.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['field_id'], ['fields.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('uuid'),
        sa.CheckConstraint('area_planted_acres > 0')
    )
    
    op.create_index('idx_planting_farm', 'crop_plantings', ['farm_id'])
    op.create_index('idx_planting_user', 'crop_plantings', ['user_id'])
    op.create_index('idx_planting_status', 'crop_plantings', ['status'])
    op.create_index('idx_planting_dates', 'crop_plantings', ['planting_date', 'expected_harvest_date'])
    
    # ========================================================================
    # DIAGNOSIS SYSTEM TABLES
    # ========================================================================
    
    # Diseases table
    op.create_table(
        'diseases',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('uuid', postgresql.UUID(as_uuid=True), server_default=sa.text('uuid_generate_v4()'), nullable=False),
        
        # Basic info
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('scientific_name', sa.String(length=200), nullable=True),
        sa.Column('common_names', postgresql.ARRAY(sa.String()), default=list),
        sa.Column('disease_code', sa.String(length=50), nullable=True),
        
        # Classification
        sa.Column('category', sa.String(length=100), nullable=True),
        sa.Column('pathogen_type', sa.String(length=50), nullable=True),
        sa.Column('affected_crops', postgresql.ARRAY(sa.String()), default=list),
        
        # Description
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('symptoms', postgresql.JSONB(), default=list),
        sa.Column('causes', postgresql.JSONB(), default=list),
        
        # Impact
        sa.Column('severity_level', sa.String(length=20), default='medium'),
        sa.Column('spread_rate', sa.String(length=20), nullable=True),
        sa.Column('yield_loss_percentage', sa.Float(), nullable=True),
        
        # Prevention & treatment
        sa.Column('prevention_methods', postgresql.JSONB(), default=list),
        sa.Column('treatment_methods', postgresql.JSONB(), default=list),
        sa.Column('organic_treatments', postgresql.JSONB(), default=list),
        sa.Column('chemical_treatments', postgresql.JSONB(), default=list),
        
        # Environmental conditions
        sa.Column('favorable_conditions', postgresql.JSONB(), default=dict),
        sa.Column('temperature_range_min', sa.Float(), nullable=True),
        sa.Column('temperature_range_max', sa.Float(), nullable=True),
        sa.Column('humidity_range_min', sa.Float(), nullable=True),
        sa.Column('humidity_range_max', sa.Float(), nullable=True),
        
        # Images
        sa.Column('reference_images', postgresql.ARRAY(sa.String()), default=list),
        sa.Column('thumbnail_url', sa.String(length=500), nullable=True),
        
        # Status
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('verification_status', sa.String(length=50), default='verified'),
        
        # Metadata
        sa.Column('metadata', postgresql.JSONB(), default=dict),
        sa.Column('tags', postgresql.ARRAY(sa.String()), default=list),
        
        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_deleted', sa.Boolean(), default=False),
        
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('uuid'),
        sa.UniqueConstraint('disease_code')
    )
    
    op.create_index('idx_disease_name', 'diseases', ['name'])
    op.create_index('idx_disease_category', 'diseases', ['category'])
    op.create_index('idx_disease_name_trgm', 'diseases', ['name'], postgresql_using='gin', postgresql_ops={'name': 'gin_trgm_ops'})
    
    # Diagnoses table
    op.create_table(
        'diagnoses',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('uuid', postgresql.UUID(as_uuid=True), server_default=sa.text('uuid_generate_v4()'), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('farm_id', sa.Integer(), nullable=True),
        sa.Column('crop_planting_id', sa.Integer(), nullable=True),
        
        # Image details
        sa.Column('image_url', sa.String(length=500), nullable=False),
        sa.Column('image_storage_path', sa.String(length=500), nullable=True),
        sa.Column('thumbnail_url', sa.String(length=500), nullable=True),
        sa.Column('image_metadata', postgresql.JSONB(), default=dict),
        
        # Location
        sa.Column('latitude', sa.Float(), nullable=True),
        sa.Column('longitude', sa.Float(), nullable=True),
        sa.Column('location', geoalchemy2.types.Geography(geometry_type='POINT', srid=4326), nullable=True),
        
        # User input
        sa.Column('crop_type', sa.String(length=100), nullable=True),
        sa.Column('symptoms_description', sa.Text(), nullable=True),
        sa.Column('additional_context', sa.Text(), nullable=True),
        
        # AI Analysis
        sa.Column('ai_model_version', sa.String(length=50), nullable=True),
        sa.Column('ai_confidence_score', sa.Float(), nullable=True),
        sa.Column('ai_processing_time_ms', sa.Integer(), nullable=True),
        sa.Column('ai_diagnosis_result', postgresql.JSONB(), nullable=True),
        sa.Column('detected_diseases', postgresql.ARRAY(sa.String()), default=list),
        sa.Column('detected_pests', postgresql.ARRAY(sa.String()), default=list),
        
        # Primary diagnosis
        sa.Column('primary_disease_id', sa.Integer(), nullable=True),
        sa.Column('primary_diagnosis', sa.String(length=200), nullable=True),
        sa.Column('confidence_level', sa.String(length=20), nullable=True),
        sa.Column('severity_level', sa.String(length=20), nullable=True),
        
        # Secondary possibilities
        sa.Column('secondary_diagnoses', postgresql.JSONB(), default=list),
        
        # Recommendations
        sa.Column('treatment_recommendations', postgresql.JSONB(), default=list),
        sa.Column('prevention_recommendations', postgresql.JSONB(), default=list),
        sa.Column('urgent_action_required', sa.Boolean(), default=False),
        
        # Expert review
        sa.Column('expert_reviewed', sa.Boolean(), default=False),
        sa.Column('expert_review_notes', sa.Text(), nullable=True),
        sa.Column('expert_confidence_score', sa.Float(), nullable=True),
        sa.Column('expert_diagnosis', sa.String(length=200), nullable=True),
        
        # Follow-up
        sa.Column('follow_up_required', sa.Boolean(), default=False),
        sa.Column('follow_up_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('follow_up_notes', sa.Text(), nullable=True),
        
        # Status tracking
        sa.Column('status', sa.String(length=50), default='pending'),
        sa.Column('priority', sa.String(length=20), default='normal'),
        sa.Column('resolution_status', sa.String(length=50), nullable=True),
        
        # Timing
        sa.Column('submitted_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('processed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        
        # Feedback
        sa.Column('user_rating', sa.Integer(), nullable=True),
        sa.Column('user_feedback', sa.Text(), nullable=True),
        sa.Column('treatment_effectiveness', sa.String(length=50), nullable=True),
        
        # Metadata
        sa.Column('metadata', postgresql.JSONB(), default=dict),
        sa.Column('tags', postgresql.ARRAY(sa.String()), default=list),
        
        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_deleted', sa.Boolean(), default=False),
        
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['farm_id'], ['farms.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['crop_planting_id'], ['crop_plantings.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['primary_disease_id'], ['diseases.id'], ondelete='SET NULL'),
        sa.UniqueConstraint('uuid'),
        sa.CheckConstraint('ai_confidence_score IS NULL OR (ai_confidence_score >= 0 AND ai_confidence_score <= 1)'),
        sa.CheckConstraint('user_rating IS NULL OR (user_rating >= 1 AND user_rating <= 5)')
    )
    
    op.create_index('idx_diagnosis_user', 'diagnoses', ['user_id'])
    op.create_index('idx_diagnosis_farm', 'diagnoses', ['farm_id'])
    op.create_index('idx_diagnosis_status', 'diagnoses', ['status'])
    op.create_index('idx_diagnosis_created', 'diagnoses', ['created_at'])
    op.create_index('idx_diagnosis_priority_status', 'diagnoses', ['priority', 'status'])
    
    # Treatments table
    op.create_table(
        'treatments',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('uuid', postgresql.UUID(as_uuid=True), server_default=sa.text('uuid_generate_v4()'), nullable=False),
        sa.Column('diagnosis_id', sa.Integer(), nullable=False),
        sa.Column('disease_id', sa.Integer(), nullable=True),
        
        # Treatment details
        sa.Column('treatment_name', sa.String(length=200), nullable=False),
        sa.Column('treatment_type', sa.String(length=50), nullable=True),
        sa.Column('treatment_category', sa.String(length=50), nullable=True),
        
        # Description
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('instructions', sa.Text(), nullable=True),
        sa.Column('dosage', sa.String(length=200), nullable=True),
        sa.Column('application_method', sa.String(length=100), nullable=True),
        
        # Products
        sa.Column('recommended_products', postgresql.JSONB(), default=list),
        sa.Column('alternative_products', postgresql.JSONB(), default=list),
        
        # Timing
        sa.Column('start_date', sa.Date(), nullable=True),
        sa.Column('end_date', sa.Date(), nullable=True),
        sa.Column('duration_days', sa.Integer(), nullable=True),
        sa.Column('frequency', sa.String(length=100), nullable=True),
        
        # Cost
        sa.Column('estimated_cost_ksh', sa.DECIMAL(10, 2), nullable=True),
        sa.Column('actual_cost_ksh', sa.DECIMAL(10, 2), nullable=True),
        
        # Effectiveness
        sa.Column('expected_effectiveness', sa.String(length=50), nullable=True),
        sa.Column('actual_effectiveness', sa.String(length=50), nullable=True),
        sa.Column('effectiveness_notes', sa.Text(), nullable=True),
        
        # Safety
        sa.Column('safety_precautions', postgresql.JSONB(), default=list),
        sa.Column('pre_harvest_interval_days', sa.Integer(), nullable=True),
        sa.Column('re_entry_interval_hours', sa.Integer(), nullable=True),
        
        # Status
        sa.Column('status', sa.String(length=50), default='recommended'),
        sa.Column('compliance_status', sa.String(length=50), nullable=True),
        
        # Metadata
        sa.Column('metadata', postgresql.JSONB(), default=dict),
        
        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_deleted', sa.Boolean(), default=False),
        
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['diagnosis_id'], ['diagnoses.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['disease_id'], ['diseases.id'], ondelete='SET NULL'),
        sa.UniqueConstraint('uuid')
    )
    
    op.create_index('idx_treatment_diagnosis', 'treatments', ['diagnosis_id'])
    op.create_index('idx_treatment_status', 'treatments', ['status'])
    
    # Treatment Applications table
    op.create_table(
        'treatment_applications',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('uuid', postgresql.UUID(as_uuid=True), server_default=sa.text('uuid_generate_v4()'), nullable=False),
        sa.Column('treatment_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        
        # Application details
        sa.Column('application_date', sa.DateTime(timezone=True), nullable=False),
        sa.Column('application_method', sa.String(length=100), nullable=True),
        sa.Column('product_used', sa.String(length=200), nullable=True),
        sa.Column('quantity_used', sa.String(length=100), nullable=True),
        sa.Column('area_covered_acres', sa.Float(), nullable=True),
        
        # Conditions
        sa.Column('weather_conditions', sa.String(length=200), nullable=True),
        sa.Column('temperature_c', sa.Float(), nullable=True),
        sa.Column('humidity_percent', sa.Float(), nullable=True),
        sa.Column('wind_speed_kmh', sa.Float(), nullable=True),
        
        # Cost
        sa.Column('cost_ksh', sa.DECIMAL(10, 2), nullable=True),
        
        # Notes
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('photos', postgresql.ARRAY(sa.String()), default=list),
        
        # Effectiveness
        sa.Column('effectiveness_rating', sa.Integer(), nullable=True),
        sa.Column('side_effects_observed', sa.Boolean(), default=False),
        sa.Column('side_effects_description', sa.Text(), nullable=True),
        
        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['treatment_id'], ['treatments.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('uuid'),
        sa.CheckConstraint('effectiveness_rating IS NULL OR (effectiveness_rating >= 1 AND effectiveness_rating <= 5)')
    )
    
    op.create_index('idx_application_treatment', 'treatment_applications', ['treatment_id'])
    op.create_index('idx_application_date', 'treatment_applications', ['application_date'])
    
    # ========================================================================
    # PRODUCTS & SUPPLIERS TABLES
    # ========================================================================
    
    # Products table
    op.create_table(
        'products',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('uuid', postgresql.UUID(as_uuid=True), server_default=sa.text('uuid_generate_v4()'), nullable=False),
        
        # Basic details
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('brand', sa.String(length=100), nullable=True),
        sa.Column('product_code', sa.String(length=100), nullable=True),
        sa.Column('barcode', sa.String(length=100), nullable=True),
        
        # Category
        sa.Column('category', sa.String(length=100), nullable=False),
        sa.Column('subcategory', sa.String(length=100), nullable=True),
        sa.Column('product_type', sa.String(length=50), nullable=True),
        
        # Description
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('usage_instructions', sa.Text(), nullable=True),
        sa.Column('specifications', postgresql.JSONB(), default=dict),
        
        # Pricing
        sa.Column('unit_price_ksh', sa.DECIMAL(10, 2), nullable=False),
        sa.Column('unit_of_measure', sa.String(length=50), nullable=True),
        sa.Column('bulk_pricing', postgresql.JSONB(), default=list),
        
        # Chemical (for pesticides/fertilizers)
        sa.Column('active_ingredients', postgresql.JSONB(), default=list),
        sa.Column('concentration', sa.String(length=100), nullable=True),
        sa.Column('pcpb_registration', sa.String(length=100), nullable=True),
        
        # Safety
        sa.Column('safety_rating', sa.String(length=20), nullable=True),
        sa.Column('safety_precautions', postgresql.JSONB(), default=list),
        sa.Column('pre_harvest_interval_days', sa.Integer(), nullable=True),
        
        # Certification
        sa.Column('organic_certified', sa.Boolean(), default=False),
        sa.Column('certifications', postgresql.ARRAY(sa.String()), default=list),
        
        # Images
        sa.Column('images', postgresql.ARRAY(sa.String()), default=list),
        sa.Column('thumbnail_url', sa.String(length=500), nullable=True),
        
        # Inventory
        sa.Column('in_stock', sa.Boolean(), default=True),
        sa.Column('stock_quantity', sa.Integer(), default=0),
        
        # Ratings
        sa.Column('average_rating', sa.Float(), default=0.0),
        sa.Column('review_count', sa.Integer(), default=0),
        
        # Status
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('is_featured', sa.Boolean(), default=False),
        
        # Metadata
        sa.Column('metadata', postgresql.JSONB(), default=dict),
        sa.Column('tags', postgresql.ARRAY(sa.String()), default=list),
        
        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_deleted', sa.Boolean(), default=False),
        
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('uuid'),
        sa.UniqueConstraint('product_code'),
        sa.CheckConstraint('unit_price_ksh >= 0'),
        sa.CheckConstraint('average_rating >= 0 AND average_rating <= 5')
    )
    
    op.create_index('idx_product_category', 'products', ['category'])
    op.create_index('idx_product_name_trgm', 'products', ['name'], postgresql_using='gin', postgresql_ops={'name': 'gin_trgm_ops'})
    op.create_index('idx_product_active', 'products', ['is_active'])
    
    # Suppliers table
    op.create_table(
        'suppliers',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('uuid', postgresql.UUID(as_uuid=True), server_default=sa.text('uuid_generate_v4()'), nullable=False),
        
        # Basic details
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('business_name', sa.String(length=200), nullable=True),
        sa.Column('registration_number', sa.String(length=100), nullable=True),
        
        # Contact
        sa.Column('email', sa.String(length=255), nullable=True),
        sa.Column('phone_number', sa.String(length=20), nullable=False),
        sa.Column('alternate_phone', sa.String(length=20), nullable=True),
        sa.Column('website', sa.String(length=255), nullable=True),
        
        # Address
        sa.Column('address', sa.String(length=500), nullable=True),
        sa.Column('city', sa.String(length=100), nullable=True),
        sa.Column('county', sa.String(length=100), nullable=True),
        sa.Column('country', sa.String(length=100), default='Kenya'),
        
        # Location
        sa.Column('latitude', sa.Float(), nullable=True),
        sa.Column('longitude', sa.Float(), nullable=True),
        sa.Column('location', geoalchemy2.types.Geography(geometry_type='POINT', srid=4326), nullable=True),
        
        # Business details
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('categories', postgresql.ARRAY(sa.String()), default=list),
        sa.Column('delivery_areas', postgresql.ARRAY(sa.String()), default=list),
        
        # Ratings
        sa.Column('average_rating', sa.Float(), default=0.0),
        sa.Column('review_count', sa.Integer(), default=0),
        
        # Status
        sa.Column('is_verified', sa.Boolean(), default=False),
        sa.Column('is_active', sa.Boolean(), default=True),
        
        # Metadata
        sa.Column('metadata', postgresql.JSONB(), default=dict),
        
        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_deleted', sa.Boolean(), default=False),
        
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('uuid'),
        sa.UniqueConstraint('email'),
        sa.CheckConstraint('average_rating >= 0 AND average_rating <= 5')
    )
    
    op.create_index('idx_supplier_county', 'suppliers', ['county'])
    op.create_index('idx_supplier_active', 'suppliers', ['is_active'])
    
    # Product-Supplier Association table
    op.create_table(
        'product_supplier_association',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('product_id', sa.Integer(), nullable=False),
        sa.Column('supplier_id', sa.Integer(), nullable=False),
        sa.Column('supplier_price_ksh', sa.DECIMAL(10, 2), nullable=True),
        sa.Column('is_available', sa.Boolean(), default=True),
        sa.Column('lead_time_days', sa.Integer(), nullable=True),
        sa.Column('minimum_order_quantity', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['product_id'], ['products.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['supplier_id'], ['suppliers.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('product_id', 'supplier_id')
    )
    
    op.create_index('idx_product_supplier_product', 'product_supplier_association', ['product_id'])
    op.create_index('idx_product_supplier_supplier', 'product_supplier_association', ['supplier_id'])
    
    # ========================================================================
    # DIGITAL CHAMA (COOPERATIVE) TABLES
    # ========================================================================
    
    # Chamas table
    op.create_table(
        'chamas',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('uuid', postgresql.UUID(as_uuid=True), server_default=sa.text('uuid_generate_v4()'), nullable=False),
        sa.Column('created_by_id', sa.Integer(), nullable=False),
        
        # Basic details
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('registration_number', sa.String(length=100), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        
        # Type
        sa.Column('chama_type', sa.String(length=50), nullable=True),
        sa.Column('purpose', sa.String(length=200), nullable=True),
        
        # Membership
        sa.Column('member_count', sa.Integer(), default=0),
        sa.Column('max_members', sa.Integer(), nullable=True),
        sa.Column('membership_fee_ksh', sa.DECIMAL(10, 2), default=0),
        
        # Contribution rules
        sa.Column('contribution_amount_ksh', sa.DECIMAL(10, 2), nullable=True),
        sa.Column('contribution_frequency', sa.String(length=50), nullable=True),
        sa.Column('contribution_day', sa.Integer(), nullable=True),
        
        # Financial summary
        sa.Column('total_contributions_ksh', sa.DECIMAL(15, 2), default=0),
        sa.Column('total_loans_issued_ksh', sa.DECIMAL(15, 2), default=0),
        sa.Column('total_loans_repaid_ksh', sa.DECIMAL(15, 2), default=0),
        sa.Column('available_funds_ksh', sa.DECIMAL(15, 2), default=0),
        sa.Column('pending_loans_ksh', sa.DECIMAL(15, 2), default=0),
        
        # Meeting schedule
        sa.Column('meeting_frequency', sa.String(length=50), nullable=True),
        sa.Column('meeting_day', sa.String(length=20), nullable=True),
        sa.Column('meeting_time', sa.Time(), nullable=True),
        sa.Column('meeting_location', sa.String(length=500), nullable=True),
        sa.Column('next_meeting_date', sa.DateTime(timezone=True), nullable=True),
        
        # Rules and policies
        sa.Column('rules', postgresql.JSONB(), default=dict),
        sa.Column('loan_policy', postgresql.JSONB(), default=dict),
        sa.Column('interest_rate_percent', sa.Float(), nullable=True),
        sa.Column('late_payment_penalty_percent', sa.Float(), nullable=True),
        
        # Contact
        sa.Column('contact_person', sa.String(length=200), nullable=True),
        sa.Column('contact_phone', sa.String(length=20), nullable=True),
        sa.Column('contact_email', sa.String(length=255), nullable=True),
        
        # Location
        sa.Column('county', sa.String(length=100), nullable=True),
        sa.Column('sub_county', sa.String(length=100), nullable=True),
        
        # Images
        sa.Column('logo_url', sa.String(length=500), nullable=True),
        sa.Column('banner_url', sa.String(length=500), nullable=True),
        
        # Status
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('is_verified', sa.Boolean(), default=False),
        sa.Column('verification_date', sa.DateTime(timezone=True), nullable=True),
        
        # Metadata
        sa.Column('metadata', postgresql.JSONB(), default=dict),
        
        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_deleted', sa.Boolean(), default=False),
        
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['created_by_id'], ['users.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('uuid'),
        sa.UniqueConstraint('registration_number'),
        sa.CheckConstraint('member_count >= 0'),
        sa.CheckConstraint('interest_rate_percent IS NULL OR interest_rate_percent >= 0')
    )
    
    op.create_index('idx_chama_county', 'chamas', ['county'])
    op.create_index('idx_chama_active', 'chamas', ['is_active'])
    op.create_index('idx_chama_name_trgm', 'chamas', ['name'], postgresql_using='gin', postgresql_ops={'name': 'gin_trgm_ops'})
    
    # User-Chama Association table
    op.create_table(
        'user_chama_association',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('chama_id', sa.Integer(), nullable=False),
        
        # Membership details
        sa.Column('role', sa.String(length=50), default='member'),
        sa.Column('joined_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('is_active', sa.Boolean(), default=True),
        
        # Contributions
        sa.Column('total_contributed_ksh', sa.DECIMAL(12, 2), default=0),
        sa.Column('last_contribution_at', sa.DateTime(timezone=True), nullable=True),
        
        # Loans
        sa.Column('total_borrowed_ksh', sa.DECIMAL(12, 2), default=0),
        sa.Column('total_repaid_ksh', sa.DECIMAL(12, 2), default=0),
        sa.Column('outstanding_loan_ksh', sa.DECIMAL(12, 2), default=0),
        
        # Status
        sa.Column('status', sa.String(length=50), default='active'),
        sa.Column('left_at', sa.DateTime(timezone=True), nullable=True),
        
        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['chama_id'], ['chamas.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('user_id', 'chama_id')
    )
    
    op.create_index('idx_user_chama_user', 'user_chama_association', ['user_id'])
    op.create_index('idx_user_chama_chama', 'user_chama_association', ['chama_id'])
    
    # Transactions table
    op.create_table(
        'transactions',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('uuid', postgresql.UUID(as_uuid=True), server_default=sa.text('uuid_generate_v4()'), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('chama_id', sa.Integer(), nullable=True),
        
        # Transaction details
        sa.Column('transaction_type', sa.String(length=50), nullable=False),
        sa.Column('category', sa.String(length=50), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        
        # Amount
        sa.Column('amount_ksh', sa.DECIMAL(12, 2), nullable=False),
        sa.Column('currency', sa.String(length=10), default='KES'),
        
        # Payment method
        sa.Column('payment_method', sa.String(length=50), nullable=False),
        sa.Column('payment_reference', sa.String(length=200), nullable=True),
        
        # M-Pesa specific
        sa.Column('mpesa_receipt', sa.String(length=100), nullable=True),
        sa.Column('mpesa_phone', sa.String(length=20), nullable=True),
        sa.Column('mpesa_transaction_date', sa.DateTime(timezone=True), nullable=True),
        
        # Bank specific
        sa.Column('bank_name', sa.String(length=100), nullable=True),
        sa.Column('account_number', sa.String(length=50), nullable=True),
        
        # Status
        sa.Column('status', sa.String(length=50), default='pending'),
        sa.Column('processed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('failed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('failure_reason', sa.Text(), nullable=True),
        
        # Balances
        sa.Column('balance_before_ksh', sa.DECIMAL(12, 2), nullable=True),
        sa.Column('balance_after_ksh', sa.DECIMAL(12, 2), nullable=True),
        
        # Related entities
        sa.Column('related_transaction_id', sa.Integer(), nullable=True),
        sa.Column('loan_id', sa.Integer(), nullable=True),
        
        # Metadata
        sa.Column('metadata', postgresql.JSONB(), default=dict),
        
        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_deleted', sa.Boolean(), default=False),
        
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['chama_id'], ['chamas.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['related_transaction_id'], ['transactions.id'], ondelete='SET NULL'),
        sa.UniqueConstraint('uuid'),
        sa.CheckConstraint('amount_ksh > 0')
    )
    
    op.create_index('idx_transaction_user', 'transactions', ['user_id'])
    op.create_index('idx_transaction_chama', 'transactions', ['chama_id'])
    op.create_index('idx_transaction_type_status', 'transactions', ['transaction_type', 'status'])
    op.create_index('idx_transaction_created', 'transactions', ['created_at'])
    op.create_index('idx_transaction_mpesa', 'transactions', ['mpesa_receipt'])
    
    # Loans table
    op.create_table(
        'loans',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('uuid', postgresql.UUID(as_uuid=True), server_default=sa.text('uuid_generate_v4()'), nullable=False),
        sa.Column('chama_id', sa.Integer(), nullable=False),
        sa.Column('borrower_id', sa.Integer(), nullable=False),
        
        # Loan details
        sa.Column('loan_number', sa.String(length=50), nullable=True),
        sa.Column('purpose', sa.String(length=200), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        
        # Amount
        sa.Column('principal_amount_ksh', sa.DECIMAL(12, 2), nullable=False),
        sa.Column('interest_rate_percent', sa.Float(), nullable=False),
        sa.Column('total_interest_ksh', sa.DECIMAL(12, 2), nullable=True),
        sa.Column('total_amount_ksh', sa.DECIMAL(12, 2), nullable=False),
        
        # Repayment
        sa.Column('repayment_period_months', sa.Integer(), nullable=False),
        sa.Column('repayment_frequency', sa.String(length=50), default='monthly'),
        sa.Column('installment_amount_ksh', sa.DECIMAL(12, 2), nullable=True),
        
        # Dates
        sa.Column('disbursement_date', sa.Date(), nullable=True),
        sa.Column('first_payment_date', sa.Date(), nullable=True),
        sa.Column('due_date', sa.Date(), nullable=True),
        sa.Column('last_payment_date', sa.Date(), nullable=True),
        
        # Balances
        sa.Column('amount_repaid_ksh', sa.DECIMAL(12, 2), default=0),
        sa.Column('balance_outstanding_ksh', sa.DECIMAL(12, 2), nullable=True),
        sa.Column('penalty_amount_ksh', sa.DECIMAL(12, 2), default=0),
        
        # Status
        sa.Column('status', sa.String(length=50), default='pending_approval'),
        sa.Column('approval_status', sa.String(length=50), default='pending'),
        sa.Column('approved_by_id', sa.Integer(), nullable=True),
        sa.Column('approved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('disbursed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        
        # Guarantors
        sa.Column('guarantor1_id', sa.Integer(), nullable=True),
        sa.Column('guarantor2_id', sa.Integer(), nullable=True),
        sa.Column('guarantor1_approved', sa.Boolean(), default=False),
        sa.Column('guarantor2_approved', sa.Boolean(), default=False),
        
        # Risk assessment
        sa.Column('risk_score', sa.Float(), nullable=True),
        sa.Column('credit_score', sa.Float(), nullable=True),
        sa.Column('default_risk', sa.String(length=20), nullable=True),
        
        # Notes
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('rejection_reason', sa.Text(), nullable=True),
        
        # Metadata
        sa.Column('metadata', postgresql.JSONB(), default=dict),
        
        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_deleted', sa.Boolean(), default=False),
        
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['chama_id'], ['chamas.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['borrower_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['approved_by_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['guarantor1_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['guarantor2_id'], ['users.id'], ondelete='SET NULL'),
        sa.UniqueConstraint('uuid'),
        sa.UniqueConstraint('loan_number'),
        sa.CheckConstraint('principal_amount_ksh > 0'),
        sa.CheckConstraint('interest_rate_percent >= 0'),
        sa.CheckConstraint('repayment_period_months > 0')
    )
    
    op.create_index('idx_loan_chama', 'loans', ['chama_id'])
    op.create_index('idx_loan_borrower', 'loans', ['borrower_id'])
    op.create_index('idx_loan_status', 'loans', ['status'])
    op.create_index('idx_loan_due_date', 'loans', ['due_date'])
    
    # Loan Repayments table
    op.create_table(
        'loan_repayments',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('uuid', postgresql.UUID(as_uuid=True), server_default=sa.text('uuid_generate_v4()'), nullable=False),
        sa.Column('loan_id', sa.Integer(), nullable=False),
        sa.Column('transaction_id', sa.Integer(), nullable=True),
        
        # Payment details
        sa.Column('payment_number', sa.Integer(), nullable=False),
        sa.Column('due_date', sa.Date(), nullable=False),
        sa.Column('payment_date', sa.Date(), nullable=True),
        
        # Amounts
        sa.Column('principal_amount_ksh', sa.DECIMAL(12, 2), nullable=False),
        sa.Column('interest_amount_ksh', sa.DECIMAL(12, 2), nullable=False),
        sa.Column('penalty_amount_ksh', sa.DECIMAL(12, 2), default=0),
        sa.Column('total_amount_ksh', sa.DECIMAL(12, 2), nullable=False),
        sa.Column('amount_paid_ksh', sa.DECIMAL(12, 2), default=0),
        
        # Status
        sa.Column('status', sa.String(length=50), default='pending'),
        sa.Column('is_late', sa.Boolean(), default=False),
        sa.Column('days_late', sa.Integer(), default=0),
        
        # Notes
        sa.Column('notes', sa.Text(), nullable=True),
        
        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['loan_id'], ['loans.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['transaction_id'], ['transactions.id'], ondelete='SET NULL'),
        sa.UniqueConstraint('uuid'),
        sa.CheckConstraint('total_amount_ksh > 0')
    )
    
    op.create_index('idx_repayment_loan', 'loan_repayments', ['loan_id'])
    op.create_index('idx_repayment_status_date', 'loan_repayments', ['status', 'due_date'])
    
    # Chama Meetings table
    op.create_table(
        'chama_meetings',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('uuid', postgresql.UUID(as_uuid=True), server_default=sa.text('uuid_generate_v4()'), nullable=False),
        sa.Column('chama_id', sa.Integer(), nullable=False),
        
        # Meeting details
        sa.Column('title', sa.String(length=200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('agenda', postgresql.JSONB(), default=list),
        
        # Timing
        sa.Column('scheduled_date', sa.DateTime(timezone=True), nullable=False),
        sa.Column('start_time', sa.DateTime(timezone=True), nullable=True),
        sa.Column('end_time', sa.DateTime(timezone=True), nullable=True),
        sa.Column('duration_minutes', sa.Integer(), nullable=True),
        
        # Location
        sa.Column('location', sa.String(length=500), nullable=True),
        sa.Column('meeting_type', sa.String(length=50), default='physical'),
        sa.Column('meeting_link', sa.String(length=500), nullable=True),
        
        # Attendance
        sa.Column('expected_attendees', sa.Integer(), nullable=True),
        sa.Column('actual_attendees', sa.Integer(), default=0),
        sa.Column('attendees', postgresql.ARRAY(sa.Integer()), default=list),
        sa.Column('absentees', postgresql.ARRAY(sa.Integer()), default=list),
        
        # Minutes
        sa.Column('minutes', sa.Text(), nullable=True),
        sa.Column('decisions', postgresql.JSONB(), default=list),
        sa.Column('action_items', postgresql.JSONB(), default=list),
        
        # Financial summary
        sa.Column('contributions_collected_ksh', sa.DECIMAL(12, 2), default=0),
        sa.Column('loans_approved_count', sa.Integer(), default=0),
        sa.Column('loans_approved_amount_ksh', sa.DECIMAL(12, 2), default=0),
        
        # Status
        sa.Column('status', sa.String(length=50), default='scheduled'),
        sa.Column('cancelled_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('cancellation_reason', sa.Text(), nullable=True),
        
        # Documents
        sa.Column('documents', postgresql.ARRAY(sa.String()), default=list),
        
        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['chama_id'], ['chamas.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('uuid')
    )
    
    op.create_index('idx_meeting_chama', 'chama_meetings', ['chama_id'])
    op.create_index('idx_meeting_date', 'chama_meetings', ['scheduled_date'])
    op.create_index('idx_meeting_status', 'chama_meetings', ['status'])
    
    # ========================================================================
    # IOT & SENSOR TABLES
    # ========================================================================
    
    # IoT Devices table
    op.create_table(
        'iot_devices',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('uuid', postgresql.UUID(as_uuid=True), server_default=sa.text('uuid_generate_v4()'), nullable=False),
        sa.Column('farm_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        
        # Device details
        sa.Column('device_name', sa.String(length=200), nullable=False),
        sa.Column('device_type', sa.String(length=50), nullable=False),
        sa.Column('device_model', sa.String(length=100), nullable=True),
        sa.Column('device_id', sa.String(length=100), nullable=False),
        sa.Column('mac_address', sa.String(length=50), nullable=True),
        
        # Capabilities
        sa.Column('capabilities', postgresql.ARRAY(sa.String()), default=list),
        sa.Column('sensor_types', postgresql.ARRAY(sa.String()), default=list),
        
        # Location
        sa.Column('latitude', sa.Float(), nullable=True),
        sa.Column('longitude', sa.Float(), nullable=True),
        sa.Column('location', geoalchemy2.types.Geography(geometry_type='POINT', srid=4326), nullable=True),
        sa.Column('installation_location', sa.String(length=200), nullable=True),
        
        # Network
        sa.Column('ip_address', sa.String(length=50), nullable=True),
        sa.Column('connection_type', sa.String(length=50), nullable=True),
        sa.Column('firmware_version', sa.String(length=50), nullable=True),
        
        # Status
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('is_online', sa.Boolean(), default=False),
        sa.Column('health_status', sa.String(length=50), default='good'),
        sa.Column('battery_level', sa.Float(), nullable=True),
        
        # Activity
        sa.Column('last_seen_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_reading_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('total_readings', sa.BigInteger(), default=0),
        
        # Installation
        sa.Column('installed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('installed_by', sa.String(length=200), nullable=True),
        
        # Maintenance
        sa.Column('last_maintenance_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('next_maintenance_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('maintenance_notes', sa.Text(), nullable=True),
        
        # Configuration
        sa.Column('configuration', postgresql.JSONB(), default=dict),
        sa.Column('reading_interval_seconds', sa.Integer(), default=300),
        
        # Metadata
        sa.Column('metadata', postgresql.JSONB(), default=dict),
        
        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_deleted', sa.Boolean(), default=False),
        
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['farm_id'], ['farms.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('uuid'),
        sa.UniqueConstraint('device_id'),
        sa.CheckConstraint('battery_level IS NULL OR (battery_level >= 0 AND battery_level <= 100)')
    )
    
    op.create_index('idx_device_farm', 'iot_devices', ['farm_id'])
    op.create_index('idx_device_type', 'iot_devices', ['device_type'])
    op.create_index('idx_device_status', 'iot_devices', ['is_online', 'health_status'])
    
    # Sensor Readings table
    op.create_table(
        'sensor_readings',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('uuid', postgresql.UUID(as_uuid=True), server_default=sa.text('uuid_generate_v4()'), nullable=False),
        sa.Column('device_id', sa.Integer(), nullable=False),
        
        # Reading details
        sa.Column('reading_type', sa.String(length=50), nullable=False),
        sa.Column('reading_value', sa.Float(), nullable=False),
        sa.Column('unit', sa.String(length=20), nullable=True),
        
        # Additional values
        sa.Column('temperature_c', sa.Float(), nullable=True),
        sa.Column('humidity_percent', sa.Float(), nullable=True),
        sa.Column('soil_moisture_percent', sa.Float(), nullable=True),
        sa.Column('soil_temperature_c', sa.Float(), nullable=True),
        sa.Column('rainfall_mm', sa.Float(), nullable=True),
        sa.Column('wind_speed_kmh', sa.Float(), nullable=True),
        sa.Column('wind_direction_degrees', sa.Float(), nullable=True),
        sa.Column('light_intensity_lux', sa.Float(), nullable=True),
        sa.Column('soil_ph', sa.Float(), nullable=True),
        sa.Column('soil_ec', sa.Float(), nullable=True),
        sa.Column('co2_ppm', sa.Float(), nullable=True),
        
        # Quality
        sa.Column('quality_score', sa.Float(), default=1.0),
        sa.Column('is_anomaly', sa.Boolean(), default=False),
        sa.Column('is_validated', sa.Boolean(), default=True),
        
        # Raw data
        sa.Column('raw_data', postgresql.JSONB(), nullable=True),
        
        # Timing
        sa.Column('reading_timestamp', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['device_id'], ['iot_devices.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('uuid')
    )
    
    op.create_index('idx_reading_device_time', 'sensor_readings', ['device_id', 'reading_timestamp'])
    op.create_index('idx_reading_type', 'sensor_readings', ['reading_type'])
    op.create_index('idx_reading_timestamp', 'sensor_readings', ['reading_timestamp'])
    
    # Weather Records table
    op.create_table(
        'weather_records',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('uuid', postgresql.UUID(as_uuid=True), server_default=sa.text('uuid_generate_v4()'), nullable=False),
        sa.Column('farm_id', sa.Integer(), nullable=True),
        sa.Column('device_id', sa.Integer(), nullable=True),
        
        # Location
        sa.Column('latitude', sa.Float(), nullable=False),
        sa.Column('longitude', sa.Float(), nullable=False),
        sa.Column('location', geoalchemy2.types.Geography(geometry_type='POINT', srid=4326), nullable=False),
        
        # Temperature
        sa.Column('temperature_c', sa.Float(), nullable=True),
        sa.Column('feels_like_c', sa.Float(), nullable=True),
        sa.Column('temperature_min_c', sa.Float(), nullable=True),
        sa.Column('temperature_max_c', sa.Float(), nullable=True),
        
        # Humidity & Pressure
        sa.Column('humidity_percent', sa.Float(), nullable=True),
        sa.Column('pressure_hpa', sa.Float(), nullable=True),
        
        # Wind
        sa.Column('wind_speed_kmh', sa.Float(), nullable=True),
        sa.Column('wind_direction_degrees', sa.Float(), nullable=True),
        sa.Column('wind_gust_kmh', sa.Float(), nullable=True),
        
        # Precipitation
        sa.Column('rainfall_mm', sa.Float(), nullable=True),
        sa.Column('rainfall_1h_mm', sa.Float(), nullable=True),
        sa.Column('rainfall_24h_mm', sa.Float(), nullable=True),
        
        # Cloud & Visibility
        sa.Column('cloud_cover_percent', sa.Float(), nullable=True),
        sa.Column('visibility_meters', sa.Float(), nullable=True),
        
        # UV & Solar
        sa.Column('uv_index', sa.Float(), nullable=True),
        sa.Column('solar_radiation', sa.Float(), nullable=True),
        
        # Conditions
        sa.Column('weather_condition', sa.String(length=100), nullable=True),
        sa.Column('weather_description', sa.String(length=200), nullable=True),
        sa.Column('weather_icon', sa.String(length=20), nullable=True),
        
        # Source
        sa.Column('data_source', sa.String(length=50), nullable=True),
        sa.Column('source_api', sa.String(length=100), nullable=True),
        
        # Raw data
        sa.Column('raw_data', postgresql.JSONB(), nullable=True),
        
        # Timing
        sa.Column('recorded_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['farm_id'], ['farms.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['device_id'], ['iot_devices.id'], ondelete='SET NULL'),
        sa.UniqueConstraint('uuid')
    )
    
    op.create_index('idx_weather_farm', 'weather_records', ['farm_id'])
    op.create_index('idx_weather_location', 'weather_records', ['location'], postgresql_using='gist')
    op.create_index('idx_weather_recorded', 'weather_records', ['recorded_at'])
    
    # Soil Tests table
    op.create_table(
        'soil_tests',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('uuid', postgresql.UUID(as_uuid=True), server_default=sa.text('uuid_generate_v4()'), nullable=False),
        sa.Column('farm_id', sa.Integer(), nullable=False),
        sa.Column('field_id', sa.Integer(), nullable=True),
        sa.Column('user_id', sa.Integer(), nullable=False),
        
        # Test details
        sa.Column('test_date', sa.Date(), nullable=False),
        sa.Column('test_type', sa.String(length=100), nullable=True),
        sa.Column('lab_name', sa.String(length=200), nullable=True),
        sa.Column('lab_reference', sa.String(length=100), nullable=True),
        
        # Location
        sa.Column('sample_location', sa.String(length=200), nullable=True),
        sa.Column('sample_depth_cm', sa.Float(), nullable=True),
        sa.Column('latitude', sa.Float(), nullable=True),
        sa.Column('longitude', sa.Float(), nullable=True),
        sa.Column('location', geoalchemy2.types.Geography(geometry_type='POINT', srid=4326), nullable=True),
        
        # Physical properties
        sa.Column('soil_type', sa.String(length=100), nullable=True),
        sa.Column('texture', sa.String(length=100), nullable=True),
        sa.Column('color', sa.String(length=50), nullable=True),
        sa.Column('moisture_content_percent', sa.Float(), nullable=True),
        sa.Column('bulk_density', sa.Float(), nullable=True),
        
        # Chemical properties
        sa.Column('ph', sa.Float(), nullable=True),
        sa.Column('electrical_conductivity', sa.Float(), nullable=True),
        sa.Column('organic_matter_percent', sa.Float(), nullable=True),
        sa.Column('organic_carbon_percent', sa.Float(), nullable=True),
        
        # Macronutrients
        sa.Column('nitrogen_ppm', sa.Float(), nullable=True),
        sa.Column('phosphorus_ppm', sa.Float(), nullable=True),
        sa.Column('potassium_ppm', sa.Float(), nullable=True),
        sa.Column('calcium_ppm', sa.Float(), nullable=True),
        sa.Column('magnesium_ppm', sa.Float(), nullable=True),
        sa.Column('sulfur_ppm', sa.Float(), nullable=True),
        
        # Micronutrients
        sa.Column('iron_ppm', sa.Float(), nullable=True),
        sa.Column('zinc_ppm', sa.Float(), nullable=True),
        sa.Column('copper_ppm', sa.Float(), nullable=True),
        sa.Column('manganese_ppm', sa.Float(), nullable=True),
        sa.Column('boron_ppm', sa.Float(), nullable=True),
        
        # Heavy metals
        sa.Column('lead_ppm', sa.Float(), nullable=True),
        sa.Column('cadmium_ppm', sa.Float(), nullable=True),
        sa.Column('mercury_ppm', sa.Float(), nullable=True),
        
        # Recommendations
        sa.Column('recommendations', postgresql.JSONB(), default=list),
        sa.Column('fertility_rating', sa.String(length=50), nullable=True),
        sa.Column('health_score', sa.Float(), nullable=True),
        
        # Documents
        sa.Column('report_url', sa.String(length=500), nullable=True),
        sa.Column('documents', postgresql.ARRAY(sa.String()), default=list),
        
        # Notes
        sa.Column('notes', sa.Text(), nullable=True),
        
        # Full results
        sa.Column('full_results', postgresql.JSONB(), default=dict),
        
        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_deleted', sa.Boolean(), default=False),
        
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['farm_id'], ['farms.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['field_id'], ['fields.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('uuid'),
        sa.CheckConstraint('ph IS NULL OR (ph >= 0 AND ph <= 14)')
    )
    
    op.create_index('idx_soiltest_farm', 'soil_tests', ['farm_id'])
    op.create_index('idx_soiltest_date', 'soil_tests', ['test_date'])
    
    # ========================================================================
    # ALERTS & NOTIFICATIONS TABLES
    # ========================================================================
    
    # Alerts table
    op.create_table(
        'alerts',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('uuid', postgresql.UUID(as_uuid=True), server_default=sa.text('uuid_generate_v4()'), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('farm_id', sa.Integer(), nullable=True),
        sa.Column('device_id', sa.Integer(), nullable=True),
        
        # Alert details
        sa.Column('alert_type', sa.String(length=50), nullable=False),
        sa.Column('category', sa.String(length=50), nullable=True),
        sa.Column('severity', sa.String(length=20), default='medium'),
        sa.Column('priority', sa.String(length=20), default='normal'),
        
        # Content
        sa.Column('title', sa.String(length=200), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('detailed_message', sa.Text(), nullable=True),
        
        # Source
        sa.Column('source', sa.String(length=100), nullable=True),
        sa.Column('source_data', postgresql.JSONB(), nullable=True),
        
        # Conditions that triggered alert
        sa.Column('trigger_conditions', postgresql.JSONB(), nullable=True),
        sa.Column('threshold_value', sa.Float(), nullable=True),
        sa.Column('actual_value', sa.Float(), nullable=True),
        
        # Action
        sa.Column('action_required', sa.Boolean(), default=False),
        sa.Column('recommended_actions', postgresql.JSONB(), default=list),
        sa.Column('action_deadline', sa.DateTime(timezone=True), nullable=True),
        
        # Status
        sa.Column('status', sa.String(length=50), default='active'),
        sa.Column('is_read', sa.Boolean(), default=False),
        sa.Column('read_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('acknowledged', sa.Boolean(), default=False),
        sa.Column('acknowledged_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('resolved', sa.Boolean(), default=False),
        sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('resolution_notes', sa.Text(), nullable=True),
        
        # Notification sent
        sa.Column('notification_sent', sa.Boolean(), default=False),
        sa.Column('notification_channels', postgresql.ARRAY(sa.String()), default=list),
        
        # Expiry
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        
        # Metadata
        sa.Column('metadata', postgresql.JSONB(), default=dict),
        
        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['farm_id'], ['farms.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['device_id'], ['iot_devices.id'], ondelete='SET NULL'),
        sa.UniqueConstraint('uuid')
    )
    
    op.create_index('idx_alert_user', 'alerts', ['user_id'])
    op.create_index('idx_alert_farm', 'alerts', ['farm_id'])
    op.create_index('idx_alert_type_status', 'alerts', ['alert_type', 'status'])
    op.create_index('idx_alert_severity', 'alerts', ['severity'])
    op.create_index('idx_alert_created', 'alerts', ['created_at'])
    
    # Notifications table
    op.create_table(
        'notifications',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('uuid', postgresql.UUID(as_uuid=True), server_default=sa.text('uuid_generate_v4()'), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('alert_id', sa.Integer(), nullable=True),
        
        # Notification details
        sa.Column('notification_type', sa.String(length=50), nullable=False),
        sa.Column('channel', sa.String(length=50), nullable=False),
        sa.Column('priority', sa.String(length=20), default='normal'),
        
        # Content
        sa.Column('title', sa.String(length=200), nullable=False),
        sa.Column('body', sa.Text(), nullable=False),
        sa.Column('data', postgresql.JSONB(), nullable=True),
        
        # Links
        sa.Column('action_url', sa.String(length=500), nullable=True),
        sa.Column('deep_link', sa.String(length=500), nullable=True),
        
        # Delivery details
        sa.Column('recipient_email', sa.String(length=255), nullable=True),
        sa.Column('recipient_phone', sa.String(length=20), nullable=True),
        sa.Column('recipient_device_token', sa.String(length=500), nullable=True),
        
        # Status
        sa.Column('status', sa.String(length=50), default='pending'),
        sa.Column('sent_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('delivered_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('read_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('failed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('failure_reason', sa.Text(), nullable=True),
        
        # Retry
        sa.Column('retry_count', sa.Integer(), default=0),
        sa.Column('last_retry_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('next_retry_at', sa.DateTime(timezone=True), nullable=True),
        
        # Response
        sa.Column('provider_response', postgresql.JSONB(), nullable=True),
        sa.Column('provider_message_id', sa.String(length=255), nullable=True),
        
        # Metadata
        sa.Column('metadata', postgresql.JSONB(), default=dict),
        
        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['alert_id'], ['alerts.id'], ondelete='SET NULL'),
        sa.UniqueConstraint('uuid')
    )
    
    op.create_index('idx_notification_user', 'notifications', ['user_id'])
    op.create_index('idx_notification_status', 'notifications', ['status'])
    op.create_index('idx_notification_channel', 'notifications', ['channel'])
    op.create_index('idx_notification_created', 'notifications', ['created_at'])
    
    # ========================================================================
    # AUDIT TABLE
    # ========================================================================
    
    # Audit Logs table
    op.create_table(
        'audit_logs',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('uuid', postgresql.UUID(as_uuid=True), server_default=sa.text('uuid_generate_v4()'), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        
        # Action details
        sa.Column('action', sa.String(length=50), nullable=False),
        sa.Column('entity_type', sa.String(length=100), nullable=False),
        sa.Column('entity_id', sa.String(length=100), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        
        # Changes
        sa.Column('old_values', postgresql.JSONB(), nullable=True),
        sa.Column('new_values', postgresql.JSONB(), nullable=True),
        sa.Column('changed_fields', postgresql.ARRAY(sa.String()), default=list),
        
        # Request context
        sa.Column('ip_address', postgresql.INET(), nullable=True),
        sa.Column('user_agent', sa.Text(), nullable=True),
        sa.Column('request_method', sa.String(length=10), nullable=True),
        sa.Column('request_path', sa.String(length=500), nullable=True),
        sa.Column('request_query', sa.Text(), nullable=True),
        
        # Session context
        sa.Column('session_id', sa.String(length=255), nullable=True),
        sa.Column('api_key_id', sa.Integer(), nullable=True),
        
        # Result
        sa.Column('success', sa.Boolean(), default=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('status_code', sa.Integer(), nullable=True),
        
        # Performance
        sa.Column('duration_ms', sa.Integer(), nullable=True),
        
        # Metadata
        sa.Column('metadata', postgresql.JSONB(), default=dict),
        sa.Column('tags', postgresql.ARRAY(sa.String()), default=list),
        
        # Timestamp
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
        sa.UniqueConstraint('uuid')
    )
    
    op.create_index('idx_audit_user', 'audit_logs', ['user_id'])
    op.create_index('idx_audit_action', 'audit_logs', ['action'])
    op.create_index('idx_audit_entity', 'audit_logs', ['entity_type', 'entity_id'])
    op.create_index('idx_audit_created', 'audit_logs', ['created_at'])
    op.create_index('idx_audit_success', 'audit_logs', ['success'])
    
    # ========================================================================
    # ASSOCIATION TABLES FOR MANY-TO-MANY RELATIONSHIPS
    # ========================================================================
    
    # Diagnosis-Expert Association (for expert reviews)
    op.create_table(
        'diagnosis_expert_association',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('diagnosis_id', sa.Integer(), nullable=False),
        sa.Column('expert_id', sa.Integer(), nullable=False),
        sa.Column('assigned_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('status', sa.String(length=50), default='assigned'),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['diagnosis_id'], ['diagnoses.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['expert_id'], ['users.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('diagnosis_id', 'expert_id')
    )
    
    op.create_index('idx_diagnosis_expert_diagnosis', 'diagnosis_expert_association', ['diagnosis_id'])
    op.create_index('idx_diagnosis_expert_expert', 'diagnosis_expert_association', ['expert_id'])
    
    # Crop-Disease Association (for disease susceptibility)
    op.create_table(
        'crop_disease_association',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('crop_name', sa.String(length=100), nullable=False),
        sa.Column('disease_id', sa.Integer(), nullable=False),
        sa.Column('susceptibility_level', sa.String(length=20), default='medium'),
        sa.Column('growth_stage_vulnerable', postgresql.ARRAY(sa.String()), default=list),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['disease_id'], ['diseases.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('crop_name', 'disease_id')
    )
    
    op.create_index('idx_crop_disease_crop', 'crop_disease_association', ['crop_name'])
    op.create_index('idx_crop_disease_disease', 'crop_disease_association', ['disease_id'])


def downgrade() -> None:
    """Drop all tables in reverse order."""
    
    # Drop association tables first
    op.drop_table('crop_disease_association')
    op.drop_table('diagnosis_expert_association')
    
    # Drop audit table
    op.drop_table('audit_logs')
    
    # Drop notifications and alerts
    op.drop_table('notifications')
    op.drop_table('alerts')
    
    # Drop IoT and sensor tables
    op.drop_table('soil_tests')
    op.drop_table('weather_records')
    op.drop_table('sensor_readings')
    op.drop_table('iot_devices')
    
    # Drop chama tables
    op.drop_table('chama_meetings')
    op.drop_table('loan_repayments')
    op.drop_table('loans')
    op.drop_table('transactions')
    op.drop_table('user_chama_association')
    op.drop_table('chamas')
    
    # Drop product tables
    op.drop_table('product_supplier_association')
    op.drop_table('suppliers')
    op.drop_table('products')
    
    # Drop diagnosis tables
    op.drop_table('treatment_applications')
    op.drop_table('treatments')
    op.drop_table('diagnoses')
    op.drop_table('diseases')
    
    # Drop farm tables
    op.drop_table('crop_plantings')
    op.drop_table('fields')
    op.drop_table('farms')
    
    # Drop user management tables
    op.drop_table('api_keys')
    op.drop_table('user_sessions')
    op.drop_table('users')
    
    # Drop extensions
    op.execute('DROP EXTENSION IF EXISTS btree_gin')
    op.execute('DROP EXTENSION IF EXISTS pg_trgm')
    op.execute('DROP EXTENSION IF EXISTS "uuid-ossp"')
    op.execute('DROP EXTENSION IF EXISTS postgis')
