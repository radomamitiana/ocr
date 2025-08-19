#!/bin/bash

# Script de démarrage pour l'API OCR Factures

echo "🚀 Démarrage de l'API OCR Factures..."

# Vérification de Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 n'est pas installé. Veuillez l'installer d'abord."
    echo "   Sur macOS: brew install python3"
    echo "   Sur Ubuntu: sudo apt-get install python3 python3-pip"
    exit 1
fi

# Vérification de pip
if ! command -v pip3 &> /dev/null; then
    echo "❌ pip3 n'est pas installé. Veuillez l'installer d'abord."
    exit 1
fi

# Installation des dépendances
echo "📦 Installation des dépendances Python..."
pip3 install -r requirements.txt

# Création des répertoires nécessaires
mkdir -p data/temp logs

# Copie du fichier de configuration
if [ ! -f .env ]; then
    cp .env.example .env
    echo "✅ Fichier .env créé à partir de .env.example"
fi

# Démarrage de l'API
echo "🌟 Démarrage de l'API sur http://localhost:8000"
echo "📚 Documentation disponible sur http://localhost:8000/api/v1/docs"
echo ""
echo "Pour arrêter l'API, appuyez sur Ctrl+C"
echo ""

python3 -m uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload
