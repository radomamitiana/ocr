# Cahier des Charges - Projet OCR Factures

## 1. Présentation du Projet

### 1.1 Contexte
Développement d'une solution Python d'OCR (Reconnaissance Optique de Caractères) pour automatiser le traitement des factures comptables. Le système doit extraire les données des factures sous format image et les structurer en format JSON exploitable.

### 1.2 Objectifs
- Automatiser la saisie des données de factures via une API REST
- Réduire les erreurs de saisie manuelle
- Accélérer le processus de traitement comptable
- Fournir des données structurées et exploitables
- Permettre l'intégration facile avec des systèmes externes

## 2. Spécifications Fonctionnelles

### 2.1 Fonctionnalités Principales

#### 2.1.1 Traitement d'Images
- **Entrée** : Fichiers images (PNG, JPG, JPEG, PDF)
- **Formats supportés** : 
  - Images haute résolution (minimum 300 DPI recommandé)
  - Documents scannés
  - Photos de factures
- **Préprocessing** :
  - Correction de l'orientation
  - Amélioration de la qualité d'image
  - Détection et correction de l'inclinaison
  - Normalisation des contrastes

#### 2.1.2 Extraction de Données
Les données suivantes doivent être extraites :

**Informations Fournisseur :**
- Nom/Raison sociale
- Adresse complète
- SIRET/SIREN
- Numéro de TVA intracommunautaire
- Téléphone/Email

**Informations Client :**
- Nom/Raison sociale du client
- Adresse de facturation
- Numéro client

**Informations Facture :**
- Numéro de facture
- Date d'émission
- Date d'échéance
- Devise
- Conditions de paiement

**Détails Produits/Services :**
- Description des articles/services
- Quantités
- Prix unitaires
- Taux de TVA
- Montants HT/TTC

**Totaux :**
- Montant HT total
- Montant TVA (par taux)
- Montant TTC total
- Montant à payer

#### 2.1.3 Structuration des Données
**Format de sortie JSON :**
```json
{
  "metadata": {
    "filename": "string",
    "processing_date": "ISO 8601",
    "confidence_score": "float",
    "processing_time": "float"
  },
  "supplier": {
    "name": "string",
    "address": {
      "street": "string",
      "city": "string",
      "postal_code": "string",
      "country": "string"
    },
    "siret": "string",
    "vat_number": "string",
    "contact": {
      "phone": "string",
      "email": "string"
    }
  },
  "customer": {
    "name": "string",
    "address": {
      "street": "string",
      "city": "string",
      "postal_code": "string",
      "country": "string"
    },
    "customer_id": "string"
  },
  "invoice": {
    "number": "string",
    "date": "YYYY-MM-DD",
    "due_date": "YYYY-MM-DD",
    "currency": "string",
    "payment_terms": "string"
  },
  "line_items": [
    {
      "description": "string",
      "quantity": "float",
      "unit_price": "float",
      "vat_rate": "float",
      "amount_excl_vat": "float",
      "vat_amount": "float",
      "amount_incl_vat": "float"
    }
  ],
  "totals": {
    "subtotal_excl_vat": "float",
    "total_vat": "float",
    "total_incl_vat": "float",
    "amount_due": "float"
  },
  "validation": {
    "calculation_check": "boolean",
    "required_fields_present": "boolean",
    "data_quality_score": "float"
  }
}
```

### 2.2 Fonctionnalités Secondaires

#### 2.2.1 Traitement par Lots
- Traitement de multiples factures simultanément
- Génération de rapports de traitement
- Gestion des erreurs par fichier

#### 2.2.2 Validation et Contrôle Qualité
- Vérification de cohérence des calculs
- Score de confiance par champ extrait
- Signalement des anomalies détectées

#### 2.2.3 Interface API REST
- **Endpoint principal** : `POST /api/v1/process-invoice`
- **Input** : Fichier image (multipart/form-data)
- **Output** : Objet JSON structuré
- **Pas d'authentification** : Accès libre pour intégration externe
- **Documentation API** : Swagger/OpenAPI automatique
- **Logs détaillés** : Traçabilité complète des traitements

