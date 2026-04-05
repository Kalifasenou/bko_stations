"""
Constantes pour l'application BKO Station
"""

# Types de carburant (stations)
FUEL_TYPES = {
    'ESSENCE': 'Essence',
    'GAZOLE': 'Gazole',
}

# Statuts de carburant
FUEL_STATUS = {
    'AVAILABLE': 'Disponible',
    'EMPTY': 'Épuisé',
}

# Statuts électricité (zones)
ELECTRICITY_STATUS = {
    'AVAILABLE': 'Disponible',
    'OUTAGE': 'Coupure',
    'EMPTY_COMPAT': 'Épuisé',
    'UNSTABLE': 'Instable',
    'RETURN_RECENT': 'Retour récent',
}

ELECTRICITY_LOAD_LEVELS = {
    'LOW': 'Faible',
    'NORMAL': 'Normal',
    'HIGH': 'Fort',
}

ELECTRICITY_SOURCES = {
    'HOUSEHOLD': 'Ménage',
    'BUSINESS': 'Commerçant',
    'OBSERVER': 'Observateur',
}

# Couleurs de station
STATION_COLORS = {
    'GREEN': 'green',      # Carburant disponible
    'RED': 'red',          # Carburant épuisé
    'YELLOW': 'yellow',   # Carburant partiellement disponible
    'GRAY': 'gray',       # Pas de signalement récent
}

# Limites de temps (en heures)
TIME_LIMITS = {
    'SIGNALEMENT_EXPIRY': 4,        # Les signalements expirent après 4h
    'VOTE_COOLDOWN': 1,             # 1h entre deux votes pour la même station
    'APPROVAL_COOLDOWN': 1,         # 1h entre deux approbations pour la même station
}

# Limites de distance (en km)
DISTANCE_LIMITS = {
    'DEFAULT_RADIUS': 10,           # Rayon par défaut pour la recherche
    'NEARBY_DEFAULT_RADIUS': 2,     # Rayon par défaut pour les stations proches
    'MIN_RADIUS': 0.1,              # Rayon minimum
    'MAX_RADIUS': 100,              # Rayon maximum
}

# Limites de pagination
PAGINATION_LIMITS = {
    'DEFAULT_PAGE_SIZE': 20,
    'MAX_PAGE_SIZE': 100,
    'MIN_PAGE_SIZE': 1,
}

# Limites de recherche
SEARCH_LIMITS = {
    'MIN_QUERY_LENGTH': 2,
    'MAX_QUERY_LENGTH': 100,
    'MAX_RESULTS': 20,
}

# Limites de statistiques
STATISTICS_LIMITS = {
    'TOP_STATIONS_COUNT': 5,
    'HEATMAP_DEFAULT_HOURS': 24,
    'HEATMAP_MAX_HOURS': 168,  # 1 semaine
}

# Messages d'erreur
ERROR_MESSAGES = {
    'INVALID_COORDINATES': 'Les coordonnées GPS sont invalides',
    'INVALID_RADIUS': 'Le rayon doit être entre {min} et {max} km',
    'DUPLICATE_VOTE': 'Vous avez déjà signalé cette station dans l\'heure',
    'DUPLICATE_APPROVAL': 'Vous avez déjà approuvé un signalement pour cette station dans l\'heure',
    'STATION_NOT_FOUND': 'La station demandée n\'existe pas',
    'INVALID_SEARCH_QUERY': 'La recherche doit contenir au moins {min} caractères',
    'MISSING_PARAMETER': 'Le paramètre \'{param}\' est requis',
}

# Messages de succès
SUCCESS_MESSAGES = {
    'SIGNALEMENT_CREATED': 'Signalement créé avec succès',
    'SIGNALEMENT_APPROVED': 'Signalement approuvé avec succès',
    'STATION_CREATED': 'Station créée avec succès',
    'STATION_UPDATED': 'Station mise à jour avec succès',
    'STATION_DELETED': 'Station supprimée avec succès',
}

# Durées de cache (en secondes)
CACHE_DURATIONS = {
    'STATISTICS': 60,
    'STATISTICS_BY_BRAND': 120,
    'SEARCH': 300,
    'STATIONS_BY_STATUS': 120,
    'FUEL_AVAILABILITY_MAP': 120,
    'SIGNALEMENTS_HEATMAP': 60,
}

# Coordonnées de Bamako (pour validation)
BAMAKO_BOUNDS = {
    'MIN_LAT': 11.5,
    'MAX_LAT': 13.0,
    'MIN_LON': -9.0,
    'MAX_LON': -7.5,
}
