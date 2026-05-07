from apps.core.models import Content


def create_content(event_id: int, file_path: str, duration_limit: int) -> Content:
    """Create and return a new Content item."""
    return Content.objects.create(
        event_id=event_id,
        file_path=file_path,
        duration_limit=duration_limit,
    )
