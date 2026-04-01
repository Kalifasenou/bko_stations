#!/bin/bash

# Arrêter le script si une commande échoue
set -e

echo "--> Lancement des migrations..."
python manage.py migrate --noinput

echo "--> Vérification du superadmin..."
python manage.py shell -c "from django.contrib.auth import get_user_model; User=get_user_model(); username='lelouch'; email='admin@bko-stations.local'; password='Lelouch2026'; u=User.objects.filter(username=username).first(); (User.objects.create_superuser(username=username,email=email,password=password), print('Superadmin créé: lelouch')) if u is None else print('Superadmin déjà existant: lelouch')"

echo "--> Lancement du serveur Gunicorn..."
exec gunicorn config.wsgi:application --bind 0.0.0.0:$PORT
