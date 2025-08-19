"""
Processeur spécialisé pour les fichiers PDF
"""

import numpy as np
import pdf2image
from pathlib import Path
from typing import List, Optional
from src.interfaces.processors import FileProcessor
from src.utils.logger import app_logger
from src.utils.exceptions import FileProcessingError


class PDFProcessor:
    """Processeur spécialisé pour les fichiers PDF"""
    
    def __init__(self, dpi: int = 300, first_page: int = 1, last_page: Optional[int] = None):
        """
        Initialise le processeur PDF
        
        Args:
            dpi: Résolution pour la conversion
            first_page: Première page à convertir
            last_page: Dernière page à convertir (None pour toutes)
        """
        self.dpi = dpi
        self.first_page = first_page
        self.last_page = last_page
        self.supported_extensions = ['pdf']
    
    def can_process(self, file_path: str) -> bool:
        """Vérifie si le processeur peut traiter ce type de fichier"""
        extension = Path(file_path).suffix.lower().lstrip('.')
        return extension in self.supported_extensions
    
    def process(self, file_path: str) -> np.ndarray:
        """
        Traite le fichier PDF et retourne l'image de la première page
        
        Args:
            file_path: Chemin vers le fichier PDF
            
        Returns:
            Image sous forme de numpy array
            
        Raises:
            FileProcessingError: Si la conversion échoue
        """
        try:
            app_logger.info(f"Conversion PDF en cours: {file_path}")
            
            pages = pdf2image.convert_from_path(
                file_path,
                dpi=self.dpi,
                first_page=self.first_page,
                last_page=self.last_page or self.first_page
            )
            
            if not pages:
                raise FileProcessingError("Aucune page trouvée dans le PDF")
            
            # Convertir la première page en numpy array
            pil_image = pages[0]
            image_array = np.array(pil_image)
            
            app_logger.info(f"PDF converti avec succès - Taille: {image_array.shape}")
            return image_array
            
        except Exception as e:
            app_logger.error(f"Erreur lors de la conversion PDF: {str(e)}")
            raise FileProcessingError(f"Impossible de convertir le PDF: {str(e)}")
    
    def process_all_pages(self, file_path: str) -> List[np.ndarray]:
        """
        Traite toutes les pages du PDF
        
        Args:
            file_path: Chemin vers le fichier PDF
            
        Returns:
            Liste des images (une par page)
        """
        try:
            app_logger.info(f"Conversion de toutes les pages PDF: {file_path}")
            
            pages = pdf2image.convert_from_path(file_path, dpi=self.dpi)
            
            if not pages:
                raise FileProcessingError("Aucune page trouvée dans le PDF")
            
            images = []
            for i, page in enumerate(pages):
                image_array = np.array(page)
                images.append(image_array)
                app_logger.debug(f"Page {i+1} convertie - Taille: {image_array.shape}")
            
            app_logger.info(f"PDF converti avec succès - {len(images)} pages")
            return images
            
        except Exception as e:
            app_logger.error(f"Erreur lors de la conversion PDF: {str(e)}")
            raise FileProcessingError(f"Impossible de convertir le PDF: {str(e)}")
    
    def get_page_count(self, file_path: str) -> int:
        """
        Retourne le nombre de pages du PDF
        
        Args:
            file_path: Chemin vers le fichier PDF
            
        Returns:
            Nombre de pages
        """
        try:
            # Conversion rapide pour compter les pages
            pages = pdf2image.convert_from_path(file_path, dpi=72)  # DPI faible pour la vitesse
            return len(pages)
            
        except Exception as e:
            app_logger.error(f"Erreur lors du comptage des pages: {str(e)}")
            raise FileProcessingError(f"Impossible de compter les pages du PDF: {str(e)}")
