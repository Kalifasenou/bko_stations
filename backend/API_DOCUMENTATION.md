# Documentation API - BKO Station

## Vue d'ensemble
API REST pour gérer les stations de carburant à Bamako et les signalements de disponibilité en temps réel.

## Base URL
```
http://localhost:8000/api/
```

## Authentification JWT

L'API utilise JWT pour les opérations d'écriture.

### Obtenir un token
**POST** `/auth/token/`

**Body:**
```json
{
  "username": "votre_utilisateur",
  "password": "votre_mot_de_passe"
}
```

**Réponse (200 OK):**
```json
{
  "access": "<jwt_access_token>",
  "refresh": "<jwt_refresh_token>"
}
```

### Rafraîchir un token
**POST** `/auth/token/refresh/`

**Body:**
```json
{
  "refresh": "<jwt_refresh_token>"
}
```

**Réponse (200 OK):**
```json
{
  "access": "<nouveau_jwt_access_token>"
}
```

### Utiliser le token
Ajouter l'en-tête HTTP suivant:

`Authorization: Bearer <jwt_access_token>`

---

## Endpoints Stations

### 1. Lister toutes les stations
**GET** `/stations/`

**Paramètres de requête:**
- `lat` (float, optionnel): Latitude pour filtrer par proximité
- `lon` (float, optionnel): Longitude pour filtrer par proximité
- `radius` (float, optionnel): Rayon en km (défaut: 10)
- `page` (int, optionnel): Numéro de page (défaut: 1)
- `page_size` (int, optionnel): Nombre de résultats par page (défaut: 20, max: 100)

**Exemple:**
```bash
GET /stations/?lat=12.6452&lon=-8.0029&radius=5
```

**Réponse (200 OK):**
```json
{
  "count": 45,
  "next": "http://localhost:8000/api/stations/?page=2",
  "previous": null,
  "results": [
    {
      "id": 1,
      "name": "Station Shell Bamako",
      "brand": "Shell",
      "latitude": 12.6452,
      "longitude": -8.0029,
      "distance": 0.5,
      "status_color": "green",
      "latest_signalement": {
        "id": 10,
        "fuel_type": "Essence",
        "status": "Disponible",
        "approval_count": 5,
        "time_ago": "Il y a 15 min"
      },
      "essence_signalement": {...},
      "gazole_signalement": {...}
    }
  ]
}
```

### 2. Récupérer une station
**GET** `/stations/{id}/`

**Réponse (200 OK):**
```json
{
  "id": 1,
  "name": "Station Shell Bamako",
  "brand": "Shell",
  "latitude": 12.6452,
  "longitude": -8.0029,
  "status_color": "green",
  "latest_signalement": {...}
}
```

### 3. Stations proches
**GET** `/stations/{id}/nearby/?radius=2`

**Paramètres:**
- `radius` (float, optionnel): Rayon en km (défaut: 2)

**Réponse (200 OK):** Liste des stations à proximité avec distances

### 4. Créer une station (Admin/Staff uniquement)
**POST** `/stations/`

**Body:**
```json
{
  "name": "Nouvelle Station",
  "brand": "Total",
  "address": "Badalabougou",
  "latitude": 12.6500,
  "longitude": -8.0100,
  "manager_name": "Moussa Traoré",
  "is_active": true
}
```

### 5. Mettre à jour une station (Admin/Staff uniquement)
**PUT/PATCH** `/stations/{id}/`

### 6. Supprimer une station (Admin/Staff uniquement)
**DELETE** `/stations/{id}/`

---

## Endpoints Signalements

### 1. Créer un signalement (Authentifié)
**POST** `/signalements/`

**Body:**
```json
{
  "station": 1,
  "fuel_type": "Essence",
  "status": "Disponible"
}
```

**Réponse:**
- `201 Created` si le signalement est nouveau (aucun signalement récent identique)
- `200 OK` si un signalement récent existe déjà avec le même statut (incrément de `approval_count`)

```json
{
  "id": 10,
  "station": 1,
  "station_name": "Station Shell Bamako",
  "fuel_type": "Essence",
  "status": "Disponible",
  "approval_count": 1,
  "timestamp": "2026-03-15T17:47:28Z",
  "time_ago": "À l'instant",
  "is_expired": false
}
```

**Erreurs:**
- `400 Bad Request`: Station manquante ou vote en doublon (1h)
- `404 Not Found`: Station inexistante

### 2. Approuver un signalement (Authentifié)
**POST** `/signalements/{id}/approve/`

**Réponse (200 OK):** Signalement mis à jour avec `approval_count` incrémenté

**Erreurs:**
- `400 Bad Request`: Approbation en doublon (1h)

### 3. Derniers signalements
**GET** `/signalements/latest/?limit=10`

**Paramètres:**
- `limit` (int, optionnel): Nombre de résultats (défaut: 10)

**Réponse (200 OK):** Liste des signalements des 4 dernières heures

### 4. Signalements par station
**GET** `/signalements/by_station/?station_id=1`

**Paramètres:**
- `station_id` (int, requis): ID de la station

