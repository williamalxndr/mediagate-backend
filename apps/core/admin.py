from django.contrib import admin
from django.contrib.auth.models import Group

from apps.core.models import AccessToken, Content, Event
from apps.core.roles import ROLE_CHOICES


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ("name", "start_time", "end_time", "created_at")
    search_fields = ("name",)
    ordering = ("-start_time",)


@admin.register(Content)
class ContentAdmin(admin.ModelAdmin):
    list_display = ("file_path", "event", "duration_limit", "created_at")
    list_filter = ("event",)
    search_fields = ("file_path", "event__name")
    ordering = ("event", "file_path")


@admin.register(AccessToken)
class AccessTokenAdmin(admin.ModelAdmin):
    list_display = (
        "token",
        "content",
        "expires_at",
        "started_at",
        "max_duration",
        "is_revoked",
    )
    list_filter = ("is_revoked", "expires_at", "started_at")
    search_fields = ("token", "content__file_path", "content__event__name")
    readonly_fields = ("token", "created_at", "updated_at")
    ordering = ("-created_at",)


class RoleListFilter(admin.SimpleListFilter):
    title = "project role"
    parameter_name = "project_role"

    def lookups(self, request, model_admin):
        return tuple((role, role.title()) for role in ROLE_CHOICES)

    def queryset(self, request, queryset):
        if not self.value():
            return queryset
        return queryset.filter(name=self.value())


class GroupAdmin(admin.ModelAdmin):
    list_display = ("name",)
    list_filter = (RoleListFilter,)
    search_fields = ("name",)


admin.site.unregister(Group)
admin.site.register(Group, GroupAdmin)
