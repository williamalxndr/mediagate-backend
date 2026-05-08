"""One-shot seed: create a demo Event, Content (with a real file on disk),
and AccessToken so the /download flow can be tested end-to-end.

Run from backend/:
    .venv/bin/python scripts/seed_demo_token.py
"""

import os
import sys
from datetime import timedelta
from pathlib import Path

import django

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")
django.setup()

from django.core.files.base import ContentFile
from django.utils import timezone

from apps.core.models import AccessToken, Content, Event

DEMO_TOKEN = "demo-token-please-replace"

now = timezone.now()

event, _ = Event.objects.get_or_create(
    name="Demo Event",
    defaults={
        "start_time": now - timedelta(hours=1),
        "end_time": now + timedelta(days=7),
    },
)
# If event already existed but is now outside its window, refresh it.
event.start_time = now - timedelta(hours=1)
event.end_time = now + timedelta(days=7)
event.save(update_fields=["start_time", "end_time", "updated_at"])

content, created = Content.objects.get_or_create(
    event=event,
    file_path="demo/hello.txt",
    defaults={"duration_limit": 3600},
)
if created or not content.file:
    content.file.save(
        "hello.txt",
        ContentFile(
            b"Hello from the demo file. If you can read this, the "
            b"/download?token=... flow works end-to-end.\n"
        ),
        save=True,
    )

token, _ = AccessToken.objects.update_or_create(
    token=DEMO_TOKEN,
    defaults={
        "content": content,
        "expires_at": now + timedelta(days=7),
        "started_at": None,
        "max_duration": 3600,
        "is_revoked": False,
    },
)

print(f"Event:    {event.id} {event.name} ({event.start_time} → {event.end_time})")
print(f"Content:  {content.id} file_path={content.file_path} file={content.file.name}")
print(f"Token:    {token.token}")
print(f"Open:     http://localhost:3000/download?token={token.token}")