**Réponse (200 OK):** Tous les signalements actifs pour cette station

---

## Endpoints Statistiques

### 1. Statistiques globales
**GET** `/statistics/`

**Réponse (200 OK):**
```json
{
  "total_stations": 45,
  "stations_with_fuel": 38,
  "stations_empty": 5,
  "stations_unknown": 2,
  "signalements_24h": 156,
  "active_signalements": 42,
  "fuel_availability": {
    "essence_disponible": 35,
    "gazole_disponible": 32
  },
  "top_stations": [
    {"id": 1, "name": "Station 1", "brand": "Shell", "count": 12}
  ],
  "last_updated": "2026-03-15T17:47:28Z"
}
```

### 2. Statistiques par marque
**GET** `/statistics/by-brand/`

**Réponse (200 OK):**
```json
[
  {
    "brand": "Shell",
    "total_stations": 15,
    "available": 12,
    "empty": 2,
    "unknown": 1
  },
  {
    "brand": "Total",
    "total_stations": 12,
    "available": 10,
    "empty": 1,
    "unknown": 1
  }
]
```

### 3. Carte de disponibilité
**GET** `/fuel-availability-map/`

**Réponse (200 OK):**
```json
[
  {
    "id": 1,
    "name": "Station Shell",
    "brand": "Shell",
    "latitude": 12.6452,
    "longitude": -8.0029,
    "status_color": "green",
    "fuel_status": {
      "Essence": {
        "status": "Disponible",
        "approval_count": 5,
        "timestamp": "2026-03-15T17:47:28Z"
      },
      "Gazole": {
        "status": "Épuisé",
        "approval_count": 3,
        "timestamp": "2026-03-15T17:30:00Z"
      }
    }
  }
]
```

### 4. Heatmap des signalements
**GET** `/signalements/heatmap/?hours=24`

**Paramètres:**
- `hours` (int, optionnel): Nombre d'heures à considérer (défaut: 24)

**Réponse (200 OK):**
```json
[
  {
    "station__latitude": 12.6452,
    "station__longitude": -8.0029,
    "status": "Disponible",
    "count": 5
  }
]
```

---

## Endpoints Monitoring

### 1. Health check (public)
**GET** `/health/`

### 2. Monitoring opérationnel (authentifié)
**GET** `/monitoring/`

**Réponse (200 OK):**
```json
{
  "status": "ok",
  "database": "connected",
  "cache": "ok",
  "total_stations": 50,
  "active_signalements_4h": 18,
  "log_level": 20,
  "timestamp": "2026-03-15T22:00:00Z"
}
```

---

## Endpoints Recherche

### 1. Rechercher des stations
**GET** `/search/?q=Shell`

**Paramètres:**
- `q` (string, requis): Terme de recherche (min 2 caractères)

**Réponse (200 OK):** Liste des stations correspondantes (max 20)

**Erreurs:**
- `400 Bad Request`: Requête trop courte ou manquante

### 2. Stations par statut
**GET** `/stations/by-status/?status=available`

**Paramètres:**
- `status` (string, optionnel): `available`, `empty`, `unknown`, `all` (défaut: `all`)

**Réponse (200 OK):** Stations filtrées par statut

---

## Codes de statut HTTP

| Code | Signification |
|------|---------------|
| 200 | OK - Requête réussie |
| 201 | Created - Ressource créée |
| 400 | Bad Request - Paramètres invalides |
| 404 | Not Found - Ressource non trouvée |
| 500 | Server Error - Erreur serveur |

---

## Codes de couleur de station

| Couleur | Signification |
|---------|---------------|
| 🟢 Green | Au moins un carburant disponible |
| 🔴 Red | Tous les carburants épuisés |
| 🟡 Yellow | Carburants partiellement disponibles |
| ⚫ Gray | Pas de signalement récent |

---

## Types de carburant

- `Essence`
- `Gazole`

## Statuts de carburant

- `Disponible`
- `Épuisé`

---

## Limitations

- **Rate limiting**: 1 vote par IP par station par heure
- **Expiration**: Les signalements expirent après 4 heures
- **Pagination**: Max 100 résultats par page
- **Recherche**: Min 2 caractères, max 20 résultats

---

## Exemples cURL

### Créer un signalement
```bash
curl -X POST http://localhost:8000/api/signalements/ \
  -H "Content-Type: application/json" \
  -d '{
    "station": 1,
    "fuel_type": "Essence",
    "status": "Disponible"
  }'
```

### Récupérer les stations proches
```bash
curl "http://localhost:8000/api/stations/?lat=12.6452&lon=-8.0029&radius=5"
```

### Approuver un signalement
```bash
curl -X POST http://localhost:8000/api/signalements/1/approve/
```

### Obtenir les statistiques
```bash
curl http://localhost:8000/api/statistics/
```

---

## Notes de développement

- Tous les timestamps sont en UTC (ISO 8601)
- Les coordonnées GPS doivent être valides (lat: -90 à 90, lon: -180 à 180)
- L'IP de l'utilisateur est automatiquement capturée pour le rate limiting
- Les signalements sont triés par timestamp décroissant
