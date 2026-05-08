"""API tests for events."""

from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from apps.core.models import Event


class EventViewTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin_user = type(
            "AdminUser",
            (),
            {
                "is_authenticated": True,
                "is_staff": True,
            },
        )()
        self.anonymous_user = type(
            "AnonUser",
            (),
            {
                "is_authenticated": False,
            },
        )()
        self.url = reverse("events:event-list-create")

    def _authenticate(self, user):
        self.client.force_authenticate(user=user)

    def test_list_requires_admin(self):
        # Anonymous → 403 (IsAdminApiUser returns False for unauthenticated)
        response = self.client.get(self.url)
        assert response.status_code == status.HTTP_403_FORBIDDEN

        # Non-staff → 403
        non_staff = type(
            "NonStaff",
            (),
            {
                "is_authenticated": True,
                "is_staff": False,
                "is_superuser": False,
                "groups": type(
                    "Groups",
                    (),
                    {
                        "filter": lambda *a, **kw: type(
                            "QS", (), {"exists": lambda *a: False}
                        )()
                    },
                )(),
            },
        )()
        self._authenticate(non_staff)
        response = self.client.get(self.url)
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_list_returns_events(self):
        self._authenticate(self.admin_user)
        Event.objects.create(
            name="Launch",
            start_time=timezone.now(),
            end_time=timezone.now() + timedelta(hours=2),
        )

        response = self.client.get(self.url)

        assert response.status_code == status.HTTP_200_OK
        assert "results" in response.data
        assert len(response.data["results"]) == 1
        assert response.data["results"][0]["name"] == "Launch"

    def test_list_returns_empty_when_no_events(self):
        self._authenticate(self.admin_user)
        response = self.client.get(self.url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["results"] == []

    def test_create_requires_admin(self):
        payload = {
            "name": "New Event",
            "start_time": timezone.now().isoformat(),
            "end_time": (timezone.now() + timedelta(hours=2)).isoformat(),
        }
        response = self.client.post(self.url, payload, format="json")
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_create_event_returns_201(self):
        self._authenticate(self.admin_user)
        payload = {
            "name": "New Event",
            "start_time": timezone.now().isoformat(),
            "end_time": (timezone.now() + timedelta(hours=2)).isoformat(),
        }

        response = self.client.post(self.url, payload, format="json")

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["name"] == "New Event"
        assert Event.objects.filter(name="New Event").exists()

    def test_create_event_invalid_times_returns_400(self):
        self._authenticate(self.admin_user)
        payload = {
            "name": "Bad Event",
            "start_time": timezone.now().isoformat(),
            "end_time": (timezone.now() - timedelta(hours=1)).isoformat(),
        }

        response = self.client.post(self.url, payload, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "end_time" in response.data
