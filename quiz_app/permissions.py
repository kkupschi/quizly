from rest_framework.permissions import BasePermission


class IsOwner(BasePermission):
    """Lässt den Zugriff nur auf eigene Objekte zu."""

    def has_object_permission(self, request, view, obj):
        """Vergleicht den Besitzer des Objekts mit dem angemeldeten User."""
        return obj.owner == request.user
