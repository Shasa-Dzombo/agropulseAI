"""
MLOps Experiment Tracking & Model Registry

Comprehensive ML experiment tracking system similar to MLflow, providing:
- Experiment management and organization
- Metric and parameter logging
- Model versioning and registry
- Artifact storage (models, plots, data)
- Model deployment tracking
- A/B testing framework
- Model lineage and provenance
- Hyperparameter optimization integration
"""

import os
import json
import pickle
import hashlib
import shutil
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple, Union
from dataclasses import dataclass, asdict, field
from enum import Enum
import logging
from pathlib import Path
import yaml

import numpy as np
from sqlalchemy import (
    Column, String, Integer, Float, DateTime, 
    Text, Boolean, ForeignKey, JSON, create_engine
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker

logger = logging.getLogger(__name__)
Base = declarative_base()


class ModelStage(Enum):
    """Model lifecycle stages"""
    NONE = "None"
    STAGING = "Staging"
    PRODUCTION = "Production"
    ARCHIVED = "Archived"


class RunStatus(Enum):
    """Experiment run status"""
    RUNNING = "RUNNING"
    FINISHED = "FINISHED"
    FAILED = "FAILED"
    KILLED = "KILLED"
    SCHEDULED = "SCHEDULED"


class DeploymentStatus(Enum):
    """Model deployment status"""
    PENDING = "PENDING"
    DEPLOYING = "DEPLOYING"
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    FAILED = "FAILED"
    ROLLING_BACK = "ROLLING_BACK"


# Database Models
class Experiment(Base):
    """Experiment table"""
    __tablename__ = 'experiments'
    
    experiment_id = Column(String(36), primary_key=True)
    name = Column(String(256), unique=True, nullable=False)
    description = Column(Text)
    artifact_location = Column(String(512))
    lifecycle_stage = Column(String(32), default="active")
    creation_time = Column(DateTime, default=datetime.utcnow)
    last_update_time = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    tags = Column(JSON)
    
    runs = relationship("Run", back_populates="experiment", cascade="all, delete-orphan")


class Run(Base):
    """Experiment run table"""
    __tablename__ = 'runs'
    
    run_id = Column(String(36), primary_key=True)
    experiment_id = Column(String(36), ForeignKey('experiments.experiment_id'))
    run_name = Column(String(256))
    user_id = Column(String(256))
    status = Column(String(32), default=RunStatus.RUNNING.value)
    start_time = Column(DateTime, default=datetime.utcnow)
    end_time = Column(DateTime)
    source_type = Column(String(64))
    source_name = Column(String(512))
    entry_point = Column(String(256))
    artifact_uri = Column(String(512))
    lifecycle_stage = Column(String(32), default="active")
    
    experiment = relationship("Experiment", back_populates="runs")
    metrics = relationship("Metric", back_populates="run", cascade="all, delete-orphan")
    params = relationship("Param", back_populates="run", cascade="all, delete-orphan")
    tags = relationship("Tag", back_populates="run", cascade="all, delete-orphan")


class Metric(Base):
    """Run metrics table"""
    __tablename__ = 'metrics'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    run_id = Column(String(36), ForeignKey('runs.run_id'))
    key = Column(String(256), nullable=False)
    value = Column(Float, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    step = Column(Integer, default=0)
    
    run = relationship("Run", back_populates="metrics")


class Param(Base):
    """Run parameters table"""
    __tablename__ = 'params'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    run_id = Column(String(36), ForeignKey('runs.run_id'))
    key = Column(String(256), nullable=False)
    value = Column(String(512), nullable=False)
    
    run = relationship("Run", back_populates="params")


class Tag(Base):
    """Run tags table"""
    __tablename__ = 'tags'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    run_id = Column(String(36), ForeignKey('runs.run_id'))
    key = Column(String(256), nullable=False)
    value = Column(String(512))
    
    run = relationship("Run", back_populates="tags")


class RegisteredModel(Base):
    """Registered model table"""
    __tablename__ = 'registered_models'
    
    name = Column(String(256), primary_key=True)
    description = Column(Text)
    creation_time = Column(DateTime, default=datetime.utcnow)
    last_update_time = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    versions = relationship("ModelVersion", back_populates="model", cascade="all, delete-orphan")


class ModelVersion(Base):
    """Model version table"""
    __tablename__ = 'model_versions'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(256), ForeignKey('registered_models.name'))
    version = Column(Integer, nullable=False)
    creation_time = Column(DateTime, default=datetime.utcnow)
    last_update_time = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    description = Column(Text)
    user_id = Column(String(256))
    current_stage = Column(String(32), default=ModelStage.NONE.value)
    source = Column(String(512))
    run_id = Column(String(36))
    status = Column(String(32), default="READY")
    status_message = Column(Text)
    tags = Column(JSON)
    
    model = relationship("RegisteredModel", back_populates="versions")


class ModelDeployment(Base):
    """Model deployment tracking table"""
    __tablename__ = 'model_deployments'
    
    deployment_id = Column(String(36), primary_key=True)
    model_name = Column(String(256), nullable=False)
    model_version = Column(Integer, nullable=False)
    endpoint_name = Column(String(256), nullable=False)
    deployment_type = Column(String(64))  # rest_api, batch, streaming
    environment = Column(String(64))  # dev, staging, production
    status = Column(String(32), default=DeploymentStatus.PENDING.value)
    config = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
    deployed_at = Column(DateTime)
    terminated_at = Column(DateTime)
    created_by = Column(String(256))
    metrics = Column(JSON)


@dataclass
class ExperimentConfig:
    """Experiment configuration"""
    name: str
    description: str = ""
    artifact_location: Optional[str] = None
    tags: Dict[str, str] = field(default_factory=dict)


@dataclass
class RunConfig:
    """Run configuration"""
    run_name: Optional[str] = None
    experiment_name: Optional[str] = None
    experiment_id: Optional[str] = None
    user_id: Optional[str] = None
    tags: Dict[str, str] = field(default_factory=dict)
    description: str = ""


class ExperimentTracker:
    """
    Main experiment tracking system
    
    Manages ML experiments, runs, metrics, and artifacts similar to MLflow.
    """
    
    def __init__(self, tracking_uri: str = "sqlite:///mlops.db", 
                 artifact_root: str = "./mlruns"):
        """
        Initialize experiment tracker
        
        Args:
            tracking_uri: Database connection string
            artifact_root: Root directory for artifacts
        """
        self.engine = create_engine(tracking_uri)
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self.artifact_root = Path(artifact_root)
        self.artifact_root.mkdir(parents=True, exist_ok=True)
        self.active_run = None
        
    def create_experiment(self, config: ExperimentConfig) -> str:
        """
        Create a new experiment
        
        Args:
            config: Experiment configuration
            
        Returns:
            experiment_id: Created experiment ID
        """
        session = self.Session()
        try:
            experiment_id = str(uuid.uuid4())
            artifact_location = config.artifact_location or str(
                self.artifact_root / experiment_id
            )
            
            experiment = Experiment(
                experiment_id=experiment_id,
                name=config.name,
                description=config.description,
                artifact_location=artifact_location,
                tags=config.tags
            )
            
            session.add(experiment)
            session.commit()
            
            # Create artifact directory
            Path(artifact_location).mkdir(parents=True, exist_ok=True)
            
            logger.info(f"Created experiment '{config.name}' with ID: {experiment_id}")
            return experiment_id
            
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to create experiment: {e}")
            raise
        finally:
            session.close()
    
    def get_experiment(self, experiment_id: Optional[str] = None,
                      name: Optional[str] = None) -> Optional[Experiment]:
        """Get experiment by ID or name"""
        session = self.Session()
        try:
            if experiment_id:
                return session.query(Experiment).filter_by(
                    experiment_id=experiment_id
                ).first()
            elif name:
                return session.query(Experiment).filter_by(name=name).first()
            return None
        finally:
            session.close()
    
    def list_experiments(self, max_results: int = 100) -> List[Experiment]:
        """List all experiments"""
        session = self.Session()
        try:
            return session.query(Experiment).filter_by(
                lifecycle_stage="active"
            ).limit(max_results).all()
        finally:
            session.close()
    
    def start_run(self, config: RunConfig) -> 'ActiveRun':
        """
        Start a new experiment run
        
        Args:
            config: Run configuration
            
        Returns:
            ActiveRun context manager
        """
        session = self.Session()
        try:
            # Get or create experiment
            experiment = None
            if config.experiment_id:
                experiment = session.query(Experiment).filter_by(
                    experiment_id=config.experiment_id
                ).first()
            elif config.experiment_name:
                experiment = session.query(Experiment).filter_by(
                    name=config.experiment_name
                ).first()
                if not experiment:
                    exp_config = ExperimentConfig(name=config.experiment_name)
                    exp_id = self.create_experiment(exp_config)
                    experiment = session.query(Experiment).filter_by(
                        experiment_id=exp_id
                    ).first()
            
            if not experiment:
                raise ValueError("No experiment specified")
            
            # Create run
            run_id = str(uuid.uuid4())
            artifact_uri = str(Path(experiment.artifact_location) / run_id)
            
            run = Run(
                run_id=run_id,
                experiment_id=experiment.experiment_id,
                run_name=config.run_name or f"run_{run_id[:8]}",
                user_id=config.user_id,
                artifact_uri=artifact_uri
            )
            
            session.add(run)
            
            # Add tags
            for key, value in config.tags.items():
                tag = Tag(run_id=run_id, key=key, value=value)
                session.add(tag)
            
            session.commit()
            
            # Create artifact directory
            Path(artifact_uri).mkdir(parents=True, exist_ok=True)
            
            self.active_run = ActiveRun(self, run_id, session)
            logger.info(f"Started run '{run.run_name}' (ID: {run_id})")
            
            return self.active_run
            
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to start run: {e}")
            raise
    
    def end_run(self, run_id: str, status: RunStatus = RunStatus.FINISHED):
        """End an experiment run"""
        session = self.Session()
        try:
            run = session.query(Run).filter_by(run_id=run_id).first()
            if run:
                run.status = status.value
                run.end_time = datetime.utcnow()
                session.commit()
                logger.info(f"Ended run {run_id} with status: {status.value}")
                
                if self.active_run and self.active_run.run_id == run_id:
                    self.active_run = None
        finally:
            session.close()
    
    def log_metric(self, run_id: str, key: str, value: float, 
                   step: int = 0, timestamp: Optional[datetime] = None):
        """Log a metric for a run"""
        session = self.Session()
        try:
            metric = Metric(
                run_id=run_id,
                key=key,
                value=value,
                step=step,
                timestamp=timestamp or datetime.utcnow()
            )
            session.add(metric)
            session.commit()
        finally:
            session.close()
    
    def log_param(self, run_id: str, key: str, value: Any):
        """Log a parameter for a run"""
        session = self.Session()
        try:
            param = Param(
                run_id=run_id,
                key=key,
                value=str(value)
            )
            session.add(param)
            session.commit()
        finally:
            session.close()
    
    def log_params(self, run_id: str, params: Dict[str, Any]):
        """Log multiple parameters"""
        for key, value in params.items():
            self.log_param(run_id, key, value)
    
    def log_metrics(self, run_id: str, metrics: Dict[str, float], step: int = 0):
        """Log multiple metrics"""
        for key, value in metrics.items():
            self.log_metric(run_id, key, value, step)
    
    def get_run(self, run_id: str) -> Optional[Run]:
        """Get run by ID"""
        session = self.Session()
        try:
            return session.query(Run).filter_by(run_id=run_id).first()
        finally:
            session.close()
    
    def search_runs(self, experiment_ids: List[str], 
                   filter_string: str = "", 
                   max_results: int = 100) -> List[Run]:
        """
        Search runs with filtering
        
        Args:
            experiment_ids: List of experiment IDs to search
            filter_string: SQL-like filter (e.g., "metrics.accuracy > 0.9")
            max_results: Maximum number of results
            
        Returns:
            List of matching runs
        """
        session = self.Session()
        try:
            query = session.query(Run).filter(
                Run.experiment_id.in_(experiment_ids),
                Run.lifecycle_stage == "active"
            )
            
            # TODO: Implement advanced filtering
            # For now, simple status filtering
            if "status" in filter_string:
                for status in RunStatus:
                    if status.value in filter_string:
                        query = query.filter(Run.status == status.value)
            
            return query.limit(max_results).all()
        finally:
            session.close()
    
    def delete_run(self, run_id: str):
        """Delete a run (soft delete)"""
        session = self.Session()
        try:
            run = session.query(Run).filter_by(run_id=run_id).first()
            if run:
                run.lifecycle_stage = "deleted"
                session.commit()
                logger.info(f"Deleted run: {run_id}")
        finally:
            session.close()


class ActiveRun:
    """
    Active run context manager
    
    Provides convenient API for logging during an active run.
    """
    
    def __init__(self, tracker: ExperimentTracker, run_id: str, session):
        self.tracker = tracker
        self.run_id = run_id
        self.session = session
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            self.tracker.end_run(self.run_id, RunStatus.FINISHED)
        else:
            self.tracker.end_run(self.run_id, RunStatus.FAILED)
        return False
    
    def log_metric(self, key: str, value: float, step: int = 0):
        """Log a metric"""
        self.tracker.log_metric(self.run_id, key, value, step)
    
    def log_metrics(self, metrics: Dict[str, float], step: int = 0):
        """Log multiple metrics"""
        self.tracker.log_metrics(self.run_id, metrics, step)
    
    def log_param(self, key: str, value: Any):
        """Log a parameter"""
        self.tracker.log_param(self.run_id, key, value)
    
    def log_params(self, params: Dict[str, Any]):
        """Log multiple parameters"""
        self.tracker.log_params(self.run_id, params)
    
    def log_artifact(self, local_path: str, artifact_path: str = ""):
        """Log an artifact file"""
        artifact_store = ArtifactStore(self.tracker.artifact_root)
        artifact_store.log_artifact(self.run_id, local_path, artifact_path)
    
    def log_model(self, model: Any, artifact_path: str = "model"):
        """Log a model"""
        artifact_store = ArtifactStore(self.tracker.artifact_root)
        artifact_store.log_model(self.run_id, model, artifact_path)


class ModelRegistry:
    """
    Model registry for versioning and lifecycle management
    
    Manages registered models, versions, and stage transitions.
    """
    
    def __init__(self, tracker: ExperimentTracker):
        self.tracker = tracker
        self.Session = tracker.Session
    
    def create_registered_model(self, name: str, 
                               description: str = "") -> RegisteredModel:
        """
        Register a new model
        
        Args:
            name: Model name
            description: Model description
            
        Returns:
            Registered model
        """
        session = self.Session()
        try:
            model = RegisteredModel(
                name=name,
                description=description
            )
            session.add(model)
            session.commit()
            logger.info(f"Registered model: {name}")
            return model
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to register model: {e}")
            raise
        finally:
            session.close()
    
    def create_model_version(self, name: str, source: str, 
                           run_id: Optional[str] = None,
                           description: str = "",
                           tags: Dict[str, str] = None) -> ModelVersion:
        """
        Create a new model version
        
        Args:
            name: Model name
            source: Model source URI
            run_id: Associated run ID
            description: Version description
            tags: Version tags
            
        Returns:
            Model version
        """
        session = self.Session()
        try:
            # Get or create registered model
            model = session.query(RegisteredModel).filter_by(name=name).first()
            if not model:
                model = RegisteredModel(name=name)
                session.add(model)
                session.flush()
            
            # Determine next version number
            max_version = session.query(ModelVersion).filter_by(
                name=name
            ).count()
            version_number = max_version + 1
            
            # Create version
            version = ModelVersion(
                name=name,
                version=version_number,
                source=source,
                run_id=run_id,
                description=description,
                tags=tags or {}
            )
            
            session.add(version)
            session.commit()
            
            logger.info(f"Created model version: {name} v{version_number}")
            return version
            
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to create model version: {e}")
            raise
        finally:
            session.close()
    
    def transition_model_version_stage(self, name: str, version: int,
                                      stage: ModelStage,
                                      archive_existing: bool = True):
        """
        Transition model version to a new stage
        
        Args:
            name: Model name
            version: Version number
            stage: Target stage
            archive_existing: Archive existing versions in target stage
        """
        session = self.Session()
        try:
            # Archive existing versions in target stage if requested
            if archive_existing and stage != ModelStage.NONE:
                existing = session.query(ModelVersion).filter_by(
                    name=name,
                    current_stage=stage.value
                ).all()
                
                for v in existing:
                    v.current_stage = ModelStage.ARCHIVED.value
            
            # Update target version
            model_version = session.query(ModelVersion).filter_by(
                name=name,
                version=version
            ).first()
            
            if not model_version:
                raise ValueError(f"Model version not found: {name} v{version}")
            
            model_version.current_stage = stage.value
            session.commit()
            
            logger.info(f"Transitioned {name} v{version} to {stage.value}")
            
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to transition model stage: {e}")
            raise
        finally:
            session.close()
    
    def get_model_version(self, name: str, version: int) -> Optional[ModelVersion]:
        """Get specific model version"""
        session = self.Session()
        try:
            return session.query(ModelVersion).filter_by(
                name=name,
                version=version
            ).first()
        finally:
            session.close()
    
    def get_latest_versions(self, name: str, 
                          stages: List[ModelStage] = None) -> List[ModelVersion]:
        """
        Get latest model versions for specified stages
        
        Args:
            name: Model name
            stages: List of stages to filter by
            
        Returns:
            List of model versions
        """
        session = self.Session()
        try:
            query = session.query(ModelVersion).filter_by(name=name)
            
            if stages:
                stage_values = [s.value for s in stages]
                query = query.filter(ModelVersion.current_stage.in_(stage_values))
            
            # Get latest for each stage
            versions = query.order_by(ModelVersion.version.desc()).all()
            
            # Deduplicate by stage (keep latest)
            seen_stages = set()
            result = []
            for v in versions:
                if v.current_stage not in seen_stages:
                    result.append(v)
                    seen_stages.add(v.current_stage)
            
            return result
        finally:
            session.close()
    
    def search_model_versions(self, filter_string: str = "",
                            max_results: int = 100) -> List[ModelVersion]:
        """Search model versions with filtering"""
        session = self.Session()
        try:
            query = session.query(ModelVersion)
            
            # Simple filtering by stage
            if "stage" in filter_string.lower():
                for stage in ModelStage:
                    if stage.value.lower() in filter_string.lower():
                        query = query.filter(
                            ModelVersion.current_stage == stage.value
                        )
            
            return query.limit(max_results).all()
        finally:
            session.close()
    
    def delete_model_version(self, name: str, version: int):
        """Delete a model version"""
        session = self.Session()
        try:
            model_version = session.query(ModelVersion).filter_by(
                name=name,
                version=version
            ).first()
            
            if model_version:
                session.delete(model_version)
                session.commit()
                logger.info(f"Deleted model version: {name} v{version}")
        finally:
            session.close()


class ArtifactStore:
    """
    Artifact storage manager
    
    Handles storage and retrieval of model artifacts, plots, and files.
    """
    
    def __init__(self, artifact_root: Path):
        self.artifact_root = artifact_root
    
    def log_artifact(self, run_id: str, local_path: str, 
                    artifact_path: str = ""):
        """
        Log an artifact file
        
        Args:
            run_id: Run ID
            local_path: Local file path
            artifact_path: Relative path in artifact store
        """
        try:
            src = Path(local_path)
            if not src.exists():
                raise FileNotFoundError(f"File not found: {local_path}")
            
            # Determine destination
            dest_dir = self.artifact_root / run_id
            if artifact_path:
                dest_dir = dest_dir / artifact_path
            dest_dir.mkdir(parents=True, exist_ok=True)
            
            dest = dest_dir / src.name
            
            # Copy file
            if src.is_file():
                shutil.copy2(src, dest)
            else:
                shutil.copytree(src, dest, dirs_exist_ok=True)
            
            logger.info(f"Logged artifact: {dest}")
            
        except Exception as e:
            logger.error(f"Failed to log artifact: {e}")
            raise
    
    def log_artifacts(self, run_id: str, local_dir: str, 
                     artifact_path: str = ""):
        """Log all files in a directory"""
        local_path = Path(local_dir)
        for item in local_path.iterdir():
            self.log_artifact(run_id, str(item), artifact_path)
    
    def log_model(self, run_id: str, model: Any, artifact_path: str = "model"):
        """
        Log a machine learning model
        
        Args:
            run_id: Run ID
            model: Model object
            artifact_path: Artifact path
        """
        try:
            model_dir = self.artifact_root / run_id / artifact_path
            model_dir.mkdir(parents=True, exist_ok=True)
            
            # Save model using pickle
            model_path = model_dir / "model.pkl"
            with open(model_path, 'wb') as f:
                pickle.dump(model, f)
            
            # Save model metadata
            metadata = {
                'model_type': type(model).__name__,
                'saved_at': datetime.utcnow().isoformat(),
                'python_version': __import__('sys').version
            }
            
            metadata_path = model_dir / "MLmodel"
            with open(metadata_path, 'w') as f:
                yaml.dump(metadata, f)
            
            logger.info(f"Logged model: {model_path}")
            
        except Exception as e:
            logger.error(f"Failed to log model: {e}")
            raise
    
    def load_model(self, run_id: str, artifact_path: str = "model") -> Any:
        """Load a model from artifact store"""
        model_path = self.artifact_root / run_id / artifact_path / "model.pkl"
        
        if not model_path.exists():
            raise FileNotFoundError(f"Model not found: {model_path}")
        
        with open(model_path, 'rb') as f:
            model = pickle.load(f)
        
        return model
    
    def list_artifacts(self, run_id: str, path: str = "") -> List[str]:
        """List artifacts for a run"""
        artifact_dir = self.artifact_root / run_id
        if path:
            artifact_dir = artifact_dir / path
        
        if not artifact_dir.exists():
            return []
        
        artifacts = []
        for item in artifact_dir.rglob("*"):
            if item.is_file():
                rel_path = item.relative_to(artifact_dir)
                artifacts.append(str(rel_path))
        
        return artifacts
    
    def download_artifact(self, run_id: str, artifact_path: str, 
                         dst_path: str):
        """Download an artifact to local path"""
        src = self.artifact_root / run_id / artifact_path
        dst = Path(dst_path)
        
        if src.is_file():
            shutil.copy2(src, dst)
        else:
            shutil.copytree(src, dst, dirs_exist_ok=True)


class MetricLogger:
    """
    Advanced metric logging with aggregations
    
    Provides utilities for logging and analyzing metrics over time.
    """
    
    def __init__(self, tracker: ExperimentTracker):
        self.tracker = tracker
    
    def log_metric_series(self, run_id: str, key: str, 
                         values: List[float], steps: List[int]):
        """Log a series of metric values"""
        for value, step in zip(values, steps):
            self.tracker.log_metric(run_id, key, value, step)
    
    def log_confusion_matrix(self, run_id: str, cm: np.ndarray, 
                           class_names: List[str]):
        """Log confusion matrix"""
        # Store as artifact
        artifact_store = ArtifactStore(self.tracker.artifact_root)
        
        cm_dict = {
            'matrix': cm.tolist(),
            'class_names': class_names
        }
        
        cm_path = self.tracker.artifact_root / run_id / "confusion_matrix.json"
        cm_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(cm_path, 'w') as f:
            json.dump(cm_dict, f, indent=2)
    
    def log_classification_report(self, run_id: str, report: Dict[str, Any]):
        """Log classification metrics report"""
        # Log individual metrics
        for class_name, metrics in report.items():
            if isinstance(metrics, dict):
                for metric_name, value in metrics.items():
                    if isinstance(value, (int, float)):
                        key = f"{class_name}_{metric_name}"
                        self.tracker.log_metric(run_id, key, value)
    
    def get_metric_history(self, run_id: str, key: str) -> List[Tuple[int, float]]:
        """Get metric history for a run"""
        session = self.tracker.Session()
        try:
            metrics = session.query(Metric).filter_by(
                run_id=run_id,
                key=key
            ).order_by(Metric.step).all()
            
            return [(m.step, m.value) for m in metrics]
        finally:
            session.close()
    
    def get_metric_statistics(self, run_id: str, key: str) -> Dict[str, float]:
        """Calculate statistics for a metric"""
        history = self.get_metric_history(run_id, key)
        
        if not history:
            return {}
        
        values = [v for _, v in history]
        
        return {
            'count': len(values),
            'min': min(values),
            'max': max(values),
            'mean': np.mean(values),
            'std': np.std(values),
            'median': np.median(values),
            'q25': np.percentile(values, 25),
            'q75': np.percentile(values, 75)
        }


class HyperparameterTuner:
    """
    Hyperparameter optimization integration
    
    Integrates with experiment tracking for hyperparameter search.
    """
    
    def __init__(self, tracker: ExperimentTracker):
        self.tracker = tracker
    
    def grid_search(self, experiment_name: str, 
                   param_grid: Dict[str, List[Any]],
                   train_func: callable,
                   metric_name: str = "accuracy",
                   maximize: bool = True) -> Dict[str, Any]:
        """
        Perform grid search over hyperparameters
        
        Args:
            experiment_name: Experiment name
            param_grid: Dictionary of parameter lists
            train_func: Training function that takes params and returns metrics
            metric_name: Metric to optimize
            maximize: Whether to maximize metric
            
        Returns:
            Best parameters and score
        """
        import itertools
        
        # Generate all parameter combinations
        keys = list(param_grid.keys())
        values = list(param_grid.values())
        combinations = list(itertools.product(*values))
        
        best_score = float('-inf') if maximize else float('inf')
        best_params = None
        
        for combo in combinations:
            params = dict(zip(keys, combo))
            
            # Run training with these parameters
            config = RunConfig(
                experiment_name=experiment_name,
                run_name=f"grid_search_{hash(str(params))}",
                tags={'tuning': 'grid_search'}
            )
            
            with self.tracker.start_run(config) as run:
                run.log_params(params)
                
                # Execute training
                metrics = train_func(**params)
                run.log_metrics(metrics)
                
                # Check if best
                score = metrics.get(metric_name, 0)
                is_better = (maximize and score > best_score) or \
                           (not maximize and score < best_score)
                
                if is_better:
                    best_score = score
                    best_params = params
        
        logger.info(f"Grid search complete. Best {metric_name}: {best_score}")
        logger.info(f"Best parameters: {best_params}")
        
        return {
            'best_params': best_params,
            'best_score': best_score,
            'metric_name': metric_name
        }
    
    def random_search(self, experiment_name: str,
                     param_distributions: Dict[str, callable],
                     train_func: callable,
                     n_iter: int = 10,
                     metric_name: str = "accuracy",
                     maximize: bool = True) -> Dict[str, Any]:
        """
        Perform random search over hyperparameters
        
        Args:
            experiment_name: Experiment name
            param_distributions: Dictionary of parameter samplers
            train_func: Training function
            n_iter: Number of iterations
            metric_name: Metric to optimize
            maximize: Whether to maximize metric
            
        Returns:
            Best parameters and score
        """
        best_score = float('-inf') if maximize else float('inf')
        best_params = None
        
        for i in range(n_iter):
            # Sample parameters
            params = {
                key: sampler() for key, sampler in param_distributions.items()
            }
            
            # Run training
            config = RunConfig(
                experiment_name=experiment_name,
                run_name=f"random_search_{i}",
                tags={'tuning': 'random_search'}
            )
            
            with self.tracker.start_run(config) as run:
                run.log_params(params)
                
                metrics = train_func(**params)
                run.log_metrics(metrics)
                
                score = metrics.get(metric_name, 0)
                is_better = (maximize and score > best_score) or \
                           (not maximize and score < best_score)
                
                if is_better:
                    best_score = score
                    best_params = params
        
        logger.info(f"Random search complete. Best {metric_name}: {best_score}")
        return {
            'best_params': best_params,
            'best_score': best_score,
            'metric_name': metric_name
        }


class ModelDeployer:
    """
    Model deployment tracker
    
    Tracks model deployments across environments.
    """
    
    def __init__(self, tracker: ExperimentTracker):
        self.tracker = tracker
        self.Session = tracker.Session
    
    def create_deployment(self, model_name: str, model_version: int,
                         endpoint_name: str,
                         deployment_type: str = "rest_api",
                         environment: str = "production",
                         config: Dict[str, Any] = None,
                         created_by: str = None) -> str:
        """
        Create a model deployment record
        
        Args:
            model_name: Model name
            model_version: Model version
            endpoint_name: Deployment endpoint
            deployment_type: Type (rest_api, batch, streaming)
            environment: Environment (dev, staging, production)
            config: Deployment configuration
            created_by: User who created deployment
            
        Returns:
            deployment_id
        """
        session = self.Session()
        try:
            deployment_id = str(uuid.uuid4())
            
            deployment = ModelDeployment(
                deployment_id=deployment_id,
                model_name=model_name,
                model_version=model_version,
                endpoint_name=endpoint_name,
                deployment_type=deployment_type,
                environment=environment,
                config=config or {},
                created_by=created_by
            )
            
            session.add(deployment)
            session.commit()
            
            logger.info(f"Created deployment: {endpoint_name}")
            return deployment_id
            
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to create deployment: {e}")
            raise
        finally:
            session.close()
    
    def update_deployment_status(self, deployment_id: str,
                                 status: DeploymentStatus,
                                 metrics: Dict[str, Any] = None):
        """Update deployment status"""
        session = self.Session()
        try:
            deployment = session.query(ModelDeployment).filter_by(
                deployment_id=deployment_id
            ).first()
            
            if not deployment:
                raise ValueError(f"Deployment not found: {deployment_id}")
            
            deployment.status = status.value
            
            if status == DeploymentStatus.ACTIVE and not deployment.deployed_at:
                deployment.deployed_at = datetime.utcnow()
            elif status == DeploymentStatus.INACTIVE and not deployment.terminated_at:
                deployment.terminated_at = datetime.utcnow()
            
            if metrics:
                deployment.metrics = metrics
            
            session.commit()
            logger.info(f"Updated deployment {deployment_id} to {status.value}")
            
        finally:
            session.close()
    
    def get_active_deployments(self, environment: str = None) -> List[ModelDeployment]:
        """Get active deployments"""
        session = self.Session()
        try:
            query = session.query(ModelDeployment).filter_by(
                status=DeploymentStatus.ACTIVE.value
            )
            
            if environment:
                query = query.filter_by(environment=environment)
            
            return query.all()
        finally:
            session.close()
    
    def rollback_deployment(self, deployment_id: str,
                           previous_version: int):
        """Rollback to a previous model version"""
        session = self.Session()
        try:
            deployment = session.query(ModelDeployment).filter_by(
                deployment_id=deployment_id
            ).first()
            
            if not deployment:
                raise ValueError(f"Deployment not found: {deployment_id}")
            
            # Update to rolling back status
            deployment.status = DeploymentStatus.ROLLING_BACK.value
            session.commit()
            
            # Create new deployment with previous version
            new_deployment_id = self.create_deployment(
                model_name=deployment.model_name,
                model_version=previous_version,
                endpoint_name=deployment.endpoint_name,
                deployment_type=deployment.deployment_type,
                environment=deployment.environment,
                config=deployment.config,
                created_by=deployment.created_by
            )
            
            # Deactivate old deployment
            deployment.status = DeploymentStatus.INACTIVE.value
            deployment.terminated_at = datetime.utcnow()
            session.commit()
            
            logger.info(f"Rolled back deployment {deployment_id} to version {previous_version}")
            return new_deployment_id
            
        finally:
            session.close()


class ExperimentComparator:
    """
    Experiment comparison and analysis
    
    Compares metrics across runs and experiments.
    """
    
    def __init__(self, tracker: ExperimentTracker):
        self.tracker = tracker
    
    def compare_runs(self, run_ids: List[str]) -> Dict[str, Any]:
        """
        Compare multiple runs
        
        Args:
            run_ids: List of run IDs to compare
            
        Returns:
            Comparison summary
        """
        session = self.tracker.Session()
        try:
            comparison = {
                'runs': [],
                'metrics': {},
                'params': {}
            }
            
            for run_id in run_ids:
                run = session.query(Run).filter_by(run_id=run_id).first()
                if not run:
                    continue
                
                run_info = {
                    'run_id': run_id,
                    'run_name': run.run_name,
                    'status': run.status,
                    'duration': None
                }
                
                if run.end_time and run.start_time:
                    duration = (run.end_time - run.start_time).total_seconds()
                    run_info['duration'] = duration
                
                comparison['runs'].append(run_info)
                
                # Collect metrics
                metrics = session.query(Metric).filter_by(run_id=run_id).all()
                for metric in metrics:
                    if metric.key not in comparison['metrics']:
                        comparison['metrics'][metric.key] = {}
                    comparison['metrics'][metric.key][run_id] = metric.value
                
                # Collect params
                params = session.query(Param).filter_by(run_id=run_id).all()
                for param in params:
                    if param.key not in comparison['params']:
                        comparison['params'][param.key] = {}
                    comparison['params'][param.key][run_id] = param.value
            
            return comparison
            
        finally:
            session.close()
    
    def find_best_run(self, experiment_id: str, 
                     metric_name: str,
                     maximize: bool = True) -> Optional[Run]:
        """Find best run for an experiment based on metric"""
        session = self.tracker.Session()
        try:
            runs = session.query(Run).filter_by(
                experiment_id=experiment_id,
                lifecycle_stage="active"
            ).all()
            
            best_run = None
            best_value = float('-inf') if maximize else float('inf')
            
            for run in runs:
                metrics = session.query(Metric).filter_by(
                    run_id=run.run_id,
                    key=metric_name
                ).order_by(Metric.step.desc()).first()
                
                if metrics:
                    is_better = (maximize and metrics.value > best_value) or \
                               (not maximize and metrics.value < best_value)
                    
                    if is_better:
                        best_value = metrics.value
                        best_run = run
            
            return best_run
            
        finally:
            session.close()
    
    def generate_leaderboard(self, experiment_id: str,
                           metric_name: str,
                           top_k: int = 10) -> List[Dict[str, Any]]:
        """Generate leaderboard for an experiment"""
        session = self.tracker.Session()
        try:
            runs = session.query(Run).filter_by(
                experiment_id=experiment_id,
                lifecycle_stage="active"
            ).all()
            
            leaderboard = []
            
            for run in runs:
                metrics = session.query(Metric).filter_by(
                    run_id=run.run_id,
                    key=metric_name
                ).order_by(Metric.step.desc()).first()
                
                if metrics:
                    leaderboard.append({
                        'run_id': run.run_id,
                        'run_name': run.run_name,
                        'metric': metrics.value,
                        'timestamp': metrics.timestamp
                    })
            
            # Sort by metric value
            leaderboard.sort(key=lambda x: x['metric'], reverse=True)
            
            return leaderboard[:top_k]
            
        finally:
            session.close()


class ModelLineage:
    """
    Model lineage and provenance tracking
    
    Tracks relationships between models, data, and experiments.
    """
    
    def __init__(self, tracker: ExperimentTracker):
        self.tracker = tracker
    
    def trace_model_lineage(self, model_name: str, 
                           version: int) -> Dict[str, Any]:
        """
        Trace complete lineage of a model version
        
        Args:
            model_name: Model name
            version: Version number
            
        Returns:
            Lineage information
        """
        session = self.tracker.Session()
        try:
            registry = ModelRegistry(self.tracker)
            model_version = registry.get_model_version(model_name, version)
            
            if not model_version:
                return {}
            
            lineage = {
                'model': {
                    'name': model_name,
                    'version': version,
                    'created_at': model_version.creation_time,
                    'stage': model_version.current_stage
                },
                'run': None,
                'experiment': None,
                'params': {},
                'metrics': {},
                'artifacts': []
            }
            
            # Get run info
            if model_version.run_id:
                run = session.query(Run).filter_by(
                    run_id=model_version.run_id
                ).first()
                
                if run:
                    lineage['run'] = {
                        'run_id': run.run_id,
                        'run_name': run.run_name,
                        'status': run.status,
                        'start_time': run.start_time,
                        'end_time': run.end_time
                    }
                    
                    # Get experiment
                    experiment = session.query(Experiment).filter_by(
                        experiment_id=run.experiment_id
                    ).first()
                    
                    if experiment:
                        lineage['experiment'] = {
                            'experiment_id': experiment.experiment_id,
                            'name': experiment.name
                        }
                    
                    # Get params
                    params = session.query(Param).filter_by(
                        run_id=run.run_id
                    ).all()
                    lineage['params'] = {p.key: p.value for p in params}
                    
                    # Get metrics
                    metrics = session.query(Metric).filter_by(
                        run_id=run.run_id
                    ).all()
                    lineage['metrics'] = {m.key: m.value for m in metrics}
                    
                    # Get artifacts
                    artifact_store = ArtifactStore(self.tracker.artifact_root)
                    lineage['artifacts'] = artifact_store.list_artifacts(run.run_id)
            
            return lineage
            
        finally:
            session.close()
    
    def get_model_dependencies(self, model_name: str, 
                              version: int) -> List[Dict[str, Any]]:
        """Get models that this model depends on"""
        # This would track if model was derived from another model
        # For now, returns empty list
        return []
    
    def get_downstream_models(self, model_name: str,
                             version: int) -> List[Dict[str, Any]]:
        """Get models derived from this model"""
        # Track models that used this as a base
        return []


# Example usage
def example_usage():
    """Demonstrate experiment tracking usage"""
    
    # Initialize tracker
    tracker = ExperimentTracker(
        tracking_uri="sqlite:///mlops.db",
        artifact_root="./mlruns"
    )
    
    # Create experiment
    exp_config = ExperimentConfig(
        name="crop_yield_prediction",
        description="Predicting crop yields from sensor data",
        tags={'domain': 'agriculture', 'model_type': 'regression'}
    )
    exp_id = tracker.create_experiment(exp_config)
    
    # Start a run
    run_config = RunConfig(
        experiment_id=exp_id,
        run_name="xgboost_baseline",
        tags={'model': 'xgboost', 'version': 'v1'}
    )
    
    with tracker.start_run(run_config) as run:
        # Log parameters
        run.log_params({
            'max_depth': 6,
            'learning_rate': 0.1,
            'n_estimators': 100
        })
        
        # Simulate training and log metrics
        for epoch in range(10):
            run.log_metrics({
                'train_rmse': 100 - epoch * 5,
                'val_rmse': 110 - epoch * 4
            }, step=epoch)
        
        # Log final metrics
        run.log_metrics({
            'test_rmse': 65.3,
            'r2_score': 0.85
        })
        
        # Log model artifact
        # run.log_model(trained_model, "model")
    
    # Model registry
    registry = ModelRegistry(tracker)
    
    # Register model
    model_version = registry.create_model_version(
        name="crop_yield_predictor",
        source=f"runs/{run.run_id}/model",
        run_id=run.run_id,
        description="XGBoost regression model for yield prediction"
    )
    
    # Transition to staging
    registry.transition_model_version_stage(
        name="crop_yield_predictor",
        version=model_version.version,
        stage=ModelStage.STAGING
    )
    
    # Compare runs
    comparator = ExperimentComparator(tracker)
    best_run = comparator.find_best_run(
        experiment_id=exp_id,
        metric_name="test_rmse",
        maximize=False
    )
    
    print(f"Best run: {best_run.run_name if best_run else 'None'}")
    
    # Model deployment
    deployer = ModelDeployer(tracker)
    deployment_id = deployer.create_deployment(
        model_name="crop_yield_predictor",
        model_version=1,
        endpoint_name="yield-api-v1",
        environment="production",
        config={'instances': 3, 'memory': '2Gi'}
    )
    
    deployer.update_deployment_status(
        deployment_id,
        DeploymentStatus.ACTIVE,
        metrics={'latency_p95': 45.2, 'qps': 120}
    )
    
    logger.info("Example complete!")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    example_usage()
