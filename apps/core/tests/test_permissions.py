from django.contrib.auth.models import AnonymousUser, Group, User
from django.test import TestCase
from rest_framework.test import APIRequestFactory

from apps.core.roles import ROLE_ADMIN, ensure_default_roles
from common.permissions import IsAdminApiUser


class IsAdminApiUserTests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.permission = IsAdminApiUser()

    def has_permission_for(self, user) -> bool:
        request = self.factory.get("/api/admin/")
        request.user = user
        return self.permission.has_permission(request, None)

    def test_anonymous_user_is_denied(self):
        assert not self.has_permission_for(AnonymousUser())

    def test_non_staff_non_admin_group_user_is_denied(self):
        user = User.objects.create_user(username="viewer", password="password")

        assert not self.has_permission_for(user)

    def test_staff_user_is_allowed(self):
        user = User.objects.create_user(
            username="staff",
            password="password",
            is_staff=True,
        )

        assert self.has_permission_for(user)

    def test_staff_group_user_is_allowed(self):
        ensure_default_roles()
        user = User.objects.create_user(username="manager", password="password")
        user.groups.add(Group.objects.get(name=ROLE_ADMIN))

        assert self.has_permission_for(user)
