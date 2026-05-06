from __future__ import annotations

from typing import Any

import boto3
from django.conf import settings

_client: Any = None


def get_s3_client() -> Any:
    global _client
    if _client is None:
        kwargs: dict[str, Any] = {
            "service_name": "s3",
            "aws_access_key_id": settings.AWS_ACCESS_KEY_ID,
            "aws_secret_access_key": settings.AWS_SECRET_ACCESS_KEY,
        }
        if settings.AWS_S3_REGION_NAME:
            kwargs["region_name"] = settings.AWS_S3_REGION_NAME
        if settings.AWS_S3_ENDPOINT_URL:
            kwargs["endpoint_url"] = settings.AWS_S3_ENDPOINT_URL
        _client = boto3.client(**kwargs)
    return _client


def _reset_client_for_tests() -> None:
    global _client
    _client = None
