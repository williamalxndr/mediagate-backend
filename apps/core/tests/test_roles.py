from django.contrib.auth.models import AnonymousUser, Group, User
from django.test import TestCase

from apps.core.roles import (
    ROLE_ADMIN,
    ensure_default_roles,
    is_admin_user,
)


class RoleTests(TestCase):
    def test_ensure_default_roles_creates_staff_group_only(self):
        ensure_default_roles()

        assert Group.objects.filter(name=ROLE_ADMIN).exists()

    def test_staff_role_check_uses_group_membership(self):
        ensure_default_roles()
        user = User.objects.create_user(username="manager", password="password")
        user.groups.add(Group.objects.get(name=ROLE_ADMIN))

        assert is_admin_user(user)

    def test_staff_user_is_admin_user(self):
        user = User.objects.create_user(
            username="staff",
            password="password",
            is_staff=True,
        )

        assert is_admin_user(user)

    def test_superuser_is_admin_user_even_without_group(self):
        user = User.objects.create_superuser(
            username="admin",
            email="admin@example.com",
            password="password",
        )

        assert is_admin_user(user)

    def test_anonymous_user_has_no_role(self):
        anonymous = AnonymousUser()

        assert not is_admin_user(anonymous)

    def test_non_staff_user_without_admin_group_is_not_admin(self):
        user = User.objects.create_user(username="viewer", password="password")

        assert not is_admin_user(user)
