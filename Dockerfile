# Dockerfile pour l'application OCR Factures
FROM python:3.11-slim

# Installation des dépendances système
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    tesseract-ocr-fra \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    libglib2.0-0 \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

# Définition du répertoire de travail
WORKDIR /app

# Copie des fichiers de dépendances
COPY requirements.txt .

# Installation des dépendances Python
RUN pip install --no-cache-dir -r requirements.txt

# Copie du code source
COPY src/ ./src/
COPY .env.example .env

# Création des répertoires nécessaires
RUN mkdir -p data/temp logs

# Exposition du port
EXPOSE 8000

# Variables d'environnement
ENV PYTHONPATH=/app
ENV TESSERACT_CMD=/usr/bin/tesseract

# Commande de démarrage
CMD ["python", "-m", "uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
