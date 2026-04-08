# Déploiement Fullstack sur Render (Backend Django + Frontend statique)

Ce projet est prêt pour un déploiement Render via le fichier [`render.yaml`](render.yaml).

## 1) Pré-requis

- Repository GitHub/GitLab avec ce code poussé
- Compte Render (gratuit ou payant)
- Git installé localement (optionnel, pour les tests locaux)

## 2) Déploiement automatique via Blueprint

1. Ouvrir Render Dashboard
2. Cliquer sur **New +** → **Blueprint**
3. Connecter le repository GitHub/GitLab
4. Render détecte automatiquement [`render.yaml`](render.yaml) et crée:
   - **Web Service backend**: `bko-station-backend` (Python/Django) **plan: free** (instance hobby avec cold starts)
   - **Static Site frontend**: `bko-station-frontend` (HTML/CSS/JS) **plan: free**
   - **PostgreSQL**: `bko-station-db` (base de données) **plan: free**

### Configuration automatique

Le Blueprint configure automatiquement:
- `DEBUG=False` pour la production
- `ENVIRONMENT=production` pour activer les sécurités
- `SECRET_KEY` générée automatiquement
- `DATABASE_URL` liée à la base PostgreSQL Render
- CORS configuré entre frontend et backend
- SSL/TLS activé par défaut

## 3) Vérifier les variables d'environnement backend

Dans le service backend, vérifier les variables suivantes (préremplies par [`render.yaml`](render.yaml)):

| Variable | Valeur | Description |
|----------|--------|-------------|
| `PYTHON_VERSION` | `3.12.7` | Version Python |
| `DJANGO_SETTINGS_MODULE` | `config.settings` | Module de configuration |
| `ENVIRONMENT` | `production` | Environnement de production |
| `DEBUG` | `False` | Mode débogage désactivé |
| `SECRET_KEY` | *(générée)* | Clé secrète Django |
| `ALLOWED_HOSTS` | `bko-station-backend.onrender.com,localhost,127.0.0.1` | Hôtes autorisés |
| `CORS_ALLOW_ALL_ORIGINS` | `False` | CORS restreint |
| `CORS_ALLOWED_ORIGINS` | `https://bko-station-frontend.onrender.com,http://localhost:8080` | Origines CORS |
| `CSRF_TRUSTED_ORIGINS` | `https://bko-station-backend.onrender.com,https://bko-station-frontend.onrender.com` | Origines CSRF |
| `SECURE_SSL_REDIRECT` | `True` | Redirection HTTPS |
| `SESSION_COOKIE_SECURE` | `True` | Cookies sécurisés |
| `CSRF_COOKIE_SECURE` | `True` | CSRF cookies sécurisés |
| `DATABASE_URL` | *(liée à la DB Render)* | Connection string PostgreSQL |

