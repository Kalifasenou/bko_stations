/**
 * BAMAKA GAZ TRACKER - Main Application
 * PWA with offline support, real-time updates, and crowd-sourced fuel availability
 */

// ============================================
// CONFIGURATION
// ============================================
const CONFIG = {
  API_BASE_URL: window.APP_CONFIG?.API_BASE_URL || "http://localhost:8000/api",
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
  currentView: "list",
  lastUpdate: null,
  authToken: null,
  currentUser: null,
  isStaff: false,
  electricityByStation: {},
  electricityZones: [],
  electricityRecommendation: null,
  electricityLastSyncAt: null,
  electricityFilters: {
    status: "all",
    radius: 10,
    freshnessMinutes: 240,
    sortBy: "distance",
  },
  lastSyncAt: null,
  searchFilters: {
    query: "",
    availableFuel: "all",
    radius: 10,
    freshnessMinutes: 240,
    sortBy: "distance",
  },
  addStation: {
    isPrefilledFromGeolocation: false,
    locationFillInProgress: false,
    lastKnownLatitude: null,
    lastKnownLongitude: null,
    locationStatus: "",
  },
  addStationMap: null,
  addStationMarker: null,
  pagination: {
    page: 1,
    hasMore: true,
    loading: false,
  },
};

const AUTH_STORAGE_KEYS = {
  TOKEN: "bko_auth_token",
  USERNAME: "bko_auth_username",
  IS_STAFF: "bko_auth_is_staff",
};

// ============================================
// DOM ELEMENTS
// ============================================
const elements = {
  map: document.getElementById("map"),
  loading: document.getElementById("loading"),
  livePulse: document.getElementById("live-pulse"),
  pulseText: document.getElementById("pulse-text"),
  stationSheet: document.getElementById("station-sheet"),
  installPrompt: document.getElementById("install-prompt"),
  installBtn: document.getElementById("install-btn"),
  // Station details
  stationName: document.getElementById("station-name"),
  stationBrand: document.getElementById("station-brand"),
  stationStatus: document.getElementById("station-status"),
  statusText: document.getElementById("status-text"),
  lastUpdate: document.getElementById("last-update"),
  trustScore: document.getElementById("trust-score"),
  stationDistance: document.getElementById("station-distance"),
  distanceRow: document.getElementById("distance-row"),
  electricityStatus: document.getElementById("electricity-status"),
  gasoilSituation: document.getElementById("gasoil-situation"),
  // Fuel cards
  essenceCard: document.getElementById("essence-card"),
  gazoleCard: document.getElementById("gazole-card"),
  essenceStatus: document.getElementById("essence-status"),
  gazoleStatus: document.getElementById("gazole-status"),
  // Action buttons
  btnAvailable: document.getElementById("btn-available"),
  btnEmpty: document.getElementById("btn-empty"),
  // Auth
  authInfo: document.getElementById("auth-info"),
  authToggle: document.getElementById("auth-toggle"),
  // Navigation
  navButtons: document.querySelectorAll(".nav-btn"),
};

// ============================================
// INITIALIZATION
// ============================================
document.addEventListener("DOMContentLoaded", () => {
  initApp();
});

async function initApp() {
  try {
    initAuth();

    // Initialize map
    initMap();

    // Setup event listeners
    setupEventListeners();

    // Get user location first (core UX)
    await getUserLocation();

    // Load nearby stations with current filters
    await refreshStations({ keepSelection: false, showToastOnError: true });

    // Default to list view for quick decision making
    switchView("list");
    elements.navButtons.forEach((b) => b.classList.remove("active"));
    const listBtn = Array.from(elements.navButtons).find(
      (b) => b.dataset.view === "list",
    );
    if (listBtn) listBtn.classList.add("active");

    // Start live pulse
    startLivePulse();

    // Start periodic stations refresh
    startStationsRefresh();

    // Setup PWA
    setupPWA();

    // Hide loading
    setTimeout(() => {
      elements.loading.classList.add("hidden");
    }, 700);
  } catch (error) {
    console.error("Error initializing app:", error);
    showToast("Erreur lors du chargement de l'application", "error");
  }
}