## 3. Spécifications Techniques

### 3.1 API REST

#### 3.1.1 Endpoints

**Endpoint Principal :**
```
POST /api/v1/process-invoice
Content-Type: multipart/form-data
```

**Paramètres d'entrée :**
- `file` (required) : Fichier image (PNG, JPG, JPEG, PDF)
- `options` (optional) : Paramètres de traitement JSON
  ```json
  {
    "language": "fra",
    "confidence_threshold": 0.8,
    "enable_validation": true
  }
  ```

**Réponse de succès (200) :**
```json
{
  "status": "success",
  "processing_time": 15.2,
  "data": {
    // Structure JSON complète définie en section 2.1.3
  }
}
```

**Réponse d'erreur (400/500) :**
```json
{
  "status": "error",
  "error_code": "INVALID_FILE_FORMAT",
  "message": "Format de fichier non supporté",
  "details": {
    "supported_formats": ["PNG", "JPG", "JPEG", "PDF"],
    "received_format": "GIF"
  }
}
```

**Endpoints Secondaires :**
```
GET /api/v1/health          # Status de l'API
GET /api/v1/version         # Version de l'application
GET /api/v1/docs           # Documentation Swagger
```

#### 3.1.2 Gestion des Erreurs
- **400 Bad Request** : Fichier manquant ou format invalide
- **413 Payload Too Large** : Fichier trop volumineux (>10MB)
- **422 Unprocessable Entity** : Impossible d'extraire les données
- **500 Internal Server Error** : Erreur de traitement interne
- **503 Service Unavailable** : Service temporairement indisponible

#### 3.1.3 Limitations et Contraintes
- **Taille maximale** : 10MB par fichier
- **Formats supportés** : PNG, JPG, JPEG, PDF
- **Timeout** : 60 secondes maximum par requête
- **Rate limiting** : 100 requêtes/minute par IP (configurable)

### 3.2 Architecture du Système

#### 3.2.1 Structure du Projet
```
ocr_factures/
├── src/
│   ├── __init__.py
│   ├── main.py                    # Point d'entrée FastAPI
│   ├── api/
│   │   ├── __init__.py
│   │   ├── routes.py              # Endpoints API REST
│   │   ├── models.py              # Modèles Pydantic
│   │   └── middleware.py          # Middleware (CORS, logging)
│   ├── config/
│   │   ├── __init__.py
│   │   └── settings.py
│   ├── preprocessing/
│   │   ├── __init__.py
│   │   ├── image_processor.py
│   │   └── document_enhancer.py
│   ├── ocr/
│   │   ├── __init__.py
│   │   ├── ocr_engine.py
│   │   └── llm_processor.py
│   ├── extraction/
│   │   ├── __init__.py
│   │   ├── data_extractor.py
│   │   └── field_parser.py
│   ├── validation/
│   │   ├── __init__.py
│   │   ├── data_validator.py
│   │   └── calculation_checker.py
│   ├── output/
│   │   ├── __init__.py
│   │   ├── json_formatter.py
│   │   └── response_builder.py
│   └── utils/
│       ├── __init__.py
│       ├── logger.py
│       ├── helpers.py
│       └── exceptions.py
├── tests/
│   ├── __init__.py
│   ├── test_api.py                # Tests API REST
│   ├── test_preprocessing.py
│   ├── test_ocr.py
│   ├── test_extraction.py
│   └── test_validation.py
├── data/
│   ├── temp/                      # Fichiers temporaires
│   ├── models/                    # Modèles ML
│   └── samples/                   # Échantillons de test
├── docs/
│   ├── README.md
│   ├── API.md
│   └── DEPLOYMENT.md
├── requirements.txt
├── setup.py
├── .env.example
├── .gitignore
├── Dockerfile
└── docker-compose.yml
```

