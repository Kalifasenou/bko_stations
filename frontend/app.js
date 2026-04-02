/**
 * BAMAKA GAZ TRACKER - Main Application
 * PWA with offline support, real-time updates, and crowd-sourced fuel availability
 */

// ============================================
// CONFIGURATION
// ============================================
const CONFIG = {
    API_BASE_URL: window.APP_CONFIG?.API_BASE_URL || 'http://localhost:8000/api',
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
    pagination: {
        page: 1,
        hasMore: true,
        loading: false,
    },
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
    electricityStatus: document.getElementById('electricity-status'),
    gasoilSituation: document.getElementById('gasoil-situation'),
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

        // Start periodic stations refresh
        startStationsRefresh();
        
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
    if (state.pagination.loading) return;
    
    state.pagination.loading = true;
    
    try {
        const url = new URL(`${CONFIG.API_BASE_URL}/stations/`);
        
        // Add user location if available
        if (state.userLocation) {
            url.searchParams.append('lat', state.userLocation.lat);
            url.searchParams.append('lon', state.userLocation.lng);
            url.searchParams.append('radius', 10);
        }
        
        // Add pagination params
        url.searchParams.append('page', state.pagination.page);
        url.searchParams.append('page_size', 50);
        
        const response = await fetch(url);
        if (!response.ok) throw new Error('Failed to load stations');
        
        const data = await response.json();
        
        // Handle paginated response
        const newStations = data.results || data;
        
        // Check if there are more pages
        state.pagination.hasMore = !!(data.next);
        
        // Add new stations (avoid duplicates)
        const existingIds = new Set(state.stations.map(s => s.id));
        const uniqueStations = newStations.filter(s => !existingIds.has(s.id));
        state.stations = [...state.stations, ...uniqueStations];
        
        renderStations();
        
    } catch (error) {
        console.error('Error loading stations:', error);
        showToast('Erreur de chargement des stations', 'error');
    } finally {
        state.pagination.loading = false;
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
    // Use the status_color from backend which properly handles both fuel types
    return station.status_color || 'gray';
}

function getStationStatus(station) {
    const color = getStationColor(station);
    if (color === 'green') return 'available';
    if (color === 'red') return 'empty';
    if (color === 'yellow') return 'partial';
    return 'unknown';
}

function getColorHex(color) {
    const colors = {
        green: '#00FF41',
        red: '#FF3131',
        yellow: '#FFD700',
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

    // Update additional situations
    updateAdditionalSituations(station);
    
    // Update fuel cards with BOTH fuel types
    updateFuelCards(station);
    
    // Show sheet
    elements.stationSheet.classList.add('active');
    
    // Center map on station
    state.map.setView([station.latitude, station.longitude], 16);
}

function getStatusText(station) {
    const color = getStationColor(station);
    if (color === 'green') return 'Carburant disponible';
    if (color === 'red') return 'Rupture de stock';
    if (color === 'yellow') return 'Stock partiel';
    return 'Inconnu';
}

function updateFuelCards(station) {
    // Get specific fuel data from backend
    const essenceData = station.essence_signalement;
    const gazoleData = station.gazole_signalement;
    
    // Reset cards
    elements.essenceCard.className = 'fuel-card';
    elements.gazoleCard.className = 'fuel-card';
    elements.essenceStatus.textContent = 'Non signalé';
    elements.gazoleStatus.textContent = 'Non signalé';
    
    // Update essence card
    if (essenceData) {
        elements.essenceCard.className = `fuel-card ${essenceData.status === 'Disponible' ? 'available' : 'empty'}`;
        elements.essenceStatus.textContent = `${essenceData.status} (${essenceData.time_ago})`;
    }
    
    // Update gazole card
    if (gazoleData) {
        elements.gazoleCard.className = `fuel-card ${gazoleData.status === 'Disponible' ? 'available' : 'empty'}`;
        elements.gazoleStatus.textContent = `${gazoleData.status} (${gazoleData.time_ago})`;
    }
}

function updateAdditionalSituations(station) {
    const gazoleData = station.gazole_signalement;

    // L'électricité n'est pas encore fournie par l'API
    elements.electricityStatus.textContent = 'Non disponible dans l’API';

    if (gazoleData) {
        elements.gasoilSituation.textContent = `${gazoleData.status} (${gazoleData.time_ago})`;
    } else {
        elements.gasoilSituation.textContent = 'Non signalé';
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
            state.pagination.page = 1;
            state.stations = [];
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
            let errorPayload = {};
            try {
                errorPayload = await response.json();
            } catch (_) {
                // no-op: fallback message below
            }

            if (response.status === 401) {
                throw new Error('Connexion requise pour envoyer un signalement');
            }

            throw new Error(errorPayload.error || 'Erreur lors du signalement');
        }
        
        const data = await response.json();
        
        // Show success
        showToast('Signalement enregistré ! Merci 🙏', 'success');
        
        // Refresh stations
        state.pagination.page = 1;
        state.stations = [];
        await loadStations();
        
        // Update selected station with fresh data
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

function startStationsRefresh() {
    setInterval(async () => {
        try {
            const selectedStationId = state.selectedStation?.id;

            state.pagination.page = 1;
            state.stations = [];
            await loadStations();

            if (selectedStationId) {
                const refreshedStation = state.stations.find(s => s.id === selectedStationId);
                if (refreshedStation) {
                    selectStation(refreshedStation);
                }
            }
        } catch (error) {
            console.error('Error refreshing stations:', error);
        }
    }, CONFIG.REFRESH_INTERVAL);
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
    // Action buttons - now with fuel type selection
    elements.btnAvailable.addEventListener('click', () => {
        showFuelTypeSelector('Disponible');
    });
    
    elements.btnEmpty.addEventListener('click', () => {
        showFuelTypeSelector('Épuisé');
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
    document.querySelector('.sheet-handle')?.addEventListener('click', closeStationSheet);
    
    // Map click to close sheet
    state.map.on('click', closeStationSheet);
    
    // Install button
    elements.installBtn.addEventListener('click', installPWA);
}

// ============================================
// FUEL TYPE SELECTOR
// ============================================
function showFuelTypeSelector(status) {
    // Create modal if not exists
    let modal = document.getElementById('fuel-type-modal');
    if (!modal) {
        modal = document.createElement('div');
        modal.id = 'fuel-type-modal';
        modal.className = 'modal-overlay';
        modal.innerHTML = `
            <div class="modal-content">
                <h3>Quel carburant signaler ?</h3>
                <div class="fuel-type-options">
                    <button class="fuel-type-btn" data-fuel="Essence">
                        ⛽ Essence
                    </button>
                    <button class="fuel-type-btn" data-fuel="Gazole">
                        🚛 Gazole
                    </button>
                    <button class="fuel-type-btn" data-fuel="both">
                        ⛽ + 🚛 Les deux
                    </button>
                </div>
                <button class="modal-close">Annuler</button>
            </div>
        `;
        document.body.appendChild(modal);
        
        // Add event listeners
        modal.querySelectorAll('.fuel-type-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                const fuelType = btn.dataset.fuel;
                modal.remove();
                submitSignalement(fuelType, status);
            });
        });
        
        modal.querySelector('.modal-close').addEventListener('click', () => {
            modal.remove();
        });
    }
    
    modal.style.display = 'flex';
}

async function submitSignalement(fuelType, status) {
    if (fuelType === 'both') {
        // Report both fuel types
        await reportAvailability('Essence', status);
        await reportAvailability('Gazole', status);
    } else {
        await reportAvailability(fuelType, status);
    }
}

function switchView(view) {
    state.currentView = view;
    
    // Hide all views
    document.getElementById('map').style.display = 'none';
    document.querySelectorAll('.view-container').forEach(el => el.style.display = 'none');
    
    // Show selected view
    switch (view) {
        case 'map':
            document.getElementById('map').style.display = 'block';
            closeStationSheet();
            setTimeout(() => {
                if (state.map) {
                    state.map.invalidateSize();
                }
            }, 0);
            break;
        case 'list':
            showListView();
            break;
        case 'alerts':
            showAlertsView();
            break;
        case 'add-station':
            showAddStationView();
            break;
    }
}

function showListView() {
    // Create list view if not exists
    let listView = document.getElementById('list-view');
    if (!listView) {
        listView = document.createElement('div');
        listView.id = 'list-view';
        listView.className = 'view-container';
        listView.innerHTML = `
            <div class="view-header">
                <h2>Liste des stations</h2>
                <input type="text" id="search-input" placeholder="Rechercher une station..." class="search-input">
            </div>
            <div class="station-list" id="station-list-container"></div>
        `;
        document.body.appendChild(listView);
        
        // Add search listener
        listView.querySelector('#search-input').addEventListener('input', (e) => {
            filterStationList(e.target.value);
        });
    }
    
    // Render list
    renderStationList();
    
    // Show list
    listView.style.display = 'block';
}

function renderStationList(filteredStations = null) {
    const container = document.getElementById('station-list-container');
    if (!container) return;
    
    const stationsToRender = filteredStations || state.stations;
    
    if (stationsToRender.length === 0) {
        container.innerHTML = '<div class="empty-state">Aucune station trouvée</div>';
        return;
    }
    
    container.innerHTML = stationsToRender.map(station => `
        <div class="station-list-item" onclick="selectStationById(${station.id})">
            <div class="station-list-header">
                <span class="station-list-name">${station.name}</span>
                <span class="station-list-status ${getStationStatus(station)}"></span>
            </div>
            <div class="station-list-meta">
                <span>${station.brand}</span>
                ${station.distance ? `<span class="distance-badge">${station.distance} km</span>` : ''}
                ${station.has_recent_signalement ? '<span class="fresh-badge">Récent</span>' : ''}
            </div>
        </div>
    `).join('');
}

function filterStationList(query) {
    if (!query.trim()) {
        renderStationList();
        return;
    }
    
    const filtered = state.stations.filter(station => 
        station.name.toLowerCase().includes(query.toLowerCase()) ||
        station.brand.toLowerCase().includes(query.toLowerCase())
    );
    renderStationList(filtered);
}

function showAlertsView() {
    // Create alerts view if not exists
    let alertsView = document.getElementById('alerts-view');
    if (!alertsView) {
        alertsView = document.createElement('div');
        alertsView.id = 'alerts-view';
        alertsView.className = 'view-container';
        alertsView.innerHTML = `
            <div class="view-header">
                <h2>Derniers signalements</h2>
            </div>
            <div class="alerts-list" id="alerts-list-container"></div>
        `;
        document.body.appendChild(alertsView);
    }
    
    // Get recent signalements
    fetch(`${CONFIG.API_BASE_URL}/signalements/latest/?limit=20`)
        .then(r => r.json())
        .then(signalements => {
            const container = document.getElementById('alerts-list-container');
            if (signalements.length === 0) {
                container.innerHTML = '<div class="empty-state">Aucun signalement récent</div>';
                return;
            }
            
            container.innerHTML = signalements.map(s => `
                <div class="alert-item ${s.status === 'Épuisé' ? 'empty' : ''}">
                    <div class="alert-header">
                        <span class="alert-station">${s.station_name}</span>
                        <span class="alert-time">${s.time_ago}</span>
                    </div>
                    <div class="alert-message">
                        <span class="alert-fuel">${s.fuel_type}</span>
                        <span class="alert-status ${s.status === 'Disponible' ? 'available' : 'empty'}">${s.status}</span>
                        <span class="alert-approvals">${s.approval_count} confirmation(s)</span>
                    </div>
                </div>
            `).join('');
        })
        .catch(err => {
            console.error('Error loading alerts:', err);
        });
    
    // Show alerts
    alertsView.style.display = 'block';
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

function showAddStationView() {
    let addView = document.getElementById('add-station-view');
    if (!addView) {
        addView = document.createElement('div');
        addView.id = 'add-station-view';
        addView.className = 'view-container';
        addView.innerHTML = `
            <div class="view-header">
                <h2>Ajouter une station</h2>
                <p class="view-subtitle">Ajoutez une nouvelle station dans la carte communautaire</p>
            </div>
            <form id="add-station-form" class="station-form">
                <label class="form-label" for="station-name-input">Nom de la station *</label>
                <input id="station-name-input" name="name" class="form-input" type="text" required maxlength="100" placeholder="Ex: Station ACI 2000">

                <label class="form-label" for="station-brand-input">Enseigne *</label>
                <input id="station-brand-input" name="brand" class="form-input" type="text" required maxlength="50" placeholder="Ex: Shell, Total, Oryx">

                <label class="form-label" for="station-address-input">Lieu / Adresse</label>
                <input id="station-address-input" name="address" class="form-input" type="text" maxlength="255" placeholder="Ex: Badalabougou, Bamako">

                <div class="form-grid">
                    <div>
                        <label class="form-label" for="station-lat-input">Latitude GPS *</label>
                        <input id="station-lat-input" name="latitude" class="form-input" type="number" required step="any" min="-90" max="90" placeholder="12.6392">
                    </div>
                    <div>
                        <label class="form-label" for="station-lon-input">Longitude GPS *</label>
                        <input id="station-lon-input" name="longitude" class="form-input" type="number" required step="any" min="-180" max="180" placeholder="-8.0029">
                    </div>
                </div>

                <label class="form-label" for="station-manager-input">Nom du gérant</label>
                <input id="station-manager-input" name="manager_name" class="form-input" type="text" maxlength="100" placeholder="Ex: Moussa Traoré">

                <button id="add-station-submit" class="form-submit-btn" type="submit">Enregistrer la station</button>
            </form>
        `;
        document.body.appendChild(addView);

        const form = addView.querySelector('#add-station-form');
        form.addEventListener('submit', handleAddStationSubmit);
    }

    addView.style.display = 'block';
}

function parseCoordinate(value) {
    const parsed = Number.parseFloat(value);
    return Number.isFinite(parsed) ? parsed : null;
}

async function handleAddStationSubmit(event) {
    event.preventDefault();

    const form = event.target;
    const submitButton = form.querySelector('#add-station-submit');
    const formData = new FormData(form);

    const latitude = parseCoordinate(formData.get('latitude'));
    const longitude = parseCoordinate(formData.get('longitude'));

    if (latitude === null || latitude < -90 || latitude > 90) {
        showToast('Latitude invalide (-90 à 90)', 'error');
        return;
    }

    if (longitude === null || longitude < -180 || longitude > 180) {
        showToast('Longitude invalide (-180 à 180)', 'error');
        return;
    }

    const payload = {
        name: String(formData.get('name') || '').trim(),
        brand: String(formData.get('brand') || '').trim(),
        address: String(formData.get('address') || '').trim(),
        latitude,
        longitude,
        manager_name: String(formData.get('manager_name') || '').trim(),
        is_active: true,
    };

    if (!payload.name || !payload.brand) {
        showToast('Nom et enseigne sont obligatoires', 'error');
        return;
    }

    submitButton.disabled = true;

    try {
        const response = await fetch(`${CONFIG.API_BASE_URL}/stations/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(payload),
        });

        const responseData = await response.json();

        if (!response.ok) {
            if (response.status === 401) {
                throw new Error('Connexion requise pour ajouter une station');
            }
            const errorMessage = responseData.error || 'Erreur lors de la création de la station';
            throw new Error(errorMessage);
        }

        showToast('Station ajoutée avec succès', 'success');

        form.reset();

        state.pagination.page = 1;
        state.stations = [];
        await loadStations();

        switchView('map');
        elements.navButtons.forEach(b => b.classList.remove('active'));
        elements.navButtons[0].classList.add('active');
    } catch (error) {
        console.error('Error creating station:', error);
        showToast(error.message, 'error');
    } finally {
        submitButton.disabled = false;
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
