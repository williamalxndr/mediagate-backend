from datetime import timedelta

import pytest
from django.core.exceptions import ValidationError
from django.test import SimpleTestCase
from django.utils import timezone

from apps.core.models import AccessToken, Content, Event


class EventModelTests(SimpleTestCase):
    def test_event_end_time_must_be_after_start_time(self):
        start_time = timezone.now()
        event = Event(
            name="Launch",
            start_time=start_time,
            end_time=start_time,
        )

        with pytest.raises(ValidationError):
            event.clean()


class ContentModelTests(SimpleTestCase):
    def test_duration_limit_delta_uses_seconds(self):
        content = Content(file_path="videos/intro.mp4", duration_limit=900)

        assert content.duration_limit_delta == timedelta(seconds=900)


class AccessTokenModelTests(SimpleTestCase):
    def test_token_is_auto_generated_and_unique_per_instance(self):
        first = AccessToken(max_duration=300, expires_at=timezone.now())
        second = AccessToken(max_duration=300, expires_at=timezone.now())

        assert first.token
        assert second.token
        assert first.token != second.token

    def test_effective_expires_at_uses_hard_expiry_before_started(self):
        expires_at = timezone.now() + timedelta(hours=1)
        access_token = AccessToken(max_duration=300, expires_at=expires_at)

        assert not access_token.has_started
        assert access_token.effective_expires_at == expires_at

    def test_effective_expires_at_uses_earliest_started_duration_or_hard_expiry(self):
        started_at = timezone.now()
        expires_at = started_at + timedelta(hours=1)
        access_token = AccessToken(
            max_duration=300,
            expires_at=expires_at,
            started_at=started_at,
        )

        assert access_token.has_started
        assert access_token.effective_expires_at == started_at + timedelta(seconds=300)

    def test_is_expired_uses_effective_expiry(self):
        access_token = AccessToken(
            max_duration=300,
            expires_at=timezone.now() - timedelta(seconds=1),
        )

        assert access_token.is_expired
