/**
 * BAMAKO GAZ TRACKER - Service Worker
 * Provides offline support and caching for PWA functionality
 */

const CACHE_NAME = 'bamako-gaz-v2';
const STATIC_CACHE = 'bamako-gaz-static-v2';
const MAP_CACHE = 'bamako-gaz-maps-v2';
const API_CACHE = 'bamako-gaz-api-v2';

// Static assets to cache on install
const STATIC_ASSETS = [
    '/',
    '/index.html',
    '/styles.css',
    '/app.js',
    '/manifest.json',
    // External resources
    'https://unpkg.com/leaflet@1.9.4/dist/leaflet.css',
    'https://unpkg.com/leaflet@1.9.4/dist/leaflet.js',
];

// Install event - cache static assets
self.addEventListener('install', (event) => {
    console.log('[SW] Installing...');
    
    event.waitUntil(
        caches.open(STATIC_CACHE)
            .then(cache => {
                console.log('[SW] Caching static assets');
                return cache.addAll(STATIC_ASSETS);
            })
            .catch(err => console.error('[SW] Error caching static assets:', err))
    );
    
    // Skip waiting to activate immediately
    self.skipWaiting();
});

// Activate event - clean up old caches
self.addEventListener('activate', (event) => {
    console.log('[SW] Activating...');
    
    event.waitUntil(
        caches.keys()
            .then(cacheNames => {
                return Promise.all(
                    cacheNames.map(cacheName => {
                        // Delete old versions
                        if (cacheName !== STATIC_CACHE && 
                            cacheName !== MAP_CACHE && 
                            cacheName !== API_CACHE) {
                            console.log('[SW] Deleting old cache:', cacheName);
                            return caches.delete(cacheName);
                        }
                    })
                );
            })
            .then(() => {
                console.log('[SW] Claiming clients');
                return self.clients.claim();
            })
    );
});

// Fetch event - serve from cache or network
self.addEventListener('fetch', (event) => {
    const { request } = event;
    const url = new URL(request.url);
    
    // Skip non-GET requests
    if (request.method !== 'GET') {
        return;
    }
    
    // Handle different types of requests
    if (isMapTile(request)) {
        event.respondWith(handleMapTile(request));
    } else if (isAPIRequest(request)) {
        event.respondWith(handleAPIRequest(request));
    } else if (isStaticAsset(request)) {
        event.respondWith(handleStaticAsset(request));
    } else {
        // Default: network first, cache fallback
        event.respondWith(networkFirst(request));
    }
});

// ============================================
// REQUEST TYPE CHECKERS
// ============================================

function isMapTile(request) {
    return request.url.includes('basemaps.cartocdn.com') ||
           request.url.includes('tile.openstreetmap.org') ||
           request.url.includes('.tile.');
}

function isAPIRequest(request) {
    return request.url.includes('/api/');
}

function isStaticAsset(request) {
    const staticExtensions = ['.html', '.css', '.js', '.json', '.png', '.jpg', '.svg', '.woff', '.woff2'];
    return staticExtensions.some(ext => request.url.endsWith(ext));
}

// ============================================
// CACHE STRATEGIES
// ============================================

// Cache First - for static assets
async function handleStaticAsset(request) {
    const cache = await caches.open(STATIC_CACHE);
    const cached = await cache.match(request);
    
    if (cached) {
        // Return cached version and update in background
        fetch(request)
            .then(response => {
                if (response.ok) {
                    cache.put(request, response.clone());
                }
            })
            .catch(() => {});
        
        return cached;
    }
    
    // Not in cache, fetch and cache
    try {
        const response = await fetch(request);
        if (response.ok) {
            cache.put(request, response.clone());
        }
        return response;
    } catch (error) {
        // Return offline fallback for HTML
        if (request.url.endsWith('.html') || request.url.endsWith('/')) {
            return cache.match('/index.html');
        }
        throw error;
    }
}

