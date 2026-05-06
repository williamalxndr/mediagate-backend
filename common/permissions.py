from rest_framework.permissions import BasePermission

from apps.core.roles import is_admin_user


class IsAdminApiUser(BasePermission):
    message = "Admin API access requires an authenticated admin user."

    def has_permission(self, request, view) -> bool:
        return is_admin_user(request.user)
