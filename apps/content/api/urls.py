from django.urls import path

from .views import ContentListCreateView, ContentPublicListView

app_name = "content"

urlpatterns = [
    path("", ContentListCreateView.as_view(), name="content-list-create"),
    path("public/", ContentPublicListView.as_view(), name="content-public-list"),
]
