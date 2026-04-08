# 🚀 Déploiement 100% Gratuit de BKO Station (Vercel + Railway)

**Note** : Utilisez des **guillemets simples** dans la Build Command Vercel pour éviter les erreurs d'échappement.

## Meilleure Stratégie Recommandée (2026)

**Frontend (Static) + Backend (Serverless) + DB gratuite**

### Architecture recommandée :
- **Frontend** → **Vercel** (meilleur pour les apps statiques/PWA)
- **Backend** → **Railway** (tier gratuit généreux pour Django + Postgres)
- **Base de données** → Intégrée à Railway (PostgreSQL gratuit)

**Avantages** :
- Zéro coût
- Déploiement en 1 clic
- Cold starts très courts sur Railway
- Vercel optimise parfaitement le frontend statique + PWA
- Pas de limite de bande passante agressive

---

## 1. Préparation (à faire une seule fois)

### 1.1 Fichiers déjà créés pour vous

- [`railway.json`](railway.json:1) → Configuration Railway (créé)
- [`backend/config/settings.py`](backend/config/settings.py:40) → Mis à jour avec les domaines Railway et Vercel (ALLOWED_HOSTS, CORS, CSRF)
- [`DEPLOY_FREE.md`](DEPLOY_FREE.md:1) → Ce guide

Le frontend [`frontend/config.js`](frontend/config.js) détecte déjà automatiquement l'environnement.

### 1.2 Créer un fichier `railway.json` à la racine du projet

```json
{
  "$schema": "https://railway.app/json-schema.json",
  "build": {
    "builder": "NIXPACKS",
    "buildCommand": "cd backend && pip install -r requirements.txt && python manage.py collectstatic --noinput",
    "watchPaths": ["backend/**"]
  },
  "deploy": {
    "startCommand": "cd backend && python manage.py migrate --noinput && gunicorn config.wsgi:application --bind 0.0.0.0:$PORT --timeout 120",
    "healthcheckPath": "/api/health/",
    "restartPolicy": "ON_FAILURE"
  }
}
```

### 1.3 Mettre à jour `backend/config/settings.py` pour Railway

Ajoutez les domaines Railway dans `ALLOWED_HOSTS` et `CSRF_TRUSTED_ORIGINS`.

---

## 2. CI/CD Automatique (Push = Déploiement)

**Chaque `git push` sur `main` déclenchera automatiquement** :
- Reconstruction du **frontend** sur Vercel
- Reconstruction du **backend** sur Railway (`migrate` + `collectstatic`)
- La **base de données** persiste (Railway gère les volumes persistants)

**Important pour ne jamais perdre les données** :
- Railway utilise un volume PostgreSQL persistant (les données survivent aux redéploiements)
- Les migrations Django sont exécutées à chaque build (`python manage.py migrate`)
- Ne jamais supprimer la base de données dans le dashboard Railway

---

## 3. Déploiement Étape par Étape

### Étape 1 : Déployer le Backend + DB sur Railway (15 min)

1. Allez sur [railway.app](https://railway.app) et connectez-vous avec GitHub
2. Cliquez sur **New Project** → **Deploy from GitHub repo**
3. Sélectionnez votre repo `Kalifasenou/bko_stations`
4. Dans **Root Directory**, mettez `backend`
5. Railway détectera automatiquement le `railway.json` (qui pointe maintenant vers le `Dockerfile` du backend pour une meilleure compatibilité)
6. Ajoutez les variables d'environnement suivantes :

```env
DJANGO_SETTINGS_MODULE=config.settings
ENVIRONMENT=production
DEBUG=False
SECRET_KEY=generate_a_random_secret_key_here
ALLOWED_HOSTS=*.up.railway.app,localhost,127.0.0.1
CORS_ALLOWED_ORIGINS=https://bko-station-frontend.vercel.app,http://localhost:8080
CSRF_TRUSTED_ORIGINS=https://*.up.railway.app,https://bko-station-frontend.vercel.app
```

7. Railway créera automatiquement une base PostgreSQL gratuite.
8. Copiez l'URL du backend (ex: `https://bko-station-backend.up.railway.app`)

### Étape 2 : Déployer le Frontend sur Vercel (5 min)

1. Allez sur [vercel.com](https://vercel.com) et connectez votre repo
2. Créez un nouveau projet pour le dossier `frontend`
3. Dans **Build Settings** :
   - **Build Command** : `echo 'window.APP_CONFIG = { API_BASE_URL: \"https://bkostations-production.up.railway.app/api\" };' > config.js`
   - **Output Directory** : `.`
4. Ajoutez la variable d'environnement `API_BASE_URL` avec l'URL exacte de votre backend Railway (`https://bkostations-production.up.railway.app/api`)
5. Déployez

### Étape 3 : Mise à jour finale

1. Mettez à jour les variables CORS dans le backend Railway avec l'URL exacte de votre frontend Vercel.
2. Redéployez (un simple `git push` suffit ensuite pour tout mettre à jour).
3. Testez avec les scripts de vérification mis à jour.

**CI/CD activé** : À partir de maintenant, **tout push sur `main`** déploiera automatiquement les modifications du frontend, backend et exécutera les migrations sans perdre les données existantes dans la base PostgreSQL persistante de Railway.

---

## Alternatives si Railway ne convient pas

### Option 2 : Fly.io (plus technique)
- Très bon pour les apps Django
- Nécessite `fly.toml` et Docker

**Recommandation forte** : **Railway + Vercel** est la combinaison la plus simple et performante en 2026 pour ce type d'application.

Voulez-vous que je crée les fichiers de configuration (`railway.json`, mise à jour de `settings.py`, nouveau script de déploiement) pour cette stratégie ?