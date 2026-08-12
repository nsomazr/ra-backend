from rest_framework.permissions import SAFE_METHODS, BasePermission


class IsNotViewer(BasePermission):
    """Block CBM Viewer (and any read-only role) from write operations."""

    message = "View-only accounts cannot change assessment data."

    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True
        user = request.user
        if not user or not user.is_authenticated:
            return False
        return getattr(user, "role", None) != "CBM_VIEWER"


class IsAdminRole(BasePermission):
    def has_permission(self, request, view):
        user = request.user
        return bool(
            user
            and user.is_authenticated
            and (user.is_staff or getattr(user, "role", None) == "ADMIN")
        )
