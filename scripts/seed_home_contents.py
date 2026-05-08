"""Wipe demo data and seed a single "Stand Up Malam Minggu" event containing
3 stand-up comedy videos.

The home page hits GET /api/contents/public/, which only returns contents whose
event end_time is still in the future.

Note on duration_limit semantics: it represents how long the viewer has to
*download* the video after activation, not a per-viewing time cap. Default is
1 week.

Run from backend/:
    .venv/bin/python scripts/seed_home_contents.py
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

from django.utils import timezone

from apps.core.models import AccessToken, Content, Event, Order

now = timezone.now()
ONE_WEEK = 7 * 24 * 3600

print("Wiping existing Orders, AccessTokens, Contents, and Events…")
Order.objects.all().delete()
AccessToken.objects.all().delete()
Content.objects.all().delete()
Event.objects.all().delete()

EVENT_NAME = "Stand Up Malam Minggu"

CONTENTS: list[tuple[str, str, int]] = [
    ("STAND UP COMEDY GE PAMUNGKAS", "samples/sutc-ge-pamungkas.mp4", 75000),
    ("STAND UP COMEDY ARIE KRITING", "samples/sutc-arie-kriting.mp4", 75000),
    ("STAND UP COMEDY ERNEST PRAKASA", "samples/sutc-ernest-prakasa.mp4", 75000),
]

event = Event.objects.create(
    name=EVENT_NAME,
    start_time=now,
    end_time=now + timedelta(days=365),
)
print(f"OK  Event: {event.name}")

for title, file_path, price in CONTENTS:
    content = Content.objects.create(
        event=event,
        title=title,
        file_path=file_path,
        price=price,
        duration_limit=ONE_WEEK,
    )
    print(f"    └─ {content.title} (Rp {content.price:,})")

print(
    f"\nDone. {Event.objects.count()} event, {Content.objects.count()} contents in DB."
)