// ============================================
// MAP INITIALIZATION
// ============================================
function initMap() {
  // Create map with dark theme
  state.map = L.map("map", {
    zoomControl: false,
    attributionControl: true,
  }).setView(CONFIG.MAP_CENTER, CONFIG.MAP_ZOOM);

  // Add zoom control to bottom right
  L.control
    .zoom({
      position: "bottomright",
    })
    .addTo(state.map);

  // Add dark theme tiles (CartoDB Dark Matter)
  L.tileLayer("https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png", {
    attribution:
      '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>',
    subdomains: "abcd",
    maxZoom: 20,
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

    if (state.userLocation) {
      url.searchParams.append("lat", state.userLocation.lat);
      url.searchParams.append("lon", state.userLocation.lng);
      url.searchParams.append("radius", String(state.searchFilters.radius));
    }

    if (state.searchFilters.availableFuel !== "all") {
      url.searchParams.append(
        "available_fuel",
        state.searchFilters.availableFuel,
      );
    }

    if (state.searchFilters.freshnessMinutes) {
      url.searchParams.append(
        "freshness_minutes",
        String(state.searchFilters.freshnessMinutes),
      );
    }

    if (state.searchFilters.sortBy === "recent") {
      url.searchParams.append("sort_by", "recent");
    } else if (state.searchFilters.sortBy === "name") {
      url.searchParams.append("sort_by", "name");
    }

    url.searchParams.append("page", state.pagination.page);
    url.searchParams.append("page_size", 50);

    const response = await fetch(url);
    if (!response.ok) throw new Error("Failed to load stations");

    const data = await response.json();
    const newStations = data.results || data;
    state.pagination.hasMore = !!data.next;

    const existingIds = new Set(state.stations.map((s) => s.id));
    const uniqueStations = newStations.filter((s) => !existingIds.has(s.id));
    state.stations = [...state.stations, ...uniqueStations];
    state.lastSyncAt = new Date();

    renderStations();
  } catch (error) {
    console.error("Error loading stations:", error);
    throw error;
  } finally {
    state.pagination.loading = false;
  }
}

function getFuelBadgeText(signalement) {
  if (!signalement) return "Inconnu";
  return `${signalement.status} • ${signalement.time_ago}`;
}

function getFuelClass(signalement) {
  if (!signalement) return "unknown";
  return signalement.status === "Disponible" ? "available" : "empty";
}

function applyClientSearchFilter(stations) {
  const query = (state.searchFilters.query || "").trim().toLowerCase();
  if (!query) return stations;

  return stations.filter(
    (station) =>
      station.name.toLowerCase().includes(query) ||
      station.brand.toLowerCase().includes(query),
  );
}

function renderStations() {
  const filteredStations = applyClientSearchFilter(state.stations);

  Object.values(state.markers).forEach((marker) =>
    state.map.removeLayer(marker),
  );
  state.markers = {};

  filteredStations.forEach((station) => {
    const marker = createStationMarker(station);
    state.markers[station.id] = marker;
    marker.addTo(state.map);
  });

  if (state.currentView === "list") {
    renderStationList(filteredStations);
  }

  updateSyncIndicator();
}

function createStationMarker(station) {
  const color = getStationColor(station);
  const status = getStationStatus(station);

  // Create custom icon
  const icon = L.divIcon({
    className: `station-marker ${status} ${isFresh(station) ? "fresh" : ""}`,
    iconSize: [20, 20],
    iconAnchor: [10, 10],
    popupAnchor: [0, -10],
  });

  // Create marker
  const marker = L.marker([station.latitude, station.longitude], { icon });

  // Add click handler
  marker.on("click", () => selectStation(station));

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
  return station.status_color || "gray";
}

function getStationStatus(station) {
  const color = getStationColor(station);
  if (color === "green") return "available";
  if (color === "red") return "empty";
  if (color === "yellow") return "partial";
  return "unknown";
}

function getColorHex(color) {
  const colors = {
    green: "#00FF41",
    red: "#FF3131",
    yellow: "#FFD700",
    gray: "#6B7280",
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
    elements.trustScore.textContent = `${latest.approval_count} confirmation${latest.approval_count > 1 ? "s" : ""}`;
  } else {
    elements.lastUpdate.textContent = "Jamais signalé";
    elements.trustScore.textContent = "--";
  }

  // Update distance
  if (station.distance) {
    elements.stationDistance.textContent = `${station.distance} km`;
    elements.distanceRow.style.display = "flex";
  } else {
    elements.distanceRow.style.display = "none";
  }

  // Update additional situations
  void updateAdditionalSituations(station);

  // Update fuel cards with BOTH fuel types
  updateFuelCards(station);

  // Show sheet
  elements.stationSheet.classList.add("active");

  // Center map on station
  state.map.setView([station.latitude, station.longitude], 16);
}

function getStatusText(station) {
  const color = getStationColor(station);
  if (color === "green") return "Carburant disponible";
  if (color === "red") return "Rupture de stock";
  if (color === "yellow") return "Stock partiel";
  return "Inconnu";
}

function updateFuelCards(station) {
  // Get specific fuel data from backend
  const essenceData = station.essence_signalement;
  const gazoleData = station.gazole_signalement;

  // Reset cards
  elements.essenceCard.className = "fuel-card";
  elements.gazoleCard.className = "fuel-card";
  elements.essenceStatus.textContent = "Non signalé";
  elements.gazoleStatus.textContent = "Non signalé";

  // Update essence card
  if (essenceData) {
    elements.essenceCard.className = `fuel-card ${essenceData.status === "Disponible" ? "available" : "empty"}`;
    elements.essenceStatus.textContent = `${essenceData.status} (${essenceData.time_ago})`;
  }

  // Update gazole card
  if (gazoleData) {
    elements.gazoleCard.className = `fuel-card ${gazoleData.status === "Disponible" ? "available" : "empty"}`;
    elements.gazoleStatus.textContent = `${gazoleData.status} (${gazoleData.time_ago})`;
  }
}

async function updateAdditionalSituations(station) {
  const gazoleData = station.gazole_signalement;

  if (gazoleData) {
    elements.gasoilSituation.textContent = `${gazoleData.status} (${gazoleData.time_ago})`;
  } else {
    elements.gasoilSituation.textContent = "Non signalé";
  }

  const cacheKey = `${station.id}:${station.latitude}:${station.longitude}`;
  let electricityData = state.electricityByStation[cacheKey];

  if (!electricityData) {
    try {
      const url = new URL(`${CONFIG.API_BASE_URL}/electricity/by-location/`);
      url.searchParams.append("lat", station.latitude);
      url.searchParams.append("lon", station.longitude);
      const response = await fetch(url);
      if (response.ok) {
        electricityData = await response.json();
        state.electricityByStation[cacheKey] = electricityData;
      }
    } catch (error) {
      console.error("Erreur chargement électricité par zone:", error);
    }
  }

  if (electricityData?.signalement?.status) {
    const status = electricityData.signalement.status;
    const zoneName = electricityData.zone?.name
      ? ` - ${electricityData.zone.name}`
      : "";
    const timeAgo = electricityData.signalement.time_ago
      ? ` (${electricityData.signalement.time_ago})`
      : "";
    elements.electricityStatus.textContent = `${status}${zoneName}${timeAgo}`;
  } else if (electricityData && !electricityData.zone) {
    elements.electricityStatus.textContent = "Hors zone électrique couverte";
  } else {
    elements.electricityStatus.textContent = "Non signalé";
  }
}

function closeStationSheet() {
  elements.stationSheet.classList.remove("active");
  state.selectedStation = null;
}

// ============================================
// AUTHENTICATION
// ============================================
function initAuth() {
  state.authToken = localStorage.getItem(AUTH_STORAGE_KEYS.TOKEN);
  const savedUsername = localStorage.getItem(AUTH_STORAGE_KEYS.USERNAME);
  const savedPhone = localStorage.getItem("bko_auth_phone");
  const savedIsStaff = localStorage.getItem(AUTH_STORAGE_KEYS.IS_STAFF);
  state.isStaff = savedIsStaff === "true";
  state.currentUser = savedUsername
    ? { username: savedUsername, phone: savedPhone || "" }
    : null;

  if (elements.authToggle) {
    elements.authToggle.addEventListener("click", () => {
      if (state.authToken) {
        logout();
        return;
      }
      showAuthModal("login");
    });
  }

  const adminBtn = document.getElementById("admin-btn");
  if (adminBtn) {
    adminBtn.addEventListener("click", () => {
      switchView("admin");
      elements.navButtons.forEach((b) => b.classList.remove("active"));
    });
  }

  updateAuthUI();
}

function updateAuthUI() {
  const isAuthenticated = Boolean(state.authToken);

  if (elements.authInfo) {
    if (isAuthenticated) {
      const display =
        state.currentUser?.phone ||
        state.currentUser?.username ||
        "utilisateur";
      elements.authInfo.textContent = `Connecté: ${display}`;
    } else {
      elements.authInfo.textContent = "Pas besoin de compte ✨";
    }
  }

  if (elements.authToggle) {
    elements.authToggle.textContent = isAuthenticated
      ? "Se déconnecter"
      : "Se connecter";
  }

  const adminBtn = document.getElementById("admin-btn");
  if (adminBtn) {
    adminBtn.style.display = isAuthenticated && state.isStaff ? "flex" : "none";
  }
}

function logout() {
  state.authToken = null;
  state.currentUser = null;
  state.isStaff = false;
  localStorage.removeItem(AUTH_STORAGE_KEYS.TOKEN);
  localStorage.removeItem(AUTH_STORAGE_KEYS.USERNAME);
  localStorage.removeItem(AUTH_STORAGE_KEYS.IS_STAFF);
  updateAuthUI();
  showToast("Déconnexion effectuée", "success");
}

function getAuthHeaders() {
  if (!state.authToken) {
    return {};
  }
  return {
    Authorization: `Bearer ${state.authToken}`,
  };
}

function requireAuth(actionLabel) {
  if (state.authToken) {
    return true;
  }

  showToast(`Connexion requise pour ${actionLabel}`, "error");
  showAuthModal("login");
  return false;
}

function showAuthModal(mode = "login") {
  let modal = document.getElementById("auth-modal");

  if (!modal) {
    modal = document.createElement("div");
    modal.id = "auth-modal";
    modal.className = "modal-overlay";
    document.body.appendChild(modal);
  }

  const isLogin = mode === "login";
  modal.innerHTML = `
        <div class="modal-content auth-modal-content">
            <h3>${isLogin ? "Connexion" : "Créer un compte"}</h3>
            <p style="font-size:13px;color:rgba(255,255,255,0.65);margin:0 0 12px 0;text-align:center;">💡 Un compte est optionnel — vous pouvez signaler sans vous inscrire</p>
            <div id="auth-feedback" class="auth-feedback" style="display:none;"></div>
            <form id="auth-form" class="auth-form">
                ${
                  isLogin
                    ? '<input id="auth-phone" class="form-input" type="tel" name="identifier" minlength="6" required placeholder="Numéro de téléphone (ex: 70000000)">'
                    : '<input id="auth-username" class="form-input" type="text" name="username" minlength="3" maxlength="150" required placeholder="Nom d\'utilisateur">'
                }
                <input id="auth-password" class="form-input" type="password" name="password" minlength="8" required placeholder="Mot de passe">
                ${!isLogin ? '<input id="auth-phone-reg" class="form-input" type="tel" name="phone" minlength="6" required placeholder="Numéro de téléphone (ex: 70000000)">' : ""}
                <button id="auth-submit" class="form-submit-btn" type="submit">${isLogin ? "Se connecter" : "Créer le compte"}</button>
            </form>
            <button id="auth-switch" class="modal-close" type="button">${isLogin ? "Créer un compte" : "J\u2019ai déjà un compte"}</button>
            <button id="auth-close" class="modal-close" type="button">Fermer</button>
        </div>
    `;

  const form = modal.querySelector("#auth-form");
  const authSwitch = modal.querySelector("#auth-switch");
  const authClose = modal.querySelector("#auth-close");
  const feedback = modal.querySelector("#auth-feedback");

  function showFeedback(message, type) {
    feedback.textContent = message;
    feedback.className = `auth-feedback ${type}`;
    feedback.style.display = "block";
    // Scroll feedback into view so user sees it
    feedback.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }

  function clearFeedback() {
    feedback.style.display = "none";
    feedback.textContent = "";
  }

  function setLoading(loading) {
    const btn = form.querySelector("#auth-submit");
    if (loading) {
      btn.disabled = true;
      btn.textContent = "Traitement en cours...";
    } else {
      btn.disabled = false;
      btn.textContent = isLogin ? "Se connecter" : "Créer le compte";
    }
  }

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    clearFeedback();

    const identifier = form.identifier
      ? String(form.identifier.value || "").trim()
      : "";
    const password = String(form.password.value || "").trim();
    const username = form.username
      ? String(form.username.value || "").trim()
      : "";
    const phone = form.phone ? String(form.phone.value || "").trim() : "";

    if (isLogin) {
      if (!identifier || !password) {
        showFeedback(
          "Veuillez saisir votre numéro de téléphone et votre mot de passe",
          "error",
        );
        return;
      }
    } else {
      if (!username || !password || !phone) {
        showFeedback("Veuillez remplir tous les champs", "error");
        return;
      }
    }

    setLoading(true);
    try {
      if (isLogin) {
        await login(identifier, password);
      } else {
        await register(username, password, phone);
      }
      modal.style.display = "none";
    } catch (error) {
      showFeedback(error.message, "error");
    } finally {
      setLoading(false);
    }
  });

  authSwitch.addEventListener("click", () => {
    showAuthModal(isLogin ? "register" : "login");
  });

  authClose.addEventListener("click", () => {
    modal.style.display = "none";
  });

  modal.style.display = "flex";
}

