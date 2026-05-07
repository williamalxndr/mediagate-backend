from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.events.selectors import list_events
from apps.events.services import create_event
from common.permissions import IsAdminApiUser

from .serializers import EventCreateSerializer, EventSerializer


class EventListCreateView(APIView):
    """GET /api/events/ — list all events.
    POST /api/events/ — create a new event."""

    permission_classes = [IsAdminApiUser]

    def get(self, request):
        events = list_events()
        serializer = EventSerializer(events, many=True)
        return Response({"results": serializer.data})

    def post(self, request):
        serializer = EventCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        event = create_event(
            name=serializer.validated_data["name"],
            start_time=serializer.validated_data["start_time"],
            end_time=serializer.validated_data["end_time"],
        )
        return Response(
            EventSerializer(event).data,
            status=status.HTTP_201_CREATED,
        )
