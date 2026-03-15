from django.db import models
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
from datetime import timedelta


class Station(models.Model):
    """Station de carburant à Bamako"""
    name = models.CharField(max_length=100, verbose_name="Nom de la station")
    brand = models.CharField(max_length=50, verbose_name="Enseigne (Shell, Total, Oryx, etc.)")
    address = models.CharField(
        max_length=255,
        blank=True,
        default='',
        verbose_name="Adresse"
    )
    latitude = models.FloatField(
        verbose_name="Latitude",
        validators=[MinValueValidator(-90), MaxValueValidator(90)]
    )
    longitude = models.FloatField(
        verbose_name="Longitude",
        validators=[MinValueValidator(-180), MaxValueValidator(180)]
    )
    phone = models.CharField(
        max_length=20,
        blank=True,
        default='',
        verbose_name="Téléphone"
    )
    is_active = models.BooleanField(default=True, verbose_name="Active")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Station"
        verbose_name_plural = "Stations"
        ordering = ['name']
        indexes = [
            models.Index(fields=['brand']),
            models.Index(fields=['is_active']),
            models.Index(fields=['latitude', 'longitude']),
        ]

    def __str__(self):
        return f"{self.name} ({self.brand})"

    def get_latest_signalement(self):
        """Retourne le dernier signalement non expiré (moins de 4h)"""
        return self.signalements.filter(
            timestamp__gte=timezone.now() - timedelta(hours=4)
        ).order_by('-timestamp').first()

    def get_latest_signalement_for_fuel(self, fuel_type):
        """Retourne le dernier signalement non expiré pour un carburant donné"""
        return self.signalements.filter(
            fuel_type=fuel_type,
            timestamp__gte=timezone.now() - timedelta(hours=4)
        ).order_by('-timestamp').first()

    @property
    def status_color(self):
        """Retourne la couleur selon le statut global de la station."""
        essence = self.get_latest_signalement_for_fuel('Essence')
        gazole = self.get_latest_signalement_for_fuel('Gazole')

        signals = [s for s in (essence, gazole) if s]
        if not signals:
            return 'gray'

        has_available = any(s.status == 'Disponible' for s in signals)
        has_empty = any(s.status == 'Épuisé' for s in signals)

        if has_available and has_empty:
            return 'yellow'
        if has_available:
            return 'green'
        return 'red'

    @property
    def has_recent_signalement(self):
        """Vérifie s'il y a un signalement récent (moins de 4h)"""
        return self.signalements.filter(
            timestamp__gte=timezone.now() - timedelta(hours=4)
        ).exists()


class Signalement(models.Model):
    """Signalement de disponibilité de carburant"""
    FUEL_TYPES = [
        ('Essence', 'Essence'),
        ('Gazole', 'Gazole'),
    ]
    STATUS_CHOICES = [
        ('Disponible', 'Disponible'),
        ('Épuisé', 'Épuisé'),
    ]

    station = models.ForeignKey(
        Station,
        on_delete=models.CASCADE,
        related_name='signalements',
        verbose_name="Station"
    )
    fuel_type = models.CharField(max_length=20, choices=FUEL_TYPES, verbose_name="Type de carburant")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, verbose_name="Statut")
    # Use default=timezone.now so tests can override, but still auto-populate in practice
    timestamp = models.DateTimeField(default=timezone.now, verbose_name="Date du signalement")
    approval_count = models.IntegerField(default=1, verbose_name="Nombre d'approbations")
    ip = models.GenericIPAddressField(null=True, blank=True, verbose_name="Adresse IP")
    comment = models.CharField(
        max_length=255,
        blank=True,
        default='',
        verbose_name="Commentaire"
    )

    class Meta:
        verbose_name = "Signalement"
        verbose_name_plural = "Signalements"
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['station', 'timestamp']),
            models.Index(fields=['fuel_type', 'status']),
            models.Index(fields=['timestamp']),
            models.Index(fields=['ip']),
        ]

    def is_expired(self):
        """Un signalement expire après 4 heures"""
        return timezone.now() - self.timestamp > timedelta(hours=4)

    def __str__(self):
        return f"{self.station.name} - {self.fuel_type}: {self.status} ({self.approval_count} confirmations)"
