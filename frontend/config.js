/**
 * BKO Station - Configuration
 * Configure l'URL de l'API backend
 */

// Détection automatique de l'environnement
const isProduction = window.location.protocol === 'https:';
const hostname = window.location.hostname;

// Configuration automatique basée sur l'environnement
const API_CONFIGS = {
    // Développement local
    'localhost': 'http://localhost:8000/api',
    '127.0.0.1': 'http://localhost:8000/api',
    // Production Render
    'bko-station-frontend.onrender.com': 'https://bko-station-backend.onrender.com/api',
    // Autres environnements - utilise l'hôte actuel
};

// Fonction pour obtenir l'URL de l'API
function getApiBaseUrl() {
    // 1. Vérifier si une variable globale est définie (priorité la plus haute)
    if (window.APP_CONFIG?.API_BASE_URL) {
        return window.APP_CONFIG.API_BASE_URL;
    }
    
    // 2. Vérifier les configurations prédéfinies
    if (API_CONFIGS[hostname]) {
        return API_CONFIGS[hostname];
    }
    
    // 3. Fallback: utiliser l'hôte actuel avec le protocole appropriate
    const protocol = isProduction ? 'https:' : 'http:';
    return `${protocol}//${hostname}:8000/api`;
}

// Configuration globale
window.APP_CONFIG = {
    API_BASE_URL: getApiBaseUrl(),
    ENVIRONMENT: isProduction ? 'production' : 'development',
    
    // Paramètres de l'application
    MAP_CENTER: [12.6392, -8.0029], // Bamako center
    MAP_ZOOM: 13,
    REFRESH_INTERVAL: 30000, // 30 secondes
    PULSE_INTERVAL: 5000, // 5 secondes
    
    // Limites
    MAX_SEARCH_RESULTS: 20,
    MAX_RADIUS_KM: 100,
    
    // Durées (en millisecondes)
    SIGNALEMENT_EXPIRY: 4 * 60 * 60 * 1000, // 4 heures
    VOTE_COOLDOWN: 60 * 60 * 1000, // 1 heure
};

// Debug: afficher la configuration dans la console
if (!isProduction) {
    console.log('🔧 BKO Station - Configuration:');
    console.log('   API URL:', window.APP_CONFIG.API_BASE_URL);
    console.log('   Environment:', window.APP_CONFIG.ENVIRONMENT);
}
