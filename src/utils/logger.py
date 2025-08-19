"""
Configuration du système de logs
"""

import sys
from pathlib import Path
from loguru import logger
from src.config.settings import settings


def setup_logger():
    """Configure le système de logs avec loguru"""
    
    # Supprimer la configuration par défaut
    logger.remove()
    
    # Configuration pour la console
    logger.add(
        sys.stdout,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        level=settings.log_level,
        colorize=True
    )
    
    # Configuration pour le fichier de logs
    log_path = Path(settings.log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    
    logger.add(
        settings.log_file,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        level=settings.log_level,
        rotation="10 MB",
        retention="30 days",
        compression="zip"
    )
    
    return logger


# Instance globale du logger
app_logger = setup_logger()
