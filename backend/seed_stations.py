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

from stations.models import Station, Signalement, ZoneElectrique, ElectriciteSignalement

stations = [
    {
        'name': 'Station Shell ACI 2000',
        'brand': 'Shell',
        'latitude': 12.6390,
        'longitude': -8.0025,
        'situations': {'Essence': 'Disponible', 'Gazole': 'Épuisé'}
    },
    {
        'name': 'Station Total Pont',
        'brand': 'TotalEnergies',
        'latitude': 12.6420,
        'longitude': -7.9990,
        'situations': {'Essence': 'Épuisé', 'Gazole': 'Disponible'}
    },
    {
        'name': 'Station Oryx Bamako',
        'brand': 'Oryx',
        'latitude': 12.6350,
        'longitude': -8.0100,
        'situations': {'Essence': 'Disponible', 'Gazole': 'Disponible'}
    },
    {
        'name': 'Station Shell Badalabougou',
        'brand': 'Shell',
        'latitude': 12.6500,
        'longitude': -7.9850,
        'situations': {'Essence': 'Épuisé', 'Gazole': 'Épuisé'}
    },
    {
        'name': 'Station Total Hippodrome',
        'brand': 'TotalEnergies',
        'latitude': 12.6450,
        'longitude': -8.0150,
        'situations': {'Essence': 'Disponible', 'Gazole': 'Épuisé'}
    },
    {
        'name': 'Station ExxonMobil Djélibougou',
        'brand': 'ExxonMobil',
        'latitude': 12.6300,
        'longitude': -8.0200,
        'situations': {'Essence': 'Épuisé', 'Gazole': 'Disponible'}
    },
    {
        'name': 'Station Oryx Sabalibougou',
        'brand': 'Oryx',
        'latitude': 12.6550,
        'longitude': -7.9750,
        'situations': {'Essence': 'Disponible', 'Gazole': 'Disponible'}
    },
    {
        'name': 'Station Shell Sotrama',
        'brand': 'Shell',
        'latitude': 12.6380,
        'longitude': -8.0080,
        'situations': {'Essence': 'Épuisé', 'Gazole': 'Épuisé'}
    },
    {
        'name': 'Station Total Faladié',
        'brand': 'TotalEnergies',
        'latitude': 12.5985,
        'longitude': -7.9458,
        'situations': {'Essence': 'Disponible', 'Gazole': 'Disponible'}
    },
    {
        'name': 'Station Shell Yirimadio',
        'brand': 'Shell',
        'latitude': 12.6067,
        'longitude': -7.9215,
        'situations': {'Essence': 'Épuisé', 'Gazole': 'Disponible'}
    },
    {
        'name': 'Station Oryx Kalaban Coura',
        'brand': 'Oryx',
        'latitude': 12.5872,
        'longitude': -7.9674,
        'situations': {'Essence': 'Disponible', 'Gazole': 'Épuisé'}
    },
    {
        'name': 'Station Petro Baco Djicoroni',
        'brand': 'Petro Baco',
        'latitude': 12.6129,
        'longitude': -8.0324,
        'situations': {'Essence': 'Épuisé', 'Gazole': 'Épuisé'}
    },
    {
        'name': 'Station Total Niamakoro',
        'brand': 'TotalEnergies',
        'latitude': 12.5738,
        'longitude': -7.9511,
        'situations': {'Essence': 'Disponible', 'Gazole': 'Disponible'}
    },
]

zones_electriques = [
    {'name': 'ACI 2000', 'zone_type': 'Quartier', 'latitude': 12.6400, 'longitude': -8.0000, 'radius_km': 2.5, 'status': 'Disponible'},
    {'name': 'Badalabougou', 'zone_type': 'Quartier', 'latitude': 12.6480, 'longitude': -7.9860, 'radius_km': 2.0, 'status': 'Épuisé'},
    {'name': 'Kalaban Coura', 'zone_type': 'Quartier', 'latitude': 12.5870, 'longitude': -7.9670, 'radius_km': 2.0, 'status': 'Instable'},
    {'name': 'Faladié', 'zone_type': 'Secteur', 'latitude': 12.5990, 'longitude': -7.9460, 'radius_km': 2.0, 'status': 'Disponible'},
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

for zone_data in zones_electriques:
    zone, _ = ZoneElectrique.objects.update_or_create(
        name=zone_data['name'],
        defaults={
            'zone_type': zone_data['zone_type'],
            'latitude': zone_data['latitude'],
            'longitude': zone_data['longitude'],
            'radius_km': zone_data['radius_km'],
            'is_active': True,
        }
    )

    ElectriciteSignalement.objects.update_or_create(
        zone=zone,
        defaults={
            'status': zone_data['status'],
            'timestamp': timezone.now(),
            'approval_count': 1,
            'comment': 'Initialisation seed électricité',
        }
    )

User = get_user_model()
seed_admin_username = os.getenv('SEED_ADMIN_USERNAME')
seed_admin_password = os.getenv('SEED_ADMIN_PASSWORD')
seed_admin_email = os.getenv('SEED_ADMIN_EMAIL', 'admin@bko-stations.local')

if seed_admin_username and seed_admin_password:
    admin_user, _ = User.objects.get_or_create(
        username=seed_admin_username,
        defaults={'is_staff': True, 'is_superuser': True, 'email': seed_admin_email}
    )
    admin_user.is_staff = True
    admin_user.is_superuser = True
    admin_user.is_active = True
    admin_user.email = seed_admin_email
    admin_user.set_password(seed_admin_password)
    admin_user.save()
    print(f"Admin seed prêt: username={seed_admin_username}")
else:
    print("SEED_ADMIN_USERNAME / SEED_ADMIN_PASSWORD absents: aucun admin seed créé.")

print(f"Seed terminé: {Station.objects.count()} stations actives.")
