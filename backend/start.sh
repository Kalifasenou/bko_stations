#!/bin/bash

# Arrêter le script si une commande échoue
set -e

echo "--> Lancement des migrations..."
python manage.py migrate --noinput

echo "--> Lancement du serveur Gunicorn..."
exec gunicorn config.wsgi:application --bind 0.0.0.0:$PORT