// Stale While Revalidate - for map tiles
async function handleMapTile(request) {
    const cache = await caches.open(MAP_CACHE);
    const cached = await cache.match(request);
    
    const fetchPromise = fetch(request)
        .then(response => {
            if (response.ok) {
                cache.put(request, response.clone());
            }
            return response;
        })
        .catch(() => cached);
    
    return cached || fetchPromise;
}

// Network First with Cache Fallback - for API requests
async function handleAPIRequest(request) {
    const cache = await caches.open(API_CACHE);
    
    try {
        const networkResponse = await fetch(request);
        
        if (networkResponse.ok) {
            // Cache successful API responses
            cache.put(request, networkResponse.clone());
            return networkResponse;
        }
        
        throw new Error('Network response not ok');
        
    } catch (error) {
        // Try to return cached version
        const cached = await cache.match(request);
        
        if (cached) {
            console.log('[SW] Serving cached API response');
            return cached;
        }
        
        // Return offline response
        return new Response(
            JSON.stringify({ 
                error: 'Offline',
                message: 'Vous êtes hors ligne. Les données seront synchronisées dès que possible.'
            }),
            {
                status: 503,
                headers: { 'Content-Type': 'application/json' }
            }
        );
    }
}

// Network First - general fallback
async function networkFirst(request) {
    try {
        const networkResponse = await fetch(request);
        return networkResponse;
    } catch (error) {
        const cache = await caches.open(STATIC_CACHE);
        const cached = await cache.match(request);
        
        if (cached) {
            return cached;
        }
        
        throw error;
    }
}

// ============================================
// BACKGROUND SYNC (for offline reports)
// ============================================

self.addEventListener('sync', (event) => {
    if (event.tag === 'sync-reports') {
        event.waitUntil(syncReports());
    }
});

async function syncReports() {
    // Get pending reports from IndexedDB and send them
    // This would require IndexedDB setup in the main app
    console.log('[SW] Syncing pending reports...');
}

// ============================================
// PUSH NOTIFICATIONS (for live updates)
// ============================================

self.addEventListener('push', (event) => {
    const data = event.data?.json() || {};
    
    const options = {
        body: data.body || 'Nouvelle mise à jour disponible',
        icon: '/icons/icon.svg',
        badge: '/icons/icon.svg',
        tag: data.tag || 'bamako-gaz-update',
        requireInteraction: false,
        data: data.data || {},
        actions: [
            {
                action: 'open',
                title: 'Ouvrir'
            },
            {
                action: 'dismiss',
                title: 'Ignorer'
            }
        ]
    };
    
    event.waitUntil(
        self.registration.showNotification(
            data.title || 'Bamako Gaz Tracker',
            options
        )
    );
});

self.addEventListener('notificationclick', (event) => {
    event.notification.close();
    
    if (event.action === 'open' || !event.action) {
        event.waitUntil(
            clients.openWindow('/')
        );
    }
});

// ============================================
// MESSAGE HANDLING (from main app)
// ============================================

self.addEventListener('message', (event) => {
    if (event.data === 'skipWaiting') {
        self.skipWaiting();
    }
    
    if (event.data.type === 'CACHE_URLS') {
        const urls = event.data.urls;
        event.waitUntil(
            caches.open(STATIC_CACHE)
                .then(cache => cache.addAll(urls))
        );
    }
    
    if (event.data.type === 'CLEAR_CACHE') {
        event.waitUntil(
            caches.keys()
                .then(names => Promise.all(names.map(name => caches.delete(name))))
        );
    }
});

// ============================================
// PERIODIC SYNC (for background updates)
// ============================================

self.addEventListener('periodicsync', (event) => {
    if (event.tag === 'station-updates') {
        event.waitUntil(updateStationData());
    }
});

async function updateStationData() {
    // Fetch latest station data in background
    console.log('[SW] Periodic sync: updating station data');
}
