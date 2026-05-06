from django.contrib.auth.models import Group

ROLE_ADMIN = "admin"

ROLE_CHOICES = (ROLE_ADMIN,)


def ensure_default_roles() -> None:
    for role in ROLE_CHOICES:
        Group.objects.get_or_create(name=role)


def user_has_role(user, role: str) -> bool:
    if not user or not user.is_authenticated:
        return False
    if role == ROLE_ADMIN and (user.is_staff or user.is_superuser):
        return True
    return user.groups.filter(name=role).exists()


def is_admin_user(user) -> bool:
    return user_has_role(user, ROLE_ADMIN)
