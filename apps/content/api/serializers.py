from rest_framework import serializers

from apps.core.models import Content, Event


class ContentSerializer(serializers.ModelSerializer):
    event_id = serializers.IntegerField(source="event.id", read_only=True)

    class Meta:
        model = Content
        fields = [
            "id",
            "event_id",
            "file_path",
            "duration_limit",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class ContentCreateSerializer(serializers.Serializer):
    event_id = serializers.IntegerField()
    file_path = serializers.CharField(max_length=1024)
    duration_limit = serializers.IntegerField(min_value=1)

    def validate_event_id(self, value):
        if not Event.objects.filter(pk=value).exists():
            raise serializers.ValidationError("Event not found.")
        return value
