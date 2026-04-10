"""
Utilitaires pour l'application BKO Station
"""

import logging
import math
from datetime import timedelta

from django.core.exceptions import ValidationError
from django.utils import timezone

from .constants import BAMAKO_BOUNDS, DISTANCE_LIMITS, ERROR_MESSAGES, TIME_LIMITS

logger = logging.getLogger(__name__)


def calculate_distance(lat1, lon1, lat2, lon2):
    """
    Calcule la distance en km entre deux points GPS (formule de Haversine)

    Args:
        lat1, lon1: Coordonnées du premier point
        lat2, lon2: Coordonnées du deuxième point

    Returns:
        Distance en km (float)
    """
    try:
        R = 6371  # Rayon de la Terre en km

        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        delta_lat = math.radians(lat2 - lat1)
        delta_lon = math.radians(lon2 - lon1)

        a = (
            math.sin(delta_lat / 2) ** 2
            + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon / 2) ** 2
        )
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

        return R * c
    except Exception as e:
        logger.error(f"Erreur dans calculate_distance: {e}")
        raise ValidationError("Erreur lors du calcul de distance")


def validate_coordinates(lat, lon):
    """
    Valide les coordonnées GPS

    Args:
        lat: Latitude
        lon: Longitude

    Returns:
        Tuple (lat, lon) validé

    Raises:
        ValidationError: Si les coordonnées sont invalides
    """
    try:
        lat = float(lat)
        lon = float(lon)

        if not (-90 <= lat <= 90):
            raise ValidationError("La latitude doit être entre -90 et 90")
        if not (-180 <= lon <= 180):
            raise ValidationError("La longitude doit être entre -180 et 180")

        # Vérifier que les coordonnées sont dans la zone couverte (Bamako)
        validate_bamako_coordinates(lat, lon)

        return lat, lon
    except (TypeError, ValueError):
        raise ValidationError(ERROR_MESSAGES["INVALID_COORDINATES"])


def is_within_bamako_bounds(lat, lon):
    """Vérifie si un point est dans la zone de couverture Bamako."""
    try:
        lat = float(lat)
        lon = float(lon)
    except (TypeError, ValueError):
        return False

    return (
        BAMAKO_BOUNDS["MIN_LAT"] <= lat <= BAMAKO_BOUNDS["MAX_LAT"]
        and BAMAKO_BOUNDS["MIN_LON"] <= lon <= BAMAKO_BOUNDS["MAX_LON"]
    )


def validate_bamako_coordinates(lat, lon):
    """Valide qu'un point GPS appartient à la zone couverte de Bamako."""
    if not is_within_bamako_bounds(lat, lon):
        raise ValidationError(
            "Les coordonnées sont hors de la zone de couverture (Bamako)"
        )
    return float(lat), float(lon)


def validate_radius(radius):
    """
    Valide le rayon de recherche

    Args:
        radius: Rayon en km

    Returns:
        Rayon validé (float)

    Raises:
        ValidationError: Si le rayon est invalide
    """
    try:
        radius = float(radius)
        min_r = DISTANCE_LIMITS["MIN_RADIUS"]
        max_r = DISTANCE_LIMITS["MAX_RADIUS"]

        if not (min_r <= radius <= max_r):
            raise ValidationError(
                ERROR_MESSAGES["INVALID_RADIUS"].format(min=min_r, max=max_r)
            )

        return radius
    except (TypeError, ValueError):
        raise ValidationError(
            ERROR_MESSAGES["INVALID_RADIUS"].format(
                min=DISTANCE_LIMITS["MIN_RADIUS"], max=DISTANCE_LIMITS["MAX_RADIUS"]
            )
        )


def validate_search_query(query):
    """
    Valide la requête de recherche

    Args:
        query: Requête de recherche

    Returns:
        Requête validée (string)

    Raises:
        ValidationError: Si la requête est invalide
    """
    if not query or len(query.strip()) < 2:
        raise ValidationError(ERROR_MESSAGES["INVALID_SEARCH_QUERY"].format(min=2))

    return query.strip()


def get_time_ago_string(timestamp):
    """
    Retourne une chaîne représentant le temps écoulé

    Args:
        timestamp: Timestamp datetime

    Returns:
        String formatée (ex: "Il y a 15 min")
    """
    try:
        delta = timezone.now() - timestamp
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
    except Exception as e:
        logger.error(f"Erreur dans get_time_ago_string: {e}")
        return "Date inconnue"


def is_signalement_expired(timestamp):
    """
    Vérifie si un signalement est expiré

    Args:
        timestamp: Timestamp du signalement

    Returns:
        Boolean
    """
    expiry_hours = TIME_LIMITS["SIGNALEMENT_EXPIRY"]
    expiry_time = timezone.now() - timedelta(hours=expiry_hours)
    return timestamp < expiry_time


def get_user_ip(request):
    """
    Récupère l'adresse IP de l'utilisateur

    Args:
        request: Objet request Django

    Returns:
        Adresse IP (string)
    """
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        ip = x_forwarded_for.split(",")[0]
    else:
        ip = request.META.get("REMOTE_ADDR")
    return ip


def format_error_response(error_code, detail=None):
    """
    Formate une réponse d'erreur standardisée

    Args:
        error_code: Code d'erreur
        detail: Détail optionnel

    Returns:
        Dict formaté
    """
    return {
        "error": error_code,
        "detail": detail or ERROR_MESSAGES.get(error_code, "Erreur inconnue"),
        "timestamp": timezone.now().isoformat(),
    }


def format_success_response(message, data=None):
    """
    Formate une réponse de succès standardisée

    Args:
        message: Message de succès
        data: Données optionnelles

    Returns:
        Dict formaté
    """
    response = {
        "success": True,
        "message": message,
        "timestamp": timezone.now().isoformat(),
    }
    if data:
        response["data"] = data
    return response
