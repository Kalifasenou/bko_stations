#!/usr/bin/env python
"""Script de seed: stations + situations carburant + admin"""
import os
import sys
import django
from django.utils import timezone
from django.contrib.auth import get_user_model

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from stations.models import Station, Signalement

stations = [
    {
        'name': 'Station Shell ACI 2000',
        'brand': 'Shell',
        'latitude': 12.6390,
        'longitude': -8.0025,
        'situations': {'Essence': 'Disponible', 'Gazole': 'Épuisé', 'Électricité': 'Disponible'}
    },
    {
        'name': 'Station Total Pont',
        'brand': 'TotalEnergies',
        'latitude': 12.6420,
        'longitude': -7.9990,
        'situations': {'Essence': 'Épuisé', 'Gazole': 'Disponible', 'Électricité': 'Épuisé'}
    },
    {
        'name': 'Station Oryx Bamako',
        'brand': 'Oryx',
        'latitude': 12.6350,
        'longitude': -8.0100,
        'situations': {'Essence': 'Disponible', 'Gazole': 'Disponible', 'Électricité': 'Disponible'}
    },
    {
        'name': 'Station Shell Badalabougou',
        'brand': 'Shell',
        'latitude': 12.6500,
        'longitude': -7.9850,
        'situations': {'Essence': 'Épuisé', 'Gazole': 'Épuisé', 'Électricité': 'Disponible'}
    },
    {
        'name': 'Station Total Hippodrome',
        'brand': 'TotalEnergies',
        'latitude': 12.6450,
        'longitude': -8.0150,
        'situations': {'Essence': 'Disponible', 'Gazole': 'Épuisé', 'Électricité': 'Épuisé'}
    },
    {
        'name': 'Station ExxonMobil Djélibougou',
        'brand': 'ExxonMobil',
        'latitude': 12.6300,
        'longitude': -8.0200,
        'situations': {'Essence': 'Épuisé', 'Gazole': 'Disponible', 'Électricité': 'Disponible'}
    },
    {
        'name': 'Station Oryx Sabalibougou',
        'brand': 'Oryx',
        'latitude': 12.6550,
        'longitude': -7.9750,
        'situations': {'Essence': 'Disponible', 'Gazole': 'Disponible', 'Électricité': 'Épuisé'}
    },
    {
        'name': 'Station Shell Sotrama',
        'brand': 'Shell',
        'latitude': 12.6380,
        'longitude': -8.0080,
        'situations': {'Essence': 'Épuisé', 'Gazole': 'Épuisé', 'Électricité': 'Épuisé'}
    },
    {
        'name': 'Station Total Faladié',
        'brand': 'TotalEnergies',
        'latitude': 12.5985,
        'longitude': -7.9458,
        'situations': {'Essence': 'Disponible', 'Gazole': 'Disponible', 'Électricité': 'Disponible'}
    },
    {
        'name': 'Station Shell Yirimadio',
        'brand': 'Shell',
        'latitude': 12.6067,
        'longitude': -7.9215,
        'situations': {'Essence': 'Épuisé', 'Gazole': 'Disponible', 'Électricité': 'Épuisé'}
    },
    {
        'name': 'Station Oryx Kalaban Coura',
        'brand': 'Oryx',
        'latitude': 12.5872,
        'longitude': -7.9674,
        'situations': {'Essence': 'Disponible', 'Gazole': 'Épuisé', 'Électricité': 'Disponible'}
    },
    {
        'name': 'Station Petro Baco Djicoroni',
        'brand': 'Petro Baco',
        'latitude': 12.6129,
        'longitude': -8.0324,
        'situations': {'Essence': 'Épuisé', 'Gazole': 'Épuisé', 'Électricité': 'Disponible'}
    },
    {
        'name': 'Station Total Niamakoro',
        'brand': 'TotalEnergies',
        'latitude': 12.5738,
        'longitude': -7.9511,
        'situations': {'Essence': 'Disponible', 'Gazole': 'Disponible', 'Électricité': 'Épuisé'}
    },
]

for data in stations:
    station_payload = {
        'name': data['name'],
        'brand': data['brand'],
        'latitude': data['latitude'],
        'longitude': data['longitude'],
    }
    station, _ = Station.objects.update_or_create(name=data['name'], defaults=station_payload)

    for fuel_type, fuel_status in data['situations'].items():
        Signalement.objects.update_or_create(
            station=station,
            fuel_type=fuel_type,
            defaults={
                'status': fuel_status,
                'timestamp': timezone.now(),
                'approval_count': 1,
                'comment': 'Initialisation seed',
            },
        )

User = get_user_model()
admin_user, created = User.objects.get_or_create(
    username='senou',
    defaults={'is_staff': True, 'is_superuser': True}
)
admin_user.is_staff = True
admin_user.is_superuser = True
admin_user.is_active = True
admin_user.set_password('Senou@2026')
admin_user.save()

print(f"Seed terminé: {Station.objects.count()} stations actives.")
print("Admin prêt: username=senou, password=Senou@2026")