#### 3.2.2 Technologies et Bibliothèques

**API REST :**
- `FastAPI` : Framework API REST principal
- `uvicorn` : Serveur ASGI pour FastAPI
- `python-multipart` : Support multipart/form-data
- `slowapi` : Rate limiting pour FastAPI

**OCR et Traitement d'Images :**
- `Tesseract OCR` : Moteur OCR principal
- `pytesseract` : Interface Python pour Tesseract
- `OpenCV` : Traitement et préprocessing d'images
- `Pillow (PIL)` : Manipulation d'images
- `pdf2image` : Conversion PDF vers images

**LLM et IA :**
- `transformers` : Modèles Hugging Face
- `torch` : Framework PyTorch
- `langchain` : Framework pour applications LLM
- Modèles spécialisés : `microsoft/layoutlm-base-uncased` ou équivalent

**Traitement de Données :**
- `pandas` : Manipulation de données
- `numpy` : Calculs numériques
- `pydantic` : Validation de données et modèles API
- `jsonschema` : Validation de schémas JSON

**Monitoring et Logs :**
- `loguru` : Système de logs avancé
- `prometheus-client` : Métriques (optionnel)
- `structlog` : Logs structurés

### 3.3 Intégration LLM

#### 3.3.1 Modèle Recommandé
- **Modèle principal** : LayoutLM ou équivalent spécialisé dans les documents
- **Modèle de fallback** : GPT-3.5/4 via API ou modèle local
- **Fine-tuning** : Entraînement sur dataset de factures françaises

#### 3.3.2 Pipeline de Traitement
1. **OCR Traditionnel** : Extraction du texte brut
2. **Analyse Layout** : Compréhension de la structure du document
3. **LLM Processing** : Extraction intelligente des champs
4. **Post-processing** : Validation et formatage

### 3.4 Performance et Scalabilité

#### 3.4.1 Exigences de Performance
- Temps de traitement : < 30 secondes par facture
- Précision d'extraction : > 95% pour les champs critiques
- Support concurrent : 5 factures simultanées minimum
- Disponibilité API : 99.5% uptime minimum

#### 3.4.2 Gestion des Ressources
- Utilisation mémoire optimisée
- Support GPU optionnel pour l'accélération
- Cache intelligent pour les modèles
- Load balancing pour haute disponibilité

## 4. Bonnes Pratiques de Développement

### 4.1 Standards de Code

#### 4.1.1 Style et Formatage
- **PEP 8** : Respect strict des conventions Python
- **Black** : Formatage automatique du code
- **isort** : Organisation des imports
- **flake8** : Linting et vérification de style

#### 4.1.2 Documentation
- **Docstrings** : Documentation complète des fonctions/classes
- **Type Hints** : Annotations de type systématiques
- **README** : Documentation utilisateur complète
- **API Documentation** : Documentation technique détaillée

#### 4.1.3 Tests
- **pytest** : Framework de tests
- **Coverage** : Couverture de code > 80%
- **Tests unitaires** : Chaque module testé individuellement
- **Tests d'intégration** : Tests end-to-end
- **Tests de performance** : Benchmarks de vitesse

### 4.2 Gestion de Projet

#### 4.2.1 Versioning
- **Git** : Contrôle de version
- **Semantic Versioning** : Numérotation des versions
- **Branches** : Feature branches + main/develop

#### 4.2.2 CI/CD
- **GitHub Actions** ou équivalent
- Tests automatiques sur push/PR
- Déploiement automatisé
- Vérification de qualité de code

#### 4.2.3 Configuration
- **Variables d'environnement** : Configuration externalisée
- **Fichiers de config** : YAML/JSON pour paramètres
- **Secrets management** : Gestion sécurisée des clés API

### 4.3 Sécurité et Confidentialité

#### 4.3.1 Protection des Données
- Chiffrement des données sensibles
- Anonymisation des données de test
- Conformité RGPD

