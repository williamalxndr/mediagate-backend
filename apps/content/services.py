from __future__ import annotations

from typing import Any

from apps.core.models import Content


def create_content(
    event_id: int,
    duration_limit: int,
    file_path: str | None = None,
    file: Any = None,
    title: str | None = None,
    cover: Any = None,
    price: int | None = None,
) -> Content:
    """Create and return a new Content item.

    Either `file` (uploaded file, demo mode) or `file_path` (object-storage key)
    must be provided. When `file` is provided and `file_path` is not, the saved
    file's name is used as the file_path so the API contract still has a value.
    """
    if file is None and not file_path:
        raise ValueError("Either file or file_path must be provided.")

    content = Content(
        event_id=event_id,
        duration_limit=duration_limit,
        file_path=file_path or "",
        title=title or "",
        price=price,
    )
    if file is not None:
        content.file = file
    if cover is not None:
        content.cover = cover
    content.save()

    if not content.file_path and content.file:
        content.file_path = content.file.name
        content.save(update_fields=["file_path", "updated_at"])

    return content
