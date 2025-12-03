"""
Configuration Management
Handles all environment variables and settings
"""

from pydantic_settings import BaseSettings
from typing import Optional
import os

class Settings(BaseSettings):
    """Application settings from environment variables"""
    
    # App
    APP_NAME: str = "OnShape BOM Manager"
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"
    
    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./onshape.db")
    
    # OnShape OAuth
    ONSHAPE_CLIENT_ID: str = os.getenv("ONSHAPE_CLIENT_ID", "")
    ONSHAPE_CLIENT_SECRET: str = os.getenv("ONSHAPE_CLIENT_SECRET", "")
    ONSHAPE_REDIRECT_URI: str = os.getenv("ONSHAPE_REDIRECT_URI", "redirect_uri=https://onshape-server-api.onrender.com/auth/callback")
    
    # Encryption
    ENCRYPTION_KEY: str = os.getenv("ENCRYPTION_KEY", "")
    
    # OnShape API
    ONSHAPE_AUTH_URL: str = "https://oauth.onshape.com/oauth/authorize"
    ONSHAPE_TOKEN_URL: str = "https://oauth.onshape.com/oauth/token"
    ONSHAPE_API_URL: str = "https://cad.onshape.com/api"
    ONSHAPE_SCOPE: str = "OAuth2Read OAuth2Write"
    
    class Config:
        env_file = ".env"

settings = Settings()