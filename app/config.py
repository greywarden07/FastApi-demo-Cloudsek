from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration settings loaded from environment"""

    mongodb_url: str = Field(..., alias="MONGODB_URL", description="MongoDB connection string")
    database_name: str = Field(..., alias="DATABASE_NAME", description="MongoDB database name")
    collection_name: str = Field(..., alias="COLLECTION_NAME", description="MongoDB collection name")

    log_level: str = Field(default="INFO", alias="LOG_LEVEL", description="Application log level")
    http_client_timeout: float = Field(default=20.0, alias="HTTP_CLIENT_TIMEOUT", gt=0)
    http_client_max_redirects: int = Field(default=5, alias="HTTP_CLIENT_MAX_REDIRECTS", ge=1)
    page_source_max_bytes: int = Field(default=500_000, alias="PAGE_SOURCE_MAX_BYTES", ge=1)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        env_prefix="",
    )


settings = Settings()
