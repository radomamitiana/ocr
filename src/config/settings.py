"""
Configuration de l'application
"""

import os
from typing import List
try:
    from pydantic_settings import BaseSettings
except ImportError:
    from pydantic import BaseSettings


class Settings(BaseSettings):
    # API Configuration
    app_name: str = "OCR Factures API"
    app_version: str = "1.0.0"
    debug: bool = False
    
    # Server Configuration
    host: str = "0.0.0.0"
    port: int = 8000
    reload: bool = False
    
    # File Upload Configuration
    max_file_size: int = 10 * 1024 * 1024  # 10MB
    allowed_extensions: List[str] = ["png", "jpg", "jpeg", "pdf"]
    upload_dir: str = "data/temp"
    
    # OCR Configuration
    tesseract_cmd: str = "/opt/homebrew/bin/tesseract"  # Chemin vers tesseract
    ocr_language: str = "fra"
    confidence_threshold: float = 0.8
    
    # Rate Limiting
    rate_limit_requests: int = 100
    rate_limit_period: int = 60  # seconds
    
    # Processing Configuration
    max_processing_time: int = 60  # seconds
    enable_gpu: bool = False
    
    # Logging Configuration
    log_level: str = "INFO"
    log_file: str = "logs/app.log"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


# Instance globale des paramètres
settings = Settings()
