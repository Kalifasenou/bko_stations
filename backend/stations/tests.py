from django.test import TestCase, Client
from django.utils import timezone
from datetime import timedelta
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase, APIClient
from rest_framework import status

from .models import Station, Signalement, ZoneElectrique, ElectriciteSignalement


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
        User = get_user_model()
        self.user = User.objects.create_user(username='apiuser', password='StrongPass123!')
        self.staff_user = User.objects.create_user(
            username='apistaff',
            password='StrongPass123!',
            is_staff=True
        )
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

    def test_create_station_with_manager_name(self):
        """Test la création d'une station avec nom du gérant"""
        data = {
            'name': 'Nouvelle Station',
            'brand': 'Oryx',
            'address': 'Sotuba',
            'latitude': 12.6700,
            'longitude': -7.9800,
            'manager_name': 'Amadou Diallo',
            'is_active': True,
        }
        response = self.client.post('/api/stations/', data)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_create_station_with_manager_name_authenticated_non_staff_forbidden(self):
        """Un utilisateur authentifié non staff ne peut pas créer de station"""
        token_response = self.client.post('/api/auth/token/', {
            'username': 'apiuser',
            'password': 'StrongPass123!'
        }, format='json')
        access = token_response.data['access']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access}')

        data = {
            'name': 'Nouvelle Station Auth',
            'brand': 'Oryx',
            'address': 'Sotuba',
            'latitude': 12.6700,
            'longitude': -7.9800,
            'manager_name': 'Amadou Diallo',
            'is_active': True,
        }
        response = self.client.post('/api/stations/', data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_create_station_with_manager_name_staff_allowed(self):
        """Un utilisateur staff authentifié peut créer une station"""
        token_response = self.client.post('/api/auth/token/', {
            'username': 'apistaff',
            'password': 'StrongPass123!'
        }, format='json')
        access = token_response.data['access']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access}')

        data = {
            'name': 'Nouvelle Station Staff',
            'brand': 'Oryx',
            'address': 'Sotuba',
            'latitude': 12.6710,
            'longitude': -7.9810,
            'manager_name': 'Amadou Diallo',
            'is_active': True,
        }
        response = self.client.post('/api/stations/', data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['manager_name'], 'Amadou Diallo')


class SignalementAPITests(APITestCase):
    """Tests pour l'API des signalements"""
    
    def setUp(self):
        self.client = APIClient()
        User = get_user_model()
        self.user = User.objects.create_user(username='signaluser', password='StrongPass123!')
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
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_create_signalement_authenticated(self):
        """Test la création d'un signalement avec JWT"""
        token_response = self.client.post('/api/auth/token/', {
            'username': 'signaluser',
            'password': 'StrongPass123!'
        }, format='json')
        access = token_response.data['access']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access}')

        data = {
            'station': self.station.id,
            'fuel_type': 'Essence',
            'status': 'Disponible'
        }
        response = self.client.post('/api/signalements/', data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
    
    def test_create_signalement_missing_station(self):
        """Test que la création échoue sans station (requiert auth)"""
        data = {
            'fuel_type': 'Essence',
            'status': 'Disponible'
        }
        response = self.client.post('/api/signalements/', data)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
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

    def test_create_signalement_same_status_increments_approval_count(self):
        """Même statut récent => incrément d'approbation"""
        token_response = self.client.post('/api/auth/token/', {
            'username': 'signaluser',
            'password': 'StrongPass123!'
        }, format='json')
        access = token_response.data['access']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access}')

        Signalement.objects.create(
            station=self.station,
            fuel_type='Essence',
            status='Disponible',
            approval_count=2,
            ip='10.10.10.10'
        )

        self.client.credentials(
            HTTP_AUTHORIZATION=f'Bearer {access}',
            HTTP_X_FORWARDED_FOR='11.11.11.11'
        )
        response = self.client.post('/api/signalements/', {
            'station': self.station.id,
            'fuel_type': 'Essence',
            'status': 'Disponible'
        })

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['approval_count'], 3)
        self.assertEqual(Signalement.objects.filter(station=self.station, fuel_type='Essence').count(), 1)

    def test_create_signalement_opposite_status_creates_new_event(self):
        """Statut opposé récent => nouveau signalement"""
        token_response = self.client.post('/api/auth/token/', {
            'username': 'signaluser',
            'password': 'StrongPass123!'
        }, format='json')
        access = token_response.data['access']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access}')

        Signalement.objects.create(
            station=self.station,
            fuel_type='Essence',
            status='Disponible',
            approval_count=4,
            ip='10.10.10.10'
        )

        self.client.credentials(
            HTTP_AUTHORIZATION=f'Bearer {access}',
            HTTP_X_FORWARDED_FOR='12.12.12.12'
        )
        response = self.client.post('/api/signalements/', {
            'station': self.station.id,
            'fuel_type': 'Essence',
            'status': 'Épuisé'
        })

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Signalement.objects.filter(station=self.station, fuel_type='Essence').count(), 2)
        latest = Signalement.objects.filter(station=self.station, fuel_type='Essence').order_by('-timestamp').first()
        self.assertEqual(latest.status, 'Épuisé')
        self.assertEqual(latest.approval_count, 1)


class ElectricityZoneAPITests(APITestCase):
    """Tests des endpoints zones électriques"""

    def setUp(self):
        self.client = APIClient()
        User = get_user_model()
        self.user = User.objects.create_user(username='elecuser', password='StrongPass123!')
        self.zone = ZoneElectrique.objects.create(
            name='Badalabougou',
            zone_type='Quartier',
            latitude=12.6500,
            longitude=-7.9850,
            radius_km=2.0,
        )
        ElectriciteSignalement.objects.create(zone=self.zone, status='Disponible')

    def test_list_zones(self):
        response = self.client.get('/api/zones-electriques/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_electricity_by_location(self):
        response = self.client.get('/api/electricity/by-location/?lat=12.6499&lon=-7.9851')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('zone', response.data)

    def test_create_electricity_signalement_authenticated(self):
        token_response = self.client.post('/api/auth/token/', {
            'username': 'elecuser',
            'password': 'StrongPass123!'
        }, format='json')
        access = token_response.data['access']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access}')

        response = self.client.post('/api/electricite-signalements/', {
            'zone': self.zone.id,
            'status': 'Instable'
        }, format='json')
        self.assertIn(response.status_code, [status.HTTP_200_OK, status.HTTP_201_CREATED])


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


class AuthAndMonitoringAPITests(APITestCase):
    """Tests JWT et endpoint monitoring"""

    def setUp(self):
        self.client = APIClient()
        User = get_user_model()
        self.user = User.objects.create_user(username='monitoruser', password='StrongPass123!')

    def test_token_obtain_and_refresh(self):
        response = self.client.post('/api/auth/token/', {
            'username': 'monitoruser',
            'password': 'StrongPass123!'
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)

        refresh_response = self.client.post('/api/auth/token/refresh/', {
            'refresh': response.data['refresh']
        }, format='json')
        self.assertEqual(refresh_response.status_code, status.HTTP_200_OK)
        self.assertIn('access', refresh_response.data)

    def test_monitoring_requires_authentication(self):
        response = self.client.get('/api/monitoring/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_monitoring_with_authentication(self):
        token_response = self.client.post('/api/auth/token/', {
            'username': 'monitoruser',
            'password': 'StrongPass123!'
        }, format='json')
        access = token_response.data['access']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access}')

        response = self.client.get('/api/monitoring/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('status', response.data)
        self.assertIn('database', response.data)
