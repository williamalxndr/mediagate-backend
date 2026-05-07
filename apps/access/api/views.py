from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.access.selectors import (
    TokenNotFoundError,
    get_access_token_by_id,
    list_access_tokens,
)
from apps.access.services import (
    AccessDeniedError,
    create_access_token,
    resolve_access,
    revoke_access_token,
)
from common.permissions import IsAdminApiUser
from common.storage import StorageError

from .serializers import (
    AccessPayloadSerializer,
    AccessTokenCreateSerializer,
    AccessTokenListSerializer,
    AccessTokenQuerySerializer,
    RevokeResponseSerializer,
)


# ---- Public access endpoint ----


class AccessView(APIView):
    """
    GET /api/access/?token=...

    Public endpoint — no authentication required.

    Returns a signed S3/MinIO URL and countdown data for the given token.
    On first access, records the download start time atomically.
    """

    authentication_classes = []
    permission_classes = []

    def get(self, request):
        serializer = AccessTokenQuerySerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        token_str = serializer.validated_data["token"]

        try:
            payload = resolve_access(token_str)
        except TokenNotFoundError:
            return Response(
                {"detail": "Token not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        except AccessDeniedError as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_403_FORBIDDEN,
            )
        except StorageError as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        response_serializer = AccessPayloadSerializer(payload)
        return Response(response_serializer.data)


# ---- Admin token management ----


class AccessTokenListCreateView(APIView):
    """
    GET /api/access-tokens/ — list all access tokens (admin only).
    POST /api/access-tokens/ — create a new access token (admin only).
    """

    permission_classes = [IsAdminApiUser]

    def get(self, request):
        tokens = list_access_tokens()
        serializer = AccessTokenListSerializer(tokens, many=True)
        return Response({"results": serializer.data})

    def post(self, request):
        serializer = AccessTokenCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        token = create_access_token(
            content_id=serializer.validated_data["content_id"],
            expires_at=serializer.validated_data["expires_at"],
            max_duration=serializer.validated_data["max_duration"],
        )
        response_data = AccessTokenListSerializer(token).data
        # Add watch_url for create response per API contract
        response_data["watch_url"] = f"/watch?token={token.token}"
        return Response(response_data, status=status.HTTP_201_CREATED)


class AccessTokenRevokeView(APIView):
    """PATCH /api/access-tokens/{id}/revoke/ — revoke an access token (admin only)."""

    permission_classes = [IsAdminApiUser]

    def patch(self, request, pk):
        try:
            token = get_access_token_by_id(pk)
        except TokenNotFoundError:
            return Response(
                {"detail": "Token not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        revoke_access_token(token)
        return Response(
            {"id": token.id, "is_revoked": True},
            status=status.HTTP_200_OK,
        )
