from django.urls import path

from .views import EventListCreateView

app_name = "events"

urlpatterns = [
    path("", EventListCreateView.as_view(), name="event-list-create"),
]
