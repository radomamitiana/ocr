"""
Interfaces pour les processeurs de documents
"""

from abc import ABC, abstractmethod
from typing import Protocol, runtime_checkable, Dict, Any
import numpy as np
from src.api.models import InvoiceData


@runtime_checkable
class FileProcessor(Protocol):
    """Interface pour les processeurs de fichiers"""
    
    def can_process(self, file_path: str) -> bool:
        """Vérifie si le processeur peut traiter ce type de fichier"""
        ...
    
    def process(self, file_path: str) -> np.ndarray:
        """Traite le fichier et retourne l'image"""
        ...


class ImageProcessorInterface(ABC):
    """Interface abstraite pour le preprocessing d'images"""
    
    @abstractmethod
    def process_file(self, file_path: str) -> np.ndarray:
        """Traite un fichier et retourne l'image préprocessée"""
        pass
    
    @abstractmethod
    def preprocess_image(self, image: np.ndarray) -> np.ndarray:
        """Applique les traitements de préprocessing"""
        pass


class OCREngineInterface(ABC):
    """Interface abstraite pour les moteurs OCR"""
    
    @abstractmethod
    def extract_text(self, image: np.ndarray, language: str = "fra") -> Dict[str, Any]:
        """Extrait le texte d'une image"""
        pass
    
    @abstractmethod
    def extract_structured_data(self, image: np.ndarray, language: str = "fra") -> Dict[str, Any]:
        """Extrait les données structurées avec positions"""
        pass


class DataExtractorInterface(ABC):
    """Interface abstraite pour l'extraction de données"""
    
    @abstractmethod
    def extract_invoice_data(self, text: str, structured_data: Dict = None) -> InvoiceData:
        """Extrait les données de facture du texte OCR"""
        pass


class ValidatorInterface(ABC):
    """Interface abstraite pour la validation des données"""
    
    @abstractmethod
    def validate(self, invoice_data: InvoiceData) -> bool:
        """Valide les données extraites"""
        pass
    
    @abstractmethod
    def get_validation_errors(self, invoice_data: InvoiceData) -> list:
        """Retourne la liste des erreurs de validation"""
        pass
