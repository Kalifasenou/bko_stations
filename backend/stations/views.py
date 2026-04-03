from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view, permission_classes, throttle_classes
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticatedOrReadOnly, IsAuthenticated
from rest_framework.pagination import PageNumberPagination
from rest_framework.throttling import AnonRateThrottle, UserRateThrottle
from django.utils import timezone
from django.views.decorators.cache import cache_page
from django.utils.decorators import method_decorator
from datetime import timedelta
from django.db.models import F, Count, Q, Prefetch, Case, When, IntegerField
from django.shortcuts import get_object_or_404
from django.core.exceptions import ValidationError
from django.core.cache import cache
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import RefreshToken
import math
import logging

from .models import Station, Signalement
from .serializers import StationSerializer, SignalementSerializer
from .utils import get_user_ip, validate_coordinates as utils_validate_coordinates
from .permissions import IsAdminOrReadOnly

logger = logging.getLogger(__name__)


# Rate limiting throttles
class SignalementAnonRateThrottle(AnonRateThrottle):
    rate = '10/hour'

class SignalementUserRateThrottle(UserRateThrottle):
    rate = '20/hour'


def rate_limit_signalements(zone='anon'):
    """Décorateur pour limiter les signalements par IP"""
    def decorator(view_func):
        if zone == 'anon':
            return throttle_classes([SignalementAnonRateThrottle])(view_func)
        return throttle_classes([SignalementUserRateThrottle])(view_func)
    return decorator


class StandardResultsSetPagination(PageNumberPagination):
    """Pagination standard pour les listes"""
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


