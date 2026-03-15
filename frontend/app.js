/**
 * BAMAKO GAZ TRACKER - Main Application
 * PWA with offline support, real-time updates, and crowd-sourced fuel availability
 */

// ============================================
// CONFIGURATION
// ============================================
const CONFIG = {
    API_BASE_URL: 'http://localhost:8000/api',
    MAP_CENTER: [12.6392, -8.0029], // Bamako center
    MAP_ZOOM: 13,
    REFRESH_INTERVAL: 30000, // 30 seconds
    PULSE_INTERVAL: 5000, // 5 seconds
};

// ============================================
// STATE MANAGEMENT
// ============================================
const state = {
    map: null,
    stations: [],
    markers: {},
    selectedStation: null,
    userLocation: null,
    currentView: 'map',
    lastUpdate: null,
};

// ============================================
// DOM ELEMENTS
// ============================================
const elements = {
    map: document.getElementById('map'),
    loading: document.getElementById('loading'),
    livePulse: document.getElementById('live-pulse'),
    pulseText: document.getElementById('pulse-text'),
    stationSheet: document.getElementById('station-sheet'),
    installPrompt: document.getElementById('install-prompt'),
    installBtn: document.getElementById('install-btn'),
    // Station details
    stationName: document.getElementById('station-name'),
    stationBrand: document.getElementById('station-brand'),
    stationStatus: document.getElementById('station-status'),
    statusText: document.getElementById('status-text'),
    lastUpdate: document.getElementById('last-update'),
    trustScore: document.getElementById('trust-score'),
    stationDistance: document.getElementById('station-distance'),
    distanceRow: document.getElementById('distance-row'),
    // Fuel cards
    essenceCard: document.getElementById('essence-card'),
    gazoleCard: document.getElementById('gazole-card'),
    essenceStatus: document.getElementById('essence-status'),
    gazoleStatus: document.getElementById('gazole-status'),
    // Action buttons
    btnAvailable: document.getElementById('btn-available'),
    btnEmpty: document.getElementById('btn-empty'),
    // Navigation
    navButtons: document.querySelectorAll('.nav-btn'),
};

// ============================================
// INITIALIZATION
// ============================================
document.addEventListener('DOMContentLoaded', () => {
    initApp();
});

async function initApp() {
    try {
        // Initialize map
        initMap();
        
        // Load stations
        await loadStations();
        
        // Get user location
        getUserLocation();
        
        // Setup event listeners
        setupEventListeners();
        
        // Start live pulse
        startLivePulse();
        
        // Setup PWA
        setupPWA();
        
        // Hide loading
        setTimeout(() => {
            elements.loading.classList.add('hidden');
        }, 1000);
        
    } catch (error) {
        console.error('Error initializing app:', error);
        showToast('Erreur lors du chargement de l\'application', 'error');
    }
}

// ============================================
// MAP INITIALIZATION
// ============================================
function initMap() {
    // Create map with dark theme
    state.map = L.map('map', {
        zoomControl: false,
        attributionControl: true,
    }).setView(CONFIG.MAP_CENTER, CONFIG.MAP_ZOOM);
    
    // Add zoom control to bottom right
    L.control.zoom({
        position: 'bottomright'
    }).addTo(state.map);
    
    // Add dark theme tiles (CartoDB Dark Matter)
    L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>',
        subdomains: 'abcd',
        maxZoom: 20
    }).addTo(state.map);
}

// ============================================
// STATIONS MANAGEMENT
// ============================================
async function loadStations() {
    try {
        const url = new URL(`${CONFIG.API_BASE_URL}/stations/`);
        
        // Add user location if available
        if (state.userLocation) {
            url.searchParams.append('lat', state.userLocation.lat);
            url.searchParams.append('lon', state.userLocation.lng);
            url.searchParams.append('radius', 10);
        }
        
        const response = await fetch(url);
        if (!response.ok) throw new Error('Failed to load stations');
        
        state.stations = await response.json();
        renderStations();
        
    } catch (error) {
        console.error('Error loading stations:', error);
        showToast('Erreur de chargement des stations', 'error');
    }
}

