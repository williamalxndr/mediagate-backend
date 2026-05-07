"""API tests for content."""
from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from apps.core.models import Content, Event


def make_admin():
    return type("AdminUser", (), {"is_authenticated": True, "is_staff": True})()


class ContentViewTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = make_admin()
        self.url = reverse("content:content-list-create")
        self.event = Event.objects.create(
            name="Test Event",
            start_time=timezone.now(),
            end_time=timezone.now() + timedelta(hours=2),
        )

    def _auth(self):
        self.client.force_authenticate(user=self.admin)

    def test_list_requires_admin(self):
        response = self.client.get(self.url)
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_list_returns_contents(self):
        self._auth()
        Content.objects.create(
            event=self.event,
            file_path="videos/intro.mp4",
            duration_limit=1800,
        )

        response = self.client.get(self.url)

        assert response.status_code == status.HTTP_200_OK
        assert "results" in response.data
        assert len(response.data["results"]) == 1
        assert response.data["results"][0]["file_path"] == "videos/intro.mp4"
        assert response.data["results"][0]["event_id"] == self.event.id

    def test_list_returns_empty_when_no_content(self):
        self._auth()
        response = self.client.get(self.url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["results"] == []

    def test_create_requires_admin(self):
        payload = {
            "event_id": self.event.id,
            "file_path": "videos/intro.mp4",
            "duration_limit": 1800,
        }
        response = self.client.post(self.url, payload, format="json")
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_create_content_returns_201(self):
        self._auth()
        payload = {
            "event_id": self.event.id,
            "file_path": "videos/intro.mp4",
            "duration_limit": 1800,
        }

        response = self.client.post(self.url, payload, format="json")

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["file_path"] == "videos/intro.mp4"
        assert response.data["event_id"] == self.event.id
        assert Content.objects.filter(file_path="videos/intro.mp4").exists()

    def test_create_content_invalid_event_returns_400(self):
        self._auth()
        payload = {
            "event_id": 99999,
            "file_path": "videos/intro.mp4",
            "duration_limit": 1800,
        }

        response = self.client.post(self.url, payload, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "event_id" in response.data

    def test_create_content_missing_fields_returns_400(self):
        self._auth()
        response = self.client.post(self.url, {}, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
