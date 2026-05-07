from django.urls import path

from .views import (
    AccessDownloadView,
    AccessTokenListCreateView,
    AccessTokenRevokeView,
    AccessView,
)

app_name = "access"

urlpatterns = [
    # Public viewer endpoint
    path("", AccessView.as_view(), name="access"),
    # Public file stream (demo mode — local file)
    path("download/", AccessDownloadView.as_view(), name="download"),
    # Admin token management
    path(
        "access-tokens/",
        AccessTokenListCreateView.as_view(),
        name="token-list-create",
    ),
    path(
        "access-tokens/<int:pk>/revoke/",
        AccessTokenRevokeView.as_view(),
        name="token-revoke",
    ),
]
