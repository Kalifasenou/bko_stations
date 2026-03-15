# ⛽ Bamako Gaz Tracker

Application PWA (Progressive Web App) pour le suivi en temps réel de la disponibilité du carburant à Bamako, Mali.

## 🎯 Concept

Une carte interactive de Bamako où chaque station est un point coloré :
- 🟢 **Vert** : Carburant disponible
- 🟡 **Jaune** : Un seul type disponible (Essence ou Gazole)
- 🔴 **Rouge** : Rupture totale
- ⚪ **Gris** : Statut inconnu

## ✨ Fonctionnalités

### 1. **Géolocalisation**
- Trouve automatiquement les stations autour de vous
- Affiche la distance en kilomètres
- Centre la carte sur votre position

### 2. **Signalement Rapide**
- Bouton "✅ Il y a du fuel" - Signale la disponibilité
- Bouton "❌ C'est fini" - Signale une rupture
- Validation par IP (1 signalement/heure par station)

### 3. **Système de Confiance**
- "Vérifié par X personnes"
- Plus il y a d'approbations, plus le signal est fiable
- Algorithme de fraîcheur : les signalements expirent après 4h

### 4. **Mode PWA**
- Installation sur l'écran d'accueil (iOS/Android)
- Fonctionnement hors-ligne partiel
- Service Worker pour la mise en cache des tuiles de carte

