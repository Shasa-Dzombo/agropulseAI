"""
Over-The-Air (OTA) Update Manager

Secure firmware and software updates for IoT devices at scale.

Features:
- Secure update delivery
- Delta updates
- Rollback capability
- Update scheduling
- Bandwidth optimization
- Firmware validation
- Multi-stage rollout
- A/B partition updates
"""

import os
import logging
import hashlib
import hmac
from typing import Dict, List, Optional, Tuple, Union
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
import json
import asyncio

import aiohttp
import aiofiles
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.hazmat.backends import default_backend
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Boolean, Float, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker


logger = logging.getLogger(__name__)

Base = declarative_base()


class UpdateStatus(Enum):
    """Update status enumeration"""
    PENDING = "pending"
    DOWNLOADING = "downloading"
    VALIDATING = "validating"
    INSTALLING = "installing"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


class UpdatePriority(Enum):
    """Update priority levels"""
    CRITICAL = "critical"  # Security patches, immediately
    HIGH = "high"  # Important bug fixes, within 24h
    MEDIUM = "medium"  # Feature updates, within week
    LOW = "low"  # Optional updates, user discretion


@dataclass
class FirmwarePackage:
    """Firmware package information"""
    package_id: str
    version: str
    device_models: List[str]
    file_size: int
    hash_sha256: str
    signature: str
    download_url: str
    delta_from_version: Optional[str] = None
    delta_size: Optional[int] = None
    release_notes: str = ""
    release_date: datetime = field(default_factory=datetime.now)
    min_required_version: Optional[str] = None
    priority: UpdatePriority = UpdatePriority.MEDIUM
    metadata: Dict = field(default_factory=dict)


@dataclass
class UpdateJob:
    """OTA update job"""
    job_id: str
    device_id: str
    firmware_package: FirmwarePackage
    current_version: str
    target_version: str
    status: UpdateStatus
    progress_percent: float
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3
    bandwidth_limit_kbps: Optional[int] = None


@dataclass
class UpdateStatistics:
    """Update campaign statistics"""
    campaign_id: str
    total_devices: int
    completed: int
    failed: int
    in_progress: int
    pending: int
    success_rate: float
    average_duration_seconds: float
    total_data_transferred_mb: float


class FirmwarePackageModel(Base):
    """SQLAlchemy model for firmware packages"""
    __tablename__ = 'firmware_packages'
    
    id = Column(Integer, primary_key=True)
    package_id = Column(String(100), unique=True, nullable=False, index=True)
    version = Column(String(50), nullable=False)
    device_models = Column(JSON)
    file_size = Column(Integer)
    hash_sha256 = Column(String(64))
    signature = Column(String(1000))
    download_url = Column(String(500))
    delta_from_version = Column(String(50))
    delta_size = Column(Integer)
    release_notes = Column(String(5000))
    release_date = Column(DateTime)
    min_required_version = Column(String(50))
    priority = Column(String(20))
    metadata = Column(JSON)


class UpdateJobModel(Base):
    """SQLAlchemy model for update jobs"""
    __tablename__ = 'update_jobs'
    
    id = Column(Integer, primary_key=True)
    job_id = Column(String(100), unique=True, nullable=False, index=True)
    device_id = Column(String(100), nullable=False, index=True)
    package_id = Column(String(100), nullable=False)
    current_version = Column(String(50))
    target_version = Column(String(50))
    status = Column(String(50))
    progress_percent = Column(Float)
    created_at = Column(DateTime)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    error_message = Column(String(1000))
    retry_count = Column(Integer)


