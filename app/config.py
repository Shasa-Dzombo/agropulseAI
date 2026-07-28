import os
from pydantic_settings import BaseSettings
from typing import Optional

# pydantic-settings resolves env_file relative to the process's CWD, not this
# file - anchor it to the repo root so scripts run from subdirectories (e.g.
# scripts/) still pick up the real .env instead of silently finding nothing.
_ENV_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".env")


class Settings(BaseSettings):
    # Application
    APP_NAME: str = "AgroPulse"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True
    ENVIRONMENT: str = "development"
    
    # Server
    HOST: str = "localhost"
    PORT: int = 8030
    
    # Database
    DATABASE_URL: str
    DATABASE_POOL_SIZE: int = 20
    DATABASE_MAX_OVERFLOW: int = 10
    
    # Security
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # AWS
    AWS_ACCESS_KEY_ID: str
    AWS_SECRET_ACCESS_KEY: str
    AWS_REGION: str = "us-east-1"
    AWS_S3_BUCKET: str
    AWS_SAGEMAKER_ENDPOINT: Optional[str] = None
    AWS_BEDROCK_MODEL_ID: str = "anthropic.claude-v2"
    
    # Azure
    AZURE_SUBSCRIPTION_KEY: Optional[str] = None
    AZURE_ENDPOINT: Optional[str] = None
    AZURE_QUANTUM_WORKSPACE: Optional[str] = None
    AZURE_QUANTUM_RESOURCE_GROUP: Optional[str] = None
    
    # Blockchain
    BLOCKCHAIN_NETWORK: str = "polygon-mumbai"
    BLOCKCHAIN_RPC_URL: str
    PERMIT_CONTRACT_ADDRESS: str
    PRIVATE_KEY: str
    GAS_LIMIT: int = 100000
    
    # Payment Gateway
    FLUTTERWAVE_PUBLIC_KEY: str
    FLUTTERWAVE_SECRET_KEY: str
    FLUTTERWAVE_ENCRYPTION_KEY: str
    MPESA_SHORTCODE: str
    MPESA_CONSUMER_KEY: str
    MPESA_CONSUMER_SECRET: str
    
    # Quantum Computing
    AMAZON_BRAKET_S3_BUCKET: str = "amazon-braket-outputs"
    AZURE_QUANTUM_LOCATION: str = "westus"
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # Pricing (in KSh)
    DIAGNOSIS_PRICE: float = 50.0
    WEEKLY_SUBSCRIPTION: float = 500.0
    MONTHLY_SUBSCRIPTION: float = 1800.0

    # Drone orchard survey pipeline
    DRONE_IMAGE_STORAGE: str = "s3"  # "s3" | "local" | "supabase" - local writes to DRONE_LOCAL_IMAGE_DIR, no credentials needed; supabase uses SUPABASE_STORAGE_* below
    DRONE_LOCAL_IMAGE_DIR: str = "local_uploads"
    DRONE_CAMERA_SOURCE: str = "synthetic"  # "synthetic" or "local_files" - local_files reads real photos from DRONE_CAMERA_SOURCE_DIR instead of generating them
    DRONE_CAMERA_SOURCE_DIR: str = "local_uploads/drone-imagery/1"

    # Supabase Storage (S3-compatible) - alternative to AWS S3 for drone imagery.
    # Separate from Supabase's Postgres connection (see app/db_config.py's
    # EnterpriseDBConfig.SUPABASE_URL) - these are Storage-specific S3 access
    # keys from the Supabase dashboard, not the project's anon/service-role key.
    SUPABASE_PROJECT_URL: Optional[str] = None  # e.g. https://<project-ref>.supabase.co
    SUPABASE_STORAGE_ENDPOINT_URL: Optional[str] = None  # e.g. https://<project-ref>.supabase.co/storage/v1/s3
    SUPABASE_STORAGE_ACCESS_KEY_ID: Optional[str] = None
    SUPABASE_STORAGE_SECRET_ACCESS_KEY: Optional[str] = None
    SUPABASE_STORAGE_BUCKET: Optional[str] = None

    # Kindwise crop.health disease detection (opt-in, paid, drone pipeline only)
    KINDWISE_API_KEY: Optional[str] = None
    KINDWISE_CACHE_DIR: str = "kindwise_cache"
    KINDWISE_BASE_URL: Optional[str] = None  # override only if Kindwise's endpoint changes - defaults to the client's own https://crop.kindwise.com/api/v1
    KINDWISE_TIMEOUT: int = 30
    KINDWISE_MAX_REQUESTS_PER_MINUTE: int = 60
    KINDWISE_MAX_REQUESTS_PER_DAY: int = 5000

    # OpenWeatherMap (optional, opt-in - drone pipeline pre-flight/weather
    # context). Free tier: 1,000 calls/day. Unset = weather features skip
    # gracefully, same pattern as KINDWISE_API_KEY above.
    OPENWEATHER_API_KEY: Optional[str] = None

    class Config:
        env_file = _ENV_FILE
        case_sensitive = True


settings = Settings()
