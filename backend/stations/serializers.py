from rest_framework import serializers
from .models import Station, Signalement, ZoneElectrique, ElectriciteSignalement
from .constants import FUEL_TYPES, FUEL_STATUS, ELECTRICITY_STATUS


class SignalementSerializer(serializers.ModelSerializer):
    """Sérialiseur pour les signalements"""
    station_name = serializers.CharField(source='station.name', read_only=True)
    station_brand = serializers.CharField(source='station.brand', read_only=True)
    time_ago = serializers.SerializerMethodField()
    is_expired = serializers.SerializerMethodField()

    class Meta:
        model = Signalement
        fields = [
            'id', 'station', 'station_name', 'station_brand',
            'fuel_type', 'status', 'timestamp', 'approval_count',
            'time_ago', 'is_expired', 'comment'
        ]
        read_only_fields = ['id', 'timestamp', 'approval_count']

    def validate_fuel_type(self, value):
        """Valide le type de carburant"""
        valid_fuel_types = [fuel for fuel in FUEL_TYPES.values()]
        if value not in valid_fuel_types:
            raise serializers.ValidationError(
                f"Le type de carburant doit être l'un des suivants: {', '.join(valid_fuel_types)}"
            )
        return value

    def validate_status(self, value):
        """Valide le statut du carburant"""
        valid_statuses = [status for status in FUEL_STATUS.values()]
        if value not in valid_statuses:
            raise serializers.ValidationError(
                f"Le statut doit être l'un des suivants: {', '.join(valid_statuses)}"
            )
        return value

    def validate(self, attrs):
        """Validation globale du signalement"""
        station = attrs.get('station')
        fuel_type = attrs.get('fuel_type')
        
        if station and fuel_type:
            # Vérifier que la station existe et est active
            if not station.is_active:
                raise serializers.ValidationError(
                    {"station": "Cette station n'est plus active"}
                )
        
        return attrs

    def get_time_ago(self, obj):
        """Retourne le temps écoulé depuis le signalement"""
        from django.utils import timezone

        delta = timezone.now() - obj.timestamp
        minutes = int(delta.total_seconds() / 60)

        if minutes < 1:
            return "À l'instant"
        if minutes < 60:
            return f"Il y a {minutes} min"
        if minutes < 1440:
            hours = minutes // 60
            return f"Il y a {hours}h"

        days = minutes // 1440
        return f"Il y a {days}j"

    def get_is_expired(self, obj):
        return obj.is_expired()


