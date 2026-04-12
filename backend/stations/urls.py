from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    ElectriciteSignalementViewSet,
    SignalementViewSet,
    StationViewSet,
    ZoneElectriqueViewSet,
    admin_statistics,
    brands_list,
    electricity_by_location,
    electricity_nearby,
    electricity_recommendation,
    electricity_statistics,
    electricity_timeline,
    fuel_availability_map,
    health_check,
    login_user,
    monitoring_overview,
    register_user,
    search_stations,
    signalements_heatmap,
    station_timeline,
    stations_by_status,
    stations_nearby,
    statistics,
    statistics_by_brand,
    user_favorites,
)

router = DefaultRouter()
router.register(r"stations", StationViewSet, basename="station")
router.register(r"signalements", SignalementViewSet, basename="signalement")
router.register(r"zones-electriques", ZoneElectriqueViewSet, basename="zone-electrique")
router.register(
    r"electricite-signalements",
    ElectriciteSignalementViewSet,
    basename="electricite-signalement",
)

urlpatterns = [
    # Auth endpoints
    path("auth/register/", register_user, name="register-user"),
    path("auth/login/", login_user, name="login-user"),
    # Favorites endpoints
    path("favorites/", user_favorites, name="user-favorites"),
    path("favorites/<int:station_id>/", user_favorites, name="user-favorite-toggle"),
    # Health check endpoint
    path("health/", health_check, name="health-check"),
    # Statistics endpoints
    path("statistics/", statistics, name="statistics"),
    path("statistics/by-brand/", statistics_by_brand, name="statistics-by-brand"),
    path("admin/statistics/", admin_statistics, name="admin-statistics"),
    # Search endpoints
    path("search/", search_stations, name="search-stations"),
    # Station endpoints
    path("stations/brands/", brands_list, name="brands-list"),
    path("stations/nearby/", stations_nearby, name="stations-nearby"),
    path("stations/by-status/", stations_by_status, name="stations-by-status"),
    path("stations/<int:pk>/timeline/", station_timeline, name="station-timeline"),
    # Map endpoints
    path("fuel-availability-map/", fuel_availability_map, name="fuel-availability-map"),
    path(
        "electricity/by-location/",
        electricity_by_location,
        name="electricity-by-location",
    ),
    path("electricity/nearby/", electricity_nearby, name="electricity-nearby"),
    path(
        "electricity/recommendation/",
        electricity_recommendation,
        name="electricity-recommendation",
    ),
    path(
        "electricity/zones/<int:zone_id>/timeline/",
        electricity_timeline,
        name="electricity-timeline",
    ),
    path(
        "electricity/statistics/", electricity_statistics, name="electricity-statistics"
    ),
    path(
        "electricity/signalements/quick/",
        ElectriciteSignalementViewSet.as_view({"post": "create"}),
        name="electricity-signalement-quick",
    ),
    path("signalements/heatmap/", signalements_heatmap, name="signalements-heatmap"),
    path("monitoring/", monitoring_overview, name="monitoring-overview"),
    path("healthz/", health_check, name="healthz"),
    path("", include(router.urls)),
]
