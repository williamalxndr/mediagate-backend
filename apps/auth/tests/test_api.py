from unittest.mock import MagicMock

import pytest
from rest_framework import status
from rest_framework.test import APIRequestFactory

from apps.auth.api.views import LoginView, LogoutView, MeView
from apps.auth.selectors import get_me_payload
from apps.auth.services import AuthenticationError, NonAdminError, authenticate_admin


class AuthenticateAdminTests:
    def test_returns_user_on_valid_admin_credentials(self):
        user = MagicMock()
        user.is_authenticated = True

        import apps.auth.services as services_module

        original_authenticate = services_module.authenticate
        original_is_admin = services_module.is_admin_user
        services_module.authenticate = MagicMock(return_value=user)
        services_module.is_admin_user = MagicMock(return_value=True)

        try:
            request = MagicMock()
            result = authenticate_admin(request, "admin", "password123")
            assert result == user
            services_module.authenticate.assert_called_once_with(
                request=request, username="admin", password="password123"
            )
            services_module.is_admin_user.assert_called_once_with(user)
        finally:
            services_module.authenticate = original_authenticate
            services_module.is_admin_user = original_is_admin

    def test_raises_authentication_error_on_wrong_password(self):
        import apps.auth.services as services_module

        original = services_module.authenticate
        services_module.authenticate = MagicMock(return_value=None)

        try:
            request = MagicMock()
            with pytest.raises(AuthenticationError):
                authenticate_admin(request, "admin", "wrongpassword")
        finally:
            services_module.authenticate = original

    def test_raises_non_admin_error_for_non_admin_user(self):
        user = MagicMock()
        user.is_authenticated = True

        import apps.auth.services as services_module

        original_auth = services_module.authenticate
        original_is_admin = services_module.is_admin_user
        services_module.authenticate = MagicMock(return_value=user)
        services_module.is_admin_user = MagicMock(return_value=False)

        try:
            request = MagicMock()
            with pytest.raises(NonAdminError):
                authenticate_admin(request, "viewer", "password123")
        finally:
            services_module.authenticate = original_auth
            services_module.is_admin_user = original_is_admin


class GetMePayloadTests:
    def test_returns_correct_payload(self):
        user = MagicMock()
        user.id = 42
        user.username = "testuser"
        user.email = "test@example.com"

        import apps.auth.selectors as selectors_module

        original = selectors_module.is_admin_user
        selectors_module.is_admin_user = MagicMock(return_value=True)

        try:
            payload = get_me_payload(user)
            assert payload == {
                "id": 42,
                "username": "testuser",
                "email": "test@example.com",
                "is_staff": True,
            }
        finally:
            selectors_module.is_admin_user = original


class LoginViewTests:
    def setup_method(self):
        self.factory = APIRequestFactory()
        self.view = LoginView.as_view()

    def test_login_ok_returns_200(self):
        user = MagicMock()
        user.id = 1
        user.username = "admin"
        user.email = "admin@example.com"

        import apps.auth.api.views as views_module
        import apps.auth.services as services_module
        import apps.auth.selectors as selectors_module

        original_login = views_module.login
        original_auth = services_module.authenticate
        original_is_admin = services_module.is_admin_user
        original_payload = selectors_module.get_me_payload

        views_module.login = MagicMock()
        services_module.authenticate = MagicMock(return_value=user)
        services_module.is_admin_user = MagicMock(return_value=True)
        selectors_module.get_me_payload = MagicMock(
            return_value={
                "id": 1,
                "username": "admin",
                "email": "admin@example.com",
                "is_staff": True,
            }
        )

        try:
            request = self.factory.post(
                "/api/auth/login/",
                {"username": "admin", "password": "password123"},
                format="json",
            )
            response = self.view(request)
            assert response.status_code == status.HTTP_200_OK
            assert response.data["username"] == "admin"
            assert response.data["is_staff"] is True
            views_module.login.assert_called_once()
        finally:
            views_module.login = original_login
            services_module.authenticate = original_auth
            services_module.is_admin_user = original_is_admin
            selectors_module.get_me_payload = original_payload

    def test_login_wrong_password_returns_400(self):
        import apps.auth.services as services_module

        original = services_module.authenticate
        services_module.authenticate = MagicMock(
            side_effect=AuthenticationError("Invalid")
        )

        try:
            request = self.factory.post(
                "/api/auth/login/",
                {"username": "admin", "password": "wrong"},
                format="json",
            )
            response = self.view(request)
            assert response.status_code == status.HTTP_400_BAD_REQUEST
        finally:
            services_module.authenticate = original

    def test_login_non_admin_returns_403(self):
        user = MagicMock()
        user.is_authenticated = True

        import apps.auth.services as services_module

        original_auth = services_module.authenticate
        original_is_admin = services_module.is_admin_user

        services_module.authenticate = MagicMock(return_value=user)
        services_module.is_admin_user = MagicMock(
            side_effect=NonAdminError("Not admin")
        )

        try:
            request = self.factory.post(
                "/api/auth/login/",
                {"username": "viewer", "password": "password123"},
                format="json",
            )
            response = self.view(request)
            assert response.status_code == status.HTTP_403_FORBIDDEN
        finally:
            services_module.authenticate = original_auth
            services_module.is_admin_user = original_is_admin

    def test_login_missing_fields_returns_400(self):
        request = self.factory.post(
            "/api/auth/login/",
            {"username": "admin"},
            format="json",
        )
        response = self.view(request)
        assert response.status_code == status.HTTP_400_BAD_REQUEST


class LogoutViewTests:
    def setup_method(self):
        self.factory = APIRequestFactory()
        self.view = LogoutView.as_view()

    def test_logout_returns_204(self):
        import apps.auth.api.views as views_module

        original_logout = views_module.logout
        views_module.logout = MagicMock()

        try:
            request = self.factory.post("/api/auth/logout/")
            response = self.view(request)
            assert response.status_code == status.HTTP_204_NO_CONTENT
            views_module.logout.assert_called_once()
        finally:
            views_module.logout = original_logout


class MeViewTests:
    def setup_method(self):
        self.factory = APIRequestFactory()
        self.view = MeView.as_view()

    def test_me_returns_200_for_authenticated_admin(self):
        user = MagicMock()
        user.is_authenticated = True
        user.id = 1
        user.username = "admin"
        user.email = "admin@example.com"

        import apps.auth.selectors as selectors_module

        original = selectors_module.get_me_payload
        selectors_module.get_me_payload = MagicMock(
            return_value={
                "id": 1,
                "username": "admin",
                "email": "admin@example.com",
                "is_staff": True,
            }
        )

        try:
            request = self.factory.get("/api/auth/me/")
            request.user = user
            response = self.view(request)
            assert response.status_code == status.HTTP_200_OK
            assert response.data["username"] == "admin"
        finally:
            selectors_module.get_me_payload = original

    def test_me_returns_401_for_anonymous_user(self):
        request = self.factory.get("/api/auth/me/")
        request.user = MagicMock(is_authenticated=False)
        response = self.view(request)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