class ZoneElectriqueSerializer(serializers.ModelSerializer):
    """Sérialiseur des zones électriques"""
    latest_signalement = serializers.SerializerMethodField()
    reliability_score = serializers.SerializerMethodField()
    has_conflicting_reports = serializers.SerializerMethodField()
    electricity_status_color = serializers.ReadOnlyField()

    class Meta:
        model = ZoneElectrique
        fields = [
            'id', 'name', 'zone_type', 'latitude', 'longitude', 'radius_km',
            'is_active', 'latest_signalement', 'reliability_score', 'has_conflicting_reports', 'electricity_status_color',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at', 'latest_signalement', 'reliability_score', 'has_conflicting_reports', 'electricity_status_color']

    def get_latest_signalement(self, obj):
        latest = obj.get_latest_signalement()
        if latest:
            return ElectriciteSignalementSerializer(latest).data
        return None

    def get_reliability_score(self, obj):
        return obj.get_reliability_score()

    def get_has_conflicting_reports(self, obj):
        return obj.has_conflicting_recent_reports()


class ElectriciteSignalementSerializer(serializers.ModelSerializer):
    """Sérialiseur pour les signalements d'électricité (zones)"""
    zone_name = serializers.CharField(source='zone.name', read_only=True)
    zone_type = serializers.CharField(source='zone.zone_type', read_only=True)
    time_ago = serializers.SerializerMethodField()
    is_expired = serializers.SerializerMethodField()

    class Meta:
        model = ElectriciteSignalement
        fields = [
            'id', 'zone', 'zone_name', 'zone_type',
            'status', 'load_level', 'source_type', 'duration_estimate_minutes',
            'timestamp', 'approval_count',
            'time_ago', 'is_expired', 'comment'
        ]
        read_only_fields = ['id', 'timestamp', 'approval_count']

    def validate_status(self, value):
        valid_statuses = [status for status in ELECTRICITY_STATUS.values()]
        if value not in valid_statuses:
            raise serializers.ValidationError(
                f"Le statut électricité doit être l'un des suivants: {', '.join(valid_statuses)}"
            )
        return value

    def validate_duration_estimate_minutes(self, value):
        if value < 0 or value > 1440:
            raise serializers.ValidationError("La durée estimée doit être entre 0 et 1440 minutes")
        return value

    def validate(self, attrs):
        zone = attrs.get('zone')
        if zone and not zone.is_active:
            raise serializers.ValidationError({"zone": "Cette zone n'est plus active"})
        return attrs

    def get_time_ago(self, obj):
        from django.utils import timezone

        delta = timezone.now() - obj.timestamp
        minutes = int(delta.total_seconds() / 60)

        if minutes < 1:
            return "À l'instant"
        if minutes < 60:
            return f"Il y a {minutes} min"
        if minutes < 1440:
            hours = minutes // 60
            return f"Il y a {hours}h"

        days = minutes // 1440
        return f"Il y a {days}j"

    def get_is_expired(self, obj):
        return obj.is_expired()


class StationSerializer(serializers.ModelSerializer):
    """Sérialiseur pour les stations"""
    latest_signalement = serializers.SerializerMethodField()
    essence_signalement = serializers.SerializerMethodField()
    gazole_signalement = serializers.SerializerMethodField()
    status_color = serializers.CharField(read_only=True)
    distance = serializers.SerializerMethodField(required=False)
    has_recent_signalement = serializers.BooleanField(read_only=True)
    confidence_score = serializers.SerializerMethodField()
    has_conflicting_reports = serializers.SerializerMethodField()

    class Meta:
        model = Station
        fields = [
            'id', 'name', 'brand', 'address', 'manager_name', 'phone',
            'latitude', 'longitude', 'is_active',
            'created_at', 'updated_at', 'latest_signalement',
            'essence_signalement', 'gazole_signalement',
            'status_color', 'distance', 'has_recent_signalement',
            'confidence_score', 'has_conflicting_reports'
        ]
        read_only_fields = ['created_at', 'updated_at', 'status_color', 'has_recent_signalement', 'confidence_score', 'has_conflicting_reports']

    def get_latest_signalement(self, obj):
        """Retourne le dernier signalement non expiré"""
        latest = obj.get_latest_signalement()
        if latest:
            return SignalementSerializer(latest).data
        return None

    def get_essence_signalement(self, obj):
        """Retourne le dernier signalement non expiré pour l'essence"""
        latest = obj.get_latest_signalement_for_fuel('Essence')
        if latest:
            return SignalementSerializer(latest).data
        return None

    def get_gazole_signalement(self, obj):
        """Retourne le dernier signalement non expiré pour le gazole"""
        latest = obj.get_latest_signalement_for_fuel('Gazole')
        if latest:
            return SignalementSerializer(latest).data
        return None

    def get_distance(self, obj):
        """Retourne la distance si l'utilisateur a fourni sa position"""
        return getattr(obj, 'distance', None)

    def validate(self, attrs):
        """Validation globale de la station"""
        lat = attrs.get('latitude')
        lon = attrs.get('longitude')

        if lat is not None and lon is not None:
            if not (-90 <= lat <= 90):
                raise serializers.ValidationError(
                    {"latitude": "La latitude doit être entre -90 et 90"}
                )
            if not (-180 <= lon <= 180):
                raise serializers.ValidationError(
                    {"longitude": "La longitude doit être entre -180 et 180"}
                )

        return attrs
