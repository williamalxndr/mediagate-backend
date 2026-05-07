from rest_framework import serializers


class AccessTokenQuerySerializer(serializers.Serializer):
    token = serializers.CharField(required=True)


class AccessPayloadSerializer(serializers.Serializer):
    signed_url = serializers.CharField(read_only=True)
    signed_url_expires_at = serializers.DateTimeField(read_only=True)
    access_expires_at = serializers.DateTimeField(read_only=True)
    remaining_seconds = serializers.IntegerField(read_only=True)
    content = serializers.SerializerMethodField()

    def get_content(self, obj):
        return {
            "id": obj.content_id,
            "event_id": obj.event_id,
        }
