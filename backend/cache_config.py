"""
Configuration du cache pour l'application BKO Station
"""

# Configuration du cache en mémoire (développement)
CACHES_DEVELOPMENT = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'bko-station-cache',
        'TIMEOUT': 300,  # 5 minutes par défaut
        'OPTIONS': {
            'MAX_ENTRIES': 1000
        }
    }
}

# Configuration du cache avec Redis (production)
CACHES_PRODUCTION = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': 'redis://127.0.0.1:6379/1',
        'TIMEOUT': 300,
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            'CONNECTION_POOL_KWARGS': {'max_connections': 50}
        }
    }
}

# Configuration du cache avec fichiers (alternative)
CACHES_FILE = {
    'default': {
        'BACKEND': 'django.core.cache.backends.filebased.FileBasedCache',
        'LOCATION': '/var/tmp/bko_station_cache',
        'TIMEOUT': 300,
        'OPTIONS': {
            'MAX_ENTRIES': 1000
        }
    }
}

# Durées de cache par endpoint
CACHE_TIMEOUTS = {
    'statistics': 60,           # 1 minute
    'statistics_by_brand': 120, # 2 minutes
    'search': 300,              # 5 minutes
    'stations_by_status': 120,  # 2 minutes
    'fuel_availability_map': 120,  # 2 minutes
    'signalements_heatmap': 60,    # 1 minute
}

# Configuration du cache pour les vues
CACHE_MIDDLEWARE_SECONDS = 600  # 10 minutes

# Clés de cache personnalisées
CACHE_KEYS = {
    'stations_list': 'stations:list',
    'statistics': 'stats:global',
    'statistics_by_brand': 'stats:by_brand',
    'top_stations': 'stats:top_stations',
}
