from datetime import timedelta

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone


class ZoneElectrique(models.Model):
    """Zone géographique pour le suivi de l'électricité"""

    ZONE_TYPES = [
        ("Quartier", "Quartier"),
        ("Secteur", "Secteur"),
        ("Zone", "Zone"),
    ]

    name = models.CharField(max_length=120, unique=True, verbose_name="Nom de la zone")
    zone_type = models.CharField(
        max_length=20,
        choices=ZONE_TYPES,
        default="Quartier",
        verbose_name="Type de zone",
    )
    latitude = models.FloatField(
        verbose_name="Latitude",
        validators=[MinValueValidator(-90), MaxValueValidator(90)],
    )
    longitude = models.FloatField(
        verbose_name="Longitude",
        validators=[MinValueValidator(-180), MaxValueValidator(180)],
    )
    radius_km = models.FloatField(
        default=2.5, validators=[MinValueValidator(0.1)], verbose_name="Rayon (km)"
    )
    is_active = models.BooleanField(default=True, verbose_name="Active")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Zone électrique"
        verbose_name_plural = "Zones électriques"
        ordering = ["name"]
        indexes = [
            models.Index(fields=["zone_type"]),
            models.Index(fields=["is_active"]),
        ]

    def __str__(self):
        return f"{self.name} ({self.zone_type})"

    def get_latest_signalement(self):
        """Retourne le dernier signalement non expiré (moins de 4h)"""
        return (
            self.signalements_electricite.filter(
                timestamp__gte=timezone.now() - timedelta(hours=4)
            )
            .order_by("-timestamp")
            .first()
        )

    def get_reliability_score(self):
        """Score de fiabilité (0-100) basé sur récence + confirmations"""
        four_hours_ago = timezone.now() - timedelta(hours=4)
        recent = self.signalements_electricite.filter(timestamp__gte=four_hours_ago)
        if not recent.exists():
            return 0

        weighted = 0
        weight_sum = 0
        for signalement in recent:
            age_minutes = max(
                1, int((timezone.now() - signalement.timestamp).total_seconds() / 60)
            )
            recency_weight = max(1, 240 - age_minutes)
            confidence = min(10, signalement.approval_count)
            contributor_weight = signalement.get_contributor_weight()
            weighted += recency_weight * confidence * contributor_weight
            weight_sum += recency_weight * 10

        return int((weighted / weight_sum) * 100) if weight_sum else 0

    def has_conflicting_recent_reports(self):
        """Détecte des contradictions récentes sur la zone"""
        two_hours_ago = timezone.now() - timedelta(hours=2)
        statuses = (
            self.signalements_electricite.filter(timestamp__gte=two_hours_ago)
            .values_list("status", flat=True)
            .distinct()
        )
        return len(list(statuses)) > 1

    @property
    def electricity_status_color(self):
        latest = self.get_latest_signalement()
        if not latest:
            return "gray"
        if latest.status in ["Disponible", "Retour récent"]:
            return "green"
        if latest.status == "Instable":
            return "yellow"
        return "red"


