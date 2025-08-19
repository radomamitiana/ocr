# OCR Factures API

API REST pour l'extraction automatique de données de factures via OCR et LLM.

## 🚀 Fonctionnalités

- **Extraction OCR** : Utilise Tesseract pour extraire le texte des images
- **Preprocessing intelligent** : Amélioration automatique de la qualité d'image
- **Extraction de données** : Reconnaissance intelligente des champs de facture
- **API REST** : Interface simple et documentée
- **Formats supportés** : PNG, JPG, JPEG, PDF
- **Validation** : Vérification de cohérence des données extraites

## 📋 Prérequis

- Python 3.11+
- Tesseract OCR
- Docker (optionnel)

## 🛠️ Installation

### Installation locale

1. **Cloner le projet**
```bash
git clone <repository-url>
cd ocr_factures
```

2. **Installer les dépendances système (Ubuntu/Debian)**
```bash
sudo apt-get update
sudo apt-get install tesseract-ocr tesseract-ocr-fra poppler-utils
```

3. **Installer les dépendances Python**
```bash
pip install -r requirements.txt
```

4. **Configuration**
```bash
cp .env.example .env
# Modifier .env selon vos besoins
```

5. **Lancer l'application**
```bash
cd ocr_factures
python -m uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload
```

### Installation avec Docker

1. **Construire et lancer**
```bash
docker-compose up --build
```

## 🔧 Utilisation

### API Endpoints

- **POST** `/api/v1/process-invoice` - Traiter une facture
- **GET** `/api/v1/health` - Vérification de santé
- **GET** `/api/v1/version` - Informations de version
- **GET** `/api/v1/docs` - Documentation Swagger

### Exemple avec curl

```bash
curl -X POST "http://localhost:8000/api/v1/process-invoice" \
     -H "accept: application/json" \
     -H "Content-Type: multipart/form-data" \
     -F "file=@facture.pdf"
```

### Exemple avec Postman

1. **URL** : `POST http://localhost:8000/api/v1/process-invoice`
2. **Headers** : `Content-Type: multipart/form-data`
3. **Body** : 
   - Type: `form-data`
   - Key: `file` (type: File)
   - Value: Sélectionner votre fichier de facture

### Réponse JSON

```json
{
  "status": "success",
  "processing_time": 15.2,
  "data": {
    "metadata": {
      "filename": "facture.pdf",
      "processing_date": "2025-08-19T11:30:00",
      "confidence_score": 0.95,
      "processing_time": 15.2
    },
    "supplier": {
      "name": "Entreprise ABC",
      "siret": "12345678901234",
      "vat_number": "FR12345678901"
    },
    "invoice": {
      "number": "F2025-001",
      "date": "2025-08-19",
      "currency": "EUR"
    },
    "totals": {
      "total_incl_vat": 1200.00,
      "amount_due": 1200.00
    }
  }
}
```

## 🧪 Tests

### Tests avec Postman

1. **Santé de l'API**
   - GET `http://localhost:8000/api/v1/health`
   - Réponse attendue : `{"status": "healthy", ...}`

2. **Documentation**
   - GET `http://localhost:8000/api/v1/docs`
   - Interface Swagger interactive

3. **Traitement de facture**
   - POST `http://localhost:8000/api/v1/process-invoice`
   - Uploader un fichier de facture

## 📁 Structure du Projet

```
ocr_factures/
├── src/
│   ├── api/                 # Routes et modèles API
│   ├── config/              # Configuration
│   ├── preprocessing/       # Traitement d'images
│   ├── ocr/                # Moteur OCR
│   ├── extraction/         # Extraction de données
│   ├── validation/         # Validation des données
│   ├── output/             # Formatage des réponses
│   └── utils/              # Utilitaires
├── tests/                  # Tests unitaires
├── data/                   # Données temporaires
├── logs/                   # Fichiers de logs
├── requirements.txt        # Dépendances Python
├── Dockerfile             # Configuration Docker
├── docker-compose.yml     # Orchestration Docker
└── README.md              # Documentation
```

## ⚙️ Configuration

Variables d'environnement principales :

```env
# Serveur
HOST=0.0.0.0
PORT=8000
DEBUG=false

# OCR
TESSERACT_CMD=/usr/bin/tesseract
OCR_LANGUAGE=fra
CONFIDENCE_THRESHOLD=0.8

# Fichiers
MAX_FILE_SIZE=10485760  # 10MB
UPLOAD_DIR=data/temp

# Logs
LOG_LEVEL=INFO
LOG_FILE=logs/app.log
```

## 🐛 Dépannage

### Erreurs communes

1. **Tesseract non trouvé**
   - Vérifier l'installation : `tesseract --version`
   - Configurer le chemin dans `.env`

2. **Erreur de dépendances**
   - Réinstaller : `pip install -r requirements.txt`

3. **Erreur de permissions**
   - Vérifier les droits sur les dossiers `data/` et `logs/`

### Logs

Les logs sont disponibles dans :
- Console (développement)
- Fichier `logs/app.log` (production)

## 📊 Performance

- **Temps de traitement** : < 30 secondes par facture
- **Formats supportés** : PNG, JPG, JPEG, PDF
- **Taille maximale** : 10MB par fichier
- **Précision** : > 95% sur les champs critiques

## 🔒 Sécurité

- Validation des fichiers uploadés
- Nettoyage automatique des fichiers temporaires
- Gestion sécurisée des erreurs
- Rate limiting configurable

## 📝 Licence

Ce projet est sous licence MIT.

## 🤝 Contribution

1. Fork le projet
2. Créer une branche feature
3. Commit les changements
4. Push vers la branche
5. Ouvrir une Pull Request

## 📞 Support

Pour toute question ou problème :
- Créer une issue sur GitHub
- Consulter la documentation API : `/api/v1/docs`
