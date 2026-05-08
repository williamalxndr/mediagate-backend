from rest_framework import serializers

from apps.core.models import AccessToken, Content

# ---- Public access endpoint serializers ----


class AccessTokenQuerySerializer(serializers.Serializer):
    token = serializers.CharField(required=True)


class AccessPayloadSerializer(serializers.Serializer):
    signed_url = serializers.CharField(read_only=True)
    signed_url_expires_at = serializers.DateTimeField(read_only=True)
    access_expires_at = serializers.DateTimeField(read_only=True)
    remaining_seconds = serializers.IntegerField(read_only=True)
    content_type = serializers.CharField(read_only=True, allow_null=True)
    content = serializers.SerializerMethodField()

    def get_content(self, obj):
        return {
            "id": obj.content_id,
            "event_id": obj.event_id,
        }


# ---- Admin token management serializers ----


class _TokenOrderSummarySerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    customer_name = serializers.CharField(read_only=True)
    whatsapp_e164 = serializers.CharField(read_only=True)


class AccessTokenListSerializer(serializers.ModelSerializer):
    content_id = serializers.IntegerField(source="content.id", read_only=True)
    order = serializers.SerializerMethodField()

    class Meta:
        model = AccessToken
        fields = [
            "id",
            "token",
            "content_id",
            "expires_at",
            "started_at",
            "max_duration",
            "is_revoked",
            "order",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

    def get_order(self, obj):
        order = getattr(obj, "order", None)
        if order is None:
            return None
        return _TokenOrderSummarySerializer(order).data


class AccessTokenCreateSerializer(serializers.Serializer):
    content_id = serializers.IntegerField()
    expires_at = serializers.DateTimeField()
    max_duration = serializers.IntegerField(min_value=1)

    def validate_content_id(self, value):
        if not Content.objects.filter(pk=value).exists():
            raise serializers.ValidationError("Content not found.")
        return value


class RevokeResponseSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    is_revoked = serializers.BooleanField(read_only=True)