#### 4.3.2 Sécurité du Code
- Validation des entrées utilisateur
- Gestion sécurisée des fichiers temporaires
- Audit des dépendances (safety, bandit)

## 5. Livrables

### 5.1 Code Source
- Application Python complète
- Tests unitaires et d'intégration
- Documentation technique
- Scripts de déploiement

### 5.2 Documentation
- Manuel utilisateur
- Guide d'installation
- Documentation API
- Guide de maintenance

### 5.3 Outils de Déploiement
- Dockerfile pour containerisation
- Requirements.txt avec versions figées
- Scripts d'installation automatisée
- Configuration d'exemple

## 6. Planning et Jalons

### 6.1 Phase 1 : Fondations (2 semaines)
- [ ] Setup du projet et architecture FastAPI
- [ ] Implémentation de l'API REST de base
- [ ] Implémentation du preprocessing d'images
- [ ] Intégration OCR de base
- [ ] Tests unitaires fondamentaux

### 6.2 Phase 2 : Intelligence (3 semaines)
- [ ] Intégration du modèle LLM
- [ ] Développement de l'extraction de données
- [ ] Implémentation de la validation
- [ ] Endpoints API complets
- [ ] Tests d'intégration API

### 6.3 Phase 3 : Optimisation (2 semaines)
- [ ] Optimisation des performances
- [ ] Gestion des erreurs et rate limiting
- [ ] Documentation API Swagger
- [ ] Tests de charge et performance

### 6.4 Phase 4 : Finalisation (1 semaine)
- [ ] Tests finaux de l'API
- [ ] Containerisation Docker
- [ ] Documentation utilisateur
- [ ] Déploiement en production

## 7. Critères d'Acceptation

### 7.1 Fonctionnels
- ✅ Extraction correcte des champs obligatoires (>95% précision)
- ✅ Format JSON conforme au schéma défini
- ✅ Traitement de tous les formats d'images supportés
- ✅ Validation des calculs de TVA et totaux

### 7.2 API REST
- ✅ Endpoint `POST /api/v1/process-invoice` fonctionnel
- ✅ Support multipart/form-data pour upload de fichiers
- ✅ Réponses JSON conformes aux spécifications
- ✅ Gestion d'erreurs HTTP appropriée (400, 413, 422, 500, 503)
- ✅ Documentation Swagger/OpenAPI accessible
- ✅ Rate limiting configuré et fonctionnel
- ✅ Pas d'authentification requise (accès libre)

### 7.3 Techniques
- ✅ Code respectant PEP 8 et bonnes pratiques
- ✅ Couverture de tests > 80%
- ✅ Tests API automatisés (pytest + FastAPI TestClient)
- ✅ Documentation complète
- ✅ Performance < 30s par facture
- ✅ Architecture FastAPI avec Pydantic

### 7.4 Qualité
- ✅ Gestion d'erreurs robuste
- ✅ Logs détaillés et exploitables
- ✅ Validation des entrées utilisateur
- ✅ Déploiement Docker fonctionnel
- ✅ Monitoring et métriques disponibles

## 8. Risques et Mitigation

### 8.1 Risques Techniques
- **Qualité variable des images** → Preprocessing avancé
- **Formats de factures hétérogènes** → LLM adaptatif
- **Performance du modèle** → Optimisation et cache

### 8.2 Risques Projet
- **Complexité sous-estimée** → Planning avec buffer
- **Disponibilité des ressources** → Architecture modulaire
- **Évolution des besoins** → Architecture flexible

## 9. Maintenance et Évolution

### 9.1 Maintenance
- Monitoring des performances
- Mise à jour des modèles
- Correction des bugs
- Support utilisateur

### 9.2 Évolutions Futures
- Support de nouveaux formats
- Amélioration de la précision
- Interface web avancée
- Intégration avec systèmes comptables

---

**Version** : 1.0  
**Date** : 19/08/2025  
**Auteur** : Assistant IA  
**Statut** : Draft