async function login(identifier, password) {
  const response = await fetch(`${CONFIG.API_BASE_URL}/auth/login/`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ identifier, password }),
  });

  const payload = await response.json();

  if (!response.ok || !payload.access) {
    throw new Error(payload.error || "Identifiant ou mot de passe incorrect");
  }

  state.authToken = payload.access;
  state.currentUser = {
    id: payload.user?.id,
    username: payload.user?.username || identifier,
    phone: payload.user?.phone || identifier,
  };
  state.isStaff = Boolean(payload.user?.is_staff);
  localStorage.setItem(AUTH_STORAGE_KEYS.TOKEN, payload.access);
  localStorage.setItem(AUTH_STORAGE_KEYS.USERNAME, state.currentUser.username);
  localStorage.setItem("bko_auth_phone", state.currentUser.phone);
  localStorage.setItem(AUTH_STORAGE_KEYS.IS_STAFF, String(state.isStaff));
  updateAuthUI();
  showToast("Connexion réussie", "success");
}

async function register(username, password, phone) {
  const response = await fetch(`${CONFIG.API_BASE_URL}/auth/register/`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ username, password, phone }),
  });

  const payload = await response.json();

  if (!response.ok || !payload.access) {
    throw new Error(payload.error || "Création du compte impossible");
  }

  state.authToken = payload.access;
  state.currentUser = {
    id: payload.user?.id,
    username: payload.user?.username || username,
    phone: payload.user?.phone || phone,
  };
  state.isStaff = Boolean(payload.user?.is_staff);
  localStorage.setItem(AUTH_STORAGE_KEYS.TOKEN, payload.access);
  localStorage.setItem(AUTH_STORAGE_KEYS.USERNAME, state.currentUser.username);
  localStorage.setItem("bko_auth_phone", state.currentUser.phone);
  localStorage.setItem(AUTH_STORAGE_KEYS.IS_STAFF, String(state.isStaff));
  updateAuthUI();
  showToast("Compte créé avec succès ! Connecté.", "success");
}

// ============================================
// USER LOCATION
// ============================================
let userMarker = null;

async function getUserLocation() {
  if (!navigator.geolocation) {
    console.log("Geolocation not supported");
    showToast("Géolocalisation non supportée", "error");
    return false;
  }

  return new Promise((resolve) => {
    navigator.geolocation.getCurrentPosition(
      (position) => {
        state.userLocation = {
          lat: position.coords.latitude,
          lng: position.coords.longitude,
        };

        addUserMarker(state.userLocation);
        state.map.setView([state.userLocation.lat, state.userLocation.lng], 14);
        resolve(true);
      },
      (error) => {
        console.log("Geolocation error:", error);
        showToast("Position non détectée. Affichage global activé.", "error");
        resolve(false);
      },
      { enableHighAccuracy: true, timeout: 10000 },
    );
  });
}

function addUserMarker(location) {
  const icon = L.divIcon({
    className: "user-location-marker",
    iconSize: [20, 20],
    iconAnchor: [10, 10],
  });

  if (userMarker) {
    state.map.removeLayer(userMarker);
  }

  userMarker = L.marker([location.lat, location.lng], { icon }).addTo(
    state.map,
  );
}

async function refreshStations({
  keepSelection = true,
  showToastOnError = false,
} = {}) {
  const selectedStationId = keepSelection ? state.selectedStation?.id : null;

  state.pagination.page = 1;
  state.stations = [];

  try {
    await loadStations();

    if (selectedStationId) {
      const refreshedStation = state.stations.find(
        (s) => s.id === selectedStationId,
      );
      if (refreshedStation) {
        selectStation(refreshedStation);
      }
    }
  } catch (error) {
    if (showToastOnError) {
      showToast("Erreur de chargement des stations", "error");
    }
  }
}

function updateSyncIndicator() {
  const syncEl = document.getElementById("sync-info");
  if (!syncEl) return;

  if (!state.lastSyncAt) {
    syncEl.textContent = "Synchronisation en attente";
    return;
  }

  const minutesAgo = Math.max(
    0,
    Math.floor((Date.now() - state.lastSyncAt.getTime()) / 60000),
  );
  syncEl.textContent =
    minutesAgo === 0
      ? "Synchronisé à l’instant"
      : `Synchronisé il y a ${minutesAgo} min`;
}

// ============================================
// SIGNALEMENT (REPORTING)
// ============================================
async function reportAvailability(fuelType, status, comment = "") {
  if (!state.selectedStation) return;
  if (!requireAuth("envoyer un commentaire/réaction")) return;

  // Disable buttons
  elements.btnAvailable.disabled = true;
  elements.btnEmpty.disabled = true;

  try {
    const response = await fetch(`${CONFIG.API_BASE_URL}/signalements/`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...getAuthHeaders(),
      },
      body: JSON.stringify({
        station: state.selectedStation.id,
        fuel_type: fuelType,
        status: status,
        comment,
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
        throw new Error("Connexion requise pour envoyer un signalement");
      }

      throw new Error(errorPayload.error || "Erreur lors du signalement");
    }

    const data = await response.json();

    // Show success
    showToast("Signalement enregistré ! Merci 🙏", "success");

    await refreshStations({ keepSelection: true, showToastOnError: false });
  } catch (error) {
    console.error("Error reporting:", error);
    showToast(error.message, "error");
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
      await refreshStations({ keepSelection: true, showToastOnError: false });
    } catch (error) {
      console.error("Error refreshing stations:", error);
    }
  }, CONFIG.REFRESH_INTERVAL);
}

async function updatePulse() {
  try {
    const response = await fetch(
      `${CONFIG.API_BASE_URL}/signalements/latest/?limit=5`,
    );
    if (!response.ok) return;

    const signalements = await response.json();
    if (signalements.length === 0) return;

    // Show pulse banner
    elements.livePulse.style.display = "flex";

    // Rotate through signalements
    let index = 0;
    const rotatePulse = () => {
      const s = signalements[index % signalements.length];
      const status = s.status === "Disponible" ? "✅" : "❌";
      const fuel = s.fuel_type || "Carburant";
      elements.pulseText.textContent = `${status} ${s.station_name}: ${fuel} ${s.status.toLowerCase()} (${s.time_ago})`;
      index++;
    };

    rotatePulse();
  } catch (error) {
    console.error("Error updating pulse:", error);
  }
}