function renderStations() {
    // Clear existing markers
    Object.values(state.markers).forEach(marker => state.map.removeLayer(marker));
    state.markers = {};
    
    // Add markers for each station
    state.stations.forEach(station => {
        const marker = createStationMarker(station);
        state.markers[station.id] = marker;
        marker.addTo(state.map);
    });
}

function createStationMarker(station) {
    const color = getStationColor(station);
    const status = getStationStatus(station);
    
    // Create custom icon
    const icon = L.divIcon({
        className: `station-marker ${status} ${isFresh(station) ? 'fresh' : ''}`,
        iconSize: [20, 20],
        iconAnchor: [10, 10],
        popupAnchor: [0, -10],
    });
    
    // Create marker
    const marker = L.marker([station.latitude, station.longitude], { icon });
    
    // Add click handler
    marker.on('click', () => selectStation(station));
    
    // Add popup
    const popupContent = `
        <div style="text-align: center;">
            <strong>${station.name}</strong><br>
            <span style="color: ${getColorHex(color)};">${station.brand}</span>
        </div>
    `;
    marker.bindPopup(popupContent);
    
    return marker;
}

function getStationColor(station) {
    const latest = station.latest_signalement;
    if (!latest) return 'gray';
    if (latest.status === 'Disponible') return 'green';
    return 'red';
}

function getStationStatus(station) {
    const latest = station.latest_signalement;
    if (!latest) return 'unknown';
    if (latest.status === 'Disponible') return 'available';
    return 'empty';
}

function getColorHex(color) {
    const colors = {
        green: '#00FF41',
        red: '#FF3131',
        gray: '#6B7280',
    };
    return colors[color] || colors.gray;
}

function isFresh(station) {
    const latest = station.latest_signalement;
    if (!latest) return false;
    const minutes = getMinutesAgo(latest.timestamp);
    return minutes < 30;
}

// ============================================
// STATION SELECTION
// ============================================
function selectStation(station) {
    state.selectedStation = station;
    
    // Update UI
    elements.stationName.textContent = station.name;
    elements.stationBrand.textContent = station.brand;
    
    // Update status
    const status = getStationStatus(station);
    const statusText = getStatusText(station);
    elements.stationStatus.className = `status-indicator ${status}`;
    elements.statusText.textContent = statusText;
    
    // Update details
    const latest = station.latest_signalement;
    if (latest) {
        elements.lastUpdate.textContent = latest.time_ago;
        elements.trustScore.textContent = `${latest.approval_count} confirmation${latest.approval_count > 1 ? 's' : ''}`;
    } else {
        elements.lastUpdate.textContent = 'Jamais signalé';
        elements.trustScore.textContent = '--';
    }
    
    // Update distance
    if (station.distance) {
        elements.stationDistance.textContent = `${station.distance} km`;
        elements.distanceRow.style.display = 'flex';
    } else {
        elements.distanceRow.style.display = 'none';
    }
    
    // Update fuel cards
    updateFuelCards(station);
    
    // Show sheet
    elements.stationSheet.classList.add('active');
    
    // Center map on station
    state.map.setView([station.latitude, station.longitude], 16);
}

function getStatusText(station) {
    const latest = station.latest_signalement;
    if (!latest) return 'Inconnu';
    if (latest.status === 'Disponible') return 'Carburant disponible';
    return 'Rupture de stock';
}

function updateFuelCards(station) {
    const latest = station.latest_signalement;
    
    // Reset cards
    elements.essenceCard.className = 'fuel-card';
    elements.gazoleCard.className = 'fuel-card';
    elements.essenceStatus.textContent = 'Non signalé';
    elements.gazoleStatus.textContent = 'Non signalé';
    
    if (latest) {
        const isEssence = latest.fuel_type === 'Essence';
        const isAvailable = latest.status === 'Disponible';
        
        if (isEssence) {
            elements.essenceCard.className = `fuel-card ${isAvailable ? 'available' : 'empty'}`;
            elements.essenceStatus.textContent = isAvailable ? 'Disponible' : 'Épuisé';
        } else {
            elements.gazoleCard.className = `fuel-card ${isAvailable ? 'available' : 'empty'}`;
            elements.gazoleStatus.textContent = isAvailable ? 'Disponible' : 'Épuisé';
        }
    }
}

function closeStationSheet() {
    elements.stationSheet.classList.remove('active');
    state.selectedStation = null;
}

