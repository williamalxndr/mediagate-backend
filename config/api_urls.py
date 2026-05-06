from django.urls import include, path

urlpatterns = [
    path("access/", include("apps.access.api.urls")),
    path("contents/", include("apps.content.api.urls")),
    path("events/", include("apps.events.api.urls")),
]
