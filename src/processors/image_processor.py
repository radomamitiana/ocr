"""
Processeur spécialisé pour les fichiers images
"""

import cv2
import numpy as np
from pathlib import Path
from typing import List
from src.interfaces.processors import FileProcessor
from src.utils.logger import app_logger
from src.utils.exceptions import FileProcessingError


class ImageProcessor:
    """Processeur spécialisé pour les fichiers images"""
    
    def __init__(self):
        """Initialise le processeur d'images"""
        self.supported_extensions = ['png', 'jpg', 'jpeg', 'bmp', 'tiff', 'tif']
    
    def can_process(self, file_path: str) -> bool:
        """Vérifie si le processeur peut traiter ce type de fichier"""
        extension = Path(file_path).suffix.lower().lstrip('.')
        return extension in self.supported_extensions
    
    def process(self, file_path: str) -> np.ndarray:
        """
        Traite le fichier image et retourne l'image
        
        Args:
            file_path: Chemin vers le fichier image
            
        Returns:
            Image sous forme de numpy array
            
        Raises:
            FileProcessingError: Si le chargement échoue
        """
        try:
            app_logger.info(f"Chargement de l'image: {file_path}")
            
            image = cv2.imread(file_path)
            if image is None:
                raise FileProcessingError("Impossible de charger l'image")
            
            # Convertir BGR vers RGB
            image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            
            app_logger.info(f"Image chargée avec succès - Taille: {image_rgb.shape}")
            return image_rgb
            
        except Exception as e:
            app_logger.error(f"Erreur lors du chargement de l'image: {str(e)}")
            raise FileProcessingError(f"Impossible de charger l'image: {str(e)}")
    
    def get_image_info(self, file_path: str) -> dict:
        """
        Retourne les informations sur l'image
        
        Args:
            file_path: Chemin vers le fichier image
            
        Returns:
            Dictionnaire avec les informations de l'image
        """
        try:
            image = cv2.imread(file_path)
            if image is None:
                raise FileProcessingError("Impossible de charger l'image")
            
            height, width, channels = image.shape
            file_size = Path(file_path).stat().st_size
            
            return {
                'width': width,
                'height': height,
                'channels': channels,
                'file_size': file_size,
                'format': Path(file_path).suffix.upper().lstrip('.')
            }
            
        except Exception as e:
            app_logger.error(f"Erreur lors de la lecture des informations: {str(e)}")
            raise FileProcessingError(f"Impossible de lire les informations de l'image: {str(e)}")
