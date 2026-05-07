from apps.core.models import Event


def list_events():
    """Return all events ordered by start_time descending."""
    return Event.objects.all()
