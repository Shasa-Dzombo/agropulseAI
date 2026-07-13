from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # Application
    APP_NAME: str = "AgroPulse"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True
    ENVIRONMENT: str = "development"
    
    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    
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
    DRONE_IMAGE_STORAGE: str = "s3"  # "s3" or "local" - local writes to DRONE_LOCAL_IMAGE_DIR, no AWS credentials needed
    DRONE_LOCAL_IMAGE_DIR: str = "local_uploads"
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
