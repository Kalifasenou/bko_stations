#!/bin/bash

# Arrêter le script si une commande échoue
set -e

echo "--> Lancement des migrations..."
python manage.py migrate --noinput

echo "--> Vérification du superadmin (via variables d'environnement)..."
python manage.py shell -c "import os; from django.contrib.auth import get_user_model; User=get_user_model(); username=os.getenv('DJANGO_SUPERUSER_USERNAME'); email=os.getenv('DJANGO_SUPERUSER_EMAIL'); password=os.getenv('DJANGO_SUPERUSER_PASSWORD');
if username and email and password:
    u=User.objects.filter(username=username).first();
    (User.objects.create_superuser(username=username,email=email,password=password), print(f'Superadmin créé: {username}')) if u is None else print(f'Superadmin déjà existant: {username}');
else:
    print('Variables DJANGO_SUPERUSER_* absentes: création automatique ignorée.')"

echo "--> Lancement du serveur Gunicorn..."
exec gunicorn config.wsgi:application --bind 0.0.0.0:$PORT --timeout 120 --workers 2 --threads 2
