"""
Permissions personnalisées pour l'application BKO Station

Objectif:
- Garder les actions sûres (GET/HEAD/OPTIONS) accessibles à tous.
- Empêcher les modifications directes (PUT/PATCH/DELETE) par les non-staff.
- Autoriser la création (POST) des entités publiques de contribution
  (stations/zones) sans login, tout en laissant les autres écritures staff-only.
"""

from rest_framework import permissions


class IsAdminOrReadOnly(permissions.BasePermission):
    """
    Politique générique:
    - lecture: tout le monde
    - création (POST): autorisée pour tout le monde (soumis au contrôle anti-abus applicatif)
    - modification/suppression: staff uniquement

    Cette règle permet la "suggestion" publique de nouvelles stations/zones
    tout en évitant la modification directe par les non-staff.
    """

    def has_permission(self, request, view):
        # Read-only: accessible à tous
        if request.method in permissions.SAFE_METHODS:
            return True

        # Création de contributions: autorisée même sans authentification
        # (création sera soumise ensuite à validation/admin côté métier).
        if request.method == "POST":
            return True

        # Toute autre action d'écriture (PUT/PATCH/DELETE) réservée au staff
        return bool(request.user and request.user.is_staff)


class IsAdminOrReadOnlyWithPublicCreate(permissions.BasePermission):
    """
    Variante explicite de la règle précédente, à utiliser si vous voulez une
    intention plus lisible dans les ViewSets.
    """

    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True

        if request.method == "POST":
            return True

        return bool(request.user and request.user.is_staff)


class IsOwnerOrReadOnly(permissions.BasePermission):
    """
    Politique propriétaire:
    - lecture: tout le monde
    - écriture: uniquement le propriétaire de l'objet
    """

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        return bool(
            request.user and request.user.is_authenticated and obj.owner == request.user
        )


class IsAuthenticatedOrReadOnlyForSignalement(permissions.BasePermission):
    """
    Politique pour signalements:
    - lecture: accessible à tous
    - création/modification/suppression: requiert auth (et throttling côté vue)
    """

    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return bool(request.user and request.user.is_authenticated)


class IsPublicCreateAdminModify(permissions.BasePermission):
    """
    Permission utilitaire:
    - GET/HEAD/OPTIONS autorisés à tous
    - POST autorisé à tous (ex: proposition de station/zone)
    - autres écritures réservées aux admins/staff
    """

    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        if request.method == "POST":
            return True
        return bool(request.user and request.user.is_staff)
