"""
Exceptions personnalisées pour l'application
"""


class OCRError(Exception):
    """Exception de base pour les erreurs OCR"""
    pass


class FileProcessingError(OCRError):
    """Erreur lors du traitement de fichier"""
    pass


class InvalidFileFormatError(FileProcessingError):
    """Format de fichier non supporté"""
    pass


class FileSizeError(FileProcessingError):
    """Fichier trop volumineux"""
    pass


class OCRProcessingError(OCRError):
    """Erreur lors du traitement OCR"""
    pass


class DataExtractionError(OCRError):
    """Erreur lors de l'extraction de données"""
    pass


class ValidationError(OCRError):
    """Erreur de validation des données"""
    pass


class ConfigurationError(OCRError):
    """Erreur de configuration"""
    pass
