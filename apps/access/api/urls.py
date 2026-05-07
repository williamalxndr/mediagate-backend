from django.urls import path

from .views import AccessView

app_name = "access"

urlpatterns = [
    path("", AccessView.as_view(), name="access"),
]
