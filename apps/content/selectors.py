from apps.core.models import Content


def list_contents():
    """Return all content items ordered by creation date descending."""
    return Content.objects.select_related("event").all().order_by("-created_at")
