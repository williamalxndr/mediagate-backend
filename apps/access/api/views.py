from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.access.selectors import TokenNotFoundError
from apps.access.services import AccessDeniedError, resolve_access
from common.storage import StorageError

from .serializers import AccessPayloadSerializer, AccessTokenQuerySerializer


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
