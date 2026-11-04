# Image Python légère pour Debian
FROM python:3.12-slim-bookworm

# Variables d'environnement Python
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Installation des dépendances système si nécessaire
RUN apt-get update && apt-get install -y --no-install-recommends \
    sqlite3 \
    && rm -rf /var/lib/apt/lists/*

# Installation des dépendances Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copie du code source
COPY src/ ./src/
COPY main.py .

# Création du dossier pour la base SQLite
RUN mkdir -p /app/data

# Commande d'exécution
CMD ["python", "main.py"]
