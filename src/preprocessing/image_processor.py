"""
Module de préprocessing des images pour améliorer la qualité OCR
"""

import cv2
import numpy as np
from PIL import Image, ImageEnhance
from typing import Tuple, Optional
import pdf2image
from pathlib import Path
from src.utils.logger import app_logger
from src.utils.exceptions import FileProcessingError, InvalidFileFormatError


class ImageProcessor:
    """Classe pour le préprocessing des images"""
    
    def __init__(self):
        self.supported_formats = ['png', 'jpg', 'jpeg', 'pdf']
    
    def process_file(self, file_path: str) -> np.ndarray:
        """
        Traite un fichier et retourne l'image préprocessée
        
        Args:
            file_path: Chemin vers le fichier à traiter
            
        Returns:
            Image préprocessée sous forme de numpy array
        """
        try:
            file_extension = Path(file_path).suffix.lower().lstrip('.')
            
            if file_extension not in self.supported_formats:
                raise InvalidFileFormatError(f"Format {file_extension} non supporté")
            
            app_logger.info(f"Traitement du fichier: {file_path}")
            
            if file_extension == 'pdf':
                image = self._process_pdf(file_path)
            else:
                image = self._process_image(file_path)
            
            # Préprocessing de l'image
            processed_image = self._preprocess_image(image)
            
            app_logger.info("Préprocessing terminé avec succès")
            return processed_image
            
        except Exception as e:
            app_logger.error(f"Erreur lors du traitement du fichier: {str(e)}")
            raise FileProcessingError(f"Impossible de traiter le fichier: {str(e)}")
    
    def _process_pdf(self, pdf_path: str) -> np.ndarray:
        """Convertit la première page d'un PDF en image"""
        try:
            pages = pdf2image.convert_from_path(pdf_path, dpi=300, first_page=1, last_page=1)
            if not pages:
                raise FileProcessingError("Impossible de convertir le PDF")
            
            # Convertir en numpy array
            pil_image = pages[0]
            return np.array(pil_image)
            
        except Exception as e:
            raise FileProcessingError(f"Erreur lors de la conversion PDF: {str(e)}")
    
    def _process_image(self, image_path: str) -> np.ndarray:
        """Charge une image standard"""
        try:
            image = cv2.imread(image_path)
            if image is None:
                raise FileProcessingError("Impossible de charger l'image")
            
            # Convertir BGR vers RGB
            image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            return image
            
        except Exception as e:
            raise FileProcessingError(f"Erreur lors du chargement de l'image: {str(e)}")
    
    def _preprocess_image(self, image: np.ndarray) -> np.ndarray:
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
            
            # Correction de l'inclinaison
            corrected = self._correct_skew(gray)
            
            # Amélioration du contraste
            enhanced = self._enhance_contrast(corrected)
            
            # Réduction du bruit
            denoised = self._denoise_image(enhanced)
            
            # Binarisation adaptative
            binary = self._adaptive_threshold(denoised)
            
            return binary
            
        except Exception as e:
            app_logger.error(f"Erreur lors du préprocessing: {str(e)}")
            return image
    
    def _correct_skew(self, image: np.ndarray) -> np.ndarray:
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
    
    def _enhance_contrast(self, image: np.ndarray) -> np.ndarray:
        """Améliore le contraste de l'image"""
        try:
            # CLAHE (Contrast Limited Adaptive Histogram Equalization)
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            enhanced = clahe.apply(image)
            return enhanced
            
        except Exception as e:
            app_logger.warning(f"Impossible d'améliorer le contraste: {str(e)}")
            return image
    
    def _denoise_image(self, image: np.ndarray) -> np.ndarray:
        """Réduit le bruit dans l'image"""
        try:
            # Filtre de débruitage non-local
            denoised = cv2.fastNlMeansDenoising(image, None, 10, 7, 21)
            return denoised
            
        except Exception as e:
            app_logger.warning(f"Impossible de réduire le bruit: {str(e)}")
            return image
    
    def _adaptive_threshold(self, image: np.ndarray) -> np.ndarray:
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
