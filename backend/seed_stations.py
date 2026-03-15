#!/usr/bin/env python
"""Script pour ajouter les stations de carburant de Bamako"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from stations.models import Station

stations = [
    {'name': 'Station Shell ACI 2000', 'brand': 'Shell', 'latitude': 12.6390, 'longitude': -8.0025},
    {'name': 'Station Total Pont', 'brand': 'TotalEnergies', 'latitude': 12.6420, 'longitude': -7.9990},
    {'name': 'Station Oryx Bamako', 'brand': 'Oryx', 'latitude': 12.6350, 'longitude': -8.0100},
    {'name': 'Station Shell Badalabougou', 'brand': 'Shell', 'latitude': 12.6500, 'longitude': -7.9850},
    {'name': 'Station Total Hippodrome', 'brand': 'TotalEnergies', 'latitude': 12.6450, 'longitude': -8.0150},
    {'name': 'Station ExxonMobil Djélibougou', 'brand': 'ExxonMobil', 'latitude': 12.6300, 'longitude': -8.0200},
    {'name': 'Station Oryx Sabalibougou', 'brand': 'Oryx', 'latitude': 12.6550, 'longitude': -7.9750},
    {'name': 'Station Shell Sotrama', 'brand': 'Shell', 'latitude': 12.6380, 'longitude': -8.0080},
]

for s in stations:
    Station.objects.get_or_create(name=s['name'], defaults=s)

print(f'{Station.objects.count()} stations created in Bamako!')