"""
Exceptions personnalisées pour l'application BKO Station
"""
from rest_framework.exceptions import APIException
from rest_framework import status


class InvalidCoordinatesError(APIException):
    """Erreur de coordonnées GPS invalides"""
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "Les coordonnées GPS sont invalides"
    default_code = 'invalid_coordinates'


class DuplicateVoteError(APIException):
    """Erreur de vote en doublon"""
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "Vous avez déjà voté pour cette station récemment"
    default_code = 'duplicate_vote'


class StationNotFoundError(APIException):
    """Erreur station non trouvée"""
    status_code = status.HTTP_404_NOT_FOUND
    default_detail = "La station demandée n'existe pas"
    default_code = 'station_not_found'


class InvalidRadiusError(APIException):
    """Erreur rayon invalide"""
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "Le rayon doit être un nombre positif"
    default_code = 'invalid_radius'


class InvalidSearchQueryError(APIException):
    """Erreur requête de recherche invalide"""
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "La requête de recherche doit contenir au moins 2 caractères"
    default_code = 'invalid_search_query'


class RateLimitExceededError(APIException):
    """Erreur limite de requêtes dépassée"""
    status_code = status.HTTP_429_TOO_MANY_REQUESTS
    default_detail = "Trop de requêtes. Veuillez réessayer plus tard"
    default_code = 'rate_limit_exceeded'


class ValidationError(APIException):
    """Erreur de validation générique"""
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "Les données fournies sont invalides"
    default_code = 'validation_error'

    def __init__(self, detail=None, code=None):
        if detail is not None:
            self.detail = detail
        else:
            self.detail = self.default_detail
        self.code = code or self.default_code
