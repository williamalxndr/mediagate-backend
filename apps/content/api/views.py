from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.content.selectors import list_contents
from apps.content.services import create_content
from common.permissions import IsAdminApiUser

from .serializers import ContentCreateSerializer, ContentSerializer


class ContentListCreateView(APIView):
    """GET /api/contents/ — list all content.
    POST /api/contents/ — create new content."""

    permission_classes = [IsAdminApiUser]

    def get(self, request):
        contents = list_contents()
        serializer = ContentSerializer(contents, many=True)
        return Response({"results": serializer.data})

    def post(self, request):
        serializer = ContentCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        content = create_content(
            event_id=serializer.validated_data["event_id"],
            file_path=serializer.validated_data["file_path"],
            duration_limit=serializer.validated_data["duration_limit"],
        )
        return Response(
            ContentSerializer(content).data,
            status=status.HTTP_201_CREATED,
        )
