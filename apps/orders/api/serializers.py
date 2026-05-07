from rest_framework import serializers

from apps.core.models import Content, Order

from ..services import InvalidWhatsAppNumberError, normalize_whatsapp


class OrderCreateSerializer(serializers.Serializer):
    customer_name = serializers.CharField(max_length=255)
    whatsapp_number = serializers.CharField(max_length=32)
    content_id = serializers.IntegerField()

    def validate_whatsapp_number(self, value):
        try:
            normalize_whatsapp(value)
        except InvalidWhatsAppNumberError as exc:
            raise serializers.ValidationError(str(exc))
        return value

    def validate_content_id(self, value):
        if not Content.objects.filter(pk=value).exists():
            raise serializers.ValidationError("Content not found.")
        return value


class OrderPublicCreateResponseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Order
        fields = ["id", "status", "created_at"]
        read_only_fields = fields


class _OrderAccessTokenSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    token = serializers.CharField(read_only=True)
    content_id = serializers.IntegerField(read_only=True)
    expires_at = serializers.DateTimeField(read_only=True)
    max_duration = serializers.IntegerField(read_only=True)
    is_revoked = serializers.BooleanField(read_only=True)


class OrderAdminListSerializer(serializers.ModelSerializer):
    access_token = serializers.SerializerMethodField()

    content_title = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = [
            "id",
            "customer_name",
            "whatsapp_number",
            "whatsapp_e164",
            "status",
            "notes",
            "content_id",
            "content_title",
            "access_token",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

    def get_content_title(self, obj):
        if not obj.content_id:
            return None
        return obj.content.title or obj.content.file_path

    def get_access_token(self, obj):
        if not obj.access_token_id:
            return None
        return _OrderAccessTokenSerializer(obj.access_token).data


