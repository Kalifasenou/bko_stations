#!/bin/bash

# Script de configuration rapide pour BKO Station Backend
# Usage: bash setup.sh [dev|prod]

set -e

ENVIRONMENT=${1:-dev}
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

echo "🚀 Configuration de BKO Station Backend - Mode: $ENVIRONMENT"
echo "=================================================="

# Créer l'environnement virtuel
if [ ! -d "venv" ]; then
    echo "📦 Création de l'environnement virtuel..."
    python3 -m venv venv
fi

# Activer l'environnement virtuel
echo "✅ Activation de l'environnement virtuel..."
source venv/bin/activate

# Installer les dépendances
echo "📥 Installation des dépendances..."
pip install --upgrade pip setuptools wheel
pip install -r requirements.txt

# Créer le fichier .env s'il n'existe pas
if [ ! -f ".env" ]; then
    echo "📝 Création du fichier .env..."
    cp .env.example .env
    echo "⚠️  Veuillez configurer les variables dans .env"
fi

# Créer les répertoires nécessaires
echo "📁 Création des répertoires..."
mkdir -p logs static media

# Appliquer les migrations
echo "🗄️  Application des migrations..."
python manage.py migrate

# Créer un superutilisateur (optionnel)
if [ "$ENVIRONMENT" = "dev" ]; then
    echo ""
    read -p "Créer un superutilisateur? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        python manage.py createsuperuser
    fi
    
    # Charger les données de test
    read -p "Charger les données de test? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        python manage.py seed_stations
    fi
fi

# Collecter les fichiers statiques
echo "📦 Collecte des fichiers statiques..."
python manage.py collectstatic --noinput

# Exécuter les tests
echo "🧪 Exécution des tests..."
python manage.py test --verbosity=2

echo ""
echo "=================================================="
echo "✅ Configuration terminée!"
echo ""
echo "Pour démarrer le serveur de développement:"
echo "  source venv/bin/activate"
echo "  python manage.py runserver"
echo ""
echo "Pour accéder à l'API:"
echo "  http://localhost:8000/api/"
echo ""
echo "Pour accéder à l'admin:"
echo "  http://localhost:8000/admin/"
echo ""
