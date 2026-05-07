from django.urls import include, path

urlpatterns = [
    path("auth/", include("apps.auth.api.urls")),
    path("access/", include("apps.access.api.urls")),
    path("contents/", include("apps.content.api.urls")),
    path("events/", include("apps.events.api.urls")),
    path("orders/", include("apps.orders.api.urls")),
]
