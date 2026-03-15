from django.test import TestCase, Client
from django.utils import timezone
from datetime import timedelta
from rest_framework.test import APITestCase, APIClient
from rest_framework import status

from .models import Station, Signalement


class StationModelTests(TestCase):
    """Tests pour le modèle Station"""
    
    def setUp(self):
        self.station = Station.objects.create(
            name="Station Test",
            brand="Shell",
            latitude=12.6452,
            longitude=-8.0029
        )
    
    def test_station_creation(self):
        """Test la création d'une station"""
        self.assertEqual(self.station.name, "Station Test")
        self.assertEqual(self.station.brand, "Shell")
    
    def test_station_str(self):
        """Test la représentation string d'une station"""
        expected = "Station Test (Shell)"
        self.assertEqual(str(self.station), expected)
    
    def test_get_latest_signalement(self):
        """Test la récupération du dernier signalement"""
        signalement = Signalement.objects.create(
            station=self.station,
            fuel_type='Essence',
            status='Disponible'
        )
        latest = self.station.get_latest_signalement()
        self.assertEqual(latest.id, signalement.id)
    
    def test_get_latest_signalement_expired(self):
        """Test que les signalements expirés ne sont pas retournés"""
        # Créer un signalement expiré
        old_time = timezone.now() - timedelta(hours=5)
        signalement = Signalement.objects.create(
            station=self.station,
            fuel_type='Essence',
            status='Disponible',
            timestamp=old_time
        )
        latest = self.station.get_latest_signalement()
        self.assertIsNone(latest)
    
    def test_status_color_green(self):
        """Test la couleur verte (carburant disponible)"""
        Signalement.objects.create(
            station=self.station,
            fuel_type='Essence',
            status='Disponible'
        )
        self.assertEqual(self.station.status_color, 'green')
    
    def test_status_color_red(self):
        """Test la couleur rouge (carburant épuisé)"""
        Signalement.objects.create(
            station=self.station,
            fuel_type='Essence',
            status='Épuisé'
        )
        self.assertEqual(self.station.status_color, 'red')
    
    def test_status_color_yellow(self):
        """Test la couleur jaune (carburant partiellement disponible)"""
        Signalement.objects.create(
            station=self.station,
            fuel_type='Essence',
            status='Disponible'
        )
        Signalement.objects.create(
            station=self.station,
            fuel_type='Gazole',
            status='Épuisé'
        )
        self.assertEqual(self.station.status_color, 'yellow')
    
    def test_status_color_gray(self):
        """Test la couleur grise (pas de signalement)"""
        self.assertEqual(self.station.status_color, 'gray')


class SignalementModelTests(TestCase):
    """Tests pour le modèle Signalement"""
    
    def setUp(self):
        self.station = Station.objects.create(
            name="Station Test",
            brand="Shell",
            latitude=12.6452,
            longitude=-8.0029
        )
    
    def test_signalement_creation(self):
        """Test la création d'un signalement"""
        signalement = Signalement.objects.create(
            station=self.station,
            fuel_type='Essence',
            status='Disponible'
        )
        self.assertEqual(signalement.approval_count, 1)
        self.assertFalse(signalement.is_expired())
    
    def test_signalement_expiration(self):
        """Test l'expiration d'un signalement"""
        old_time = timezone.now() - timedelta(hours=5)
        signalement = Signalement.objects.create(
            station=self.station,
            fuel_type='Essence',
            status='Disponible',
            timestamp=old_time
        )
        self.assertTrue(signalement.is_expired())
    
    def test_signalement_str(self):
        """Test la représentation string d'un signalement"""
        signalement = Signalement.objects.create(
            station=self.station,
            fuel_type='Essence',
            status='Disponible'
        )
        expected = "Station Test - Essence: Disponible (1 confirmations)"
        self.assertEqual(str(signalement), expected)


class StationAPITests(APITestCase):
    """Tests pour l'API des stations"""
    
    def setUp(self):
        self.client = APIClient()
        self.station1 = Station.objects.create(
            name="Station 1",
            brand="Shell",
            latitude=12.6452,
            longitude=-8.0029
        )
        self.station2 = Station.objects.create(
            name="Station 2",
            brand="Total",
            latitude=12.6500,
            longitude=-8.0100
        )
    
    def test_list_stations(self):
        """Test la liste des stations"""
        response = self.client.get('/api/stations/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
    
    def test_retrieve_station(self):
        """Test la récupération d'une station"""
        response = self.client.get(f'/api/stations/{self.station1.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], 'Station 1')
    
    def test_nearby_stations(self):
        """Test la récupération des stations proches"""
        response = self.client.get(
            f'/api/stations/{self.station1.id}/nearby/?radius=10'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
    
    def test_search_stations(self):
        """Test la recherche de stations"""
        response = self.client.get('/api/search/?q=Shell')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
    
    def test_search_stations_short_query(self):
        """Test que la recherche avec une requête trop courte échoue"""
        response = self.client.get('/api/search/?q=S')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class SignalementAPITests(APITestCase):
    """Tests pour l'API des signalements"""
    
    def setUp(self):
        self.client = APIClient()
        self.station = Station.objects.create(
            name="Station Test",
            brand="Shell",
            latitude=12.6452,
            longitude=-8.0029
        )
    
    def test_create_signalement(self):
        """Test la création d'un signalement"""
        data = {
            'station': self.station.id,
            'fuel_type': 'Essence',
            'status': 'Disponible'
        }
        response = self.client.post('/api/signalements/', data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
    
    def test_create_signalement_missing_station(self):
        """Test que la création échoue sans station"""
        data = {
            'fuel_type': 'Essence',
            'status': 'Disponible'
        }
        response = self.client.post('/api/signalements/', data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_latest_signalements(self):
        """Test la récupération des derniers signalements"""
        Signalement.objects.create(
            station=self.station,
            fuel_type='Essence',
            status='Disponible'
        )
        response = self.client.get('/api/signalements/latest/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
    
    def test_signalements_by_station(self):
        """Test la récupération des signalements par station"""
        Signalement.objects.create(
            station=self.station,
            fuel_type='Essence',
            status='Disponible'
        )
        response = self.client.get(
            f'/api/signalements/by_station/?station_id={self.station.id}'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class StatisticsAPITests(APITestCase):
    """Tests pour l'API des statistiques"""
    
    def setUp(self):
        self.client = APIClient()
        self.station = Station.objects.create(
            name="Station Test",
            brand="Shell",
            latitude=12.6452,
            longitude=-8.0029
        )
    
    def test_statistics(self):
        """Test l'endpoint des statistiques"""
        response = self.client.get('/api/statistics/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('total_stations', response.data)
    
    def test_statistics_by_brand(self):
        """Test l'endpoint des statistiques par marque"""
        response = self.client.get('/api/statistics/by-brand/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
    
    def test_fuel_availability_map(self):
        """Test l'endpoint de la carte de disponibilité"""
        response = self.client.get('/api/fuel-availability-map/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
    
    def test_signalements_heatmap(self):
        """Test l'endpoint de la heatmap"""
        response = self.client.get('/api/signalements/heatmap/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
