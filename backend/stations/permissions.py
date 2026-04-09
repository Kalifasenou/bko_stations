"""
Permissions personnalisées pour l'application BKO Station
"""
from rest_framework import permissions


class IsAdminOrReadOnly(permissions.BasePermission):
    """
    Permission personnalisée:
    - Les admins peuvent faire toutes les opérations
    - Les autres utilisateurs ne peuvent que lire
    """
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user and request.user.is_staff


class IsOwnerOrReadOnly(permissions.BasePermission):
    """
    Permission personnalisée:
    - Les propriétaires peuvent modifier leurs objets
    - Les autres utilisateurs ne peuvent que lire
    """
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        return obj.owner == request.user


class IsAuthenticatedOrReadOnlyForSignalement(permissions.BasePermission):
    """
    Permission pour les signalements:
    - Lecture: accessible à tous (y compris anonymes)
    - Écriture (POST): nécessite authentification
    - Le rate limiting est géré par les throttle classes
    """
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user and request.user.is_authenticated
