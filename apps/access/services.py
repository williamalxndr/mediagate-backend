from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from django.utils import timezone

from apps.access.selectors import (
    EventInactiveError,
    TokenExpiredError,
    TokenNotFoundError,
    TokenRevokedError,
    calculate_remaining_seconds,
    get_access_token_by_token,
    record_access_start,
)
from common.storage import StorageError, generate_signed_url


@dataclass(frozen=True)
class AccessPayload:
    signed_url: str
    signed_url_expires_at: datetime
    access_expires_at: datetime
    remaining_seconds: int
    content_id: int
    event_id: int


class AccessDeniedError(Exception):
    pass


def resolve_access(token_str: str) -> AccessPayload:
    """
    Full workflow for a public access token lookup:

    1. Find token → TokenNotFoundError / 404
    2. Validate usability → TokenRevokedError/TokenExpiredError/EventInactiveError / 403
    3. Record first access start (atomic)
    4. Generate signed URL for the content file
    5. Return AccessPayload with signed URL + countdown data

    Raises AccessDeniedError wrapping the underlying selector error on 403.
    Raises StorageError if signed URL generation fails.
    """
    try:
        token = get_access_token_by_token(token_str)
    except TokenNotFoundError:
        raise  # let view translate to 404

    try:
        validate_token_access_early(token)
    except (TokenRevokedError, TokenExpiredError, EventInactiveError) as exc:
        raise AccessDeniedError(str(exc)) from exc

    record_access_start(token)

    # Re-fetch after potential save to get accurate started_at
    token.refresh_from_db()
    remaining = calculate_remaining_seconds(token)

    try:
        signed = generate_signed_url(token.content.file_path)
    except StorageError as exc:
        raise AccessDeniedError(str(exc)) from exc

    return AccessPayload(
        signed_url=signed.url,
        signed_url_expires_at=signed.expires_at,
        access_expires_at=token.effective_expires_at,
        remaining_seconds=remaining,
        content_id=token.content_id,
        event_id=token.content.event_id,
    )


def validate_token_access_early(token) -> None:
    """
    Pre-emptive validation (without locking).

    Checks revoked, expired, and event active window.
    Raises TokenRevokedError / TokenExpiredError / EventInactiveError.
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
