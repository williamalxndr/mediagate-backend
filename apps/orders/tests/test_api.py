"""API tests for the orders endpoints."""

from datetime import timedelta

from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from apps.core.models import Content, Event, Order


def make_admin():
    return type("AdminUser", (), {"is_authenticated": True, "is_staff": True})()


@override_settings(
    REST_FRAMEWORK={
        "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
        "DEFAULT_PARSER_CLASSES": ["rest_framework.parsers.JSONParser"],
    }
)
class OrderCreateViewTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = reverse("orders:order-create")
        self.event = Event.objects.create(
            name="Test Event",
            start_time=timezone.now(),
            end_time=timezone.now() + timedelta(hours=2),
        )
        self.content = Content.objects.create(
            event=self.event,
            file_path="videos/test.mp4",
            duration_limit=1800,
        )

    def test_anonymous_creates_order(self):
        payload = {
            "customer_name": "Budi Santoso",
            "whatsapp_number": "081234567890",
            "content_id": self.content.id,
        }
        response = self.client.post(self.url, payload, format="json")
        assert response.status_code == status.HTTP_201_CREATED
        order = Order.objects.get(pk=response.data["id"])
        assert order.whatsapp_e164 == "6281234567890"
        assert order.status == Order.STATUS_PENDING
        assert order.content_id == self.content.id

    def test_international_number_kept_as_is(self):
        payload = {
            "customer_name": "Jane",
            "whatsapp_number": "+62 812-3456-7890",
            "content_id": self.content.id,
        }
        response = self.client.post(self.url, payload, format="json")
        assert response.status_code == status.HTTP_201_CREATED
        order = Order.objects.get(pk=response.data["id"])
        assert order.whatsapp_e164 == "6281234567890"

    def test_short_number_rejected(self):
        payload = {
            "customer_name": "X",
            "whatsapp_number": "123",
            "content_id": self.content.id,
        }
        response = self.client.post(self.url, payload, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "whatsapp_number" in response.data


class OrderAdminViewTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = make_admin()
        self.event = Event.objects.create(
            name="Test Event",
            start_time=timezone.now(),
            end_time=timezone.now() + timedelta(hours=2),
        )
        self.content = Content.objects.create(
            event=self.event,
            file_path="videos/test.mp4",
            duration_limit=1800,
        )
        self.order = Order.objects.create(
            customer_name="Budi",
            whatsapp_number="081234567890",
            whatsapp_e164="6281234567890",
            content=self.content,
        )

    def _auth(self):
        self.client.force_authenticate(user=self.admin)

    def test_list_requires_admin(self):
        response = self.client.get(reverse("orders:order-admin-list"))
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_list_returns_orders(self):
        self._auth()
        response = self.client.get(reverse("orders:order-admin-list"))
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) == 1
        assert response.data["results"][0]["whatsapp_e164"] == "6281234567890"

    def test_list_filters_by_status(self):
        self._auth()
        Order.objects.create(
            customer_name="Other",
            whatsapp_number="081111111111",
            whatsapp_e164="6281111111111",
            status=Order.STATUS_CANCELLED,
        )
        response = self.client.get(
            reverse("orders:order-admin-list"), {"status": "pending"}
        )
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) == 1
        assert response.data["results"][0]["status"] == "pending"

    def test_issue_token_creates_token_and_fulfills(self):
        self._auth()
        url = reverse("orders:order-issue-token", args=[self.order.id])
        response = self.client.post(url, {}, format="json")
        assert response.status_code == status.HTTP_201_CREATED
        self.order.refresh_from_db()
        assert self.order.status == Order.STATUS_FULFILLED
        assert self.order.access_token is not None
        assert self.order.access_token.content_id == self.content.id

    def test_issue_token_twice_rejected(self):
        self._auth()
        url = reverse("orders:order-issue-token", args=[self.order.id])
        first = self.client.post(url, {}, format="json")
        assert first.status_code == status.HTTP_201_CREATED
        second = self.client.post(url, {}, format="json")
        assert second.status_code == status.HTTP_409_CONFLICT

    def test_regenerate_token_creates_new_token_and_revokes_old(self):
        self._auth()
        issue_url = reverse("orders:order-issue-token", args=[self.order.id])
        self.client.post(issue_url, {}, format="json")
        self.order.refresh_from_db()
        old_token = self.order.access_token
        regen_url = reverse("orders:order-regenerate-token", args=[self.order.id])
        response = self.client.post(regen_url, {}, format="json")
        assert response.status_code == status.HTTP_201_CREATED
        self.order.refresh_from_db()
        assert self.order.access_token_id != old_token.id
        assert self.order.access_token.content_id == self.content.id
        old_token.refresh_from_db()
        assert old_token.is_revoked is True

    def test_regenerate_pending_order_rejected(self):
        self._auth()
        url = reverse("orders:order-regenerate-token", args=[self.order.id])
        response = self.client.post(url, {}, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_cancel_pending_order(self):
        self._auth()
        url = reverse("orders:order-cancel", args=[self.order.id])
        response = self.client.patch(url, {}, format="json")
        assert response.status_code == status.HTTP_200_OK
        self.order.refresh_from_db()
        assert self.order.status == Order.STATUS_CANCELLED

    def test_cancel_fulfilled_order_rejected(self):
        self._auth()
        issue_url = reverse("orders:order-issue-token", args=[self.order.id])
        self.client.post(issue_url, {}, format="json")
        cancel_url = reverse("orders:order-cancel", args=[self.order.id])
        response = self.client.patch(cancel_url, {}, format="json")
        assert response.status_code == status.HTTP_409_CONFLICT

    def test_detail_returns_order(self):
        self._auth()
        url = reverse("orders:order-admin-detail", args=[self.order.id])
        response = self.client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data["customer_name"] == "Budi"
