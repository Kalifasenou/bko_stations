#!/bin/bash
set -e

echo "==> [1/4] Application des migrations Django..."
python manage.py migrate --noinput --verbosity 2

echo ""
echo "==> [2/4] État des migrations stations:"
python manage.py showmigrations stations || true

echo ""
echo "==> [3/4] Auto-seed (si BDD vide)..."
NEEDS_SEED=$(python -c "
import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()
from stations.models import Station
print('YES' if Station.objects.count() == 0 else 'NO')
" 2>/dev/null || echo "ERROR")

if [ "$NEEDS_SEED" = "YES" ]; then
    echo "BDD vide -> exécution de seed_stations.py"
    python seed_stations.py || echo "   (le seed a échoué, on continue)"
else
    echo "BDD déjà peuplée ou indisponible (status=$NEEDS_SEED) -> seed ignoré"
fi

echo ""
echo "==> [4/4] Vérification/création du superadmin..."
python manage.py shell -c "
import os
from django.contrib.auth import get_user_model
User = get_user_model()
username = os.getenv('DJANGO_SUPERUSER_USERNAME')
email = os.getenv('DJANGO_SUPERUSER_EMAIL')
password = os.getenv('DJANGO_SUPERUSER_PASSWORD')
if username and email and password:
    u = User.objects.filter(username=username).first()
    if u is None:
        User.objects.create_superuser(username=username, email=email, password=password)
        print(f'Superadmin créé: {username}')
    else:
        print(f'Superadmin déjà existant: {username}')
else:
    print('Variables DJANGO_SUPERUSER_* absentes: création automatique ignorée.')
" || echo "   (création du superadmin ignorée suite à une erreur)"

echo ""
echo "==> Lancement de Gunicorn..."
# Railway injecte la variable PORT dynamiquement. Fallback sur 8080 si absente.
PORT="${PORT:-8080}"
echo "Port d'écoute: $PORT"
exec gunicorn config.wsgi:application \
    --bind "0.0.0.0:$PORT" \
    --timeout 120 \
    --workers 2 \
    --threads 2 \
    --access-logfile - \
    --error-logfile - \
    --log-level info
