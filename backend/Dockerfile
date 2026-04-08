# --- Stage 1: Build ---
FROM python:3.12-slim as builder

# Empêche Python d'écrire des fichiers .pyc et force l'affichage des logs en temps réel
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

WORKDIR /app

# Installation des dépendances système pour compiler psycopg2 ou d'autres libs
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Création d'un environnement virtuel propre
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# --- Stage 2: Runtime ---
FROM python:3.12-slim

WORKDIR /app

# On installe seulement le nécessaire pour faire tourner PostgreSQL (libpq5)
RUN apt-get update && apt-get install -y libpq5 && rm -rf /var/lib/apt/lists/*

# On récupère l'environnement virtuel complet du builder
COPY --from=builder /opt/venv /opt/venv

# --- CRUCIAL : On active l'environnement virtuel dans le PATH ---
ENV PATH="/opt/venv/bin:$PATH"
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Copier le reste du code
COPY . .

# Création des dossiers nécessaires
RUN mkdir -p logs static media

# Collecte des fichiers statiques
RUN python manage.py collectstatic --noinput || true

# Commande de démarrage
COPY start.sh /app/start.sh
RUN chmod +x /app/start.sh

# 2. On donne les droits d'exécution
RUN chmod +x /app/start.sh

# 3. On définit le script comme commande de démarrage
# (Supprime toute autre ligne CMD ou ENTRYPOINT avant celle-ci)
CMD ["/app/start.sh"]
