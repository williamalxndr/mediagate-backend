from django.urls import path

from .views import ContentListCreateView

app_name = "content"

urlpatterns = [
    path("", ContentListCreateView.as_view(), name="content-list-create"),
]
