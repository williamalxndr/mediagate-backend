from django.utils import timezone
from rest_framework import status
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.content.selectors import list_contents
from apps.content.services import create_content
from apps.core.models import Content
from common.permissions import IsAdminApiUser

from .serializers import (
    ContentCreateSerializer,
    ContentPublicSerializer,
    ContentSerializer,
)


class ContentListCreateView(APIView):
    """GET /api/contents/ — list all content.
    POST /api/contents/ — create new content (JSON or multipart file upload)."""

    permission_classes = [IsAdminApiUser]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get(self, request):
        contents = list_contents()
        serializer = ContentSerializer(
            contents, many=True, context={"request": request}
        )
        return Response({"results": serializer.data})

    def post(self, request):
        serializer = ContentCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        content = create_content(
            event_id=serializer.validated_data["event_id"],
            duration_limit=serializer.validated_data["duration_limit"],
            file_path=serializer.validated_data.get("file_path") or None,
            file=serializer.validated_data.get("file"),
            title=serializer.validated_data.get("title"),
            cover=serializer.validated_data.get("cover"),
            price=serializer.validated_data.get("price"),
        )
        return Response(
            ContentSerializer(content).data,
            status=status.HTTP_201_CREATED,
        )


class ContentPublicListView(APIView):
    """GET /api/contents/public/ — anonymous catalog of upcoming/live content."""

    authentication_classes = []
    permission_classes = []

    def get(self, request):
        contents = (
            Content.objects.select_related("event")
            .filter(event__end_time__gt=timezone.now())
            .order_by("-event__start_time")
        )
        return Response(
            {
                "results": ContentPublicSerializer(
                    contents, many=True, context={"request": request}
                ).data
            }
        )
