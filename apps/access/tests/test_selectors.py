"""Selector unit tests for access tokens."""
from datetime import timedelta

import pytest
from django.test import TestCase
from django.utils import timezone

from apps.access.selectors import (
    EventInactiveError,
    TokenExpiredError,
    TokenNotFoundError,
    TokenRevokedError,
    calculate_remaining_seconds,
    get_access_token_by_token,
    validate_token_access,
)
from apps.core.models import AccessToken, Content, Event


class GetAccessTokenByTokenTests(TestCase):
    def test_returns_token_when_found(self):
        event = Event.objects.create(
            name="Test Event",
            start_time=timezone.now() - timedelta(hours=1),
            end_time=timezone.now() + timedelta(hours=2),
        )
        content = Content.objects.create(
            event=event,
            file_path="videos/test.mp4",
            duration_limit=300,
        )
        token = AccessToken.objects.create(
            content=content,
            expires_at=timezone.now() + timedelta(hours=1),
            max_duration=300,
        )

        result = get_access_token_by_token(token.token)
        assert result.pk == token.pk

    def test_raises_token_not_found_for_unknown_token(self):
        with pytest.raises(TokenNotFoundError):
            get_access_token_by_token("nonexistent-token-value")


class ValidateTokenAccessTests(TestCase):
    def test_raises_revoked_error_when_revoked(self):
        event = Event.objects.create(
            name="Test Event",
            start_time=timezone.now() - timedelta(hours=1),
            end_time=timezone.now() + timedelta(hours=2),
        )
        content = Content.objects.create(
            event=event,
            file_path="videos/test.mp4",
            duration_limit=300,
        )
        token = AccessToken.objects.create(
            content=content,
            expires_at=timezone.now() + timedelta(hours=1),
            max_duration=300,
            is_revoked=True,
        )

        with pytest.raises(TokenRevokedError):
            validate_token_access(token)

    def test_raises_expired_error_when_past_effective_expiry(self):
        event = Event.objects.create(
            name="Test Event",
            start_time=timezone.now() - timedelta(hours=1),
            end_time=timezone.now() + timedelta(hours=2),
        )
        content = Content.objects.create(
            event=event,
            file_path="videos/test.mp4",
            duration_limit=300,
        )
        token = AccessToken.objects.create(
            content=content,
            expires_at=timezone.now() - timedelta(minutes=5),
            max_duration=300,
        )

        with pytest.raises(TokenExpiredError):
            validate_token_access(token)

    def test_raises_inactive_error_when_event_not_started(self):
        event = Event.objects.create(
            name="Test Event",
            start_time=timezone.now() + timedelta(hours=1),
            end_time=timezone.now() + timedelta(hours=3),
        )
        content = Content.objects.create(
            event=event,
            file_path="videos/test.mp4",
            duration_limit=300,
        )
        token = AccessToken.objects.create(
            content=content,
            expires_at=timezone.now() + timedelta(hours=2),
            max_duration=300,
        )

        with pytest.raises(EventInactiveError):
            validate_token_access(token)

    def test_passes_for_valid_token(self):
        event = Event.objects.create(
            name="Test Event",
            start_time=timezone.now() - timedelta(hours=1),
            end_time=timezone.now() + timedelta(hours=2),
        )
        content = Content.objects.create(
            event=event,
            file_path="videos/test.mp4",
            duration_limit=300,
        )
        token = AccessToken.objects.create(
            content=content,
            expires_at=timezone.now() + timedelta(hours=1),
            max_duration=300,
        )

        # Should not raise
        validate_token_access(token)


class CalculateRemainingSecondsTests(TestCase):
    def test_returns_positive_seconds_when_not_expired(self):
        event = Event.objects.create(
            name="Test Event",
            start_time=timezone.now() - timedelta(hours=1),
            end_time=timezone.now() + timedelta(hours=2),
        )
        content = Content.objects.create(
            event=event,
            file_path="videos/test.mp4",
            duration_limit=3600,
        )
        token = AccessToken.objects.create(
            content=content,
            expires_at=timezone.now() + timedelta(seconds=600),
            max_duration=3600,
        )

        remaining = calculate_remaining_seconds(token)
        assert 590 < remaining <= 600

    def test_returns_zero_when_expired(self):
        event = Event.objects.create(
            name="Test Event",
            start_time=timezone.now() - timedelta(hours=1),
            end_time=timezone.now() + timedelta(hours=2),
        )
        content = Content.objects.create(
            event=event,
            file_path="videos/test.mp4",
            duration_limit=300,
        )
        token = AccessToken.objects.create(
            content=content,
            expires_at=timezone.now() - timedelta(seconds=10),
            max_duration=300,
        )

        assert calculate_remaining_seconds(token) == 0
