"""
Processeur d'images amélioré suivant les principes SOLID
"""

import cv2
import numpy as np
from typing import List, Dict, Any
from src.interfaces.processors import ImageProcessorInterface
from src.processors.pdf_processor import PDFProcessor
from src.processors.image_processor import ImageProcessor
from src.utils.logger import app_logger
from src.utils.exceptions import FileProcessingError, InvalidFileFormatError


class ImageEnhancer:
    """Classe responsable de l'amélioration d'images (Single Responsibility)"""
    
    def correct_skew(self, image: np.ndarray) -> np.ndarray:
        """Corrige l'inclinaison de l'image"""
        try:
            # Détection des contours
            edges = cv2.Canny(image, 50, 150, apertureSize=3)
            
            # Détection des lignes avec la transformée de Hough
            lines = cv2.HoughLines(edges, 1, np.pi/180, threshold=100)
            
            if lines is not None:
                angles = []
                for rho, theta in lines[:10]:  # Prendre les 10 premières lignes
                    angle = theta * 180 / np.pi
                    if angle < 45:
                        angles.append(angle)
                    elif angle > 135:
                        angles.append(angle - 180)
                
                if angles:
                    median_angle = np.median(angles)
                    
                    # Rotation de l'image
                    if abs(median_angle) > 0.5:  # Seuil minimum pour la rotation
                        center = tuple(np.array(image.shape[1::-1]) / 2)
                        rot_mat = cv2.getRotationMatrix2D(center, median_angle, 1.0)
                        image = cv2.warpAffine(image, rot_mat, image.shape[1::-1], flags=cv2.INTER_LINEAR)
            
            return image
            
        except Exception as e:
            app_logger.warning(f"Impossible de corriger l'inclinaison: {str(e)}")
            return image
    
    def enhance_contrast(self, image: np.ndarray) -> np.ndarray:
        """Améliore le contraste de l'image"""
        try:
            # CLAHE (Contrast Limited Adaptive Histogram Equalization)
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            enhanced = clahe.apply(image)
            return enhanced
            
        except Exception as e:
            app_logger.warning(f"Impossible d'améliorer le contraste: {str(e)}")
            return image
    
    def denoise_image(self, image: np.ndarray) -> np.ndarray:
        """Réduit le bruit dans l'image"""
        try:
            # Filtre de débruitage non-local
            denoised = cv2.fastNlMeansDenoising(image, None, 10, 7, 21)
            return denoised
            
        except Exception as e:
            app_logger.warning(f"Impossible de réduire le bruit: {str(e)}")
            return image
    
    def adaptive_threshold(self, image: np.ndarray) -> np.ndarray:
        """Applique une binarisation adaptative"""
        try:
            # Binarisation adaptative
            binary = cv2.adaptiveThreshold(
                image, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                cv2.THRESH_BINARY, 11, 2
            )
            return binary
            
        except Exception as e:
            app_logger.warning(f"Impossible d'appliquer la binarisation: {str(e)}")
            return image


class FileProcessorFactory:
    """Factory pour créer les processeurs appropriés (Factory Pattern)"""
    
    def __init__(self):
        self._processors = [
            PDFProcessor(),
            ImageProcessor()
        ]
    
    def get_processor(self, file_path: str):
        """Retourne le processeur approprié pour le fichier"""
        for processor in self._processors:
            if processor.can_process(file_path):
                return processor
        
        raise InvalidFileFormatError(f"Aucun processeur disponible pour le fichier: {file_path}")
    
    def get_supported_formats(self) -> List[str]:
        """Retourne la liste des formats supportés"""
        formats = []
        for processor in self._processors:
            formats.extend(processor.supported_extensions)
        return list(set(formats))


class EnhancedImageProcessor(ImageProcessorInterface):
    """
    Processeur d'images amélioré suivant les principes SOLID
    
    - Single Responsibility: Chaque classe a une responsabilité unique
    - Open/Closed: Extensible via l'ajout de nouveaux processeurs
    - Liskov Substitution: Respecte l'interface ImageProcessorInterface
    - Interface Segregation: Interfaces spécialisées
    - Dependency Inversion: Dépend des abstractions, pas des implémentations
    """
    
    def __init__(self, enhancer: ImageEnhancer = None, factory: FileProcessorFactory = None):
        """
        Initialise le processeur avec injection de dépendances
        
        Args:
            enhancer: Enhancer d'images (injection de dépendance)
            factory: Factory de processeurs (injection de dépendance)
        """
        self.enhancer = enhancer or ImageEnhancer()
        self.factory = factory or FileProcessorFactory()
    
    def process_file(self, file_path: str) -> np.ndarray:
        """
        Traite un fichier et retourne l'image préprocessée
        
        Args:
            file_path: Chemin vers le fichier à traiter
            
        Returns:
            Image préprocessée sous forme de numpy array
        """
        try:
            app_logger.info(f"Traitement du fichier: {file_path}")
            
            # Obtenir le processeur approprié (Factory Pattern)
            processor = self.factory.get_processor(file_path)
            
            # Traiter le fichier
            image = processor.process(file_path)
            
            # Préprocessing de l'image
            processed_image = self.preprocess_image(image)
            
            app_logger.info("Préprocessing terminé avec succès")
            return processed_image
            
        except Exception as e:
            app_logger.error(f"Erreur lors du traitement du fichier: {str(e)}")
            raise FileProcessingError(f"Impossible de traiter le fichier: {str(e)}")
    
    def preprocess_image(self, image: np.ndarray) -> np.ndarray:
        """
        Applique les traitements de préprocessing
        
        Args:
            image: Image d'entrée
            
        Returns:
            Image préprocessée
        """
        try:
            # Conversion en niveaux de gris
            if len(image.shape) == 3:
                gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
            else:
                gray = image.copy()
            
            # Application des améliorations (Strategy Pattern via l'enhancer)
            corrected = self.enhancer.correct_skew(gray)
            enhanced = self.enhancer.enhance_contrast(corrected)
            denoised = self.enhancer.denoise_image(enhanced)
            binary = self.enhancer.adaptive_threshold(denoised)
            
            return binary
            
        except Exception as e:
            app_logger.error(f"Erreur lors du préprocessing: {str(e)}")
            return image
    
    def get_supported_formats(self) -> List[str]:
        """Retourne la liste des formats supportés"""
        return self.factory.get_supported_formats()
