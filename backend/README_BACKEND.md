# BKO Station - Backend API

API REST pour gérer les stations de carburant à Bamako et les signalements de disponibilité en temps réel.

## 📋 Table des matières

- [Installation](#installation)
- [Configuration](#configuration)
- [Démarrage](#démarrage)
- [Tests](#tests)
- [Déploiement](#déploiement)
- [Architecture](#architecture)
- [Endpoints](#endpoints)

## 🚀 Installation

### Prérequis

- Python 3.8+
- Django 4.0+
- Django REST Framework
- PostgreSQL (production) ou SQLite (développement)

### Étapes d'installation

1. **Cloner le repository**
```bash
git clone <repository-url>
cd backend
```

2. **Créer un environnement virtuel**
```bash
python -m venv venv
source venv/bin/activate  # Sur Windows: venv\Scripts\activate
```

3. **Installer les dépendances**
```bash
pip install -r requirements.txt
```

4. **Configurer les variables d'environnement**
```bash
cp .env.example .env
# Éditer .env avec vos paramètres
```

5. **Appliquer les migrations**
```bash
python manage.py migrate
```

6. **Créer un superutilisateur**
```bash
python manage.py createsuperuser
```

7. **Charger les données initiales (optionnel)**
```bash
python manage.py seed_stations
```

## ⚙️ Configuration

### Variables d'environnement (.env)

```env
# Django
DEBUG=True
SECRET_KEY=your-secret-key-here
ALLOWED_HOSTS=localhost,127.0.0.1

# Database
DB_ENGINE=django.db.backends.sqlite3
DB_NAME=db.sqlite3
# Pour PostgreSQL:
# DB_ENGINE=django.db.backends.postgresql
# DB_NAME=bko_station
# DB_USER=postgres
# DB_PASSWORD=password
# DB_HOST=localhost
# DB_PORT=5432

# Cache
CACHE_BACKEND=django.core.cache.backends.locmem.LocMemCache
# Pour Redis:
# CACHE_BACKEND=django.core.cache.backends.redis.RedisCache
# CACHE_LOCATION=redis://127.0.0.1:6379/1

# CORS
CORS_ALLOWED_ORIGINS=http://localhost:3000,http://localhost:8000

# Logging
LOG_LEVEL=INFO
```

### Settings Django

Les paramètres principaux sont dans [`config/settings.py`](config/settings.py):

- **INSTALLED_APPS**: Applications Django installées
- **MIDDLEWARE**: Middlewares actifs
- **DATABASES**: Configuration de la base de données
- **CACHES**: Configuration du cache
- **REST_FRAMEWORK**: Configuration de DRF

## 🏃 Démarrage

### Développement

```bash
python manage.py runserver
```

L'API sera disponible à `http://localhost:8000/api/`

### Production

```bash
gunicorn config.wsgi:application --bind 0.0.0.0:8000
```

## 🧪 Tests

### Exécuter tous les tests

```bash
python manage.py test
```

### Exécuter les tests d'une application

```bash
python manage.py test stations
```

### Exécuter un test spécifique

```bash
python manage.py test stations.tests.StationModelTests.test_station_creation
```

### Avec couverture de code

```bash
coverage run --source='.' manage.py test
coverage report
coverage html
```

## 📦 Déploiement

### Avec Docker

1. **Créer l'image Docker**
```bash
docker build -t bko-station-backend .
```

2. **Lancer le conteneur**
```bash
docker run -p 8000:8000 \
  -e DEBUG=False \
  -e SECRET_KEY=your-secret-key \
  bko-station-backend
```

### Avec Heroku

1. **Créer une app Heroku**
```bash
heroku create bko-station-api
```

2. **Ajouter PostgreSQL**
```bash
heroku addons:create heroku-postgresql:hobby-dev
```

3. **Configurer les variables d'environnement**
```bash
heroku config:set DEBUG=False
heroku config:set SECRET_KEY=your-secret-key
```

4. **Déployer**
```bash
git push heroku main
```

### Avec AWS/EB

```bash
eb init -p python-3.9 bko-station
eb create bko-station-env
eb deploy
```

## 🏗️ Architecture

### Structure du projet

```
backend/
├── config/              # Configuration Django
│   ├── settings.py     # Paramètres principaux
│   ├── urls.py         # URLs principales
│   ├── wsgi.py         # WSGI pour production
│   └── asgi.py         # ASGI pour WebSockets
├── stations/           # Application principale
│   ├── models.py       # Modèles de données
│   ├── views.py        # Vues et ViewSets
│   ├── serializers.py  # Sérialiseurs DRF
│   ├── urls.py         # URLs de l'app
│   ├── admin.py        # Interface admin
│   ├── tests.py        # Tests unitaires
│   ├── permissions.py  # Permissions personnalisées
│   ├── exceptions.py   # Exceptions personnalisées
│   ├── constants.py    # Constantes
│   └── utils.py        # Fonctions utilitaires
├── cache_config.py     # Configuration du cache
├── manage.py           # Utilitaire Django
├── requirements.txt    # Dépendances Python
└── db.sqlite3          # Base de données (dev)
```

### Modèles de données

#### Station
- `id`: Identifiant unique
- `name`: Nom de la station
- `brand`: Marque (Shell, Total, Oryx, etc.)
- `latitude`: Latitude GPS
- `longitude`: Longitude GPS
- `created_at`: Date de création
- `updated_at`: Date de mise à jour

#### Signalement
- `id`: Identifiant unique
- `station`: Référence à la station
- `fuel_type`: Type de carburant (Essence, Gazole)
- `status`: Statut (Disponible, Épuisé)
- `timestamp`: Date du signalement
- `approval_count`: Nombre d'approbations
- `ip`: Adresse IP de l'utilisateur

## 📡 Endpoints

### Stations
- `GET /api/stations/` - Lister les stations
- `GET /api/stations/{id}/` - Récupérer une station
- `GET /api/stations/{id}/nearby/` - Stations proches
- `POST /api/stations/` - Créer une station (Admin)
- `PUT /api/stations/{id}/` - Mettre à jour (Admin)
- `DELETE /api/stations/{id}/` - Supprimer (Admin)

### Signalements
- `POST /api/signalements/` - Créer un signalement
- `POST /api/signalements/{id}/approve/` - Approuver
- `GET /api/signalements/latest/` - Derniers signalements
- `GET /api/signalements/by_station/` - Par station

### Statistiques
- `GET /api/statistics/` - Statistiques globales
- `GET /api/statistics/by-brand/` - Par marque
- `GET /api/fuel-availability-map/` - Carte de disponibilité
- `GET /api/signalements/heatmap/` - Heatmap

### Recherche
- `GET /api/search/` - Rechercher des stations
- `GET /api/stations/by-status/` - Par statut

## 🔐 Authentification

L'API utilise actuellement `AllowAny` pour les permissions. Pour ajouter l'authentification:

1. **Token Authentication**
```python
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.TokenAuthentication',
    ],
}
```

2. **JWT Authentication**
```bash
pip install djangorestframework-simplejwt
```

## 📊 Monitoring

### Logs

Les logs sont configurés dans `config/settings.py`:

```python
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': 'logs/django.log',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['file'],
            'level': 'INFO',
        },
    },
}
```

### Performance

- Utiliser `select_related()` et `prefetch_related()` pour optimiser les requêtes
- Activer le cache pour les endpoints statiques
- Utiliser les index de base de données

## 🐛 Dépannage

### Erreur de migration

```bash
python manage.py makemigrations
python manage.py migrate
```

### Réinitialiser la base de données

```bash
python manage.py flush
python manage.py migrate
```

### Vider le cache

```bash
python manage.py shell
>>> from django.core.cache import cache
>>> cache.clear()
```

## 📚 Documentation supplémentaire

- [API_DOCUMENTATION.md](API_DOCUMENTATION.md) - Documentation complète de l'API
- [Django Documentation](https://docs.djangoproject.com/)
- [Django REST Framework](https://www.django-rest-framework.org/)

## 📝 Licence

MIT License - Voir LICENSE pour plus de détails
