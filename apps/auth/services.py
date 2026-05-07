from django.contrib.auth import authenticate

from apps.core.roles import is_admin_user


class AuthenticationError(Exception):
    pass


class NonAdminError(Exception):
    pass


def authenticate_admin(request, username: str, password: str):
    """
    Authenticate an admin user by username and password.

    Returns the authenticated user on success.
    Raises AuthenticationError on wrong credentials.
    Raises NonAdminError if credentials are valid but user is not an admin.
    """
    user = authenticate(request=request, username=username, password=password)
    if user is None:
        raise AuthenticationError("Invalid username or password.")
    if not is_admin_user(user):
        raise NonAdminError("User is not an admin.")
    return user
