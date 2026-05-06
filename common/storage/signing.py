from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from botocore.exceptions import BotoCoreError, ClientError
from django.conf import settings
from django.utils import timezone

from common.storage import client as client_module


class StorageError(Exception):
    """Raised when the storage layer cannot produce a signed URL."""


@dataclass(frozen=True)
class SignedUrl:
    url: str
    expires_at: datetime
    ttl_seconds: int


def generate_signed_url(file_path: str) -> SignedUrl:
    if not file_path:
        raise ValueError("file_path must not be empty")
    if file_path.startswith("/"):
        raise ValueError("file_path must not start with '/'")
    if "\x00" in file_path:
        raise ValueError("file_path must not contain a NUL byte")

    bucket = settings.AWS_STORAGE_BUCKET_NAME
    if not bucket:
        raise StorageError("AWS_STORAGE_BUCKET_NAME is not configured")

    ttl_seconds = settings.SIGNED_URL_TTL_SECONDS

    try:
        client = client_module.get_s3_client()
        url = client.generate_presigned_url(
            "get_object",
            Params={"Bucket": bucket, "Key": file_path},
            ExpiresIn=ttl_seconds,
        )
    except (BotoCoreError, ClientError) as exc:
        raise StorageError("failed to generate signed URL") from exc

    expires_at = timezone.now() + timedelta(seconds=ttl_seconds)
    return SignedUrl(url=url, expires_at=expires_at, ttl_seconds=ttl_seconds)
