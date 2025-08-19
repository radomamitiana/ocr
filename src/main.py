"""
Point d'entrée principal de l'application FastAPI
"""

import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from contextlib import asynccontextmanager

from src.api.routes import router
from src.config.settings import settings
from src.utils.logger import app_logger, setup_logger
from src.utils.exceptions import OCRError


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gestionnaire de cycle de vie de l'application"""
    # Startup
    app_logger.info("Démarrage de l'application OCR Factures")
    app_logger.info(f"Version: {settings.app_version}")
    app_logger.info(f"Mode debug: {settings.debug}")
    
    yield
    
    # Shutdown
    app_logger.info("Arrêt de l'application OCR Factures")


# Création de l'application FastAPI
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="API REST pour l'extraction automatique de données de factures via OCR et LLM",
    docs_url="/api/v1/docs",
    redoc_url="/api/v1/redoc",
    openapi_url="/api/v1/openapi.json",
    lifespan=lifespan
)

# Configuration CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En production, spécifier les domaines autorisés
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Inclusion des routes avec préfixe
app.include_router(router, prefix="/api/v1", tags=["OCR Factures"])


# Gestionnaires d'erreurs globaux

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Gestionnaire d'erreurs de validation"""
    app_logger.error(f"Erreur de validation: {exc}")
    return JSONResponse(
        status_code=422,
        content={
            "status": "error",
            "error_code": "VALIDATION_ERROR",
            "message": "Erreur de validation des données",
            "details": exc.errors()
        }
    )


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """Gestionnaire d'erreurs HTTP"""
    app_logger.error(f"Erreur HTTP {exc.status_code}: {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "status": "error",
            "error_code": f"HTTP_{exc.status_code}",
            "message": exc.detail
        }
    )


@app.exception_handler(OCRError)
async def ocr_exception_handler(request: Request, exc: OCRError):
    """Gestionnaire d'erreurs OCR personnalisées"""
    app_logger.error(f"Erreur OCR: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "status": "error",
            "error_code": "OCR_ERROR",
            "message": str(exc)
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Gestionnaire d'erreurs générales"""
    app_logger.error(f"Erreur non gérée: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "status": "error",
            "error_code": "INTERNAL_ERROR",
            "message": "Erreur interne du serveur"
        }
    )


# Middleware de logging des requêtes
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Middleware pour logger les requêtes"""
    start_time = time.time()
    
    # Log de la requête entrante
    app_logger.info(f"Requête: {request.method} {request.url}")
    
    # Traitement de la requête
    response = await call_next(request)
    
    # Log de la réponse
    process_time = time.time() - start_time
    app_logger.info(
        f"Réponse: {response.status_code} - "
        f"Temps de traitement: {process_time:.2f}s"
    )
    
    return response


# Route racine
@app.get("/", include_in_schema=False)
async def root():
    """Route racine avec redirection vers la documentation"""
    return {
        "message": "API OCR Factures",
        "version": settings.app_version,
        "documentation": "/api/v1/docs",
        "health": "/api/v1/health"
    }


# Point d'entrée pour le développement
if __name__ == "__main__":
    import time
    
    uvicorn.run(
        "src.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.reload,
        log_level=settings.log_level.lower()
    )
