# 🚀 Démarrage Rapide - BKO Station Backend

## ⚡ 5 minutes pour démarrer

### Option 1: Développement Local (Recommandé pour commencer)

```bash
# 1. Cloner et naviguer
cd backend

# 2. Exécuter le script de setup
bash setup.sh dev

# 3. Démarrer le serveur
source venv/bin/activate
python manage.py runserver

# 4. Accéder à l'API
# http://localhost:8000/api/
# http://localhost:8000/admin/
```

### Option 2: Docker (Recommandé pour production)

```bash
# 1. Naviguer au répertoire backend
cd backend

# 2. Démarrer les services
docker-compose up -d

# 3. Appliquer les migrations
docker-compose exec web python manage.py migrate

# 4. Créer un superutilisateur
docker-compose exec web python manage.py createsuperuser

# 5. Accéder à l'API
# http://localhost:8000/api/
# http://localhost:8000/admin/
```

---

## 📋 Vérification Rapide

### Tester les endpoints principaux

```bash
# Lister les stations
curl http://localhost:8000/api/stations/

# Obtenir les statistiques
curl http://localhost:8000/api/statistics/

# Rechercher une station
curl "http://localhost:8000/api/search/?q=Shell"

# Créer un signalement
curl -X POST http://localhost:8000/api/signalements/ \
  -H "Content-Type: application/json" \
  -d '{
    "station": 1,
    "fuel_type": "Essence",
    "status": "Disponible"
  }'
```

---

## 🔧 Configuration Essentielle

### Fichier `.env`

```env
DEBUG=True
SECRET_KEY=your-secret-key-here
ALLOWED_HOSTS=localhost,127.0.0.1
DB_ENGINE=django.db.backends.sqlite3
DB_NAME=db.sqlite3
```

---

## 📚 Documentation Complète

| Document | Contenu |
|----------|---------|
| [`API_DOCUMENTATION.md`](API_DOCUMENTATION.md) | Tous les endpoints avec exemples |
| [`README_BACKEND.md`](README_BACKEND.md) | Guide complet d'installation |
| [`CHANGELOG.md`](CHANGELOG.md) | Historique des changements |
| [`IMPROVEMENTS_SUMMARY.md`](IMPROVEMENTS_SUMMARY.md) | Résumé des améliorations |

---

## 🧪 Exécuter les Tests

```bash
# Tous les tests
python manage.py test

# Tests spécifiques
python manage.py test stations.tests.StationModelTests

# Avec couverture
coverage run --source='.' manage.py test
coverage report
```

---

## 🐛 Dépannage Rapide

### Erreur: "No module named 'django'"
```bash
pip install -r requirements.txt
```

### Erreur: "database is locked"
```bash
rm db.sqlite3
python manage.py migrate
```

### Erreur: "Port 8000 already in use"
```bash
python manage.py runserver 8001
```

### Réinitialiser la base de données
```bash
python manage.py flush
python manage.py migrate
python seed_stations.py
```

---

## 📊 Endpoints Clés

### Stations
- `GET /api/stations/` - Lister
- `GET /api/stations/{id}/` - Détails
- `GET /api/stations/{id}/nearby/` - Proches

### Signalements
- `POST /api/signalements/` - Créer
- `POST /api/signalements/{id}/approve/` - Approuver
- `GET /api/signalements/latest/` - Derniers

### Statistiques
- `GET /api/statistics/` - Globales
- `GET /api/statistics/by-brand/` - Par marque
- `GET /api/fuel-availability-map/` - Carte
- `GET /api/signalements/heatmap/` - Heatmap

### Recherche
- `GET /api/search/?q=Shell` - Rechercher
- `GET /api/stations/by-status/?status=available` - Par statut

---

## 🔐 Admin Django

```bash
# Créer un superutilisateur
python manage.py createsuperuser

# Accéder à l'admin
# http://localhost:8000/admin/
```

---

## 📦 Charger les Données de Test

```bash
python seed_stations.py
```

---

## 🚀 Prochaines Étapes

1. ✅ Démarrer le serveur
2. ✅ Tester les endpoints
3. ✅ Consulter la documentation API
4. ✅ Configurer le cache Redis (optionnel)
5. ✅ Déployer en production

---

## 💡 Conseils

- Utilisez Postman ou Insomnia pour tester l'API
- Consultez les logs pour déboguer: `tail -f logs/django.log`
- Activez le mode debug pour plus d'informations: `DEBUG=True`
- Utilisez `python manage.py shell` pour tester le code

---

## 📞 Besoin d'aide?

1. Consultez [`README_BACKEND.md`](README_BACKEND.md)
2. Vérifiez [`API_DOCUMENTATION.md`](API_DOCUMENTATION.md)
3. Lisez [`CHANGELOG.md`](CHANGELOG.md)
4. Vérifiez les logs: `logs/django.log`

---

**Bon développement! 🎉**
