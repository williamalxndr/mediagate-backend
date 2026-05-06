"""Unit tests for common.storage signed URL service.

These tests pin the contract documented in common/storage/API.md.
The boto3 S3 client is mocked — no network calls are made.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest
from botocore.exceptions import ClientError, EndpointConnectionError
from django.test import override_settings
from django.utils import timezone as dj_timezone

from common.storage import SignedUrl, StorageError, generate_signed_url


@override_settings(
    AWS_STORAGE_BUCKET_NAME="test-bucket",
    AWS_ACCESS_KEY_ID="test-key",
    AWS_SECRET_ACCESS_KEY="test-secret",
    AWS_S3_REGION_NAME="us-east-1",
    AWS_S3_ENDPOINT_URL="",
    SIGNED_URL_TTL_SECONDS=300,
)
class GenerateSignedUrlSuccessTests:
    """Happy-path behaviour."""

    def test_returns_signed_url_dataclass(self):
        with patch("common.storage.client.get_s3_client") as get_client:
            get_client.return_value.generate_presigned_url.return_value = (
                "https://s3.amazonaws.com/test-bucket/path/file.mp4?signature=abc"
            )

            result = generate_signed_url("path/file.mp4")

        assert isinstance(result, SignedUrl)
        assert result.url.startswith("https://")
        assert result.ttl_seconds == 300

    def test_calls_boto3_with_get_object_and_correct_params(self):
        with patch("common.storage.client.get_s3_client") as get_client:
            client = get_client.return_value
            client.generate_presigned_url.return_value = "https://signed.example/url"

            generate_signed_url("events/launch/video.mp4")

            client.generate_presigned_url.assert_called_once()
            args, kwargs = client.generate_presigned_url.call_args
            # First positional arg or "ClientMethod" kwarg should be "get_object"
            client_method = args[0] if args else kwargs.get("ClientMethod")
            assert client_method == "get_object"
            assert kwargs["Params"]["Bucket"] == "test-bucket"
            assert kwargs["Params"]["Key"] == "events/launch/video.mp4"
            assert kwargs["ExpiresIn"] == 300

    def test_expires_at_is_now_plus_ttl_in_utc(self):
        fixed_now = datetime(2026, 5, 7, 10, 0, 0, tzinfo=timezone.utc)
        with (
            patch("common.storage.client.get_s3_client") as get_client,
            patch("common.storage.signing.timezone.now", return_value=fixed_now),
        ):
            get_client.return_value.generate_presigned_url.return_value = "https://x"

            result = generate_signed_url("a.mp4")

        assert result.expires_at == fixed_now + timedelta(seconds=300)
        assert result.expires_at.tzinfo is not None

    def test_expires_at_is_timezone_aware(self):
        with patch("common.storage.client.get_s3_client") as get_client:
            get_client.return_value.generate_presigned_url.return_value = "https://x"

            result = generate_signed_url("a.mp4")

        assert dj_timezone.is_aware(result.expires_at)

    @override_settings(SIGNED_URL_TTL_SECONDS=60)
    def test_uses_settings_ttl_value(self):
        with patch("common.storage.client.get_s3_client") as get_client:
            get_client.return_value.generate_presigned_url.return_value = "https://x"

            result = generate_signed_url("a.mp4")

            assert result.ttl_seconds == 60
            _, kwargs = get_client.return_value.generate_presigned_url.call_args
            assert kwargs["ExpiresIn"] == 60


@override_settings(
    AWS_STORAGE_BUCKET_NAME="test-bucket",
    AWS_ACCESS_KEY_ID="k",
    AWS_SECRET_ACCESS_KEY="s",
    SIGNED_URL_TTL_SECONDS=300,
)
class GenerateSignedUrlInputValidationTests:
    """ValueError cases — caught before any boto3 call."""

    def test_empty_file_path_raises_value_error(self):
        with patch("common.storage.client.get_s3_client") as get_client:
            with pytest.raises(ValueError):
                generate_signed_url("")
            get_client.assert_not_called()

    def test_file_path_starting_with_slash_raises_value_error(self):
        with patch("common.storage.client.get_s3_client") as get_client:
            with pytest.raises(ValueError):
                generate_signed_url("/events/launch/video.mp4")
            get_client.assert_not_called()

    def test_file_path_with_nul_byte_raises_value_error(self):
        with patch("common.storage.client.get_s3_client") as get_client:
            with pytest.raises(ValueError):
                generate_signed_url("events/\x00/video.mp4")
            get_client.assert_not_called()


class GenerateSignedUrlConfigErrorTests:
    """StorageError when configuration is incomplete."""

    @override_settings(AWS_STORAGE_BUCKET_NAME="")
    def test_missing_bucket_name_raises_storage_error(self):
        with pytest.raises(StorageError):
            generate_signed_url("a.mp4")


@override_settings(
    AWS_STORAGE_BUCKET_NAME="test-bucket",
    AWS_ACCESS_KEY_ID="k",
    AWS_SECRET_ACCESS_KEY="s",
    SIGNED_URL_TTL_SECONDS=300,
)
class GenerateSignedUrlBoto3ErrorTests:
    """boto3 errors are wrapped as StorageError, with original chained as __cause__."""

    def test_client_error_is_wrapped(self):
        boto_err = ClientError(
            {"Error": {"Code": "AccessDenied", "Message": "nope"}},
            "GetObject",
        )
        with patch("common.storage.client.get_s3_client") as get_client:
            get_client.return_value.generate_presigned_url.side_effect = boto_err

            with pytest.raises(StorageError) as exc_info:
                generate_signed_url("a.mp4")

        assert exc_info.value.__cause__ is boto_err

    def test_endpoint_connection_error_is_wrapped(self):
        boto_err = EndpointConnectionError(endpoint_url="http://minio:9000")
        with patch("common.storage.client.get_s3_client") as get_client:
            get_client.return_value.generate_presigned_url.side_effect = boto_err

            with pytest.raises(StorageError) as exc_info:
                generate_signed_url("a.mp4")

        assert exc_info.value.__cause__ is boto_err


@override_settings(
    AWS_STORAGE_BUCKET_NAME="test-bucket",
    AWS_ACCESS_KEY_ID="k",
    AWS_SECRET_ACCESS_KEY="s",
    SIGNED_URL_TTL_SECONDS=300,
)
class S3ClientFactoryTests:
    """get_s3_client uses settings, including MinIO endpoint_url when set."""

    @override_settings(AWS_S3_ENDPOINT_URL="http://minio.local:9000")
    def test_uses_endpoint_url_when_set(self):
        from common.storage import client as client_module

        client_module._reset_client_for_tests()
        with patch("common.storage.client.boto3.client") as boto3_client:
            boto3_client.return_value = MagicMock()
            client_module.get_s3_client()

        _, kwargs = boto3_client.call_args
        assert kwargs["endpoint_url"] == "http://minio.local:9000"

    @override_settings(AWS_S3_ENDPOINT_URL="")
    def test_no_endpoint_url_for_aws_s3(self):
        from common.storage import client as client_module

        client_module._reset_client_for_tests()
        with patch("common.storage.client.boto3.client") as boto3_client:
            boto3_client.return_value = MagicMock()
            client_module.get_s3_client()

        _, kwargs = boto3_client.call_args
        assert kwargs.get("endpoint_url") in (None, "")