// ============================================
// EVENT LISTENERS
// ============================================
function setupEventListeners() {
  elements.btnAvailable.addEventListener("click", () => {
    showFuelTypeSelector("Disponible");
  });

  elements.btnEmpty.addEventListener("click", () => {
    showFuelTypeSelector("Épuisé");
  });

  elements.navButtons.forEach((btn) => {
    btn.addEventListener("click", () => {
      const view = btn.dataset.view;
      switchView(view);

      elements.navButtons.forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
    });
  });

  document
    .querySelector(".sheet-handle")
    ?.addEventListener("click", closeStationSheet);
  document
    .querySelector("#sheet-close-btn")
    ?.addEventListener("click", closeStationSheet);
  state.map.on("click", closeStationSheet);
  elements.installBtn.addEventListener("click", installPWA);

  document.addEventListener("click", async (event) => {
    const target = event.target;

    if (target?.id === "refresh-nearby-btn") {
      await refreshStations({ keepSelection: true, showToastOnError: true });
      return;
    }

    if (target?.id === "apply-filters-btn") {
      const queryInput = document.getElementById("search-input");
      const fuelSelect = document.getElementById("filter-fuel-select");
      const radiusSelect = document.getElementById("filter-radius-select");
      const freshnessSelect = document.getElementById(
        "filter-freshness-select",
      );
      const sortSelect = document.getElementById("filter-sort-select");

      state.searchFilters.query = String(queryInput?.value || "").trim();
      state.searchFilters.availableFuel = String(fuelSelect?.value || "all");
      state.searchFilters.radius = Number(radiusSelect?.value || 10);
      state.searchFilters.freshnessMinutes = Number(
        freshnessSelect?.value || 240,
      );
      state.searchFilters.sortBy = String(sortSelect?.value || "distance");

      await refreshStations({ keepSelection: true, showToastOnError: true });
      return;
    }

    if (target?.id === "electricity-apply-btn") {
      const statusSelect = document.getElementById("electricity-status-select");
      const radiusSelect = document.getElementById("electricity-radius-select");
      const freshnessSelect = document.getElementById(
        "electricity-freshness-select",
      );
      const sortSelect = document.getElementById("electricity-sort-select");

      state.electricityFilters.status = String(statusSelect?.value || "all");
      state.electricityFilters.radius = Number(radiusSelect?.value || 10);
      state.electricityFilters.freshnessMinutes = Number(
        freshnessSelect?.value || 240,
      );
      state.electricityFilters.sortBy = String(sortSelect?.value || "distance");

      await refreshElectricityView(true);
      return;
    }

    if (target?.id === "electricity-refresh-btn") {
      await refreshElectricityView(true);
      return;
    }
  });
}

