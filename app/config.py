from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration settings loaded from environment"""

    # Database connection settings - these are required and must be provided via environment variables
    mongodb_url: str = Field(..., alias="MONGODB_URL", description="MongoDB connection string")
    database_name: str = Field(..., alias="DATABASE_NAME", description="MongoDB database name")
    collection_name: str = Field(..., alias="COLLECTION_NAME", description="MongoDB collection name")

    # Application behavior settings - these have sensible defaults but can be overridden
    log_level: str = Field(default="INFO", alias="LOG_LEVEL", description="Application log level")
    
    # HTTP client settings to prevent hanging on slow websites
    http_client_timeout: float = Field(default=20.0, alias="HTTP_CLIENT_TIMEOUT", gt=0)
    http_client_max_redirects: int = Field(default=5, alias="HTTP_CLIENT_MAX_REDIRECTS", ge=1)
    
    # Limit page source size to avoid memory issues with huge HTML responses
    page_source_max_bytes: int = Field(default=500_000, alias="PAGE_SOURCE_MAX_BYTES", ge=1)

    model_config = SettingsConfigDict(
        env_file=".env",  
        env_file_encoding="utf-8",
        extra="ignore",  
        env_prefix="",
    )

settings = Settings()
