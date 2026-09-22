"""
Central configuration for SWITCHYARD using environment variables.
"""
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Environment & Logging
    SWITCHYARD_ENV: str = "development"
    SWITCHYARD_LOG_LEVEL: str = "INFO"

    # Database
    DATABASE_URL: str = "sqlite:///./switchyard_operational.db"

    # Data Directories
    DATA_RAW_DIR: Path = Path("./data/generated")
    DATA_PROCESSED_DIR: Path = Path("./data/processed")
    DATA_REJECTED_DIR: Path = Path("./data/rejected")
    DATA_SAMPLE_DIR: Path = Path("./data/sample")

    # Priority Scoring Weights (Must sum to 1.0)
    WEIGHT_SLA_RISK: float = 0.35
    WEIGHT_CUSTOMER_IMPACT: float = 0.25
    WEIGHT_FINANCIAL_IMPACT: float = 0.20
    WEIGHT_CASE_AGE: float = 0.10
    WEIGHT_OPERATIONAL_CRITICALITY: float = 0.10

    # SLA Thresholds
    SLA_WARNING_THRESHOLD_RATIO: float = 0.80
    SLA_BREACH_THRESHOLD_RATIO: float = 1.00

    # AWS Cloud Integration
    AWS_REGION: str = "us-east-1"
    AWS_S3_BUCKET: str = "switchyard-operational-lakehouse"
    AWS_GLUE_DATABASE: str = "switchyard_analytics"
    AWS_ATHENA_WORKGROUP: str = "primary"
    AWS_ATHENA_OUTPUT_LOCATION: str = "s3://switchyard-operational-lakehouse/athena-results/"


settings = Settings()
