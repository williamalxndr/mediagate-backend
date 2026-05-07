"""API tests for the public access endpoint."""
from datetime import timedelta
from unittest.mock import MagicMock, patch

import pytest
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from apps.access.selectors import TokenNotFoundError
from apps.access.services import AccessDeniedError, AccessPayload
from apps.core.models import AccessToken, Content, Event


class AccessViewTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.event = Event.objects.create(
            name="Live Event",
            start_time=timezone.now() - timedelta(hours=1),
            end_time=timezone.now() + timedelta(hours=2),
        )
        self.content = Content.objects.create(
            event=self.event,
            file_path="videos/live.mp4",
            duration_limit=1800,
        )
        self.token = AccessToken.objects.create(
            content=self.content,
            expires_at=timezone.now() + timedelta(hours=1),
            max_duration=1800,
        )
        self.url = reverse("access:access")

    def test_missing_token_returns_400(self):
        response = self.client.get(self.url)
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_unknown_token_returns_404(self):
        response = self.client.get(self.url, {"token": "nonexistent"})
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.data["detail"] == "Token not found."

    def test_revoked_token_returns_403(self):
        self.token.is_revoked = True
        self.token.save()

        response = self.client.get(self.url, {"token": self.token.token})
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert "revoked" in response.data["detail"].lower()

    def test_expired_token_returns_403(self):
        self.token.expires_at = timezone.now() - timedelta(minutes=1)
        self.token.save()

        response = self.client.get(self.url, {"token": self.token.token})
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert "expired" in response.data["detail"].lower()

    def test_event_not_started_returns_403(self):
        self.event.start_time = timezone.now() + timedelta(hours=1)
        self.event.end_time = timezone.now() + timedelta(hours=3)
        self.event.save()

        response = self.client.get(self.url, {"token": self.token.token})
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert "active" in response.data["detail"].lower()

    def test_event_ended_returns_403(self):
        self.event.end_time = timezone.now() - timedelta(minutes=1)
        self.event.save()

        response = self.client.get(self.url, {"token": self.token.token})
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_valid_token_returns_signed_url_and_countdown(self):
        mock_payload = AccessPayload(
            signed_url="https://storage.example.com/videos/live.mp4?signature=abc",
            signed_url_expires_at=timezone.now() + timedelta(minutes=5),
            access_expires_at=timezone.now() + timedelta(hours=1),
            remaining_seconds=3600,
            content_id=self.content.id,
            event_id=self.event.id,
        )

        with patch("apps.access.api.views.resolve_access", return_value=mock_payload):
            response = self.client.get(self.url, {"token": self.token.token})

        assert response.status_code == status.HTTP_200_OK
        assert "signed_url" in response.data
        assert response.data["remaining_seconds"] == 3600
        assert response.data["content"]["id"] == self.content.id
        assert response.data["content"]["event_id"] == self.event.id

