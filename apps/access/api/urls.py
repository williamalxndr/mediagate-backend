from django.urls import path

from .views import AccessTokenListCreateView, AccessTokenRevokeView, AccessView

app_name = "access"

urlpatterns = [
    # Public viewer endpoint
    path("", AccessView.as_view(), name="access"),
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
