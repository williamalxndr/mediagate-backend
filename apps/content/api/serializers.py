from rest_framework import serializers

from apps.core.models import Content, Event


class ContentPublicSerializer(serializers.ModelSerializer):
    event_name = serializers.CharField(source="event.name", read_only=True)
    event_start_time = serializers.DateTimeField(source="event.start_time", read_only=True)
    cover_url = serializers.SerializerMethodField()
    price_display = serializers.SerializerMethodField()

    class Meta:
        model = Content
        fields = [
            "id",
            "title",
            "event_name",
            "event_start_time",
            "cover_url",
            "price",
            "price_display",
            "duration_limit",
        ]
        read_only_fields = fields

    def get_cover_url(self, obj):
        if obj.cover:
            return obj.cover.url
        return None

    def get_price_display(self, obj):
        if obj.price:
            return f"Rp {obj.price:,.0f}".replace(",", ".")
        return None


class ContentSerializer(serializers.ModelSerializer):
    event_id = serializers.IntegerField(source="event.id", read_only=True)
    has_file = serializers.SerializerMethodField()
    has_cover = serializers.SerializerMethodField()
    cover_url = serializers.SerializerMethodField()

    class Meta:
        model = Content
        fields = [
            "id",
            "event_id",
            "title",
            "file_path",
            "has_file",
            "cover",
            "has_cover",
            "cover_url",
            "price",
            "duration_limit",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "has_file", "has_cover", "cover_url", "created_at", "updated_at"]

    def get_has_file(self, obj) -> bool:
        return bool(obj.file)

    def get_has_cover(self, obj) -> bool:
        return bool(obj.cover)

    def get_cover_url(self, obj):
        if obj.cover:
            return obj.cover.url
        return None


class ContentCreateSerializer(serializers.Serializer):
    event_id = serializers.IntegerField()
    title = serializers.CharField(max_length=255, required=False, allow_blank=True)
    file_path = serializers.CharField(max_length=1024, required=False, allow_blank=True)
    file = serializers.FileField(required=False)
    cover = serializers.ImageField(required=False)
    price = serializers.IntegerField(min_value=0, required=False)
    duration_limit = serializers.IntegerField(min_value=1)

    def validate_event_id(self, value):
        if not Event.objects.filter(pk=value).exists():
            raise serializers.ValidationError("Event not found.")
        return value

    def validate(self, attrs):
        if not attrs.get("file") and not attrs.get("file_path"):
            raise serializers.ValidationError(
                "Either 'file' (upload) or 'file_path' (storage key) must be provided."
            )
        return attrs