// ============================================
// FUEL TYPE SELECTOR
// ============================================
function showFuelTypeSelector(status) {
  if (!requireAuth("envoyer un commentaire/réaction")) {
    return;
  }

  // Create modal if not exists
  let modal = document.getElementById("fuel-type-modal");
  if (!modal) {
    modal = document.createElement("div");
    modal.id = "fuel-type-modal";
    modal.className = "modal-overlay";
    document.body.appendChild(modal);
  }

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
                <button class="fuel-type-btn" data-fuel="all">
                    ⛽ + 🚛 Les deux
                </button>
                <button class="fuel-type-btn" data-fuel="ElectriciteZone">
                    ⚡ Électricité (zone)
                </button>
            </div>
            <textarea id="signalement-comment" class="form-input" rows="3" maxlength="255" placeholder="Commentaire (optionnel)"></textarea>
            <button class="modal-close" type="button">Annuler</button>
        </div>
    `;

  // Add event listeners
  modal.querySelectorAll(".fuel-type-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      const fuelType = btn.dataset.fuel;
      const comment = String(
        modal.querySelector("#signalement-comment")?.value || "",
      ).trim();
      modal.style.display = "none";
      submitSignalement(fuelType, status, comment);
    });
  });

  modal.querySelector(".modal-close").addEventListener("click", () => {
    modal.style.display = "none";
  });

  modal.style.display = "flex";
}

async function reportElectricityByZone(status, comment = "") {
  if (!state.selectedStation) return;
  if (!requireAuth("signaler l'électricité")) return;

  try {
    const lookupUrl = new URL(
      `${CONFIG.API_BASE_URL}/electricity/by-location/`,
    );
    lookupUrl.searchParams.append("lat", state.selectedStation.latitude);
    lookupUrl.searchParams.append("lon", state.selectedStation.longitude);
    const lookupResponse = await fetch(lookupUrl);
    if (!lookupResponse.ok) {
      throw new Error("Impossible de trouver la zone électrique");
    }

    const lookupData = await lookupResponse.json();
    const zoneId = lookupData?.zone?.id;
    if (!zoneId) {
      throw new Error("Votre position est hors zone électrique couverte");
    }

    const response = await fetch(
      `${CONFIG.API_BASE_URL}/electricite-signalements/`,
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...getAuthHeaders(),
        },
        body: JSON.stringify({
          zone: zoneId,
          status,
          comment,
        }),
      },
    );

    const payload = await response.json();
    if (!response.ok) {
      throw new Error(payload.error || "Erreur signalement électricité");
    }

    showToast("Signalement électricité enregistré", "success");
    state.electricityByStation = {};
    await updateAdditionalSituations(state.selectedStation);
  } catch (error) {
    console.error("Error reporting electricity:", error);
    showToast(error.message, "error");
  }
}

async function submitSignalement(fuelType, status, comment = "") {
  if (fuelType === "all") {
    await reportAvailability("Essence", status, comment);
    await reportAvailability("Gazole", status, comment);
    return;
  }

  if (fuelType === "ElectriciteZone") {
    await reportElectricityByZone(status, comment);
    return;
  }

  await reportAvailability(fuelType, status, comment);
}

function switchView(view) {
  state.currentView = view;

  // Hide all view containers by removing active class
  document
    .querySelectorAll(".view-container")
    .forEach((el) => el.classList.remove("active"));

  // Cleanup add-station map when leaving that view
  if (state.addStationMap) {
    state.addStationMap.remove();
    state.addStationMap = null;
    state.addStationMarker = null;
  }

  const isDesktop = window.innerWidth >= 768;

  switch (view) {
    case "map":
      // On desktop, map is always visible behind overlays
      if (!isDesktop) {
        document.getElementById("map").style.display = "block";
      }
      closeStationSheet();
      setTimeout(() => {
        if (state.map) {
          state.map.invalidateSize();
        }
      }, 0);
      break;
    case "list":
      if (!isDesktop) {
        document.getElementById("map").style.display = "none";
      }
      showListView();
      break;
    case "alerts":
      if (!isDesktop) {
        document.getElementById("map").style.display = "none";
      }
      showAlertsView();
      break;
    case "electricity":
      if (!isDesktop) {
        document.getElementById("map").style.display = "none";
      }
      showElectricityView();
      break;
    case "add-station":
      if (!isDesktop) {
        document.getElementById("map").style.display = "none";
      }
      showAddStationView();
      break;
    case "admin":
      if (!isDesktop) {
        document.getElementById("map").style.display = "none";
      }
      showAdminView();
      break;
  }
}

function showListView() {
  let listView = document.getElementById("list-view");
  if (!listView) {
    listView = document.createElement("div");
    listView.id = "list-view";
    listView.className = "view-container";
    listView.innerHTML = `
            <div class="view-header">
                <h2>Stations autour de moi</h2>
                <p id="sync-info" class="view-subtitle">Synchronisation en attente</p>
                <input type="text" id="search-input" placeholder="Rechercher station ou enseigne..." class="search-input">
                <div class="filters-grid">
                    <select id="filter-fuel-select" class="search-input">
                        <option value="all">Tous carburants</option>
                        <option value="Essence">Essence signalée (dispo/épuisé)</option>
                        <option value="Gazole">Gazole signalé (dispo/épuisé)</option>
                    </select>
                    <select id="filter-radius-select" class="search-input">
                        <option value="2">Rayon 2 km</option>
                        <option value="5">Rayon 5 km</option>
                        <option value="10" selected>Rayon 10 km</option>
                        <option value="20">Rayon 20 km</option>
                    </select>
                    <select id="filter-freshness-select" class="search-input">
                        <option value="30">Mis à jour < 30 min</option>
                        <option value="60">Mis à jour < 1h</option>
                        <option value="240" selected>Mis à jour < 4h</option>
                    </select>
                    <select id="filter-sort-select" class="search-input">
                        <option value="distance" selected>Trier: distance</option>
                        <option value="recent">Trier: fraîcheur</option>
                        <option value="name">Trier: nom</option>
                    </select>
                </div>
                <div class="filters-actions">
                    <button id="apply-filters-btn" class="form-submit-btn" type="button">Appliquer filtres</button>
                    <button id="refresh-nearby-btn" class="modal-close" type="button">Rafraîchir autour de moi</button>
                </div>
            </div>
            <div class="station-list" id="station-list-container"></div>
        `;
    document.body.appendChild(listView);

    const queryInput = listView.querySelector("#search-input");
    if (queryInput) {
      queryInput.addEventListener("input", (e) => {
        state.searchFilters.query = String(e.target.value || "").trim();
        renderStations();
      });
    }
  }

  const fuelSelect = listView.querySelector("#filter-fuel-select");
  const radiusSelect = listView.querySelector("#filter-radius-select");
  const freshnessSelect = listView.querySelector("#filter-freshness-select");
  const sortSelect = listView.querySelector("#filter-sort-select");

  if (fuelSelect) fuelSelect.value = state.searchFilters.availableFuel;
  if (radiusSelect) radiusSelect.value = String(state.searchFilters.radius);
  if (freshnessSelect)
    freshnessSelect.value = String(state.searchFilters.freshnessMinutes);
  if (sortSelect) sortSelect.value = state.searchFilters.sortBy;

  renderStationList(applyClientSearchFilter(state.stations));
  updateSyncIndicator();
  listView.classList.add("active");
}

function renderStationList(filteredStations = null) {
  const container = document.getElementById("station-list-container");
  if (!container) return;

  const stationsToRender = filteredStations || state.stations;

  if (stationsToRender.length === 0) {
    container.innerHTML =
      '<div class="empty-state">Aucune station correspondant aux filtres</div>';
    return;
  }

  container.innerHTML = stationsToRender
    .map((station) => {
      const essence = station.essence_signalement;
      const gazole = station.gazole_signalement;

      return `
            <div class="station-list-item" onclick="selectStationById(${station.id})">
                <div class="station-list-header">
                    <span class="station-list-name">${station.name}</span>
                    <span class="station-list-status ${getStationStatus(station)}"></span>
                </div>
                <div class="station-list-meta">
                    <span>${station.brand}</span>
                    ${station.distance ? `<span class="distance-badge">${station.distance} km</span>` : ""}
                    ${station.has_recent_signalement ? '<span class="fresh-badge">Récent</span>' : ""}
                </div>
                <div class="fuel-inline-statuses">
                    <span class="fuel-inline-badge ${getFuelClass(essence)}">Essence: ${getFuelBadgeText(essence)}</span>
                    <span class="fuel-inline-badge ${getFuelClass(gazole)}">Gazole: ${getFuelBadgeText(gazole)}</span>
                </div>
            </div>
        `;
    })
    .join("");
}

function showAlertsView() {
  // Create alerts view if not exists
  let alertsView = document.getElementById("alerts-view");
  if (!alertsView) {
    alertsView = document.createElement("div");
    alertsView.id = "alerts-view";
    alertsView.className = "view-container";
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
    .then((r) => r.json())
    .then((signalements) => {
      const container = document.getElementById("alerts-list-container");
      if (signalements.length === 0) {
        container.innerHTML =
          '<div class="empty-state">Aucun signalement récent</div>';
        return;
      }

      container.innerHTML = signalements
        .map(
          (s) => `
                <div class="alert-item ${s.status === "Épuisé" ? "empty" : ""}">
                    <div class="alert-header">
                        <span class="alert-station">${s.station_name}</span>
                        <span class="alert-time">${s.time_ago}</span>
                    </div>
                    <div class="alert-message">
                        <span class="alert-fuel">${s.fuel_type}</span>
                        <span class="alert-status ${s.status === "Disponible" ? "available" : "empty"}">${s.status}</span>
                        <span class="alert-approvals">${s.approval_count} confirmation(s)</span>
                    </div>
                </div>
            `,
        )
        .join("");
    })
    .catch((err) => {
      console.error("Error loading alerts:", err);
    });

  // Show alerts
  alertsView.classList.add("active");
}

function selectStationById(id) {
  const station = state.stations.find((s) => s.id === id);
  if (station) {
    switchView("map");
    selectStation(station);

    // Update nav
    elements.navButtons.forEach((b) => b.classList.remove("active"));
    elements.navButtons[0].classList.add("active");
  }
}

function getElectricityStatusClass(status) {
  if (status === "Disponible" || status === "Retour récent") return "available";
  if (status === "Instable") return "unstable";
  if (status === "Coupure" || status === "Épuisé") return "empty";
  return "unknown";
}

function getElectricityStatusLabel(item) {
  const signal = item.latest_signalement;
  if (!signal) return "Inconnu";
  const time = signal.time_ago ? ` • ${signal.time_ago}` : "";
  const load = signal.load_level ? ` • Charge ${signal.load_level}` : "";
  return `${signal.status}${time}${load}`;
}

function updateElectricitySyncInfo() {
  const el = document.getElementById("electricity-sync-info");
  if (!el) return;

  const cacheInfo = state.electricityLastSyncAt
    ? "Données en ligne"
    : localStorage.getItem("bko_electricity_cache")
      ? "Données cache"
      : "Synchronisation en attente";

  if (!state.electricityLastSyncAt) {
    el.textContent = cacheInfo;
    return;
  }

  const minutesAgo = Math.max(
    0,
    Math.floor((Date.now() - state.electricityLastSyncAt.getTime()) / 60000),
  );
  const freshness =
    minutesAgo === 0
      ? "Synchronisé à l’instant"
      : `Synchronisé il y a ${minutesAgo} min`;
  el.textContent = `${freshness} • ${cacheInfo}`;
}

async function loadElectricityNearby() {
  if (!state.userLocation) return;

  const url = new URL(`${CONFIG.API_BASE_URL}/electricity/nearby/`);
  url.searchParams.append("lat", state.userLocation.lat);
  url.searchParams.append("lon", state.userLocation.lng);
  url.searchParams.append("radius", String(state.electricityFilters.radius));
  url.searchParams.append(
    "freshness_minutes",
    String(state.electricityFilters.freshnessMinutes),
  );
  url.searchParams.append("sort_by", state.electricityFilters.sortBy);
  if (state.electricityFilters.status !== "all") {
    url.searchParams.append("status", state.electricityFilters.status);
  }

  const response = await fetch(url);
  if (!response.ok) {
    const cached = localStorage.getItem("bko_electricity_cache");
    if (cached) {
      state.electricityZones = JSON.parse(cached);
      return;
    }
    throw new Error("Erreur chargement zones électriques");
  }

  state.electricityZones = await response.json();
  localStorage.setItem(
    "bko_electricity_cache",
    JSON.stringify(state.electricityZones),
  );
  state.electricityLastSyncAt = new Date();
}

async function loadElectricityRecommendation() {
  if (!state.userLocation) return;

  const url = new URL(`${CONFIG.API_BASE_URL}/electricity/recommendation/`);
  url.searchParams.append("lat", state.userLocation.lat);
  url.searchParams.append("lon", state.userLocation.lng);
  url.searchParams.append("radius", String(state.electricityFilters.radius));

  const response = await fetch(url);
  if (!response.ok) {
    const cached = localStorage.getItem("bko_electricity_reco_cache");
    state.electricityRecommendation = cached ? JSON.parse(cached) : null;
    return;
  }

  const payload = await response.json();
  state.electricityRecommendation = payload.recommendation || null;
  localStorage.setItem(
    "bko_electricity_reco_cache",
    JSON.stringify(state.electricityRecommendation),
  );
}

function renderElectricityList() {
  const container = document.getElementById("electricity-list-container");
  if (!container) return;

  if (!state.electricityZones.length) {
    container.innerHTML =
      '<div class="empty-state">Aucune zone électrique trouvée</div>';
    return;
  }

  container.innerHTML = state.electricityZones
    .map((item) => {
      const zone = item.zone;
      const status = item.latest_signalement?.status || "Inconnu";
      const statusClass = getElectricityStatusClass(status);
      const reliability = item.reliability_score ?? zone.reliability_score ?? 0;

      return `
            <div class="station-list-item electricity-item" onclick="focusElectricityZone(${zone.id}, ${zone.latitude}, ${zone.longitude})">
                <div class="station-list-header">
                    <span class="station-list-name">${zone.name}</span>
                    <span class="station-list-status ${statusClass}"></span>
                </div>
                <div class="station-list-meta">
                    <span>${zone.zone_type}</span>
                    <span class="distance-badge">${item.distance_km} km</span>
                    <span class="fresh-badge">Fiabilité ${reliability}%</span>
                </div>
                <div class="fuel-inline-statuses">
                    <span class="fuel-inline-badge ${statusClass}">${getElectricityStatusLabel(item)}</span>
                </div>
            </div>
        `;
    })
    .join("");

  const recommendationBox = document.getElementById(
    "electricity-recommendation-box",
  );
  if (!recommendationBox) return;

  if (!state.electricityRecommendation) {
    recommendationBox.innerHTML =
      '<div class="empty-state">Aucune recommandation disponible</div>';
    return;
  }

  const rec = state.electricityRecommendation;
  recommendationBox.innerHTML = `
        <div class="alert-item">
            <div class="alert-header">
                <span class="alert-station">Meilleure zone: ${rec.zone.name}</span>
                <span class="alert-time">${rec.distance_km} km</span>
            </div>
            <div class="alert-message">
                <span class="alert-fuel">${rec.latest_signalement?.status || "Inconnu"}</span>
                <span class="alert-approvals">Score ${rec.score}</span>
            </div>
        </div>
    `;
}

async function refreshElectricityView(showErrorToast = false) {
  try {
    await loadElectricityNearby();
    await loadElectricityRecommendation();
    renderElectricityList();
    updateElectricitySyncInfo();
  } catch (error) {
    console.error("Error loading electricity view:", error);
    if (showErrorToast) {
      showToast("Erreur chargement section électricité", "error");
    }
  }
}

function showElectricityView() {
  let electricityView = document.getElementById("electricity-view");
  if (!electricityView) {
    electricityView = document.createElement("div");
    electricityView.id = "electricity-view";
    electricityView.className = "view-container";
    electricityView.innerHTML = `
            <div class="view-header">
                <h2>Électricité autour de moi</h2>
                <p id="electricity-sync-info" class="view-subtitle">Synchronisation en attente</p>
                <div class="filters-grid">
                    <select id="electricity-status-select" class="search-input">
                        <option value="all">Tous statuts</option>
                        <option value="Disponible">Disponible</option>
                        <option value="Retour récent">Retour récent</option>
                        <option value="Instable">Instable</option>
                        <option value="Coupure">Coupure</option>
                    </select>
                    <select id="electricity-radius-select" class="search-input">
                        <option value="2">Rayon 2 km</option>
                        <option value="5">Rayon 5 km</option>
                        <option value="10" selected>Rayon 10 km</option>
                        <option value="20">Rayon 20 km</option>
                    </select>
                    <select id="electricity-freshness-select" class="search-input">
                        <option value="30">Mis à jour < 30 min</option>
                        <option value="60">Mis à jour < 1h</option>
                        <option value="240" selected>Mis à jour < 4h</option>
                    </select>
                    <select id="electricity-sort-select" class="search-input">
                        <option value="distance" selected>Trier: distance</option>
                        <option value="reliability">Trier: fiabilité</option>
                        <option value="freshness">Trier: fraîcheur</option>
                    </select>
                </div>
                <div class="filters-actions">
                    <button id="electricity-apply-btn" class="form-submit-btn" type="button">Appliquer</button>
                    <button id="electricity-refresh-btn" class="modal-close" type="button">Rafraîchir</button>
                </div>
            </div>
            <div id="electricity-recommendation-box" class="alerts-list"></div>
            <div id="electricity-list-container" class="station-list"></div>
        `;
    document.body.appendChild(electricityView);
  }

  const statusSelect = electricityView.querySelector(
    "#electricity-status-select",
  );
  const radiusSelect = electricityView.querySelector(
    "#electricity-radius-select",
  );
  const freshnessSelect = electricityView.querySelector(
    "#electricity-freshness-select",
  );
  const sortSelect = electricityView.querySelector("#electricity-sort-select");

  if (statusSelect) statusSelect.value = state.electricityFilters.status;
  if (radiusSelect)
    radiusSelect.value = String(state.electricityFilters.radius);
  if (freshnessSelect)
    freshnessSelect.value = String(state.electricityFilters.freshnessMinutes);
  if (sortSelect) sortSelect.value = state.electricityFilters.sortBy;

  refreshElectricityView(false);
  electricityView.classList.add("active");
}

function focusElectricityZone(_id, lat, lon) {
  switchView("map");
  state.map.setView([lat, lon], 14);
  elements.navButtons.forEach((b) => b.classList.remove("active"));
  const mapBtn = Array.from(elements.navButtons).find(
    (b) => b.dataset.view === "map",
  );
  if (mapBtn) mapBtn.classList.add("active");
}

window.focusElectricityZone = focusElectricityZone;

function updateCoordinatesFromMap(lat, lng) {
  const latInput = document.getElementById("station-lat-input");
  const lonInput = document.getElementById("station-lon-input");
  if (latInput) latInput.value = lat.toFixed(6);
  if (lonInput) lonInput.value = lng.toFixed(6);
  state.addStation.isPrefilledFromGeolocation = false;
  state.addStation.locationStatus = "map";
  setAddStationLocationStatus(
    document.getElementById("add-station-form"),
    `Position sélectionnée sur la carte (${lat.toFixed(4)}, ${lng.toFixed(4)})`,
    "success",
  );
}

function showAddStationView() {
  let addView = document.getElementById("add-station-view");
  if (!addView) {
    addView = document.createElement("div");
    addView.id = "add-station-view";
    addView.className = "view-container";
    addView.innerHTML = `
            <div class="view-header">
                <h2>Ajouter une station</h2>
                <p class="view-subtitle">
                    Trouvez une station qui n'est pas sur la carte ? Ajoutez-la en quelques clics !
                </p>
            </div>
            <span class="station-form-note">Pas besoin de compte pour ajouter une station ✨</span>
            <form id="add-station-form" class="station-form">
                <div id="add-station-map"></div>
                <div class="station-map-hint">📍 Cliquez sur la carte pour placer la station</div>

                <div class="form-grid">
                    <div>
                        <label class="form-label" for="station-lat-input">Latitude</label>
                        <input id="station-lat-input" name="latitude" class="form-input" type="number" required step="any" min="-90" max="90" placeholder="12.6392">
                    </div>
                    <div>
                        <label class="form-label" for="station-lon-input">Longitude</label>
                        <input id="station-lon-input" name="longitude" class="form-input" type="number" required step="any" min="-180" max="180" placeholder="-8.0029">
                    </div>
                </div>

                <button id="fill-station-location-btn" class="form-submit-btn" type="button" style="background:#00FF41;color:#0A0E14;">📍 Remplir depuis ma position</button>
                <div id="station-location-status" style="margin-top: 6px; font-size: 12px;"></div>

                <label class="form-label" for="station-name-input">Nom de la station *</label>
                <input id="station-name-input" name="name" class="form-input" type="text" required maxlength="100" placeholder="Ex: Station ACI 2000">

                <label class="form-label" for="station-brand-input">Enseigne *</label>
                <input id="station-brand-input" name="brand" class="form-input" type="text" required maxlength="50" placeholder="Ex: Shell, Total, Oryx">

                <label class="form-label" for="station-address-input">Lieu / Adresse</label>
                <input id="station-address-input" name="address" class="form-input" type="text" maxlength="255" placeholder="Ex: Badalabougou, Bamako">

                <label class="form-label" for="station-manager-input">Nom du gérant</label>
                <input id="station-manager-input" name="manager_name" class="form-input" type="text" maxlength="100" placeholder="Ex: Moussa Traoré">

                <button id="add-station-submit" class="form-submit-btn" type="submit">Enregistrer la station</button>
            </form>
        `;
    document.body.appendChild(addView);
  }

  const form = addView.querySelector("#add-station-form");
  setupAddStationForm(form);
  addView.classList.add("active");

  // Initialize Leaflet mini-map for location picking
  setTimeout(() => {
    if (state.addStationMap) {
      state.addStationMap.remove();
      state.addStationMap = null;
      state.addStationMarker = null;
    }

    const mapContainer = document.getElementById("add-station-map");
    if (!mapContainer) return;

    const mapCenter = state.userLocation
      ? [state.userLocation.lat, state.userLocation.lng]
      : CONFIG.MAP_CENTER;
    const mapZoom = state.userLocation ? 15 : CONFIG.MAP_ZOOM;

    const map = L.map("add-station-map", {
      center: mapCenter,
      zoom: mapZoom,
      zoomControl: true,
      attributionControl: false,
    });

    L.tileLayer(
      "https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png",
      { maxZoom: 19 },
    ).addTo(map);

    // Handle map click to place/move marker
    map.on("click", function (e) {
      const { lat, lng } = e.latlng;

      if (state.addStationMarker) {
        state.addStationMarker.setLatLng([lat, lng]);
      } else {
        state.addStationMarker = L.marker([lat, lng], {
          draggable: true,
        }).addTo(map);

        state.addStationMarker.on("dragend", function () {
          const pos = state.addStationMarker.getLatLng();
          updateCoordinatesFromMap(pos.lat, pos.lng);
        });
      }

      updateCoordinatesFromMap(lat, lng);
    });

    state.addStationMap = map;

    // Fix map rendering after container is fully laid out
    setTimeout(() => {
      if (state.addStationMap) {
        state.addStationMap.invalidateSize();
      }
    }, 200);
  }, 100);
}

// ============================================
// ADMIN VIEW - Pending Station Approvals
// ============================================
function showAdminView() {
  if (!state.isStaff) {
    showToast("Accès réservé aux administrateurs", "error");
    return;
  }

  let adminView = document.getElementById("admin-view");
  if (!adminView) {
    adminView = document.createElement("div");
    adminView.id = "admin-view";
    adminView.className = "view-container";
    adminView.innerHTML = `
            <div class="view-header">
                <h2>⚙️ Administration</h2>
                <p class="view-subtitle">Stations en attente de validation</p>
            </div>
            <div id="admin-stations-list" class="admin-stations-list">
                <div class="empty-state">Chargement des stations en attente...</div>
            </div>
        `;
    document.body.appendChild(adminView);
  }

  adminView.classList.add("active");
  loadPendingStations();
}

async function loadPendingStations() {
  const container = document.getElementById("admin-stations-list");
  if (!container) return;

  container.innerHTML = '<div class="empty-state">Chargement...</div>';

  try {
    const response = await fetch(
      `${CONFIG.API_BASE_URL}/stations/?page_size=100`,
      {
        headers: {
          ...getAuthHeaders(),
        },
      },
    );

    if (!response.ok) {
      throw new Error("Erreur lors du chargement des stations");
    }

    const data = await response.json();
    // Handle paginated response: DRF returns {count, next, results}
    const allStations = Array.isArray(data) ? data : data.results || [];
    // Filter client-side: only show pending stations
    const pendingStations = allStations.filter((s) => s.is_pending === true);

    if (pendingStations.length === 0) {
      container.innerHTML =
        '<div class="empty-state">Aucune station en attente de validation 🎉</div>';
      return;
    }

    container.innerHTML = pendingStations
      .map(
        (station) => `
            <div class="admin-station-card" data-station-id="${station.id}">
                <div class="admin-station-header">
                    <span class="admin-station-name">${station.name || "Sans nom"}</span>
                    <span class="admin-station-brand brand-badge">${station.brand || ""}</span>
                </div>
                <div class="admin-station-details">
                    <div class="detail-row">
                        <span class="detail-label">Adresse</span>
                        <span class="detail-value">${station.address || "—"}</span>
                    </div>
                    <div class="detail-row">
                        <span class="detail-label">Coordonnées</span>
                        <span class="detail-value">
                            <a href="#" class="admin-coord-link" onclick="focusAdminStationOnMap(event, ${station.latitude}, ${station.longitude})">${Number(station.latitude).toFixed(5)}, ${Number(station.longitude).toFixed(5)}</a>
                        </span>
                    </div>
                    <div class="detail-row">
                        <span class="detail-label">Soumise le</span>
                        <span class="detail-value">${station.created_at ? new Date(station.created_at).toLocaleDateString("fr-FR", { day: "2-digit", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit" }) : "—"}</span>
                    </div>
                    ${station.manager_name ? `<div class="detail-row"><span class="detail-label">Gérant</span><span class="detail-value">${station.manager_name}</span></div>` : ""}
                    ${station.submitted_by ? `<div class="detail-row"><span class="detail-label">Soumise par</span><span class="detail-value">${station.submitted_by}</span></div>` : ""}
                </div>
                <div class="admin-station-actions">
                    <button class="admin-action-btn admin-approve-btn" onclick="approveStation(${station.id})">
                        ✅ Approuver
                    </button>
                    <button class="admin-action-btn admin-reject-btn" onclick="toggleRejectForm(${station.id})">
                        ❌ Rejeter
                    </button>
                </div>
                <div class="admin-reject-form" id="reject-form-${station.id}" style="display:none;">
                    <input type="text" class="form-input admin-reject-input" id="reject-reason-${station.id}" placeholder="Raison du rejet (optionnel)" />
                    <button class="admin-action-btn admin-reject-confirm-btn" onclick="rejectStation(${station.id})">Confirmer le rejet</button>
                </div>
            </div>
        `,
      )
      .join("");
  } catch (error) {
    console.error("Error loading pending stations:", error);
    container.innerHTML =
      '<div class="empty-state">Erreur lors du chargement</div>';
    showToast("Erreur lors du chargement des stations", "error");
  }
}

function toggleRejectForm(stationId) {
  const form = document.getElementById(`reject-form-${stationId}`);
  if (form) {
    form.style.display = form.style.display === "none" ? "flex" : "none";
  }
}

async function approveStation(stationId) {
  const card = document.querySelector(
    `.admin-station-card[data-station-id="${stationId}"]`,
  );
  try {
    const response = await fetch(
      `${CONFIG.API_BASE_URL}/stations/${stationId}/approve/`,
      {
        method: "POST",
        headers: {
          ...getAuthHeaders(),
          "Content-Type": "application/json",
        },
      },
    );

    if (!response.ok) {
      const data = await response.json().catch(() => ({}));
      throw new Error(data.detail || "Erreur lors de l'approbation");
    }

    showToast("Station approuvée avec succès ✅", "success");

    // Remove the card with animation
    if (card) {
      card.style.transition = "opacity 0.3s, transform 0.3s";
      card.style.opacity = "0";
      card.style.transform = "translateX(50px)";
      setTimeout(() => {
        card.remove();
        // Check if list is empty
        const remaining = document.querySelectorAll(".admin-station-card");
        if (remaining.length === 0) {
          const container = document.getElementById("admin-stations-list");
          if (container) {
            container.innerHTML =
              '<div class="empty-state">Aucune station en attente de validation 🎉</div>';
          }
        }
      }, 300);
    }

    // Refresh map stations in background
    refreshStations({ keepSelection: true, showToastOnError: false });
  } catch (error) {
    console.error("Error approving station:", error);
    showToast(error.message || "Erreur lors de l'approbation", "error");
  }
}

async function rejectStation(stationId) {
  const reasonInput = document.getElementById(`reject-reason-${stationId}`);
  const reason = reasonInput ? reasonInput.value.trim() : "";
  const card = document.querySelector(
    `.admin-station-card[data-station-id="${stationId}"]`,
  );

  try {
    const response = await fetch(
      `${CONFIG.API_BASE_URL}/stations/${stationId}/reject/`,
      {
        method: "POST",
        headers: {
          ...getAuthHeaders(),
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ reason }),
      },
    );

    if (!response.ok) {
      const data = await response.json().catch(() => ({}));
      throw new Error(data.detail || "Erreur lors du rejet");
    }

    showToast("Station rejetée ❌", "success");

    // Remove the card with animation
    if (card) {
      card.style.transition = "opacity 0.3s, transform 0.3s";
      card.style.opacity = "0";
      card.style.transform = "translateX(-50px)";
      setTimeout(() => {
        card.remove();
        // Check if list is empty
        const remaining = document.querySelectorAll(".admin-station-card");
        if (remaining.length === 0) {
          const container = document.getElementById("admin-stations-list");
          if (container) {
            container.innerHTML =
              '<div class="empty-state">Aucune station en attente de validation 🎉</div>';
          }
        }
      }, 300);
    }
  } catch (error) {
    console.error("Error rejecting station:", error);
    showToast(error.message || "Erreur lors du rejet", "error");
  }
}

function focusAdminStationOnMap(event, lat, lng) {
  event.preventDefault();
  // Switch to map view and center on station
  switchView("map");
  elements.navButtons.forEach((b) => b.classList.remove("active"));
  elements.navButtons[0].classList.add("active");
  if (state.map) {
    state.map.setView([lat, lng], 16);
  }
}

// Expose admin functions globally for onclick handlers
window.approveStation = approveStation;
window.rejectStation = rejectStation;
window.toggleRejectForm = toggleRejectForm;
window.focusAdminStationOnMap = focusAdminStationOnMap;

function parseCoordinate(value) {
  const parsed = Number.parseFloat(value);
  return Number.isFinite(parsed) ? parsed : null;
}

function setAddStationLocationStatus(form, message, type = "info") {
  if (!form) return;
  const statusEl = form.querySelector("#station-location-status");
  if (!statusEl) return;

  statusEl.textContent = message || "";
  statusEl.style.display = message ? "block" : "none";

  if (type === "success") {
    statusEl.style.color = "var(--accent-green)";
  } else if (type === "error") {
    statusEl.style.color = "var(--accent-red)";
  } else if (type === "warning") {
    statusEl.style.color = "var(--accent-yellow)";
  } else {
    statusEl.style.color = "var(--text-secondary)";
  }
}

function setupAddStationForm(form) {
  if (!form) return;

  form.onsubmit = handleAddStationSubmit;

  const fillLocationBtn = form.querySelector("#fill-station-location-btn");
  if (fillLocationBtn) {
    fillLocationBtn.onclick = (event) => {
      event.preventDefault();
      fillStationLocationFromCurrentPosition(form);
    };
  }

  const latitudeInput = form.querySelector("#station-lat-input");
  const longitudeInput = form.querySelector("#station-lon-input");

  const onManualLocationInput = () => {
    state.addStation.isPrefilledFromGeolocation = false;
    state.addStation.locationStatus = "manual";
    setAddStationLocationStatus(
      form,
      "Coordonnées saisies manuellement.",
      "warning",
    );
  };

  if (latitudeInput) {
    latitudeInput.oninput = onManualLocationInput;
  }
  if (longitudeInput) {
    longitudeInput.oninput = onManualLocationInput;
  }

  const initialMessage = state.userLocation
    ? 'Position détectée. Utilisez "Remplir depuis ma position" pour préremplir les coordonnées.'
    : "Complétez la position manuellement ou utilisez votre position actuelle.";
  setAddStationLocationStatus(
    form,
    initialMessage,
    state.userLocation ? "info" : "warning",
  );
}

async function fillStationLocationFromCurrentPosition(form) {
  if (!form) return false;

  const fillLocationBtn = form.querySelector("#fill-station-location-btn");
  const latitudeInput = form.querySelector("#station-lat-input");
  const longitudeInput = form.querySelector("#station-lon-input");

  if (!latitudeInput || !longitudeInput) {
    return false;
  }

  if (state.addStation.locationFillInProgress) {
    return false;
  }

  state.addStation.locationFillInProgress = true;
  if (fillLocationBtn) {
    fillLocationBtn.disabled = true;
    fillLocationBtn.textContent = "Détection en cours...";
  }
  setAddStationLocationStatus(form, "Recherche de votre position...", "info");

  try {
    if (!state.userLocation) {
      const hasLocation = await getUserLocation();
      if (!hasLocation || !state.userLocation) {
        throw new Error(
          "Impossible d’accéder à votre position pour l’instant.",
        );
      }
    }

    const lat = Number.parseFloat(state.userLocation.lat);
    const lng = Number.parseFloat(state.userLocation.lng);

    const latRounded = Number.parseFloat(lat.toFixed(6));
    const lngRounded = Number.parseFloat(lng.toFixed(6));

    latitudeInput.value = latRounded;
    longitudeInput.value = lngRounded;

    state.addStation.isPrefilledFromGeolocation = true;
    state.addStation.lastKnownLatitude = latRounded;
    state.addStation.lastKnownLongitude = lngRounded;
    state.addStation.locationStatus = "gps";

    // Update marker on mini-map if visible
    if (state.addStationMap) {
      if (state.addStationMarker) {
        state.addStationMarker.setLatLng([latRounded, lngRounded]);
      } else {
        state.addStationMarker = L.marker([latRounded, lngRounded], {
          draggable: true,
        }).addTo(state.addStationMap);
        state.addStationMarker.on("dragend", function () {
          const pos = state.addStationMarker.getLatLng();
          updateCoordinatesFromMap(pos.lat, pos.lng);
        });
      }
      state.addStationMap.setView([latRounded, lngRounded], 15);
    }

    setAddStationLocationStatus(
      form,
      `Position préremplie depuis votre GPS (${latRounded}, ${lngRounded}).`,
      "success",
    );

    return true;
  } catch (error) {
    setAddStationLocationStatus(
      form,
      error.message || "Impossible de récupérer votre position.",
      "error",
    );
    return false;
  } finally {
    state.addStation.locationFillInProgress = false;
    if (fillLocationBtn) {
      fillLocationBtn.disabled = false;
      fillLocationBtn.textContent = "Remplir depuis ma position";
    }
  }
}

async function handleAddStationSubmit(event) {
  event.preventDefault();

  const form = event.target;
  const submitButton = form.querySelector("#add-station-submit");
  const formData = new FormData(form);

  const latitude = parseCoordinate(formData.get("latitude"));
  const longitude = parseCoordinate(formData.get("longitude"));

  if (latitude === null || latitude < -90 || latitude > 90) {
    showToast("Latitude invalide (-90 à 90)", "error");
    return;
  }

  if (longitude === null || longitude < -180 || longitude > 180) {
    showToast("Longitude invalide (-180 à 180)", "error");
    return;
  }

  const payload = {
    name: String(formData.get("name") || "").trim(),
    brand: String(formData.get("brand") || "").trim(),
    address: String(formData.get("address") || "").trim(),
    latitude,
    longitude,
    manager_name: String(formData.get("manager_name") || "").trim(),
    is_active: true,
  };

  if (!payload.name || !payload.brand) {
    showToast("Nom et enseigne sont obligatoires", "error");
    return;
  }

  // Submission is now allowed for anonymous users (public create). Keep auth optional when available.

  submitButton.disabled = true;

  try {
    const response = await fetch(`${CONFIG.API_BASE_URL}/stations/`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...getAuthHeaders(),
      },
      body: JSON.stringify(payload),
    });

    const responseData = await response.json();

    if (!response.ok) {
      const errorMessage =
        responseData.error || "Erreur lors de la création de la station";
      throw new Error(errorMessage);
    }

    const sourceLabel = state.addStation.isPrefilledFromGeolocation
      ? " (position détectée)"
      : "";
    showToast(
      `Station soumise ! Elle sera visible après validation par un admin 📋`,
      "success",
    );

    form.reset();
    state.addStation.isPrefilledFromGeolocation = false;
    setAddStationLocationStatus(
      form,
      "Prête pour une nouvelle station.",
      "info",
    );

    // Show temporary success banner inside form
    const successBanner = document.createElement("div");
    successBanner.className = "add-station-success-banner";
    successBanner.textContent =
      "Votre proposition de station a bien été envoyée. Un administrateur la vérifiera bientôt.";
    form.prepend(successBanner);
    setTimeout(() => {
      if (successBanner.parentNode) {
        successBanner.remove();
      }
    }, 5000);

    await refreshStations({ keepSelection: false, showToastOnError: true });

    switchView("map");
    elements.navButtons.forEach((b) => b.classList.remove("active"));
    elements.navButtons[0].classList.add("active");
  } catch (error) {
    console.error("Error creating station:", error);
    showToast(error.message, "error");
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
  window.addEventListener("beforeinstallprompt", (e) => {
    e.preventDefault();
    deferredPrompt = e;
    elements.installPrompt.style.display = "flex";
  });

  // Hide prompt when installed
  window.addEventListener("appinstalled", () => {
    elements.installPrompt.style.display = "none";
    deferredPrompt = null;
  });

  // Register service worker
  if ("serviceWorker" in navigator) {
    navigator.serviceWorker
      .register("service-worker.js")
      .then((reg) => console.log("Service Worker registered"))
      .catch((err) => console.log("Service Worker registration failed"));
  }
}

async function installPWA() {
  if (!deferredPrompt) return;

  deferredPrompt.prompt();
  const { outcome } = await deferredPrompt.userChoice;

  if (outcome === "accepted") {
    elements.installPrompt.style.display = "none";
  }

  deferredPrompt = null;
}

// ============================================
// UTILITIES
// ============================================
function showToast(message, type = "success") {
  // Remove existing toasts
  document.querySelectorAll(".toast").forEach((t) => t.remove());

  // Create toast
  const toast = document.createElement("div");
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