### 5. **Design "Cyber-BKO"**
- Mode sombre par défaut (#0A0E14)
- Accents néon (Vert #00FF41, Rouge #FF3131)
- Interface "pouce-friendly" (boutons en bas)
- Animations pulse pour les mises à jour fraîches

## 🏗️ Architecture

### Backend (Django REST Framework)
```
backend/
├── config/           # Configuration Django
├── stations/         # App principale
│   ├── models.py     # Station, Signalement
│   ├── views.py      # API endpoints
│   ├── serializers.py
│   └── urls.py
├── manage.py
└── requirements.txt
```

**Modèles :**
- `Station` : Nom, Enseigne, Coordonnées GPS
- `Signalement` : Type (Essence/Gazole), Statut, Timestamp, Approbations, IP

**Endpoints API :**
- `GET /api/stations/` - Liste des stations
- `GET /api/stations/?lat=X&lon=Y&radius=Z` - Stations proches
- `POST /api/signalements/` - Créer un signalement
- `GET /api/signalements/latest/` - Derniers signalements (Live Pulse)

### Frontend (PWA Vanilla JS)
```
frontend/
├── index.html        # Structure principale
├── styles.css        # Thème Cyber-BKO
├── app.js            # Logique applicative
├── manifest.json     # Configuration PWA
├── service-worker.js # Cache & offline
└── icons/            # Icônes PWA
```

**Technologies :**
- **Cartographie** : Leaflet.js + OpenStreetMap (CartoDB Dark Matter)
- **Géolocalisation** : API Navigator Geolocation
- **PWA** : Service Worker, Manifest, Cache API

## 🚀 Installation

### Prérequis
- Python 3.10+
- pip
- Navigateur moderne (Chrome, Firefox, Safari, Edge)

### Backend

```bash
# 1. Cloner le projet
cd bko_station

# 2. Créer l'environnement virtuel
cd backend
python -m venv venv

# Windows
venv\Scripts\activate

# macOS/Linux
source venv/bin/activate

# 3. Installer les dépendances
pip install -r requirements.txt

# 4. Appliquer les migrations
python manage.py migrate

# 5. Créer un superuser (optionnel)
python manage.py createsuperuser

# 6. Peupler la base avec les stations de Bamako
python seed_stations.py

# 7. Lancer le serveur
python manage.py runserver
```

Le backend est accessible sur `http://localhost:8000`

### Frontend

Le frontend est une application statique. Vous pouvez :

**Option 1 : Serveur de développement Python**
```bash
cd frontend
python -m http.server 5500
```

**Option 2 : Live Server (VS Code)**
- Installer l'extension "Live Server"
- Clic droit sur `index.html` → "Open with Live Server"

**Option 3 : Node.js (optionnel)**
```bash
cd frontend
npx serve
```

Le frontend est accessible sur `http://localhost:5500`

## 📱 Installation PWA

### Android (Chrome)
1. Ouvrir l'application dans Chrome
2. Cliquer sur "Ajouter à l'écran d'accueil" dans le menu
3. Ou attendre la bannière d'installation

### iOS (Safari)
1. Ouvrir l'application dans Safari
2. Cliquer sur le bouton "Partager"
3. Sélectionner "Sur l'écran d'accueil"

### Desktop (Chrome/Edge)
1. Ouvrir l'application
2. Cliquer sur l'icône d'installation dans la barre d'adresse
3. Ou all dans le menu → "Installer Bamako Gaz Tracker"

## 🔧 Configuration

### Variables d'environnement (backend)

Créer un fichier `.env` dans `backend/` :

```env
DEBUG=True
SECRET_KEY=votre-cle-secrete-ici
ALLOWED_HOSTS=localhost,127.0.0.1
DATABASE_URL=sqlite:///db.sqlite3
# Ou pour PostgreSQL :
# DATABASE_URL=postgres://user:password@localhost:5432/bamako_gaz
```

### Configuration API (frontend)

Dans `frontend/app.js`, modifier si nécessaire :

```javascript
const CONFIG = {
    API_BASE_URL: 'http://localhost:8000/api',
    // ...
};
```

## 🗺️ Stations incluses

Le fichier `seed_stations.py` contient 8 stations de référence à Bamako :

- Shell ACI 2000
- Total Pont
- Oryx Bamako
- Shell Badalabougou
- Total Hippodrome
- ExxonMobil Djélibougou
- Oryx Sabalibougou
- Shell Sotrama

Vous pouvez ajouter plus de stations via l'admin Django ou l'API.

## 🧪 Tests

```bash
cd backend
python manage.py test
```

## 🚢 Déploiement

### Backend (Heroku/DigitalOcean/AWS)

```bash
# Installer gunicorn et whitenoise
pip install gunicorn whitenoise

# Collecter les fichiers statiques
python manage.py collectstatic

# Lancer avec gunicorn
gunicorn config.wsgi:application
```

### Frontend (Vercel/Netlify/GitHub Pages)

Le frontend est statique et peut être déployé sur n'importe quel hébergeur statique :

```bash
# Build (si nécessaire)
cd frontend

# Déployer sur Vercel
vercel --prod

# Ou Netlify
netlify deploy --prod
```

**Important** : Mettre à jour `API_BASE_URL` dans `app.js` avec l'URL de production du backend.

## 🎨 Personnalisation

### Thème

Les couleurs sont définies dans `styles.css` :

```css
:root {
    --bg-primary: #0A0E14;      /* Fond principal */
    --accent-green: #00FF41;     /* Disponible */
    --accent-red: #FF3131;       /* Rupture */
    --accent-yellow: #FFD700;    /* Partiel */
}
```

### Carte

Le style de carte est défini dans `app.js` :

```javascript
L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
    // Options
});
```

Autres styles disponibles :
- `light_all` - Carte claire
- `dark_all` - Carte sombre (défaut)
- `rastertiles/voyager` - Style moderne

## 📄 Licence

MIT License - Voir [LICENSE](LICENSE)

## 🤝 Contribution

Les contributions sont les bienvenues !

1. Fork le projet
2. Créer une branche (`git checkout -b feature/AmazingFeature`)
3. Commit les changements (`git commit -m 'Add some AmazingFeature'`)
4. Push sur la branche (`git push origin feature/AmazingFeature`)
5. Ouvrir une Pull Request

## 🙏 Remerciements

- [OpenStreetMap](https://www.openstreetmap.org/) pour les données cartographiques
- [CartoDB](https://carto.com/) pour les tuiles Dark Matter
- [Leaflet](https://leafletjs.com/) pour la bibliothèque de cartographie
- La communauté de Bamako pour l'inspiration !

---

**Développé avec ❤️ pour Bamako** 🇲🇱
