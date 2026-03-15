# Stage 1: Builder
FROM python:3.9-slim as builder

WORKDIR /app

# Installer les dépendances système
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copier requirements et installer les dépendances Python
COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

# Stage 2: Runtime
FROM python:3.9-slim

WORKDIR /app

# Installer les dépendances système runtime
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copier les dépendances Python depuis le builder
COPY --from=builder /root/.local /root/.local

# Ajouter le répertoire local au PATH
ENV PATH=/root/.local/bin:$PATH

# Copier le code de l'application
COPY . .

# Créer les répertoires nécessaires
RUN mkdir -p logs static media

# Collecter les fichiers statiques
RUN python manage.py collectstatic --noinput || true

# Exposer le port
EXPOSE 8000

# Commande de démarrage
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "4", "--timeout", "120"]
