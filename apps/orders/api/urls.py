from django.urls import path

from .views import (
    OrderAdminDetailView,
    OrderAdminListView,
    OrderCancelView,
    OrderCreateView,
    OrderIssueTokenView,
)

app_name = "orders"

urlpatterns = [
    path("", OrderCreateView.as_view(), name="order-create"),
    path("admin/", OrderAdminListView.as_view(), name="order-admin-list"),
    path(
        "admin/<int:pk>/",
        OrderAdminDetailView.as_view(),
        name="order-admin-detail",
    ),
    path(
        "admin/<int:pk>/issue-token/",
        OrderIssueTokenView.as_view(),
        name="order-issue-token",
    ),
    path(
        "admin/<int:pk>/cancel/",
        OrderCancelView.as_view(),
        name="order-cancel",
    ),
]