> **Note importante** : Render a récemment modifié sa politique. Le plan `free` pour les Web Services est maintenant limité (Hobby tier avec cold starts après 15 min d'inactivité). Si le blueprint échoue à nouveau avec "no such plan free", vous devrez passer au plan `starter` ou utiliser une alternative gratuite comme Railway, Fly.io ou Render avec un compte payant minimal.

> **Important**: Si les URLs Render diffèrent (noms de services différents), ajuster `ALLOWED_HOSTS`, `CORS_ALLOWED_ORIGINS`, `CSRF_TRUSTED_ORIGINS`.

## 4) URL API côté frontend

Le build frontend écrit automatiquement [`frontend/config.js`](frontend/config.js) avec:

```javascript
window.APP_CONFIG = { API_BASE_URL: 'https://bko-station-backend.onrender.com/api' };
```

Si ton backend a un autre nom/URL, mettre à jour la commande `buildCommand` dans [`render.yaml`](render.yaml).

## 5) Commandes backend Render

Le backend utilise:

- **Build**: `pip install -r requirements.txt && python manage.py collectstatic --noinput && python manage.py migrate --noinput`
- **Start**: `gunicorn config.wsgi:application --bind 0.0.0.0:$PORT --timeout 120 --workers 2 --threads 2`

### Optimisations Gunicorn

- `--timeout 120`: Timeout augmenté pour les requêtes longues
- `--workers 2`: 2 workers pour le plan gratuit
- `--threads 2`: Threads pour la concurrence

## 6) Vérification post-déploiement

### Exécuter le script de vérification

```bash
# Linux/macOS
bash scripts/verify_deployment.sh https://bko-station-backend.onrender.com https://bko-station-frontend.onrender.com

# Windows
scripts\verify_deployment.bat https://bko-station-backend.onrender.com https://bko-station-frontend.onrender.com
```

### Vérifications manuelles

#### Santé backend
- `GET https://<backend>.onrender.com/api/health/` → doit retourner `{"status":"healthy",...}`

#### Liste des stations
- `GET https://<backend>.onrender.com/api/stations/` → doit retourner la liste des stations

#### JWT Authentication
- `POST https://<backend>.onrender.com/api/auth/token/` avec username/password → doit retourner un token

#### Statistiques
- `GET https://<backend>.onrender.com/api/statistics/` → doit retourner les statistiques

#### Frontend
- Ouvrir `https://<frontend>.onrender.com`
- Vérifier le chargement de la carte et des stations
- Vérifier qu'un ajout de signalement fonctionne avec un token JWT

## 7) Points importants

### Sécurité
- Les opérations d'écriture sont protégées par JWT
- `DEBUG=False` en production
- SSL/TLS activé par défaut sur Render
- Cookies sécurisés (`Secure`, `HttpOnly`)
- Headers de sécurité configurés (X-Frame-Options, X-Content-Type-Options, X-XSS-Protection)

### Performance
- Plan gratuit Render: cold start après 15 minutes d'inactivité
- Gunicorn configuré avec 2 workers + 2 threads
- Cache local (LocMemCache) par défaut, Redis optionnel
- Pagination activée (50 résultats par page)

### Base de données
- PostgreSQL Render (plan gratuit: 1 Go max)
- Migrations exécutées automatiquement au build
- `conn_max_age=600` pour le connection pooling

### Monitoring
- Logs disponibles dans le dashboard Render
- Health check sur `/api/health/`
- Logs Django configurés (console + fichier)

## 8) Déploiement local (test avant production)

### Backend
```bash
cd backend
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

### Frontend
```bash
cd frontend
python -m http.server 8080
```

### Vérification locale
```bash
# Windows
scripts\verify_deployment.bat http://localhost:8000 http://localhost:8080

# Linux/macOS
bash scripts/verify_deployment.sh http://localhost:8000 http://localhost:8080
```

## 9) Structure du projet

```
bko_station/
├── render.yaml                 # Configuration Render Blueprint
├── DEPLOY_RENDER.md            # Ce fichier
├── README.md                   # Documentation générale
├── scripts/
│   ├── verify_deployment.sh    # Script de vérification (Linux/macOS)
│   └── verify_deployment.bat   # Script de vérification (Windows)
├── backend/                    # Application Django
│   ├── config/                 # Configuration Django
│   │   ├── settings.py         # Paramètres
│   │   ├── urls.py             # URLs principales
│   │   └── wsgi.py             # WSGI entry point
│   ├── stations/               # Application principale
│   │   ├── models.py           # Modèles de données
│   │   ├── views.py            # Vues API
│   │   ├── serializers.py      # Sérialiseurs DRF
│   │   ├── urls.py             # URLs de l'application
│   │   └── tests.py            # Tests unitaires
│   ├── requirements.txt        # Dépendances Python
│   ├── manage.py               # Script de gestion Django
│   └── Dockerfile              # Configuration Docker
└── frontend/                   # Application frontend statique
    ├── index.html              # Page principale
    ├── app.js                  # Logique applicative
    ├── styles.css              # Styles
    ├── config.js               # Configuration API
    ├── service-worker.js       # PWA Service Worker
    └── manifest.json           # PWA Manifest
```

## 10) Dépannage

### Cold Start
Le plan gratuit Render met le service en veille après 15 minutes d'inactivité. La première requête peut prendre 30-60 secondes.

### Erreur CORS
Vérifier que `CORS_ALLOWED_ORIGINS` contient l'URL exacte du frontend.

### Erreur Database
Vérifier que `DATABASE_URL` est correctement liée à la base Render.

### Erreur 500
Vérifier les logs dans le dashboard Render pour le traceback complet.
