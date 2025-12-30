"""
Application configuration settings
"""

from pydantic_settings import BaseSettings
from typing import List
import os


class Settings(BaseSettings):
    """Application settings with environment variable support"""
    
    # Azure Cosmos DB Configuration
    COSMOS_ENDPOINT: str = os.getenv(
        "COSMOS_ENDPOINT",
        "https://your-account.documents.azure.com:443/"
    )
    COSMOS_KEY: str = os.getenv("COSMOS_KEY", "")
    COSMOS_DATABASE: str = os.getenv("COSMOS_DATABASE", "InKCatalystNextGenDB")
    COSMOS_CONTAINER: str = os.getenv("COSMOS_CONTAINER", "Projects")
    
    # Azure Entra ID Configuration
    ENTRA_ID_TENANT_ID: str = os.getenv("ENTRA_ID_TENANT_ID", "")
    ENTRA_ID_CLIENT_ID: str = os.getenv("ENTRA_ID_CLIENT_ID", "")
    ENTRA_ID_AUDIENCE: str = os.getenv("ENTRA_ID_AUDIENCE", "")  # Usually same as client ID
    ENTRA_ID_ENABLED: bool = os.getenv("ENTRA_ID_ENABLED", "true").lower() == "true"
    # Use SimpleTokenValidator for testing without RSA key verification
    ENTRA_ID_SIMPLE_VALIDATION: bool = os.getenv("ENTRA_ID_SIMPLE_VALIDATION", "false").lower() == "true"
    
    # CORS Configuration
    ALLOWED_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:8000",
        "http://localhost:5000",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:8000",
        "http://127.0.0.1:5000",
    ]
    
    # JWT Configuration (for future use)
    JWT_SECRET: str = os.getenv("JWT_SECRET", "change-me-in-production")
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRATION_MINUTES: int = 60
    
    # Application Settings
    APP_ENV: str = os.getenv("APP_ENV", "development")
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