class Station(models.Model):
    """Station de carburant à Bamako"""

    name = models.CharField(max_length=100, verbose_name="Nom de la station")
    brand = models.CharField(
        max_length=50, verbose_name="Enseigne (Shell, Total, Oryx, etc.)"
    )
    address = models.CharField(
        max_length=255, blank=True, default="", verbose_name="Adresse"
    )
    manager_name = models.CharField(
        max_length=100, blank=True, default="", verbose_name="Nom du gérant"
    )
    latitude = models.FloatField(
        verbose_name="Latitude",
        validators=[MinValueValidator(-90), MaxValueValidator(90)],
    )
    longitude = models.FloatField(
        verbose_name="Longitude",
        validators=[MinValueValidator(-180), MaxValueValidator(180)],
    )
    phone = models.CharField(
        max_length=20, blank=True, default="", verbose_name="Téléphone"
    )
    is_active = models.BooleanField(default=True, verbose_name="Active")
    is_pending = models.BooleanField(
        default=False, verbose_name="En attente de validation"
    )
    rejected_reason = models.CharField(
        max_length=500, blank=True, default="", verbose_name="Motif de rejet"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Station"
        verbose_name_plural = "Stations"
        ordering = ["name"]
        indexes = [
            models.Index(fields=["brand"]),
            models.Index(fields=["is_active"]),
            models.Index(fields=["is_pending"]),
            models.Index(fields=["latitude", "longitude"]),
        ]

    def __str__(self):
        return f"{self.name} ({self.brand})"

    def get_latest_signalement(self):
        """Retourne le dernier signalement non expiré (moins de 4h)"""
        return (
            self.signalements.filter(timestamp__gte=timezone.now() - timedelta(hours=4))
            .order_by("-timestamp")
            .first()
        )

    def get_latest_signalement_for_fuel(self, fuel_type):
        """Retourne le dernier signalement non expiré pour un carburant donné"""
        return (
            self.signalements.filter(
                fuel_type=fuel_type, timestamp__gte=timezone.now() - timedelta(hours=4)
            )
            .order_by("-timestamp")
            .first()
        )

    @property
    def status_color(self):
        """Retourne la couleur selon le statut global de la station."""
        essence = self.get_latest_signalement_for_fuel("Essence")
        gazole = self.get_latest_signalement_for_fuel("Gazole")

        signals = [s for s in (essence, gazole) if s]
        if not signals:
            return "gray"

        has_available = any(s.status == "Disponible" for s in signals)
        has_empty = any(s.status == "Épuisé" for s in signals)

        if has_available and has_empty:
            return "yellow"
        if has_available:
            return "green"
        return "red"

    @property
    def has_recent_signalement(self):
        """Vérifie s'il y a un signalement récent (moins de 4h)"""
        return self.signalements.filter(
            timestamp__gte=timezone.now() - timedelta(hours=4)
        ).exists()

    def get_confidence_score(self):
        """Score confiance station (0-100)"""
        four_hours_ago = timezone.now() - timedelta(hours=4)
        recent = self.signalements.filter(
            timestamp__gte=four_hours_ago, fuel_type__in=["Essence", "Gazole"]
        )
        if not recent.exists():
            return 0

        weighted = 0
        total = 0
        for signalement in recent:
            age_minutes = max(
                1, int((timezone.now() - signalement.timestamp).total_seconds() / 60)
            )
            recency_weight = max(1, 240 - age_minutes)
            approval_weight = min(8, signalement.approval_count)
            weighted += recency_weight * approval_weight
            total += recency_weight * 8

        return int((weighted / total) * 100) if total else 0

    def has_conflicting_recent_reports(self):
        """Détecte des statuts contradictoires récents pour un même carburant"""
        two_hours_ago = timezone.now() - timedelta(hours=2)
        for fuel in ["Essence", "Gazole"]:
            statuses = (
                self.signalements.filter(fuel_type=fuel, timestamp__gte=two_hours_ago)
                .values_list("status", flat=True)
                .distinct()
            )
            if len(list(statuses)) > 1:
                return True
        return False


class Signalement(models.Model):
    """Signalement de disponibilité de carburant (stations uniquement)"""

    FUEL_TYPES = [
        ("Essence", "Essence"),
        ("Gazole", "Gazole"),
    ]
    STATUS_CHOICES = [
        ("Disponible", "Disponible"),
        ("Épuisé", "Épuisé"),
    ]

    station = models.ForeignKey(
        Station,
        on_delete=models.CASCADE,
        related_name="signalements",
        verbose_name="Station",
    )
    fuel_type = models.CharField(
        max_length=20, choices=FUEL_TYPES, verbose_name="Type de carburant"
    )
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, verbose_name="Statut"
    )
    timestamp = models.DateTimeField(
        default=timezone.now, verbose_name="Date du signalement"
    )
    approval_count = models.IntegerField(
        default=1, verbose_name="Nombre d'approbations"
    )
    ip = models.GenericIPAddressField(null=True, blank=True, verbose_name="Adresse IP")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="fuel_signalements",
        verbose_name="Utilisateur",
    )
    comment = models.CharField(
        max_length=255, blank=True, default="", verbose_name="Commentaire"
    )

    class Meta:
        verbose_name = "Signalement carburant"
        verbose_name_plural = "Signalements carburant"
        ordering = ["-timestamp"]
        indexes = [
            models.Index(fields=["station", "timestamp"]),
            models.Index(fields=["fuel_type", "status"]),
            models.Index(fields=["timestamp"]),
            models.Index(fields=["ip"]),
        ]

    def is_expired(self):
        """Un signalement expire après 4 heures"""
        return timezone.now() - self.timestamp > timedelta(hours=4)

    def __str__(self):
        return f"{self.station.name} - {self.fuel_type}: {self.status} ({self.approval_count} confirmations)"


