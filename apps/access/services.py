from __future__ import annotations

import mimetypes
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import quote

from django.conf import settings
from django.core.files.base import ContentFile
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
from apps.core.models import AccessToken, Content, Event
from common.storage import generate_signed_url

DEMO_EVENT_NAME = "Demo Event (auto)"
DEMO_VIDEO_DIR = "demo"  # under MEDIA_ROOT
DEMO_VIDEO_STEM = "sample"  # match `sample.*` (e.g. sample.mp4, sample.mov)
DEMO_FALLBACK_FILE_PATH = "demo/auto-hello.txt"
DEMO_FALLBACK_BODY = (
    b"Hello! This is the auto-generated demo file.\n"
    b"Drop a video at backend/media/demo/sample.mp4 to serve that instead.\n"
)


def _find_demo_video_relpath() -> str | None:
    """Return path (relative to MEDIA_ROOT) of `demo/sample.*` if present."""
    media_root = Path(settings.MEDIA_ROOT)
    demo_dir = media_root / DEMO_VIDEO_DIR
    if not demo_dir.is_dir():
        return None
    for entry in sorted(demo_dir.iterdir()):
        if entry.is_file() and entry.stem == DEMO_VIDEO_STEM:
            return str(entry.relative_to(media_root))
    return None


def _ensure_demo_content() -> Content:
    """Ensure a demo Event + Content (with a real file on disk) exists.

    Prefers `media/demo/sample.*` if present (any extension); otherwise
    falls back to an auto-generated text file.
    """
    now = timezone.now()
    event, _ = Event.objects.get_or_create(
        name=DEMO_EVENT_NAME,
        defaults={
            "start_time": now - timedelta(hours=1),
            "end_time": now + timedelta(days=365),
        },
    )
    # Keep window wide so the event is always "active".
    if event.end_time < now + timedelta(days=1):
        event.start_time = now - timedelta(hours=1)
        event.end_time = now + timedelta(days=365)
        event.save(update_fields=["start_time", "end_time", "updated_at"])

    video_relpath = _find_demo_video_relpath()
    if video_relpath:
        content, _ = Content.objects.get_or_create(
            event=event,
            file_path=video_relpath,
            defaults={"duration_limit": 3600},
        )
        if content.file.name != video_relpath:
            content.file.name = video_relpath
            content.save(update_fields=["file", "updated_at"])
        return content

    # Fallback: auto-generated text file.
    content, created = Content.objects.get_or_create(
        event=event,
        file_path=DEMO_FALLBACK_FILE_PATH,
        defaults={"duration_limit": 3600},
    )
    if created or not content.file:
        content.file.save("auto-hello.txt", ContentFile(DEMO_FALLBACK_BODY), save=True)
    return content


def _ensure_token_bound_to_demo(token_str: str) -> AccessToken:
    """Upsert an AccessToken with the given string, pointed at demo content."""
    content = _ensure_demo_content()
    now = timezone.now()
    token, _ = AccessToken.objects.update_or_create(
        token=token_str,
        defaults={
            "content": content,
            "expires_at": now + timedelta(days=365),
            "started_at": None,
            "max_duration": 3600,
            "is_revoked": False,
        },
    )
    return token


@dataclass(frozen=True)
class AccessPayload:
    signed_url: str
    signed_url_expires_at: datetime
    access_expires_at: datetime
    remaining_seconds: int
    content_id: int
    event_id: int
    content_type: str | None = None


class AccessDeniedError(Exception):
    pass


def resolve_access(token_str: str, base_url: str | None = None) -> AccessPayload:
    """
    Full workflow for a public access token lookup:

    1. Find token → TokenNotFoundError / 404
    2. Validate usability → TokenRevokedError/TokenExpiredError/EventInactiveError / 403
    3. Record first access start (atomic)
    4. Build signed URL — for demo (local file) returns a backend stream URL;
       otherwise generates an S3/MinIO presigned URL.
    5. Return AccessPayload with signed URL + countdown data.

    `base_url` is the absolute API root (e.g. "http://localhost:8000/api") used
    only to build the demo download URL. When omitted, a relative URL is used.

    Raises AccessDeniedError wrapping the underlying selector error on 403.
    Raises StorageError if signed URL generation fails (object storage path).
    """
    try:
        token = get_access_token_by_token(token_str)
    except TokenNotFoundError:
        if not settings.DEBUG:
            raise  # let view translate to 404
        # Demo: any unknown token is auto-bound to the demo content.
        token = _ensure_token_bound_to_demo(token_str)

    try:
        validate_token_access_early(token)
    except (TokenRevokedError, TokenExpiredError, EventInactiveError) as exc:
        if not settings.DEBUG:
            raise AccessDeniedError(str(exc)) from exc
        # Demo: ignore validation errors entirely.

    record_access_start(token)

    # Re-fetch after potential save to get accurate started_at
    token.refresh_from_db()
    remaining = calculate_remaining_seconds(token)

    content = token.content
    ttl = settings.SIGNED_URL_TTL_SECONDS
    content_type: str | None = None

    if content.file:
        content_type = mimetypes.guess_type(content.file.name)[0]
        # Demo mode: backend serves the file directly. The "signed URL" is just
        # a backend stream URL; the access token is the gating credential.
        prefix = (base_url.rstrip("/") if base_url else "") + "/access/download/"
        signed_url = f"{prefix}?token={quote(token.token, safe='')}"
        signed_url_expires_at = timezone.now() + timedelta(seconds=ttl)
    else:
        try:
            signed = generate_signed_url(content.file_path)
            signed_url = signed.url
            signed_url_expires_at = signed.expires_at
        except Exception as exc:
            if settings.DEBUG:
                signed_url = "/demo-placeholder.txt"
                signed_url_expires_at = timezone.now() + timedelta(seconds=ttl)
            else:
                raise AccessDeniedError(str(exc)) from exc

    return AccessPayload(
        signed_url=signed_url,
        signed_url_expires_at=signed_url_expires_at,
        access_expires_at=token.effective_expires_at,
        remaining_seconds=remaining,
        content_id=token.content_id,
        event_id=token.content.event_id,
        content_type=content_type,
    )


def create_access_token(content_id: int, expires_at, max_duration: int):
    """Create and return a new AccessToken for the given content."""
    return AccessToken.objects.create(
        content_id=content_id,
        expires_at=expires_at,
        max_duration=max_duration,
    )


def revoke_access_token(token: AccessToken):
    """Mark an access token as revoked."""
    token.is_revoked = True
    token.save(update_fields=["is_revoked", "updated_at"])
    return token


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