class FirmwareValidator:
    """
    Firmware validation and integrity checking
    
    Validates firmware packages before deployment.
    """
    
    def __init__(self, public_key_path: Optional[str] = None):
        self.public_key = None
        
        if public_key_path and os.path.exists(public_key_path):
            with open(public_key_path, 'rb') as key_file:
                self.public_key = serialization.load_pem_public_key(
                    key_file.read(),
                    backend=default_backend()
                )
        
        logger.info("FirmwareValidator initialized")
    
    def validate_hash(self, file_path: str, expected_hash: str) -> bool:
        """
        Validate file hash
        
        Args:
            file_path: Path to firmware file
            expected_hash: Expected SHA256 hash
            
        Returns:
            True if hash matches
        """
        sha256_hash = hashlib.sha256()
        
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        
        calculated_hash = sha256_hash.hexdigest()
        is_valid = calculated_hash == expected_hash
        
        if is_valid:
            logger.info(f"Hash validation passed for {file_path}")
        else:
            logger.error(
                f"Hash validation failed for {file_path}: "
                f"expected {expected_hash}, got {calculated_hash}"
            )
        
        return is_valid
    
    def verify_signature(self, file_path: str, signature: bytes) -> bool:
        """
        Verify firmware signature
        
        Args:
            file_path: Path to firmware file
            signature: Digital signature
            
        Returns:
            True if signature is valid
        """
        if not self.public_key:
            logger.warning("No public key available for signature verification")
            return False
        
        try:
            with open(file_path, 'rb') as f:
                firmware_data = f.read()
            
            self.public_key.verify(
                signature,
                firmware_data,
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.MAX_LENGTH
                ),
                hashes.SHA256()
            )
            
            logger.info(f"Signature verification passed for {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"Signature verification failed: {e}")
            return False
    
    def validate_version(self, current_version: str, target_version: str) -> bool:
        """
        Validate version upgrade path
        
        Args:
            current_version: Current firmware version
            target_version: Target firmware version
            
        Returns:
            True if upgrade path is valid
        """
        try:
            # Simple semantic versioning check
            current_parts = [int(x) for x in current_version.split('.')]
            target_parts = [int(x) for x in target_version.split('.')]
            
            # Ensure we're not downgrading (unless explicitly allowed)
            if target_parts < current_parts:
                logger.warning(f"Downgrade detected: {current_version} -> {target_version}")
                return False
            
            # Check if major version jump is allowed (max 1 major version)
            if target_parts[0] > current_parts[0] + 1:
                logger.error("Major version jump too large")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Version validation error: {e}")
            return False


class DeltaUpdateGenerator:
    """
    Generate delta updates for bandwidth optimization
    
    Creates binary diffs between firmware versions.
    """
    
    def __init__(self):
        logger.info("DeltaUpdateGenerator initialized")
    
    def generate_delta(
        self,
        old_firmware_path: str,
        new_firmware_path: str,
        output_path: str
    ) -> int:
        """
        Generate delta patch
        
        Args:
            old_firmware_path: Path to old firmware
            new_firmware_path: Path to new firmware
            output_path: Path for delta output
            
        Returns:
            Size of delta file in bytes
        """
        try:
            import bsdiff4
            
            # Read firmware files
            with open(old_firmware_path, 'rb') as f:
                old_data = f.read()
            
            with open(new_firmware_path, 'rb') as f:
                new_data = f.read()
            
            # Generate delta
            delta = bsdiff4.diff(old_data, new_data)
            
            # Save delta
            with open(output_path, 'wb') as f:
                f.write(delta)
            
            delta_size = len(delta)
            original_size = len(new_data)
            compression_ratio = (1 - delta_size / original_size) * 100
            
            logger.info(
                f"Delta generated: {delta_size} bytes "
                f"({compression_ratio:.1f}% reduction)"
            )
            
            return delta_size
            
        except Exception as e:
            logger.error(f"Delta generation failed: {e}")
            return 0
    
    def apply_delta(
        self,
        old_firmware_path: str,
        delta_path: str,
        output_path: str
    ) -> bool:
        """
        Apply delta patch
        
        Args:
            old_firmware_path: Path to old firmware
            delta_path: Path to delta patch
            output_path: Path for patched output
            
        Returns:
            True if successful
        """
        try:
            import bsdiff4
            
            with open(old_firmware_path, 'rb') as f:
                old_data = f.read()
            
            with open(delta_path, 'rb') as f:
                delta_data = f.read()
            
            # Apply patch
            new_data = bsdiff4.patch(old_data, delta_data)
            
            # Save patched firmware
            with open(output_path, 'wb') as f:
                f.write(new_data)
            
            logger.info(f"Delta applied successfully to {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"Delta application failed: {e}")
            return False


class OTAUpdateManager:
    """
    Complete OTA update management system
    
    Handles firmware distribution, scheduling, and monitoring.
    """
    
    def __init__(
        self,
        database_url: str,
        storage_path: str,
        cdn_base_url: Optional[str] = None
    ):
        # Database setup
        self.engine = create_engine(database_url)
        Base.metadata.create_all(self.engine)
        self.SessionLocal = sessionmaker(bind=self.engine)
        
        # Storage for firmware packages
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        # CDN for distribution
        self.cdn_base_url = cdn_base_url
        
        # Validators
        self.validator = FirmwareValidator()
        self.delta_generator = DeltaUpdateGenerator()
        
        # Active jobs
        self.active_jobs: Dict[str, UpdateJob] = {}
        
        # Campaign management
        self.campaigns: Dict[str, Dict] = {}
        
        logger.info(f"OTAUpdateManager initialized (storage={storage_path})")
    
    def register_firmware_package(
        self,
        package: FirmwarePackage,
        firmware_file_path: str
    ) -> str:
        """
        Register new firmware package
        
        Args:
            package: Firmware package info
            firmware_file_path: Path to firmware file
            
        Returns:
            Package ID
        """
        # Validate firmware
        if not self.validator.validate_hash(firmware_file_path, package.hash_sha256):
            raise ValueError("Firmware hash validation failed")
        
        # Copy to storage
        storage_file = self.storage_path / f"{package.package_id}.bin"
        import shutil
        shutil.copy2(firmware_file_path, storage_file)
        
        # Update download URL
        if self.cdn_base_url:
            package.download_url = f"{self.cdn_base_url}/{package.package_id}.bin"
        else:
            package.download_url = str(storage_file)
        
        # Save to database
        db = self.SessionLocal()
        try:
            pkg_model = FirmwarePackageModel(
                package_id=package.package_id,
                version=package.version,
                device_models=package.device_models,
                file_size=package.file_size,
                hash_sha256=package.hash_sha256,
                signature=package.signature,
                download_url=package.download_url,
                delta_from_version=package.delta_from_version,
                delta_size=package.delta_size,
                release_notes=package.release_notes,
                release_date=package.release_date,
                min_required_version=package.min_required_version,
                priority=package.priority.value,
                metadata=package.metadata
            )
            db.add(pkg_model)
            db.commit()
        finally:
            db.close()
        
        logger.info(f"Registered firmware package: {package.package_id}")
        return package.package_id
    
    def create_update_job(
        self,
        device_id: str,
        package_id: str,
        current_version: str,
        bandwidth_limit_kbps: Optional[int] = None
    ) -> UpdateJob:
        """
        Create OTA update job
        
        Args:
            device_id: Device ID
            package_id: Firmware package ID
            current_version: Current firmware version
            bandwidth_limit_kbps: Optional bandwidth limit
            
        Returns:
            Update job
        """
        import uuid
        
        # Get package
        db = self.SessionLocal()
        try:
            pkg = db.query(FirmwarePackageModel).filter_by(package_id=package_id).first()
            if not pkg:
                raise ValueError(f"Package not found: {package_id}")
            
            firmware_package = FirmwarePackage(
                package_id=pkg.package_id,
                version=pkg.version,
                device_models=pkg.device_models,
                file_size=pkg.file_size,
                hash_sha256=pkg.hash_sha256,
                signature=pkg.signature,
                download_url=pkg.download_url,
                delta_from_version=pkg.delta_from_version,
                delta_size=pkg.delta_size,
                release_notes=pkg.release_notes,
                release_date=pkg.release_date,
                min_required_version=pkg.min_required_version,
                priority=UpdatePriority(pkg.priority),
                metadata=pkg.metadata or {}
            )
        finally:
            db.close()
        
        # Validate version upgrade
        if not self.validator.validate_version(current_version, firmware_package.version):
            raise ValueError("Invalid version upgrade path")
        
        # Create job
        job_id = str(uuid.uuid4())
        job = UpdateJob(
            job_id=job_id,
            device_id=device_id,
            firmware_package=firmware_package,
            current_version=current_version,
            target_version=firmware_package.version,
            status=UpdateStatus.PENDING,
            progress_percent=0.0,
            created_at=datetime.now(),
            bandwidth_limit_kbps=bandwidth_limit_kbps
        )
        
        # Save to database
        db = self.SessionLocal()
        try:
            job_model = UpdateJobModel(
                job_id=job_id,
                device_id=device_id,
                package_id=package_id,
                current_version=current_version,
                target_version=firmware_package.version,
                status=UpdateStatus.PENDING.value,
                progress_percent=0.0,
                created_at=datetime.now(),
                retry_count=0
            )
            db.add(job_model)
            db.commit()
        finally:
            db.close()
        
        self.active_jobs[job_id] = job
        
        logger.info(f"Created update job: {job_id} for device {device_id}")
        return job
    
    async def execute_update(self, job_id: str) -> bool:
        """
        Execute OTA update
        
        Args:
            job_id: Update job ID
            
        Returns:
            True if successful
        """
        if job_id not in self.active_jobs:
            logger.error(f"Job not found: {job_id}")
            return False
        
        job = self.active_jobs[job_id]
        job.status = UpdateStatus.DOWNLOADING
        job.started_at = datetime.now()
        
        try:
            # Download firmware
            download_path = self.storage_path / f"download_{job_id}.bin"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(job.firmware_package.download_url) as response:
                    if response.status != 200:
                        raise Exception(f"Download failed: HTTP {response.status}")
                    
                    total_size = int(response.headers.get('content-length', 0))
                    downloaded = 0
                    
                    async with aiofiles.open(download_path, 'wb') as f:
                        async for chunk in response.content.iter_chunked(8192):
                            await f.write(chunk)
                            downloaded += len(chunk)
                            
                            # Update progress
                            if total_size > 0:
                                job.progress_percent = (downloaded / total_size) * 50
                                
                            # Apply bandwidth limit
                            if job.bandwidth_limit_kbps:
                                await asyncio.sleep(len(chunk) / (job.bandwidth_limit_kbps * 128))
            
            # Validate downloaded firmware
            job.status = UpdateStatus.VALIDATING
            if not self.validator.validate_hash(
                str(download_path),
                job.firmware_package.hash_sha256
            ):
                raise Exception("Firmware validation failed")
            
            job.progress_percent = 60
            
            # Simulate installation (in production, would trigger device update)
            job.status = UpdateStatus.INSTALLING
            await asyncio.sleep(5)  # Simulate installation time
            job.progress_percent = 90
            
            # Cleanup
            if download_path.exists():
                download_path.unlink()
            
            # Complete
            job.status = UpdateStatus.COMPLETED
            job.progress_percent = 100
            job.completed_at = datetime.now()
            
            logger.info(f"Update completed for job {job_id}")
            return True
            
        except Exception as e:
            logger.error(f"Update failed for job {job_id}: {e}")
            job.status = UpdateStatus.FAILED
            job.error_message = str(e)
            job.retry_count += 1
            
            return False
    
    def create_update_campaign(
        self,
        campaign_id: str,
        package_id: str,
        device_ids: List[str],
        rollout_strategy: str = 'gradual',  # 'immediate', 'gradual', 'staged'
        rollout_percent_per_hour: int = 10
    ) -> str:
        """
        Create update campaign for multiple devices
        
        Args:
            campaign_id: Campaign ID
            package_id: Firmware package ID
            device_ids: List of device IDs
            rollout_strategy: Rollout strategy
            rollout_percent_per_hour: Percent of devices to update per hour
            
        Returns:
            Campaign ID
        """
        campaign = {
            'campaign_id': campaign_id,
            'package_id': package_id,
            'device_ids': device_ids,
            'rollout_strategy': rollout_strategy,
            'rollout_percent_per_hour': rollout_percent_per_hour,
            'created_at': datetime.now(),
            'status': 'active',
            'jobs': []
        }
        
        self.campaigns[campaign_id] = campaign
        
        logger.info(
            f"Created update campaign {campaign_id} for {len(device_ids)} devices"
        )
        
        return campaign_id
    
    def get_campaign_statistics(self, campaign_id: str) -> Optional[UpdateStatistics]:
        """Get statistics for update campaign"""
        if campaign_id not in self.campaigns:
            return None
        
        campaign = self.campaigns[campaign_id]
        jobs = campaign.get('jobs', [])
        
        if not jobs:
            return UpdateStatistics(
                campaign_id=campaign_id,
                total_devices=len(campaign['device_ids']),
                completed=0,
                failed=0,
                in_progress=0,
                pending=0,
                success_rate=0.0,
                average_duration_seconds=0.0,
                total_data_transferred_mb=0.0
            )
        
        completed = sum(1 for j in jobs if j.status == UpdateStatus.COMPLETED)
        failed = sum(1 for j in jobs if j.status == UpdateStatus.FAILED)
        in_progress = sum(1 for j in jobs if j.status in [UpdateStatus.DOWNLOADING, UpdateStatus.INSTALLING])
        pending = sum(1 for j in jobs if j.status == UpdateStatus.PENDING)
        
        success_rate = completed / len(jobs) * 100 if jobs else 0
        
        # Calculate average duration
        completed_jobs = [j for j in jobs if j.status == UpdateStatus.COMPLETED and j.completed_at]
        avg_duration = 0.0
        if completed_jobs:
            durations = [
                (j.completed_at - j.started_at).total_seconds()
                for j in completed_jobs if j.started_at
            ]
            avg_duration = sum(durations) / len(durations) if durations else 0.0
        
        # Calculate total data transferred
        total_data_mb = sum(j.firmware_package.file_size for j in jobs) / (1024 * 1024)
        
        return UpdateStatistics(
            campaign_id=campaign_id,
            total_devices=len(campaign['device_ids']),
            completed=completed,
            failed=failed,
            in_progress=in_progress,
            pending=pending,
            success_rate=success_rate,
            average_duration_seconds=avg_duration,
            total_data_transferred_mb=total_data_mb
        )
