# Déploiement Fullstack sur Render (Backend Django + Frontend statique)

Ce projet est prêt pour un déploiement Render via le fichier [`render.yaml`](render.yaml).

## 1) Pré-requis

- Repository GitHub/GitLab avec ce code poussé
- Compte Render

## 2) Déploiement automatique via Blueprint

1. Ouvrir Render
2. Cliquer sur **New +** → **Blueprint**
3. Connecter le repository
4. Render détecte [`render.yaml`](render.yaml) et crée:
   - Web Service backend: `bko-station-backend`
   - Static site frontend: `bko-station-frontend`
   - PostgreSQL: `bko-station-db`

## 3) Vérifier les variables d'environnement backend

Dans le service backend, vérifier les variables suivantes (préremplies par [`render.yaml`](render.yaml)):

- `SECRET_KEY` (générée)
- `DEBUG=False`
- `ALLOWED_HOSTS=bko-station-backend.onrender.com`
- `DATABASE_URL` (liée à la DB Render)
- `CORS_ALLOWED_ORIGINS=https://bko-station-frontend.onrender.com`
- `CSRF_TRUSTED_ORIGINS=https://bko-station-backend.onrender.com,https://bko-station-frontend.onrender.com`

Si les noms réels Render diffèrent (URL différente), ajuster `ALLOWED_HOSTS`, `CORS_ALLOWED_ORIGINS`, `CSRF_TRUSTED_ORIGINS`.

## 4) URL API côté frontend

Le build frontend écrit automatiquement [`frontend/config.js`](frontend/config.js) avec:

- `API_BASE_URL=https://bko-station-backend.onrender.com/api`

Si ton backend a un autre nom/URL, mettre à jour la commande `buildCommand` dans [`render.yaml`](render.yaml).

## 5) Commandes backend Render

Le backend utilise:

- Build: `pip install -r requirements.txt && python manage.py collectstatic --noinput`
- Start: `python manage.py migrate && gunicorn config.wsgi:application --bind 0.0.0.0:$PORT`

## 6) Vérification post-déploiement

### Santé backend
- `GET https://<backend>.onrender.com/api/health/` → doit retourner `healthy`

### JWT
- `POST https://<backend>.onrender.com/api/auth/token/` avec username/password

### Frontend
- Ouvrir `https://<frontend>.onrender.com`
- Vérifier le chargement de la carte et des stations
- Vérifier qu’un ajout station fonctionne avec un token JWT (écriture protégée)

## 7) Points importants

- Les opérations d'écriture sont protégées par JWT.
- En production, garder `DEBUG=False`.
- Le plan free Render peut provoquer un "cold start".
