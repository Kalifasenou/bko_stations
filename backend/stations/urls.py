from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    StationViewSet, SignalementViewSet, statistics, search_stations,
    stations_by_status, statistics_by_brand, fuel_availability_map,
    signalements_heatmap, health_check, monitoring_overview,
    brands_list, stations_nearby, register_user
)

router = DefaultRouter()
router.register(r'stations', StationViewSet, basename='station')
router.register(r'signalements', SignalementViewSet, basename='signalement')

urlpatterns = [
    # Auth endpoint
    path('auth/register/', register_user, name='register-user'),
    # Health check endpoint
    path('health/', health_check, name='health-check'),
    # Statistics endpoints
    path('statistics/', statistics, name='statistics'),
    path('statistics/by-brand/', statistics_by_brand, name='statistics-by-brand'),
    # Search endpoints
    path('search/', search_stations, name='search-stations'),
    # Station endpoints
    path('stations/brands/', brands_list, name='brands-list'),
    path('stations/nearby/', stations_nearby, name='stations-nearby'),
    path('stations/by-status/', stations_by_status, name='stations-by-status'),
    # Map endpoints
    path('fuel-availability-map/', fuel_availability_map, name='fuel-availability-map'),
    path('signalements/heatmap/', signalements_heatmap, name='signalements-heatmap'),
    path('monitoring/', monitoring_overview, name='monitoring-overview'),
    path('', include(router.urls)),
]