def calculate_distance(lat1, lon1, lat2, lon2):
    """Calcule la distance en km entre deux points GPS (formule de Haversine)"""
    R = 6371  # Rayon de la Terre en km
    
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lon = math.radians(lon2 - lon1)
    
    a = math.sin(delta_lat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    
    return R * c


class StationViewSet(viewsets.ModelViewSet):
    """ViewSet pour les stations de carburant"""
    queryset = Station.objects.filter(is_active=True)
    serializer_class = StationSerializer
    permission_classes = [IsAdminOrReadOnly]
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        queryset = Station.objects.filter(is_active=True)
        
        # Filtrer par brand si fourni
        brand = self.request.query_params.get('brand')
        if brand:
            queryset = queryset.filter(brand__icontains=brand)
        
        # Filtrer par latitude/longitude si fourni
        lat = self.request.query_params.get('lat')
        lon = self.request.query_params.get('lon')
        
        if lat and lon:
            try:
                lat, lon = utils_validate_coordinates(lat, lon)
                radius = float(self.request.query_params.get('radius', 10))
                if radius <= 0:
                    raise ValidationError("Le rayon doit être positif")
                
                # Récupérer toutes les stations et calculer les distances
                stations_with_distance = []
                distance_map = {}
                for station in queryset:
                    distance = calculate_distance(lat, lon, station.latitude, station.longitude)
                    if distance <= radius:
                        rounded_distance = round(distance, 1)
                        station.distance = rounded_distance
                        stations_with_distance.append(station)
                        distance_map[station.id] = rounded_distance
                
                # Trier par distance et conserver l'ordre pour la pagination
                stations_with_distance.sort(key=lambda x: x.distance)
                ids = [s.id for s in stations_with_distance]
                
                if not ids:
                    return Station.objects.none()
                
                preserved_order = Case(
                    *[When(pk=pk, then=pos) for pos, pk in enumerate(ids)],
                    output_field=IntegerField()
                )
                queryset = Station.objects.filter(id__in=ids).annotate(_distance_order=preserved_order).order_by('_distance_order')
                
                # Réappliquer les distances après réévaluation du QuerySet
                for station in queryset:
                    station.distance = distance_map.get(station.id)
            except ValidationError as e:
                logger.warning(f"Erreur de validation GPS: {e}")
                return Station.objects.none()
        
        return queryset

    @action(detail=True, methods=['get'])
    def nearby(self, request, pk=None):
        """Retourne les stations à proximité d'une station donnée"""
        try:
            station = self.get_object()
            lat = station.latitude
            lon = station.longitude
            radius = float(request.query_params.get('radius', 2))
            
            if radius <= 0:
                return Response(
                    {"error": "Le rayon doit être positif"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            nearby_stations = []
            for s in Station.objects.filter(is_active=True).exclude(pk=station.pk):
                distance = calculate_distance(lat, lon, s.latitude, s.longitude)
                if distance <= radius:
                    s.distance = round(distance, 1)
                    nearby_stations.append(s)
            
            nearby_stations.sort(key=lambda x: x.distance)
            serializer = self.get_serializer(nearby_stations, many=True)
            return Response(serializer.data)
        except ValueError as e:
            logger.error(f"Erreur dans nearby: {e}")
            return Response(
                {"error": "Paramètres invalides"},
                status=status.HTTP_400_BAD_REQUEST
            )


class SignalementViewSet(viewsets.ModelViewSet):
    """ViewSet pour les signalements de carburant"""
    queryset = Signalement.objects.all()
    serializer_class = SignalementSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    throttle_classes = [SignalementAnonRateThrottle, SignalementUserRateThrottle]

    def create(self, request, *args, **kwargs):
        """Créer un nouveau signalement avec validation IP et incrémentation"""
        ip = get_user_ip(request)
        station_id = request.data.get('station')
        fuel_type = request.data.get('fuel_type')
        new_status = request.data.get('status')
        
        if not station_id:
            return Response(
                {"error": "Le champ 'station' est requis"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Vérifier si l'utilisateur a déjà voté dans l'heure pour cette station
        one_hour_ago = timezone.now() - timedelta(hours=1)
        existing_vote = Signalement.objects.filter(
            station_id=station_id,
            ip=ip,
            timestamp__gte=one_hour_ago
        ).first()
        
        if existing_vote:
            return Response(
                {"error": "Vous avez déjà signalé cette station dans l'heure. Réessayez plus tard."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Vérifier s'il existe un signalement récent (non expiré) pour cette station et ce type de carburant
        four_hours_ago = timezone.now() - timedelta(hours=4)
        existing_signalement = Signalement.objects.filter(
            station_id=station_id,
            fuel_type=fuel_type,
            timestamp__gte=four_hours_ago
        ).order_by('-timestamp').first()

        if existing_signalement and existing_signalement.status == new_status:
            # Même statut: on incrémente la confiance du signal existant
            existing_signalement.approval_count = F('approval_count') + 1
            existing_signalement.timestamp = timezone.now()  # Rafraîchir le timestamp
            existing_signalement.save(update_fields=['approval_count', 'timestamp'])
            existing_signalement.refresh_from_db()

            serializer = self.get_serializer(existing_signalement)
            return Response(serializer.data, status=status.HTTP_200_OK)

        # Nouveau statut (ou absence d'historique récent): créer un nouvel événement
        data = request.data.copy()
        data['ip'] = ip
        serializer = self.get_serializer(data=data)
        
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['get'])
    def latest(self, request):
        """Retourne les derniers signalements (pour le live pulse)"""
        try:
            limit = int(request.query_params.get('limit', 10))
        except ValueError:
            return Response(
                {"error": "Le paramètre 'limit' doit être un nombre entier"},
                status=status.HTTP_400_BAD_REQUEST
            )

        limit = max(1, min(limit, 50))

        signalements = Signalement.objects.filter(
            timestamp__gte=timezone.now() - timedelta(hours=4)
        ).order_by('-timestamp')[:limit]
        
        serializer = self.get_serializer(signalements, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """Approuver un signalement existant"""
        ip = get_user_ip(request)
        signalement = self.get_object()
        
        # Vérifier si l'utilisateur a déjà approuvé dans l'heure
        one_hour_ago = timezone.now() - timedelta(hours=1)
        recent_approval = Signalement.objects.filter(
            station=signalement.station,
            ip=ip,
            timestamp__gte=one_hour_ago
        ).exists()
        
        if recent_approval:
            return Response(
                {"error": "Vous avez déjà approuvé un signalement pour cette station dans l'heure."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Incrémenter le compteur
        signalement.approval_count = F('approval_count') + 1
        signalement.timestamp = timezone.now()
        signalement.save()
        signalement.refresh_from_db()
        
        serializer = self.get_serializer(signalement)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def by_station(self, request):
        """Retourne les signalements pour une station spécifique"""
        station_id = request.query_params.get('station_id')
        if not station_id:
            return Response(
                {"error": "Le paramètre 'station_id' est requis"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            station_id = int(station_id)
        except ValueError:
            return Response(
                {"error": "Le paramètre 'station_id' doit être un entier"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            limit = int(request.query_params.get('limit', 50))
        except ValueError:
            return Response(
                {"error": "Le paramètre 'limit' doit être un nombre entier"},
                status=status.HTTP_400_BAD_REQUEST
            )

        limit = max(1, min(limit, 200))

        signalements = Signalement.objects.filter(
            station_id=station_id,
            timestamp__gte=timezone.now() - timedelta(hours=4)
        ).order_by('-timestamp')[:limit]
        
        serializer = self.get_serializer(signalements, many=True)
        return Response(serializer.data)


# ============================================
# STATISTICS & UTILITY ENDPOINTS
# ============================================

@api_view(['GET'])
@permission_classes([AllowAny])
@cache_page(60)
def statistics(request):
    """Retourne les statistiques globales de l'application"""
    try:
        now = timezone.now()
        four_hours_ago = now - timedelta(hours=4)
        twenty_four_hours_ago = now - timedelta(hours=24)
        
        # Total stations
        total_stations = Station.objects.filter(is_active=True).count()
        
        # Signalements actifs (non expirés)
        active_signalements = Signalement.objects.filter(timestamp__gte=four_hours_ago)
        
        # Stations avec carburant disponible (au moins un carburant disponible)
        stations_with_fuel = Station.objects.filter(
            is_active=True,
            signalements__timestamp__gte=four_hours_ago,
            signalements__status='Disponible'
        ).distinct().count()
        
        # Stations en rupture (tous les signalements récents sont 'Épuisé')
        # On exclut les stations qui ont au moins un signalement 'Disponible'
        stations_empty = Station.objects.filter(
            is_active=True,
            signalements__timestamp__gte=four_hours_ago,
            signalements__status='Épuisé'
        ).exclude(
            signalements__timestamp__gte=four_hours_ago,
            signalements__status='Disponible'
        ).distinct().count()
        
        # Signalements des dernières 24h
        signalements_24h = Signalement.objects.filter(timestamp__gte=twenty_four_hours_ago).count()
        
        # Signalements par type de carburant
        essence_disponible = Signalement.objects.filter(
            timestamp__gte=four_hours_ago,
            fuel_type='Essence',
            status='Disponible'
        ).count()
        
        gazole_disponible = Signalement.objects.filter(
            timestamp__gte=four_hours_ago,
            fuel_type='Gazole',
            status='Disponible'
        ).count()

        electricite_disponible = Signalement.objects.filter(
            timestamp__gte=four_hours_ago,
            fuel_type='Électricité',
            status='Disponible'
        ).count()
        
        # Top stations avec le plus de signalements
        top_stations = Station.objects.filter(is_active=True).annotate(
            signalement_count=Count('signalements', filter=Q(signalements__timestamp__gte=twenty_four_hours_ago))
        ).filter(signalement_count__gt=0).order_by('-signalement_count')[:5]
        
        return Response({
            'total_stations': total_stations,
            'stations_with_fuel': stations_with_fuel,
            'stations_empty': stations_empty,
            'stations_unknown': max(0, total_stations - stations_with_fuel - stations_empty),
            'signalements_24h': signalements_24h,
            'active_signalements': active_signalements.count(),
            'fuel_availability': {
                'essence_disponible': essence_disponible,
                'gazole_disponible': gazole_disponible,
                'electricite_disponible': electricite_disponible,
            },
            'top_stations': [
                {'id': s.id, 'name': s.name, 'brand': s.brand, 'count': s.signalement_count}
                for s in top_stations
            ],
            'last_updated': now.isoformat(),
        })
    except Exception as e:
        logger.error(f"Erreur dans statistics: {e}")
        return Response(
            {"error": "Erreur lors du calcul des statistiques"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([AllowAny])
@cache_page(300)
def search_stations(request):
    """Recherche de stations par nom ou marque"""
    try:
        query = request.query_params.get('q', '').strip()
        
        if not query:
            return Response(
                {"error": "Le paramètre 'q' est requis pour la recherche"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if len(query) < 2:
            return Response(
                {"error": "La recherche doit contenir au moins 2 caractères"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        stations = Station.objects.filter(
            Q(name__icontains=query) | Q(brand__icontains=query),
            is_active=True
        ).order_by('name')[:20]
        
        serializer = StationSerializer(stations, many=True)
        return Response(serializer.data)
    except Exception as e:
        logger.error(f"Erreur dans search_stations: {e}")
        return Response(
            {"error": "Erreur lors de la recherche"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([AllowAny])
@cache_page(120)
def stations_by_status(request):
    """Retourne les stations filtrées par statut"""
    try:
        status_filter = request.query_params.get('status', 'all')
        four_hours_ago = timezone.now() - timedelta(hours=4)
        
        stations = Station.objects.filter(is_active=True)
        
        if status_filter == 'available':
            # Stations avec au moins un carburant disponible
            stations = stations.filter(
                signalements__timestamp__gte=four_hours_ago,
                signalements__status='Disponible'
            ).distinct()
        elif status_filter == 'empty':
            # Stations où tous les carburants sont épuisés
            stations = stations.filter(
                signalements__timestamp__gte=four_hours_ago,
                signalements__status='Épuisé'
            ).exclude(
                signalements__timestamp__gte=four_hours_ago,
                signalements__status='Disponible'
            ).distinct()
        elif status_filter == 'unknown':
            # Stations sans signalement récent
            stations = stations.exclude(
                signalements__timestamp__gte=four_hours_ago
            ).distinct()
        
        serializer = StationSerializer(stations, many=True)
        return Response(serializer.data)
    except Exception as e:
        logger.error(f"Erreur dans stations_by_status: {e}")
        return Response(
            {"error": "Erreur lors du filtrage des stations"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([AllowAny])
@cache_page(120)
def statistics_by_brand(request):
    """Retourne les statistiques par marque de carburant"""
    try:
        four_hours_ago = timezone.now() - timedelta(hours=4)
        
        brands = Station.objects.filter(is_active=True).values('brand').distinct()
        stats = []
        
        for brand_obj in brands:
            brand = brand_obj['brand']
            brand_stations = Station.objects.filter(is_active=True, brand=brand)
            
            available = brand_stations.filter(
                signalements__timestamp__gte=four_hours_ago,
                signalements__status='Disponible'
            ).distinct().count()
            
            empty = brand_stations.filter(
                signalements__timestamp__gte=four_hours_ago,
                signalements__status='Épuisé'
            ).exclude(
                signalements__timestamp__gte=four_hours_ago,
                signalements__status='Disponible'
            ).distinct().count()
            
            stats.append({
                'brand': brand,
                'total_stations': brand_stations.count(),
                'available': available,
                'empty': empty,
                'unknown': brand_stations.count() - available - empty,
            })
        
        return Response(sorted(stats, key=lambda x: x['brand']))
    except Exception as e:
        logger.error(f"Erreur dans statistics_by_brand: {e}")
        return Response(
            {"error": "Erreur lors du calcul des statistiques par marque"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([AllowAny])
@cache_page(120)
def fuel_availability_map(request):
    """Retourne une carte de disponibilité des carburants par station"""
    try:
        four_hours_ago = timezone.now() - timedelta(hours=4)
        
        stations = Station.objects.filter(is_active=True).prefetch_related(
            Prefetch('signalements',
                     queryset=Signalement.objects.filter(timestamp__gte=four_hours_ago))
        )
        
        data = []
        for station in stations:
            fuel_status = {}
            for signalement in station.signalements.all():
                fuel_status[signalement.fuel_type] = {
                    'status': signalement.status,
                    'approval_count': signalement.approval_count,
                    'timestamp': signalement.timestamp.isoformat()
                }
            
            data.append({
                'id': station.id,
                'name': station.name,
                'brand': station.brand,
                'latitude': station.latitude,
                'longitude': station.longitude,
                'fuel_status': fuel_status,
                'status_color': station.status_color,
            })
        
        return Response(data)
    except Exception as e:
        logger.error(f"Erreur dans fuel_availability_map: {e}")
        return Response(
            {"error": "Erreur lors de la génération de la carte"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([AllowAny])
def brands_list(request):
    """Retourne la liste de toutes les marques de stations"""
    try:
        brands = Station.objects.filter(is_active=True).values_list('brand', flat=True).distinct()
        brands = sorted([b for b in brands if b])
        return Response({
            'brands': brands,
            'count': len(brands)
        })
    except Exception as e:
        logger.error(f"Erreur dans brands_list: {e}")
        return Response(
            {"error": "Erreur lors de la récupération des marques"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([AllowAny])
def stations_nearby(request):
    """Retourne les stations à proximité de la position de l'utilisateur"""
    try:
        lat = request.query_params.get('lat')
        lon = request.query_params.get('lon')
        radius = float(request.query_params.get('radius', 10))
        
        if not lat or not lon:
            return Response(
                {"error": "Les paramètres 'lat' et 'lon' sont requis"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            lat, lon = utils_validate_coordinates(lat, lon)
        except ValidationError as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if radius <= 0 or radius > 100:
            return Response(
                {"error": "Le rayon doit être entre 0.1 et 100 km"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Récupérer toutes les stations actives
        stations = Station.objects.filter(is_active=True)
        
        # Calculer les distances et filtrer
        nearby_stations = []
        for station in stations:
            distance = calculate_distance(lat, lon, station.latitude, station.longitude)
            if distance <= radius:
                station.distance = round(distance, 1)
                nearby_stations.append(station)
        
        # Trier par distance
        nearby_stations.sort(key=lambda x: x.distance)
        
        serializer = StationSerializer(nearby_stations, many=True)
        return Response({
            'stations': serializer.data,
            'count': len(nearby_stations),
            'user_location': {'lat': lat, 'lon': lon}
        })
    except ValueError as e:
        logger.error(f"Erreur dans stations_nearby: {e}")
        return Response(
            {"error": "Paramètres invalides"},
            status=status.HTTP_400_BAD_REQUEST
        )
    except Exception as e:
        logger.error(f"Erreur dans stations_nearby: {e}")
        return Response(
            {"error": "Erreur lors de la recherche"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([AllowAny])
@cache_page(60)
def signalements_heatmap(request):
    """Retourne les données pour une heatmap de signalements"""
    try:
        hours = int(request.query_params.get('hours', 24))
        if hours <= 0:
            raise ValidationError("Le nombre d'heures doit être positif")
        if hours > 168:
            raise ValidationError("Le nombre d'heures ne peut pas dépasser 168 (7 jours)")
        
        time_threshold = timezone.now() - timedelta(hours=hours)
        
        signalements = Signalement.objects.filter(
            timestamp__gte=time_threshold
        ).values('station__latitude', 'station__longitude', 'status').annotate(
            count=Count('id')
        )
        
        return Response(list(signalements))
    except (ValueError, ValidationError) as e:
        logger.warning(f"Erreur dans signalements_heatmap: {e}")
        return Response(
            {"error": "Paramètres invalides"},
            status=status.HTTP_400_BAD_REQUEST
        )
    except Exception as e:
        logger.error(f"Erreur dans signalements_heatmap: {e}")
        return Response(
            {"error": "Erreur lors de la génération de la heatmap"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([AllowAny])
def register_user(request):
    """Créer un compte utilisateur et retourner des tokens JWT"""
    username = str(request.data.get('username', '')).strip()
    password = str(request.data.get('password', '')).strip()

    if len(username) < 3:
        return Response(
            {'error': "Le nom d'utilisateur doit contenir au moins 3 caractères"},
            status=status.HTTP_400_BAD_REQUEST
        )

    if len(password) < 8:
        return Response(
            {'error': 'Le mot de passe doit contenir au moins 8 caractères'},
            status=status.HTTP_400_BAD_REQUEST
        )

    User = get_user_model()

    if User.objects.filter(username=username).exists():
        return Response(
            {'error': "Ce nom d'utilisateur existe déjà"},
            status=status.HTTP_400_BAD_REQUEST
        )

    user = User.objects.create_user(username=username, password=password)
    refresh = RefreshToken.for_user(user)

    return Response(
        {
            'user': {'id': user.id, 'username': user.username},
            'refresh': str(refresh),
            'access': str(refresh.access_token),
        },
        status=status.HTTP_201_CREATED
    )


@api_view(['GET'])
@permission_classes([AllowAny])
@cache_page(30)
def health_check(request):
    """Endpoint de vérification de santé de l'API"""
    try:
        # Check database connection
        from django.db import connection
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        
        # Get some basic stats
        total_stations = Station.objects.filter(is_active=True).count()
        recent_signalements = Signalement.objects.filter(
            timestamp__gte=timezone.now() - timedelta(hours=4)
        ).count()
        
        return Response({
            'status': 'healthy',
            'database': 'connected',
            'total_stations': total_stations,
            'recent_signalements': recent_signalements,
            'timestamp': timezone.now().isoformat(),
        })
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return Response(
            {'status': 'unhealthy', 'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def monitoring_overview(request):
    """Endpoint de monitoring opérationnel (authentification requise)"""
    try:
        from django.db import connection
        from django.core.cache import cache

        db_status = 'connected'
        cache_status = 'ok'

        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
        except Exception:
            db_status = 'error'

        try:
            cache.set('monitoring_probe', 'ok', timeout=5)
            cache.get('monitoring_probe')
        except Exception:
            cache_status = 'error'

        total_stations = Station.objects.filter(is_active=True).count()
        active_signalements = Signalement.objects.filter(
            timestamp__gte=timezone.now() - timedelta(hours=4)
        ).count()

        return Response({
            'status': 'ok' if db_status == 'connected' and cache_status == 'ok' else 'degraded',
            'database': db_status,
            'cache': cache_status,
            'total_stations': total_stations,
            'active_signalements_4h': active_signalements,
            'log_level': logger.getEffectiveLevel(),
            'timestamp': timezone.now().isoformat(),
        })
    except Exception as e:
        logger.error(f"Monitoring overview failed: {e}")
        return Response(
            {'status': 'error', 'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
