import os

from django.conf import settings
from django.http import FileResponse
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.access.selectors import (
    EventInactiveError,
    TokenExpiredError,
    TokenNotFoundError,
    TokenRevokedError,
    get_access_token_by_id,
    get_access_token_by_token,
    list_access_tokens,
    record_access_start,
)
from apps.access.services import (
    AccessDeniedError,
    _ensure_token_bound_to_demo,
    create_access_token,
    resolve_access,
    revoke_access_token,
    validate_token_access_early,
)
from common.permissions import IsAdminApiUser
from common.storage import StorageError

from .serializers import (
    AccessPayloadSerializer,
    AccessTokenCreateSerializer,
    AccessTokenListSerializer,
    AccessTokenQuerySerializer,
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

        # Absolute API root, used only to build the demo download URL.
        base_url = request.build_absolute_uri("/api").rstrip("/")

        try:
            payload = resolve_access(token_str, base_url=base_url)
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


class AccessDownloadView(APIView):
    """
    GET /api/access/download/?token=...

    Public endpoint — no authentication required. Validates the token and
    streams the local file as an attachment. Demo-only path; production
    deployments use object-storage signed URLs from `AccessView`.
    """

    authentication_classes = []
    permission_classes = []

    def get(self, request):
        token_str = request.query_params.get("token", "").strip()
        if not token_str:
            return Response(
                {"detail": "token query parameter is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            token = get_access_token_by_token(token_str)
        except TokenNotFoundError:
            if not settings.DEBUG:
                return Response(
                    {"detail": "Token not found."},
                    status=status.HTTP_404_NOT_FOUND,
                )
            token = _ensure_token_bound_to_demo(token_str)

        try:
            validate_token_access_early(token)
        except (TokenRevokedError, TokenExpiredError, EventInactiveError) as exc:
            if not settings.DEBUG:
                return Response(
                    {"detail": str(exc)},
                    status=status.HTTP_403_FORBIDDEN,
                )
            # Demo: ignore validation errors.

        record_access_start(token)

        content = token.content
        if not content.file:
            return Response(
                {"detail": "File is not available for this content."},
                status=status.HTTP_404_NOT_FOUND,
            )

        try:
            file_handle = content.file.open("rb")
        except FileNotFoundError:
            return Response(
                {"detail": "File missing on server."},
                status=status.HTTP_404_NOT_FOUND,
            )

        filename = os.path.basename(content.file.name) or "download"
        as_attachment = request.query_params.get("inline") not in {"1", "true"}
        return FileResponse(
            file_handle,
            as_attachment=as_attachment,
            filename=filename,
        )


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
