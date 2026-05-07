from django.contrib.auth import login, logout
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.auth.selectors import get_me_payload
from apps.auth.services import AuthenticationError, NonAdminError, authenticate_admin

from .serializers import LoginSerializer, MeSerializer


class LoginView(APIView):
    """POST /api/auth/login/ — authenticate an admin user."""

    authentication_classes = []
    permission_classes = []

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            user = authenticate_admin(
                request,
                username=serializer.validated_data["username"],
                password=serializer.validated_data["password"],
            )
        except AuthenticationError:
            return Response(
                {"detail": "Invalid username or password."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except NonAdminError:
            return Response(
                {"detail": "User is not an admin."},
                status=status.HTTP_403_FORBIDDEN,
            )
        login(request, user)
        return Response(MeSerializer(get_me_payload(user)).data)


class LogoutView(APIView):
    """POST /api/auth/logout/ — end the admin session."""

    def post(self, request):
        logout(request)
        return Response(status=status.HTTP_204_NO_CONTENT)


class MeView(APIView):
    """GET /api/auth/me/ — return the authenticated admin's profile."""

    def get(self, request):
        if not request.user.is_authenticated:
            return Response(
                {"detail": "Authentication required."},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        return Response(MeSerializer(get_me_payload(request.user)).data)
