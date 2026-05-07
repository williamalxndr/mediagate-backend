from apps.core.roles import is_admin_user


def get_me_payload(user) -> dict:
    """Return a serializable payload for the current admin user."""
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email or "",
        "is_staff": is_admin_user(user),
    }