class ElectriciteSignalement(models.Model):
    """Signalement d'état électrique pour une zone géographique"""

    STATUS_CHOICES = [
        ("Disponible", "Disponible"),
        ("Coupure", "Coupure"),
        ("Instable", "Instable"),
        ("Retour récent", "Retour récent"),
        ("Épuisé", "Épuisé"),  # compatibilité historique
    ]
    LOAD_LEVELS = [
        ("Faible", "Faible"),
        ("Normal", "Normal"),
        ("Fort", "Fort"),
    ]
    SOURCE_TYPES = [
        ("Ménage", "Ménage"),
        ("Commerçant", "Commerçant"),
        ("Observateur", "Observateur"),
    ]

    zone = models.ForeignKey(
        ZoneElectrique,
        on_delete=models.CASCADE,
        related_name="signalements_electricite",
        verbose_name="Zone",
    )
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, verbose_name="Statut électricité"
    )
    load_level = models.CharField(
        max_length=20,
        choices=LOAD_LEVELS,
        default="Normal",
        verbose_name="Niveau de charge",
    )
    source_type = models.CharField(
        max_length=20,
        choices=SOURCE_TYPES,
        default="Observateur",
        verbose_name="Type de source",
    )
    duration_estimate_minutes = models.PositiveIntegerField(
        default=0, verbose_name="Durée estimée (minutes)"
    )
    timestamp = models.DateTimeField(
        default=timezone.now, verbose_name="Date du signalement"
    )
    approval_count = models.IntegerField(
        default=1, verbose_name="Nombre d'approbations"
    )
    ip = models.GenericIPAddressField(null=True, blank=True, verbose_name="Adresse IP")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="electricity_signalements",
        verbose_name="Utilisateur",
    )
    comment = models.CharField(
        max_length=255, blank=True, default="", verbose_name="Commentaire"
    )

    class Meta:
        verbose_name = "Signalement électricité"
        verbose_name_plural = "Signalements électricité"
        ordering = ["-timestamp"]
        indexes = [
            models.Index(fields=["zone", "timestamp"]),
            models.Index(fields=["status"]),
            models.Index(fields=["timestamp"]),
            models.Index(fields=["ip"]),
        ]

    def is_expired(self):
        return timezone.now() - self.timestamp > timedelta(hours=4)

    def get_contributor_weight(self):
        """Poids du contributeur pour pondérer la confiance"""
        if self.user and self.user.is_authenticated:
            recent = ElectriciteSignalement.objects.filter(
                user=self.user, timestamp__gte=timezone.now() - timedelta(days=30)
            ).count()
            return 1.2 if recent >= 5 else 1.0
        return 1.0

    def __str__(self):
        return f"{self.zone.name} - Électricité: {self.status} ({self.approval_count} confirmations)"


class UserProfile(models.Model):
    """Profil utilisateur étendu avec numéro de téléphone"""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile",
        verbose_name="Utilisateur",
    )
    phone = models.CharField(
        max_length=20,
        unique=True,
        blank=True,
        null=True,
        verbose_name="Numéro de téléphone",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Profil utilisateur"
        verbose_name_plural = "Profils utilisateurs"

    def __str__(self):
        return f"{self.user.username} - {self.phone or 'Pas de téléphone'}"
