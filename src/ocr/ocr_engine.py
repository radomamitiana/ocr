"""
Module OCR utilisant Tesseract pour l'extraction de texte
"""

import pytesseract
import cv2
import numpy as np
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from src.config.settings import settings
from src.utils.logger import app_logger
from src.utils.exceptions import OCRProcessingError, ConfigurationError


@dataclass
class OCRResult:
    """Résultat de l'OCR avec informations de confiance"""
    text: str
    confidence: float
    word_confidences: List[float]
    bounding_boxes: List[Tuple[int, int, int, int]]


class OCREngine:
    """Moteur OCR basé sur Tesseract"""
    
    def __init__(self):
        self._configure_tesseract()
        self._validate_tesseract()
    
    def _configure_tesseract(self):
        """Configure Tesseract"""
        try:
            # Configuration du chemin vers tesseract si spécifié
            if settings.tesseract_cmd:
                pytesseract.pytesseract.tesseract_cmd = settings.tesseract_cmd
                
        except Exception as e:
            raise ConfigurationError(f"Erreur de configuration Tesseract: {str(e)}")
    
    def _validate_tesseract(self):
        """Valide que Tesseract est correctement installé"""
        try:
            version = pytesseract.get_tesseract_version()
            app_logger.info(f"Tesseract version: {version}")
            
        except Exception as e:
            raise ConfigurationError(f"Tesseract non trouvé ou mal configuré: {str(e)}")
    
    def extract_text(self, image: np.ndarray, language: str = "fra") -> OCRResult:
        """
        Extrait le texte d'une image
        
        Args:
            image: Image à traiter
            language: Langue pour l'OCR (défaut: français)
            
        Returns:
            Résultat OCR avec texte et métadonnées
        """
        try:
            app_logger.info(f"Extraction OCR en cours (langue: {language})")
            
            # Configuration OCR
            config = self._get_ocr_config()
            
            # Extraction du texte
            text = pytesseract.image_to_string(
                image, 
                lang=language, 
                config=config
            )
            
            # Extraction des données détaillées
            data = pytesseract.image_to_data(
                image, 
                lang=language, 
                config=config,
                output_type=pytesseract.Output.DICT
            )
            
            # Calcul de la confiance moyenne
            confidences = [int(conf) for conf in data['conf'] if int(conf) > 0]
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0
            
            # Extraction des boîtes englobantes des mots
            bounding_boxes = []
            word_confidences = []
            
            for i in range(len(data['text'])):
                if int(data['conf'][i]) > 0:
                    x, y, w, h = data['left'][i], data['top'][i], data['width'][i], data['height'][i]
                    bounding_boxes.append((x, y, x + w, y + h))
                    word_confidences.append(float(data['conf'][i]))
            
            result = OCRResult(
                text=text.strip(),
                confidence=avg_confidence / 100.0,  # Normaliser entre 0 et 1
                word_confidences=word_confidences,
                bounding_boxes=bounding_boxes
            )
            
            app_logger.info(f"OCR terminé - Confiance: {result.confidence:.2f}")
            return result
            
        except Exception as e:
            app_logger.error(f"Erreur lors de l'extraction OCR: {str(e)}")
            raise OCRProcessingError(f"Échec de l'extraction OCR: {str(e)}")
    
    def _get_ocr_config(self) -> str:
        """Retourne la configuration OCR optimisée pour les factures"""
        return (
            "--oem 3 "  # OCR Engine Mode: Default
            "--psm 6 "  # Page Segmentation Mode: Uniform block of text
            "-c tessedit_char_whitelist=0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyzÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖØÙÚÛÜÝÞßàáâãäåæçèéêëìíîïðñòóôõöøùúûüýþÿ.,;:!?()[]{}\"'-+*/=€$%@#&_|\\/<> "
        )
    
    def extract_structured_data(self, image: np.ndarray, language: str = "fra") -> Dict:
        """
        Extrait les données structurées avec positions
        
        Args:
            image: Image à traiter
            language: Langue pour l'OCR
            
        Returns:
            Dictionnaire avec texte et positions
        """
        try:
            config = self._get_ocr_config()
            
            # Extraction des données avec positions
            data = pytesseract.image_to_data(
                image, 
                lang=language, 
                config=config,
                output_type=pytesseract.Output.DICT
            )
            
            # Structuration des données
            structured_data = {
                'words': [],
                'lines': [],
                'paragraphs': []
            }
            
            current_line = []
            current_paragraph = []
            
            for i in range(len(data['text'])):
                if int(data['conf'][i]) > settings.confidence_threshold * 100:
                    word_info = {
                        'text': data['text'][i],
                        'confidence': float(data['conf'][i]) / 100.0,
                        'bbox': (
                            data['left'][i], 
                            data['top'][i], 
                            data['left'][i] + data['width'][i], 
                            data['top'][i] + data['height'][i]
                        ),
                        'level': data['level'][i]
                    }
                    
                    structured_data['words'].append(word_info)
                    
                    # Groupement par lignes
                    if data['level'][i] == 5:  # Niveau mot
                        current_line.append(word_info)
                    elif current_line:
                        structured_data['lines'].append(current_line)
                        current_line = []
            
            # Ajouter la dernière ligne
            if current_line:
                structured_data['lines'].append(current_line)
            
            return structured_data
            
        except Exception as e:
            app_logger.error(f"Erreur lors de l'extraction structurée: {str(e)}")
            raise OCRProcessingError(f"Échec de l'extraction structurée: {str(e)}")
