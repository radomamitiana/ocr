"""
Routes de l'API REST pour le traitement des factures
"""

import os
import time
import tempfile
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, status
from fastapi.responses import JSONResponse
from src.api.models import *
from src.api.invoice_models import InvoiceResponse
from src.services.invoice_service import get_invoice_service
from src.config.settings import settings
from src.preprocessing.enhanced_image_processor import EnhancedImageProcessor
from src.ocr.ocr_engine import OCREngine
from src.extraction.data_extractor import DataExtractor
from src.extraction.ml_enhanced_extractor import MLEnhancedExtractor
from src.utils.logger import app_logger
from src.utils.exceptions import *


# Création du routeur
router = APIRouter()

# Instances des processeurs
image_processor = EnhancedImageProcessor()
ocr_engine = OCREngine()
data_extractor = DataExtractor()
ml_extractor = MLEnhancedExtractor()


@router.post(
    "/process-invoice",
    response_model=InvoiceResponse,
    status_code=status.HTTP_200_OK,
    summary="Traite une facture et extrait les données",
    description="Upload d'une image de facture (PNG, JPG, JPEG, PDF) et extraction automatique des données structurées avec sauvegarde en base"
)
async def process_invoice(
    file: UploadFile = File(..., description="Fichier image de la facture"),
    options: Optional[str] = Form(None, description="Options de traitement au format JSON")
):
    """
    Endpoint principal pour traiter une facture
    
    Args:
        file: Fichier image uploadé
        options: Options de traitement (optionnel)
        
    Returns:
        Données extraites de la facture au format JSON
    """
    start_time = time.time()
    temp_file_path = None
    
    try:
        app_logger.info(f"Début du traitement de la facture: {file.filename}")
        
        # Validation du fichier
        _validate_file(file)
        
        # Parsing des options
        processing_options = _parse_options(options)
        
        # Sauvegarde temporaire du fichier
        temp_file_path = await _save_temp_file(file)
        
        # Preprocessing de l'image
        processed_image = image_processor.process_file(temp_file_path)
        
        # Extraction OCR
        ocr_result = ocr_engine.extract_text(
            processed_image, 
            language=processing_options.language
        )
        
        # Extraction des données structurées
        structured_data = ocr_engine.extract_structured_data(
            processed_image,
            language=processing_options.language
        )
        
        # Extraction des données de facture avec ML amélioré
        invoice_data = ml_extractor.extract_invoice_data_with_ml(
            ocr_result.text,
            structured_data,
            file.filename
        )
        
        # Mise à jour des métadonnées
        processing_time = time.time() - start_time
        invoice_data.metadata.filename = file.filename
        invoice_data.metadata.processing_time = processing_time
        invoice_data.metadata.confidence_score = ocr_result.confidence
        
        # Validation si demandée - temporairement désactivée pour debug
        # if processing_options.enable_validation:
        #     _validate_extracted_data(invoice_data, processing_options.confidence_threshold)
        
        # Création de la facture en base de données via le service
        invoice_service = get_invoice_service()
        invoice_dto = invoice_service.create_invoice_from_extracted_data(
            invoice_data, 
            file.filename,
            ocr_result.text  # Passage du texte brut pour l'extraction améliorée
        )
        
        app_logger.info(f"Traitement terminé en {processing_time:.2f}s")
        
        return InvoiceResponse(
            status="success",
            processing_time=processing_time,
            invoice=invoice_dto
        )
        
    except InvalidFileFormatError as e:
        app_logger.error(f"Format de fichier invalide: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "status": "error",
                "error_code": "INVALID_FILE_FORMAT",
                "message": str(e),
                "details": {
                    "supported_formats": settings.allowed_extensions,
                    "received_format": file.filename.split('.')[-1] if file.filename else "unknown"
                }
            }
        )
        
    except FileSizeError as e:
        app_logger.error(f"Fichier trop volumineux: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail={
                "status": "error",
                "error_code": "FILE_TOO_LARGE",
                "message": str(e),
                "details": {
                    "max_size_mb": settings.max_file_size / (1024 * 1024)
                }
            }
        )
        
    except (OCRProcessingError, DataExtractionError) as e:
        app_logger.error(f"Erreur de traitement: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "status": "error",
                "error_code": "PROCESSING_ERROR",
                "message": "Impossible d'extraire les données de la facture",
                "details": {"error": str(e)}
            }
        )
        
    except Exception as e:
        app_logger.error(f"Erreur interne: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "status": "error",
                "error_code": "INTERNAL_ERROR",
                "message": "Erreur interne du serveur",
                "details": {"error": str(e)}
            }
        )
        
    finally:
        # Nettoyage du fichier temporaire
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                os.unlink(temp_file_path)
            except Exception as e:
                app_logger.warning(f"Impossible de supprimer le fichier temporaire: {str(e)}")


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Vérification de l'état de l'API",
    description="Endpoint de santé pour vérifier que l'API fonctionne correctement"
)
async def health_check():
    """Endpoint de vérification de santé"""
    return HealthResponse()


