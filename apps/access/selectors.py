from __future__ import annotations

from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from apps.core.models import AccessToken, Content


class TokenNotFoundError(Exception):
    pass


class TokenRevokedError(Exception):
    pass


class TokenExpiredError(Exception):
    pass


class EventInactiveError(Exception):
    pass


def get_access_token_by_token(token_str: str) -> AccessToken:
    """Look up an AccessToken by its token string. Raises TokenNotFoundError if missing."""
    try:
        return AccessToken.objects.select_related("content__event").get(token=token_str)
    except AccessToken.DoesNotExist:
        raise TokenNotFoundError("Token not found.")


def validate_token_access(token: AccessToken) -> None:
    """
    Validate that a token can be used right now.

    Raises TokenRevokedError   — token has been manually revoked.
    Raises TokenExpiredError   — token past its effective expiry.
    Raises EventInactiveError  — event not currently active.
    """
    if token.is_revoked:
        raise TokenRevokedError("Token has been revoked.")

    effective = token.effective_expires_at
    if timezone.now() >= effective:
        raise TokenExpiredError("Token has expired.")

    event = token.content.event
    now = timezone.now()
    if not (event.start_time <= now <= event.end_time):
        raise EventInactiveError("Event is not currently active.")


def record_access_start(token: AccessToken) -> None:
    """
    Atomically record started_at on first access.

    Uses select_for_update to prevent race conditions.
    """
    with transaction.atomic():
        # Re-fetch with lock to avoid race condition
        token = AccessToken.objects.select_for_update().get(pk=token.pk)
        if token.started_at is None:
            token.started_at = timezone.now()
            token.save(update_fields=["started_at", "updated_at"])


def calculate_remaining_seconds(token: AccessToken) -> int:
    """Return seconds remaining until effective expiry."""
    delta = token.effective_expires_at - timezone.now()
    return max(0, int(delta.total_seconds()))
