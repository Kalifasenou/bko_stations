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
from django.db.models import F, Count, Q, Prefetch, Case, When, IntegerField, Max
from django.shortcuts import get_object_or_404
from django.core.exceptions import ValidationError
from django.core.cache import cache
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import RefreshToken
import logging

from .models import Station, Signalement, ZoneElectrique, ElectriciteSignalement
from .serializers import (
    StationSerializer,
    SignalementSerializer,
    ZoneElectriqueSerializer,
    ElectriciteSignalementSerializer,
)
from .utils import (
    calculate_distance,
    get_user_ip,
    validate_coordinates as utils_validate_coordinates,
)
from .permissions import IsAdminOrReadOnly, IsAuthenticatedOrReadOnlyForSignalement

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

                stations_with_distance = []
                distance_map = {}
                for station in queryset:
                    distance = calculate_distance(lat, lon, station.latitude, station.longitude)
                    if distance <= radius:
                        rounded_distance = round(distance, 1)
                        station.distance = rounded_distance
                        stations_with_distance.append(station)
                        distance_map[station.id] = rounded_distance

                stations_with_distance.sort(key=lambda x: x.distance)
                ids = [s.id for s in stations_with_distance]

                if not ids:
                    return Station.objects.none()

                preserved_order = Case(
                    *[When(pk=pk, then=pos) for pos, pk in enumerate(ids)],
                    output_field=IntegerField()
                )
                queryset = Station.objects.filter(id__in=ids).annotate(_distance_order=preserved_order).order_by('_distance_order')

                for station in queryset:
                    station.distance = distance_map.get(station.id)
            except ValidationError as e:
                logger.warning(f"Erreur de validation GPS: {e}")
                return Station.objects.none()

        available_fuel = self.request.query_params.get('available_fuel')
        if available_fuel in ['Essence', 'Gazole']:
            queryset = queryset.filter(
                signalements__fuel_type=available_fuel,
                signalements__status='Disponible',
                signalements__timestamp__gte=timezone.now() - timedelta(hours=4)
            ).distinct()

        freshness_minutes = self.request.query_params.get('freshness_minutes')
        if freshness_minutes:
            try:
                freshness_minutes = max(1, min(int(freshness_minutes), 240))
                threshold = timezone.now() - timedelta(minutes=freshness_minutes)
                # Only filter by freshness if there's also a fuel filter active
                # Otherwise show all stations (with or without signalements)
                if available_fuel:
                    queryset = queryset.filter(signalements__timestamp__gte=threshold).distinct()
            except ValueError:
                pass

        sort_by = self.request.query_params.get('sort_by')
        if sort_by == 'recent':
            queryset = queryset.annotate(last_signalement_at=Max('signalements__timestamp')).order_by('-last_signalement_at', 'name')
        elif sort_by == 'name':
            queryset = queryset.order_by('name')

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
    permission_classes = [IsAuthenticatedOrReadOnlyForSignalement]

    def get_throttles(self):
        """Apply rate limiting only to write operations (POST)"""
        if self.action == 'create':
            return [SignalementAnonRateThrottle(), SignalementUserRateThrottle()]
        return []

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

        if fuel_type not in ['Essence', 'Gazole']:
            return Response(
                {"error": "Seuls Essence et Gazole sont autorisés pour les stations"},
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
        data.setdefault('load_level', request.data.get('load_level', 'Normal'))
        data.setdefault('source_type', request.data.get('source_type', 'Observateur'))
        data.setdefault('duration_estimate_minutes', request.data.get('duration_estimate_minutes', 0))
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
            timestamp__gte=timezone.now() - timedelta(hours=4),
            fuel_type__in=['Essence', 'Gazole']
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
            fuel_type__in=['Essence', 'Gazole'],
            timestamp__gte=timezone.now() - timedelta(hours=4)
        ).order_by('-timestamp')[:limit]
        
        serializer = self.get_serializer(signalements, many=True)
        return Response(serializer.data)


class ZoneElectriqueViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet lecture seule pour les zones électriques"""
    queryset = ZoneElectrique.objects.filter(is_active=True)
    serializer_class = ZoneElectriqueSerializer
    permission_classes = [AllowAny]


class ElectriciteSignalementViewSet(viewsets.ModelViewSet):
    """ViewSet pour les signalements électricité par zone"""
    queryset = ElectriciteSignalement.objects.all()
    serializer_class = ElectriciteSignalementSerializer
    permission_classes = [IsAuthenticatedOrReadOnlyForSignalement]
    throttle_classes = [SignalementAnonRateThrottle, SignalementUserRateThrottle]

    def create(self, request, *args, **kwargs):
        ip = get_user_ip(request)
        zone_id = request.data.get('zone')
        new_status = request.data.get('status')

        if not zone_id:
            return Response(
                {"error": "Le champ 'zone' est requis"},
                status=status.HTTP_400_BAD_REQUEST
            )

        if new_status not in ['Disponible', 'Coupure', 'Instable', 'Retour récent', 'Épuisé']:
            return Response(
                {"error": "Le statut électricité doit être Disponible, Coupure, Instable ou Retour récent"},
                status=status.HTTP_400_BAD_REQUEST
            )

        one_hour_ago = timezone.now() - timedelta(hours=1)
        existing_vote = ElectriciteSignalement.objects.filter(
            zone_id=zone_id,
            ip=ip,
            timestamp__gte=one_hour_ago
        ).first()

        if existing_vote:
            return Response(
                {"error": "Vous avez déjà signalé cette zone dans l'heure. Réessayez plus tard."},
                status=status.HTTP_400_BAD_REQUEST
            )

        four_hours_ago = timezone.now() - timedelta(hours=4)
        existing_signalement = ElectriciteSignalement.objects.filter(
            zone_id=zone_id,
            timestamp__gte=four_hours_ago
        ).order_by('-timestamp').first()

        incoming_load = request.data.get('load_level', 'Normal')
        incoming_source = request.data.get('source_type', 'Observateur')
        incoming_duration = int(request.data.get('duration_estimate_minutes', 0) or 0)

        if (
            existing_signalement
            and existing_signalement.status == new_status
            and existing_signalement.load_level == incoming_load
        ):
            existing_signalement.approval_count = F('approval_count') + 1
            existing_signalement.timestamp = timezone.now()
            existing_signalement.source_type = incoming_source
            existing_signalement.duration_estimate_minutes = incoming_duration
            existing_signalement.save(
                update_fields=['approval_count', 'timestamp', 'source_type', 'duration_estimate_minutes']
            )
            existing_signalement.refresh_from_db()
            serializer = self.get_serializer(existing_signalement)
            return Response(serializer.data, status=status.HTTP_200_OK)

        data = request.data.copy()
        data['ip'] = ip
        serializer = self.get_serializer(data=data)

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['get'])
    def latest(self, request):
        try:
            limit = int(request.query_params.get('limit', 10))
        except ValueError:
            return Response(
                {"error": "Le paramètre 'limit' doit être un nombre entier"},
                status=status.HTTP_400_BAD_REQUEST
            )

        limit = max(1, min(limit, 50))
        signalements = ElectriciteSignalement.objects.filter(
            timestamp__gte=timezone.now() - timedelta(hours=4)
        ).order_by('-timestamp')[:limit]

        serializer = self.get_serializer(signalements, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def by_zone(self, request):
        zone_id = request.query_params.get('zone_id')
        if not zone_id:
            return Response(
                {"error": "Le paramètre 'zone_id' est requis"},
                status=status.HTTP_400_BAD_REQUEST
            )

        signalements = ElectriciteSignalement.objects.filter(
            zone_id=zone_id,
            timestamp__gte=timezone.now() - timedelta(hours=4)
        ).order_by('-timestamp')[:50]

        serializer = self.get_serializer(signalements, many=True)
        return Response(serializer.data)


@api_view(['GET'])
@permission_classes([AllowAny])
def electricity_by_location(request):
    """Retourne la zone électrique la plus proche d'un point GPS"""
    lat = request.query_params.get('lat')
    lon = request.query_params.get('lon')

    if not lat or not lon:
        return Response(
            {"error": "Les paramètres 'lat' et 'lon' sont requis"},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        lat, lon = utils_validate_coordinates(lat, lon)
    except ValidationError as e:
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    zones = ZoneElectrique.objects.filter(is_active=True)
    if not zones.exists():
        return Response({"zone": None, "signalement": None})

    nearest_zone = None
    min_distance = None
    for zone in zones:
        distance = calculate_distance(lat, lon, zone.latitude, zone.longitude)
        if min_distance is None or distance < min_distance:
            min_distance = distance
            nearest_zone = zone

    latest = nearest_zone.get_latest_signalement() if nearest_zone else None
    return Response({
        'zone': ZoneElectriqueSerializer(nearest_zone).data if nearest_zone else None,
        'distance_km': round(min_distance, 2) if min_distance is not None else None,
        'signalement': ElectriciteSignalementSerializer(latest).data if latest else None,
        'reliability_score': nearest_zone.get_reliability_score() if nearest_zone else 0,
    })


@api_view(['GET'])
@permission_classes([AllowAny])
def electricity_nearby(request):
    """Liste les zones électriques proches avec filtres"""
    lat = request.query_params.get('lat')
    lon = request.query_params.get('lon')
    if not lat or not lon:
        return Response({"error": "Les paramètres 'lat' et 'lon' sont requis"}, status=status.HTTP_400_BAD_REQUEST)

    try:
        lat, lon = utils_validate_coordinates(lat, lon)
        radius = float(request.query_params.get('radius', 10))
    except (ValidationError, ValueError) as e:
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    status_filter = request.query_params.get('status')
    try:
        freshness_minutes = int(request.query_params.get('freshness_minutes', 240))
    except ValueError:
        freshness_minutes = 240
    threshold = timezone.now() - timedelta(minutes=max(1, min(freshness_minutes, 1440)))

    results = []
    for zone in ZoneElectrique.objects.filter(is_active=True):
        distance = calculate_distance(lat, lon, zone.latitude, zone.longitude)
        if distance > radius:
            continue

        latest = zone.signalements_electricite.filter(timestamp__gte=threshold).order_by('-timestamp').first()
        if status_filter and status_filter != 'all' and (not latest or latest.status != status_filter):
            continue

        results.append({
            'zone': ZoneElectriqueSerializer(zone).data,
            'distance_km': round(distance, 2),
            'latest_signalement': ElectriciteSignalementSerializer(latest).data if latest else None,
            'reliability_score': zone.get_reliability_score(),
        })

    sort_by = request.query_params.get('sort_by', 'distance')
    if sort_by == 'reliability':
        results.sort(key=lambda x: x['reliability_score'], reverse=True)
    elif sort_by == 'freshness':
        results.sort(key=lambda x: x['latest_signalement']['timestamp'] if x['latest_signalement'] else '', reverse=True)
    else:
        results.sort(key=lambda x: x['distance_km'])

    return Response(results)


@api_view(['GET'])
@permission_classes([AllowAny])
def electricity_recommendation(request):
    """Retourne la meilleure zone recommandée près de l'utilisateur"""
    lat = request.query_params.get('lat')
    lon = request.query_params.get('lon')
    if not lat or not lon:
        return Response({"error": "Les paramètres 'lat' et 'lon' sont requis"}, status=status.HTTP_400_BAD_REQUEST)

    try:
        lat, lon = utils_validate_coordinates(lat, lon)
        radius = float(request.query_params.get('radius', 10))
    except (ValidationError, ValueError) as e:
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    candidates = []
    for zone in ZoneElectrique.objects.filter(is_active=True):
        distance = calculate_distance(lat, lon, zone.latitude, zone.longitude)
        if distance > radius:
            continue
        latest = zone.get_latest_signalement()
        if not latest:
            continue

        status_bonus = 0
        if latest.status == 'Disponible':
            status_bonus = 40
        elif latest.status == 'Retour récent':
            status_bonus = 25
        elif latest.status == 'Instable':
            status_bonus = 10

        score = zone.get_reliability_score() + status_bonus - min(30, int(distance * 3))
        candidates.append((score, zone, distance, latest))

    if not candidates:
        return Response({'recommendation': None})

    candidates.sort(key=lambda x: x[0], reverse=True)
    best_score, best_zone, best_distance, best_signalement = candidates[0]

    return Response({
        'recommendation': {
            'zone': ZoneElectriqueSerializer(best_zone).data,
            'distance_km': round(best_distance, 2),
            'latest_signalement': ElectriciteSignalementSerializer(best_signalement).data,
            'score': best_score,
        }
    })


@api_view(['GET'])
@permission_classes([AllowAny])
def electricity_timeline(request, zone_id):
    """Historique des signalements électricité pour une zone"""
    try:
        zone = ZoneElectrique.objects.get(pk=zone_id, is_active=True)
    except ZoneElectrique.DoesNotExist:
        return Response({"error": "Zone introuvable"}, status=status.HTTP_404_NOT_FOUND)

    try:
        hours = int(request.query_params.get('hours', 24))
    except ValueError:
        hours = 24
    hours = max(1, min(hours, 168))
    threshold = timezone.now() - timedelta(hours=hours)

    timeline = zone.signalements_electricite.filter(timestamp__gte=threshold).order_by('-timestamp')[:200]
    serializer = ElectriciteSignalementSerializer(timeline, many=True)
    return Response({
        'zone': ZoneElectriqueSerializer(zone).data,
        'timeline': serializer.data,
    })


@api_view(['GET'])
@permission_classes([AllowAny])
def electricity_statistics(request):
    """Statistiques dédiées électricité"""
    now = timezone.now()
    four_hours_ago = now - timedelta(hours=4)
    twenty_four_hours_ago = now - timedelta(hours=24)

    active_zones = ZoneElectrique.objects.filter(is_active=True)
    recent = ElectriciteSignalement.objects.filter(timestamp__gte=four_hours_ago)

    by_status = recent.values('status').annotate(count=Count('id')).order_by('-count')
    top_zones = active_zones.annotate(
        signalement_count=Count('signalements_electricite', filter=Q(signalements_electricite__timestamp__gte=twenty_four_hours_ago))
    ).order_by('-signalement_count')[:5]

    return Response({
        'total_zones': active_zones.count(),
        'recent_signalements': recent.count(),
        'by_status': list(by_status),
        'top_zones': [
            {
                'id': z.id,
                'name': z.name,
                'zone_type': z.zone_type,
                'signalement_count': z.signalement_count,
                'reliability_score': z.get_reliability_score(),
            }
            for z in top_zones
        ],
        'last_updated': now.isoformat(),
    })


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
        active_signalements = Signalement.objects.filter(
            timestamp__gte=four_hours_ago,
            fuel_type__in=['Essence', 'Gazole']
        )
        
        # Stations avec carburant disponible (au moins un carburant disponible)
        stations_with_fuel = Station.objects.filter(
            is_active=True,
            signalements__timestamp__gte=four_hours_ago,
            signalements__fuel_type__in=['Essence', 'Gazole'],
            signalements__status='Disponible'
        ).distinct().count()
        
        # Stations en rupture (tous les signalements récents sont 'Épuisé')
        # On exclut les stations qui ont au moins un signalement 'Disponible'
        stations_empty = Station.objects.filter(
            is_active=True,
            signalements__timestamp__gte=four_hours_ago,
            signalements__fuel_type__in=['Essence', 'Gazole'],
            signalements__status='Épuisé'
        ).exclude(
            signalements__timestamp__gte=four_hours_ago,
            signalements__fuel_type__in=['Essence', 'Gazole'],
            signalements__status='Disponible'
        ).distinct().count()
        
        # Signalements des dernières 24h
        signalements_24h = Signalement.objects.filter(
            timestamp__gte=twenty_four_hours_ago,
            fuel_type__in=['Essence', 'Gazole']
        ).count()
        
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

        electricite_disponible = ElectriciteSignalement.objects.filter(
            timestamp__gte=four_hours_ago,
            status='Disponible'
        ).count()

        electricite_instable = ElectriciteSignalement.objects.filter(
            timestamp__gte=four_hours_ago,
            status='Instable'
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
            },
            'electricity_availability': {
                'zones_disponibles': electricite_disponible,
                'zones_instables': electricite_instable,
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
                signalements__fuel_type__in=['Essence', 'Gazole'],
                signalements__status='Disponible'
            ).distinct()
        elif status_filter == 'empty':
            # Stations où tous les carburants sont épuisés
            stations = stations.filter(
                signalements__timestamp__gte=four_hours_ago,
                signalements__fuel_type__in=['Essence', 'Gazole'],
                signalements__status='Épuisé'
            ).exclude(
                signalements__timestamp__gte=four_hours_ago,
                signalements__fuel_type__in=['Essence', 'Gazole'],
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
                signalements__fuel_type__in=['Essence', 'Gazole'],
                signalements__status='Disponible'
            ).distinct().count()

            empty = brand_stations.filter(
                signalements__timestamp__gte=four_hours_ago,
                signalements__fuel_type__in=['Essence', 'Gazole'],
                signalements__status='Épuisé'
            ).exclude(
                signalements__timestamp__gte=four_hours_ago,
                signalements__fuel_type__in=['Essence', 'Gazole'],
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
            Prefetch(
                'signalements',
                queryset=Signalement.objects.filter(
                    timestamp__gte=four_hours_ago,
                    fuel_type__in=['Essence', 'Gazole']
                )
            )
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
            timestamp__gte=time_threshold,
            fuel_type__in=['Essence', 'Gazole']
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
    """Créer un compte utilisateur avec numéro de téléphone et retourner des tokens JWT.
    Le numéro de téléphone est l'identifiant unique."""
    phone = str(request.data.get('phone', '')).strip()
    password = str(request.data.get('password', '')).strip()
    username = str(request.data.get('username', '')).strip()

    if not phone or len(phone) < 6:
        return Response(
            {'error': 'Le numéro de téléphone est requis et doit contenir au moins 6 chiffres'},
            status=status.HTTP_400_BAD_REQUEST
        )

    if len(password) < 8:
        return Response(
            {'error': 'Le mot de passe doit contenir au moins 8 caractères'},
            status=status.HTTP_400_BAD_REQUEST
        )

    if not username:
        username = phone  # Use phone as username if not provided

    User = get_user_model()
    from .models import UserProfile

    # Vérifier l'unicité du numéro de téléphone (identifiant unique)
    if UserProfile.objects.filter(phone=phone).exists():
        return Response(
            {'error': 'Ce numéro de téléphone est déjà utilisé par un autre compte'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # Vérifier si le username existe déjà
    if User.objects.filter(username=username).exists():
        return Response(
            {'error': "Ce nom d'utilisateur existe déjà"},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        user = User.objects.create_user(username=username, password=password)
        UserProfile.objects.create(user=user, phone=phone)
    except Exception as e:
        logger.error(f"Erreur création utilisateur: {e}")
        return Response(
            {'error': 'Erreur serveur lors de la création du compte. Réessayez.'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

    refresh = RefreshToken.for_user(user)

    return Response(
        {
            'user': {'id': user.id, 'username': user.username, 'phone': phone},
            'refresh': str(refresh),
            'access': str(refresh.access_token),
            'message': 'Compte créé avec succès !',
        },
        status=status.HTTP_201_CREATED
    )


@api_view(['POST'])
@permission_classes([AllowAny])
def login_user(request):
    """Authentifier un utilisateur par téléphone (ou username) + mot de passe."""
    identifier = str(request.data.get('identifier', '')).strip()
    password = str(request.data.get('password', '')).strip()

    if not identifier or not password:
        return Response(
            {'error': 'Veuillez fournir un identifiant (téléphone) et un mot de passe'},
            status=status.HTTP_400_BAD_REQUEST
        )

    from django.contrib.auth import authenticate
    from .models import UserProfile

    user = None

    # Essayer par téléphone d'abord
    if identifier.isdigit():
        profile = UserProfile.objects.select_related('user').filter(phone=identifier).first()
        if profile:
            user = authenticate(request, username=profile.user.username, password=password)
    else:
        # Essayer par username
        user = authenticate(request, username=identifier, password=password)

    if user is None:
        return Response(
            {'error': 'Identifiant ou mot de passe incorrect'},
            status=status.HTTP_401_UNAUTHORIZED
        )

    if not user.is_active:
        return Response(
            {'error': 'Ce compte est désactivé'},
            status=status.HTTP_403_FORBIDDEN
        )

    refresh = RefreshToken.for_user(user)
    phone = getattr(user, 'profile', None)
    phone_value = phone.phone if phone else ''

    return Response(
        {
            'user': {'id': user.id, 'username': user.username, 'phone': phone_value},
            'refresh': str(refresh),
            'access': str(refresh.access_token),
            'message': 'Connexion réussie',
        },
        status=status.HTTP_200_OK
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
            timestamp__gte=timezone.now() - timedelta(hours=4),
            fuel_type__in=['Essence', 'Gazole']
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