@router.get(
    "/version",
    response_model=VersionResponse,
    summary="Informations de version",
    description="Retourne les informations de version de l'API"
)
async def get_version():
    """Endpoint d'information de version"""
    return VersionResponse()


# Fonctions utilitaires

def _validate_file(file: UploadFile):
    """Valide le fichier uploadé"""
    if not file.filename:
        raise InvalidFileFormatError("Nom de fichier manquant")
    
    # Vérification de l'extension
    file_extension = file.filename.split('.')[-1].lower()
    if file_extension not in settings.allowed_extensions:
        raise InvalidFileFormatError(
            f"Format {file_extension} non supporté. "
            f"Formats acceptés: {', '.join(settings.allowed_extensions)}"
        )
    
    # Vérification de la taille (approximative basée sur les headers)
    if hasattr(file, 'size') and file.size and file.size > settings.max_file_size:
        raise FileSizeError(
            f"Fichier trop volumineux ({file.size} bytes). "
            f"Taille maximale: {settings.max_file_size} bytes"
        )


def _parse_options(options_str: Optional[str]) -> ProcessingOptions:
    """Parse les options de traitement"""
    if not options_str:
        return ProcessingOptions()
    
    try:
        import json
        options_dict = json.loads(options_str)
        return ProcessingOptions(**options_dict)
    except (json.JSONDecodeError, ValueError) as e:
        app_logger.warning(f"Options invalides, utilisation des valeurs par défaut: {str(e)}")
        return ProcessingOptions()


async def _save_temp_file(file: UploadFile) -> str:
    """Sauvegarde le fichier uploadé temporairement"""
    try:
        # Création du répertoire temporaire si nécessaire
        temp_dir = Path(settings.upload_dir)
        temp_dir.mkdir(parents=True, exist_ok=True)
        
        # Génération d'un nom de fichier temporaire
        file_extension = file.filename.split('.')[-1].lower()
        temp_file = tempfile.NamedTemporaryFile(
            delete=False,
            suffix=f".{file_extension}",
            dir=temp_dir
        )
        
        # Lecture et écriture du contenu
        content = await file.read()
        
        # Vérification de la taille réelle
        if len(content) > settings.max_file_size:
            raise FileSizeError(
                f"Fichier trop volumineux ({len(content)} bytes). "
                f"Taille maximale: {settings.max_file_size} bytes"
            )
        
        temp_file.write(content)
        temp_file.close()
        
        return temp_file.name
        
    except Exception as e:
        raise FileProcessingError(f"Impossible de sauvegarder le fichier: {str(e)}")


def _validate_extracted_data(invoice_data: InvoiceData, confidence_threshold: float):
    """Valide les données extraites"""
    if invoice_data.metadata.confidence_score < confidence_threshold:
        raise DataExtractionError(
            f"Confiance trop faible ({invoice_data.metadata.confidence_score:.2f} < {confidence_threshold})"
        )
    
    if not invoice_data.validation or not invoice_data.validation.required_fields_present:
        raise DataExtractionError("Champs requis manquants dans la facture")
