"""Central model definitions for the project.

All database models live in this app so schema ownership stays in one place.
Domain apps should import these models and keep their business logic in
selectors/services/API modules.
"""
from datetime import timedelta
from secrets import token_urlsafe

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import F, Q
from django.utils import timezone


def generate_access_token() -> str:
    """Generate a high-entropy URL-safe access token."""
    return token_urlsafe(48)


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Event(TimeStampedModel):
    name = models.CharField(max_length=255)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()

    class Meta:
        ordering = ["-start_time"]
        constraints = [
            models.CheckConstraint(
                condition=Q(end_time__gt=F("start_time")),
                name="core_event_end_time_after_start_time",
            ),
        ]

    def __str__(self) -> str:
        return self.name

    def clean(self) -> None:
        super().clean()
        if self.start_time and self.end_time and self.end_time <= self.start_time:
            raise ValidationError(
                {"end_time": "Event end time must be after start time."}
            )


class Content(TimeStampedModel):
    event = models.ForeignKey(
        Event,
        related_name="contents",
        on_delete=models.CASCADE,
    )
    title = models.CharField(
        max_length=255,
        blank=True,
        help_text="Display name, e.g. 'FOTO+VIDEO'.",
    )
    file_path = models.CharField(max_length=1024)
    file = models.FileField(
        upload_to="contents/%Y/%m/",
        null=True,
        blank=True,
        help_text="Local file (demo mode). Production uses file_path against object storage.",
    )
    cover = models.ImageField(
        upload_to="covers/%Y/%m/",
        null=True,
        blank=True,
        help_text="Preview image shown on the public catalog.",
    )
    price = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Price in IDR (e.g. 4500000 for Rp 4.500.000).",
    )
    duration_limit = models.PositiveIntegerField(help_text="Duration limit in seconds.")

    class Meta:
        indexes = [
            models.Index(fields=["event"], name="core_content_event_idx"),
            models.Index(fields=["file_path"], name="core_content_file_path_idx"),
        ]

    def __str__(self) -> str:
        return self.title or self.file_path

    @property
    def duration_limit_delta(self) -> timedelta:
        return timedelta(seconds=self.duration_limit)


class AccessToken(TimeStampedModel):
    token = models.CharField(
        max_length=128,
        unique=True,
        default=generate_access_token,
    )
    content = models.ForeignKey(
        Content,
        related_name="access_tokens",
        on_delete=models.CASCADE,
    )
    expires_at = models.DateTimeField()
    started_at = models.DateTimeField(null=True, blank=True)
    max_duration = models.PositiveIntegerField(help_text="Maximum duration in seconds.")
    is_revoked = models.BooleanField(default=False)

    class Meta:
        indexes = [
            models.Index(fields=["token"], name="core_access_token_idx"),
            models.Index(fields=["expires_at"], name="core_access_expires_at_idx"),
            models.Index(fields=["is_revoked"], name="core_access_revoked_idx"),
        ]

    def __str__(self) -> str:
        return self.token

    @property
    def max_duration_delta(self) -> timedelta:
        return timedelta(seconds=self.max_duration)

    @property
    def has_started(self) -> bool:
        return self.started_at is not None

    @property
    def effective_expires_at(self):
        if not self.started_at:
            return self.expires_at
        duration_expires_at = self.started_at + self.max_duration_delta
        return min(self.expires_at, duration_expires_at)

    @property
    def is_expired(self) -> bool:
        return timezone.now() >= self.effective_expires_at