// ============================================
// USER LOCATION
// ============================================
function getUserLocation() {
    if (!navigator.geolocation) {
        console.log('Geolocation not supported');
        return;
    }
    
    navigator.geolocation.getCurrentPosition(
        (position) => {
            state.userLocation = {
                lat: position.coords.latitude,
                lng: position.coords.longitude,
            };
            
            // Add user marker
            addUserMarker(state.userLocation);
            
            // Center map on user
            state.map.setView([state.userLocation.lat, state.userLocation.lng], 14);
            
            // Reload stations with location
            loadStations();
        },
        (error) => {
            console.log('Geolocation error:', error);
        },
        { enableHighAccuracy: true, timeout: 10000 }
    );
}

function addUserMarker(location) {
    const icon = L.divIcon({
        className: 'user-location-marker',
        iconSize: [20, 20],
        iconAnchor: [10, 10],
    });
    
    L.marker([location.lat, location.lng], { icon }).addTo(state.map);
}

// ============================================
// SIGNALEMENT (REPORTING)
// ============================================
async function reportAvailability(fuelType, status) {
    if (!state.selectedStation) return;
    
    // Disable buttons
    elements.btnAvailable.disabled = true;
    elements.btnEmpty.disabled = true;
    
    try {
        const response = await fetch(`${CONFIG.API_BASE_URL}/signalements/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                station: state.selectedStation.id,
                fuel_type: fuelType,
                status: status,
            }),
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error || 'Erreur lors du signalement');
        }
        
        const data = await response.json();
        
        // Show success
        showToast('Signalement enregistré ! Merci 🙏', 'success');
        
        // Refresh stations
        await loadStations();
        
        // Update selected station
        const updatedStation = state.stations.find(s => s.id === state.selectedStation.id);
        if (updatedStation) {
            selectStation(updatedStation);
        }
        
    } catch (error) {
        console.error('Error reporting:', error);
        showToast(error.message, 'error');
    } finally {
        elements.btnAvailable.disabled = false;
        elements.btnEmpty.disabled = false;
    }
}

// ============================================
// LIVE PULSE
// ============================================
async function startLivePulse() {
    await updatePulse();
    setInterval(updatePulse, CONFIG.PULSE_INTERVAL);
}

async function updatePulse() {
    try {
        const response = await fetch(`${CONFIG.API_BASE_URL}/signalements/latest/?limit=5`);
        if (!response.ok) return;
        
        const signalements = await response.json();
        if (signalements.length === 0) return;
        
        // Show pulse banner
        elements.livePulse.style.display = 'flex';
        
        // Rotate through signalements
        let index = 0;
        const rotatePulse = () => {
            const s = signalements[index % signalements.length];
            const status = s.status === 'Disponible' ? '✅' : '❌';
            const fuel = s.fuel_type === 'Essence' ? 'Essence' : 'Gazole';
            elements.pulseText.textContent = `${status} ${s.station_name}: ${fuel} ${s.status.toLowerCase()} (${s.time_ago})`;
            index++;
        };
        
        rotatePulse();
        
    } catch (error) {
        console.error('Error updating pulse:', error);
    }
}

// ============================================
// EVENT LISTENERS
// ============================================
function setupEventListeners() {
    // Action buttons
    elements.btnAvailable.addEventListener('click', () => {
        // Report both fuel types as available
        reportAvailability('Essence', 'Disponible');
        setTimeout(() => reportAvailability('Gazole', 'Disponible'), 500);
    });
    
    elements.btnEmpty.addEventListener('click', () => {
        // Report both fuel types as empty
        reportAvailability('Essence', 'Épuisé');
        setTimeout(() => reportAvailability('Gazole', 'Épuisé'), 500);
    });
    
    // Navigation
    elements.navButtons.forEach(btn => {
        btn.addEventListener('click', () => {
            const view = btn.dataset.view;
            switchView(view);
            
            // Update active state
            elements.navButtons.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
        });
    });
    
    // Close sheet on handle click
    document.querySelector('.sheet-handle').addEventListener('click', closeStationSheet);
    
    // Map click to close sheet
    state.map.on('click', closeStationSheet);
    
    // Install button
    elements.installBtn.addEventListener('click', installPWA);
}

function switchView(view) {
    state.currentView = view;
    
    // Hide all views
    document.getElementById('map').style.display = 'none';
    
    // Show selected view
    switch (view) {
        case 'map':
            document.getElementById('map').style.display = 'block';
            closeStationSheet();
            break;
        case 'list':
            showListView();
            break;
        case 'alerts':
            showAlertsView();
            break;
    }
}

function showListView() {
    // Create list view if not exists
    let listView = document.getElementById('list-view');
    if (!listView) {
        listView = document.createElement('div');
        listView.id = 'list-view';
        document.body.appendChild(listView);
    }
    
    // Render list
    listView.innerHTML = state.stations.map(station => `
        <div class="station-list-item" onclick="selectStationById(${station.id})">
            <div class="station-list-header">
                <span class="station-list-name">${station.name}</span>
                <span class="station-list-status ${getStationStatus(station)}"></span>
            </div>
            <div class="station-list-meta">
                <span>${station.brand}</span>
                ${station.distance ? `<span>${station.distance} km</span>` : ''}
            </div>
        </div>
    `).join('');
    
    // Show list
    document.querySelectorAll('#list-view, #alerts-view').forEach(el => el?.classList.remove('active'));
    listView.classList.add('active');
}

function showAlertsView() {
    // Create alerts view if not exists
    let alertsView = document.getElementById('alerts-view');
    if (!alertsView) {
        alertsView = document.createElement('div');
        alertsView.id = 'alerts-view';
        document.body.appendChild(alertsView);
    }
    
    // Get recent signalements
    fetch(`${CONFIG.API_BASE_URL}/signalements/latest/?limit=20`)
        .then(r => r.json())
        .then(signalements => {
            alertsView.innerHTML = signalements.map(s => `
                <div class="alert-item ${s.status === 'Épuisé' ? 'empty' : ''}">
                    <div class="alert-header">
                        <span class="alert-station">${s.station_name}</span>
                        <span class="alert-time">${s.time_ago}</span>
                    </div>
                    <div class="alert-message">
                        ${s.fuel_type} ${s.status.toLowerCase()} - ${s.approval_count} confirmation(s)
                    </div>
                </div>
            `).join('');
        });
    
    // Show alerts
    document.querySelectorAll('#list-view, #alerts-view').forEach(el => el?.classList.remove('active'));
    alertsView.classList.add('active');
}

function selectStationById(id) {
    const station = state.stations.find(s => s.id === id);
    if (station) {
        switchView('map');
        selectStation(station);
        
        // Update nav
        elements.navButtons.forEach(b => b.classList.remove('active'));
        elements.navButtons[0].classList.add('active');
    }
}

// ============================================
// PWA SETUP
// ============================================
let deferredPrompt = null;

function setupPWA() {
    // Listen for install prompt
    window.addEventListener('beforeinstallprompt', (e) => {
        e.preventDefault();
        deferredPrompt = e;
        elements.installPrompt.style.display = 'flex';
    });
    
    // Hide prompt when installed
    window.addEventListener('appinstalled', () => {
        elements.installPrompt.style.display = 'none';
        deferredPrompt = null;
    });
    
    // Register service worker
    if ('serviceWorker' in navigator) {
        navigator.serviceWorker.register('service-worker.js')
            .then(reg => console.log('Service Worker registered'))
            .catch(err => console.log('Service Worker registration failed'));
    }
}

async function installPWA() {
    if (!deferredPrompt) return;
    
    deferredPrompt.prompt();
    const { outcome } = await deferredPrompt.userChoice;
    
    if (outcome === 'accepted') {
        elements.installPrompt.style.display = 'none';
    }
    
    deferredPrompt = null;
}

// ============================================
// UTILITIES
// ============================================
function showToast(message, type = 'success') {
    // Remove existing toasts
    document.querySelectorAll('.toast').forEach(t => t.remove());
    
    // Create toast
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.textContent = message;
    document.body.appendChild(toast);
    
    // Remove after 3 seconds
    setTimeout(() => {
        toast.remove();
    }, 3000);
}

function getMinutesAgo(timestamp) {
    const date = new Date(timestamp);
    const now = new Date();
    return Math.floor((now - date) / 60000);
}

// Expose functions globally for onclick handlers
window.selectStationById = selectStationById;
