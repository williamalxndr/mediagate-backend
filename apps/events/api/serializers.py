from rest_framework import serializers

from apps.core.models import Event


class EventSerializer(serializers.ModelSerializer):
    class Meta:
        model = Event
        fields = ["id", "name", "start_time", "end_time", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]


class EventCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Event
        fields = ["name", "start_time", "end_time"]

    def validate(self, attrs):
        if attrs["start_time"] >= attrs["end_time"]:
            raise serializers.ValidationError(
                {"end_time": "End time must be after start time."}
            )
        return attrs
