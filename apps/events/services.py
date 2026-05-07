from apps.core.models import Event


def create_event(name: str, start_time, end_time) -> Event:
    """Create and return a new Event."""
    return Event.objects.create(
        name=name,
        start_time=start_time,
        end_time=end_time,
    )
