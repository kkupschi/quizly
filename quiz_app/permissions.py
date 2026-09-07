from rest_framework.permissions import BasePermission


class IsOwner(BasePermission):
    """Grants access to own objects only."""

    def has_object_permission(self, request, view, obj):
        """Compares the owner of the object with the current user."""
        return obj.owner == request.user
